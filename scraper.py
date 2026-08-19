import re
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def scrape_dzritv():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    matches_data = []

    try:
        main_url = "https://dzritv.com/"
        driver.get(main_url)
        time.sleep(5)

        # পেজ সম্পূর্ণ নিচে স্ক্রোল করে ক্যাটাগরি ও কার্ডগুলো লোড করা
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # পেজের সমস্ত ম্যাচ কার্ড বা লিঙ্ক খোঁজা
        match_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/match/' in href or '/live/' in href or '/stream/' in href or '/watch/' in href:
                full_url = href if href.startswith('http') else f"https://dzritv.com{href}"
                match_links.add(full_url)

        print(f"Total Match Links Found: {len(match_links)}")

        for link in match_links:
            try:
                driver.get(link)
                time.sleep(4)  # প্লেয়ার এবং আইফ্রেম লোড হওয়ার জন্য অপেক্ষা
                
                page_source = driver.page_source
                inner_soup = BeautifulSoup(page_source, 'html.parser')

                # ১. ম্যাচের নাম সংগ্রহ
                title_elem = inner_soup.find('h1') or inner_soup.find('h2') or inner_soup.find('title')
                title = title_elem.get_text(strip=True).replace(" - DZRITV", "").strip() if title_elem else "Live Match"

                # ২. ক্যাটাগরি সংগ্রাহ (যেমন: Cricket, Football, Football Live, etc.)
                category = "General Sports"
                cat_elem = inner_soup.find('span', class_=re.compile(r'category|genre|sport', re.I)) or inner_soup.find('a', class_=re.compile(r'category|genre|sport', re.I))
                if cat_elem:
                    category = cat_elem.get_text(strip=True)

                # ৩. ইমেজ/থাম্বনেইল বের করা
                img_elem = inner_soup.find('img')
                img_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
                if img_url and not img_url.startswith('http'):
                    img_url = f"https://dzritv.com{img_url}"

                # ৪. প্লেয়ার বা স্ট্রিম ইউআরএল শনাক্তকরণ (iFrame, m3u8 বা Embed URL)
                player_url = None
                
                # iFrame থেকে লিংক স্ক্র্যাপ করা
                iframes = inner_soup.find_all('iframe')
                for iframe in iframes:
                    src = iframe.get('src') or iframe.get('data-src')
                    if src and ('player' in src or 'embed' in src or 'stream' in src or 'http' in src):
                        player_url = src if src.startswith('http') else f"https:{src}" if src.startswith('//') else f"https://dzritv.com{src}"
                        break

                # পেজ সোর্সে সরাসরি স্ট্রিম লিংক (.m3u8 / embed) থাকলে
                if not player_url:
                    stream_match = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4))', page_source) or re.search(r'(https?://[^\s"\'<>]+/embed/[^\s"\'<>]+)', page_source)
                    if stream_match:
                        player_url = stream_match.group(1)

                # কেবল প্লেয়ার লিংক পাওয়া গেলে ডাটা যুক্ত হবে
                if player_url:
                    matches_data.append({
                        "match_name": title,
                        "category": category,
                        "image": img_url,
                        "player_url": player_url,
                        "page_url": link
                    })
                    print(f"[FOUND] Category: {category} | Match: {title} | Player: {player_url}")
                else:
                    print(f"[NO PLAYER] Skipping {link}")

            except Exception as e:
                print(f"Error scraping {link}: {e}")

        # JSON ফাইল তৈরি ও ডাটা সেভ
        with open("dzritv_matches.json", "w", encoding="utf-8") as f:
            json.dump(matches_data, f, ensure_ascii=False, indent=2)

        print(f"Successfully saved {len(matches_data)} matches to dzritv_matches.json")

    except Exception as e:
        print(f"Main scraper failed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_dzritv()
