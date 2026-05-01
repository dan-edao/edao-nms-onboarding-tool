#!/bin/bash
# EDAO-NMS Onboarding Tool — macOS launcher (self-healing).
# Double-click this file to start the tool.
# First time: right-click → Open (to bypass Gatekeeper).
#
# Tool version label is in edao_onboard.py — this script intentionally
# does NOT carry a version number so it doesn't drift on every release.

cd "$(dirname "$0")"

export TK_SILENCE_DEPRECATION=1

# ── Self-heal the .app sibling ────────────────────────────────────────
# macOS Launch Services refuses to open a bundle whose ad-hoc seal has
# been invalidated (e.g. someone bumped CFBundleVersion in Info.plist
# or modified main.scpt). When that happens, the Control Hub's Deploy
# Now! → edaonms-proxy-onboard:// handoff silently fails — the URL
# fires but no window appears.
#
# This launcher always runs in-process (not via Launch Services), so
# we can be sure it executes regardless of the .app's seal state. We
# verify the seal here and re-sign + re-register if it's broken, so
# whenever the operator falls back to double-clicking this script
# directly, the bundle is repaired in passing and the next URL launch
# from the Control Hub works again.
#
# No-ops on a healthy bundle (codesign --verify exit 0).
APP_BUNDLE="$(pwd)/EDAO-NMS Onboarding Tool.app"
if [ -d "$APP_BUNDLE" ]; then
    if ! /usr/bin/codesign --verify --deep --strict "$APP_BUNDLE" >/dev/null 2>&1; then
        echo "[launcher] .app bundle seal broken — auto-repairing"
        /usr/bin/xattr -cr "$APP_BUNDLE" 2>/dev/null
        /usr/bin/codesign --force --deep --sign - "$APP_BUNDLE" >/dev/null 2>&1
        /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
            -f -R "$APP_BUNDLE" >/dev/null 2>&1
    fi
fi

# Pick a Python that has a working Tk (>= 8.6).
# Apple's stock /usr/bin/python3 ships Tk 8.5, which renders blank windows
# on modern macOS — we explicitly skip it and prefer python.org / Homebrew.
CANDIDATES=(
    /Library/Frameworks/Python.framework/Versions/3.13/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.11/bin/python3
    /Library/Frameworks/Python.framework/Versions/3.10/bin/python3
    /opt/homebrew/bin/python3
    /usr/local/bin/python3
    /usr/bin/python3
)

PY=""
PY_REASON=""
for cand in "${CANDIDATES[@]}"; do
    [ -x "$cand" ] || continue
    # Probe: tkinter importable AND Tk >= 8.6.
    out=$("$cand" -c 'import sys, tkinter; v=float(tkinter.TkVersion); sys.exit(0 if v>=8.6 else 2)' 2>/dev/null)
    rc=$?
    if [ $rc -eq 0 ]; then
        PY="$cand"
        break
    elif [ $rc -eq 2 ] && [ -z "$PY_REASON" ]; then
        PY_REASON="old_tk"
    elif [ -z "$PY_REASON" ]; then
        PY_REASON="no_tkinter"
    fi
done

if [ -z "$PY" ]; then
    if [ "$PY_REASON" = "old_tk" ]; then
        MSG="The Python interpreter on this Mac uses Tk 8.5, which renders blank windows on recent macOS versions.\n\nFix (one of):\n  •  Install Python from python.org (bundles Tk 8.6)\n  •  brew install python-tk@3.14   (or your Homebrew Python version)\n\nThen re-launch this tool."
        TITLE="Tk 8.5 detected — UI will not render"
    elif [ "$PY_REASON" = "no_tkinter" ]; then
        MSG="The Python interpreter on this Mac is missing the tkinter module.\n\nFix (one of):\n  •  Install Python from python.org (tkinter included)\n  •  brew install python-tk@3.14   (or your Homebrew Python version)\n\nThen re-launch this tool."
        TITLE="tkinter not installed"
    else
        MSG="Install Python 3.10+ from python.org (recommended) or via Homebrew:\n  brew install python3 python-tk@3.14"
        TITLE="Python 3 not found"
    fi
    osascript -e "display alert \"$TITLE\" message \"$MSG\" as critical"
    exit 1
fi

exec "$PY" edao_onboard.py
