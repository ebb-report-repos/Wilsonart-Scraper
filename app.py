import streamlit as st
import pandas as pd
import os
import io
from main import run_scraper  # Your scraping logic wrapped as a function
import datetime


import requests

if st.button("Run Scraper"):
    response = requests.post(
        f"https://api.github.com/repos/{st.secrets.REPO}/actions/workflows/wilsonart_scraper.yml/dispatches",
        headers={
            "Authorization": f"token {st.secrets.GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        },
        json={"ref": "main"}
    )

    if response.status_code == 204:
        st.success("Scraper started successfully. Check back in ~2 hours.")
    else:
        st.error("Failed to start scraper.")


st.set_page_config(page_title="Wilsonart Warehouse Availability", layout="wide")
st.title("Wilsonart Warehouse Availability")

# ----------------------------
# Session state for persistence
# ----------------------------
if "scraper_ran" not in st.session_state:
    st.session_state.scraper_ran = False
if "df_compare" not in st.session_state:
    st.session_state.df_compare = None
if "both_available" not in st.session_state:
    st.session_state.both_available = None
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []

# Scrollable log container
log_container = st.empty()

def log(message):
    """Add message to log container and keep it in session state"""
    st.session_state.log_lines.append(message)
    log_container.text_area(
        "Scraper Log",
        value="\n".join(st.session_state.log_lines),
        height=250,
        max_chars=None
    )

# # ----------------------------
# # Run scraper
# # ----------------------------
# if st.button("Run Scraper") or st.session_state.scraper_ran:
#     if not st.session_state.scraper_ran:
#         st.info("Scraping in progress... this may take a few minutes")
#         with st.spinner("Scraper is running..."):
#             try:
#                 df_compare, both_available = run_scraper(log_callback=log)
#                 st.session_state.df_compare = df_compare
#                 st.session_state.both_available = both_available
#                 st.session_state.scraper_ran = True
#                 st.success("Scraping complete!")
#             except Exception as e:
#                 st.error(f"Scraper failed: {e}")
#                 raise e

#     # ----------------------------
#     # Display results
#     # ----------------------------
#     st.subheader("Full Warehouse Comparison")
#     st.dataframe(st.session_state.df_compare)

#     st.subheader("Products Available in Both LA & Seattle")
#     st.dataframe(st.session_state.both_available)

    # ----------------------------
    # Save Excel to disk
    # ----------------------------
    os.makedirs("output", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output_file = os.path.join("output", f"warehouse_availability_report_{timestamp}.xlsx")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        st.session_state.df_compare.to_excel(writer, sheet_name="All Products", index=False)
        st.session_state.both_available.to_excel(writer, sheet_name="Both Available", index=False)

    # ----------------------------
    # Prepare in-memory Excel for download (keeps session)
    # ----------------------------
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        st.session_state.df_compare.to_excel(writer, sheet_name="All Products", index=False)
        st.session_state.both_available.to_excel(writer, sheet_name="Both Available", index=False)
    excel_buffer.seek(0)

    st.download_button(
        label="Download Excel Report",
        data=excel_buffer,
        file_name=f"warehouse_availability_report_{timestamp}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ----------------------------
# Allow downloading past reports
# ----------------------------
st.subheader("Download Past Reports")
output_folder = "output"
if os.path.exists(output_folder):
    output_files = sorted(os.listdir(output_folder), reverse=True)  # newest first
    if output_files:
        for file in output_files:
            file_path = os.path.join(output_folder, file)
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"Download {file}",
                    data=f,
                    file_name=file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("No reports found in the output folder.")
else:
    st.info("Output folder does not exist yet.")
