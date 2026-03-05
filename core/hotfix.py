import os
import re

def apply_hotfix_if_needed(decompiled_dir: str, config: dict):
    """
    Checks if the current version has a hotfix suffix defined in app.json.
    If so, it applies the suffix to both apktool.yml and AndroidManifest.xml.
    """
    hotfixes = config.get("hotfixes", {})
    if not hotfixes:
        return

    # 1. Edit apktool.yml
    apktool_yml_path = os.path.join(decompiled_dir, "apktool.yml")
    if os.path.exists(apktool_yml_path):
        with open(apktool_yml_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Matches versionName with or without quotes
        pattern_yml = re.compile(r"(versionName:\s*)(['\"]?)([^'\">\r\n]+)\2")
        match_yml = pattern_yml.search(content)
        if match_yml:
            base_ver = match_yml.group(3).strip()
            suffix = hotfixes.get(base_ver)
            
            if suffix and not base_ver.endswith(suffix):
                new_ver = f"{base_ver}{suffix}"
                new_content = pattern_yml.sub(rf"\g<1>\g<2>{new_ver}\g<2>", content, count=1)
                with open(apktool_yml_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"[+] [Hotfix] apktool.yml patched: {base_ver} -> {new_ver}")

    # 2. Edit AndroidManifest.xml
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        pattern_manifest = re.compile(r'(android:versionName=")([^"]+)(")')
        match_manifest = pattern_manifest.search(content)
        if match_manifest:
            base_ver = match_manifest.group(2)
            suffix = hotfixes.get(base_ver)
            
            if suffix and not base_ver.endswith(suffix):
                new_ver = f"{base_ver}{suffix}"
                new_content = pattern_manifest.sub(rf"\g<1>{new_ver}\g<3>", content, count=1)
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"    [+] [Hotfix] AndroidManifest.xml patched: {base_ver} -> {new_ver}")
