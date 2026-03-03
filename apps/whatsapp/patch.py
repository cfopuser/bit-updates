import os
import re

def patch(decompiled_dir: str) -> bool:
    print(f"[*] Starting WhatsApp Kosher patch (Precision Sniper Mode v16 - METHOD ISOLATION)...")
    
    # ביצוע הפאצ'ים
    photos = _patch_profile_photos(decompiled_dir)
    newsletter = _patch_newsletter_launcher(decompiled_dir)
    tabs = _patch_home_tabs(decompiled_dir)
    spi = _patch_secure_pending_intent(decompiled_dir)
    browser = _patch_force_external_browser(decompiled_dir)

    results = [photos, newsletter, tabs, spi, browser]
    
    if all(results):
        print("\n[SUCCESS] All patches and clone were applied successfully!")
        return True
    else:
        print("\n[FAILURE] One or more critical patches failed. Check logs.")
        return False
        

# ---------------------------------------------------------
# 1. חסימת תמונות פרופיל
# ---------------------------------------------------------
def _patch_profile_photos(root_dir):
    anchor = 'contactPhotosBitmapManager/getphotofast/'
    print(f"\n[1] Scanning for Photo Manager ({anchor})...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("    [-] File not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        original_content = content
        
        declaration_pattern = r"(\s+(?:\.locals|\.registers) \d+)"

        bitmap_regex = r"(\.method public final \w+\(Landroid\/content\/Context;L[^;]+;Ljava\/lang\/String;FIJZZ\)Landroid\/graphics\/Bitmap;)" + declaration_pattern
        content = re.sub(bitmap_regex, r"\1\2\n    const/4 v0, 0x0\n    return-object v0", content)

        stream_regex = r"(\.method public final \w+\(L[^;]+;Z\)Ljava\/io\/InputStream;)" + declaration_pattern
        content = re.sub(stream_regex, r"\1\2\n    const/4 v0, 0x0\n    return-object v0", content)
        
        if content != original_content:
            print("    [+] Photo loaders blocked successfully.")
            with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
            return True
        else:
            print("    [-] Photo loader signatures not found.")
            return False

    except Exception as e:
        print(f"    [-] Error: {e}")
        return False

# ---------------------------------------------------------
# 2. נטרול ניוזלטר (Newsletter Launcher)
# ---------------------------------------------------------
def _patch_newsletter_launcher(root_dir):
    anchor = "NewsletterLinkLauncher/type not handled"
    print(f"\n[2] Scanning for Newsletter Launcher ({anchor})...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("    [-] File not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        original_content = content
        
        injection = "\n    return-void"
        declaration_pattern = r"(\s+(?:\.locals|\.registers) \d+)"
        
        entry_regex = r"(\.method public final \w+\(Landroid\/content\/Context;Landroid\/net\/Uri;\)V)" + declaration_pattern
        content = re.sub(entry_regex, r"\1\2" + injection, content)

        main_regex = r"(\.method public final \w+\(Landroid\/content\/Context;Landroid\/net\/Uri;L[^;]+;Ljava\/lang\/Integer;Ljava\/lang\/Long;Ljava\/lang\/String;IJ\)V)" + declaration_pattern
        content = re.sub(main_regex, r"\1\2" + injection, content)

        if content != original_content:
            print("    [+] Newsletter launcher methods killed.")
            with open(target_file, 'w', encoding='utf-8') as f: f.write(content)
            return True
        else:
            print("    [-] Newsletter launcher signatures not found.")
            return False

    except Exception as e:
        print(f"    [-] Error: {e}")
        return False

# ---------------------------------------------------------
# 3. הסרת טאב העדכונים (Home Tabs) - METHOD ISOLATION
# ---------------------------------------------------------
def _patch_home_tabs(root_dir):
    anchor = "Tried to set badge for invalid tab id"
    print(f"\n[3] Scanning for Home Tabs ({anchor})...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("    [-] File not found.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        # מחלקים את הקובץ לבלוקים של מתודות, כדי למנוע זליגה של ה-Regex ממתודה למתודה
        method_pattern = re.compile(r'(\.method.*?\.end method)', re.DOTALL)
        
        new_content = content
        patch_applied = False
        
        # סורקים כל מתודה בנפרד
        for method_match in method_pattern.finditer(content):
            method_body = method_match.group(1)
            
            # מחפשים את המתודה הספציפית שבתוכה מתבצעת בניית הרשימה
            # היא חייבת להכיל גם 0x12c, גם 0x258, וגם הוספה ל-Collection
            if "0x12c" in method_body and "0x258" in method_body and "AbstractCollection;->add" in method_body:
                
                # עכשיו אנחנו בטוחים ב-100% שאנחנו בתוך מתודה A05
                # נחפש את ה-12c, ואת ה-add הראשון שבא אחריו. 
                updates_regex = r"(const/16\s+[vp]\d+,\s*0x12c.*?)((?:invoke-virtual|invoke-interface)\s*\{[vp]\d+,\s*[vp]\d+\},\s*Ljava/util/AbstractCollection;->add\(Ljava/lang/Object;\)Z)"
                
                if re.search(updates_regex, method_body, re.DOTALL):
                    # מחליפים בהערה
                    new_method_body = re.sub(updates_regex, r"\1# \2", method_body, count=1, flags=re.DOTALL)
                    
                    # מעדכנים את הקובץ המלא עם המתודה הערוכה
                    new_content = new_content.replace(method_body, new_method_body)
                    patch_applied = True
                    print("    [+] Home Tabs: 'Updates' tab (0x12c) REMOVED from the target method.")
                    break # מצאנו וטיפלנו, אפשר לעצור את הלולאה
        
        if patch_applied:
            with open(target_file, 'w', encoding='utf-8') as f: f.write(new_content)
            return True
        else:
            print("    [-] Home Tabs: Target method found, but regex failed to match 0x12c block.")
            return False

    except Exception as e:
        print(f"    [-] Error: {e}")
        return False

# ---------------------------------------------------------
# 4. תיקון SecurePendingIntent (Strict Regex Logic)
# ---------------------------------------------------------
def _patch_secure_pending_intent(root_dir):
    anchor = "Please set reporter for SecurePendingIntent library"
    print(f"\n[4] Scanning for SecurePendingIntent ({anchor})...")
    
    target_file = _find_file_by_string(root_dir, anchor)
    if not target_file:
        print("    [i] File not found (optional, skipping).")
        return True 

    try:
        with open(target_file, 'r', encoding='utf-8') as f: content = f.read()
        
        # Regex שמחפש if-nez שדבוק לשגיאה (מופרד רק ע"י שורות line ורווחים)
        pattern = re.compile(r"(if-nez [vp]\d+, (:cond_\w+))(\s*(?:\.line \d+\s*)*)(const-string [vp]\d+, \"Please set reporter)")

        # החלפה ישירה ל-goto. אם יש return באמצע - ה-Regex פשוט יתעלם מזה.
        new_content, num_subs = pattern.subn(r"goto \2\3\4", content)
        
        if num_subs > 0:
            with open(target_file, 'w', encoding='utf-8') as f: f.write(new_content)
            print(f"    [SUCCESS] Bypassed {num_subs} SecurePendingIntent checks.")
            return True
        else:
            print("    [-] Check not found or already bypassed.")
            return True # אנחנו מחזירים True כדי לא לעצור את הקימפול במקרה של שינוי באפליקציה

    except Exception as e:
        print(f"    [-] Error: {e}")
        return False
# ---------------------------------------------------------
# 5. חסימת דפדפן פנימי (Hijack onCreate) - גרסה מתוקנת v2
# ---------------------------------------------------------
def _patch_force_external_browser(root_dir):
    target_filename = "WaInAppBrowsingActivity.smali"
    print(f"\n[5] Hijacking Internal Browser ({target_filename})...")
    
    target_file = None
    # חיפוש הקובץ
    for root, dirs, files in os.walk(root_dir):
        if target_filename in files:
            target_file = os.path.join(root, target_filename)
            break
            
    if not target_file:
        print("    [-] WaInAppBrowsingActivity.smali not found. Skipping.")
        return False

    try:
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. זיהוי דינמי של מחלקת האב (Parent Class) מתוך כותרת הקובץ
        # אנו מחפשים את השורה: .super L...;
        super_class_match = re.search(r"^\.super\s+(L[^;]+;)", content, re.MULTILINE)
        
        if not super_class_match:
            print("    [-] Could not determine parent class from .super declaration.")
            return False
            
        parent_class = super_class_match.group(1)
        print(f"    [i] Detected parent class: {parent_class}")

        # 2. מציאת המתודה onCreate המקורית כדי להחליף אותה
        method_pattern = re.compile(
            r"(\.method public onCreate\(Landroid\/os\/Bundle;\)V)(.*?)(\.end method)",
            re.DOTALL
        )
        
        match = method_pattern.search(content)
        if not match:
            print("    [-] onCreate method not found.")
            return False

        original_body = match.group(2)

        # 3. הכנת הקוד החדש
        # אנו בונים את שורת ה-invoke-super בצורה מלאכותית ונכונה בהתבסס על ה-parent_class שמצאנו למעלה.
        # זה פותר את הבעיה של NoSuchMethodError.
        new_body = f"""
    .locals 4

    # 1. Call Super (Generated correctly based on .super declaration)
    invoke-super {{p0, p1}}, {parent_class}->onCreate(Landroid/os/Bundle;)V

    # 2. Get URL from Intent
    invoke-virtual {{p0}}, Landroid/app/Activity;->getIntent()Landroid/content/Intent;
    move-result-object v0
    const-string v1, "webview_url"
    invoke-virtual {{v0, v1}}, Landroid/content/Intent;->getStringExtra(Ljava/lang/String;)Ljava/lang/String;
    move-result-object v2

    # Check if URL exists
    if-nez v2, :cond_start_browser
    invoke-virtual {{p0}}, Landroid/app/Activity;->finish()V
    return-void

    :cond_start_browser
    # 3. Prepare External Intent
    invoke-static {{v2}}, Landroid/net/Uri;->parse(Ljava/lang/String;)Landroid/net/Uri;
    move-result-object v0
    new-instance v1, Landroid/content/Intent;
    const-string v3, "android.intent.action.VIEW"
    invoke-direct {{v1, v3, v0}}, Landroid/content/Intent;-><init>(Ljava/lang/String;Landroid/net/Uri;)V
    
    # 4. Try Start Activity
    :try_start_0
    invoke-virtual {{p0, v1}}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V
    :try_end_0
    .catch Ljava/lang/Exception; {{:try_start_0 .. :try_end_0}} :catch_0

    goto :goto_finish

    :catch_0
    # 5. Error (No Browser) -> Toast
    move-exception v0
    const/4 v0, 0x1 
    # "לא נמצא דפדפן / No Browser Found" in Unicode
    const-string v1, "\\u05dc\\u05d0 \\u05e0\\u05de\\u05e6\\u05d0 \\u05d3\\u05e4\\u05d3\\u05e4\\u05df / No Browser Found" 
    
    invoke-static {{p0, v1, v0}}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v0
    invoke-virtual {{v0}}, Landroid/widget/Toast;->show()V

    :goto_finish
    # 6. Kill Internal Activity
    invoke-virtual {{p0}}, Landroid/app/Activity;->finish()V
    return-void
"""

        # 4. ביצוע ההחלפה
        new_content = content.replace(original_body, new_body)
        
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print(f"    [+] Browser hijacked successfully! (Parent: {parent_class})")
        return True

    except Exception as e:
        print(f"    [-] Error patching browser: {e}")
        return False
# ---------------------------------------------------------
# פונקציות עזר
# ---------------------------------------------------------
def _find_file_by_string(root_dir, search_string):
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