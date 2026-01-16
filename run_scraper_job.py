from main import run_scraper
import pandas as pd
import datetime
import os

def log(msg):
    print(msg)

def main():
    os.makedirs("output", exist_ok=True)

    # Run scraper with logging
    df_compare, both_available = run_scraper(log_callback=log)

    # Save Excel
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    output_file = f"output/warehouse_availability_report_{timestamp}.xlsx"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_compare.to_excel(writer, sheet_name="All Products", index=False)
        both_available.to_excel(writer, sheet_name="Both Available", index=False)

    print(f"✅ Report saved: {output_file}")

if __name__ == "__main__":
    main()
