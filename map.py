import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

# TODO: functions to automatically download and extract these

# download from: https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_1_states_provinces.zip
shapefile_path = "/home/aabiji/Downloads/provinces/ne_10m_admin_1_states_provinces.shp"

# download from: https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_0_countries.zip
country_shapefile_path = "/home/aabiji/Downloads/countries/ne_10m_admin_0_countries.shp"

connection = sqlite3.connect("dataset/Hydat.sqlite3")
stations = pd.read_sql_query("SELECT * from STATIONS", connection)

fig = plt.figure(figsize=(15, 15))
ax = plt.axes(projection=ccrs.PlateCarree())

# zoom in on Canada [lon_min, lon_max, lat_min, lat_max]
ax.set_extent([-141, -52, 41, 84], crs=ccrs.PlateCarree())

# plot the provinces
reader = shpreader.Reader(shapefile_path)
provinces = [r.geometry for r in reader.records() if r.attributes["admin"] == "Canada"]
for geometry in provinces:
    ax.add_geometries([geometry], ccrs.PlateCarree(), edgecolor="gray",
                      facecolor="none", linewidth=1)

countries = shpreader.Reader(country_shapefile_path)
country = [r.geometry for r in countries.records() if r.attributes["ADMIN"] == "Canada"]

# plot the border
for geometry in country:
    ax.add_geometries([geometry], ccrs.PlateCarree(), edgecolor="grey",
                      facecolor="none", linewidth=1.5)

# plot the stations
for station in stations.itertuples():
    ax.scatter(station.LONGITUDE, station.LATITUDE, color="dodgerblue",
               s=10, alpha=0.7, edgecolors="none", transform=ccrs.PlateCarree())

ax.set_title("Gauging stations across Canada", fontsize=16, pad=30)
ax.set_axis_off()
ax.set_aspect(1.5) # stretch vertically
plt.show()
