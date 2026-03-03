# APK Patcher

Modular automation for downloading, patching, signing, and publishing Android APK updates.

Live site: https://cfopuser.github.io/app-store/

## Pipeline

The project now follows one clean flow with explicit stages:

1. `download_app` checks source metadata and downloads only when a new version exists.
2. Optional `pre_patch.py` runs APK-level patching (per app).
3. Optional `apk-mitm` stage runs unless disabled per app.
4. App `patch.py` runs decompiled-smali/resource patching.
5. Optional clone stage runs from `clone_config` in `app.json`.
6. Universal updater injection runs by default (configurable per app).
7. CI rebuilds, signs, tags, and publishes release assets.

## App Module Contract

Each app lives in `apps/<app_id>/`:

- `app.json` required metadata + behavior flags.
- `patch.py` required with `patch(decompiled_dir) -> bool`.
- `pre_patch.py` optional with `pre_patch(apk_path) -> bool`.
- `version.txt` tracked current upstream version.
- `status.json` last pipeline result.

## Local Usage

```bash
python run.py --list
python run.py --app whatsapp --step download
python run.py --app whatsapp --step patch
```

## Configuration Flags (`app.json`)

- `skip_mitm` (bool): skip `apk-mitm`.
- `inject_updater` (bool): enable/disable universal updater injection (default: `true`).
- `updater_target_smali` (str): force a specific activity smali path for updater hook.
- `clone_config` (object): apply package clone transformation after patching.

## License

See [LICENSE](LICENSE).
