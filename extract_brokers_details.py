import os
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import pandas as pd

write_lock = Lock()



class BrokerScraper:
    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        })

    @staticmethod
    def clean_location(raw_text: str) -> str:
        if not raw_text: return ""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return lines[0] if lines else ""

    def scrape_broker(self, url_info: tuple) -> tuple:
        """
        url_info is (index, url)
        Returns (index, data_dict)
        """

        import time
        import random

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

            response = None

            for attempt in range(3):

                try:

                    # Stagger requests between threads
                    time.sleep(random.uniform(0.5, 2.0))

                    response = self.session.get(
                        url,
                        timeout=30
                    )

                    if response.status_code == 200:
                        break

                    print(
                        f"Retry {attempt + 1} "
                        f"[{index}] "
                        f"Status={response.status_code}"
                    )

                except Exception as e:

                    print(
                        f"Retry {attempt + 1} "
                        f"[{index}] "
                        f"{e}"
                    )

                time.sleep((attempt + 1) * 2)

            if not response or response.status_code != 200:
                print(
                    f"Failed [{index}]: "
                    f"{url}"
                )

                return index, result

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            # Validate page
            broker_header = soup.select_one(
                "div.broker-header"
            )

            if not broker_header:
                print(
                    f"Invalid page [{index}]: "
                    f"{url}"
                )

                return index, result

            # Company + Location
            broker_details = soup.select_one(
                "div.broker-header div.broker-details"
            )

            if broker_details:

                paragraphs = broker_details.find_all("p")

                for p in paragraphs:

                    if p.find("i", class_="fa-location-dot"):

                        location_text = p.get_text(
                            separator="\n",
                            strip=True
                        )

                        result["Location"] = self.clean_location(
                            location_text
                        )

                    else:

                        text = p.get_text(
                            strip=True
                        )

                        if text:
                            result["Company Name"] = text

            # Phone
            phone_element = soup.select_one(
                "span#broker-phone-show"
            )

            if phone_element:
                result["Phone"] = (
                    phone_element.get(
                        "data-phone",
                        ""
                    ).strip()
                )

            # Email
            email_element = soup.select_one(
                "span#broker-email-show"
            )

            if email_element:
                result["Email"] = (
                    email_element.get(
                        "data-email",
                        ""
                    ).strip()
                )

            # Languages
            lang_element = soup.select_one(
                "div.broker-languages"
            )

            if lang_element:
                lang_values = [
                    span.get_text(strip=True)
                    for span in lang_element.find_all("span")
                    if span.get_text(strip=True)
                ]

                result["Languages Spoken"] = (
                    ", ".join(lang_values)
                )

            # Education
            edu_element = soup.select_one(
                "div.broker-education"
            )

            if edu_element:
                edu_values = [
                    span.get_text(strip=True)
                    for span in edu_element.find_all("span")
                    if span.get_text(strip=True)
                ]

                result["Education"] = (
                    ", ".join(edu_values)
                )

            # Specialties
            spec_element = soup.select_one(
                "div.broker-services"
            )

            if spec_element:
                spec_values = [
                    span.get_text(strip=True)
                    for span in spec_element.find_all("span")
                    if span.get_text(strip=True)
                ]

                result["Specialties"] = (
                    ", ".join(spec_values)
                )

            print(
                f"Success [{index}] "
                f"Phone={bool(result['Phone'])} "
                f"Email={bool(result['Email'])}"
            )

        except Exception as e:

            print(
                f"Error [{index}] "
                f"{url} -> {e}"
            )

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

    scraper = BrokerScraper()

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