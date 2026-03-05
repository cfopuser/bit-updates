"""
Generic patch runner — dynamically loads an app's patch.py module.
"""

import importlib.util
import os
import re

from core.cloner import run_clone
from core.universal_updater import inject_universal_updater
from core.utils import load_app_config


def apply_version_suffix(decompiled_dir: str, suffix: str):
    apktool_yml_path = os.path.join(decompiled_dir, "apktool.yml")
    if not os.path.exists(apktool_yml_path):
        print(f"[-] [Patcher] apktool.yml not found. Cannot apply suffix '{suffix}'.")
        return

    with open(apktool_yml_path, "r", encoding="utf-8") as f:
        content = f.read()

    # מחפש את שורת הגרסה ומוסיף את הסיומת לפני המרכאות הסוגרות
    pattern = re.compile(r"(versionName:\s*)(['\"]?)(.*?)\2")
    match = pattern.search(content)
    if match:
        old_ver = match.group(3)
        if not old_ver.endswith(suffix):
            new_content = pattern.sub(rf"\g<1>\g<2>{old_ver}{suffix}\g<2>", content, count=1)
            with open(apktool_yml_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"    [+][Patcher] Applied version suffix: {old_ver} -> {old_ver}{suffix}")
        else:
            print(f"    [i] [Patcher] Version suffix '{suffix}' already applied.")
    else:
        print(f"[-] [Patcher] Could not find versionName in apktool.yml")

def run_patch(app_id: str, decompiled_dir: str) -> bool:
    """
    Import apps/{app_id}/patch.py and call its patch(decompiled_dir) function.

    Args:
        app_id: The app identifier (subfolder name under apps/).
        decompiled_dir: Path to the apktool-decompiled directory.

    Returns:
        True if the patch was applied successfully, False otherwise.
    """
    patch_module_path = os.path.join("apps", app_id, "patch.py")

    if not os.path.isfile(patch_module_path):
        print(f"[-] [{app_id}] No patch.py found at {patch_module_path}")
        return False

    print(f"[*] [{app_id}] Loading patch module: {patch_module_path}")

    try:
        spec = importlib.util.spec_from_file_location(
            f"apps.{app_id}.patch", patch_module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[-] [{app_id}] Failed to load patch module: {e}")
        return False

    if not hasattr(module, "patch") or not callable(module.patch):
        print(f"[-] [{app_id}] patch.py does not have a callable 'patch' function")
        return False

    print(f"[*] [{app_id}] Running patch on: {decompiled_dir}")
    try:
        result = module.patch(decompiled_dir)
    except Exception as e:
        print(f"[-] [{app_id}] Patch raised an exception: {e}")
        return False

    if not result:
        print(f"[-] [{app_id}] Patch returned failure.")
        return False

    config = {}
    try:
        config = load_app_config(app_id)
    except Exception:
        # Keep patch runner resilient in unit tests and local ad-hoc runs.
        config = {}

    clone_config = config.get("clone_config")
    if clone_config:
        print(f"[*] [{app_id}] Applying clone configuration...")
        if not run_clone(decompiled_dir, clone_config):
            print(f"[-] [{app_id}] Clone stage failed.")
            return False

    version_suffix = config.get("version_name_suffix")
    if version_suffix:
        print(f"[*] [{app_id}] Applying version suffix '{version_suffix}'...")
        apply_version_suffix(decompiled_dir, version_suffix)
    
    inject_updater = bool(config.get("inject_updater", True))
    if inject_updater:
        target_smali = config.get("updater_target_smali")
        print(f"[*] [{app_id}] Applying updater injection...")
        updater_success = inject_universal_updater(
            decompiled_dir=decompiled_dir,
            app_id=app_id,
            target_activity_smali=target_smali,
        )
        if not updater_success:
            print(f"[-] [{app_id}] Updater injection failed.")
            return False
    else:
        print(f"[*] [{app_id}] Updater injection disabled by config.")

    print(f"[+] [{app_id}] Patch completed successfully!")

    return True
