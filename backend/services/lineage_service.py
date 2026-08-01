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


# Every query computes the ancestor and descendant sets of the selected
# instance, regardless of mode. The traversal set itself is chosen per mode,
# but membership in these two sets is what lets each returned feature be
# tagged as "before" / "after" / "self" so the map can colour them.
#
# Ancestors walk up   (i.inst    = a.lineage -> i is the PARENT of a found node)
# Descendants walk down (i.lineage = d.inst  -> i is a CHILD of a found node)
#
# Note both sets include the seed row itself; the role CASE checks "self"
# first so the seed is never mislabelled.
_ROLE_CTES = """
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
    ){extra_ctes},
    lineage_tree AS (
        {tree_select}
    )
"""

# Extra CTE needed only by mode "all", which walks edges in both directions
# and so also picks up cousin/sibling branches that are neither ancestors
# nor descendants of the selected instance.
_COMPONENT_CTE = """,
    component AS (
        SELECT inst, lineage FROM {table} WHERE inst = :inst
        UNION
        SELECT i.inst, i.lineage
        FROM {table} i
        JOIN component c ON (i.lineage = c.inst OR i.inst = c.lineage)
    )"""

# Which set of instances each mode actually returns.
_MODE_TREE_SELECT = {
    'chain': 'SELECT inst FROM ancestors UNION SELECT inst FROM descendants',
    'before': 'SELECT inst FROM ancestors',
    'after': 'SELECT inst FROM descendants',
    'all': 'SELECT inst FROM component',
}

# Per-feature relationship to the clicked polygon. Drives the map colours.
_ROLE_CASE = """
    CASE
        WHEN f.inst = :inst THEN 'self'
        WHEN EXISTS (SELECT 1 FROM ancestors a WHERE a.inst = f.inst) THEN 'before'
        WHEN EXISTS (SELECT 1 FROM descendants d WHERE d.inst = f.inst) THEN 'after'
        ELSE 'related'
    END AS lineage_role
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
        if mode not in _MODE_TREE_SELECT:
            raise ValueError(
                f"Invalid mode: {mode}. Choose from {list(_MODE_TREE_SELECT)}"
            )

        if not inst or not str(inst).strip():
            raise ValueError("An 'inst' identifier is required for lineage tracking.")

        try:
            limit = int(max_features)
        except (TypeError, ValueError):
            limit = DEFAULT_MAX_FEATURES
        limit = max(1, min(limit, 10000))

        # All traversals use UNION (not UNION ALL) so already-visited rows are
        # dropped, which guarantees termination even if the data has a cycle.
        cte = _ROLE_CTES.format(
            table=self.TABLE,
            extra_ctes=(
                _COMPONENT_CTE.format(table=self.TABLE) if mode == 'all' else ''
            ),
            tree_select=_MODE_TREE_SELECT[mode]
        )

        session = self.get_session()
        try:
            column_names = self._get_property_columns(session)
            columns_str = ', '.join(f'f.{c}' for c in column_names)

            query = text(f"""
                {cte}
                SELECT
                    f.gid,
                    ST_AsGeoJSON(ST_Transform(f.geom, 4326))::json AS geometry,
                    {columns_str},
                    COUNT(*) OVER () AS total_in_lineage,
                    {_ROLE_CASE}
                FROM {self.TABLE} f
                WHERE f.inst IN (SELECT inst FROM lineage_tree)
                ORDER BY f.scenedate, f.gid
                LIMIT :limit
            """)

            results = session.execute(
                query, {'inst': inst, 'limit': limit}
            ).fetchall()

            features = []
            total = 0
            role_counts = {'self': 0, 'before': 0, 'after': 0, 'related': 0}
            n_cols = len(column_names)

            for row in results:
                # row layout:
                #   [0]            gid
                #   [1]            geometry
                #   [2 .. n_cols+1] property columns
                #   [n_cols+2]     total_in_lineage
                #   [n_cols+3]     lineage_role
                properties = {
                    col_name: row[i + 2]
                    for i, col_name in enumerate(column_names)
                }
                total = row[n_cols + 2]
                role = row[n_cols + 3]

                # Expose the relationship to the clicked polygon so the map can
                # colour ancestors and descendants differently.
                properties['lineage_role'] = role
                if role in role_counts:
                    role_counts[role] += 1

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
                    'truncated': total > len(features),
                    'roles': role_counts
                }
            }

        except Exception as e:
            print(f"Error tracking lineage: {e}")
            raise
        finally:
            session.close()


# Singleton instance
lineage_service = LineageService()
