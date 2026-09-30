import argparse
import shutil
from pathlib import Path

CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".avif", ".jfif"],
    "Videos": [".mp4", ".mkv", ".avi", ".mov", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".m4a"],
    "PDFs": [".pdf"],
    "Documents": [".doc", ".docx", ".txt", ".ppt", ".pptx", ".xls", ".xlsx", ".csv"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Programs": [".exe", ".msi"],
    "Code": [".py", ".js", ".html", ".htm", ".css", ".java", ".cpp", ".ipynb"],
}

# Files still being downloaded - never touch these
SKIP = {".crdownload", ".part", ".tmp", ".ini", ".lnk"}


def get_category(file):
    ext = file.suffix.lower()
    for name, extensions in CATEGORIES.items():
        if ext in extensions:
            return name
    return "Other"


def unique_path(path):
    # If a file with the same name exists, add (1), (2)... instead of overwriting
    if not path.exists():
        return path
    counter = 1
    while True:
        new_path = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not new_path.exists():
            return new_path
        counter += 1


def main():
    parser = argparse.ArgumentParser(
        description="Sort a messy folder into neat sub-folders by file type."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=str(Path.home() / "Downloads"),
        help="Folder to clean (default: your Downloads folder)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show what would move, without moving anything",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return

    count = 0
    for item in folder.iterdir():
        if not item.is_file() or item.suffix.lower() in SKIP:
            continue
        category = get_category(item)
        if args.preview:
            print(f"Would move: {item.name}  ->  {category}")
        else:
            target_dir = folder / category
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(unique_path(target_dir / item.name)))
            print(f"Moved: {item.name}  ->  {category}")
        count += 1

    if args.preview:
        print(f"\n{count} file(s) would be moved. Nothing was changed.")
    else:
        print(f"\nDone! {count} file(s) sorted.")


if __name__ == "__main__":
    main()