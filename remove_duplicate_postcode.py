import pandas as pd

# Load your original CSV file
input_file = "extracted_suburbs_postcodes.csv"  # Replace with your input file name
output_file = "clean_postcodes.csv"

df = pd.read_csv(input_file)

# Drop rows where 'PostCode' is duplicated, keeping only the first occurrence
df_unique = df.drop_duplicates(subset=['PostCode'], keep='first')

# Save to the new CSV file
df_unique.to_csv(output_file, index=False)

print(f"Done! Saved {len(df_unique)} unique postcodes to '{output_file}'.")