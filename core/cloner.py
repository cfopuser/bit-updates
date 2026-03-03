"""
Package clone transformer for decompiled APKs.
"""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET


ANDROID_NS = "http://schemas.android.com/apk/res/android"


def _resolve_component_name(name: str, package_name: str) -> str:
    if not name:
        return name
    if name.startswith("."):
        return package_name + name
    if "." not in name:
        return f"{package_name}.{name}"
    return name


def _update_manifest(decompiled_dir: str, old_pkg: str, new_pkg: str) -> bool:
    manifest_path = os.path.join(decompiled_dir, "AndroidManifest.xml")
    if not os.path.exists(manifest_path):
        print("[-] [Cloner] AndroidManifest.xml not found.")
        return False

    attr_name = f"{{{ANDROID_NS}}}name"
    attr_authorities = f"{{{ANDROID_NS}}}authorities"
    attr_target = f"{{{ANDROID_NS}}}targetActivity"

    ET.register_namespace("android", ANDROID_NS)

    try:
        tree = ET.parse(manifest_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"[-] [Cloner] Failed to parse AndroidManifest.xml: {exc}")
        return False

    manifest_package = root.get("package") or old_pkg

    for tag in ("activity", "activity-alias", "service", "receiver", "provider"):
        for elem in root.iter(tag):
            name = elem.get(attr_name)
            if name:
                elem.set(attr_name, _resolve_component_name(name, manifest_package))

            target = elem.get(attr_target)
            if target:
                elem.set(attr_target, _resolve_component_name(target, manifest_package))

    for provider in root.iter("provider"):
        authorities = provider.get(attr_authorities)
        if not authorities:
            continue
        updated = []
        for authority in authorities.split(";"):
            value = authority.strip()
            if not value:
                continue
            if old_pkg in value:
                updated.append(value.replace(old_pkg, new_pkg))
            elif value.startswith(new_pkg):
                updated.append(value)
            else:
                updated.append(f"{new_pkg}_{value}")
        provider.set(attr_authorities, ";".join(updated))

    for tag in ("permission", "uses-permission", "uses-permission-sdk-23"):
        for elem in root.iter(tag):
            value = (elem.get(attr_name) or "").strip()
            if not value:
                continue
            if value.startswith("android.permission.") or value.startswith("com.android."):
                continue
            if old_pkg in value:
                elem.set(attr_name, value.replace(old_pkg, new_pkg))
            elif value.startswith(new_pkg):
                continue
            else:
                elem.set(attr_name, f"{new_pkg}_{value}")

    root.set("package", new_pkg)

    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)
    print("    [+] [Cloner] AndroidManifest.xml updated.")
    return True


def _update_apktool_yml(decompiled_dir: str, new_pkg: str):
    apktool_yml_path = os.path.join(decompiled_dir, "apktool.yml")
    if not os.path.exists(apktool_yml_path):
        return

    with open(apktool_yml_path, "r", encoding="utf-8") as file:
        content = file.read()

    if "renameManifestPackage:" in content:
        content = re.sub(r"renameManifestPackage:.*", f"renameManifestPackage: {new_pkg}", content)
    else:
        content += f"\nrenameManifestPackage: {new_pkg}\n"

    with open(apktool_yml_path, "w", encoding="utf-8") as file:
        file.write(content)

    print("    [+] [Cloner] apktool.yml updated.")


def _update_app_name_suffix(decompiled_dir: str, suffix: str):
    if not suffix:
        return

    strings_path = os.path.join(decompiled_dir, "res", "values", "strings.xml")
    if not os.path.exists(strings_path):
        return

    try:
        with open(strings_path, "r", encoding="utf-8") as file:
            content = file.read()
    except Exception as exc:
        print(f"    [-] [Cloner] Failed to read strings.xml: {exc}")
        return

    updated = re.sub(
        r'(<string name="app_name">)(.*?)(</string>)',
        rf"\1\2{suffix}\3",
        content,
        count=1,
    )
    if updated == content:
        return

    with open(strings_path, "w", encoding="utf-8") as file:
        file.write(updated)
    print(f"    [+] [Cloner] App name suffix applied: {suffix!r}")


def run_clone(decompiled_dir: str, clone_config: dict) -> bool:
    """
    Apply package clone transformations.
    """
    old_pkg = (clone_config.get("old_pkg") or "").strip()
    new_pkg = (clone_config.get("new_pkg") or "").strip()
    app_name_suffix = clone_config.get("app_name_suffix", " (Cloned)")

    if not old_pkg or not new_pkg:
        print("[-] [Cloner] 'old_pkg' and 'new_pkg' are required.")
        return False

    print(f"[*] [Cloner] Cloning package: {old_pkg} -> {new_pkg}")

    if not _update_manifest(decompiled_dir, old_pkg, new_pkg):
        return False

    _update_apktool_yml(decompiled_dir, new_pkg)
    _update_app_name_suffix(decompiled_dir, app_name_suffix)

    print("    [+] [Cloner] Clone stage completed.")
    return True
