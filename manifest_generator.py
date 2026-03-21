import os
import hashlib
import json

# ==========================================
# Run this script BEFORE uploading a new update to your server.
# It will generate a manifest.json file containing the hashes of your app files.
# ==========================================

VERSION = "1.0.1"

# We want the manifest to go directly into the built PyInstaller folder
BUILD_DIR = os.path.abspath(os.path.join("dist", "AstroBasics"))
OUTPUT_FILE = os.path.join(BUILD_DIR, "manifest.json")

# Files and folders to EXCLUDE from the update checks
EXCLUDE_DIRS = ['update_cache', 'autosave', 'analysis_export']
EXCLUDE_FILES = ['manifest.json', 'astro_settings.json', 'apply_update.bat', 'apply_update.sh']

def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def build_manifest():
    manifest = {
        "version": VERSION,
        "files": {}
    }
    
    # Target the PyInstaller build directory, NOT the source root
    base_dir = BUILD_DIR
    
    if not os.path.exists(base_dir):
        print(f"Error: Could not find '{base_dir}'. Run PyInstaller first!")
        return
    
    for root, dirs, files in os.walk(base_dir):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES or file.endswith(".pyc"):
                continue
                
            filepath = os.path.join(root, file)
            # Make path relative to base directory
            rel_path = os.path.relpath(filepath, base_dir)
            # Ensure universal forward-slashes for remote paths
            rel_path = rel_path.replace("\\", "/") 
            
            manifest["files"][rel_path] = get_file_hash(filepath)
            
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Generated {OUTPUT_FILE} for Version {VERSION}")
    print(f"Files tracked: {len(manifest['files'])}")
    print("Upload this file to GitHub. for apps to detect that update is available")

if __name__ == "__main__":
    build_manifest()