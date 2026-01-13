import pandas as pd
import numpy as np
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
#============================
from bs4 import BeautifulSoup
import json
import re
import streamlit as st
import os

# ================= CONFIG =================

NUM_PAGES = 1  # number of pages to scrape

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
    print(f"\n===== Scraping {region} ({zipcode}) =====")

    data = []

    for page in range(1, NUM_PAGES + 1):
        url = URL_TEMPLATE.format(zipcode=zipcode, page=page)
        print(f"{region}: Scraping page {page}")

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
    df = df.apply(lambda col: col.str.strip().str.upper() if col.dtype == "object" else col)


    # Split Grade / ProductType
    df['ProductType'] = df['Grade'].str.split(' ').str[1]
    df['Grade'] = df['Grade'].str.split(' ').str[0]

    # Split FinishID / Finish
    df['FinishID'] = df['Finish'].str.split(' ').str[0]
    df['Finish'] = df['Finish'].str.split(' ').str[1:].str.join(' ')

    dfs[region] = df
    print(f"{region} completed - {df.shape[0]} rows")

# ================= FINAL =================

df_main_la = dfs["LA"]
df_main_sa = dfs["SEATTLE"]

print("\nScraping complete!")
print("LA shape:", df_main_la.shape)
print("Seattle shape:", df_main_sa.shape)
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
                print(f"Failed for {pn}, status code: {response.status_code}")

        except Exception as e:
            print(f"Error for {pn}: {e}")

        print(f"Processed {warehouse} ->  {index}/{len(partnumbers)}: {pn}")
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


partnumbers_sa = sa["VendPartNumber"].tolist()
warehouse_sa = get_vendor_availability(partnumbers_sa, warehouse="SEA", inforid=109283)


partnumbers_la = la["VendPartNumber"].tolist()
warehouse_la = get_vendor_availability(partnumbers_la, warehouse="LA", inforid=109284)







#======================================================================================================
warehouse_sa.rename(columns = {'Vendor Product':'VendPartNumber'},inplace = True)
df_results_sa = warehouse_sa.merge(sa,on = 'VendPartNumber',how = 'left')

duplicates_all_sa_new1 = df_results_sa[df_results_sa.duplicated(keep=False)]



warehouse_la.rename(columns = {'Vendor Product':'VendPartNumber'},inplace = True)
df_results_la = warehouse_la.merge(la,on = 'VendPartNumber',how = 'left')

duplicates_all_sa_new1 = df_results_la[df_results_la.duplicated(keep=False)]


df_results_sa_filtered=df_results_sa[['VendPartNumber', 'DesignID', 'DesignName', 'Grade', 'FinishID', 'Finish', 'SizeDescription', 'ProductType',
                                     'Current Availability', 'Quantity on Order', 'Quantity on Backorder',  'Arrival Dates1', 
                                      'Arrival Dates2', 'Arrival Dates3', 'Arrival Dates4', 'Arrival Dates5']]
df_results_la_filtered=df_results_la[['VendPartNumber', 'DesignID', 'DesignName', 'Grade', 'FinishID', 'Finish', 'SizeDescription', 'ProductType',
                               'Current Availability', 'Quantity on Order', 'Quantity on Backorder', 'Arrival Dates1', 
                               'Arrival Dates2', 'Arrival Dates3', 'Arrival Dates4', 'Arrival Dates5']] 


#=====================================

# compare with last 2 chars
df_results_sa_filtered['FinishID_str'] = df_results_sa_filtered['FinishID'].astype(str).str.zfill(2)

# DesignID is 6 chars and last 2 chars match FinishID
condition = (df_results_sa_filtered['DesignID'].str.len() == 6) & \
            (df_results_sa_filtered['DesignID'].str[-2:] == df_results_sa_filtered['FinishID_str'])

# cut the last 2 characters
df_results_sa_filtered.loc[condition, 'DesignID'] = df_results_sa_filtered.loc[condition, 'DesignID'].str[:-2]

#==================================================================================================================

df_results_la_filtered['FinishID_str'] = df_results_la_filtered['FinishID'].astype(str).str.zfill(2)


