import os
import re

def patch(decompiled_dir: str) -> bool:
    """
    Applies 'Kosher' patches to WhatsApp:
    1. Blocks Profile Photos (Thumbnails & Full View).
    2. Kills Newsletter/Channel Links Launcher.
    3. Removes ONLY the Updates/Channels Tab from Home Screen.
    4. [NEW] Fixes SecurePendingIntent Crash (LX/0sw).
    """
    print(f"[*] Starting WhatsApp Kosher patch & Crash Fixes...")
    
    # משתני מעקב להצלחה
    photos_patched = _patch_profile_photos(decompiled_dir)
    newsletter_launcher_patched = _patch_newsletter_launcher(decompiled_dir)
    tabs_patched = _patch_home_tabs(decompiled_dir)
    spi_patched = _patch_secure_pending_intent(decompiled_dir)

    if photos_patched and newsletter_launcher_patched and tabs_patched and spi_patched:
        print("[SUCCESS] All patches applied successfully!")
        return True
    elif photos_patched or newsletter_launcher_patched or tabs_patched or spi_patched:
        print("[!] PARTIAL SUCCESS: Some patches failed.")
        return True 
    else:
        print("[FAILURE] All patches failed.")
        return False

# ---------------------------------------------------------
# 1. חסימת תמונות פרופיל
# ---------------------------------------------------------
def _patch_profile_photos(root_dir):
    anchor = 'contactPhotosBitmapManager/getphotofast/'
    print(f"[*] Scanning for Photo Manager using anchor: '{anchor}'...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("[-] Photo Manager file not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        # חסימת Bitmap (A04)
        bmp_regex = r"(\.method public final \w+\(Landroid/content/Context;LX/0IB;Ljava/lang/String;FIJZZ\)Landroid/graphics/Bitmap;\s*\.registers \d+)"
        if re.search(bmp_regex, content):
            content = re.sub(bmp_regex, r"\1\n    const/4 v0, 0x0\n    return-object v0", content, count=1)
            print("[+] Profile Photos: Bitmap loader blocked.")
        
        # חסימת InputStream (A07)
        stream_regex = r"(\.method public final \w+\(LX/0IB;Z\)Ljava/io/InputStream;\s*\.registers \d+)"
        if re.search(stream_regex, content):
            content = re.sub(stream_regex, r"\1\n    const/4 v0, 0x0\n    return-object v0", content, count=1)
            print("[+] Profile Photos: Stream loader blocked.")

        with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
        return True
    except Exception as e:
        print(f"[-] Error patching photos: {e}")
        return False

# ---------------------------------------------------------
# 2. חיסול מנגנון פתיחת הערוצים (Launcher)
# ---------------------------------------------------------
def _patch_newsletter_launcher(root_dir):
    anchor = "NewsletterLinkLauncher/type not handled"
    print(f"[*] Scanning for Newsletter Launcher using anchor: '{anchor}'...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("[-] Newsletter Launcher file not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        injection = "\n    return-void"

        # חסימת A01 (Deep Links)
        entry_regex = r"(\.method public final \w+\(Landroid/content/Context;Landroid/net/Uri;\)V\s*\.registers \d+)"
        if re.search(entry_regex, content):
            content = re.sub(entry_regex, r"\1" + injection, content, count=1)
            print("[+] Newsletter: Entry point (Deep Links) killed.")

        # חסימת A02 (Main Logic)
        main_regex = r"(\.method public final \w+\(Landroid/content/Context;Landroid/net/Uri;L.*?;Ljava/lang/Integer;Ljava/lang/Long;Ljava/lang/String;IJ\)V\s*\.registers \d+)"
        if re.search(main_regex, content):
            content = re.sub(main_regex, r"\1" + injection, content, count=1)
            print("[+] Newsletter: Main logic launcher killed.")

        with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
        return True
    except Exception as e:
        print(f"[-] Error patching newsletter launcher: {e}")
        return False

# ---------------------------------------------------------
# 3. הסרת הלשוניות (טאבים) מהמסך הראשי
# ---------------------------------------------------------
def _patch_home_tabs(root_dir):
    anchor = "Tried to set badge for invalid tab id"
    print(f"[*] Scanning for Home Tabs Manager using anchor: '{anchor}'...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("[-] Home Tabs Manager file not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        # הסרת לשונית העדכונים (Channels/Updates) - מזהה 0x12c (300)
        updates_regex = r"(const/16 [vp]\d+, 0x12c\s+.*?)(invoke-virtual \{[vp]\d+, [vp]\d+\}, Ljava/util/AbstractCollection;->add\(Ljava/lang/Object;\)Z)"
        
        if re.search(updates_regex, content, re.DOTALL):
            content = re.sub(updates_regex, r"\1# \2", content, count=1, flags=re.DOTALL)
            print("[+] Home Tabs: Updates/Channels tab (0x12c) commented out.")
        else:
            print("[-] Home Tabs: Updates tab pattern not found.")

        with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
        return True

    except Exception as e:
        print(f"[-] Error patching home tabs: {e}")
        return False

# ---------------------------------------------------------
# 4. תיקון SecurePendingIntent (מונע את הקריסה ב-RegisterPhone)
# ---------------------------------------------------------
def _patch_secure_pending_intent(root_dir):
    anchor = "Please set reporter for SecurePendingIntent library"
    print(f"[*] Scanning for SecurePendingIntent logic using anchor: '{anchor}'...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("[-] SecurePendingIntent file not found. Check if already patched.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        # מחפשים את ההשוואה שנכשלת (if-nez) שזורקת שגיאה על שם החבילה, 
        # ומחליפים ל-goto כדי לדלג עליה תמיד.
        pattern = r"(if-nez [vp]\d+, (:cond_\w+))(\s+.+?Please set reporter for SecurePendingIntent library)"
        
        if re.search(pattern, content, re.DOTALL):
            # מחליף את if-nez ב-goto
            new_content = re.sub(pattern, r"goto \2\3", content, count=1, flags=re.DOTALL)
            
            with open(target_file, 'w', encoding='utf-8') as f: f.write(new_content)
            print(f"[+] SecurePendingIntent patched in {os.path.basename(target_file)} (Bypassed package name check).")
            return True
        else:
            print("[-] Could not locate the specific if-nez instruction to patch.")
            return False

    except Exception as e:
        print(f"[-] Error patching SecurePendingIntent: {e}")
        return False

# ---------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------
def _find_file_by_string(root_dir, search_string):
    """מחפש קובץ סמאלי שמכיל מחרוזת ספציפית"""
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".smali"):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        if search_string in f.read():
                            return path
                except:
                    continue
    return None