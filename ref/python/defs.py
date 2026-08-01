# This file contains constants for the CI2D3 database.

# constants -----
prj_ll = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs +towgs84=0,0,0"
prj_lcc = "+proj=lcc +lat_1=77 +lat_2=49 +lat_0=40 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"


# File extensions -----
SHAPE_EXT = '.shp'
GPKG_EXT = '.gpkg'

# Column names -----
INST = 'inst'
LINEAGE = 'lineage'
CALVINGYR = 'calvingyr'
CALVINGLOC = 'calvingloc'
AREA = 'area'
PERIMETER = 'perimeter'
LENGTH = 'length'
LON = 'lon'
LAT = 'lat'
GEOMETRY = 'geometry'
SCENEDATE = 'scenedate'
IMGREF = 'imgref'
MOTHERCERT = 'mothercert'
SHPCERT = 'shpcert'
GEOREF = 'georef'
DDINFO = 'ddinfo'
SENSOR = 'sensor'
BEAM_MODE = 'beam_mode'
POL = 'pol'

# Other constants -----
WK_NUM = 'wk_num'


# Query constants -----
ALL = 'all'
BEFORE = 'before'
AFTER = 'after'

LINEAGE_EXACT_FORMAT_FILTER = r'^\d{8}!\d{6}!_\w{2}#_\d{4}$'
LINEAGE_PATTERN_FILTER = r'.*(P|S)(0|1|2)(0|1|2|3|4|5|6|7|8|9).*'

calving_locations = {"PG", "CG", "NG", "RG", "SG"}
calving_year = [2008, 2010, 2011, 2012, "NA"]