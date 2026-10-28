"""Security Auditor: Secret Leak Scanner.

Scans the repository codebase to guarantee no AWS Access Keys, Secret Keys,
or private credentials are accidentally committed to Git.
"""
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Regex patterns for common credentials
CREDENTIAL_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]", "AWS Secret Access Key in Code"),
    (r"-----BEGIN [A-Z ]+ PRIVATE KEY-----", "Private Key Header"),
]

# Directories and files to exclude from source scan
EXCLUDE_DIRS = {".git", "venv", ".venv", "__pycache__", ".pytest_cache"}
EXCLUDE_FILES = {".env", ".env.local"}  # .env is local-only, excluded by .gitignore


def scan_for_secrets() -> bool:
    """Scan all project files for credential leaks."""
    print("=" * 76)
    print("           DEVSECOPS CODEBASE SECURITY & SECRET AUDIT")
    print("=" * 76)
    print(f" Scanning root: {PROJECT_ROOT}")
    print("-" * 76)

    found_violations = []

    # 1. Verify that .gitignore includes .env
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        print("[X] CRITICAL: .gitignore file is missing!")
        return False

    gitignore_content = gitignore_path.read_text(encoding="utf-8")
    if ".env" not in gitignore_content:
        print("[X] CRITICAL: .gitignore must include '.env' to prevent credential leaks!")
        return False
    else:
        print("[+] Verified: '.env' is actively blocked by .gitignore.")

    # 2. Scan source code files
    for file_path in PROJECT_ROOT.rglob("*"):
        # Skip directories
        if not file_path.is_file():
            continue

        # Skip excluded dirs and files
        if any(part in EXCLUDE_DIRS for part in file_path.parts):
            continue
        if file_path.name in EXCLUDE_FILES:
            continue
        if file_path.suffix in [".parquet", ".pyc", ".png", ".jpg", ".ico"]:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, desc in CREDENTIAL_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                # Exclude obvious documentation placeholders
                filtered = [
                    m for m in matches if "AKIAIOSFODNN7EXAMPLE" not in m and "YOUR_ACCESS_KEY" not in m
                ]
                if filtered:
                    found_violations.append((file_path.relative_to(PROJECT_ROOT), desc, len(filtered)))

    print("-" * 76)
    if found_violations:
        print("[X] SECURITY LEAKS DETECTED! DO NOT COMMIT TO GIT:")
        for rel_path, desc, count in found_violations:
            print(f"    - {rel_path}: {count} instance(s) of {desc}")
        print("=" * 76)
        return False

    print("[+] AUDIT PASSED: Zero AWS secrets detected in source code or tracked files!")
    print("    Repository is clean and safe to commit and push to GitHub.")
    print("=" * 76)
    return True


if __name__ == "__main__":
    is_clean = scan_for_secrets()
    sys.exit(0 if is_clean else 1)
