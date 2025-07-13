import bs4, glob, os, re, requests, zipfile

def get_dataset():
    print("Downloading the dataset ...")

    base_url = "https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/"
    soup = bs4.BeautifulSoup(requests.get(base_url).text, "html.parser")

    # anything that contains _sqlite3_ and ends in .zip
    pattern = re.compile(r".*_sqlite3_.*\.zip")

    links = [l for l in soup.find_all("a") if pattern.match(l.get_text())]
    filename = links[0]["href"]

    response = requests.get(f"{base_url}{filename}")
    with open("dataset.zip", "wb") as output:
        output.write(response.content)

    with zipfile.ZipFile("dataset.zip", "r") as zip_ref:
        zip_ref.extractall("dataset")

    files = glob.glob("./dataset/*.sqlite3", recursive=True)
    os.remove("dataset")
    return files[0]

def download_shapefiles():
    print("Downloading the provinces and countries shapefiles ...")

    extensions = ["cpg", "dbf", "prj", "shp", "shx"]
    bases = ["ne_10m_admin_1_states_provinces", "ne_10m_admin_0_countries"]
    base_url = "https://github.com/nvkelso/natural-earth-vector/raw/refs/heads/master/10m_cultural"

    for base in bases:
        os.mkdir(base)
        for extension in extensions:
            response = requests.get(f"{base_url}/{base}.{extension}")
            with open(f"{base}/{base}.{extension}", "wb") as output:
                output.write(response.content)

    return f"{bases[0]}/{bases[0]}.shp", f"{bases[1]}/{bases[1]}.shp"
