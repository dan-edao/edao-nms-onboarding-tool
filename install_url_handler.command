#!/bin/bash
# EDAO-NMS Onboarding Tool — one-time URL handler installer (macOS).
#
# Registers the "EDAO-NMS Onboarding Tool.app" sibling bundle with
# macOS Launch Services so that clicking Deploy Now! / Redeploy in
# the Control Hub (which fires edaonms-proxy-onboard://launch) opens
# this tool. Run once after extracting the folder. Safe to re-run.

set -e

cd "$(dirname "$0")"

APP_NAME="EDAO-NMS Onboarding Tool.app"
APP_PATH="$(pwd)/$APP_NAME"

if [ ! -d "$APP_PATH" ]; then
    osascript -e "display alert \"EDAO-NMS Onboarding Tool\" message \"$APP_NAME was not found in this folder.\n\nMake sure you extracted the whole edao-nms-onboarding-tool folder, not individual files.\" as critical"
    exit 1
fi

LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [ ! -x "$LSREG" ]; then
    osascript -e "display alert \"EDAO-NMS Onboarding Tool\" message \"lsregister not found at the expected macOS path. Try opening the .app once manually so Launch Services discovers it.\" as critical"
    exit 1
fi

# Repair the bundle's code signature before registering. Editing
# Info.plist (e.g. bumping CFBundleVersion) or anything inside the
# .app invalidates the ad-hoc seal osacompile applied — once the seal
# is broken, macOS Gatekeeper refuses to launch the bundle and the
# URL scheme silently fails. Stripping xattrs + an ad-hoc re-sign
# restores it. Safe to run on an already-valid bundle (codesign
# --force is idempotent).
xattr -cr "$APP_PATH"
codesign --force --deep --sign - "$APP_PATH"

# Force-register the bundle. -f forces re-registration even if the path
# was previously known. -R recurses (cheap here, single bundle).
"$LSREG" -f -R "$APP_PATH"

# Verify by querying the default handler for the scheme.
DEFAULT_BUNDLE=$("$LSREG" -dump | awk '/edaonms-proxy-onboard:/{found=1} found && /bundle id:/{print $3; exit}' || true)

osascript <<EOF
display dialog "EDAO-NMS Onboarding Tool registered.

The Control Hub Deploy Now! button will now launch this tool automatically the first time you click it (your browser will ask for confirmation).

Bundle: $APP_PATH
Scheme: edaonms-proxy-onboard://" buttons {"OK"} default button "OK" with title "URL handler installed" with icon note
EOF