condition = (df_results_la_filtered['DesignID'].str.len() == 6) & \
            (df_results_la_filtered['DesignID'].str[-2:] == df_results_la_filtered['FinishID_str'])


df_results_la_filtered.loc[condition, 'DesignID'] = df_results_la_filtered.loc[condition, 'DesignID'].str[:-2]

#========================================================================
df_results_sa_filtered.drop('FinishID_str',axis = 1, inplace = True)
df_results_la_filtered.drop('FinishID_str',axis = 1, inplace = True)


#===============================
#===================================================mapping df=================================

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
#================================================================

size_mapping_df['SizeDescription'] = (
    df_sizes['Size']
    .str.replace('X', ' X ', regex=False)
    .str.replace(r'\s+', ' ', regex=True)
    .str.strip()
)


size_mapping_correct = pd.Series(
    index=size_mapping.values,  # sizes become index
    data=size_mapping.index     # codes become values
)

size_mapping_df = size_mapping_correct.reset_index()
size_mapping_df.columns = ['SizeDescription', 'Size']
#=================both df's cleaning size description===================
df_results_la_filtered['SizeDescription'] = (
    df_results_la_filtered['SizeDescription']
    .str.replace('X', ' X ', regex=False)
    .str.replace(r'\s+', ' ', regex=True)
    .str.strip()
)

df_results_sa_filtered['SizeDescription'] = (
    df_results_sa_filtered['SizeDescription']
    .str.replace('X', ' X ', regex=False)
    .str.replace(r'\s+', ' ', regex=True)
    .str.strip()
)
#==============================================================


#========================================================================================================================

# Map sa
df_results_sa_filtered['Size'] = df_results_sa_filtered['SizeDescription'].map(
    size_mapping_df.set_index('SizeDescription')['Size']
)

# Map la
df_results_la_filtered['Size'] = df_results_la_filtered['SizeDescription'].map(
    size_mapping_df.set_index('SizeDescription')['Size']
)

#==============================creating/combining part number from multiple columns =======================================

df_results_sa_filtered['PartNumber'] = (
    df_results_sa_filtered['DesignID'].astype(str) + '-' +
    df_results_sa_filtered['Grade'].astype(str) + '-' +
    df_results_sa_filtered['FinishID'].astype(str)+
    df_results_sa_filtered['Size'].astype(str)
)


df_results_la_filtered['PartNumber'] = (
    df_results_la_filtered['DesignID'].astype(str) + '-' +
    df_results_la_filtered['Grade'].astype(str) + '-' +
    df_results_la_filtered['FinishID'].astype(str)+
    df_results_la_filtered['Size'].astype(str)
)


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

# --- 2- Rename arrival date columns for LA to ensure suffix consistency ---
for i in range(1, 6):
    col = f"Arrival Dates{i}"
    if col in la.columns:
        la.rename(columns={col: f"{col}_LA"}, inplace=True)
    if col in sa.columns:
        sa.rename(columns={col: f"{col}_SA"}, inplace=True)

# --- 3- Merge on stable product keys ---
merge_cols = ["VendPartNumber","PartNumber", "DesignID", "FinishID", "Grade"]

df_compare = la.merge(
    sa,
    on=merge_cols,
    how="outer",
    indicator=True,
    suffixes=("_LA", "_SA")
)

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
df_compare["Available_LA"] = df_compare["In_LA"] & (
    (df_compare["Availability_LA"] > 0) |
    df_compare[la_date_cols].notna().any(axis=1)
)

df_compare["Available_SA"] = df_compare["In_SA"] & (
    (df_compare["Availability_SA"] > 0) |
    df_compare[sa_date_cols].notna().any(axis=1)
)

# --- 8- Compute total availability ---
df_compare["Total_Availability"] = df_compare["Availability_LA"] + df_compare["Availability_SA"]

# --- 9- Human-readable availability status ---
df_compare["Availability_Status"] = np.select(
    [
        df_compare["Available_LA"] & df_compare["Available_SA"],
        df_compare["Available_LA"] & (~df_compare["Available_SA"]),
        (~df_compare["Available_LA"]) & df_compare["Available_SA"]
    ],
    [
        "Available in Both",
        "LA Only",
        "Seattle Only"
    ],
    default="Not Available"
)

