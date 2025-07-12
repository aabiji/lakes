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

path = "dataset/Hydat.sqlite3"
connection = sqlite3.connect(path)

# Database reference: https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/HYDAT_Definition_EN.pdf

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

"""
# so, we're getting the average water levels from all the different stations per year

# TODO: take a look at the minimum and maximums too, maybe they look different
# TODO: what if we look at regulated and unregulated sources?
# TODO: wait, our data looks wonky because each station uses a different datum,
#       we need to convert all the stations to use the same datum (measurement reference point)
# TODO: look at these other factors: precipitation, temperature, evaporation

values = pd.read_sql_query("SELECT * from ANNUAL_STATISTICS", connection)
water_levels = values[values["DATA_TYPE"] == "H"]

station_numbers = water_levels["STATION_NUMBER"].unique()
unregulated_stations = [s for s in station_numbers if is_not_regulated(s, connection)]

# only want water sources that aren't regulated
filtered = water_levels[water_levels["STATION_NUMBER"].isin(unregulated_stations)].copy()

filtered = filtered.sort_values(by=["STATION_NUMBER", "YEAR"])

filtered = filtered.dropna(subset=["MEAN"]) # remove NaNs

# group duplicate years from different stations together, and average the means
mean_water_levels_by_year = filtered.groupby("YEAR")["MEAN"].mean()

plt.plot(mean_water_levels_by_year.index, mean_water_levels_by_year.values)
plt.title(f"Mean annual water levels of various bodies of water in Canada")
plt.xlabel("Year")
plt.ylabel("Mean water level")
plt.grid(True)
plt.tight_layout()
plt.show()
"""

values = pd.read_sql_query("SELECT * from STN_DATUM_CONVERSION", connection)

stations = values.groupby("DATUM_ID_TO")
for name, group in stations:
    print(name)
    print(group)
    print()
