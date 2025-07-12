import bs4, glob, os, re, requests, sqlite3, zipfile
import matplotlib.pyplot as plt
import pandas as pd

# Database reference: https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/HYDAT_Definition_EN.pdf
connection = sqlite3.connect("dataset/Hydat.sqlite3")

class Station:
    def __init__(self, number):
        data = pd.read_sql_query(f"SELECT STATION_NAME, LATITUDE, LONGITUDE FROM STATIONS WHERE STATION_NUMBER='{number}'", connection)
        self.name = data["STATION_NAME"][0]
        self.latitude = data["LATITUDE"][0]
        self.longitude = data["LONGITUDE"][0]
        self.number = number
"""
Data symbols:

  SYMBOL_ID                     SYMBOL_EN                         SYMBOL_FR
0         A                   Partial Day                Journée incomplète
1         B                Ice Conditions                Conditions à glace
2         D                           Dry                               Sec
3         E                     Estimated                            Estimé
4         S  Sample(s) collected this day  échantillons prélevés ce jour-là
"""

"""
Data types:

  DATA_TYPE               DATA_TYPE_EN           DATA_TYPE_FR
0         H                Water Level          Niveaux d'eau
1         I  Instantantaneous Sediment  Sédiments Instantanés
2         Q                       Flow                  Débit
3         S           Sediment in mg/L        Sédiment (mg/L)
4         T          Daily Mean Tonnes                   None
"""

"""
Sediment data types:

  SED_DATA_TYPE   SED_DATA_TYPE_EN                                   SED_DATA_TYPE_FR
0            BL           Bed Load                                     Charge de fond
1            BM       Bed Material                                   Matériaux du lit
2            DI  Depth Integration                              Intégration verticale
3            PI  Point Integration                             Intégration ponctuelle
4            SV     Split Vertical  Intégration fractionnée en tous points de la v...
"""

"""
All about Datums:

https://wateroffice.ec.gc.ca/report/datum_faq_e.html

Can we assume everything's in meters, then to convert between the
different datums, we just add?

Hmm...this is more complex than I thought. Each station conversion factors
are local (for example a 1m offset in one place might need to be a 1.5m offset
in another place because of terrain), and each station is mapping from one
datum to another. There's no "central" datum every station's mapping to.
Which makes things complicated since now we'd have to analyze each data seperately....

datums 605, 35, 415, 110 seem to be the most popular (in that order)
Ok, if we analyze on a per datum basis, maybe we can superpose the graph multiple datums
on one big graph to see if they show the same trend.

For example:
                                           DATUM_EN
0              ALBERTA DEPARTMENT OF HIGHWAYS DATUM
1                                       ALCAN DATUM
2       APPROXIMATE GEODETIC SURVEY OF CANADA DATUM
3                                        ARBITRAIRE
4                                     ASSUMED DATUM
..                                              ...
140                       TRANSALTA UTILITIES DATUM
141  UNITED STATES AND CANADA BOUNDARY SURVEY DATUM
142   UNITED STATES COAST AND GEODETIC SURVEY DATUM
143         UNITED STATES RECLAMATION SERVICE DATUM
144                        WATER POWER SURVEY DATUM

     STATION_NUMBER  DATUM_ID_FROM  DATUM_ID_TO  CONVERSION_FACTOR
0           01AD009            405          415         168.270996
1           01AD014            405          415         162.388000
2           01AF003             10           35         141.917999
3           01AG002             10           35         104.588997
4           01AG003             10           35          75.311996
...             ...            ...          ...                ...
2034        11AC062             10           35         794.437988
2035        11AC063             35           90          -0.064000
2036        11AC065             35           90          -0.014000
2037        11AC066             10           35         824.281006
2038        11AC068             10           35         808.161011
"""

# so, we're getting the average water levels from all the different stations per year

# TODO: take a look at the minimum and maximums too, maybe they look different
# TODO: what if we look at regulated and unregulated sources?
# TODO: wait, our data looks wonky because each station uses a different datum,
#       we need to convert all the stations to use the same datum (measurement reference point)
# TODO: look at these other factors: precipitation, temperature, evaporation

