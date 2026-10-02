import argparse
import json
import os
import shutil
import subprocess
import sys
import time
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
SKIP = {
    ".crdownload", ".part", ".partial", ".download", ".opdownload",
    ".tmp", ".ini", ".lnk",
}

# Small file inside the cleaned folder where moves are remembered,
# so they can be undone
LOG_NAME = ".downsweep_log.json"
MAX_LOG_ENTRIES = 500

# Small files in your home folder
RULES_FILE = Path.home() / ".downsweep_rules.json"   # your own rules
WATCH_FILE = Path.home() / ".downsweep_watch.json"   # "auto mode is running" note
STOP_FILE = Path.home() / ".downsweep_stop"          # asks auto mode to stop

# Auto mode timing (seconds)
POLL_SECONDS = 5        # how often the folder is checked
SETTLE_SECONDS = 10     # a file must stay unchanged this long before it is moved
HEARTBEAT_STALE = 30    # auto mode counts as "not running" after this long without a sign of life

# Windows: where "start at login" programs are listed
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "downsweep"

BAD_FOLDER_CHARS = set('\\/:*?"<>|')


# ---------------------------------------------------------------- rules

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


# ---------------------------------------------------------------- sorting

def get_category(file, rules):
    ext = file.suffix.lower()
    if ext in rules:
        return rules[ext]
    for name, extensions in CATEGORIES.items():
        if ext in extensions:
            return name
    return "Other"


def is_candidate(item):
    """True for files downsweep is allowed to move."""
    return (
        item.is_file()
        and item.suffix.lower() not in SKIP
        and item.name != LOG_NAME
        and not item.name.startswith(".downsweep")
    )


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


def blocked(folder, category):
    target_dir = folder / category
    return target_dir.exists() and not target_dir.is_dir()


def move_into_category(item, folder, category):
    """Move one file into its category folder. Returns the new path, or None."""
    if blocked(folder, category):
        return None
    try:
        target_dir = folder / category
        target_dir.mkdir(exist_ok=True)
        target = unique_path(target_dir / item.name)
        shutil.move(str(item), str(target))
    except (OSError, shutil.Error):
        return None
    return target


def print_summary(counts):
    print("\nSummary")
    print("-------")
    for name, number in sorted(counts.items(), key=lambda pair: -pair[1]):
        print(f"{name:<12} {number}")
    print(f"{'Total':<12} {sum(counts.values())}")


def append_log(folder, new_moves):
    log_file = folder / LOG_NAME
    moves = []
    if log_file.exists():
        try:
            moves = json.loads(log_file.read_text(encoding="utf-8"))
        except ValueError:
            moves = []
    moves.extend(new_moves)
    moves = moves[-MAX_LOG_ENTRIES:]
    log_file.write_text(json.dumps(moves, indent=2), encoding="utf-8")


def clean(folder, preview):
    rules = load_rules()
    moves = []
    counts = {}
    for item in sorted(folder.iterdir()):
        if not is_candidate(item):
            continue
        category = get_category(item, rules)
        if blocked(folder, category):
            print(f"Skipped: {item.name}  (a file named {category} is in the way)")
            continue
        if preview:
            print(f"Would move: {item.name}  ->  {category}")
        else:
            target = move_into_category(item, folder, category)
            if target is None:
                print(f"Skipped: {item.name}  (could not move it, maybe it is open)")
                continue
            moves.append({"from": str(item), "to": str(target)})
            print(f"Moved: {item.name}  ->  {category}")
        counts[category] = counts.get(category, 0) + 1

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
    state = watcher_running()
    if state and same_folder(state.get("folder"), folder):
        print("Auto mode is running on this folder and would sort the files again.")
        print("Turn it off first: downsweep --auto off")
        print("Then run --undo again.")
        return

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

    # Remove folders that downsweep created and that are now empty
    for move in moves:
        category_dir = Path(move["to"]).parent
        if category_dir.is_dir() and category_dir != folder and not any(category_dir.iterdir()):
            category_dir.rmdir()

    print(f"Undone! {restored} file(s) moved back.")


# ---------------------------------------------------------------- auto mode

def same_folder(a, b):
    try:
        return Path(a).resolve() == Path(b).resolve()
    except (OSError, TypeError, ValueError):
        return False


