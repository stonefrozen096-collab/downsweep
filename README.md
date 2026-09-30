# downsweep

Sort a messy Downloads folder into neat folders with one command.

## Install

    pip install downsweep

## Use

Clean your Downloads folder:

    downsweep

See what would move first, without changing anything:

    downsweep --preview

Clean any other folder:

    downsweep "C:\path\to\folder"

## What it does

Files are moved into folders like Images, Videos, Audio, PDFs, Documents,
Archives, Programs, Code and Other. Files still being downloaded are skipped,
and existing files are never overwritten.