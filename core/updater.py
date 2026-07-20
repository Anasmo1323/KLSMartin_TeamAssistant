import os
import sys
import requests
import subprocess
from core.constants import APP_VERSION, GITHUB_REPO

def parse_version(v):
    try:
        return [int(x) for x in v.replace('v', '').split('.')]
    except:
        return [0, 0, 0]

def check_for_updates():
    """
    Returns (update_available: bool, new_version: str, download_url: str, release_notes: str)
    """
    if not GITHUB_REPO:
        return False, None, None, None
        
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        remote_ver = data.get("tag_name", "0.0.0")
        
        if parse_version(remote_ver) > parse_version(APP_VERSION):
            # Find the .exe asset
            assets = data.get("assets", [])
            download_url = None
            for asset in assets:
                if asset["name"].endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break
            
            if download_url:
                return True, remote_ver, download_url, data.get("body", "")
    except Exception as e:
        print(f"Error checking for updates on GitHub: {e}")
        
    return False, None, None, None

def download_update(download_url, destination, progress_callback=None):
    response = requests.get(download_url, stream=True, timeout=10)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1 MB
    downloaded = 0
    with open(destination, "wb") as f:
        for chunk in response.iter_content(block_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total_size > 0:
                    progress_callback(int(downloaded * 100 / total_size))
                elif progress_callback:
                    progress_callback(-1)

def apply_update_and_restart(new_exe_path):
    """
    Creates a batch script to overwrite the current executable and restarts it.
    """
    current_exe = sys.executable
    # Only run in compiled mode
    if not getattr(sys, 'frozen', False):
        print("Not running in frozen mode. Update simulation complete.")
        return

    bat_path = os.path.join(os.path.dirname(current_exe), "update_swapper.bat")
    
    bat_content = f"""@echo off
timeout /t 3 /nobreak > NUL
set _MEIPASS2=
set _MEIPASS=
move /Y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    with open(bat_path, "w") as f:
        f.write(bat_content)

    clean_env = os.environ.copy()
    clean_env.pop('_MEIPASS2', None)
    clean_env.pop('_MEIPASS', None)

    subprocess.Popen([bat_path], shell=True, env=clean_env, creationflags=subprocess.CREATE_NO_WINDOW)
    sys.exit(0)