def read_watch_state():
    try:
        return json.loads(WATCH_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def write_watch_state(folder):
    state = {"pid": os.getpid(), "folder": str(folder), "last_seen": time.time()}
    try:
        WATCH_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass


def watcher_running():
    """Returns the watcher's note if auto mode seems to be running, else None."""
    state = read_watch_state()
    if not isinstance(state, dict):
        return None
    try:
        fresh = time.time() - float(state["last_seen"]) < HEARTBEAT_STALE
    except (KeyError, TypeError, ValueError):
        return None
    return state if fresh else None


def remove_file(path):
    try:
        path.unlink()
    except OSError:
        pass


def watch(folder, max_loops=None):
    """Keep sorting new files in the folder until stopped."""
    state = watcher_running()
    if state and state.get("pid") != os.getpid():
        print("Auto mode is already running. Turn it off with: downsweep --auto off")
        return

    remove_file(STOP_FILE)
    print(f"Watching {folder}")
    print("New files are sorted once they stop changing. Press Ctrl+C to stop.")

    stable = {}   # file name -> (size and time stamp, when it was first seen like that)
    loops = 0
    try:
        while True:
            write_watch_state(folder)
            if STOP_FILE.exists():
                remove_file(STOP_FILE)
                print("Stopped.")
                break

            now = time.time()
            rules = load_rules()
            try:
                items = [i for i in folder.iterdir() if is_candidate(i)]
            except OSError:
                items = []

            moves = []
            present = set()
            for item in items:
                present.add(item.name)
                try:
                    info = item.stat()
                except OSError:
                    continue
                signature = (info.st_size, info.st_mtime)
                previous = stable.get(item.name)
                if previous is None or previous[0] != signature:
                    stable[item.name] = (signature, now)
                    continue
                if now - previous[1] < SETTLE_SECONDS:
                    continue
                category = get_category(item, rules)
                target = move_into_category(item, folder, category)
                if target is not None:
                    moves.append({"from": str(item), "to": str(target)})
                    print(f"Moved: {item.name}  ->  {category}")
                    stable.pop(item.name, None)

            for name in list(stable):
                if name not in present:
                    del stable[name]
            if moves:
                append_log(folder, moves)

            loops += 1
            if max_loops is not None and loops >= max_loops:
                break
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        current = read_watch_state()
        if isinstance(current, dict) and current.get("pid") == os.getpid():
            remove_file(WATCH_FILE)


def pythonw_path():
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def start_background(folder):
    # DETACHED_PROCESS | CREATE_NO_WINDOW: runs with no window at all
    flags = 0x00000008 | 0x08000000
    subprocess.Popen(
        [str(pythonw_path()), "-m", "downsweep", "--watch", str(folder)],
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def auto_supported():
    if sys.platform == "win32":
        return True
    print("Auto start is only available on Windows for now.")
    print("You can still run auto mode in a window with: downsweep --watch")
    return False


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
        return True
    except OSError:
        return False


def auto_on(folder):
    import winreg
    command = f'"{pythonw_path()}" -m downsweep --watch "{folder}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, command)

    print(f"Auto mode is ON for: {folder}")
    print("It starts by itself when you log in to Windows, with no window.")
    print(f"Files already in the folder will be sorted in about {SETTLE_SECONDS} seconds.")
    print("To turn it off: downsweep --auto off")
    print("To reverse what it sorted: turn it off, then run downsweep --undo")

    if watcher_running():
        print("It is already running right now.")
    else:
        start_background(folder)
        print("Started it for this session too.")


def auto_off():
    import winreg
    removed = False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_NAME)
        removed = True
    except OSError:
        pass

    if removed:
        print("Auto start removed. It will not start at login any more.")
    else:
        print("Auto start was not turned on.")

    if watcher_running():
        STOP_FILE.write_text("stop", encoding="utf-8")
        print("Stopping the running copy...")
        waited = 0.0
        while waited < POLL_SECONDS + 5:
            time.sleep(0.5)
            waited += 0.5
            if not watcher_running():
                print("Stopped.")
                return
        print("It should stop within a few seconds.")


def auto_status():
    import winreg  # noqa: F401  (only checked to confirm Windows)
    print(f"Start at login: {'ON' if autostart_enabled() else 'OFF'}")
    state = watcher_running()
    if state:
        print(f"Running now:    YES  (watching {state.get('folder')})")
    else:
        print("Running now:    NO")


# ---------------------------------------------------------------- command line

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
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep running and sort new files as they arrive (Ctrl+C to stop)",
    )
    parser.add_argument(
        "--auto",
        choices=["on", "off", "status"],
        help="Turn background auto mode on or off (Windows)",
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

    if args.auto:
        if not auto_supported():
            return
        if args.auto == "off":
            auto_off()
        elif args.auto == "status":
            auto_status()
        else:
            folder = Path(args.folder)
            if not folder.is_dir():
                print(f"Folder not found: {folder}")
                return
            auto_on(folder)
        return

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return

    if args.watch:
        watch(folder)
    elif args.undo:
        undo(folder)
    else:
        clean(folder, args.preview)


if __name__ == "__main__":
    main()
