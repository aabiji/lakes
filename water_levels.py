import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

connection = sqlite3.connect("dataset/Hydat.sqlite3")

# TODO: look at water flow, temperature, daily mean tonnes
def z_score_normalize(group):
    return (group - group.mean()) / group.std()

# get the most frequently used datums
conversions = pd.read_sql_query("SELECT * from STN_DATUM_CONVERSION", connection)
datum_usage_counts = conversions.groupby("DATUM_ID_TO")["STATION_NUMBER"].count()
most_used_datums = datum_usage_counts.sort_values(ascending=False).index.tolist()

stations = pd.read_sql_query("SELECT * from STATIONS", connection)

annual_statistics = pd.read_sql_query("SELECT * from ANNUAL_STATISTICS", connection)
print(annual_statistics)
all_water_levels = annual_statistics[annual_statistics["DATA_TYPE"] == "H"] # T = daily mean tonnes, Q = flow

all_stations = all_water_levels["STATION_NUMBER"].unique()
datums_used = stations[stations["STATION_NUMBER"].isin(all_stations)]["DATUM_ID"].unique()

# only consider water sources that haven't been regulated
# NOTE: try toggling this on/off because there is a difference
regulation_data = pd.read_sql_query("SELECT * FROM STN_REGULATION", connection)
regulated_stations = regulation_data.loc[regulation_data["REGULATED"] == 1, "STATION_NUMBER"]
unregulated_stations = set(all_stations) - set(regulated_stations)
all_water_levels = all_water_levels[all_water_levels["STATION_NUMBER"].isin(unregulated_stations)]

column = "MEAN"
yearly_station_data = []

for target_datum in most_used_datums:
    # only select water level data that uses a common datum or can be converted to the common datum
    stations_already_with_datum = stations[stations["DATUM_ID"] == target_datum]["STATION_NUMBER"].copy()
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
    water_levels_with_conversion_factor[column] += water_levels_with_conversion_factor["CONVERSION_FACTOR"]

    # remove the conversion factor column since we don't need it anymore
    water_levels_with_conversion_factor.drop(columns="CONVERSION_FACTOR", inplace=True)

    # now all the water level data are using the same datum
    water_levels = pd.concat([water_levels_using_datum, water_levels_with_conversion_factor], ignore_index=True)

    # remove rows where the min, max and mean are nan
    water_levels = water_levels.dropna(subset=[column], how="all")

    # replace nans with the last valid value
    # min-max normalize so that each graph has the same scale, regardless of datum
    water_levels[column] = water_levels.groupby("STATION_NUMBER")[column].transform(lambda x: x.ffill())
    water_levels[column] = water_levels.groupby("STATION_NUMBER")[column].transform(z_score_normalize)

    # group duplicate years from different stations together, and average the means
    mean_water_levels_by_year = water_levels.groupby("YEAR")[column].mean().reset_index()
    yearly_station_data.append(mean_water_levels_by_year)

# fainty show each plot
for plot in yearly_station_data:
    plt.plot(plot["YEAR"], plot["MEAN"], color="grey", linewidth=1, alpha=0.2)

# concatenate all normalized station-year means across all datums
combined = pd.concat(yearly_station_data, ignore_index=True)

# compute and plot overall trend line (average of all stations by year)
overall_trend = combined.groupby("YEAR")[column].mean()
plt.plot(overall_trend.index, overall_trend.values, color="blue", linewidth=3)

# draw the middle line (z-score always has a normalized mean of zero)
plt.axhline(0, color="black", linestyle="--", linewidth=1)

column_str = column[0] + column[1:].lower()
plt.title(f"Normalized {column_str} Annual Water Levels (All Datums)")
plt.xlabel("Year")
plt.ylabel(f"Z-Score Normalized {column_str} Water Level")
plt.grid(True)
plt.tight_layout()
plt.show()
