# app.py
import streamlit as st
import requests

# ----------------------------
# Streamlit Page Config
# ----------------------------
st.set_page_config(page_title="Wilsonart Warehouse Availability", layout="wide")
st.title("Wilsonart Warehouse Availability")

# ----------------------------
# Helper Function: Trigger GitHub Actions Scraper
# ----------------------------
def trigger_github_workflow():
    """
    Trigger the GitHub Actions workflow for the Wilsonart scraper.
    Returns a tuple: (success: bool, message: str)
    """
    try:
        repo = st.secrets.REPO
        token = st.secrets.GITHUB_TOKEN
    except KeyError:
        return False, "❌ GitHub secrets not found. Add REPO and GITHUB_TOKEN to .streamlit/secrets.toml"

    workflow_url = f"https://api.github.com/repos/{repo}/actions/workflows/wilsonart_scraper.yml/dispatches"
    payload = {"ref": "main"}
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }

    try:
        response = requests.post(workflow_url, json=payload, headers=headers)
        if response.status_code == 204:
            return True, (
                "✅ Scraper started successfully!\n\n"
                "The process runs on GitHub and can take up to 2 hours.\n"
                "Once finished, download the Excel report from the Actions artifacts:\n"
                f"https://github.com/{repo}/actions/workflows/wilsonart_scraper.yml"
            )
        else:
            return False, f"❌ Failed to start scraper. Status code: {response.status_code}\nResponse: {response.text}"
    except Exception as e:
        return False, f"❌ Error triggering scraper: {e}"

# ----------------------------
# Run Scraper Section
# ----------------------------
st.header("Run Scraper")
st.markdown(
    "Click the button below to start the warehouse scraper. "
    "This runs asynchronously on GitHub, so you do not need to keep this page open."
)

if st.button("Run Scraper"):
    success, message = trigger_github_workflow()
    if success:
        st.success(message)
    else:
        st.error(message)

# ----------------------------
# Download Instructions Section
# ----------------------------
st.header("Download Latest Report")
st.info(
    "Once the scraper finishes, the Excel report (with two sheets: "
    "`All Products` and `Both Available`) will be available from GitHub Actions artifacts.\n\n"
    "You can download it directly from the workflow run page once the job completes."
)

st.markdown(
    "🔗 [Go to GitHub Actions Artifacts](https://github.com/{repo}/actions/workflows/wilsonart_scraper.yml)"
)


# if st.button("Run Scraper"):
#     response = requests.post(
#         f"https://api.github.com/repos/{st.secrets.REPO}/actions/workflows/wilsonart_scraper.yml/dispatches",
#         headers={
#             "Authorization": f"token {st.secrets.GITHUB_TOKEN}",
#             "Accept": "application/vnd.github+json"
#         },
#         json={"ref": "main"}
#     )

#     if response.status_code == 204:
#         st.success("Scraper started successfully. Check back in ~2 hours.")
#     else:
#         st.error("Failed to start scraper.")


# st.set_page_config(page_title="Wilsonart Warehouse Availability", layout="wide")
# st.title("Wilsonart Warehouse Availability")

# # ----------------------------
# # Session state for persistence
# # ----------------------------
# if "scraper_ran" not in st.session_state:
#     st.session_state.scraper_ran = False
# if "df_compare" not in st.session_state:
#     st.session_state.df_compare = None
# if "both_available" not in st.session_state:
#     st.session_state.both_available = None
# if "log_lines" not in st.session_state:
#     st.session_state.log_lines = []

# # Scrollable log container
# log_container = st.empty()

# def log(message):
#     """Add message to log container and keep it in session state"""
#     st.session_state.log_lines.append(message)
#     log_container.text_area(
#         "Scraper Log",
#         value="\n".join(st.session_state.log_lines),
#         height=250,
#         max_chars=None
#     )

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

#     # ----------------------------
#     # Save Excel to disk
#     # ----------------------------
#     os.makedirs("output", exist_ok=True)
#     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
#     output_file = os.path.join("output", f"warehouse_availability_report_{timestamp}.xlsx")
#     with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
#         st.session_state.df_compare.to_excel(writer, sheet_name="All Products", index=False)
#         st.session_state.both_available.to_excel(writer, sheet_name="Both Available", index=False)

#     # ----------------------------
#     # Prepare in-memory Excel for download (keeps session)
#     # ----------------------------
#     excel_buffer = io.BytesIO()
#     with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
#         st.session_state.df_compare.to_excel(writer, sheet_name="All Products", index=False)
#         st.session_state.both_available.to_excel(writer, sheet_name="Both Available", index=False)
#     excel_buffer.seek(0)

#     st.download_button(
#         label="Download Excel Report",
#         data=excel_buffer,
#         file_name=f"warehouse_availability_report_{timestamp}.xlsx",
#         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )

# # ----------------------------
# # Allow downloading past reports
# # ----------------------------
# st.subheader("Download Past Reports")
# output_folder = "output"
# if os.path.exists(output_folder):
#     output_files = sorted(os.listdir(output_folder), reverse=True)  # newest first
#     if output_files:
#         for file in output_files:
#             file_path = os.path.join(output_folder, file)
#             with open(file_path, "rb") as f:
#                 st.download_button(
#                     label=f"Download {file}",
#                     data=f,
#                     file_name=file,
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#                 )
#     else:
#         st.info("No reports found in the output folder.")
# else:
#     st.info("Output folder does not exist yet.")
