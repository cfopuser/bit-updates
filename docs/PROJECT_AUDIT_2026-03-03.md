# Project Audit Report (2026-03-03)

Repository: `bit-updates`  
Audit focus: full-project deep dive with extra focus on WhatsApp patching flow  
Audited on: 2026-03-03

## Scope and Method

- Reviewed entrypoint orchestration, downloader/source adapters, patch runners, updater injector, per-app patch scripts, workflow automation, frontend release browser, and test suite.
- Executed validation commands:
  - `python -m compileall -q run.py core apps`
  - `python -m pytest -q`
  - `python run.py --list`
  - `python run.py --app whatsapp --step patch`
- Performed targeted runtime probes for source behavior and config sanity checks.

## High-Level Architecture

- Orchestration: [`run.py`](../run.py) controls `download -> binary patch -> mitm -> pre-patch -> patch`.
- Download system: [`core/downloader.py`](../core/downloader.py) delegates source logic via [`core/sources/registry.py`](../core/sources/registry.py).
- Source adapters:
  - APKMirror: [`core/sources/apkmirror.py`](../core/sources/apkmirror.py)
  - Aptoide: [`core/sources/aptoide.py`](../core/sources/aptoide.py)
  - APKPure: [`core/sources/apkpure.py`](../core/sources/apkpure.py)
  - Aurora/Play: [`core/sources/aurora.py`](../core/sources/aurora.py)
  - GitHub releases: [`core/sources/github.py`](../core/sources/github.py)
- Patching:
  - Dynamic app patch loader: [`core/patcher.py`](../core/patcher.py)
  - Optional binary pre-decompile patch: [`core/binary_plugin.py`](../core/binary_plugin.py)
  - Optional pre-patch stage: [`core/pre_patcher.py`](../core/pre_patcher.py)
  - Universal updater injection: [`core/universal_updater.py`](../core/universal_updater.py)
- CI/CD: [`.github/workflows/apk_patcher.yml`](../.github/workflows/apk_patcher.yml)
- Frontend release portal: [`index.html`](../index.html)

## WhatsApp Deep Dive

WhatsApp app config: [`apps/whatsapp/app.json`](../apps/whatsapp/app.json)

Observed pipeline behavior:
- `download` step executes both:
  - binary patch module ([`apps/whatsapp/binary_patch.py`](../apps/whatsapp/binary_patch.py))
  - pre-patch module ([`apps/whatsapp/pre_patch.py`](../apps/whatsapp/pre_patch.py))
- Both scripts clone `Schwartzblat/WhatsAppPatcher`, install dependencies, patch patcher internals, and run patching.
- `patch` step fails because [`apps/whatsapp/patch.py`](../apps/whatsapp/patch.py) is empty (0 bytes), while core patch runner requires a callable `patch()`.

Operational and security implications:
- Duplicate patch passes on same APK increase build time and fragility.
- Runtime cloning + dynamic `pip install` from external sources on each build introduces high supply-chain risk.
- No commit pinning for external patcher repo means behavior changes without repository changes here.

## Findings (Prioritized)

### Critical