# --- 10 Create filtered subsets for export ---
both_available = df_compare[df_compare["Available_LA"] & df_compare["Available_SA"]].copy()
la_only = df_compare[df_compare["Available_LA"] & (~df_compare["Available_SA"])].copy()
sa_only = df_compare[(~df_compare["Available_LA"]) & df_compare["Available_SA"]].copy()

# Drop _merge in subsets for cleaner reporting
for df in (both_available, la_only, sa_only):
    df.drop("_merge", axis=1, inplace=True)


#======================================================================
both_available["SizeDescription_LA"] = both_available["SizeDescription_LA"].replace(['', ' ', 'NaN'], np.nan)
both_available["SizeDescription_SA"] = both_available["SizeDescription_SA"].replace(['', ' ', 'NaN'], np.nan)
both_available["Size_LA"] = both_available["Size_LA"].replace(['', ' ', 'NaN'], np.nan)
both_available["Size_SA"] = both_available["Size_SA"].replace(['', ' ', 'NaN'], np.nan)
both_available = both_available.reset_index(drop=True)

both_available["SizeDescription"] = both_available["SizeDescription_LA"].combine_first(both_available["SizeDescription_SA"])
both_available["Size"] = both_available["Size_LA"].combine_first(both_available["Size_SA"])


both_available["SizeDescription_LA"] = both_available["SizeDescription_LA"].fillna(both_available["SizeDescription"])
both_available["SizeDescription_SA"] = both_available["SizeDescription_SA"].fillna(both_available["SizeDescription"])
both_available["Size_LA"] = both_available["Size_LA"].fillna(both_available["Size"])
both_available["Size_SA"] = both_available["Size_SA"].fillna(both_available["Size"])


#======================================================================

df_compare["SizeDescription_LA"] = df_compare["SizeDescription_LA"].replace(['', ' ', 'NaN'], np.nan)
df_compare["SizeDescription_SA"] = df_compare["SizeDescription_SA"].replace(['', ' ', 'NaN'], np.nan)
df_compare["Size_LA"] = df_compare["Size_LA"].replace(['', ' ', 'NaN'], np.nan)
df_compare["Size_SA"] = df_compare["Size_SA"].replace(['', ' ', 'NaN'], np.nan)
df_compare = df_compare.reset_index(drop=True)

df_compare["SizeDescription"] = df_compare["SizeDescription_LA"].combine_first(df_compare["SizeDescription_SA"])
df_compare["Size"] = df_compare["Size_LA"].combine_first(df_compare["Size_SA"])


df_compare["SizeDescription_LA"] = df_compare["SizeDescription_LA"].fillna(df_compare["SizeDescription"])
df_compare["SizeDescription_SA"] = df_compare["SizeDescription_SA"].fillna(df_compare["SizeDescription"])
df_compare["Size_LA"] = df_compare["Size_LA"].fillna(df_compare["Size"])
df_compare["Size_SA"] = df_compare["Size_SA"].fillna(df_compare["Size"])
#=====================================================================
# df_compare=df_compare[['PartNumber','VendPartNumber', 'DesignID', 'DesignName_LA', 'Grade', 'FinishID','SizeDescription', 'Size',
#                        'Finish_LA', 'ProductType_LA', 'Availability_LA', 'OnOrder_LA',
#                        'Backorder_LA', 'Arrival Dates1_LA', 'Arrival Dates2_LA', 'Arrival Dates3_LA',
#                        'Arrival Dates4_LA', 'Arrival Dates5_LA', 'DesignName_SA', 'Finish_SA', 
#                        'ProductType_SA', 'Availability_SA', 'OnOrder_SA', 'Backorder_SA', 'Arrival Dates1_SA', 'Arrival Dates2_SA',
#                        'Arrival Dates3_SA', 'Arrival Dates4_SA', 'Arrival Dates5_SA', 'In_LA',
#                        'In_SA', 'Available_LA', 'Available_SA', 'Total_Availability', 'Availability_Status']]


