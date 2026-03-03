# Contributing a New App

## Prerequisites

- Python 3.10+
- Basic understanding of APK structure and smali patching
- Android package name (for example `com.example.app`)

## 1. Fork and Clone

```bash
git clone https://github.com/cfopuser/app-store.git
cd app-store
pip install -r requirements.txt
```

## 2. Create App Directory

```bash
mkdir -p apps/your-app
```

## 3. Create `app.json`

`apps/your-app/app.json`:

```json
{
  "id": "your-app",
  "name": "Your App Name",
  "package_name": "com.example.app",
  "description": "What this patched app changes",
  "icon_url": "https://example.com/icon.png",
  "source": "apkmirror",
  "maintainer": "your-github-username",
  "skip_mitm": false,
  "inject_updater": true,
  "version_file": "apps/your-app/version.txt",
  "status_file": "apps/your-app/status.json"
}
```

## 4. Create `patch.py` (Required)

`apps/your-app/patch.py`:

```python
def patch(decompiled_dir: str) -> bool:
    # Apply decompiled APK changes here
    return True
```

## 5. Optional `pre_patch.py`

Use this only for APK-level work before decompile:

```python
def pre_patch(apk_path: str) -> bool:
    return True
```

## 6. Initialize Version and Status

```bash
echo "0.0.0" > apps/your-app/version.txt
echo '{"success": true, "failed_version": "", "error_message": "", "updated_at": ""}' > apps/your-app/status.json
```

## 7. Test Locally

```bash
python run.py --list
python run.py --app your-app --step download
python run.py --app your-app --step patch
```

## 8. Open Pull Request

Push and open PR with:

- app folder contents
- patch logic explanation
- test evidence (logs or screenshots)

## Guidelines

- One app per folder under `apps/`.
- `patch.py` must exist and return bool.
- Use `pre_patch.py` for APK-level manipulation only.
- Print meaningful progress logs with `[+]`, `[-]`, `[*]`.
- Do not call `sys.exit()` from app patch modules.
- Keep regex/smali patterns resilient across upstream app versions.
