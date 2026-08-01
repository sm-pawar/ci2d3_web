"""
Lineage service for ice island lineage tracking.

This module ports the graph-traversal logic from the reference analysis code
(ref/python/ci2d3.py, class CI2D3Handler.IgraphHandler) to run directly
against the PostGIS `iceislands` table instead of an in-memory igraph.

Lineage model
-------------
Each ice island observation (row) has:
  - `inst`    : a unique instance identifier (a graph vertex)
  - `lineage` : the `inst` of its parent observation (a directed edge
                parent -> child, i.e. child.lineage == parent.inst)

As in the reference `create_igraph()`, an edge only exists when a row's
`lineage` value is itself a valid `inst` in the dataset. Root observations
reference a calving source string (e.g. "..._P08") that is not an `inst`,
so they have no incoming edge.

The reference builds the graph as *undirected* (directed=False), which means
`after()` / `before()` (igraph `subcomponent`) return the whole connected
component -- the complete rooted lineage tree for a given vertex. That is the
behaviour used for the website's "Track Lineage" button (mode="all").

Modes
-----
- "chain"  : (default) this observation's own lineage line -- all of its
             ancestors plus all of its descendants. This is what "the lineage
             of this polygon" means for the map UI.
- "after"  : descendants only (this observation and everything that fractured
             / drifted from it afterwards).
- "before" : ancestors only (this observation and everything it came from).
- "all"    : the entire connected component, i.e. every observation reachable
             by ignoring edge direction. This matches the reference
             `subcomponent()` behaviour literally, but note the reference
             builds the graph with directed=False, which makes its after()
             and before() both collapse to the whole component. On this
             dataset a component averages ~2,800 observations (max ~6,300)
             because every fracture descendant of a calving event is joined
             into one component, so "all" is offered but is not the default.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from config import Config


# Join condition for the single-direction recursive traversals, keyed by mode.
# t = the lineage set accumulated so far, i = candidate row being tested.
#   i.lineage = t.inst    -> i is a CHILD of a node already found (descend)
#   i.inst    = t.lineage -> i is the PARENT of a node already found (ascend)
_MODE_JOIN_CONDITIONS = {
    'all': '(i.lineage = t.inst OR i.inst = t.lineage)',
    'after': 'i.lineage = t.inst',
    'before': 'i.inst = t.lineage',
}

# "chain" needs two independent traversals (up and down) unioned together.
# Doing it with a single OR'd join instead would walk sideways into cousin
# branches and degenerate into the whole connected component.
_CHAIN_CTE = """
    WITH RECURSIVE ancestors AS (
        SELECT inst, lineage FROM {table} WHERE inst = :inst
        UNION
        SELECT i.inst, i.lineage
        FROM {table} i
        JOIN ancestors a ON i.inst = a.lineage
    ),
    descendants AS (
        SELECT inst, lineage FROM {table} WHERE inst = :inst
        UNION
        SELECT i.inst, i.lineage
        FROM {table} i
        JOIN descendants d ON i.lineage = d.inst
    ),
    lineage_tree AS (
        SELECT inst FROM ancestors
        UNION
        SELECT inst FROM descendants
    )
"""

_SINGLE_CTE = """
    WITH RECURSIVE lineage_tree AS (
        SELECT inst, lineage FROM {table} WHERE inst = :inst
        UNION
        SELECT i.inst, i.lineage
        FROM {table} i
        JOIN lineage_tree t ON {join_condition}
    )
"""

# Safety cap: a single lineage can span thousands of polygons. Returning them
# all would stall the browser, so cap the response and report the true total.
DEFAULT_MAX_FEATURES = 2000

# Columns that must never be exposed as feature properties:
#   - geom     : the real PostGIS geometry (returned separately as GeoJSON)
#   - gid      : internal primary key
#   - geometry : a leftover text column from the source shapefile DBF that
#                collides with the GeoJSON "geometry" alias
_EXCLUDED_COLUMNS = ('geom', 'gid', 'geometry')


class LineageService:
    """Service class for lineage-tree queries against the iceislands table."""

    TABLE = 'iceislands'

    def __init__(self):
        self.engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            poolclass=NullPool,
            echo=Config.SQLALCHEMY_ECHO
        )
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def _get_property_columns(self, session):
        """Return the ordered list of property columns (excludes geom/gid/geometry)."""
        excluded = ', '.join(f"'{c}'" for c in _EXCLUDED_COLUMNS)
        columns_query = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{self.TABLE}'
                AND column_name NOT IN ({excluded})
            ORDER BY ordinal_position
        """)
        return [row[0] for row in session.execute(columns_query).fetchall()]

    def get_lineage(self, inst, mode='chain', max_features=DEFAULT_MAX_FEATURES):
        """
        Return the lineage of a given ice island instance as GeoJSON.

        Args:
            inst: The `inst` identifier of the clicked/selected ice island.
            mode: "chain" (default, ancestors + descendants of this
                  observation), "after" (descendants), "before" (ancestors),
                  or "all" (entire connected component).
            max_features: Safety cap on returned features.

        Returns:
            GeoJSON FeatureCollection of the lineage polygons, ordered
            chronologically by scenedate. The "lineage" metadata block reports
            the true total and whether the response was truncated.
        """
        mode = (mode or 'chain').lower()
        valid_modes = ['chain'] + list(_MODE_JOIN_CONDITIONS)
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Choose from {valid_modes}")

        if not inst or not str(inst).strip():
            raise ValueError("An 'inst' identifier is required for lineage tracking.")

        try:
            limit = int(max_features)
        except (TypeError, ValueError):
            limit = DEFAULT_MAX_FEATURES
        limit = max(1, min(limit, 10000))

        # Build the traversal CTE for the requested mode. Both variants use
        # UNION (not UNION ALL) so already-visited rows are dropped, which
        # guarantees termination even if the data contains a cycle.
        if mode == 'chain':
            cte = _CHAIN_CTE.format(table=self.TABLE)
        else:
            cte = _SINGLE_CTE.format(
                table=self.TABLE,
                join_condition=_MODE_JOIN_CONDITIONS[mode]
            )

        session = self.get_session()
        try:
            column_names = self._get_property_columns(session)
            columns_str = ', '.join(column_names)

            query = text(f"""
                {cte}
                SELECT
                    gid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json AS geometry,
                    {columns_str},
                    COUNT(*) OVER () AS total_in_lineage
                FROM {self.TABLE}
                WHERE inst IN (SELECT inst FROM lineage_tree)
                ORDER BY scenedate, gid
                LIMIT :limit
            """)

            results = session.execute(
                query, {'inst': inst, 'limit': limit}
            ).fetchall()

            features = []
            total = 0
            for row in results:
                # row[0]=gid, row[1]=geometry, then property columns, then total
                properties = {
                    col_name: row[i + 2]
                    for i, col_name in enumerate(column_names)
                }
                total = row[len(column_names) + 2]
                features.append({
                    'type': 'Feature',
                    'id': row[0],
                    'geometry': row[1],
                    'properties': properties
                })

            return {
                'type': 'FeatureCollection',
                'features': features,
                'count': len(features),
                'lineage': {
                    'inst': inst,
                    'mode': mode,
                    'total': total,
                    'truncated': total > len(features)
                }
            }

        except Exception as e:
            print(f"Error tracking lineage: {e}")
            raise
        finally:
            session.close()


# Singleton instance
lineage_service = LineageService()
