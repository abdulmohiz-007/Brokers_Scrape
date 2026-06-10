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
            "Languages Spoken": "",
            "Education": "",
            "Specialties": ""
        }

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 1. Dynamically identify Company vs Location using the 'fa-location-dot' icon
            broker_details = soup.select_one("div.broker-header div.broker-details")
            if broker_details:
                paragraphs = broker_details.find_all("p")
                for p in paragraphs:
                    if p.find("i", class_="fa-location-dot"):
                        location_text = p.get_text(separator="\n", strip=True)
                        result["Location"] = self.clean_location(location_text)
                    else:
                        result["Company Name"] = p.get_text(strip=True)

            # 2. Phone
            phone_element = soup.select_one("span#broker-phone-show")
            if phone_element:
                result["Phone"] = phone_element.get("data-phone", "").strip()

            # 3. Email
            email_element = soup.select_one("span#broker-email-show")
            if email_element:
                result["Email"] = email_element.get("data-email", "").strip()

            # 4. Languages Spoken
            lang_element = soup.select_one("div.broker-languages")
            if lang_element:
                lang_spans = lang_element.find_all("span")
                lang_span_texts = [span.get_text(strip=True) for span in lang_spans if span.get_text(strip=True)]
                result["Languages Spoken"] = ", ".join(lang_span_texts)


            # 5. Education
            edu_element = soup.select_one("div.broker-education")
            if edu_element:
                edu_spans = edu_element.find_all("span")
                edu_span_texts = [span.get_text(strip=True) for span in edu_spans if span.get_text(strip=True)]
                result["Education"] = ", ".join(edu_span_texts)


            # 6. Specialties (joins all inner spans with a comma)
            spec_element = soup.select_one("div.broker-services")
            if spec_element:
                spans = spec_element.find_all("span")
                span_texts = [span.get_text(strip=True) for span in spans if span.get_text(strip=True)]
                result["Specialties"] = ", ".join(span_texts)

        except Exception as e:
            print(f"Failed: {url} -> {e}")

        return result


def process_csv(
    input_csv: str,
    output_csv: str,
    url_column: str = "Broker URL"
):
    df = pd.read_csv(input_csv).head(20)

    scraper = BrokerScraper()

    target_columns = [
        "Company Name", "Location", "Phone", "Email",
        "Languages Spoken", "Education", "Specialties"
    ]
    for col in target_columns:
        if col not in df.columns:
            df[col] = ""

    total = len(df)

    for idx, row in df.iterrows():
        url = str(row[url_column]).strip()

        if not url or url.lower() == "nan":
            continue

        print(f"[{idx + 1}/{total}] {url}")

        data = scraper.scrape_broker(url)

        for col in target_columns:
            df.at[idx, col] = data[col]

        time.sleep(1)

    df.to_csv(output_csv, index=False)
    print(f"Saved: {output_csv}")


if __name__ == "__main__":
    process_csv(
        input_csv="broker_primary_details.csv",
        output_csv="broker_final_details.csv",
        url_column="Broker URL"
    )