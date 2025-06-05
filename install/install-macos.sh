#!/bin/bash
set -e
REPO_OWNER="frinshhd"
REPO_NAME="sumsnap"

echo "Downloading latest sumsnap for macOS..."
URL=$(curl -s https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest | grep "browser_download_url.*sumsnap-macos" | cut -d '"' -f 4)
curl -L "$URL" -o sumsnap
chmod +x sumsnap
echo "Moving sumsnap to /usr/local/bin (requires sudo)..."
sudo mv sumsnap /usr/local/bin/sumsnap
echo "Installed! Run 'sumsnap' from anywhere."