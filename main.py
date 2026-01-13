# main.py
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

def run_scraper(log_callback=None):
    """
    Run the Wilsonart scraper and return:
    - df_compare: full merged dataframe
    - both_available: products available in both warehouses
    """
    def log(msg):
        """Log message via callback or print"""
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log("Starting scraper...")

    # ================= CONFIG =================
    NUM_PAGES = 1
    ZIPCODES = {"LA": "90058", "SEATTLE": "98001"}
    URL_TEMPLATE = "https://business.wilsonart.com/en/catalog/category/view/s/hpl/id/8/?zipcode={zipcode}&p={page}"
    columns = ["DesignID", "DesignName", "VendPartNumber", "Grade", "FinishID", "Finish", "SizeDescription"]

    dfs = {}

    # ================= SCRAPING =================
    for region, zipcode in ZIPCODES.items():
        log(f"===== Scraping {region} ({zipcode}) =====")
        data = []

        for page in range(1, NUM_PAGES + 1):
            url = URL_TEMPLATE.format(zipcode=zipcode, page=page)
            log(f"{region}: Scraping page {page}")

            try:
                response = requests.get(url, timeout=30)
            except Exception as e:
                log(f"Request failed: {e}")
                continue

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
                for script in form.find_all("script", string=True):
                    if script.string:
                        match = re.search(
                            r"\$scope\.prototypes\s*=\s*(\[.*?\]);",
                            script.string,
                            re.DOTALL
                        )
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
                                data.append([
                                    design_id,
                                    design_name,
                                    vend_part_number,
                                    grade,
                                    "",
                                    finish_name,
                                    size_desc
                                ])

            time.sleep(0.3)

        df = pd.DataFrame(data, columns=columns)
        df = df.apply(lambda col: col.str.strip().str.upper() if col.dtype == "object" else col)

        df['ProductType'] = df['Grade'].str.split(' ').str[1]
        df['Grade'] = df['Grade'].str.split(' ').str[0]

        df['FinishID'] = df['Finish'].str.split(' ').str[0]
        df['Finish'] = df['Finish'].str.split(' ').str[1:].str.join(' ')

        dfs[region] = df
        log(f"{region} completed - {df.shape[0]} rows")

    df_main_la = dfs["LA"]
    df_main_sa = dfs["SEATTLE"]

    log("Scraping complete. Starting warehouse availability checks...")

    # ================= WAREHOUSE AVAILABILITY =================
    def get_vendor_availability(partnumbers, warehouse, inforid):
        API_URL = "https://business.wilsonart.com/en/webservices/index/stockstatus/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        results = []

        for index, pn in enumerate(partnumbers, start=1):
            payload = {"partnumber": pn, "warehouse": warehouse, "inforid": inforid}
            try:
                response = requests.post(API_URL, data=payload, headers=headers)
                if response.status_code == 200:
                    fields = response.text.strip().split("~")
                    current_avail = fields[0]
                    on_order = fields[1]
                    backorder = fields[2]
                    arrival_dates = fields[3] if len(fields) > 3 else "None"
                    results.append({
                        "Vendor Product": pn,
                        "Current Availability": current_avail,
                        "Quantity on Order": on_order,
                        "Quantity on Backorder": backorder,
                        "Arrival Dates": arrival_dates
                    })
                else:
                    log(f"Failed for {pn}, status code: {response.status_code}")
            except Exception as e:
                log(f"Error for {pn}: {e}")
            log(f"Processed {warehouse} -> {index}/{len(partnumbers)}: {pn}")
            time.sleep(0.3)

        df_results = pd.DataFrame(results)
        df_dates = df_results['Arrival Dates'].str.split(',', expand=True)
        df_dates = df_dates.apply(pd.to_datetime, errors='coerce')
        df_dates.columns = [f'Arrival Dates{i+1}' for i in range(df_dates.shape[1])]
        df_results = pd.concat([df_results, df_dates], axis=1)
        return df_results

    # Fill missing FinishID and DesignID
    for df in [df_main_la, df_main_sa]:
        df['FinishID'] = np.where(df['FinishID'].isna(), df['VendPartNumber'].astype(str).str.split('K').str[1].str[:2], df['FinishID'])
        df['Finish'] = df['Finish'].fillna('')
        df['DesignID'] = np.where(df['DesignID']=='', df['VendPartNumber'].str[:4], df['DesignID'])
        df.drop_duplicates(inplace=True)

    sa = df_main_sa.copy()
    la = df_main_la.copy()

    warehouse_sa = get_vendor_availability(sa["VendPartNumber"].tolist(), warehouse="SEA", inforid=109283)
    warehouse_la = get_vendor_availability(la["VendPartNumber"].tolist(), warehouse="LA", inforid=109284)

    warehouse_sa.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)
    warehouse_la.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)

    df_results_sa = warehouse_sa.merge(sa, on='VendPartNumber', how='left')
    df_results_la = warehouse_la.merge(la, on='VendPartNumber', how='left')

    # Filtering and size/part mapping
    for df in [df_results_sa, df_results_la]:
        df['FinishID_str'] = df['FinishID'].astype(str).str.zfill(2)
        condition = (df['DesignID'].str.len()==6) & (df['DesignID'].str[-2:] == df['FinishID_str'])
        df.loc[condition, 'DesignID'] = df.loc[condition, 'DesignID'].str[:-2]
        df.drop('FinishID_str', axis=1, inplace=True)

    # Size mapping
    size_mapping_df = pd.DataFrame({
        "SizeDescription": ["48 X 96","60 X 144","60 X 120","48 X 120","60 X 96","48 X 144","30 X 144","36 X 96","30 X 120","36 X 144","30 X 96","36 X 120","36 X 84","48 X 84","60 X 84","60 X 72","60 X 60","48 X 48","48 X 72","30 X 72","30 X 48","48 X 60","30 X 60","36 X 72","36 X 48","60 X 48","36 X 60","24 X 48","24 X 72","24 X 60","24 X 96","24 X 120","24 X 144","49 X 97","30 X 84","36 X 108"],
        "Size": ["C1","D3","D2","C2","D1","C3","A3","B1","A2","B3","A1","B2","B7","C7","D7","D6","D5","C4","C6","A6","A4","C5","A5","B6","B4","D4","B5","E4","E6","E5","E1","E2","E3","F1","A7","B9"]
    })

    for df in [df_results_sa, df_results_la]:
        df['SizeDescription'] = df['SizeDescription'].str.replace('X',' X ').str.replace(r'\s+',' ', regex=True).str.strip()
        df['Size'] = df['SizeDescription'].map(size_mapping_df.set_index('SizeDescription')['Size'])
        df['PartNumber'] = df['DesignID'] + '-' + df['Grade'] + '-' + df['FinishID'] + df['Size']

    # Merge LA/SA
    la = df_results_la.rename(columns={
        "Current Availability": "Availability_LA",
        "Quantity on Order": "OnOrder_LA",
        "Quantity on Backorder": "Backorder_LA"
    })
    sa = df_results_sa.rename(columns={
        "Current Availability": "Availability_SA",
        "Quantity on Order": "OnOrder_SA",
        "Quantity on Backorder": "Backorder_SA"
    })

    # Rename arrival columns
    for i in range(1,6):
        la.rename(columns={f"Arrival Dates{i}":f"Arrival Dates{i}_LA"}, inplace=True)
        sa.rename(columns={f"Arrival Dates{i}":f"Arrival Dates{i}_SA"}, inplace=True)

    merge_cols = ["VendPartNumber","PartNumber","DesignID","FinishID","Grade"]
    df_compare = la.merge(sa, on=merge_cols, how='outer', indicator=True, suffixes=("_LA","_SA"))
    df_compare["In_LA"] = df_compare["_merge"].isin(["left_only","both"])
    df_compare["In_SA"] = df_compare["_merge"].isin(["right_only","both"])
    for col in ["Availability_LA","Availability_SA"]:
        df_compare[col] = pd.to_numeric(df_compare[col], errors='coerce').fillna(0)

    la_date_cols = [c for c in df_compare.columns if c.startswith("Arrival Dates") and c.endswith("_LA")]
    sa_date_cols = [c for c in df_compare.columns if c.startswith("Arrival Dates") and c.endswith("_SA")]

    df_compare["Available_LA"] = df_compare["In_LA"] & ((df_compare["Availability_LA"]>0) | df_compare[la_date_cols].notna().any(axis=1))
    df_compare["Available_SA"] = df_compare["In_SA"] & ((df_compare["Availability_SA"]>0) | df_compare[sa_date_cols].notna().any(axis=1))
    df_compare["Total_Availability"] = df_compare["Availability_LA"] + df_compare["Availability_SA"]
    df_compare["Availability_Status"] = np.select(
        [df_compare["Available_LA"] & df_compare["Available_SA"],
         df_compare["Available_LA"] & (~df_compare["Available_SA"]),
         (~df_compare["Available_LA"]) & df_compare["Available_SA"]],
        ["Available in Both","LA Only","Seattle Only"], default="Not Available"
    )

    both_available = df_compare[df_compare["Available_LA"] & df_compare["Available_SA"]].copy()
    both_available.drop("_merge", axis=1, inplace=True)

    log("Scraper finished successfully!")

    return df_compare, both_available
