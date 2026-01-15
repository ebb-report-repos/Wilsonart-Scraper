def run_scraper(log_callback=None):

    import pandas as pd
    import numpy as np
    import time
    import requests
    #============================
    from bs4 import BeautifulSoup
    import json
    import re
    import streamlit as st
    import os
    
    from datetime import datetime
    # ================= CONFIG =================


    
    NUM_PAGES = 21  # number of pages to scrape
    
    ZIPCODES = {
        "LA": "90058",       # Santa Fe Springs
        "SEATTLE": "98001"   # Seattle
    }
    
    URL_TEMPLATE = (
        "https://business.wilsonart.com/en/catalog/category/view/"
        "s/hpl/id/8/?zipcode={zipcode}&p={page}"
    )
    
    columns = [
        "DesignID",
        "DesignName",
        "VendPartNumber",
        "Grade",
        "FinishID",
        "Finish",
        "SizeDescription"
    ]
    
    # ================= SCRAPING =================
    
    dfs = {}

    for region, zipcode in ZIPCODES.items():
        log_callback(f"\n===== Scraping {region} ({zipcode}) =====")
    
        data = []
    
        for page in range(1, NUM_PAGES + 1):
            url = URL_TEMPLATE.format(zipcode=zipcode, page=page)
            log_callback(f"{region}: Scraping page {page}")
    
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, "html.parser")
    
            forms = soup.find_all("form", {"data-role": "tocart-form"})
    
            for form in forms:
                # ---------------- Design ID / Name ----------------
                rec_heading = form.find("div", class_="rec_heading")
                if rec_heading:
                    lines = rec_heading.get_text(separator="\n").split("\n")
                    design_id = lines[0].strip() if len(lines) > 0 else ""
                    design_name = lines[1].strip() if len(lines) > 1 else ""
                else:
                    design_id = ""
                    design_name = ""
    
                # ---------------- Prototypes JSON ----------------
                prototypes_json = None
                for script in form.find_all("script", text=True):
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
    
                # ---------------- Iterate ----------------
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
    
            # -------- Deley--------
            time.sleep(0.3)
    
        # ====================================================================
    
        df = pd.DataFrame(data, columns=columns)
    
        # Clean strings
        df = df.applymap(lambda x: x.strip().upper() if isinstance(x, str) else x)
    
        # Split Grade / ProductType
        df['ProductType'] = df['Grade'].str.split(' ').str[1]
        df['Grade'] = df['Grade'].str.split(' ').str[0]
    
        # Split FinishID / Finish
        df['FinishID'] = df['Finish'].str.split(' ').str[0]
        df['Finish'] = df['Finish'].str.split(' ').str[1:].str.join(' ')
    
        dfs[region] = df
        log_callback(f"{region} completed - {df.shape[0]} rows")
    
    # ================= FINAL =================
    
    df_main_la = dfs["LA"]
    df_main_sa = dfs["SEATTLE"]
    
    log_callback("\nScraping complete!")
    log_callback("LA shape: " + str(df_main_la.shape))
    log_callback("Seattle shape:"+ str(df_main_sa.shape))
    #===============================================================================cleaning===================================
    ##2---------------------------------dnt----------------------------------------------
    
    #=====================================================================================================================
    df_main_la['FinishID'] = np.where(
        df_main_la['FinishID'].isna(),
        df_main_la['VendPartNumber'].astype(str).str.split('K').str[1].str[:2],
        df_main_la['FinishID']
    )
    
    df_main_la['Finish'] = df_main_la['Finish'].fillna('')
    #==============================================================
    df_main_sa['FinishID'] = np.where(
        df_main_sa['FinishID'].isna(),
        df_main_sa['VendPartNumber'].astype(str).str.split('K').str[1].str[:2],
        df_main_sa['FinishID']
    )
    
    df_main_la['Finish'] = df_main_la['Finish'].fillna('')
    #==============================================================
    df_main_sa['DesignID'] = np.where(
        df_main_sa['DesignID'] == '',
        df_main_sa['VendPartNumber'].str[:4],
        df_main_sa['DesignID']
    )
    df_main_la['DesignID'] = np.where(
        df_main_la['DesignID'] == '',
        df_main_la['VendPartNumber'].str[:4],
        df_main_la['DesignID']
    )
    
    #======================================
    
    df_main_sa=df_main_sa.drop_duplicates()
    df_main_la=df_main_la.drop_duplicates()
    
    sa = df_main_sa.copy()
    la = df_main_la.copy()
    #================================================================================================================
    
    #========================================================part II==============================================================
    
    
    
    #process the whse id's
    def get_vendor_availability(partnumbers, warehouse, inforid):
    
        API_URL = "https://business.wilsonart.com/en/webservices/index/stockstatus/"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        }
    
        results = []
    
        for index, pn in enumerate(partnumbers, start=1):
            payload = {
                "partnumber": pn,
                "warehouse": warehouse,
                "inforid": inforid
            }
    
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
    
                else:
                    log_callback(f"Failed for {pn}, status code: {response.status_code}")
    
            except Exception as e:
                log_callback(f"Error for {pn}: {e}")
    
            log_callback(f"Processed {warehouse} ->  {index}/{len(partnumbers)}: {pn}")
            time.sleep(0.3)
    
        # DataFrame from the scrapes
        df_results = pd.DataFrame(results)
    
        # split  dates 
        df_dates = df_results['Arrival Dates'].str.split(',', expand=True)
        df_dates = df_dates.apply(pd.to_datetime, errors='coerce')
        df_dates.columns = [f'Arrival Dates{i+1}' for i in range(df_dates.shape[1])]
    
        # combine 
        df_results = pd.concat([df_results, df_dates], axis=1)
        
        return df_results
    #======================================================================
    #**************************************************************************
    #8888888888888888888888888888888888888888888888888888888888888888888888888
    #======================================================================
    partnumbers_sa = sa["VendPartNumber"].tolist()
    warehouse_sa = get_vendor_availability(partnumbers_sa, warehouse="SEA", inforid=109283)
    
    partnumbers_la = la["VendPartNumber"].tolist()
    warehouse_la = get_vendor_availability(partnumbers_la, warehouse="LA", inforid=109284)
    
    #======================================================================================================
    warehouse_sa.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)
    df_results_sa = warehouse_sa.merge(sa, on='VendPartNumber', how='left')
    duplicates_all_sa_new1 = df_results_sa[df_results_sa.duplicated(keep=False)]
    
    warehouse_la.rename(columns={'Vendor Product':'VendPartNumber'}, inplace=True)
    df_results_la = warehouse_la.merge(la, on='VendPartNumber', how='left')
    duplicates_all_la_new1 = df_results_la[df_results_la.duplicated(keep=False)]
    
    # Dynamically select arrival date columns
    sa_arrival_cols = [c for c in df_results_sa.columns if c.startswith("Arrival Dates")]
    la_arrival_cols = [c for c in df_results_la.columns if c.startswith("Arrival Dates")]
    
    # Filter results including all dynamic arrival columns
    df_results_sa_filtered = df_results_sa[['VendPartNumber', 'DesignID', 'DesignName', 'Grade', 'FinishID', 'Finish', 
                                            'SizeDescription', 'ProductType', 'Current Availability', 'Quantity on Order', 
                                            'Quantity on Backorder'] + sa_arrival_cols]
    
    df_results_la_filtered = df_results_la[['VendPartNumber', 'DesignID', 'DesignName', 'Grade', 'FinishID', 'Finish', 
                                            'SizeDescription', 'ProductType', 'Current Availability', 'Quantity on Order', 
                                            'Quantity on Backorder'] + la_arrival_cols]
    
    #=====================================
    
    # compare with last 2 chars of FinishID in DesignID
    for df_filtered in [df_results_sa_filtered, df_results_la_filtered]:
        df_filtered['FinishID_str'] = df_filtered['FinishID'].astype(str).str.zfill(2)
        condition = (df_filtered['DesignID'].str.len() == 6) & \
                    (df_filtered['DesignID'].str[-2:] == df_filtered['FinishID_str'])
        df_filtered.loc[condition, 'DesignID'] = df_filtered.loc[condition, 'DesignID'].str[:-2]
        df_filtered.drop('FinishID_str', axis=1, inplace=True)
    
    #========================================================================
    # Mapping sizes
    size_mapping_df = pd.DataFrame({
        "SizeDescription": [
            "48 X 96", "60 X 144", "60 X 120", "48 X 120", "60 X 96",
            "48 X 144", "30 X 144", "36 X 96", "30 X 120", "36 X 144",
            "30 X 96", "36 X 120", "36 X 84", "48 X 84", "60 X 84",
            "60 X 72", "60 X 60", "48 X 48", "48 X 72", "30 X 72",
            "30 X 48", "48 X 60", "30 X 60", "36 X 72", "36 X 48",
            "60 X 48", "36 X 60", "24 X 48", "24 X 72", "24 X 60",
            "24 X 96", "24 X 120", "24 X 144", "49 X 97", "30 X 84",
            "36 X 108"
        ],
        "Size": [
            "C1", "D3", "D2", "C2", "D1",
            "C3", "A3", "B1", "A2", "B3",
            "A1", "B2", "B7", "C7", "D7",
            "D6", "D5", "C4", "C6", "A6",
            "A4", "C5", "A5", "B6", "B4",
            "D4", "B5", "E4", "E6", "E5",
            "E1", "E2", "E3", "F1", "A7",
            "B9"
        ]
    })
    
    # Clean up size descriptions
    for df_filtered in [df_results_sa_filtered, df_results_la_filtered]:
        df_filtered['SizeDescription'] = df_filtered['SizeDescription'].str.replace('X', ' X ', regex=False)\
                                                                     .str.replace(r'\s+', ' ', regex=True)\
                                                                     .str.strip()
        df_filtered['Size'] = df_filtered['SizeDescription'].map(size_mapping_df.set_index('SizeDescription')['Size'])
    
    #==============================creating/combining part number from multiple columns =======================================
    for df_filtered in [df_results_sa_filtered, df_results_la_filtered]:
        df_filtered['PartNumber'] = (df_filtered['DesignID'].astype(str) + '-' +
                                     df_filtered['FinishID'].astype(str) + '-' +
                                     df_filtered['Grade'].astype(str) +
                                     df_filtered['Size'].astype(str))
    
    #==================================================================
    
    #========================================================last process combining both sa / la 
    # --- 1- Rename main quantity columns for clarity ---
    la = df_results_la_filtered.rename(columns={
        "Current Availability": "Availability_LA",
        "Quantity on Order": "OnOrder_LA",
        "Quantity on Backorder": "Backorder_LA"
    })
    
    sa = df_results_sa_filtered.rename(columns={
        "Current Availability": "Availability_SA",
        "Quantity on Order": "OnOrder_SA",
        "Quantity on Backorder": "Backorder_SA"
    })
    
    # --- 2- Dynamically rename arrival date columns ---
    for col in [c for c in la.columns if c.startswith("Arrival Dates")]:
        la.rename(columns={col: f"{col}_LA"}, inplace=True)
    for col in [c for c in sa.columns if c.startswith("Arrival Dates")]:
        sa.rename(columns={col: f"{col}_SA"}, inplace=True)
    
    # --- 3- Merge on stable product keys ---
    merge_cols = ["VendPartNumber","PartNumber", "DesignID", "FinishID", "Grade"]
    
    df_compare = la.merge(sa, on=merge_cols, how="outer", indicator=True, suffixes=("_LA", "_SA"))
    
    # --- 4- Identify product presence in each warehouse ---
    df_compare["In_LA"] = df_compare["_merge"].isin(["left_only", "both"])
    df_compare["In_SA"] = df_compare["_merge"].isin(["right_only", "both"])
    
    # --- 5- Ensure numeric availability columns ---
    for col in ["Availability_LA", "Availability_SA"]:
        df_compare[col] = pd.to_numeric(df_compare[col], errors='coerce').fillna(0)
    
    # --- 6- Dynamically select arrival date columns ---
    la_date_cols = [c for c in df_compare.columns if c.startswith("Arrival Dates") and c.endswith("_LA")]
    sa_date_cols = [c for c in df_compare.columns if c.startswith("Arrival Dates") and c.endswith("_SA")]
    
    # --- 7- Compute availability: quantity > 0 OR any arrival date exists ---
    df_compare["Available_LA"] = df_compare["In_LA"] & ((df_compare["Availability_LA"] > 0) | df_compare[la_date_cols].notna().any(axis=1))
    df_compare["Available_SA"] = df_compare["In_SA"] & ((df_compare["Availability_SA"] > 0) | df_compare[sa_date_cols].notna().any(axis=1))
    
    # --- 8- Compute total availability ---
    df_compare["Total_Availability"] = df_compare["Availability_LA"] + df_compare["Availability_SA"]
    
    # --- 9- Human-readable availability status ---
    df_compare["Availability_Status"] = np.select(
        [
            df_compare["Available_LA"] & df_compare["Available_SA"],
            df_compare["Available_LA"] & (~df_compare["Available_SA"]),
            (~df_compare["Available_LA"]) & df_compare["Available_SA"]
        ],
        ["Available in Both", "LA Only", "Seattle Only"],
        default="Not Available"
    )
    
    # --- 10 Create filtered subsets for export ---
    both_available = df_compare[df_compare["Available_LA"] & df_compare["Available_SA"]].copy()
    la_only = df_compare[df_compare["Available_LA"] & (~df_compare["Available_SA"])].copy()
    sa_only = df_compare[(~df_compare["Available_LA"]) & df_compare["Available_SA"]].copy()
    
    for df in (both_available, la_only, sa_only):
        df.drop("_merge", axis=1, inplace=True)
    
    #====================================================================
    # Dynamically combine size descriptions
    for df in [both_available, df_compare]:
        for col in ["SizeDescription_LA", "SizeDescription_SA", "Size_LA", "Size_SA"]:
            df[col] = df[col].replace(['', ' ', 'NaN'], np.nan)
        df["SizeDescription"] = df["SizeDescription_LA"].combine_first(df["SizeDescription_SA"])
        df["Size"] = df["Size_LA"].combine_first(df["Size_SA"])
        for col in ["SizeDescription_LA", "SizeDescription_SA"]:
            df[col] = df[col].fillna(df["SizeDescription"])
        for col in ["Size_LA", "Size_SA"]:
            df[col] = df[col].fillna(df["Size"])
    
    #=====================================================================
    # Reorder columns dynamically
    base_cols = ['PartNumber','VendPartNumber', 'DesignID', 'DesignName_LA', 'Grade', 'FinishID','SizeDescription', 'Size',
                 'Finish_LA', 'ProductType_LA', 'Availability_LA', 'OnOrder_LA','Backorder_LA',
                 'DesignName_SA', 'Finish_SA', 'ProductType_SA', 'Availability_SA', 'OnOrder_SA', 
                 'Backorder_SA', 'In_LA', 'In_SA', 'Available_LA', 'Available_SA', 'Total_Availability', 'Availability_Status']
    arrival_cols = [col for col in df_compare.columns if 'Arrival Dates' in col]
    final_cols = base_cols + arrival_cols
    
    df_compare = df_compare[[col for col in final_cols if col in df_compare.columns]]
    both_available = both_available[[col for col in final_cols if col in both_available.columns]]
    


    return df_compare, both_available 
