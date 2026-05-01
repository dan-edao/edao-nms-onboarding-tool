#!/bin/bash
# EDAO-NMS Onboarding Tool v2.13 — macOS launcher
# Double-click this file to start the tool.
# First time: right-click → Open (to bypass Gatekeeper).

cd "$(dirname "$0")"

export TK_SILENCE_DEPRECATION=1

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
