# downsweep

**Sort a messy Downloads folder into neat folders with one command. Changed your mind? Undo it.**

![PyPI](https://img.shields.io/pypi/v/downsweep) ![License](https://img.shields.io/pypi/l/downsweep) ![Python](https://img.shields.io/pypi/pyversions/downsweep)

Your Downloads folder is full of PDFs, installers, screenshots and zip files all mixed together. `downsweep` sorts them into Images, PDFs, Documents, Programs and more in a few seconds, and lets you reverse it if you don't like the result.

## Install

```
pip install downsweep
```

## Quick start

See what would happen first. Nothing is moved:

```
downsweep --preview
```

Clean your Downloads folder:

```
downsweep
```

Changed your mind? Move everything back:

```
downsweep --undo
```

Clean any other folder:

```
downsweep "C:\path\to\folder"
```

## What you will see

```
Moved: report.pdf  ->  PDFs
Moved: photo.jpg  ->  Images
Moved: setup.exe  ->  Programs

Summary
-------
PDFs         40
Programs     30
Images       12
Total        82

Done! Changed your mind? Run: downsweep --undo
```

## Features

| Feature | What it does |
| --- | --- |
| Preview mode | Shows what would move, changes nothing |
| Undo | Moves the last cleanup's files back where they were |
| Summary | Prints how many files went into each folder |
| Safe by design | Never overwrites a file, adds (1), (2) to duplicate names |
| Download-aware | Skips files still downloading, like .crdownload and .part |
| Zero dependencies | Only uses Python's standard library |

## Folders it creates

Images, Videos, Audio, PDFs, Documents, Archives, Programs, Code and Other.

## Good to know

- Undo reverses the **last** cleanup of a folder only.
- After a cleanup, a small file called `.downsweep_log.json` is saved inside the folder. That is how undo remembers what moved. Please don't delete it if you want to undo.
- Only files directly inside the folder are sorted. Existing sub-folders are left alone.

## License

MIT
