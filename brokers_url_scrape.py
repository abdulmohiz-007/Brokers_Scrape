import os
import re
import json
import time
import pandas as pd

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class PostcodeScraper:
    SEARCH_INPUT = "//input[@id='location-filter']"
    POSTCODE_OPTION = "//div[@id='fab-autocomplete-results']//button"
    SEARCH_BUTTON = "//button[@type='submit' and contains(text(), 'Search')]"

    def __init__(
            self,
            base_url,
            broker_base_url,
            csv_file,
            output_csv,
            headless=False
    ):
        self.base_url = base_url
        self.broker_base_url = broker_base_url
        self.csv_file = csv_file
        self.output_csv = output_csv
        self.headless = headless

    def load_input_data(self):

        df = pd.read_csv(self.csv_file)

        required = [
            "Suburb",
            "State",
            "PostCode"
        ]

        missing = [
            col for col in required
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing columns: {missing}"
            )

        return df.to_dict("records")

    def wait_and_select_postcode(self, page, postcode):
        """
        Type postcode and wait for autocomplete results.
        """

        search_box = page.locator(self.SEARCH_INPUT)

        search_box.wait_for(state="visible", timeout=15000)

        search_box.click()
        time.sleep(3)
        search_box.fill("")

        # More realistic typing
        search_box.type(postcode, delay=100)
        time.sleep(3)

        option = page.locator(self.POSTCODE_OPTION).first

        option.wait_for(
            state="visible",
            timeout=20000
        )

        option.click()
        time.sleep(3)

    def perform_search(self, page):
        search_btn = page.locator(self.SEARCH_BUTTON)

        search_btn.wait_for(
            state="visible",
            timeout=10000
        )

        search_btn.click()

        # Wait for navigation/network
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_load_state("networkidle")

    def extract_js_data(self, page):
        """
        Attempts multiple extraction methods.
        """

        html = page.content()

        patterns = [
            r"const\s+hb_fab_map\s*=\s*(\{.*?\});",
            r"let\s+hb_fab_map\s*=\s*(\{.*?\});",
            r"var\s+hb_fab_map\s*=\s*(\{.*?\});",
            r"hb_fab_map\s*=\s*(\{.*?\});",
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                re.DOTALL
            )

            if not match:
                continue

            try:
                return json.loads(match.group(1))
            except Exception as e:
                print(f"JSON parse failed: {e}")

        return None

    def extract_via_browser_context(self, page):
        """
        Fallback:
        Check if object exists in JS runtime.
        """

        try:
            data = page.evaluate("""
            () => {
                if (typeof hb_fab_map !== 'undefined')
                    return hb_fab_map;

                if (window.hb_fab_map)
                    return window.hb_fab_map;

                return null;
            }
            """)

            return data

        except Exception as e:
            print(f"Browser extraction failed: {e}")
            return None

    def extract_brokers(
            self,
            data: dict,
            suburb: str,
            state: str,
            postcode: str,
    ):
        """
        Extract all brokers from hb_fab_map.
        """

        rows = []

        broker_locations = data.get("brokerLocations", [])

        for broker in broker_locations:

            card_html = broker.get("card", "")

            if not card_html:
                continue

            try:
                soup = BeautifulSoup(card_html, "html.parser")

                # Broker Name
                broker_name_el = soup.select_one(
                    "p.broker-name"
                )

                broker_name = (
                    broker_name_el.get_text(strip=True)
                    if broker_name_el
                    else ""
                )


                # Broker URL
                profile_link = soup.select_one(
                    "a.button"
                )

                href = ""

                if profile_link:
                    href = profile_link.get("href", "")

                broker_url = urljoin(
                    self.broker_base_url,
                    href
                )

                rows.append(
                    {
                        "Suburb": suburb,
                        "State": state,
                        "PostCode": postcode,
                        "Broker Name": broker_name,
                        "Broker URL": broker_url,
                    }
                )

            except Exception as e:
                print(
                    f"Broker parse failed: {e}"
                )

        return rows


    def append_to_csv(self, rows):

        if not rows:
            return

        df = pd.DataFrame(rows)

        file_exists = os.path.exists(
            self.output_csv
        )

        df.to_csv(
            self.output_csv,
            mode="a",
            header=not file_exists,
            index=False
        )

    def process_postcode(
            self,
            page,
            suburb,
            state,
            postcode
    ):

        page.goto(self.base_url)

        self.wait_and_select_postcode(
            page,
            postcode
        )

        self.perform_search(page)

        data = self.extract_via_browser_context(
            page
        )

        if not data:
            return []

        rows = self.extract_brokers(
            data=data,
            suburb=suburb,
            state=state,
            postcode=postcode
        )

        return rows
    def run(self):

        inputs = self.load_input_data()
        inputs= inputs[:1]

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=self.headless
            )

            context = browser.new_context()

            page = context.new_page()

            for row in inputs:

                suburb = row["Suburb"]
                state = row["State"]
                postcode = str(row["PostCode"])

                try:

                    broker_rows = (
                        self.process_postcode(
                            page,
                            suburb,
                            state,
                            postcode
                        )
                    )

                    self.append_to_csv(
                        broker_rows
                    )

                    print(
                        f"{postcode}: "
                        f"{len(broker_rows)} brokers"
                    )

                except Exception as e:

                    print(
                        f"{postcode} failed: {e}"
                    )

            browser.close()

if __name__ == "__main__":
    scraper = PostcodeScraper(
        base_url="https://findabroker.mfaa.com.au/find-accredited-broker/",
        broker_base_url="https://findabroker.mfaa.com.au/",
        csv_file="extracted_suburbs_postcodes.csv",
        output_csv="broker_primary_details.csv",
        headless=False
    )

    results = scraper.run()

    print(
        f"\nCompleted. Total Results: "
        f"{len(results)}"
    )