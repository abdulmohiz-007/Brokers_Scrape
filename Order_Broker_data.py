import pandas as pd
import numpy as np


def fix_misaligned_data(input_csv: str, output_csv: str):
    # Load the CSV file
    df = pd.read_csv(input_csv)

    # Check if required columns exist in the CSV
    if "Company Name" not in df.columns or "Location" not in df.columns:
        raise ValueError("The input CSV must contain both 'Company Name' and 'Location' columns.")

    # Create a boolean condition (mask) where:
    # 1. Location is missing/null/empty string
    # 2. Company Name is NOT missing/null/empty string
    is_location_empty = df["Location"].isna() | (df["Location"].astype(str).str.strip() == "")
    has_company_name = df["Company Name"].notna() & (df["Company Name"].astype(str).str.strip() != "")

    wrong_data_mask = is_location_empty & has_company_name

    # Track how many rows we are going to fix
    affected_rows_count = wrong_data_mask.sum()

    if affected_rows_count > 0:
        # Move the value from 'Company Name' to 'Location' for those specific rows
        df.loc[wrong_data_mask, "Location"] = df.loc[wrong_data_mask, "Company Name"]

        # Clear the 'Company Name' field for those rows (setting it to an empty string)
        df.loc[wrong_data_mask, "Company Name"] = ""

        print(f"Success! Fixed {affected_rows_count} rows where location was shifted into the company name.")
    else:
        print("No mismatched rows were found. No changes needed.")

    # Save the corrected data to a new CSV, preserving all original columns
    df.to_csv(output_csv, index=False)
    print(f"Saved the corrected data to: {output_csv}")


# --- Example Usage ---
input_file = "broker_final_details.csv"  # Replace with your actual input file path
output_file = "broker_ordered_details.csv"  # The clean file that will be created

fix_misaligned_data(input_file, output_file)