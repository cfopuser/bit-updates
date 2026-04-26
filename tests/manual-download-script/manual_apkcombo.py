import sys
import requests
import os
import argparse
import re
import cloudscraper
import base64
from urllib.parse import unquote
from bs4 import BeautifulSoup
from core.utils import run_apk_mitm

# Suggested User-Agent from user request
USER_AGENT = 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36'

# Using cloudscraper to handle potential Cloudflare protection
scraper = cloudscraper.create_scraper()
scraper.headers.update({
    'User-Agent': USER_AGENT
})

def parse_html(html, package_name):
    """Parses the HTML to extract app details and download link."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Title: h1 or <title>
    title_el = soup.find('h1')
    title = title_el.get_text(strip=True) if title_el else ""
    if not title:
        title_match = re.search(r'Download ([^-]+) APK', html)
        if title_match:
            title = title_match.group(1).strip()

    # Version: span.vername
    vername_el = soup.select_one('span.vername')
    version = vername_el.get_text(strip=True) if vername_el else ""
    if not version:
        version_match = re.search(r'<span[^>]*class="[^"]*vername[^"]*"[^>]*>([^<]+)</span>', html)
        if version_match:
            version = version_match.group(1).strip()

    # Version Code: span.vercode
    vercode_el = soup.select_one('span.vercode')
    version_code = ""
    if vercode_el:
        version_code = vercode_el.get_text(strip=True).replace('(', '').replace(')', '')
    else:
        vercode_match = re.search(r'\(([^)]+)\)</span>', html)
        if vercode_match:
            version_code = vercode_match.group(1).strip()

    # Download Link: a.variant
    # APKCombo often has multiple variants, we'll try to find the best one
    variants = soup.select('a.variant')
    raw_link = ""
    target_variant = None
    package_type = "apk"
    
    if variants:
        # Prefer XAPK or APKS if available, otherwise take the first
        for v in variants:
            vtype_el = v.select_one('.vtype')
            vtype_text = vtype_el.get_text(strip=True).upper() if vtype_el else ""
            if 'XAPK' in vtype_text or 'APKS' in vtype_text:
                target_variant = v
                if 'XAPK' in vtype_text: package_type = "xapk"
                if 'APKS' in vtype_text: package_type = "apks"
                break
        
        if not target_variant:
            target_variant = variants[0]
            vtype_el = target_variant.select_one('.vtype')
            vtype_text = vtype_el.get_text(strip=True).upper() if vtype_el else ""
            if 'XAPK' in vtype_text: package_type = "xapk"
            elif 'APKS' in vtype_text: package_type = "apks"
            else: package_type = "apk"
            
        raw_link = target_variant.get('href', '')
        
        # Try to extract details from the selected variant if they weren't found at the top
        if not version:
            vername_el = target_variant.select_one('.vername')
            if vername_el:
                version = vername_el.get_text(strip=True)
        if not version_code:
            vercode_el = target_variant.select_one('.vercode')
            if vercode_el:
                version_code = vercode_el.get_text(strip=True).replace('(', '').replace(')', '')
    
    if not raw_link:
        # Fallback to regex for direct links
        # More specific regex to avoid catching random links
        link_match = re.search(r'href="((?:/d\?u=|/r2\?u=|https?://[^"]+)\.apk[^"]*)"', html)
        if not link_match:
            link_match = re.search(r'href="((?:/d\?u=|/r2\?u=)[^"]+)"', html)
        if link_match:
            raw_link = link_match.group(1)
            if 'xapk' in raw_link.lower(): package_type = "xapk"
            elif 'apks' in raw_link.lower(): package_type = "apks"

    # Cleaning logic
    clean_link = raw_link
    # Handle /r2?u= and /d?u= redirectors
    if "u=" in raw_link and ("?u=" in raw_link or "&u=" in raw_link):
        idx = raw_link.find("u=")
        if idx != -1:
            val = unquote(raw_link[idx + 2:])
            if val.startswith('http'):
                # Known problematic direct hosts - keep the redirector instead
                if "pureapk.com" in val:
                    clean_link = raw_link
                else:
                    clean_link = val
            elif val.startswith('/'):
                clean_link = f"https://apkcombo.com{val}"
            else:
                # Might be base64
                try:
                    # Add padding if necessary for base64
                    padded_val = val + '=' * (-len(val) % 4)
                    decoded = base64.b64decode(padded_val).decode('utf-8', errors='ignore')
                    if 'http' in decoded:
                        # Extract the URL
                        url_match = re.search(r'https?://[^\s|%|&]+', decoded)
                        if url_match:
                            decoded_url = url_match.group(0)
                            # Check for problematic hosts
                            if "pureapk.com" in decoded_url:
                                clean_link = raw_link
                            else:
                                clean_link = decoded_url
                        else:
                            clean_link = raw_link
                    else:
                        clean_link = raw_link
                except:
                    clean_link = raw_link
    
    # If it's still a relative path (not starting with http)
    if clean_link.startswith('/') and not clean_link.startswith('http'):
        clean_link = f"https://apkcombo.com{clean_link}"

    return {
        'title': title,
        'version': version,
        'version_code': version_code,
        'download_link': clean_link,
        'package_name': package_name,
        'package_type': package_type,
        'size': '' # Will be filled if found
    }

def get_apkcombo_info(package_name):
    """Fetches app info from APKCombo, handling the XID dynamic loading if necessary."""
    url = f"https://apkcombo.com/app/{package_name}/download/apk"
    print(f"[*] Fetching {url}...")
    
    response = scraper.get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    # Phase 1: Check if we need to do the XID POST
    # Better check: search for actual variant tags
    if not soup.select_one('a.variant'):
        print("[*] Direct links not found, looking for XID...")
        # XID can be alphanumeric
        xid_match = re.search(r'var xid = "([^"]+)"', html)
        if xid_match:
            xid = xid_match.group(1)
            # Find the path segment for the AJAX call
            # Example: fetchData("/waze/com.waze/" + xid + "/dl")
            # We look for the fetchData call or the segment before xid
            path_match = re.search(rf'fetchData\("([^"]+/{package_name}/)" \+ xid', html)
            if not path_match:
                path_match = re.search(rf'"(/[^"]+/{package_name}/)"', html)
            
            if path_match:
                path_segment = path_match.group(1).strip('"')
                ajax_url = f"https://apkcombo.com{path_segment}{xid}/dl"
                print(f"[*] Performing POST to {ajax_url}...")
                
                # Phase 2: Secondary POST request
                post_res = scraper.post(ajax_url, data={
                    'package_name': package_name,
                    'version': ''
                })
                html = post_res.text
            else:
                print("[!] Could not find path segment for AJAX.")
        else:
            print("[!] Could not find XID on the page.")
    
    return parse_html(html, package_name)

def download_apk(info, no_mitm=False):
    """Downloads the APK and optionally runs apk-mitm."""
    if not info['download_link']:
        print("[!] No download link found.")
        return

    # Determine extension from package_type or link
    ext = info.get('package_type', 'apk')
    lower_link = info['download_link'].lower()
    if '.xapk' in lower_link or 'xapk' in lower_link:
        ext = 'xapk'
    elif '.apks' in lower_link or 'apks' in lower_link:
        ext = 'apks'
    
    filename = f"{info['package_name']}.{ext}"
    
    # Safe printing for console
    safe_title = info['title'].encode('ascii', 'ignore').decode('ascii')
    safe_version = info['version'].encode('ascii', 'ignore').decode('ascii')
    print(f"[*] Downloading {safe_title} (Version: {safe_version})")
    print(f"[*] Source: {info['download_link']}")
    
    try:
        with scraper.get(info['download_link'], stream=True, timeout=30) as r:
            r.raise_for_status()
            
            # Check content type to avoid downloading HTML "garbage"
            content_type = r.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
                # Some sites return 200 OK but it's an error/redirect page
                print("[!] Downloaded content is HTML, not a binary file. This might be a redirect or error page.")
                return False

            total_size = int(r.headers.get('content-length', 0))
            if total_size > 0:
                print(f"[*] Size: {total_size / (1024*1024):.2f} MB")
            
            downloaded = 0
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            done = int(50 * downloaded / total_size)
                            percent = (100 * downloaded / total_size)
                            sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {downloaded}/{total_size} bytes ({percent:.1f}%)")
                            sys.stdout.flush()
            print("\n[+] Download complete.")
            
        print(f"[+] Saved to {os.path.abspath(filename)}")
        
        if not no_mitm:
            run_apk_mitm(filename)
        return True
            
    except Exception as e:
        print(f"\n[!] Download failed: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual APKCombo Scraper & Downloader")
    parser.add_argument("package_name", help="Android package name (e.g., 'com.whatsapp')")
    parser.add_argument("--no-mitm", action="store_true", help="Skip running apk-mitm on the downloaded APK")
    
    args = parser.parse_args()
    
    try:
        info = get_apkcombo_info(args.package_name)
        if info and info['download_link']:
            # Safe printing
            safe_title = info['title'].encode('ascii', 'ignore').decode('ascii')
            safe_version = info['version'].encode('ascii', 'ignore').decode('ascii')
            print(f"[*] Found App: {safe_title}")
            print(f"[*] Version: {safe_version} ({info['version_code']})")
            download_apk(info, no_mitm=args.no_mitm)
        else:
            print("[!] Failed to extract app information or download link.")
    except Exception as e:
        # Avoid charmap error on final exception print
        msg = str(e).encode('ascii', 'ignore').decode('ascii')
        print(f"[!] An unexpected error occurred: {msg}")
