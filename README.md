# downsweep

**Sort a messy Downloads folder into neat folders with one command. Make your own rules. Changed your mind? Undo it.**

![PyPI](https://img.shields.io/pypi/v/downsweep) ![License](https://img.shields.io/pypi/l/downsweep) ![Python](https://img.shields.io/pypi/pyversions/downsweep)

Your Downloads folder is full of PDFs, installers, screenshots and zip files all mixed together. `downsweep` sorts them into Images, PDFs, Documents, Programs and more in a few seconds, lets you add your own rules, and lets you reverse it if you don't like the result.

## See it in action

![downsweep preview with a custom rule](https://raw.githubusercontent.com/stonefrozen096-collab/downsweep/main/demo.png)

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

## Your own rules

Want all your PDFs in a folder called Study? Save a rule once and downsweep remembers it:

```
downsweep --add-rule .pdf Study
```

See your rules:

```
downsweep --rules
```

Forget a rule:

```
downsweep --remove-rule .pdf
```

Your rules always win over the built-in sorting, and undo cleans up your custom folders too.

## Features

| Feature | What it does |
| --- | --- |
| Preview mode | Shows what would move, changes nothing |
| Custom rules | Send any file type to a folder you choose |
| Undo | Moves the last cleanup's files back where they were |
| Summary | Prints how many files went into each folder |
| Safe by design | Never overwrites a file, adds (1), (2) to duplicate names |
| Download-aware | Skips files still downloading, like .crdownload and .part |
| Zero dependencies | Only uses Python's standard library |

## Folders it creates

Images, Videos, Audio, PDFs, Documents, Archives, Programs, Code and Other, plus any folders from your own rules.

## Good to know

- Undo reverses the **last** cleanup of a folder only.
- After a cleanup, a small file called `.downsweep_log.json` is saved inside the folder. That is how undo remembers what moved. Please don't delete it if you want to undo.
- Your rules are saved in a small file called `.downsweep_rules.json` in your home folder, and they apply to every folder you clean.
- A rule's folder is created inside the folder being cleaned, so use a simple name like Study, not a full path.
- Only files directly inside the folder are sorted. Existing sub-folders are left alone.

## License

MIT
