import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

# TODO: functions to automatically download and extract these
# TODO: vertically stretch the map out a bit

# download from: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/
shapefile_path = "/home/aabiji/Downloads/provinces/ne_10m_admin_1_states_provinces.shp"

# download from: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/
country_shapefile_path = "/home/aabiji/Downloads/countries/ne_10m_admin_0_countries.shp"

connection = sqlite3.connect("dataset/Hydat.sqlite3")
stations = pd.read_sql_query("SELECT * from STATIONS", connection)

fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection=ccrs.PlateCarree())

# zoom in on Canada [lon_min, lon_max, lat_min, lat_max]
ax.set_extent([-141, -52, 41, 84], crs=ccrs.PlateCarree())

reader = shpreader.Reader(shapefile_path)

# plot the provinces
canada_provinces = [record.geometry for record in reader.records() if record.attributes["admin"] == "Canada"]
for geometry in canada_provinces:
    ax.add_geometries([geometry], ccrs.PlateCarree(), edgecolor='gray', facecolor='none', linewidth=1)

reader_countries = shpreader.Reader(country_shapefile_path)
canada_country = [record.geometry for record in reader_countries.records() if record.attributes["ADMIN"] == "Canada"]

# plot the border
for geometry in canada_country:
    ax.add_geometries([geometry], ccrs.PlateCarree(), edgecolor='black', facecolor='none', linewidth=1.5)

# plot the stations
for station in stations.itertuples():
    ax.scatter(station.LONGITUDE, station.LATITUDE, color="blue", transform=ccrs.PlateCarree())

plt.title("Gauging stations across Canada", fontsize=14)
ax.set_axis_off()
plt.tight_layout()
plt.show()
