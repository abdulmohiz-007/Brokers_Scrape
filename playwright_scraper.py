import asyncio
import random
import os
import pandas as pd
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from playwright.async_api import async_playwright

# Global lock for CSV writing to prevent data corruption
csv_lock = asyncio.Lock()


class BrokerScraper:
    def __init__(self, input_csv, output_csv):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.ua_factory = UserAgent()

        # Load data
        if os.path.exists(output_csv):
            self.df = pd.read_csv(output_csv)
        else:
            self.df = pd.read_csv(input_csv)
            # Initialize columns if they don't exist
            for col in ["Company Name", "Location", "Phone", "Email", "Languages Spoken", "Education", "Specialties"]:
                if col not in self.df.columns:
                    self.df[col] = ""

    def clean_location(self, raw_text: str) -> str:
        if not raw_text: return ""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return lines[0] if lines else ""

    def extract_bs4(self, html_content):
        """Standard BS4 extraction logic"""
        soup = BeautifulSoup(html_content, "html.parser")
        result = {
            "Company Name": "", "Location": "", "Phone": "",
            "Email": "", "Languages Spoken": "", "Education": "", "Specialties": ""
        }

        broker_details = soup.select_one("div.broker-header div.broker-details")
        if broker_details:
            paragraphs = broker_details.find_all("p")
            for p in paragraphs:
                if p.find("i", class_="fa-location-dot"):
                    location_text = p.get_text(separator="\n", strip=True)
                    result["Location"] = self.clean_location(location_text)
                else:
                    result["Company Name"] = p.get_text(strip=True)

        phone_element = soup.select_one("span#broker-phone-show")
        if phone_element:
            result["Phone"] = phone_element.get("data-phone", "").strip()

        email_element = soup.select_one("span#broker-email-show")
        if email_element:
            result["Email"] = email_element.get("data-email", "").strip()

        lang_element = soup.select_one("div.broker-languages")
        if lang_element:
            lang_span_texts = [span.get_text(strip=True) for span in lang_element.find_all("span") if
                               span.get_text(strip=True)]
            result["Languages Spoken"] = ", ".join(lang_span_texts)

        edu_element = soup.select_one("div.broker-education")
        if edu_element:
            edu_span_texts = [span.get_text(strip=True) for span in edu_element.find_all("span") if
                              span.get_text(strip=True)]
            result["Education"] = ", ".join(edu_span_texts)

        spec_element = soup.select_one("div.broker-services")
        if spec_element:
            span_texts = [span.get_text(strip=True) for span in spec_element.find_all("span") if
                          span.get_text(strip=True)]
            result["Specialties"] = ", ".join(span_texts)

        return result

    async def save_data(self, index, data):
        async with csv_lock:
            for key, value in data.items():
                self.df.at[index, key] = value
            self.df.to_csv(self.output_csv, index=False)

    async def create_browser_instance(self, p):
        """Creates a fresh browser with maximized settings and a new User Agent"""
        ua = self.ua_factory.random
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        # no_viewport=True is required for --start-maximized to work correctly
        context = await browser.new_context(
            ignore_https_errors=True,
            no_viewport=True,
            user_agent=ua
        )
        return browser, context

    async def worker(self, worker_id, queue):
        async with async_playwright() as p:
            request_count = 0
            browser, context = await self.create_browser_instance(p)

            while not queue.empty():
                try:
                    index, url = await queue.get()
                    print(f"Worker {worker_id} processing: {url}")

                    # Delay between requests
                    await asyncio.sleep(random.uniform(2, 5))

                    page = await context.new_page()

                    try:
                        # 1. Load URL
                        await page.goto(url, wait_until="load", timeout=60000)

                        # 2. Wait for specific element
                        selector = 'xpath=//div[@class="breakdance"]//div[@class="breakdance"][1]'
                        await page.wait_for_selector(selector, timeout=10000)

                        # 3. Extract with BS4
                        content = await page.content()
                        data = self.extract_bs4(content)

                        # 4. Save
                        await self.save_data(index, data)
                        print(f"Worker {worker_id} successfully saved index {index}")

                    except Exception as e:
                        print(f"Worker {worker_id} error on {url}: {e}")
                    finally:
                        await page.close()

                    request_count += 1
                    queue.task_done()

                    # Logic for rotating every 100 requests
                    if request_count % 100 == 0:
                        print(f"Worker {worker_id} reached 100 requests. Rotating instance...")
                        await browser.close()

                        long_wait = random.randint(30, 50)
                        print(f"Worker {worker_id} sleeping for {long_wait}s...")
                        await asyncio.sleep(long_wait)

                        # Restart with new UA and fresh session
                        browser, context = await self.create_browser_instance(p)

                except asyncio.CancelledError:
                    break

            await browser.close()

    async def run(self, num_instances=3):
        queue = asyncio.Queue()

        # Only add rows that haven't been processed (optional logic)
        for idx, row in self.df.iterrows():
            if pd.isna(row.get("Email")) or row.get("Email") == "":
                queue.put_nowait((idx, row["Broker URL"]))

        # Start 3 independent browser instances
        workers = [
            asyncio.create_task(self.worker(i, queue))
            for i in range(num_instances)
        ]

        await queue.join()
        for w in workers:
            w.cancel()


if __name__ == "__main__":
    INPUT = "missing_emails_output.csv"
    OUTPUT = "broker_final_details_v3.csv"

    scraper = BrokerScraper(INPUT, OUTPUT)
    asyncio.run(scraper.run(num_instances=3))