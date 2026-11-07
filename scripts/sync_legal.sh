#!/usr/bin/env bash
# Copies the privacy policy and terms the app shows into docs/, which GitHub Pages serves: App Store Connect needs the
# privacy policy at a public URL. The app's copies are the source of truth; never edit docs/privacy.md or
# docs/terms.md by hand. Run after changing them in the app, then commit docs/.
#   sync_legal.sh [<app Legal folder>]      default: the app checkout next to this repo
set -euo pipefail
cd "$(dirname "$0")/.."
src=${1:-../app/MyNav/Settings/Legal}
page() {  # <source name> <page title> <permalink> <out>
  { printf -- '---\ntitle: %s\npermalink: %s\n---\n\n' "$2" "$3"; cat "$src/$1.md"; } > "docs/$4"
}
page PrivacyPolicy "Privacy Policy" /privacy/ privacy.md
page TermsOfUse "Terms of Use" /terms/ terms.md
