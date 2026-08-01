"""
ci2d3.py

CI2D3 Database Analysis
=======================

A collection of functions and classes for analyzing the CI2D3 (Canadian Ice Island Drift, Deterioration and Detection) Database.

This module provides tools for:
- Loading and handling geospatial data
- Creating and analyzing ice island drift graphs
- Tracking ice island lineage and fracture events
- Visualizing calving events and drift patterns

Classes
-------
CI2D3Handler
    Main handler class for CI2D3 database operations
IgraphHandler
    Handles graph operations and analysis
GDFHandler
    Handles GeoDataFrame operations
CalvingPlotter
    Handles visualization of calving events

Dependencies
-----------
- pandas
- geopandas
- igraph
- matplotlib
- seaborn
- shapely


Authors  - Mitchell Albert, Derek Mueller
Ported to Python based on the orignal work of Emilie Stewart-Jones and Derek Mueller
Last edited. Feb 2025 - Derek Mueller


# TODO - check all docstrings to make sure they are accurate.  


"""

# imports
from datetime import timedelta
from logger_setup import setup_logger
from typing import List, Dict, Any, Union
import collections.abc

from defs import *

SHAPE_EXT = ".shp"
GPKG_EXT = ".gpkg"

import pandas as pd
import geopandas as gpd
import igraph as ig
from igraph import Graph
import matplotlib.pyplot as plt
import seaborn as sns

# import fiona
import os
import logging
from shapely.geometry import Point
import pdb

# Setup logging configuration
logger = setup_logger(
    "CI2D3Helper", "ci2d3_helper.log", level=logging.INFO, console=True
)