# get the most frequently used datums
conversions = pd.read_sql_query("SELECT * from STN_DATUM_CONVERSION", connection)
datum_usage_counts = conversions.groupby("DATUM_ID_TO")["STATION_NUMBER"].count()
most_used_datums = datum_usage_counts.sort_values(ascending=False).index[:3].tolist()

stations = pd.read_sql_query("SELECT * from STATIONS", connection)

annual_statistics = pd.read_sql_query("SELECT * from ANNUAL_STATISTICS", connection)
all_water_levels = annual_statistics[annual_statistics["DATA_TYPE"] == "H"]

all_stations = all_water_levels["STATION_NUMBER"].unique()
datums_used = stations[stations["STATION_NUMBER"].isin(all_stations)]["DATUM_ID"].unique()

#query = f"SELECT DATUM_EN from DATUM_LIST WHERE DATUM_ID='{target_datum}'"
#target_datum_name = pd.read_sql_query(query, connection)["DATUM_EN"].values[0]

# Ok, so the plot's technically correct...but it's really messy
# what if we the top 5 most used datums or something?
# or maybe we can fit a regression line???

for target_datum in most_used_datums:
    # only consider water sources that haven't been regulated
    regulation_data = pd.read_sql_query("SELECT * FROM STN_REGULATION", connection)
    regulated_stations = regulation_data.loc[regulation_data["REGULATED"] == 1, "STATION_NUMBER"]
    unregulated_stations = set(all_stations) - set(regulated_stations)
    all_water_levels = all_water_levels[all_water_levels["STATION_NUMBER"].isin(unregulated_stations)]

    # only select water level data that uses a common datum or can be converted to the common datum
    stations_already_with_datum = stations[stations["DATUM_ID"] == target_datum]["STATION_NUMBER"]
    water_levels_using_datum = all_water_levels[all_water_levels["STATION_NUMBER"].isin(stations_already_with_datum)]

    conversions = pd.read_sql_query("SELECT * from STN_DATUM_CONVERSION", connection)
    convertible_stations = conversions[conversions["DATUM_ID_TO"] == target_datum]

    # add the conversion factor column to corresponding station numbers
    water_levels_with_conversion_factor = pd.merge(
        all_water_levels,
        convertible_stations[["STATION_NUMBER", "CONVERSION_FACTOR"]],
        on="STATION_NUMBER",
        how="inner"
    )

    # apply the conversion factors to station data that can we converted to the target datum
    #water_levels_with_conversion_factor["MEAN"] += water_levels_with_conversion_factor["CONVERSION_FACTOR"]
    #water_levels_with_conversion_factor["MIN"] += water_levels_with_conversion_factor["CONVERSION_FACTOR"]
    water_levels_with_conversion_factor["MAX"] += water_levels_with_conversion_factor["CONVERSION_FACTOR"]

    # remove the conversion factor column since we don't need it anymore
    water_levels_with_conversion_factor.drop(columns="CONVERSION_FACTOR", inplace=True)

    # now all the water level data are using the same datum
    water_levels = pd.concat([water_levels_using_datum, water_levels_with_conversion_factor], ignore_index=True)

    #water_levels = water_levels.dropna(subset=["MEAN"])
    #water_levels["MEAN"] = water_levels["MEAN"].ffill()
    #water_levels["MIN"] = water_levels["MIN"].ffill()
    water_levels["MAX"] = water_levels["MAX"].ffill()
    water_levels = water_levels.sort_values(by=["YEAR"])

    # group duplicate years from different stations together, and average the means
    #mean_water_levels_by_year = water_levels.groupby("YEAR")["MEAN"].mean()
    #mean_water_levels_by_year = water_levels.groupby("YEAR")["MIN"].mean()
    mean_water_levels_by_year = water_levels.groupby("YEAR")["MAX"].mean()

    plt.plot(mean_water_levels_by_year.index, mean_water_levels_by_year.values)

plt.title(f"Mean annual water levels of the bodies of water in Canada", wrap=True)
plt.xlabel("Year")
plt.ylabel("Mean water level")
plt.grid(True)
plt.tight_layout()
plt.show()
