#!/bin/sh
# Official Jameica archive; checksums verified against Homebrew's 2.12.0 cask.
# No banking credentials, macOS security overrides, or bank requests.
set -eu

case "$(uname -s)" in
  Darwin) ;;
  *) echo 'This installer is for macOS.' >&2; exit 1 ;;
esac
case "$(uname -m)" in
  arm64)
    archive_arch='-aarch64'
    expected_sha='0d01567ae868e3f4c73a03c809bf5f0379c37e1cd408563f5cab4b12c47feb20'
    ;;
  x86_64)
    archive_arch='64'
    expected_sha='1d275e20a02876d3dbd6b042b4bfc2db1e98917854e50f3028c3189a14f8ec41'
    ;;
  *) echo 'Unsupported Mac architecture.' >&2; exit 1 ;;
esac

install_dir="$HOME/Applications"
app_path="$install_dir/jameica.app"
if [ -e "$app_path" ] || [ -e /Applications/jameica.app ]; then
  echo 'Jameica is already installed; existing installation was left intact.'
  exit 0
fi

stage_dir=$(mktemp -d "${TMPDIR:-/tmp}/ing-jameica.XXXXXX")
trap 'rm -rf "$stage_dir"' EXIT HUP INT TERM
archive_path="$stage_dir/jameica.zip"
archive_url="https://www.willuhn.de/products/jameica/releases/current/jameica/jameica-macos${archive_arch}-2.12.0.zip"

printf 'Downloading Jameica 2.12.0 from the official project...\n'
/usr/bin/curl --fail --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 15 --max-time 600 "$archive_url" --output "$archive_path"
actual_sha=$(/usr/bin/shasum -a 256 "$archive_path")
actual_sha=${actual_sha%% *}
if [ "$actual_sha" != "$expected_sha" ]; then
  echo 'Archive checksum differs from the verified 2.12.0 release. Installation stopped.' >&2
  exit 1
fi
/usr/bin/ditto -x -k "$archive_path" "$stage_dir/unpacked"
if [ ! -d "$stage_dir/unpacked/jameica.app" ]; then
  echo 'Unexpected archive layout. Installation stopped.' >&2
  exit 1
fi
mkdir -p "$install_dir"
# Recheck after download, and refuse to overwrite an installation.
if [ -e "$app_path" ]; then
  echo 'Jameica appeared during download; installation stopped without overwriting it.' >&2
  exit 1
fi
mv "$stage_dir/unpacked/jameica.app" "$app_path"
printf 'Installed: %s\n' "$app_path"
printf 'Opening Jameica. Configure Hibiscus and Depot-Viewer inside the app.\n'
/usr/bin/open "$app_path"
