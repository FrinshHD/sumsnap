#!/bin/bash
set -e
REPO_OWNER="frinshhd"
REPO_NAME="sumsnap"

echo "Downloading latest sumsnap for Linux..."
URL=$(curl -s https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/releases/latest | grep "browser_download_url.*sumsnap-linux" | cut -d '"' -f 4)
curl -L "$URL" -o sumsnap
chmod +x sumsnap
echo "Moving sumsnap to /usr/local/bin (requires sudo)..."
sudo mv sumsnap /usr/local/bin/sumsnap
echo "Installed! Run 'sumsnap' from anywhere."

# Install shell completions
echo "Installing shell completions..."
/usr/local/bin/sumsnap --install-completion bash
/usr/local/bin/sumsnap --install-completion zsh
/usr/local/bin/sumsnap --install-completion fish
echo "Shell completions installed. Restart your terminal or source your shell profile to activate completions."