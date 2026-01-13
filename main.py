# main.py
import pandas as pd
import numpy as np
import requests
import requests, json, re, time
from bs4 import BeautifulSoup
import os

def run_scraper(log_callback=None):
    """Scrapes Wilsonart warehouse availability and returns comparison DataFrame"""

    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    NUM_PAGES = 1
    ZIPCODES = {"LA": "90058", "SEATTLE": "98001"}
    URL_TEMPLATE = "https://business.wilsonart.com/en/catalog/category/view/s/hpl/id/8/?zipcode={zipcode}&p={page}"

    columns = ["DesignID", "DesignName", "VendPartNumber", "Grade", "FinishID", "Finish", "SizeDescription"]

    dfs = {}

    # ------------- SCRAPE -----------------
    for region, zipcode in ZIPCODES.items():
        log(f"\n===== Scraping {region} ({zipcode}) =====")
        data = []

        for page in range(1, NUM_PAGES + 1):
            url = URL_TEMPLATE.format(zipcode=zipcode, page=page)
            log(f"{region}: Scraping page {page}")
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
            forms = soup.find_all("form", {"data-role": "tocart-form"})

            for form in forms:
                rec_heading = form.find("div", class_="rec_heading")
                if rec_heading:
                    lines = rec_heading.get_text(separator="\n").split("\n")
                    design_id = lines[0].strip() if len(lines) > 0 else ""
                    design_name = lines[1].strip() if len(lines) > 1 else ""
                else:
                    design_id = ""
                    design_name = ""

                prototypes_json = None
                for script in form.find_all("script", text=True):
                    if script.string:
                        match = re.search(r"\$scope\.prototypes\s*=\s*(\[.*?\]);", script.string, re.DOTALL)
                        if match:
                            prototypes_json = match.group(1)
                            break
                if not prototypes_json:
                    continue

                prototypes = json.loads(prototypes_json)

                for product_type in prototypes:
                    grade = product_type.get("name", "")
                    for finish in product_type.get("finishes", []):
                        finish_name = finish.get("name", "")
                        for size in finish.get("sizes", []):
                            size_desc = size.get("name", "")
                            for part in size.get("partnumber", []):
                                vend_part_number = str(part.get("name") or "")
                                design_id_match = re.match(r"(\d{4,6})", vend_part_number)
                                design_id = design_id_match.group(1) if design_id_match else ""
                                data.append([design_id, design_name, vend_part_number, grade, "", finish_name, size_desc])
            time.sleep(0.3)

        df = pd.DataFrame(data, columns=columns)
        df = df.applymap(lambda x: x.strip().upper() if isinstance(x, str) else x)
        df['ProductType'] = df['Grade'].str.split(' ').str[1]
        df['Grade'] = df['Grade'].str.split(' ').str[0]
        df['FinishID'] = df['Finish'].str.split(' ').str[0]
        df['Finish'] = df['Finish'].str.split(' ').str[1:].str.join(' ')
        dfs[region] = df
        log(f"{region} completed - {df.shape[0]} rows")

    df_main_la = dfs["LA"]
    df_main_sa = dfs["SEATTLE"]

    # -------- Clean DesignID / FinishID ----------
    for df in [df_main_la, df_main_sa]:
        df['FinishID'] = np.where(df['FinishID'].isna(), df['VendPartNumber'].str.split('K').str[1].str[:2], df['FinishID'])
        df['Finish'] = df['Finish'].fillna('')
        df['DesignID'] = np.where(df['DesignID']=='', df['VendPartNumber'].str[:4], df['DesignID'])
        df.drop_duplicates(inplace=True)

    sa = df_main_sa.copy()
    la = df_main_la.copy()

    # --------- Vendor Availability API ----------
    def get_vendor_availability(partnumbers, warehouse, inforid):
        API_URL = "https://business.wilsonart.com/en/webservices/index/stockstatus/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        }
        results = []
        for idx, pn in enumerate(partnumbers, start=1):
            payload = {"partnumber": pn, "warehouse": warehouse, "inforid": inforid}
            try:
                response = requests.post(API_URL, data=payload, headers=headers)
                if response.status_code == 200:
                    fields = response.text.strip().split("~")
                    current_avail = fields[0]
                    on_order = fields[1]
                    backorder = fields[2]
                    arrival_dates = fields[3] if len(fields) > 3 else "None"
                    row = {
                        "Vendor Product": pn,
                        "Current Availability": current_avail,
                        "Quantity on Order": on_order,
                        "Quantity on Backorder": backorder,
                        "Arrival Dates": arrival_dates
                    }
                    results.append(row)
            except Exception as e:
                log(f"Error for {pn}: {e}")
            log(f"Processed {warehouse} -> {idx}/{len(partnumbers)}: {pn}")
            time.sleep(0.3)
        df_results = pd.DataFrame(results)
        df_dates = df_results['Arrival Dates'].str.split(',', expand=True)
        df_dates = df_dates.apply(pd.to_datetime, errors='coerce')
        df_dates.columns = [f'Arrival Dates{i+1}' for i in range(df_dates.shape[1])]
        df_results = pd.concat([df_results, df_dates], axis=1)
        return df_results

    warehouse_sa = get_vendor_availability(sa["VendPartNumber"].tolist(), "SEA", 109283)
    warehouse_la = get_vendor_availability(la["VendPartNumber"].tolist(), "LA", 109284)

    # --------- Merge and clean ----------
    warehouse_sa.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)
    warehouse_la.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)
    df_results_sa = warehouse_sa.merge(sa, on='VendPartNumber', how='left')
    df_results_la = warehouse_la.merge(la, on='VendPartNumber', how='left')

    # Dynamically get all arrival date columns
    sa_date_cols = [c for c in df_results_sa.columns if c.startswith("Arrival Dates")]
    la_date_cols = [c for c in df_results_la.columns if c.startswith("Arrival Dates")]

    # Merge LA & SA for comparison
    la_filtered = df_results_la.copy()
    sa_filtered = df_results_sa.copy()
    for i, col in enumerate(la_date_cols):
        la_filtered.rename(columns={col: f"{col}_LA"}, inplace=True)
    for i, col in enumerate(sa_date_cols):
        sa_filtered.rename(columns={col: f"{col}_SA"}, inplace=True)

    merge_cols = ["VendPartNumber", "DesignID", "Grade", "FinishID"]
    df_compare = la_filtered.merge(sa_filtered, on=merge_cols, how="outer", indicator=True)

    # Availability computation
    df_compare["Available_LA"] = df_compare["_merge"].isin(["left_only","both"]) & (
        df_compare["Current Availability"].fillna(0).astype(float) > 0 |
        df_compare[[c for c in df_compare if c.endswith("_LA")]].notna().any(axis=1)
    )
    df_compare["Available_SA"] = df_compare["_merge"].isin(["right_only","both"]) & (
        df_compare["Current Availability"].fillna(0).astype(float) > 0 |
        df_compare[[c for c in df_compare if c.endswith("_SA")]].notna().any(axis=1)
    )

    df_compare["Availability_Status"] = np.select(
        [
            df_compare["Available_LA"] & df_compare["Available_SA"],
            df_compare["Available_LA"] & (~df_compare["Available_SA"]),
            (~df_compare["Available_LA"]) & df_compare["Available_SA"]
        ],
        ["Available in Both", "LA Only", "Seattle Only"],
        default="Not Available"
    )

    both_available = df_compare[df_compare["Available_LA"] & df_compare["Available_SA"]].copy()

    log("Scraping complete!")
    return df_compare, both_available
