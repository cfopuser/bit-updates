import requests
from bs4 import BeautifulSoup
import sys
import os
from google_play_scraper import app

def get_play_store_version(package_name):
    try:
        result = app(package_name)
        return result.get('version')
    except Exception as e:
        print(f"[-] Error fetching Play Store version: {e}")
        return None

def get_local_version(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def update_local_version(file_path, version):
    with open(file_path, 'w') as f:
        f.write(version)

def download_apk(package_name, output_filename):
    print(f"[*] Searching for {package_name} on Aptoide...")
    
    # Aptoide usually follows this URL pattern for apps
    base_url = f"https://{package_name}.en.aptoide.com/app"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Method 1: Look for direct download link in the HTML
        download_url = None
        for link in soup.find_all('a', href=True):
            if 'aptoide.com/download' in link['href'] or 'f.aptoide.com' in link['href']:
                download_url = link['href']
                break
        
        if not download_url:
            meta_url = soup.find('meta', property='og:url')
            if meta_url:
                download_url = meta_url['content'].rstrip('/') + '/download'

        if not download_url:
            print("[-] Could not find download URL directly.")
            return False

        print(f"[+] Found potential download page: {download_url}")
        
        dl_page = requests.get(download_url, headers=headers)
        dl_page.raise_for_status()
        dl_soup = BeautifulSoup(dl_page.text, 'html.parser')
        
        final_apk_url = None
        for link in dl_soup.find_all('a', href=True):
            if link['href'].endswith('.apk'):
                final_apk_url = link['href']
                break
        
        if not final_apk_url:
            for link in dl_soup.find_all('a', href=True):
                if 'pool.apk' in link['href'] or ('aptoide.com' in link['href'] and 'apk' in link['href'].lower()):
                    final_apk_url = link['href']
                    break

        if not final_apk_url:
            print("[-] Could not find final APK URL.")
            return False

        print(f"[*] Downloading APK from: {final_apk_url}")
        
        apk_response = requests.get(final_apk_url, headers=headers, stream=True)
        apk_response.raise_for_status()
        
        with open(output_filename, 'wb') as f:
            for chunk in apk_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[+] APK downloaded successfully to {output_filename}")
        return True

    except Exception as e:
        print(f"[-] Error during download: {e}")
        return False

if __name__ == "__main__":
    package_name = "com.bnhp.payments.paymentsapp"
    output_filename = "latest.apk"
    version_file = "version.txt"
    force_download = False

    if len(sys.argv) > 1:
        package_name = sys.argv[1]
    if "--force" in sys.argv:
        force_download = True

    play_version = get_play_store_version(package_name)
    local_version = get_local_version(version_file)

    print(f"[*] Play Store Version: {play_version}")
    print(f"[*] Local Version: {local_version}")

    if play_version != local_version or force_download:
        print("[!] New version detected or force download enabled.")
        if download_apk(package_name, output_filename):
            update_local_version(version_file, play_version)
            # This print is used by the GitHub Action to set an output variable
            print("NEW_VERSION_FOUND=true")
        else:
            sys.exit(1)
    else:
        print("[i] No new version found.")
        print("NEW_VERSION_FOUND=false")
