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
- "all"    : the full connected lineage tree (ancestors + descendants),
             matching the reference undirected subcomponent behaviour.
- "after"  : descendants only (this observation and everything that fractured
             / drifted from it afterwards).
- "before" : ancestors only (this observation and everything it came from).
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from config import Config


# Join condition for the recursive traversal, keyed by mode.
# t = the lineage tree accumulated so far, i = candidate row being tested.
#   i.lineage = t.inst  -> i is a CHILD of a node already in the tree (descend)
#   i.inst    = t.lineage -> i is the PARENT of a node already in the tree (ascend)
_MODE_JOIN_CONDITIONS = {
    'all': '(i.lineage = t.inst OR i.inst = t.lineage)',
    'after': 'i.lineage = t.inst',
    'before': 'i.inst = t.lineage',
}

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

    def get_lineage(self, inst, mode='all'):
        """
        Return the lineage tree for a given ice island instance as GeoJSON.

        Args:
            inst: The `inst` identifier of the clicked/selected ice island.
            mode: One of "all" (full connected tree, default), "after"
                  (descendants), or "before" (ancestors).

        Returns:
            GeoJSON FeatureCollection of all ice island polygons in the lineage,
            ordered chronologically by scenedate. Includes a "lineage" metadata
            block describing the query.
        """
        mode = (mode or 'all').lower()
        if mode not in _MODE_JOIN_CONDITIONS:
            raise ValueError(
                f"Invalid mode: {mode}. Choose from {list(_MODE_JOIN_CONDITIONS)}"
            )

        if not inst or not str(inst).strip():
            raise ValueError("An 'inst' identifier is required for lineage tracking.")

        join_condition = _MODE_JOIN_CONDITIONS[mode]

        session = self.get_session()
        try:
            column_names = self._get_property_columns(session)
            columns_str = ', '.join(column_names)

            # Recursive CTE that walks the parent/child edges starting from the
            # selected instance. Uses UNION (not UNION ALL) so already-visited
            # rows are de-duplicated, which guarantees termination even if the
            # data contains a cycle.
            query = text(f"""
                WITH RECURSIVE lineage_tree AS (
                    SELECT inst, lineage
                    FROM {self.TABLE}
                    WHERE inst = :inst
                    UNION
                    SELECT i.inst, i.lineage
                    FROM {self.TABLE} i
                    JOIN lineage_tree t ON {join_condition}
                )
                SELECT
                    gid,
                    ST_AsGeoJSON(ST_Transform(geom, 4326))::json AS geometry,
                    {columns_str}
                FROM {self.TABLE}
                WHERE inst IN (SELECT inst FROM lineage_tree)
                ORDER BY scenedate, gid
            """)

            results = session.execute(query, {'inst': inst}).fetchall()

            features = []
            for row in results:
                # row[0] = gid, row[1] = geometry, row[2:] = property columns
                properties = {
                    col_name: row[i + 2]
                    for i, col_name in enumerate(column_names)
                }
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
                    'mode': mode
                }
            }

        except Exception as e:
            print(f"Error tracking lineage: {e}")
            raise
        finally:
            session.close()


# Singleton instance
lineage_service = LineageService()
