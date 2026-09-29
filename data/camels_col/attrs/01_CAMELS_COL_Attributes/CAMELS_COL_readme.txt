Readme file created by David Antonio Jimenez Osorio, 2025 (dajimenezoo30@gmail.com).
______________________________________________________________________________________________________________________________________________________

1) Description

This is the CAMELS-COL dataset (Catchment Attributes and MEteorology for Large-sample Studies - Colombia) presented in the paper by Jimenez et al., CAMELS-COL: A Large-Sample Hydrometeorological Dataset for Colombia.

This dataset provides daily observed streamflow time series for 921 stream gauges, daily meteorological time series and 71 attributes for 46 selected catchments in Colombia.

The available hydrometeorological time series include:
(i) observed precipitation with quality control metadata,
(ii) observed streamflow with quality control metadata,
(iii) potential evapotranspiration, and
(iiii) minimum, average, and maximum temperature.

The 71 catchment attributes encompass:
(i) topography,
(ii) climate,
(iii) hydrology,
(iv) land cover,
(v) geology,
(vi) soil, and
(vii) human intervention.

This dataset follows the same standards as other CAMELS datasets, including those for the United States (https://doi.org/10.5194/hess-21-5293-2017), Chile (https://doi.org/10.5194/hess-22-5817-2018), Great Britain (https://doi.org/10.5194/essd-2020-49) and Brazil (https://doi.org/10.5194/essd-12-2075-2020).
______________________________________________________________________________________________________________________________________________________

2) Contents

# 01_CAMELS_COL_Attributes.xlsx

Describes each one of the 71 attributes available in this dataset.

# 02_CAMELS_COL_Catchment_information.xlsx

Presents the gauging stations general characteristics:

The columns are "gauge_id" for the identification of each station, "gauge_department" for the department station is located, "gauge_lat" for latitude, "gauge_lon" for longitude and "gauge_elev" for elevation in meters above sea level.

# 03_CAMELS_COL_Basin_boundary.zip

This directory contains 192 files with ESRI shapefile of the catchment boundaries used in CAMELS-COL.

# 04_CAMELS_COL_Hydrometeorological_data.zip

This directory contains 192 files with the hydrometeorological data collected for each one of the catchments presented in CAMELS-COL, identified in the file name by the "gauge_id" presented in 02_CAMELS_COL_Catchment_information. 

The columns are "pr" for the precipitation in milimeters (mm), "poten_evapo" for the daily potential evaporation in the catchment in milimeters per day (mm/day), "t_max" for the daily maximum temperature in Celsius (°C), "t_min" for the daily mininum temperature in Celsius (°C), "t_mean" for the daily average temperature in Celsius (°C) and "streamflow" for the daily streamflow in cubic meters per second (m³/s).

# 05_CAMELS_COL_Geologic_characteristics.csv

Presents the classification of all the rocks presented in CAMELS-COL, a brief description of each one and the percentage of catchment area covered by the diferentes geological litologies. 

The columns are "Classification", "Description" and "Catchment_########" (for each "gauge_id" i.g. "Catchment_13037010")

# 06_CAMELS_COL_Land_cover_characteristics.csv

Presents the different catchment land cover typologies considered in CAMELS-COL and the percentage of catchment area covered by each typology. 

The columns are "Land_cover" which presents the typologies and "Catchment_########" (for each "gauge_id" i.g. "Catchment_13037010").

# 07_CAMELS_COL_Soil_characteristics.csv

Presents the percentage in each catchment of different soil types based on their properties and development considered in CAMELS-COL.

The columns are "Attribute_name" which presents the soil types and "Catchment_########" (for each "gauge_id" i.g. "Catchment_13037010").

# 08_CAMELS_COL_Climatic_indices.csv

Presents the climatic indices calculated for each catchment avaliable in CAMELS-COL.

The columns are "gauge_id" for the identification of each station and the climatic indices: "aridity", "high_prec_freq", "high_prec_dur", "low_prec_freq" and "low_prec_dur".

# 09_CAMELS_COL_Hydrological_signatures.csv

Presents the hydrological signatures calculated for each catchment avaliable in CAMELS-COL.

The columns are "gauge_id" for the identification of each station and the signatures: "q_mean" in milimeters per day (mm/day), "runoff_ratio", "stream_elas", "slope_fdc", "baseflow_index", "Q5" in milimeters per day (mm/day), "Q95" in milimeters per day (mm/day), "high_q_freq" days per year (days/yr), "high_q_dur" in days, "low_q_freq" in days per year (days/yr) and "low_q_dur" in days.

# 10_CAMELS_COL_Physiograpic_characteristics.csv

Presents the physiographic characteristics calculated for each catchment avaliable in CAMELS-COL.

The columns are "gauge_id" for the identification of each station and the physiographic characteristics: "area" in square kilimeters (km²), "perimeter" in kilometers (km), "gravelius_index", "factor_form", "streng_chanel" in kilometers (km), "equi_slope" in meters per meters (m/m), "cn_catchment", "tc_kirpich" in hours, "tc_chow" in hours, "tc_Johnstone" in hours and "tc_Engi_Corps" in hours.

# 11_CAMELS_COL_Land_use_capability.csv

Presents the land use capability calculated for each catchment avaliable in CAMELS-COL.

The columns are "gauge_id" for the identification of each station and the land cover: "class_1", "class_2", "class_3", "class_4", "class_5", "class_6", "class_7", "class_8", "Urban_area" and "No_classified", based on the classification provided by the Agustín Codazzi Geographic Institute (IGAC, 2014).

# 12_CAMELS_COL_Drainage_network.zip

Presents the drainage network as shapefile for every catchment avaliable in CAMELS-COL.

# 13_CAMELS_COL_Topographic_wetness_index.zip

Presents the Topographic Wetness Index (TWI), in raster format, calculated for each catchment avaliable in CAMELS-COL.

# 14_CAMELS_COL_Figures.zip

Presents the figures avaliable in CAMELS-COL as auxiliary material.

