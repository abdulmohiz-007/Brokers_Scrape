import requests

# Put your key here
API_KEY = ""
url = "https://app.scrapingbee.com/api/v1/usage" # Check usage endpoint

response = requests.get(f"https://app.scrapingbee.com/api/v1/?api_key={API_KEY}&url=https://httpbin.org/ip")

if response.status_code == 401:
    print("STATUS 401: You are OUT of credits or the API Key is wrong.")
elif response.status_code == 200:
    print("STATUS 200: Proxy is working perfectly!")
else:
    print(f"STATUS {response.status_code}: Something else happened. Response: {response.text}")