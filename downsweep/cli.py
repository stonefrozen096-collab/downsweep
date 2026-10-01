import argparse
import json
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

# Files still being downloaded, or system files - never touch these
SKIP = {".crdownload", ".part", ".tmp", ".ini", ".lnk"}

# Hidden file where the last cleanup is remembered, so it can be undone
LOG_NAME = ".downsweep_log.json"


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


def print_summary(counts):
    print("\nSummary")
    print("-------")
    for name, number in sorted(counts.items(), key=lambda pair: -pair[1]):
        print(f"{name:<12} {number}")
    print(f"{'Total':<12} {sum(counts.values())}")


def clean(folder, preview):
    moves = []
    counts = {}
    for item in sorted(folder.iterdir()):
        if not item.is_file() or item.suffix.lower() in SKIP or item.name == LOG_NAME:
            continue
        category = get_category(item)
        counts[category] = counts.get(category, 0) + 1
        if preview:
            print(f"Would move: {item.name}  ->  {category}")
        else:
            target_dir = folder / category
            target_dir.mkdir(exist_ok=True)
            target = unique_path(target_dir / item.name)
            shutil.move(str(item), str(target))
            moves.append({"from": str(item), "to": str(target)})
            print(f"Moved: {item.name}  ->  {category}")

    if not counts:
        print("Nothing to sort here.")
        return

    print_summary(counts)
    if preview:
        print("\nNothing was changed.")
    else:
        (folder / LOG_NAME).write_text(json.dumps(moves, indent=2), encoding="utf-8")
        print("\nDone! Changed your mind? Run: downsweep --undo")


def undo(folder):
    log_file = folder / LOG_NAME
    if not log_file.exists():
        print("Nothing to undo.")
        return

    moves = json.loads(log_file.read_text(encoding="utf-8"))
    restored = 0
    for move in moves:
        source = Path(move["to"])
        destination = Path(move["from"])
        if source.exists():
            shutil.move(str(source), str(unique_path(destination)))
            restored += 1
        else:
            print(f"Could not find, skipped: {source.name}")
    log_file.unlink()

    # Remove category folders that are now empty
    for name in list(CATEGORIES) + ["Other"]:
        category_dir = folder / name
        if category_dir.is_dir() and not any(category_dir.iterdir()):
            category_dir.rmdir()

    print(f"Undone! {restored} file(s) moved back.")


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
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Move files back to where they were (undo the last cleanup)",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return

    if args.undo:
        undo(folder)
    else:
        clean(folder, args.preview)


if __name__ == "__main__":
    main()