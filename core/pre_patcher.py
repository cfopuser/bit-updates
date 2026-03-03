"""
Pre-patch runner — dynamically loads an app's pre_patch.py module.
This runs before decompilation, allowing for APK-level manipulations (like Schwartzblat's Patcher).
"""

import importlib.util
import os


def run_pre_patch(app_id: str, apk_path: str = "latest.apk") -> bool:
    """
    Import apps/{app_id}/pre_patch.py and call its pre_patch(apk_path) function.

    Args:
        app_id: The app identifier (subfolder name under apps/).
        apk_path: Path to the APK file to be pre-patched.

    Returns:
        True if the pre-patch was applied successfully (or if no pre-patch exists),
        False if the pre-patch failed.
    """
    pre_patch_module_path = os.path.join("apps", app_id, "pre_patch.py")

    if not os.path.isfile(pre_patch_module_path):
        # Pre-patch is optional, so return True if not found.
        return True

    print(f"[*] [{app_id}] Loading pre-patch module: {pre_patch_module_path}")

    try:
        spec = importlib.util.spec_from_file_location(
            f"apps.{app_id}.pre_patch", pre_patch_module_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"[-] [{app_id}] Failed to load pre-patch module: {e}")
        return False

    if not hasattr(module, "pre_patch") or not callable(module.pre_patch):
        print(f"[-] [{app_id}] pre_patch.py does not have a callable 'pre_patch' function")
        return False

    print(f"[*] [{app_id}] Running pre-patch on: {apk_path}")
    try:
        result = module.pre_patch(apk_path)
    except Exception as e:
        print(f"[-] [{app_id}] Pre-patch raised an exception: {e}")
        return False

    if not result:
        print(f"[-] [{app_id}] Pre-patch returned failure.")
        return False

    print(f"[+] [{app_id}] Pre-patch completed successfully!")
    return True