1. WhatsApp patch stage is guaranteed to fail.
- Evidence:
  - [`apps/whatsapp/patch.py`](../apps/whatsapp/patch.py) length is `0`.
  - [`core/patcher.py:43`](../core/patcher.py#L43) requires callable `patch`.
  - Runtime repro: `python run.py --app whatsapp --step patch` fails with `patch.py does not have a callable 'patch' function`.
- Impact: WhatsApp cannot pass CI patch step/release.
- Fix:
  - Add minimal `def patch(decompiled_dir): return True` to WhatsApp patch module if binary/pre patching is authoritative.
  - Or move WhatsApp logic to decompile patch stage and keep one patch system only.

2. Download errors are treated as "no update" success.
- Evidence:
  - Downloader returns identical `(False, None)` for both "no update" and many error paths: [`core/downloader.py:139`](../core/downloader.py#L139), [`core/downloader.py:152`](../core/downloader.py#L152), [`core/downloader.py:156`](../core/downloader.py#L156), [`core/downloader.py:216`](../core/downloader.py#L216).
  - Orchestrator interprets `not update_needed` as success/no-op: [`run.py:67`](../run.py#L67) and [`run.py:68`](../run.py#L68).
  - CI gates all downstream steps on `update_needed == 'true'`: [`.github/workflows/apk_patcher.yml:84`](../.github/workflows/apk_patcher.yml#L84).
- Impact: Source/network failures are silently hidden; app may stop updating with green workflow.
- Fix:
  - Return tri-state result, e.g. `(status, update_needed, version)` where status is `ok|no_update|error`.
  - Fail pipeline explicitly on download/search/source errors.

3. Clone subsystem is broken by syntax error.
- Evidence:
  - Compile failure at [`core/cloner.py:28`](../core/cloner.py#L28).
  - `compileall` reports `SyntaxError: unterminated string literal`.
- Impact: Clone functionality is unusable when/if integrated; dead code masks intent.
- Fix:
  - Repair namespace string literals in `cloner.py`.
  - Add tests and wire clone execution only after it passes.

### High

4. WhatsApp duplicate patch systems with unpinned external code execution.
- Evidence:
  - Binary patch runs external clone/install: [`apps/whatsapp/binary_patch.py:23`](../apps/whatsapp/binary_patch.py#L23), [`apps/whatsapp/binary_patch.py:30`](../apps/whatsapp/binary_patch.py#L30), [`apps/whatsapp/binary_patch.py:35`](../apps/whatsapp/binary_patch.py#L35).
  - Pre-patch repeats same flow: [`apps/whatsapp/pre_patch.py:22`](../apps/whatsapp/pre_patch.py#L22), [`apps/whatsapp/pre_patch.py:26`](../apps/whatsapp/pre_patch.py#L26), [`apps/whatsapp/pre_patch.py:27`](../apps/whatsapp/pre_patch.py#L27).
  - Both stages are triggered in one run: [`run.py:71`](../run.py#L71), [`run.py:84`](../run.py#L84).
- Impact: Runtime instability, performance drag, and elevated supply-chain risk.
- Fix:
  - Keep only one stage (`binary_patch` or `pre_patch`) for WhatsApp.
  - Pin external repository to commit/tag.
  - Pin dependency versions with hashes.
  - Prefer prebuilt/verified patcher artifact over live `pip install` from test index.

5. Windows CLI crash due Unicode summary symbols.
- Evidence:
  - Summary uses `"✓ OK"`/`"✗ FAILED"`: [`run.py:213`](../run.py#L213).
  - Repro in current environment triggered `UnicodeEncodeError` after WhatsApp failure.
- Impact: Local Windows runs crash after processing, reducing debuggability.
- Fix:
  - Replace with ASCII-only status strings (`OK`/`FAILED`) or configure UTF-8 output fallback.

6. Repository identity drift across components.
- Evidence:
  - Frontend hardcodes repo `cfopuser/app-store`: [`index.html:214`](../index.html#L214).
  - Universal updater default fallback points elsewhere: [`core/universal_updater.py:76`](../core/universal_updater.py#L76), [`core/universal_updater.py:77`](../core/universal_updater.py#L77).
  - Spotify patch has same hardcoded fallback: [`apps/spotify/patch.py:120`](../apps/spotify/patch.py#L120), [`apps/spotify/patch.py:121`](../apps/spotify/patch.py#L121).
- Impact: Fork/local runs can emit updater URLs that point to unrelated repositories.
- Fix:
  - Standardize repo resolution in one utility.
  - Require explicit repo env in CI and local `.env` for deterministic behavior.

### Medium

7. Test suite mixes unit tests with live-network integration and side effects.
- Evidence:
  - Failing test assumes version file creation that production code intentionally does not do: [`tests/test_aptoide_download.py:35`](../tests/test_aptoide_download.py#L35).
  - Network-dependent tests call `sys.exit(1)`: [`tests/test_aptoide.py:22`](../tests/test_aptoide.py#L22), [`tests/test_apkmirror.py:36`](../tests/test_apkmirror.py#L36).
- Impact: Flaky CI, slow tests, false negatives unrelated to code regressions.
- Fix:
  - Convert source tests to mocked unit tests by default.
  - Move live-network tests to optional integration suite (`-m integration`).

8. CI writes to `main` from parallel matrix jobs.
- Evidence:
  - Matrix build per app: [`.github/workflows/apk_patcher.yml:47`](../.github/workflows/apk_patcher.yml#L47).
  - Each matrix job rebases and pushes main directly: [`.github/workflows/apk_patcher.yml:157`](../.github/workflows/apk_patcher.yml#L157), [`.github/workflows/apk_patcher.yml:158`](../.github/workflows/apk_patcher.yml#L158).
- Impact: Race conditions and overwrite risk during simultaneous app updates.
- Fix:
  - Upload per-app artifacts/status first, then single serialized publish job.
  - Use concurrency groups or protected branch workflow dispatch.

9. Release API pagination not handled in frontend.
- Evidence:
  - Frontend requests only default releases endpoint once: [`index.html:215`](../index.html#L215).
- Impact: Older releases can disappear from UI when repository grows.
- Fix:
  - Add `?per_page=100` and/or pagination follow-up requests.

10. Metadata hygiene issues.
- Evidence:
  - Leading space in package name: [`apps/termux/app.json:5`](../apps/termux/app.json#L5).
  - App ID mismatch (`Bank Yahav` vs folder `yahav`): [`apps/yahav/app.json:2`](../apps/yahav/app.json#L2).
- Impact: Inconsistent conventions, possible tool incompatibility over time.
- Fix:
  - Enforce schema validation pre-commit/CI.

## Validation Results

- `compileall`: failed (syntax error in `core/cloner.py`).
- `pytest`: `15 passed, 1 failed`.
  - Failing test: `tests/test_aptoide_download.py::test_aptoide_download` due cleanup assumption mismatch.
- Runtime:
  - `python run.py --list`: succeeds.
  - `python run.py --app whatsapp --step patch`: fails on empty WhatsApp patch module; then crashes on Windows Unicode summary output.

## Documentation Gaps

- No explicit architecture document for stage ordering and failure semantics.
- No contract document defining downloader return states (`error` vs `no update`).
- No security policy for external patch tool ingestion (repo pinning, hash pinning, trust model).
- No schema spec for `app.json` fields and validation rules.

## Recommended Remediation Plan

### Immediate (same day)

1. Fix WhatsApp patch stage (`apps/whatsapp/patch.py` callable).
2. Split downloader result states and fail on actual errors.
3. Replace Unicode summary symbols in `run.py` with ASCII.
4. Repair `core/cloner.py` syntax so repository compiles cleanly.

### Short-term (1 week)

1. Consolidate WhatsApp patching to one stage.
2. Pin external patcher repo and dependency versions.
3. Convert live network tests into isolated/mock tests by default.
4. Add schema validation for all `app.json` files.

### Medium-term (2-4 weeks)

1. Refactor CI to avoid parallel direct pushes to `main`.
2. Centralize repository URL resolution (frontend + updater + patch scripts).
3. Add integration contract tests for each pipeline stage.

## Suggested New Docs

- `docs/ARCHITECTURE.md` (pipeline, stage contracts, state transitions)
- `docs/APP_CONFIG_SCHEMA.md` (required fields and validation rules)
- `docs/SECURITY_SUPPLY_CHAIN.md` (pinning and external dependency policy)
- `docs/TEST_STRATEGY.md` (unit/integration split and network policy)
