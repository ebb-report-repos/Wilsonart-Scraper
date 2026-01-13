
# Wilsonart Scraper

Scraper and availability checker for Wilsonart business site (LA and Seattle warehouses).  
Generates HPL product availability reports in Excel and can be viewed interactively using Streamlit.

---

## Features

- Scrapes product information from Wilsonart for LA (`90058`) and Seattle (`98001`) zip codes.
- Collects product details: Design ID, Design Name, Grade, Finish, Size, Vendor Part Number.
- Queries warehouse availability via Wilsonart API.
- Generates Excel reports with:
  - `All_Products`: all products with availability
  - `Both_Available`: products available in both warehouses
- Optional interactive view using Streamlit.

---

## Folder Structure

```

scraper/
│ main.py           # main scraper
│ app.py            # Streamlit wrapper
│ requirements.txt  # dependencies
│ README.md         # instructions
│ output/           # Excel reports will be saved here

````

> `output/` folder will be created automatically by `main.py` and is ignored in the repository.

---

## Setup

### 1. Clone the repository

```bash
git clone git@github.com:ebb-report-repos/Wilsonart-Scraper.git
cd Wilsonart-Scraper
````

### 2. Install dependencies

Make sure you have Python 3.9+ installed. Then:

```bash
pip install -r requirements.txt
```

---

## Usage

### Run scraper and save Excel reports

```bash
python main.py
```

* Output files will be saved in `output/warehouse_availability_LASAV3.xlsx`
* Two sheets:

  * `All_Products`
  * `Both_Available`

---

### Run Streamlit app

```bash
streamlit run app.py
```

* Opens an interactive web interface to view the availability reports.
* Can filter, search, and download reports directly from the browser.

---

## Notes

* Make sure your machine has internet access since the scraper requests data from Wilsonart’s site and APIs.
* Existing Excel reports will be overwritten each time `main.py` is run.
* If you see warnings like `Ignoring invalid distribution ~upyterlab`, you can safely ignore them; they won’t affect the scraper.

---

## License

This repository is for internal use or research purposes. Please do not use data scraped from Wilsonart for commercial purposes without permission.


