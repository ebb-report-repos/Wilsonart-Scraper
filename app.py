import streamlit as st
import pandas as pd
import os
from main import run_scraper  # Your scraping logic wrapped as a function

st.title("Wilsonart Warehouse Availability")

# Create a scrollable log container
log_container = st.empty()
log_lines = []

def log(message):
    """Add message to log container"""
    log_lines.append(message)
    # Display in a small scrollable area
    log_container.text_area("Scraper Log", value="\n".join(log_lines), height=200, max_chars=None)

if st.button("Run Scraper"):
    st.info("Scraping in progress... this may take a few minutes")
    
    # Example: pass log callback to your scraper if needed
    df_compare, both_available = run_scraper(log_callback=log)
    
    st.success("Scraping complete!")
    
    # Show dataframe
    st.dataframe(df_compare)
    
    # Prepare output folder
    os.makedirs("output", exist_ok=True)
    output_file = os.path.join("output", "warehouse_availability_LASAV3.xlsx")
    df_compare.to_excel(output_file, index=False)
    
    # Add download button
    with open(output_file, "rb") as f:
        st.download_button(
            label="Download Excel",
            data=f,
            file_name="warehouse_availability_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
