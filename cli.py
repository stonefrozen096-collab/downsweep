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

# Small file inside the cleaned folder where the last cleanup is remembered,
# so it can be undone
LOG_NAME = ".downsweep_log.json"

# Small file in your home folder where your own rules are saved
RULES_FILE = Path.home() / ".downsweep_rules.json"

BAD_FOLDER_CHARS = set('\\/:*?"<>|')


def load_rules():
    if not RULES_FILE.exists():
        return {}
    try:
        data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except (ValueError, AttributeError):
        print(f"Could not read {RULES_FILE}. Ignoring your saved rules.")
        return {}


def save_rules(rules):
    RULES_FILE.write_text(json.dumps(rules, indent=2), encoding="utf-8")


def clean_extension(text):
    ext = text.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    return ext


def add_rule(extension, folder_name):
    ext = clean_extension(extension)
    name = folder_name.strip()
    if len(ext) < 2 or " " in ext or any(c in BAD_FOLDER_CHARS for c in ext):
        print(f"'{extension}' is not a valid file type. Example: .pdf")
        return
    if not name or name in {".", ".."} or any(c in BAD_FOLDER_CHARS for c in name):
        print("Folder name must be a simple name, like Study (no slashes).")
        return
    rules = load_rules()
    rules[ext] = name
    save_rules(rules)
    print(f"Rule saved: {ext} files will go to a folder called {name}")


def remove_rule(extension):
    ext = clean_extension(extension)
    rules = load_rules()
    if ext not in rules:
        print(f"No rule found for {ext}")
        return
    del rules[ext]
    save_rules(rules)
    print(f"Rule removed: {ext}")


def show_rules():
    rules = load_rules()
    if not rules:
        print("No custom rules yet.")
        print("Add one like this: downsweep --add-rule .pdf Study")
        return
    print("Your rules:")
    for ext, name in sorted(rules.items()):
        print(f"  {ext:<10} ->  {name}")


def get_category(file, rules):
    ext = file.suffix.lower()
    if ext in rules:
        return rules[ext]
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
    rules = load_rules()
    moves = []
    counts = {}
    for item in sorted(folder.iterdir()):
        if not item.is_file() or item.suffix.lower() in SKIP or item.name == LOG_NAME:
            continue
        category = get_category(item, rules)
        target_dir = folder / category
        if target_dir.exists() and not target_dir.is_dir():
            print(f"Skipped: {item.name}  (a file named {category} is in the way)")
            continue
        counts[category] = counts.get(category, 0) + 1
        if preview:
            print(f"Would move: {item.name}  ->  {category}")
        else:
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

    # Remove folders that the cleanup created and that are now empty
    for move in moves:
        category_dir = Path(move["to"]).parent
        if category_dir.is_dir() and category_dir != folder and not any(category_dir.iterdir()):
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
    parser.add_argument(
        "--add-rule",
        nargs=2,
        metavar=("TYPE", "FOLDER"),
        help="Save a rule, for example: --add-rule .pdf Study",
    )
    parser.add_argument(
        "--remove-rule",
        metavar="TYPE",
        help="Forget a saved rule, for example: --remove-rule .pdf",
    )
    parser.add_argument(
        "--rules",
        action="store_true",
        help="Show your saved rules",
    )
    args = parser.parse_args()

    if args.add_rule:
        add_rule(args.add_rule[0], args.add_rule[1])
        return
    if args.remove_rule:
        remove_rule(args.remove_rule)
        return
    if args.rules:
        show_rules()
        return

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
