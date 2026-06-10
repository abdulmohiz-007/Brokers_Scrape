import os
import random
import time
import pandas as pd
from typing import Optional
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("BROKERS_API_KEY")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.7198.97 Safari/537.36 OPR/114.0.5103.75",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
]


class PostcodeScraper:

    SEARCH_INPUT = "//input[@id='location-filter']"
    POSTCODE_OPTION = "//div[@id='fab-autocomplete-results']//button"
    SEARCH_BUTTON = "//button[@type='submit' and contains(text(),'Search')]"
    BROKERS_CARD = "//section[@id='search_results']"

    def __init__(
        self,
        base_url,
        broker_base_url,
        csv_file,
        output_csv,
        headless=False,
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
            c for c in required
            if c not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing columns: {missing}"
            )

        records = df.to_dict("records")

        return records

    def create_context(self, browser):

        ua = random.choice(USER_AGENTS)

        print(f"\nUsing User Agent:\n{ua}\n")

        return browser.new_context(
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080},
            user_agent=ua
        )

    def wait_and_select_postcode(
        self,
        page,
        postcode
    ):

        search_box = page.locator(
            self.SEARCH_INPUT
        )

        search_box.wait_for(
            state="visible",
            timeout=15000
        )

        search_box.click()
        time.sleep(2)
        search_box.fill("")

        search_box.type(
            postcode,
            delay=100
        )

        option = page.locator(
            self.POSTCODE_OPTION
        ).first

        option.wait_for(
            state="visible",
            timeout=10000
        )

        option.click()
        time.sleep(2)

    def perform_search(self, page):

        search_btn = page.locator(
            self.SEARCH_BUTTON
        )

        search_btn.wait_for(
            state="visible",
            timeout=10000
        )

        search_btn.click()
        time.sleep(3)
        cards_section = page.locator(self.BROKERS_CARD)
        cards_section.wait_for(state="visible", timeout=20000)

    def extract_via_browser_context(
        self,
        page
    ) -> Optional[dict]:

        try:

            page.wait_for_function(
                """
                () => {
                    if (
                        typeof hb_fab_map === 'undefined'
                    ) {
                        return false;
                    }

                    return (
                        hb_fab_map.brokerLocations &&
                        hb_fab_map.brokerLocations.length > 0
                    );
                }
                """,
                timeout=30000
            )

            return page.evaluate(
                """
                () => {
                    if (
                        typeof hb_fab_map !== 'undefined'
                    ) {
                        return hb_fab_map;
                    }

                    if (window.hb_fab_map) {
                        return window.hb_fab_map;
                    }

                    return null;
                }
                """
            )

        except Exception as e:

            print(
                f"Browser extraction failed: {e}"
            )

            return None

    def extract_brokers(
        self,
        data: dict,
        suburb: str,
        state: str,
        postcode: str,
    ):

        rows = []

        broker_locations = data.get(
            "brokerLocations",
            []
        )

        for broker in broker_locations:

            try:

                card_html = broker.get(
                    "card",
                    ""
                )

                if not card_html:
                    continue

                soup = BeautifulSoup(
                    card_html,
                    "html.parser"
                )

                broker_name_el = soup.select_one(
                    "p.broker-name"
                )

                broker_name = (
                    broker_name_el.get_text(strip=True)
                    if broker_name_el
                    else ""
                )

                profile_link = soup.select_one(
                    "a.button"
                )

                href = ""

                if profile_link:
                    href = profile_link.get(
                        "href",
                        ""
                    )

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

        if data is None:
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

        total_brokers = 0

        proxy_settings = {
            "server": "http://proxy.scrapingbee.com:8886",
            "username": api_key,
            "password": "premium_proxy=true&country_code=au&render_js=false"
        }

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=self.headless,
                args=["--start-maximized","--disable-http2"],
                proxy = proxy_settings,

            )


            context = self.create_context(
                browser
            )

            page = context.new_page()
            page.set_default_timeout(60000)

            for idx, row in enumerate(
                inputs,
                start=1
            ):

                if idx % 50 == 0:
                    time.sleep(random.randint(5,10))
                    print(
                        "\nRotating User Agent..."
                    )

                    page.close()
                    context.close()

                    context = self.create_context(
                        browser
                    )

                    page = context.new_page()
                    page.set_default_timeout(60000)

                suburb = row["Suburb"]
                state = row["State"]
                postcode = str(
                    row["PostCode"]
                )

                try:
                    time.sleep(random.randint(4,10))
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

                    total_brokers += len(
                        broker_rows
                    )

                    print(
                        f"{postcode}: "
                        f"{len(broker_rows)} brokers"
                    )

                except PlaywrightTimeoutError:

                    print(
                        f"{postcode}: timeout"
                    )

                except Exception as e:

                    print(
                        f"{postcode}: {e}"
                    )

            context.close()
            browser.close()

        return total_brokers

if __name__ == "__main__":
    scraper = PostcodeScraper(
        base_url="https://findabroker.mfaa.com.au/find-accredited-broker/",
        broker_base_url="https://findabroker.mfaa.com.au/",
        csv_file="clean_postcodes.csv",
        output_csv="broker_primary_details.csv",
        headless=False
    )

    total_brokers = scraper.run()

    print(
        f"\nCompleted. "
        f"Total Brokers: {total_brokers}"
    )