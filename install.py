import os
import sys
import platform
import shutil
import stat
import requests

REPO_OWNER = "your-username"  # <-- CHANGE THIS
REPO_NAME = "sumsnap"         # <-- CHANGE THIS

def get_asset_name():
    system = platform.system()
    if system == "Windows":
        return "sumsnap-windows.exe"
    elif system == "Darwin":
        return "sumsnap-macos"
    elif system == "Linux":
        return "sumsnap-linux"
    else:
        print("Unsupported OS")
        sys.exit(1)

def get_latest_release_url():
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    resp = requests.get(api_url)
    resp.raise_for_status()
    data = resp.json()
    asset_name = get_asset_name()
    for asset in data["assets"]:
        if asset["name"] == asset_name:
            return asset["browser_download_url"]
    print(f"Could not find asset {asset_name} in the latest release.")
    sys.exit(1)

def download_and_install():
    asset_name = get_asset_name()
    url = get_latest_release_url()
    print(f"Downloading {asset_name} from {url} ...")
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(asset_name, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded {asset_name}.")

    # Make executable on Unix
    if platform.system() != "Windows":
        st = os.stat(asset_name)
        os.chmod(asset_name, st.st_mode | stat.S_IEXEC)

    # Offer to move to PATH
    move = input("Move the binary to a directory in your PATH for global use? (y/N): ").strip().lower()
    if move == "y":
        if platform.system() == "Windows":
            dest = os.path.expandvars(r"%USERPROFILE%\AppData\Local\Microsoft\WindowsApps")
            dest_file = os.path.join(dest, asset_name)
        else:
            dest = "/usr/local/bin"
            dest_file = os.path.join(dest, "sumsnap")
        try:
            shutil.move(asset_name, dest_file)
            print(f"Moved to {dest_file}. You can now run 'sumsnap' from anywhere.")
        except Exception as e:
            print(f"Failed to move binary: {e}")
            print(f"The binary is in the current directory: {os.path.abspath(asset_name)}")
    else:
        print(f"The binary is in the current directory: {os.path.abspath(asset_name)}")

if __name__ == "__main__":
    download_and_install()