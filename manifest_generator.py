import os
import hashlib
import json

# ==========================================
# Run this script BEFORE uploading a new update to your server.
# It will generate a manifest.json file containing the hashes of your app files.
# ==========================================

VERSION = "0.0.3"

# We want the manifest to go directly into the built PyInstaller folder
BUILD_DIR = os.path.abspath(os.path.join("dist", "AstroBasics"))
OUTPUT_FILE = os.path.join(BUILD_DIR, "manifest.json")

# Files and folders to EXCLUDE from the update checks
EXCLUDE_DIRS = ['update_cache', 'autosave', 'analysis_export', 'created chart exports','saves', '__pycache__']
EXCLUDE_FILES = ['manifest.json', 'astro_settings.json', 'custom_vargas.json', 'apply_update.bat', 'apply_update.sh', '.hash_cache.json']

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file, normalizing line endings for text files."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    
    # Extensions that are susceptible to Git CRLF <-> LF modification
    text_extensions = {'.py', '.json', '.txt', '.md', '.bat', '.sh', '.csv'}
    _, ext = os.path.splitext(filepath)
    
    try:
        with open(filepath, 'rb') as f:
            if ext.lower() in text_extensions:
                # Strip carriage returns so \r\n and \n both become purely \n before hashing
                content = f.read()
                content = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                hasher.update(content)
            else:
                # Binary files are hashed exactly as they are
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
    except Exception:
        return None
        
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