import re
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def scrape_dzritv_m3u8():
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

        # পেজ সম্পূর্ণ নিচে স্ক্রোল করে ক্যাটাগরি ও ম্যাচ কার্ডগুলো লোড করা
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # পেজের সমস্ত লাইভ ম্যাচ লিংক সংগ্রহ করা
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
                time.sleep(5)  # M3U8 ডায়নামিক লিংক লোড হওয়ার জন্য সময়
                
                page_source = driver.page_source
                inner_soup = BeautifulSoup(page_source, 'html.parser')

                # ১. ম্যাচের নাম বের করা
                title_elem = inner_soup.find('h1') or inner_soup.find('h2') or inner_soup.find('title')
                title = title_elem.get_text(strip=True).replace(" - DZRITV", "").strip() if title_elem else "Live Match"

                # ২. ক্যাটাগরি বের করা
                category = "Sports"
                cat_elem = inner_soup.find('span', class_=re.compile(r'category|genre|sport', re.I)) or inner_soup.find('a', class_=re.compile(r'category|genre|sport', re.I))
                if cat_elem:
                    category = cat_elem.get_text(strip=True)

                # ৩. ইমেজ/থাম্বনেইল বের করা
                img_elem = inner_soup.find('img')
                img_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else ""
                if img_url and not img_url.startswith('http'):
                    img_url = f"https://dzritv.com{img_url}"

                # ৪. সরাসরি M3U8 স্ট্রিম লিংক (যেমন: wmsAuthSign সহ) ফিল্টার করা
                player_url = None
                
                # RegEx ব্যবহার করে .m3u8 ও Authentication Token সহ পূর্ণাঙ্গ URL অনুসন্ধান
                m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', page_source)
                
                if m3u8_match:
                    player_url = m3u8_match.group(1)
                else:
                    # যদি iFrame এর ভেতর M3U8 রিডাইরেক্ট লিংক থাকে
                    iframes = inner_soup.find_all('iframe')
                    for iframe in iframes:
                        src = iframe.get('src') or iframe.get('data-src')
                        if src:
                            full_iframe_url = src if src.startswith('http') else f"https:{src}" if src.startswith('//') else f"https://dzritv.com{src}"
                            try:
                                # iFrame এর ভেতরে ঢুকে আসল M3U8 সার্চ করা
                                driver.get(full_iframe_url)
                                time.sleep(3)
                                iframe_source = driver.page_source
                                sub_m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', iframe_source)
                                if sub_m3u8:
                                    player_url = sub_m3u8.group(1)
                                    break
                            except Exception:
                                pass

                # কেবল M3U8 লিংক পাওয়া গেলেই যুক্ত করা হবে
                if player_url:
                    matches_data.append({
                        "match_name": title,
                        "category": category,
                        "image": img_url,
                        "player_url": player_url,
                        "page_url": link
                    })
                    print(f"[FOUND M3U8] {title} | Stream: {player_url}")
                else:
                    print(f"[NO M3U8 STREAM] Skipping {link}")

            except Exception as e:
                print(f"Error checking match {link}: {e}")

        # JSON ফাইলে সংরক্ষণ করা (পুরনো বা নিষ্ক্রিয় ম্যাচ অটোমুছে যাবে)
        with open("dzritv_matches.json", "w", encoding="utf-8") as f:
            json.dump(matches_data, f, ensure_ascii=False, indent=2)

        print(f"Successfully saved {len(matches_data)} streaming matches to dzritv_matches.json")

    except Exception as e:
        print(f"Main Scraper Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_dzritv_m3u8()
