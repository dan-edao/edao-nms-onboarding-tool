#!/bin/bash
# EDAO-NMS Onboarding Tool — macOS launcher
# Double-click this file to start the tool.

cd "$(dirname "$0")"

if ! command -v python3 &>/dev/null; then
    osascript -e 'display alert "Python 3 not found" message "Install Python 3.9+ from python.org or via Homebrew:\n  brew install python3" as critical'
    exit 1
fi

python3 edao_onboard.py
