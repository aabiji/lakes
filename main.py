import bs4, glob, os, re, requests, sqlite3, zipfile
import matplotlib.pyplot as plt
import pandas as pd

def get_dataset():
    base_url = "https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/"
    soup = bs4.BeautifulSoup(requests.get(base_url).text, "html.parser")

    # anything that contains _sqlite3_ and ends in .zip
    pattern = re.compile(r".*_sqlite3_.*\.zip")

    links = [l for l in soup.find_all("a") if pattern.match(l.get_text())]
    filename = links[0]["href"]

    response = requests.get(f"{base_url}{filename}")
    with open("dataset.zip", "wb") as output:
        output.write(response.content)

    with zipfile.ZipFile("dataset.zip", 'r') as zip_ref:
        zip_ref.extractall("dataset")

    files = glob.glob('./dataset/*.sqlite3', recursive=True)
    os.remove("dataset.zip")
    return files[0]

def debug_database(connection):
    tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", connection)
    table_names = tables["name"].tolist()

    for table in table_names:
        df = pd.read_sql_query(f"PRAGMA table_info({table});", connection)
        column_names = df["name"].tolist()

        print(table)
        print("=" * len(table))
        print(column_names, "\n")

# Database reference: https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/HYDAT_Definition_EN.pdf
#print("Downloading dataset...")
#path = get_dataset()
#print(path)

path = "dataset/Hydat.sqlite3"
connection = sqlite3.connect(path)
#debug_database(connection)

"""
things to look out for:
- water level
- precipitation
- temperature
- evaporation

ANNUAL_STATISTICS
ANNUAL_INSTANT_PEAKS
DLY_LEVELS
DATA_SYMBOLS
DATA_TYPES
"""

class Station:
    def __init__(self, number):
        data = pd.read_sql_query(f"SELECT STATION_NAME, LATITUDE, LONGITUDE FROM STATIONS WHERE STATION_NUMBER='{number}'", connection)
        self.name = data["STATION_NAME"][0]
        self.latitude = data["LATITUDE"][0]
        self.longitude = data["LONGITUDE"][0]
        self.number = number

def is_not_regulated(station_number, connection):
    data = pd.read_sql_query(f"SELECT REGULATED FROM STN_REGULATION WHERE STATION_NUMBER='{station_number}'", connection)
    return len(data["REGULATED"]) == 0 or data["REGULATED"][0] == 0

# TODO: why aren't we plotting multiline?
values = pd.read_sql_query("SELECT * from ANNUAL_STATISTICS", connection)
water_levels = values[values["DATA_TYPE"] == "H"]

station_numbers = water_levels["STATION_NUMBER"].unique()
unregulated = [s for s in station_numbers if is_not_regulated(s, connection)]

for station_number in unregulated:
    station = Station(station_number)
    station_data = water_levels[water_levels["STATION_NUMBER"] == station.number]
    station_data = station_data.sort_values(by="YEAR")

    # replace each NaN with the previous valid value
    station_data["MEAN"] = station_data["MEAN"].ffill()

    plt.plot(station_data["YEAR"], station_data["MEAN"], '-', label=station.name)

plt.title(f"Mean annual water levels of various bodies of water in Canada")
plt.xlabel("Year")
plt.ylabel("Mean water level")
plt.grid(True)
plt.tight_layout()
plt.show()