# both_available=both_available[['PartNumber','VendPartNumber', 'DesignID', 'DesignName_LA', 'Grade', 'FinishID','SizeDescription', 'Size',
#                        'Finish_LA', 'ProductType_LA', 'Availability_LA', 'OnOrder_LA',
#                        'Backorder_LA', 'Arrival Dates1_LA', 'Arrival Dates2_LA', 'Arrival Dates3_LA',
#                        'Arrival Dates4_LA', 'Arrival Dates5_LA', 'DesignName_SA', 'Finish_SA', 
#                        'ProductType_SA', 'Availability_SA', 'OnOrder_SA', 'Backorder_SA', 'Arrival Dates1_SA', 'Arrival Dates2_SA',
#                        'Arrival Dates3_SA', 'Arrival Dates4_SA', 'Arrival Dates5_SA', 'In_LA',
#                        'In_SA', 'Available_LA', 'Available_SA', 'Total_Availability', 'Availability_Status']]
# Base columns that are always expected
# base_cols = ['PartNumber','VendPartNumber', 'DesignID', 'DesignName_LA', 'Grade', 'FinishID','SizeDescription', 'Size',
#              'Finish_LA', 'ProductType_LA', 'Availability_LA', 'OnOrder_LA','Backorder_LA',
#              'DesignName_SA', 'Finish_SA', 'ProductType_SA', 'Availability_SA', 'OnOrder_SA', 
#              'Backorder_SA', 'In_LA', 'In_SA', 'Available_LA', 'Available_SA', 'Total_Availability', 'Availability_Status']

# Dynamically find all arrival date columns
arrival_cols = [col for col in df_compare.columns if 'Arrival Dates' in col]

# Combine them
final_cols = base_cols + arrival_cols

# Reorder the DataFrame dynamically
df_compare = df_compare[[col for col in final_cols if col in df_compare.columns]]
both_available = both_available[[col for col in final_cols if col in both_available.columns]]

st.title("Warehouse Availability Export")

# ================= DYNAMIC CLEANING & FILTERING =================

def prepare_filtered_df(df: pd.DataFrame):
    """
    Clean df, dynamically handle Arrival Dates columns,
    and keep only relevant columns.
    """
    # --- dynamically find all 'Arrival Dates' columns ---
    arrival_cols = [col for col in df.columns if 'Arrival Dates' in col]

    # --- base columns ---
    base_cols = [
        'VendPartNumber', 'DesignID', 'DesignName', 'Grade', 'FinishID', 
        'Finish', 'SizeDescription', 'ProductType', 
        'Current Availability', 'Quantity on Order', 'Quantity on Backorder'
    ]

    # --- combine base + arrival columns dynamically ---
    selected_cols = base_cols + arrival_cols

    # --- filter safely ---
    df_filtered = df[[col for col in selected_cols if col in df.columns]].copy()

    # --- standardize size descriptions ---
    for col in ['SizeDescription']:
        if col in df_filtered.columns:
            df_filtered[col] = (
                df_filtered[col]
                .astype(str)
                .str.replace('X', ' X ', regex=False)
                .str.replace(r'\s+', ' ', regex=True)
                .str.strip()
                .replace(['', ' ', 'NaN'], np.nan)
            )

    # --- fill missing FinishID with last 2 chars of VendPartNumber if needed ---
    if 'FinishID' in df_filtered.columns:
        df_filtered['FinishID'] = np.where(
            df_filtered['FinishID'].isna(),
            df_filtered['VendPartNumber'].astype(str).str.split('K').str[1].str[:2],
            df_filtered['FinishID']
        )

    # --- fill missing DesignID from VendPartNumber ---
    if 'DesignID' in df_filtered.columns:
        df_filtered['DesignID'] = np.where(
            df_filtered['DesignID'] == '',
            df_filtered['VendPartNumber'].str[:4],
            df_filtered['DesignID']
        )

    return df_filtered, arrival_cols

