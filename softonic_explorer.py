import time
import cloudscraper
from bs4 import BeautifulSoup
import sys

def explore_softonic(softonic_id):
    print(f"[*] Starting Softonic exploration for: {softonic_id}")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    }

    app_url = f"https://{softonic_id}.en.softonic.com/android"
    print(f"[*] Fetching Main Page: {app_url}")
    
    try:
        resp = scraper.get(app_url, headers=headers, timeout=15)
        resp.raise_for_status()
        
        # שמירת ה-HTML המלא לטובת ה-Artifacts של גיטהאב
        with open("softonic_app_page.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
            
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # חילוץ כותרת והדפסה ל-Logs
        title = soup.find("h1")
        print(f"[+] Title found: {title.text.strip() if title else 'Not found'}")
        
        # חיפוש הגרסה
        print("[*] Searching for Version info:")
        for li in soup.find_all("li"):
            text = li.text.strip()
            # מחפש שורות שמכילות את המילה Version או מספרים כמו 10.1
            if "Version" in text or "10." in text:
                print(f"    -> Potential version block: {text.replace(chr(10), ' ')}")
                
        download_page = f"{app_url}/download"
        print(f"[+] Download page URL resolved to: {download_page}")
        
    except Exception as e:
        print(f"[-] Error on main page: {e}")
        sys.exit(1)

    print("\n[*] Waiting 3 seconds before navigating to download page...")
    time.sleep(3)
    
    try:
        print(f"[*] Fetching Download Page: {download_page}")
        resp2 = scraper.get(download_page, headers=headers, timeout=15)
        resp2.raise_for_status()
        
        # שמירת ה-HTML של דף ההורדה
        with open("softonic_download_page.html", "w", encoding="utf-8") as f:
            f.write(resp2.text)
            
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        
        print("[*] Searching for Direct Download Links in the DOM...")
        
        # 1. חיפוש לפי ID קלאסי של סופטוניק
        btn = soup2.find(id="download-button")
        if btn and btn.has_attr("href"):
            print(f"    [!] Found id='download-button' -> {btn['href']}")
            
        # 2. מעבר על כל הלינקים בדף כדי למצוא קבצי APK/XAPK או הפניות פנימיות
        print("\n[*] Other potential download links found:")
        for a in soup2.find_all("a", href=True):
            href = a['href']
            # נחפש סיומות רלוונטיות או שרתי הורדה של סופטוניק
            if ".apk" in href or ".xapk" in href or "ext.softonic.com" in href or "download" in href:
                # נסנן לינקים פנימיים לא קשורים
                if "articles" not in href and "windows" not in href and "mac" not in href:
                    print(f"    -> {href}")
                
    except Exception as e:
        print(f"[-] Error on download page: {e}")

if __name__ == "__main__":
    explore_softonic("egg-bus-train-in-israel")