# %% Class definition
class CI2D3Handler:
    """
    Main handler class for CI2D3 database operations.

    Parameters
    ----------
    filepath : str
        Path to the GeoPackage or Shapefile
    layer : str, optional
        Layer name for GeoPackage files

    Attributes
    ----------
    gdf : GDFHandler
        Handler for GeoDataFrame operations
    igraph : IgraphHandler
        Handler for graph operations
    """

    def __init__(self, filepath, layer=None):
        self.gdf = self.GDFHandler(filepath, layer=layer)
        self.igraph = self.IgraphHandler(self.gdf.gdf)

    class IgraphHandler:
        """
        Handles graph operations for ice island tracking.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            GeoDataFrame containing ice island data

        Methods
        -------
        create_igraph()
            Creates an igraph object from the GeoDataFrame
        after(inst)
            Returns subgraph of all nodes after given instance
        before(inst)
            Returns subgraph of all nodes before given instance
        terminal()
            Returns list of terminal node names
        drifts(calvingloc, calvingyr, wk_num)
            Isolates branches of drifting ice islands
        """

        def __init__(self, gdf: gpd.GeoDataFrame):
            self.gdf = gdf  # should come first?!
            self.igraph = self.create_igraph()

        def create_igraph(self) -> ig.Graph:
            """
            Create a directed graph representation of ice island lineage.

            This method constructs an igraph object where nodes represent ice island instances
            and edges represent parent-child relationships between instances. The graph
            captures the complete deterioration sequence of ice islands.

            Returns
            -------
            igraph.Graph
                A directed graph with the following properties:
                - Vertices: Ice island instances
                - Edges: Parent-child relationships
                - Vertex attributes:
                    - name: str, unique identifier
                    - area: float, ice island area in km²
                    - perimeter: float, ice island perimeter in km
                    - date: datetime, observation date
                    - x: float, longitude coordinate
                    - y: float, latitude coordinate
                - Edge attributes:
                    - weight: float, time difference between parent and child in days

            Notes
            -----
            The graph is constructed using the following rules:
            - Each vertex corresponds to a unique ice island instance
            - Edges are directed from parent to child instances
            - Isolated vertices represent independent ice islands
            - Multiple outgoing edges indicate fracturing events

            Examples
            --------
            >>> handler = IgraphHandler(gdf)
            >>> g = handler.create_igraph()
            >>> print(g.vs['name'])  # Print all vertex names
            >>> print(g.es['weight'])  # Print all edge weights

            """
            # make sure gdf is valid
            if self.gdf.empty:
                logger.error("GeoDataFrame is empty.")
                raise ValueError("GeoDataFrame must not be empty.")

            # Ensure the required columns are present
            required_columns = {LINEAGE, INST}
            missing_columns = required_columns - set(self.gdf.columns)
            if missing_columns:
                logger.error(
                    f"Required columns {missing_columns} are missing in the GeoDataFrame."
                )
                raise ValueError(
                    f"GeoDataFrame must contain columns: {required_columns}"
                )

            # Create the edge list
            edgelist = self.gdf[[LINEAGE, INST]]
            edgelist = edgelist[edgelist[LINEAGE].isin(edgelist[INST])]

            # Create attribute table for vertices
            vert_attrib_df = self.gdf.drop(columns=[INST]).copy()
            vert_attrib_df.insert(0, INST, self.gdf[INST])

            # Creating igraph object
            igraph = ig.Graph.DataFrame(
                edgelist, directed=False, use_vids=False, vertices=vert_attrib_df
            )

            # Check and use latitude and longitude columns for spatial coordinates in igraph nodes
            if LAT in self.gdf.columns and LON in self.gdf.columns:
                logger.info("Adding latitude and longitude to igraph nodes.")
                igraph.vs["x"] = (
                    self.gdf.set_index(INST).loc[igraph.vs["name"], LON].values
                )
                igraph.vs["y"] = (
                    self.gdf.set_index(INST).loc[igraph.vs["name"], LAT].values
                )
            else:
                logger.error("Latitude and/or longitude columns are missing.")
                raise ValueError(
                    "GeoDataFrame must contain 'latitude' and 'longitude' columns for spatial coordinates."
                )

            return igraph

        def after(self, inst: str) -> ig.Graph:
            """
            Return a subgraph containing all descendants of a given ice island instance.

            This method traverses the graph starting from the specified instance and
            returns a new graph containing only the vertices and edges that represent
            subsequent instances in the deterioration sequence.

            Parameters
            ----------
            inst : str
                Instance identifier of the starting vertex

            Returns
            -------
            igraph.Graph
                A directed graph containing:
                - The specified instance vertex
                - All descendant vertices
                - All edges connecting these vertices

                The returned graph preserves all vertex and edge attributes from
                the original graph.

            Raises
            ------
            ValueError
                If the specified instance is not found in the graph
            KeyError
                If the graph's vertex attributes are missing or corrupted

            Notes
            -----
            The method performs a forward traversal from the specified vertex,
            including all possible paths of deterioration. This includes both
            direct descendants and instances resulting from fracturing events.

            Examples
            --------
            >>> handler = IgraphHandler(gdf)
            >>> g = handler.create_igraph()
            >>> descendants = handler.after("PYI_2012_01")
            >>> print(descendants.vs['name'])  # Print all descendant instance names

            """
            v_after = self.igraph.subcomponent(inst, mode="out")
            g_after = self.igraph.induced_subgraph(v_after)
            return g_after

        def before(self, inst: str) -> ig.Graph:
            """
            Return a subgraph containing all ancestors of a given ice island instance.

            This method traverses the graph backwards from the specified instance and
            returns a new graph containing only the vertices and edges that represent
            previous instances in the deterioration sequence.

            Parameters
            ----------
            inst : str
                Instance identifier of the target vertex

            Returns
            -------
            igraph.Graph
                A directed graph containing:
                - The specified instance vertex
                - All ancestor vertices
                - All edges connecting these vertices

                The returned graph preserves all vertex and edge attributes from
                the original graph.

            Raises
            ------
            ValueError
                If the specified instance is not found in the graph
            KeyError
                If the graph's vertex attributes are missing or corrupted

            Notes
            -----
            The method performs a backward traversal from the specified vertex,
            including all possible paths of formation. This includes both
            direct ancestors and instances that were involved in fracturing events
            leading to the target instance.

            Examples
            --------
            >>> handler = IgraphHandler(gdf)
            >>> g = handler.create_igraph()
            >>> ancestors = handler.before("PYI_2012_03")
            >>> print(ancestors.vs['name'])  # Print all ancestor instance names

            """
            v_before = self.igraph.subcomponent(inst, mode="in")
            g_before = self.igraph.induced_subgraph(v_before)
            return g_before

        def terminal(self) -> List[str]:
            """
            Return a list of terminal ice island instances.

            Terminal instances are those that represent the final state of an ice island
            in the database, having no subsequent observations or child instances. These
            may represent instances where the ice island has completely deteriorated,
            become too small to track, or reached the end of the observation period.

            Returns
            -------
            list of str
                A list of instance identifiers for all terminal vertices in the graph.
                Terminal vertices are those with an out-degree of 0 (no outgoing edges).

            Notes
            -----
            Terminal instances can occur due to several scenarios:
            - Complete deterioration of the ice island
            - Ice island size falling below the detection threshold
            - Ice island drifting out of the study area
            - End of the observation period

            The method identifies terminal instances by checking the out-degree of
            each vertex in the graph. A vertex with no outgoing edges (out-degree = 0)
            is considered terminal.

            Examples
            --------
            >>> handler = IgraphHandler(gdf)
            >>> g = handler.create_igraph()
            >>> terminal_instances = handler.terminal()
            >>> print(terminal_instances)  # Print all terminal instance IDs

            """
            terminal_vertices = [
                v.index
                for v in self.igraph.vs
                if len(self.igraph.neighbors(v, mode="out")) == 0
            ]
            terminal_names = [self.igraph.vs[v]["name"] for v in terminal_vertices]
            return terminal_names

        def drifts(
            self,
            calvingloc: str = None,
            calvingyr: int = None,
            wk_num: List[int] = None,
        ) -> Dict[str, Any]:
            """
            Isolate and return drift trajectories [branches] of ice islands before/after fractures.

            This method identifies all ice island instances that originated from fracture
            events and tracks their subsequent drift paths.

            Parameters
            ----------
            calvingloc : str
                Location identifier of the calving event (e.g., 'PII', 'PG')
            calvingyr : int
                Year of the calving event
            wk_num : (List[int])
                Week number range [start, end].

            Returns
            -------
            Dict[str, Any]: Dictionary with lists of branches and induced subgraphs.

            Raises
            ------
            ValueError
                If no matching calving event is found
                If parameters are out of valid ranges
            KeyError
                If required attributes are missing from the graph

            Notes
            -----
            The method performs the following steps:
            1. Identifies the initial instances from the specified calving event
            2. Traces all possible drift paths from these instances
            3. Groups the paths by their terminal instances
            4. Returns separate subgraphs for each complete drift trajectory

            Examples
            --------
            >>> handler = IgraphHandler(gdf)
            >>> g = handler.create_igraph()
            >>> drift_paths = handler.drifts('PII', 2012, 32)
            >>> for terminal_id, path in drift_paths.items():
            ...     print(f"Path to {terminal_id}: {path.vs['name']}")

            """

            def find_branches(
                combinations: pd.DataFrame, graph: ig.Graph
            ) -> Dict[str, List]:
                """
                Find branches between given combinations of nodes in the graph.

                Parameters
                ----------
                combinations (pd.DataFrame): DataFrame with pairs of nodes to analyze.
                graph (ig.Graph): The graph to analyze.

                Returns
                -------
                Dict[str, List]: Lists of branches and their corresponding subgraphs.

                """
                branches = []
                for from_node, to_node in combinations.values:
                    try:
                        paths = graph.get_shortest_paths(
                            from_node, to=to_node, output="vpath"
                        )[0]
                        if len(paths) > 1:
                            branches.append(paths)
                    except:
                        continue

                unique_starts = set(branch[0] for branch in branches)
                drift_paths = []
                drift_subgraphs = []
                for start in unique_starts:
                    relevant_branches = [b for b in branches if b[0] == start]
                    shortest_branch = min(relevant_branches, key=len)
                    drift_paths.append(shortest_branch)
                    drift_subgraphs.append(graph.induced_subgraph(shortest_branch))

                return {"drifts_list": drift_paths, "drifts_igraph": drift_subgraphs}

            gdf_filtered = self._filter_gdf(calvingloc, calvingyr, wk_num)
            # this line of code goes nowhere
            # graph = self.create_igraph_from_gdf(gdf_filtered)
            # Not sure what Mitch intended here but try this code:
            # Create igraph object from the gdf that is filtered.
            tmp_igraph_handler = IgraphHandler(gdf_filtered)
            # get a graph
            graph = tmp_igraph_handler.create_igraph()
            comb_pairs = self._get_combinations(gdf_filtered)

            return find_branches(comb_pairs, graph)

        def _filter_gdf(
            self,
            calvingloc: str = None,
            calvingyr: int = None,
            wk_num: List[int] = None,
        ) -> gpd.GeoDataFrame:
            """
            Filter the GeoDataFrame based on calving location, year, and week number.

            Parameters
            ----------
            calvingloc : str
                Calving location identifier
            calvingyr : int
                Year of the calving event
            wk_num : list of int
                Week number range [start, end]

            Returns
            -------
            gpd.GeoDataFrame
                Filtered GeoDataFrame containing only the rows that match the specified
                calving location, year, and fall within the given week number range

            Notes
            -----
            The filtering is inclusive of both start and end week numbers.

            """
            gdf_filtered = self.gdf.copy()

            if calvingloc:
                gdf_filtered = gdf_filtered[gdf_filtered["calvingloc"] == calvingloc]
            if calvingyr:
                gdf_filtered = gdf_filtered[gdf_filtered["calvingyr"] == calvingyr]
            if wk_num:
                gdf_filtered = gdf_filtered[
                    (gdf_filtered["wk_num"] >= wk_num[0])
                    & (gdf_filtered["wk_num"] <= wk_num[1])
                ]

            return gdf_filtered

        def _get_combinations(self, gdf: gpd.GeoDataFrame) -> pd.DataFrame:
            """
            Generate all combinations of origins and terminals for branch analysis.

            Parameters
            ----------
            gdf : gpd.GeoDataFrame
                Filtered GeoDataFrame containing ice island instances

            Returns
            -------
            pandas.DataFrame
                DataFrame containing all possible pairs (combinations) of instances,
                where each row represents a potential origin-terminal pair for
                branch analysis

            Notes
            -----
            The combinations are generated by pairing each unique instance with
            every other instance that could potentially be connected in a drift
            trajectory.

            """
            origins = gdf[(gdf["lineage"].isna()) | (gdf["lineage"].isin(gdf["inst"]))][
                "inst"
            ].tolist()
            terminals = gdf[~gdf["inst"].isin(gdf["lineage"])]["inst"].tolist()

            comb = pd.DataFrame(
                [(origin, terminal) for origin in origins for terminal in terminals]
            )
            return comb

    class GDFHandler:
        """
        Handles GeoDataFrame operations for ice island data.

        Parameters
        ----------
        filepath : str
            Path to the data file
        layer : str, optional
            Layer name for GeoPackage files

        Methods
        -------
        load_gdf(file_path, layer)
            Loads GeoDataFrame from file
        fractured(type, calvingyr, calvingloc, wk_num)
            Filters instances before and after fracturing
        terminal()
            Returns terminal instances
        """

        def __init__(self, filepath, layer=None):
            self.gdf = self.load_gdf(filepath, layer=layer)  # load_gdf file here

        def load_gdf(self, file_path, layer=None) -> gpd.GeoDataFrame:
            logger.info(f"Loading data from: {file_path}")

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                raise FileNotFoundError(f"File not found: {file_path}")

            if file_path.endswith(SHAPE_EXT):
                logger.info(f"Loading data from shapefile")
                gdf = gpd.read_file(file_path)

            elif file_path.endswith(GPKG_EXT):  # and layer is not None:
                logger.info(f"Loading data from GeoPackage")

                layers = gpd.io.file.fiona.listlayers(file_path)
                logger.info(f"Layers found in GeoPackage: {layers}")

                if len(layers) == 0:
                    logger.error("No layers found in GeoPackage")
                    raise ValueError("No layers found in GeoPackage")
                else:
                    if layer is None:
                        logger.info(
                            f"No layer specified, loading first layer: '{layers[0]}'"
                        )
                        gdf = gpd.read_file(file_path, layer=layers[0])
                    elif layer in layers:
                        logger.info(f"Loading requested layer: '{layer}'")
                        gdf = gpd.read_file(file_path, layer=layer)
                    else:
                        logger.error(f"Layer not found in GeoPackage: '{layer}'")
                        logger.info(f"Available layers: {layers}")
                        raise ValueError("Layer not found in GeoPackage")
            else:
                raise ValueError(
                    f"Unsupported file extension. Supported extensions are {SHAPE_EXT} and {GPKG_EXT}."
                )

            logger.info(f"Data loaded successfully with {len(gdf)} records.")
            return gdf

        def ensure_list(values: Union[Any, None, List[Any]]) -> List[Any]:
            if values is None:
                return []
            if isinstance(values, list):
                return values
            if isinstance(values, collections.abc.Collection) and not isinstance(
                values, (str, bytes)
            ):
                logger.error(
                    f"Input of type {type(values).__name__} is not supported. Expected a single value or a list."
                )
                raise ValueError(
                    f"Input of type {type(values).__name__} is not supported. Expected a single value or a list."
                )

            # For single non-collection values like int, float, etc.
            return [values]

        def compute_week_number(df, date_col, partition_col):
            """
            Computes the week number rank within partitions defined by partition_col.

            :param df: DataFrame to compute the week number rank
            :param date_col: Column name containing the dates to be used for ranking
            :param partition_col: Column name to partition the ranking by
            :return: DataFrame with the added 'wk_num' column
            """
            df["wk_num"] = (
                df.groupby(partition_col)[date_col]
                .rank(method="dense", ascending=True)
                .astype(int)
            )
            return df

        def filter_by_column(self, gdf, column: str, values: List[Any]):
            values = self.ensure_list(values)
            if values:
                return gdf[gdf[column].isin(values)]
            return gdf

        def generate_conditions(self, query_type):
            if query_type == ALL:
                condition = self.gdf["lineage"].str.contains(
                    r"\d{8}_\d{6}_SN_#"
                ) & ~self.gdf["lineage"].str.contains(r"P|S[0-9]{1,2}")
            elif query_type == BEFORE:
                condition = (
                    self.gdf.groupby("lineage")["lineage"].transform("count") > 1
                )
            elif query_type == AFTER:
                condition = self.gdf["lineage"].str.contains(
                    r"\d{8}_\d{6}_SN_#"
                ) & ~self.gdf["lineage"].str.contains(r"P|S[0-9]{1,2}")
            else:
                raise ValueError("Invalid query_type. Choose from ALL, BEFORE, AFTER.")

            return condition

        def filter_by_week_numbers(self, wk_num):
            if wk_num is not None:
                return self.gdf[
                    (self.gdf[WK_NUM] >= wk_num[0]) & (self.gdf[WK_NUM] <= wk_num[1])
                ]
            return self.gdf

        def fractured(
            self,
            type: str = ALL,
            calvingyr: int = None,
            calvingloc: str = None,
            wk_num=None,
        ):

            # Apply filters for calving year and location
            filtered_gdf = self.filter_by_column(self.gdf, CALVINGYR, calvingyr)
            filtered_gdf = self.filter_by_column(filtered_gdf, CALVINGLOC, calvingloc)

            lineage_filter = (
                ~filtered_gdf[LINEAGE].str.match(
                    LINEAGE_EXACT_FORMAT_FILTER, escape="!"
                )
            ) & (~filtered_gdf[LINEAGE].str.match(LINEAGE_PATTERN_FILTER))

            if type == ALL:
                # Group by 'lineage' and filter groups with more than one instance
                grouped = filtered_gdf.groupby(LINEAGE).filter(lambda x: len(x) > 1)

                # Apply the 'lineage' filter and retain only the matching groups
                filtered_gdf = grouped[lineage_filter]

                # Calculate the dense rank based on 'calvingyr' and week number derived from 'scenedate'
                filtered_gdf[SCENEDATE] = pd.to_datetime(filtered_gdf[SCENEDATE])
                filtered_gdf[WK_NUM] = (
                    filtered_gdf.groupby(CALVINGYR)[SCENEDATE]
                    .rank(method="dense")
                    .astype(int)
                )

            elif type == BEFORE:
                # Group by 'lineage' and filter groups with more than one instance
                grouped = filtered_gdf.groupby(LINEAGE).filter(lambda x: len(x) > 1)

                # Calculate the dense rank based on 'calvingyr' and week number derived from 'scenedate'
                grouped[SCENEDATE] = pd.to_datetime(grouped[SCENEDATE])
                grouped[WK_NUM] = (
                    grouped.groupby(CALVINGYR)[SCENEDATE]
                    .rank(method="dense")
                    .astype(int)
                )

                filtered_gdf = grouped

            elif type == AFTER:

                # Group by 'lineage' and filter groups with more than one instance
                grouped = filtered_gdf.groupby(LINEAGE).filter(lambda x: len(x) > 1)

                # Apply the 'lineage' filter and retain only the matching groups
                filtered_gdf = grouped[lineage_filter]

                # Calculate the dense rank based on 'calvingyr' and week number derived from 'scenedate'
                filtered_gdf[SCENEDATE] = pd.to_datetime(filtered_gdf[SCENEDATE])
                filtered_gdf[WK_NUM] = (
                    filtered_gdf.groupby(CALVINGYR)[SCENEDATE]
                    .rank(method="dense")
                    .astype(int)
                )

                # Filter by instances after fracturing based on the lineage and group by lineage
                filtered_gdf = filtered_gdf[
                    filtered_gdf[LINEAGE].isin(grouped[LINEAGE])
                ]

            # Filter by week number range if provided
            if wk_num is not None:
                filtered_gdf = filtered_gdf[
                    (filtered_gdf[WK_NUM] >= wk_num[0])
                    & (filtered_gdf[WK_NUM] <= wk_num[1])
                ]

            return filtered_gdf

        # def f_fract_db(self, query_type=ALL, calvingyr=None, calvingloc=None, wk_num=None):
        #     # Apply filters for calving year and location
        #     filtered_gdf = self.filter_by_column(self.gdf, CALVINGYR, calvingyr)
        #     filtered_gdf = self.filter_by_column(filtered_gdf, CALVINGLOC, calvingloc)

        #     # Generate and apply specific conditions based on query type
        #     condition = self.generate_conditions(filtered_gdf, query_type)
        #     filtered_gdf = filtered_gdf[condition]

        #     # Compute the week number rank within partitions
        #     filtered_gdf = self.compute_week_number(filtered_gdf, date_col=SCENEDATE, partition_col=CALVINGYR)

        #     # Filter by week numbers if provided
        #     filtered_gdf = self.filter_by_week_numbers(filtered_gdf, wk_num)

        #     return filtered_gdf

        # def f_fract_db(self, query_type=ALL, calvingyr=None, calvingloc=None, wk_num=None):
        #     """
        #     Filters the GeoDataFrame for ice island instances just before and just after fracturing.

        #     :param gdf: Input GeoDataFrame
        #     :param query_type: Type of filter ('all', 'before', 'after')
        #     :param calvingyr: Single value or list of calving years
        #     :param calvingloc: Single value or list of calving locations
        #     :param wk_num: List of two integers specifying the earliest and latest desired week numbers since calving
        #     :return: Filtered GeoDataFrame
        #     """
        #     # Apply filters for calving year and location
        #     filtered_gdf = self.filter_by_column(self.gdf, 'calvingyr', calvingyr)
        #     filtered_gdf = self.filter_by_column(filtered_gdf, 'calvingloc', calvingloc)

        #     # Compute the week number rank within partitions
        #     filtered_gdf = self.compute_week_number(filtered_gdf, date_col='scenedate', partition_col='calvingyr')

        #     # Apply specific conditions based on query type
        #     if query_type == "all":
        #         condition = (
        #             filtered_gdf['lineage'].str.contains(r'\d{8}_\d{6}_SN_#') &
        #             ~filtered_gdf['lineage'].str.contains(r'(P|S)[0-9]')
        #         ) | (
        #             filtered_gdf.groupby('lineage')['lineage'].transform('count') > 1
        #         )
        #     elif query_type == "before":
        #         condition = (
        #             filtered_gdf.groupby('lineage')['lineage'].transform('count') > 1
        #         )
        #     elif query_type == "after":
        #         condition = (
        #             filtered_gdf['lineage'].str.contains(r'\d{8}_\d{6}_SN_#') &
        #             ~filtered_gdf['lineage'].str.contains(r'(P|S)[0-9]')
        #         )
        #     else:
        #         raise ValueError("Invalid query_type. Choose from 'all', 'before', 'after'.")

        #     # Apply the condition to filter the DataFrame
        #     filtered_gdf = filtered_gdf[condition]

        #     # Filter by week numbers if provided
        #     filtered_gdf = filter_by_week_numbers(filtered_gdf, wk_num)

        #     return filtered_gdf

        def terminal(self) -> gpd.GeoDataFrame:
            terminal_df = self.gdf[~self.gdf[INST].isin(self.gdf[LINEAGE])]
            return terminal_df

        # def sub_query(self, calvingyr : int = None, calvingloc : str = None) -> gpd.GeoDataFrame:
        #     '''
        #     # Specific subquery for year and location, if needed
        #     Usage:
        #         yr_condition, loc_condition = f_subquery(calvingyr, calvingloc)
        #         filtered_gdf = gdf[yr_condition(gdf) & loc_condition(gdf)]
        #     '''
        #    # Prepare calvingyr query condition
        #     if calvingyr is None:
        #         yr_condition = lambda df: pd.Series([True] * len(df))
        #     else:
        #         yr_condition = lambda df: df[CALVINGYR].isin(calvingyr)

        #     # Prepare calvingloc query condition
        #     if calvingloc is None:
        #         loc_condition = lambda df: pd.Series([True] * len(df))
        #     else:
        #         loc_condition = lambda df: df[CALVINGLOC].isin(calvingloc)

        #     return yr_condition, loc_condition


