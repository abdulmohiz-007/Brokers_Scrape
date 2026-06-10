import re
import csv
from pypdf import PdfReader


def extract_to_csv(pdf_path, output_csv_path):
    # Initialize the PDF reader
    reader = PdfReader(pdf_path)
    combined_text = ""

    # Extract text from all pages
    for page in reader.pages:
        text = page.extract_text()
        if text:
            combined_text += text + "\n"

    # Regex pattern:
    # Group 1 = Suburb (Caps & spaces), Group 2 = State, Group 3 = 4-digit Postcode
    pattern = r'\b([A-Z][A-Z\s]+?)\s+([A-Z]{2,3})\s+(\d{4})\b'

    # Find all matches
    matches = re.findall(pattern, combined_text)

    # Export to CSV
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['Suburb', 'State', 'PostCode']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

        # Write headers
        writer.writeheader()

        # Write rows
        count = 0
        for match in matches:
            writer.writerow({
                "Suburb": match[0].strip(),
                "State": match[1],
                "PostCode": match[2]
            })
            count += 1

    print(f"Extraction complete! Successfully exported {count} records to '{output_csv_path}'.")


# --- Run the program ---
pdf_file = "Postcodes.pdf"  # Replace with your PDF path
csv_file = "extracted_suburbs_postcodes.csv"

try:
    extract_to_csv(pdf_file, csv_file)
except Exception as e:
    print(f"An error occurred: {e}")