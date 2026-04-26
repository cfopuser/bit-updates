import sys
import requests
import os
import argparse
import re
import cloudscraper
from bs4 import BeautifulSoup
from core.utils import run_apk_mitm

def standardize_url(url):
    """
    Standardizes the Uptodown URL to point to the download page.
    Example: https://bit.en.uptodown.com/android -> https://bit.en.uptodown.com/android/download
    """
    # Regex to match Uptodown URLs (personalizing to the structure seen in Dart code)
    standard_url_regex = re.compile(
        r'^https?://([^.]+\.){1,}uptodown\.com(/android)?',
        re.IGNORECASE
    )
    
    # If it's just a name, assume it's the subdomain
    if not url.startswith('http'):
        url = f"https://{url}.en.uptodown.com/android"
    
    match = standard_url_regex.search(url)
    if match:
        base_url = match.group(0).rstrip('/')
        # Ensure it ends with /android/download
        if not base_url.endswith('/download'):
            if not base_url.endswith('/android'):
                base_url = f"{base_url}/android"
            base_url = f"{base_url}/download"
        return base_url
    
    raise ValueError(f"Invalid Uptodown URL or name: {url}")

def get_app_details_with_session(standard_url, session):
    """
    Parses the Uptodown download page to extract app metadata and file ID.
    """
    print(f"[*] Fetching details from {standard_url}...")
    res = session.get(standard_url)
    res.raise_for_status()
    
    soup = BeautifulSoup(res.text, 'html.parser')
    
    version_div = soup.select_one('div.version')
    version = version_div.get_text(strip=True) if version_div else None
    
    name_el = soup.select_one('#detail-app-name')
    name = name_el.get_text(strip=True) if name_el else None
    file_id = name_el.get('data-file-id') if name_el else None
    
    author_el = soup.select_one('#author-link')
    author = author_el.get_text(strip=True) if author_el else None
    
    # Technical information table (usually where package name and extension are found)
    tech_info_tds = [td.get_text(strip=True) for td in soup.select('#technical-information td') if td.get_text(strip=True)]
    
    # Ported logic from Dart:
    # appId = detailElements.lastOrNull
    app_id = tech_info_tds[-1] if tech_info_tds else None
    # extension = detailElements.elementAtOrNull(detailElements.length - 4)?.toLowerCase()
    extension = tech_info_tds[-4].lower() if len(tech_info_tds) >= 4 else 'apk'
    
    return {
        'version': version,
        'appId': app_id,
        'name': name,
        'author': author,
        'fileId': file_id,
        'extension': extension
    }

def download_uptodown_apk(url_or_name, no_mitm=False):
    """
    Main download flow for Uptodown.
    """
    session = cloudscraper.create_scraper()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })

    try:
        print("[*] Initializing session with Uptodown...")
        session.get("https://www.uptodown.com/android")
        print(f"[*] Cookies after home: {session.cookies.get_dict()}")
        
        # Also fetch the main app page to get more cookies
        app_page_url = url_or_name if url_or_name.startswith('http') else f"https://{url_or_name}.en.uptodown.com/android"
        app_page_url = app_page_url.replace('/download', '')
        print(f"[*] Visiting app page: {app_page_url}")
        session.get(app_page_url)
        print(f"[*] Cookies after app page: {session.cookies.get_dict()}")

        standard_url = standardize_url(url_or_name)
        details = get_app_details_with_session(standard_url, session)
        print(f"[*] Cookies after details: {session.cookies.get_dict()}")
        
        if not details['fileId']:
            print("[!] Error: Could not find file ID for download on the page.")
            return
        
        # Step 2: Go to the intermediate "pre-download" page
        apk_url = f"{standard_url}/{details['fileId']}-x"
        print(f"[*] Fetching final download token from {apk_url}...")
        
        session.headers.update({'Referer': standard_url})
        res = session.get(apk_url)
        print(f"[*] Cookies after intermediate: {session.cookies.get_dict()}")
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        download_button = soup.select_one('#detail-download-button')
        final_url_key = download_button.get('data-url') if download_button else None
        
        if not final_url_key:
            print("[!] Error: Could not find final download token (data-url).")
            return
        
        print(f"[*] Session cookies: {session.cookies.get_dict()}")
        final_url_key = final_url_key.strip('/')
        
        # Step 3: Download the actual file
        filename = f"{details['appId'] or 'app'}.{details['extension'] or 'apk'}"
        final_download_url = f"https://dw.uptodown.com/dwn/{final_url_key}/{filename}"
        
        print(f"[*] Downloading: {final_download_url}")
        
        session.headers.update({
            'Referer': apk_url,
            'Accept': '*/*',
        })
        
        with session.get(final_download_url, stream=True) as r:
            if r.status_code != 200:
                print(f"[!] Error: {r.status_code} for {final_download_url}")
                print(f"[!] Response headers: {r.headers}")
                print(f"[!] Response content (first 200 bytes): {r.content[:200]}")
                return
            
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print(f"[+] Success: Saved to {os.path.abspath(filename)}")
        
        if not no_mitm:
            run_apk_mitm(filename)
            
    except Exception as e:
        print(f"[!] An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download APK from Uptodown")
    parser.add_argument("url_or_name", help="Uptodown URL or subdomain name (e.g., 'bit' or 'https://bit.en.uptodown.com/android')")
    parser.add_argument("--no-mitm", action="store_true", help="Skip running apk-mitm on the downloaded APK")
    
    args = parser.parse_args()
    download_uptodown_apk(args.url_or_name, no_mitm=args.no_mitm)
