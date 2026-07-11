# M.I.A. Update Package Specification (v1)

Reference for building an offline update package for the **Update
Manager** (Settings screen → "Apply Update Package..."), per
`docs/ROADMAP.md` milestone 2.8. See `core/update_manager.py` for the
implementation this document describes.

## What an update package is

A zip file containing:

- `update_manifest.json` (required, at the zip root)
- Any project files you want applied, at the **same relative path**
  they have in the project (e.g. `core/module_manager.py`,
  `modules/notes/module.py`, `requirements.txt`)

Applying the package copies every file in it (except the manifest
itself) into the project root at its matching path — overwriting
whatever's already there, and creating new files/folders as needed.
There is no diffing or patching; if a file is in the package, it wins.

## `update_manifest.json`

```json
{
    "app": "M.I.A.",
    "manifest_version": 1,
    "target_version": "0.3.0",
    "description": "Short summary of what this update changes."
}
```

| Field | Required | Notes |
|---|---|---|
| `app` | Yes | Must be exactly `"M.I.A."` — this is the check that tells a real update package apart from an arbitrary zip. |
| `manifest_version` | No | Reserved for future format changes. Not currently checked. |
| `target_version` | No | Free-form; shown in the confirmation dialog so you know what you're about to apply. Defaults to `"unknown"` if omitted. |
| `description` | No | Free-form; shown in the confirmation dialog, and becomes the git commit body if a rollback commit is created. |

## Building one by hand

From a working copy of the repo at the version you want to ship:

```bash
cd mia
mkdir -p /tmp/mia_update/core
cp core/module_manager.py /tmp/mia_update/core/module_manager.py
cat > /tmp/mia_update/update_manifest.json <<'EOF'
{
    "app": "M.I.A.",
    "manifest_version": 1,
    "target_version": "0.2.1",
    "description": "Fixes the rescan() duplicate-module_id warning."
}
EOF
cd /tmp/mia_update
zip -r ../mia_update_0.2.1.zip .
```

Copy `mia_update_0.2.1.zip` to a USB drive (or anywhere reachable) on
the target device, then apply it from Settings.

## What happens when you apply one

1. The zip is validated (real zip, has the manifest, manifest says
   `"app": "M.I.A."`) before anything touches the live project.
2. It's extracted into a staging temp directory first — a corrupt or
   malicious package can't leave a half-applied mess, since nothing is
   copied into the real project until staging succeeds.
3. Every file (except the manifest) is copied into the project root.
4. If the project is a git working tree and `git` is on `PATH`, the
   applied files are staged and committed automatically — **only the
   files this update touched**, not a blanket `git add -A`, so any
   other uncommitted work you had sitting in the tree is left alone.
   This commit is your rollback point: `git revert` if the update
   turns out to be bad.
5. You'll need to restart M.I.A. for changes to Python files to take
   effect — already-imported modules don't hot-reload.

## Security note — read this before applying anything

Applying an update package overwrites files with **no code review and
no sandboxing** — including `core/` and `deploy/` (boot
infrastructure). This is the same trust model `docs/MODULE_SPEC.md`
already asks for when installing a new module: only apply packages you
built yourself or have reviewed and trust, exactly the judgment you'd
apply to running any other script with full access to this device.

## If the update changes `requirements.txt`

Update Manager only copies files — it does not run `pip install`.
If a package changes `requirements.txt`, install the new dependencies
yourself afterward:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```
