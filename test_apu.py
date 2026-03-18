import requests
from bs4 import BeautifulSoup
import re

def clean_price(text):
    nums = re.findall(r"\d{1,3}(?:[.,]\d{3})*", text)
    if not nums: return 0.0
    for n in nums:
        val = float(n.replace(".", "").replace(",", ""))
        if val > 1000: 
            return val
    return 0.0

def test_scrape():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    # 1. G&J
    print("Testing G&J...")
    try:
        url_gj = "https://gyj.com.co/bogota_65/productos.html"
        res = requests.get(url_gj, headers=headers, timeout=10)
        print(f"G&J Status: {res.status_code}")
        soup = BeautifulSoup(res.text, 'html.parser')
        # Based on subagent research
        for item in soup.select(".col.item"):
            name = item.get_text()
            if "BARRA CORRUGADA 1/2" in name.upper():
                price_box = item.select_one(".price-box .price")
                if price_box:
                    print(f"G&J Steel Found: {name.strip()} -> {price_box.get_text().strip()}")
                    break
    except Exception as e:
        print(f"G&J Error: {e}")

    # 2. Ferretería Ya
    print("\nTesting Ferretería Ya...")
    try:
        # Search for cement
        url_ya_cem = "https://ferreteriaya.com.co/?s=cemento+50kg&post_type=product"
        res = requests.get(url_ya_cem, headers=headers, timeout=10)
        print(f"Ferretería Ya Status: {res.status_code}")
        soup = BeautifulSoup(res.text, 'html.parser')
        for product in soup.select(".product"):
            title = product.select_one(".woocommerce-loop-product__title")
            if title and "50KG" in title.get_text().upper():
                price = product.select_one(".price .amount")
                if price:
                    print(f"Ferretería Ya Cement Found: {title.get_text().strip()} -> {price.get_text().strip()}")
                    break
    except Exception as e:
        print(f"Ferretería Ya Error: {e}")

if __name__ == "__main__":
    test_scrape()
