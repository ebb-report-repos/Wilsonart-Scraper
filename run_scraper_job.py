from main import run_scraper
import pandas as pd
import datetime
import os

def main():
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Run the scraper (NO Streamlit here)
    df_compare, both_available = run_scraper()

    # Save Excel report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output_file = f"output/warehouse_availability_report_{timestamp}.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_compare.to_excel(writer, sheet_name="All Products", index=False)
        both_available.to_excel(writer, sheet_name="Both Available", index=False)

    print(f"✅ Report saved: {output_file}")

if __name__ == "__main__":
    main()