class CalvingPlotter:
    """
    Handles visualization of calving events.

    Methods
    -------
    plot_calving_events(data)
        Plots calving events over time

    Parameters
    ----------
    data : pandas.DataFrame
        DataFrame containing calving event data with columns:
        - date: datetime
        - area: float
        - glacier: str

    """

    def __init__(self):
        pass

    def plot_calving_events(self, data):
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=data, x="date", y="area", hue="glacier")
        plt.title("Calving Events Over Time")
        plt.xlabel("Date")
        plt.ylabel("Iceberg Area (km^2)")
        plt.legend(title="Glacier")
        plt.show()


# Utility Functions


def calculate_polygon_length(gdf):
    """
    Calculate the maximum distance between any two vertices of polygons.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        GeoDataFrame containing polygon geometries

    Returns
    -------
    gpd.GeoDataFrame
        Input GeoDataFrame with additional 'length' column

    Notes
    -----
    The length is calculated as the maximum Euclidean distance
    between any two vertices of each polygon.

    """

    # Calculate the longest distance between any two vertices of the polygon
    def max_distance(polygon):
        vertices = list(polygon.exterior.coords)
        max_dist = 0
        for i in range(len(vertices)):
            for j in range(i + 1, len(vertices)):
                dist = gpd.GeoSeries(
                    [gpd.points_from_xy([vertices[i][0]], [vertices[i][1]])]
                ).distance(gpd.points_from_xy([vertices[j][0]], [vertices[j][1]]))[0]
                if dist > max_dist:
                    max_dist = dist
        return max_dist

    gdf["length"] = gdf.geometry.apply(max_distance)
    return gdf


