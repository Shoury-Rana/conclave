import os
from pathlib import Path
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# ==============================
#       CONFIGURATION
# ==============================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_FILENAME = 'repo_combined_output.txt'
OUTPUT_FILE = BASE_DIR / OUTPUT_FILENAME

# --- File extensions to always skip (non-text/binary/junk) ---
EXCLUDE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.pdf', '.zip', '.mp4', '.mp3', '.jar', '.pyc',
    '.exe', '.db', '.sqlite3', '.log', '.webp', '.ttf', '.ico', '.gif', '.svg',
    '.bin', '.tar', '.gz', '.7z', '.lock'
}

# --- Folder/file patterns to always skip ---
DEFAULT_EXCLUDES = [
    # Core dev & build folders
    '.git', '.github', '.venv', 'venv', '__pycache__', 'node_modules',
    'dist', 'build', 'out', 'coverage', '.next', '.nuxt', 'public', 'android-new',

    # Editor junk
    '.idea', '.vscode',

    # OS/system junk
    '.DS_Store', 'Thumbs.db',

    # Environment/config
    '.env', '.env.local', '.env.production', '.env.development',
]

# --- Specific files that don’t add value to flattened output ---
MANUAL_EXCLUDE = [
    'CODE_OF_CONDUCT.md', 'contributors.md', 'LICENSE', 'pyproject.toml',
    'README.md', 'SECURITY.md', 'flatten_exclude.py', 'flatten_include.py',
    '.gitignore', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'poetry.lock', 'Pipfile.lock',
]

# --- Always exclude generated output file ---
ALWAYS_EXCLUDE_FILENAMES = {OUTPUT_FILENAME}


# ==============================
#       CORE FUNCTIONS
# ==============================

def load_gitignore(base_dir: Path) -> PathSpec:
    """Load the root .gitignore (if exists)."""
    gitignore_path = base_dir / '.gitignore'
    if not gitignore_path.exists():
        return PathSpec.from_lines(GitWildMatchPattern, [])
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        return PathSpec.from_lines(GitWildMatchPattern, f.readlines())


def is_excluded(rel_path_str: str) -> bool:
    """Check if a file or folder path should be skipped."""
    path_obj = Path(rel_path_str)

    # Skip if any folder/file in the path matches DEFAULT_EXCLUDES
    for pattern in DEFAULT_EXCLUDES:
        if pattern in path_obj.parts:
            return True

    # Skip if file matches MANUAL_EXCLUDE or ALWAYS_EXCLUDE_FILENAMES
    if path_obj.name in MANUAL_EXCLUDE or path_obj.name in ALWAYS_EXCLUDE_FILENAMES:
        return True

    return False


def collect_files(base_dir: Path, output_file: Path) -> None:
    """Flatten repo text files into a single combined output file."""
    spec = load_gitignore(base_dir)

    with open(output_file, 'w', encoding='utf-8') as out:
        for path in base_dir.rglob('*'):
            if path.is_dir():
                continue

            rel_path_str = str(path.relative_to(base_dir)).replace('\\', '/')
            ext = path.suffix.lower()

            # Skip excluded or non-text files
            if (
                    spec.match_file(rel_path_str)
                    or ext in EXCLUDE_EXTENSIONS
                    or is_excluded(rel_path_str)
            ):
                continue

            try:
                with open(path, 'r', encoding='utf-8') as f:
                    out.write(f"\n\n===== {rel_path_str} =====\n")
                    out.write(f.read())
            except Exception as e:
                print(f"⚠️ Skipped: {rel_path_str} ({e})")

    print(f"\n✅ Done. Combined content written to: {output_file}")


# ==============================
#       ENTRY POINT
# ==============================

if __name__ == '__main__':
    collect_files(BASE_DIR, OUTPUT_FILE)
