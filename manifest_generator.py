import os, hashlib, json

# ==========================================
# Run this script BEFORE uploading a new update to your server.
# It will generate a manifest.json file containing the hashes of your app files.
# ==========================================

VERSION = "0.3.1"

# We want the manifest to go directly into the built PyInstaller folder
BUILD_DIR = os.path.abspath(os.path.join("dist", "AstroBasics"))
OUTPUT_FILE = os.path.join(BUILD_DIR, "manifest.json")

# Files and folders to EXCLUDE from the update checks
EXCLUDE_DIRS = ['update_cache', 'autosave', 'analysis_export', 'created chart exports', 'saves', '__pycache__']
# Fixed missing comma after icon.ico
EXCLUDE_FILES = ['manifest.json', 'icon.ico', 'astro_settings.json', 'custom_vargas.json', 'apply_update.bat', 'apply_update.sh', '.hash_cache.json', 'unins000.exe', 'unins000.dat']

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file, normalizing line endings and trailing whitespaces for text files."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    
    text_extensions = {
        '.py', '.json', '.txt', '.md', '.bat', '.sh', '.csv', 
        '.ini', '.cfg', '.toml', '.xml', '.yml', '.yaml', '.rst', 
        '.html', '.css', '.js'
    }
    text_filenames = {
        'license', 'licence', 'record', 'installer', 'metadata', 
        'wheel', 'notice', 'readme', 'authors', 'contributors'
    }
    
    _, ext = os.path.splitext(filepath)
    filename = os.path.basename(filepath).lower()
    
    is_text = (ext.lower() in text_extensions) or \
              (filename in text_filenames) or \
              (filename.startswith('license')) or \
              (filename.startswith('readme'))
    
    if not is_text and not ext:
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(8192)
                if chunk and b'\x00' not in chunk:
                    is_text = True
        except Exception:
            pass
    
    try:
        with open(filepath, 'rb') as f:
            if is_text:
                content = f.read()
                content = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                # Robustly ignore trailing spaces on each line and blank lines at EOF
                # This counters Git's autocrlf and EOF-fixer pre-commit hooks
                lines = [line.rstrip(b' \t') for line in content.split(b'\n')]
                while lines and not lines[-1]:
                    lines.pop()
                content = b'\n'.join(lines)
                hasher.update(content)
            else:
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
    
    base_dir = BUILD_DIR
    
    if not os.path.exists(base_dir):
        print(f"Error: Could not find '{base_dir}'. Run PyInstaller first!")
        return
    
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            if file in EXCLUDE_FILES or file.endswith(".pyc"):
                continue
                
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, base_dir)
            rel_path = rel_path.replace("\\", "/") 
            
            manifest["files"][rel_path] = get_file_hash(filepath)
            
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(manifest, f, indent=4)
        
    print(f"Generated {OUTPUT_FILE} for Version {VERSION}")
    print(f"Files tracked: {len(manifest['files'])}")
    print("Upload this file to GitHub for apps to detect that update is available.")

if __name__ == "__main__":
    build_manifest()