# --- prepare SA & LA dynamically ---
df_results_sa_filtered, arrival_cols_sa = prepare_filtered_df(df_results_sa)
df_results_la_filtered, arrival_cols_la = prepare_filtered_df(df_results_la)

# ================= CREATE PART NUMBER =================
def create_partnumber(df):
    df['PartNumber'] = (
        df['DesignID'].astype(str) + '-' +
        df['Grade'].astype(str) + '-' +
        df['FinishID'].astype(str)
    )
    # Add size if available
    if 'Size' in df.columns:
        df['PartNumber'] += df['Size'].astype(str)
    return df

df_results_sa_filtered = create_partnumber(df_results_sa_filtered)
df_results_la_filtered = create_partnumber(df_results_la_filtered)

# ================= MERGE LA & SA =================
merge_cols = ["VendPartNumber", "PartNumber", "DesignID", "FinishID", "Grade"]

df_compare = df_results_la_filtered.merge(
    df_results_sa_filtered,
    on=merge_cols,
    how="outer",
    suffixes=("_LA", "_SA"),
    indicator=True
)

# --- dynamically handle arrival date columns for merge ---
la_date_cols = [c for c in df_compare.columns if c.endswith("_LA") and 'Arrival Dates' in c]
sa_date_cols = [c for c in df_compare.columns if c.endswith("_SA") and 'Arrival Dates' in c]

# --- availability flags ---
for col in ['Availability_LA', 'Availability_SA']:
    if col in df_compare.columns:
        df_compare[col] = pd.to_numeric(df_compare[col], errors='coerce').fillna(0)

df_compare["Available_LA"] = df_compare["_merge"].isin(["left_only", "both"]) & (
    (df_compare.get("Availability_LA", 0) > 0) |
    df_compare[la_date_cols].notna().any(axis=1)
)

df_compare["Available_SA"] = df_compare["_merge"].isin(["right_only", "both"]) & (
    (df_compare.get("Availability_SA", 0) > 0) |
    df_compare[sa_date_cols].notna().any(axis=1)
)

df_compare["Total_Availability"] = df_compare.get("Availability_LA", 0) + df_compare.get("Availability_SA", 0)

df_compare["Availability_Status"] = np.select(
    [
        df_compare["Available_LA"] & df_compare["Available_SA"],
        df_compare["Available_LA"] & (~df_compare["Available_SA"]),
        (~df_compare["Available_LA"]) & df_compare["Available_SA"]
    ],
    [
        "Available in Both",
        "LA Only",
        "Seattle Only"
    ],
    default="Not Available"
)

# ================= FILTER BOTH_AVAILABLE =================
both_available = df_compare[df_compare["Available_LA"] & df_compare["Available_SA"]].copy()

# --- fill missing size information dynamically ---
for df in [df_compare, both_available]:
    for col in ['SizeDescription_LA', 'SizeDescription_SA', 'Size_LA', 'Size_SA']:
        if col in df.columns:
            df[col] = df[col].replace(['', ' ', 'NaN'], np.nan)
    df["SizeDescription"] = df["SizeDescription_LA"].combine_first(df.get("SizeDescription_SA"))
    df["Size"] = df["Size_LA"].combine_first(df.get("Size_SA"))
    for col in ['SizeDescription_LA', 'SizeDescription_SA']:
        if col in df.columns:
            df[col] = df[col].fillna(df["SizeDescription"])
    for col in ['Size_LA', 'Size_SA']:
        if col in df.columns:
            df[col] = df[col].fillna(df["Size"])

# --- Export directory & file ---
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "warehouse_availability_LA_SEA.xlsx")

# --- Streamlit button for export ---
if st.button("Export Excel"):
    try:
        # --- Export Excel ---
        with pd.ExcelWriter(output_file) as writer:
            df_compare.to_excel(writer, sheet_name="All_Products", index=False)
            both_available.to_excel(writer, sheet_name="Both_Available", index=False)

        st.success(f"Exported successfully! File saved at: {output_file}")

        # --- Download button ---
        with open(output_file, "rb") as f:
            st.download_button(
                "Download Excel File",
                data=f,
                file_name="warehouse_availability_LA_SEA.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error during export: {e}")

