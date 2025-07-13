import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

connection = sqlite3.connect("dataset/Hydat.sqlite3")

samples = pd.read_sql_query(
    "SELECT DATE, TEMPERATURE FROM SED_SAMPLES WHERE TEMPERATURE IS NOT NULL ORDER BY DATE",
    connection
)
samples["DATE"] = pd.to_datetime(samples["DATE"])
samples = samples.set_index("DATE")

samples = samples[samples.index >= "1965-01-01"] # ignore erroneuous data
yearly_means = samples.resample("YE").mean().reset_index()

plt.plot(yearly_means["DATE"], yearly_means["TEMPERATURE"], color="red")

plt.title("Water temperatures")
plt.xlabel("Year")
plt.ylabel("Water temperature")
plt.grid(True)
plt.show()
