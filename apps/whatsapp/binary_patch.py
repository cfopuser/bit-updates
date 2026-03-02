import os
import subprocess
import shutil
import sys

def patch(apk_path: str) -> bool:
    """
    Downloads and runs Schwartzblat's WhatsAppPatcher on the provided APK.
    """
    print("[*] [WhatsApp] Initializing Schwartzblat Patcher...")
    
    patcher_dir = "WhatsAppPatcher"
    patched_apk = "latest_patched.apk"
    
    # ניקיון שאריות
    if os.path.exists(patcher_dir):
        shutil.rmtree(patcher_dir)

    try:
        # 1. Clone Repository
        print("[*] Cloning WhatsAppPatcher repo...")
        subprocess.run(
            ["git", "clone", "--recurse-submodules", "https://github.com/Schwartzblat/WhatsAppPatcher.git"],
            check=True
        )

        # 2. Install Requirements
        print("[*] Installing dependencies...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", f"{patcher_dir}/requirements.txt"],
            check=True
        )
        # התקנת stitch-test הנדרש
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "stitch-test", 
             "--index-url", "https://test.pypi.org/simple/", 
             "--extra-index-url", "https://pypi.org/simple"],
            check=True
        )

        # 3. Bypass Firebase Patch (The specific customization)
        print("[*] Applying internal fix to bypass Firebase params...")
        main_py_path = os.path.join(patcher_dir, "main.py")
        with open(main_py_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # הסרת הקריאה ל-FirebaseParamsFinder
        content = content.replace("FirebaseParamsFinder(args),", "")
        
        with open(main_py_path, "w", encoding="utf-8") as f:
            f.write(content)

        # הסרת ה-Hook בקובץ ה-Java
        java_path = os.path.join(patcher_dir, "smali_generator/app/src/main/java/com/smali_generator/TheAmazingPatch.java")
        if os.path.exists(java_path):
            with open(java_path, "r", encoding="utf-8") as f:
                java_content = f.read()
            java_content = java_content.replace("new FirebaseParams(),", "")
            with open(java_path, "w", encoding="utf-8") as f:
                f.write(java_content)

        # 4. Run the Patcher
        # אנחנו מעבירים נתיב אבסולוטי ל-APK כדי למנוע בעיות נתיבים
        abs_apk_path = os.path.abspath(apk_path)
        abs_output_path = os.path.abspath(patched_apk)
        
        print(f"[*] Executing patcher on {abs_apk_path}...")
        
        # הרצה מתוך התיקייה של הפאצ'ר כי הוא תלוי בקבצים יחסיים
        subprocess.run(
            [sys.executable, "main.py", "-p", abs_apk_path, "-o", abs_output_path, "--no-sign"],
            cwd=patcher_dir,
            check=True
        )

        # 5. Replace original APK
        if os.path.exists(patched_apk):
            print(f"[+] Patch successful! Replacing {apk_path}")
            shutil.move(patched_apk, apk_path)
            shutil.rmtree(patcher_dir) # ניקוי
            return True
        else:
            print("[-] Patch finished but output file not found.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[-] Error running shell commands: {e}")
        return False
    except Exception as e:
        print(f"[-] Unexpected error: {e}")
        return False