# Example usage:
# filepath = "path/to/geopackage_or_shapefile.gpkg"
# helper = CI2D3Helper(filepath)
# df = helper.create_dataframe(calvingyr=[2010])
# G = helper.create_igraph(df)
# naming_system_df = helper.create_naming_system(df)
# subset_df = helper.subset_fortnightly(start_date='2010-01-01', end_date='2010-12-31')
# refined_gdf = calculate_polygon_length(helper.gdf)

# analyzer = BranchAnalyzer()
# branches = analyzer.find_branches(G)
# big_branches = analyzer.find_big_branches(G)
# mothers = analyzer.find_mothers(G)
# cleaned_graph = analyzer.remove_drift_only(G)

# plotter = CalvingPlotter()
# plotter.plot_calving_events(df)

helper = CI2D3Handler(
    "/home/dmueller/OneDrive/Research/ci2d3/ci2d3_database_v1.1a/ci2d3_1.1a.shp"
)
# helper = CI2D3Handler("path/to/geopackage_or_shapefile.gpkg")

after = helper.igraph.after(1)
after.vcount()

# Isolate PG-2010 -I think Mitch has a more elegant way of doing this...
pg2010 = CI2D3Handler.IgraphHandler(
    helper.gdf.gdf.loc[
        (helper.gdf.gdf.calvingyr == "2010") & (helper.gdf.gdf.calvingloc == "PG")
    ]
)
pg2010.igraph.vcount()

# This is much smaller so try this too...
pg2008 = CI2D3Handler.IgraphHandler(
    helper.gdf.gdf.loc[
        (helper.gdf.gdf.calvingyr == "2008") & (helper.gdf.gdf.calvingloc == "PG")
    ]
)
pg2008.igraph.vcount()

# graphing:

# TODO Document properly and put into the environment.yml
# need to install pycairo into the conda env.
# conda install pycairo
# cairo also needs to be on your computer (OS).  Google for windows, for Linux:
# sudo apt install libcairo2-dev pkg-config python3-dev

# in spyder under preferences/ipython console/ graphics, I selected inline (graphs in plot tab)
# the following worked:
fig, ax = plt.subplots()
ig.plot(pg2008.igraph, target=ax)


# note that this works - but takes a lot of time.
fig, ax = plt.subplots()
ig.plot(pg2010.igraph, target=ax)

# NOTE The plots are igraph plots not geographical in any way (as far as I know).

# The geodataframe IS geographical but lacks the igraph edges.
pg2010.gdf.plot()

# There is obviously a way to get the best of both worlds... No time right now to look into this.
