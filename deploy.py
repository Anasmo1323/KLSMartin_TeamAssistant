import os
import sys
import json
import requests
import subprocess
from getpass import getpass
from core.constants import APP_VERSION, GITHUB_REPO

def build_exe():
    print(f"--> Building v{APP_VERSION} with PyInstaller...")
    # Run the pyinstaller build command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name=KLSMartin Team Assistant",
        "--icon=icon.ico",
        "--add-data=icon.ico;.",
        "main.py",
        "-y"
    ]
    
    # We pass the list directly so subprocess handles quotes around spaces
    subprocess.run(cmd, check=True)
    
    exe_path = os.path.join("dist", "KLSMartin Team Assistant.exe")
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Failed to find built exe at {exe_path}")
        
    return exe_path

def create_github_release(token, tag_name, notes):
    print(f"--> Creating GitHub Release {tag_name}...")
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "tag_name": tag_name,
        "name": f"Release {tag_name}",
        "body": notes,
        "draft": False,
        "prerelease": False
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["id"], response.json()["upload_url"].replace("{?name,label}", "")

def upload_asset_to_release(token, upload_url, file_path):
    print(f"--> Uploading {file_path} to GitHub...")
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream"
    }
    
    with open(file_path, "rb") as f:
        params = {"name": os.path.basename(file_path)}
        response = requests.post(upload_url, headers=headers, params=params, data=f)
        response.raise_for_status()
        print("--> Upload complete!")

if __name__ == "__main__":
    print(f"--- KLSMartin Team Assistant Deployer ---")
    print(f"Target Repository: {GITHUB_REPO}")
    print(f"Current Version in code: v{APP_VERSION}")
    
    proceed = input("Do you want to build and deploy this version? (y/n): ")
    if proceed.lower() != 'y':
        sys.exit(0)
        
    notes = input("Enter release notes for this version (or leave blank): ")
    
    # Check for token in env, or ask for it
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("\nTo upload to GitHub, you need a Personal Access Token.")
        print("Generate one here: https://github.com/settings/tokens/new (Check 'repo' scope)")
        token = getpass("Enter your GitHub Token (input will be hidden): ")
        
    if not token:
        print("No token provided. Aborting.")
        sys.exit(1)
        
    try:
        exe_path = build_exe()
        release_id, upload_url = create_github_release(token, f"v{APP_VERSION}", notes)
        upload_asset_to_release(token, upload_url, exe_path)
        print(f"\nSUCCESS! v{APP_VERSION} has been built and deployed to GitHub.")
    except Exception as e:
        print(f"\nERROR: Deployment failed: {e}")
