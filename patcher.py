import os
import re
import sys

def patch_smali(decompiled_dir):
    target_filename = "AppInitiationViewModel.smali"
    file_found = False

    # The exact pattern provided
    pattern = r"(invoke-static \{[vp]\d+, [vp]\d+\}, Lkotlin\/collections\/ArraysKt___ArraysKt;->contains\(Ljava\/lang\/Object;\[Ljava\/lang\/Object;\)Z\s+move-result ([vp]\d+)\s+)if-nez \2, (:cond_\w+)"

    # Walk through the directory to find the specific smali file
    for root, dirs, files in os.walk(decompiled_dir):
        if target_filename in files:
            file_path = os.path.join(root, target_filename)
            print(f"[+] Found target file: {file_path}")
            file_found = True
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Search for the pattern
            match = re.search(pattern, content)
            
            if match:
                print(f"[i] Logic found! Target label is: {match.group(3)}")
                # Replace if-nez with goto as requested
                new_content = re.sub(pattern, r"\1goto \3", content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("[+] File patched successfully.")
            else:
                print("[-] Pattern not found in this file. It might have already been patched or the code changed.")
                sys.exit(1)
    
    if not file_found:
        print(f"[-] {target_filename} not found in decompiled directory.")
        sys.exit(1) # Fail the workflow if the file is missing

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patcher.py <decompiled_directory>")
        sys.exit(1)
        
    directory = sys.argv[1]
    patch_smali(directory)