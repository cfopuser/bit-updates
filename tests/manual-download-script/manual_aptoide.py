import sys
import requests
import os
import argparse
from core.utils import run_apk_mitm

def download_aptoide_apk(package_name, no_mitm=False):
    # Constants from StoreKit source code
    api_url = "https://ws2.aptoide.com/api/7/app/getMeta"
    
    print(f"[*] Searching for {package_name} on Aptoide...")
    
    try:
        # Query Aptoide API
        response = requests.get(api_url, params={"package_name": package_name})
        response.raise_for_status()
        data = response.json()

        # Extract download link (Logic from ApkLinkResolverService.kt)
        # Priority: 'path' -> 'path_alt'
        file_info = data.get('data', {}).get('file', {})
        download_url = file_info.get('path') or file_info.get('path_alt')

        if not download_url:
            print(f"[!] Error: Could not find a download link for {package_name}")
            return

        # Prepare filename
        filename = f"{package_name}.apk"
        
        # Download the file
        print(f"[*] Downloading: {download_url}")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        print(f"[+] Success: Saved to {os.path.abspath(filename)}")

        if not no_mitm:
            run_apk_mitm(filename)

    except requests.exceptions.HTTPError:
        print(f"[!] Error: Package '{package_name}' not found or API error.")
    except Exception as e:
        print(f"[!] An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download APK from Aptoide")
    parser.add_argument("package", help="The package name to download (e.g., com.bnhp.payments.paymentsapp)")
    parser.add_argument("--no-mitm", action="store_true", help="Skip running apk-mitm on the downloaded APK")
    
    args = parser.parse_args()
    download_aptoide_apk(args.package, no_mitm=args.no_mitm)