import streamlit as st
import pandas as pd
import os
import io
from main import run_scraper  # Your scraping logic wrapped as a function
import datetime
st.set_page_config(page_title="Wilsonart Warehouse Availability", layout="wide")
st.title("Wilsonart Warehouse Availability")

# Scrollable log container
log_container = st.empty()
log_lines = []

def log(message):
    """Add message to log container"""
    log_lines.append(message)
    log_container.text_area("Scraper Log", value="\n".join(log_lines), height=250, max_chars=None)

if st.button("Run Scraper"):
    st.info("Scraping in progress... this may take a few minutes")

    # Use spinner while scraping
    with st.spinner("Scraper is running..."):
        try:
            df_compare, both_available = run_scraper(log_callback=log)
            st.success("Scraping complete!")
        except Exception as e:
            st.error(f"Scraper failed: {e}")
            raise e

    # Display main dataframe
    st.subheader("Full Warehouse Comparison")
    st.dataframe(df_compare)

    # Display both-available products
    st.subheader("Products Available in Both LA & Seattle")
    st.dataframe(both_available)
    # Prepare output folder and save Excel
    os.makedirs("output", exist_ok=True)
    
    # Short timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")  # e.g., 20260113_1532
    
    # Output filename with timestamp
    output_file = os.path.join("output", f"warehouse_availability_report_{timestamp}.xlsx")
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:  # switched from xlsxwriter
        df_compare.to_excel(writer, sheet_name="All Products", index=False)
        both_available.to_excel(writer, sheet_name="Both Available", index=False)
    
    # # Add download button with timestamp in filename
    # with open(output_file, "rb") as f:
    #     st.download_button(
    #         label="Download Excel Report",
    #         data=f,
    #         file_name=f"warehouse_availability_report_{timestamp}.xlsx",
    #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    #     )
    
    # st.info("Excel report generated and ready to download.")


    # Add download button with timestamp in filename (using in-memory Excel for reliability)
    
    
    # Prepare Excel in memory
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_compare.to_excel(writer, sheet_name="All Products", index=False)
        both_available.to_excel(writer, sheet_name="Both Available", index=False)
    excel_buffer.seek(0)  # Move pointer to the start
    
    # Show download button immediately
    st.download_button(
        label="Download Excel Report",
        data=excel_buffer,
        file_name=f"warehouse_availability_report_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Inform user that file is ready and also saved on disk
    st.info(f"Excel report saved to disk at: {output_file} and ready to download.")


    # # Prepare output folder and save Excel
    # os.makedirs("output", exist_ok=True)
    # output_file = os.path.join("output", "warehouse_availability_report.xlsx")
    # with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    #     df_compare.to_excel(writer, sheet_name="All Products", index=False)
    #     both_available.to_excel(writer, sheet_name="Both Available", index=False)

    # # Add download button
    # with open(output_file, "rb") as f:
    #     st.download_button(
    #         label="Download Excel Report",
    #         data=f,
    #         file_name="warehouse_availability_report.xlsx",
    #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    #     )

    # st.info("Excel report generated and ready to download.")
