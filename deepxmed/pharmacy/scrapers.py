# pharmacy/scrapers.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time
import random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

def _sleep():
    time.sleep(0.6 + random.random() * 0.8)  # polite pause

def search_1mg(medicine_name):
    """
    Search 1mg for a medicine. Returns list of offers:
    [{'source':'1mg','title':'...','price': 299.0,'link':'https://...','delivery': '₹40' or ''}, ...]
    """
    results = []
    try:
        q = quote_plus(medicine_name)
        url = f"https://www.1mg.com/search/all?name={q}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return results
        soup = BeautifulSoup(r.text, "html.parser")

        # 1mg uses product cards with anchor tags - this is a best-effort selector
        cards = soup.select("li[class*='style__product-list-item'] a, div[class*='listing-product'] a")
        seen = set()
        for a in cards[:6]:
            title = a.get_text(separator=" ", strip=True)
            href = a.get('href') or ''
            if href and not href.startswith("http"):
                href = "https://www.1mg.com" + href
            # attempt to find price within anchor or sibling
            price_tag = a.select_one(".price, span[class*='price']")
            # fallback: search parent for price
            if not price_tag:
                parent = a.parent
                price_tag = parent.select_one("span[class*='rupee'], span[class*='price']")
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            # parse price numeric
            price_val = None
            try:
                price_val = float("".join(ch for ch in price_text if ch.isdigit() or ch == '.'))
            except:
                price_val = None

            if title and href and (href not in seen):
                seen.add(href)
                results.append({
                    "source": "1mg",
                    "title": title,
                    "price": price_val,
                    "link": href,
                    "delivery": "", 
                })
            if len(results) >= 5:
                break
        _sleep()
    except Exception:
        pass
    return results

def search_pharmeasy(medicine_name):
    """
    Search PharmEasy for medicine. Best-effort scraping.
    """
    results = []
    try:
        q = quote_plus(medicine_name)
        url = f"https://pharmeasy.in/search/all?search={q}"
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return results
        soup = BeautifulSoup(r.text, "html.parser")

        cards = soup.select("a[data-qa='product-name'], div.ProductCard a")
        seen = set()
        for a in cards[:6]:
            title = a.get_text(separator=" ", strip=True)
            href = a.get('href') or ''
            if href and not href.startswith("http"):
                href = "https://pharmeasy.in" + href
            # price selection
            price_tag = a.select_one(".mrp, .price, span[data-qa='price']")
            if not price_tag:
                parent = a.parent
                price_tag = parent.select_one("span[data-qa='price']")
            price_text = price_tag.get_text(strip=True) if price_tag else ""
            try:
                price_val = float("".join(ch for ch in price_text if ch.isdigit() or ch == '.'))
            except:
                price_val = None

            if title and href and (href not in seen):
                seen.add(href)
                results.append({
                    "source": "PharmEasy",
                    "title": title,
                    "price": price_val,
                    "link": href,
                    "delivery": "",
                })
            if len(results) >= 5:
                break
        _sleep()
    except Exception:
        pass
    return results

def aggregate_offers(medicine_name):
    """
    Call multiple scrapers and merge results (deduplicate by link/title).
    """
    all_offers = []
    sources = [search_1mg, search_pharmeasy]
    for fn in sources:
        try:
            offers = fn(medicine_name)
            if offers:
                all_offers.extend(offers)
        except Exception:
            continue

    # normalize price sorting (lowest first), filter None prices to end
    all_offers_sorted = sorted(
        all_offers,
        key=lambda x: (x.get("price") is None, x.get("price") if x.get("price") is not None else 1e9)
    )
    return all_offers_sorted
