import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from scrapingbee import ScrapingBeeClient
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import pandas as pd

write_lock = Lock()
load_dotenv()

# Load API Key from .env
API_KEY = os.getenv("BROKERS_API_KEY")


class BrokerScraper:
    def __init__(self, api_key):
        # Initialize the official ScrapingBee Client
        self.client = ScrapingBeeClient(api_key=api_key)

    @staticmethod
    def clean_location(raw_text: str) -> str:
        if not raw_text: return ""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return lines[0] if lines else ""

    def scrape_broker(self, url_info: tuple) -> tuple:
        """
        url_info is (index, url)
        Returns (index, data_dict) to preserve order
        """
        index, url = url_info

        result = {
            "Company Name": "",
            "Location": "",
            "Phone": "",
            "Email": "",
            "Languages Spoken": "",
            "Education": "",
            "Specialties": ""
        }

        if not url or str(url).lower() == "nan":
            return index, result

        try:
            # Use the ScrapingBee Client to make the request
            # This handles the proxy, rotation, and geolocation automatically
            response = self.client.get(
                url,
                params={
                    "country_code": "au",  # Browse from Australia
                    "premium_proxy": "True",  # Use Residential IPs (highly recommended for MFAA)
                    "render_js": "False",  # Fast and cheap (no JS needed for the profile page)
                    "timeout": 30000  # 30 seconds timeout
                }
            )

            # Check if the request was successful
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # 1. Company vs Location logic
                broker_details = soup.select_one("div.broker-header div.broker-details")
                if broker_details:
                    paragraphs = broker_details.find_all("p")
                    for p in paragraphs:
                        if p.find("i", class_="fa-location-dot"):
                            location_text = p.get_text(separator="\n", strip=True)
                            result["Location"] = self.clean_location(location_text)
                        else:
                            result["Company Name"] = p.get_text(strip=True)

                # 2. Phone (stored in data-phone attribute)
                phone_element = soup.select_one("span#broker-phone-show")
                if phone_element:
                    result["Phone"] = phone_element.get("data-phone", "").strip()

                # 3. Email (stored in data-email attribute)
                email_element = soup.select_one("span#broker-email-show")
                if email_element:
                    result["Email"] = email_element.get("data-email", "").strip()

                # 4. Languages
                lang_element = soup.select_one("div.broker-languages")
                if lang_element:
                    lang_span_texts = [span.get_text(strip=True) for span in lang_element.find_all("span") if
                                       span.get_text(strip=True)]
                    result["Languages Spoken"] = ", ".join(lang_span_texts)

                # 5. Education
                edu_element = soup.select_one("div.broker-education")
                if edu_element:
                    edu_span_texts = [span.get_text(strip=True) for span in edu_element.find_all("span") if
                                      span.get_text(strip=True)]
                    result["Education"] = ", ".join(edu_span_texts)

                # 6. Specialties
                spec_element = soup.select_one("div.broker-services")
                if spec_element:
                    span_texts = [span.get_text(strip=True) for span in spec_element.find_all("span") if
                                  span.get_text(strip=True)]
                    result["Specialties"] = ", ".join(span_texts)

                print(f"Success [{index}]: {url}")
            else:
                print(f"Failed [{index}]: {url} -> Status Code: {response.status_code}")

        except Exception as e:
            print(f"Error [{index}]: {url} -> {e}")

        return index, result


def run_parallel_scraper(input_csv, output_csv, max_threads=5):

    # Resume mode if output already exists
    if os.path.exists(output_csv):
        print(f"Resuming from existing output file: {output_csv}")
        df = pd.read_csv(output_csv, dtype=str).fillna("")
    else:
        print(f"Creating new output file from: {input_csv}")
        df = pd.read_csv(input_csv, dtype=str).fillna("")

        required_columns = [
            "Company Name",
            "Location",
            "Phone",
            "Email",
            "Languages Spoken",
            "Education",
            "Specialties"
        ]

        for col in required_columns:
            if col not in df.columns:
                df[col] = ""

        df.to_csv(output_csv, index=False)

    scraper = BrokerScraper(api_key=API_KEY)

    tasks = []

    for idx, row in df.iterrows():

        email = str(row.get("Email", "")).strip()
        phone = str(row.get("Phone", "")).strip()

        # Skip rows already completed
        if email and phone:
            continue

        broker_url = str(row.get("Broker URL", "")).strip()

        if broker_url:
            tasks.append((idx, broker_url))

    print(
        f"Found {len(tasks)} incomplete brokers out of {len(df)} total rows."
    )

    if not tasks:
        print("Nothing left to scrape.")
        return

    with ThreadPoolExecutor(max_workers=max_threads) as executor:

        for index, data in executor.map(
            scraper.scrape_broker,
            tasks
        ):

            with write_lock:

                for column_name, value in data.items():

                    # Only overwrite if we got a value
                    if str(value).strip():
                        df.at[index, column_name] = value

                df.to_csv(
                    output_csv,
                    index=False
                )

                print(
                    f"Saved row {index + 1}/{len(df)}"
                )

    print(f"Done! Saved to: {output_csv}")

if __name__ == "__main__":
    run_parallel_scraper(
        input_csv="Total_Unique_Urls.csv",
        output_csv="Total_unique_emails.csv",
        max_threads=5  # Adjust this based on your ScrapingBee concurrency limit
    )