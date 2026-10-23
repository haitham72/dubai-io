#!/bin/zsh
# S0 screenshot harness (docs/plan/ios-upgrade.md): build, install and screenshot
# every screen on both phone sizes in light and dark.
# Usage: apps/ios/tools/screens.sh [out_dir] [api_url]
# Needs a running Dubai-io API, e.g.: cd apps/api && .venv/bin/python -m uvicorn app.main:app --port 8030
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=${1:-$REPO/output/ios-screens/$(date +%Y%m%d-%H%M)}
mkdir -p "$OUT" && OUT=$(cd "$OUT" && pwd)
cd "$REPO/apps/ios"
API=${2:-http://127.0.0.1:8030}
SCREENS=(${=SCREENS_ONLY:-intro home chat services feed ask me maps})
DEVICES=("iPhone 17 Pro" "iPhone 17 Pro Max")
BUNDLE=com.dubaiio.companion.dev
DERIVED=$REPO/output/ios-build

curl -sf "$API/api/session" >/dev/null || { echo "API not reachable at $API" >&2; exit 1; }
# arm64 only: the x86_64 slice fails to resolve the local DubaiIOCore package.
xcodebuild -project DubaiIO.xcodeproj -scheme DubaiIO -configuration Debug \
  -destination 'generic/platform=iOS Simulator' -derivedDataPath "$DERIVED" \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=YES CODE_SIGNING_ALLOWED=NO -quiet build
APP=$DERIVED/Build/Products/Debug-iphonesimulator/DubaiIO.app
mkdir -p "$OUT"
for device in "${DEVICES[@]}"; do
  xcrun simctl boot "$device" 2>/dev/null || true
  xcrun simctl bootstatus "$device" -b >/dev/null
  xcrun simctl install "$device" "$APP"
  for mode in light dark; do
    xcrun simctl ui "$device" appearance $mode
    for screen in "${SCREENS[@]}"; do
      xcrun simctl terminate "$device" $BUNDLE 2>/dev/null || true
      seen=YES; [[ $screen == intro ]] && seen=NO
      xcrun simctl launch "$device" $BUNDLE -screen $screen -apiAddress "$API" -hasSeenNativeIntro $seen >/dev/null
      sleep 5
      xcrun simctl io "$device" screenshot "$OUT/${device// /-}_${mode}_${screen}.png" >/dev/null 2>&1
    done
  done
done
echo "Saved $(ls "$OUT" | wc -l | tr -d ' ') screenshots to $OUT"
