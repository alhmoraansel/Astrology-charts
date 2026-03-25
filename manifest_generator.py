import os, hashlib, json

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
EXCLUDE_FILES = ['manifest.json','icon.ico' 'astro_settings.json', 'custom_vargas.json', 'apply_update.bat', 'apply_update.sh', '.hash_cache.json','unins000.exe','unins000.dat',]

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file, normalizing line endings for text files."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    
    # Extensions that are susceptible to Git CRLF <-> LF modification
    text_extensions = {
        '.py', '.json', '.txt', '.md', '.bat', '.sh', '.csv', 
        '.ini', '.cfg', '.toml', '.xml', '.yml', '.yaml', '.rst', 
        '.html', '.css', '.js'
    }
    # Extensionless text files commonly modified by git (e.g., Python packages)
    text_filenames = {
        'license', 'licence', 'record', 'installer', 'metadata', 
        'wheel', 'notice', 'readme', 'authors', 'contributors'
    }
    
    _, ext = os.path.splitext(filepath)
    filename = os.path.basename(filepath).lower()
    
    # 1. Check if the file is explicitly a known text format/name
    is_text = (ext.lower() in text_extensions) or \
              (filename in text_filenames) or \
              (filename.startswith('license')) or \
              (filename.startswith('readme'))
    
    # 2. Git-style fallback for other extensionless files
    if not is_text and not ext:
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(8192)
                # If the file has no null bytes, treat as text to counter Git CRLF changes
                if chunk and b'\x00' not in chunk:
                    is_text = True
        except Exception:
            pass
    
    try:
        with open(filepath, 'rb') as f:
            if is_text:
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