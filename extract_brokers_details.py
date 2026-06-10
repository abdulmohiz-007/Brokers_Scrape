import re
import time
import pandas as pd
import requests

from bs4 import BeautifulSoup


class BrokerScraper:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            )
        })

    @staticmethod
    def clean_location(raw_text: str) -> str:
        """
        Examples:

        Springvale, VIC
        1366km away from your search

        -> Springvale, VIC

        Gold Coast, QLD
        15km away from your search

        -> Gold Coast, QLD
        """

        if not raw_text:
            return ""

        lines = [
            line.strip()
            for line in raw_text.splitlines()
            if line.strip()
        ]

        if not lines:
            return ""

        return lines[0]

    def scrape_broker(self, url: str) -> dict:
        result = {
            "Company Name": "",
            "Location": "",
            "Phone": "",
            "Email": "",
        }

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            broker_details = soup.select_one(
                "div.broker-header div.broker-details"
            )

            if broker_details:
                paragraphs = broker_details.find_all("p")

                if len(paragraphs) >= 1:
                    result["Company Name"] = paragraphs[0].get_text(
                        strip=True
                    )

                if len(paragraphs) >= 2:
                    location_text = paragraphs[1].get_text(
                        separator="\n",
                        strip=True
                    )

                    result["Location"] = self.clean_location(
                        location_text
                    )

            phone_element = soup.select_one(
                "span#broker-phone-show"
            )

            if phone_element:
                result["Phone"] = (
                    phone_element.get("data-phone", "")
                    .strip()
                )

            email_element = soup.select_one(
                "span#broker-email-show"
            )

            if email_element:
                result["Email"] = (
                    email_element.get("data-email", "")
                    .strip()
                )

        except Exception as e:
            print(f"Failed: {url} -> {e}")

        return result


def process_csv(
    input_csv: str,
    output_csv: str,
    url_column: str = "Broker URL"
):
    df = pd.read_csv(input_csv).head(200)

    scraper = BrokerScraper()

    if "Company Name" not in df.columns:
        df["Company Name"] = ""

    if "Location" not in df.columns:
        df["Location"] = ""

    if "Phone" not in df.columns:
        df["Phone"] = ""

    if "Email" not in df.columns:
        df["Email"] = ""

    total = len(df)

    for idx, row in df.iterrows():
        url = str(row[url_column]).strip()

        if not url or url.lower() == "nan":
            continue

        print(f"[{idx + 1}/{total}] {url}")

        data = scraper.scrape_broker(url)

        df.at[idx, "Company Name"] = data["Company Name"]
        df.at[idx, "Location"] = data["Location"]
        df.at[idx, "Phone"] = data["Phone"]
        df.at[idx, "Email"] = data["Email"]

        time.sleep(1)

    df.to_csv(output_csv, index=False)
    print(f"Saved: {output_csv}")


if __name__ == "__main__":
    process_csv(
        input_csv="broker_primary_details.csv",
        output_csv="broker_final_details.csv",
        url_column="Broker URL"
    )