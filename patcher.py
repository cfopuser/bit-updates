import os
import re
import sys

def patch_smali(decompiled_dir):
    target_filename = "AppInitiationViewModel.smali"
    file_found = False
    patch_applied = False

    print(f"[*] Searching for {target_filename}...")

    for root, dirs, files in os.walk(decompiled_dir):
        if target_filename in files:
            file_path = os.path.join(root, target_filename)
            file_found = True
            print(f"[+] Found file at: {file_path}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Regex Explanation:
                # 1. invoke-static ... ArraysKt...->contains
                #    Matches the function call.
                # 2. .*?
                #    Matches any debug lines (like .line 90) between instructions.
                # 3. move-result ([vp]\d+)
                #    Captures the register (e.g., p1).
                # 4. .*?
                #    Matches debug lines between move-result and if-nez (THE FIX).
                # 5. if-nez \2, (:cond_\w+)
                #    Matches the check on the captured register.
                
                # We group everything before 'if-nez' into group 1 so we can restore it.
                pattern = re.compile(
                    r"(invoke-static \{[vp]\d+, [vp]\d+\}, Lkotlin\/collections\/ArraysKt.*?;->contains\(.*?\).*?move-result ([vp]\d+).*?)if-nez \2, (:cond_\w+)",
                    re.DOTALL
                )
                
                match = pattern.search(content)
                
                if match:
                    print(f"[i] Logic found! Target label is: {match.group(3)}")
                    
                    # Replace 'if-nez' with 'goto' to bypass the check
                    # \1 puts back the invoke, lines, move-result, and lines
                    # goto \3 puts the jump to the success label
                    new_content = pattern.sub(r"\1goto \3", content)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print("[+] PATCH APPLIED SUCCESSFULLY: Sideload check bypassed.")
                    patch_applied = True
                    break 
                
                else:
                    print("[!] Complex regex failed, trying simple search fallback...")
                    
                    # Fallback logic: simpler string replacement
                    # Assumes register p1 based on common compilation patterns
                    if "Lkotlin/collections/ArraysKt" in content and "contains" in content:
                        print("[i] Found ArraysKt->contains usage. Attempting heuristic patch...")
                        
                        # Look for if-nez p1 appearing shortly after the contains call
                        # This regex allows for intervening lines/whitespace
                        fallback_pattern = re.compile(r"(if-nez p1, (:cond_\w+))")
                        if fallback_pattern.search(content):
                             # Only replace the if-nez associated with p1
                             new_content = fallback_pattern.sub(r"goto \2", content, count=1)
                             
                             if new_content != content:
                                 with open(file_path, 'w', encoding='utf-8') as f:
                                     f.write(new_content)
                                 print("[+] Simple fallback patch applied successfully.")
                                 patch_applied = True
                                 break

                    print("[-] Pattern not found. Dumping snippet for debugging:")
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if "contains" in line and "ArraysKt" in line:
                            print(f"Line {i}: {line}")
                            # Print context
                            for j in range(1, 6):
                                if i + j < len(lines):
                                    print(f"Line {i+j}: {lines[i+j]}")

            except Exception as e:
                print(f"[-] Error reading/writing file: {str(e)}")
                sys.exit(1)

    if not file_found:
        print(f"[-] CRITICAL: {target_filename} not found.")
        sys.exit(1)

    if not patch_applied:
        print("[-] CRITICAL: File found but patch logic could not be applied.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python patcher.py <decompiled_directory>")
        sys.exit(1)
        
    directory = sys.argv[1]
    patch_smali(directory)