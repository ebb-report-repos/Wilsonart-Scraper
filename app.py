import streamlit as st
import pandas as pd
import os
from main import run_scraper  # We'll modify main.py minimally to expose a function

st.title("Wilsonart Warehouse Availability")

if st.button("Run Scraper"):
    st.info("Scraping in progress... this may take a few minutes")
    df_compare, both_available = run_scraper()  # call main logic
    st.success("Scraping complete!")

    st.dataframe(df_compare)
    
    # Optionally allow download
    output_file = os.path.join("output", "warehouse_availability_LASAV3.xlsx")
    df_compare.to_excel(output_file, index=False)
    st.download_button("Download Excel", data=open(output_file, "rb"), file_name="warehouse_availability_LASAV3.xlsx")
