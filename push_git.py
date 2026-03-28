import re
import subprocess

FILE = "manifest_generator.py"

def get_version():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r'VERSION\s*=\s*["\'](.+?)["\']', content)
    if not match:
        raise ValueError("VERSION not found")

    return match.group(1)

def run_git(version):
    commit_msg = f"v{version}: auto commit from manifest"

    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

if __name__ == "__main__":
    version = get_version()
    print(f"Detected version: {version}")
    run_git(version)