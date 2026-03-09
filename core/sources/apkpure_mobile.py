import re
import requests

class APKPureMobileSource:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_api = "https://api.pureapk.com/m/v3/cms/app_version"
        
        # כותרות שמחקות מכשיר אנדרואיד כדי למנוע חסימות
        self.headers = {
            'x-sv': '29',
            'x-abis': 'arm64-v8a,armeabi-v7a,armeabi',
            'x-gp': '1',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36'
        }
        # שימוש ב-Session כדי לעקוב אחר ההפניות (Redirects) לשרתי ה-CDN בצורה חלקה
        self.scraper = requests.Session()

    def _extract_version(self, text: str) -> str | None:
        if not text:
            return None
        # חיפוש תבנית של גרסה המופרדת בנקודות (למשל 1.2.3 או 4.10) - מתעלם ממספרים סתמיים
        match = re.search(r"(\d+(?:\.\d+){1,})", text)
        return match.group(1) if match else None

    def get_latest_version(self, package_name: str):
        print(f"[*][APKPure Mobile] Fetching metadata for: {package_name}")
        params = {
            'hl': 'en-US',
            'package_name': package_name
        }
        
        try:
            response = self.scraper.get(
                self.base_api,
                params=params,
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()

            # חילוץ מחרוזות ארוכות מהתשובה הבינארית כדי למצוא כתובות URL
            strings = re.findall(rb'[ -~]{8,}', response.content)
            
            valid_urls =[]
            for s in strings:
                if s.startswith(b'http'):
                    s_upper = s.upper()
                    # תופס גם APK וגם XAPK
                    if b'/APK' in s_upper or b'/XAPK' in s_upper:
                        valid_urls.append(s.decode('utf-8'))
            
            if not valid_urls:
                print("[-] [APKPure Mobile] No APK/XAPK URL found in API response.")
                return None, None, None
                
            release_url = valid_urls[0]
            title = package_name
            version = None
            
            # ניסיון 1: חילוץ הגרסה מתוך ה-URL עצמו (אם זמין)
            version = self._extract_version(release_url)
            
            # ניסיון 2: פתיחת חיבור זריז וקריאת הכתובת הסופית לאחר ההפניה (Redirect)
            if not version:
                try:
                    # שימוש ב-stream=True קורא רק את ההדרים ולא מוריד את הקובץ כולו
                    resp = self.scraper.get(release_url, headers=self.headers, allow_redirects=True, stream=True, timeout=10)
                    final_url = resp.url
                    cd = resp.headers.get("Content-Disposition", "")
                    resp.close() # סגירת החיבור מיד כדי לחסוך זמן ומשאבים
                    
                    # בדיקה בשם הקובץ המוצהר
                    match = re.search(r"filename\*?=['\"]?(?:UTF-8'')?([^'\";\n]+)", cd)
                    if match:
                        filename = match.group(1)
                        version = self._extract_version(filename)
                    
                    # אם לא נמצא, נחפש בסוף הכתובת הסופית של ה-CDN שבהכרח מכילה את השם המקורי
                    if not version:
                        final_part = final_url.split('/')[-1]
                        version = self._extract_version(final_part)
                        
                except Exception as e:
                    print(f"[-][APKPure Mobile] Warning - Could not fetch final URL for version: {e}")

            # גיבוי סופי
            if not version:
                version = "latest"
            
            return version, release_url, title
            
        except Exception as e:
            print(f"[-] [APKPure Mobile] Error resolving via API: {e}")
            return None, None, None

    def get_download_url(self, initial_url: str):
        # ה-URL שהתקבל פועל כקישור הורדה ישיר
        return initial_url
