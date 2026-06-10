import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright




def test_scrapingbee_https():
    proxy_settings = {
        "server": "http://proxy.scrapingbee.com:8886",
        "username": API_KEY,
        "password": "premium_proxy=true&country_code=au&render_js=false"
    }

    with sync_playwright() as p:
        print("Launching browser...")

        browser = p.chromium.launch(
            headless=False,
            proxy=proxy_settings,
            args=["--disable-http2"]
        )

        # --- THE CRITICAL PART ---
        # ignore_https_errors=True tells Playwright:
        # "I know the proxy is intercepting the connection, proceed anyway."
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        try:
            # Now we use HTTPS safely
            print("Visiting HTTPS site via Premium AU Proxy...")
            page.goto("https://whatismyipaddress.com/", timeout=60000)
            time.sleep(2)
            page.goto("https://findabroker.mfaa.com.au/find-accredited-broker/", timeout=60000)

            ip_address = page.locator("body").inner_text().strip()

            print(f"\nSUCCESS! Your Secure Proxy IP is: {ip_address}")
            print("The 'Not Secure' warning in the browser window can be ignored.")

            page.wait_for_timeout(5000)

        except Exception as e:
            print(f"\nError: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    test_scrapingbee_https()