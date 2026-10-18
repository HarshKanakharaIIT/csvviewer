# CSV Comparison

A desktop CSV comparison tool with a modular PySide6 interface.

## Run

```bash
python -m pip install -e .
csv-compare
```

For development installs, `python -m pip install -e .` installs the project
in editable mode, so source edits are picked up without reinstalling. You can
also launch it as `python csv_compare.py`.

GUI code lives under `ui/`, with reusable file-picker, comparison-settings,
and results-table widgets in `ui/widgets/`.

Choose two CSV files, then select **Compare**. The default ignored columns are
`date` and `version`; enter header names or 1-based column numbers separated
by commas to change them. The optional sort column accepts a header name or a
1-based column number. Numeric columns are compared using the configurable
relative (`rtol`) and absolute (`atol`) tolerances.

Hover over controls and result cells for hints. After comparing, select
**Save Output...** to export a CSV containing both files' values and a status
for each compared cell. The save dialog suggests a filename based on the input
files and lets you choose the output folder and name.

The history bar supports saving named comparisons, loading saved snapshots,
refreshing a snapshot from its source files, updating a saved entry, deleting
entries, and reloading the history list from disk. The history bar's
**Load Saved** button opens a file picker for a comparison CSV previously
exported with **Save Output...**. Double-click a history dropdown entry to
load its stored snapshot. Comparison exports include the source file paths, so
loading one restores those paths in the File 1 and File 2 fields. In a source
checkout, history is stored at `history/comparison_history.json`; packaged
builds store it in the operating system's application-data directory under
`csvviewer/history/comparison_history.json`. Any existing project-level
`.csv_compare_history.json` is moved to the new history location the first time
the updated app starts. Save a comparison with
**Save New** before loading, refreshing, updating, or deleting it.
**Refresh Sources** updates the current view; select **Update Saved** to
persist the refreshed result and current settings to the selected history
entry.

Cell colors mean:

- **Green**: exact match (including numerically equal values such as `1` and
  `1.0`).
- **Orange**: numeric values match within the configured tolerance.
- **Red**: values differ, either value is blank or NaN, either numeric value is
  zero, or a row is missing from one file.

CSV files must have the same column names in the same order. Rows are compared
in file order unless a sort column is specified.

## Test

```bash
python3 -m unittest
```

## Build binaries for Linux, Windows, and macOS

The GitHub Actions workflow builds native packages on Linux, Windows, macOS
Intel, and Apple Silicon macOS. Linux gets an AppImage and ZIP; Windows and
macOS get platform-specific ZIP artifacts. Run the workflow from the
**Actions** tab, or push a commit to `main`; tagged releases starting with
`v` also trigger builds.

Each build runs on its target operating system. On Linux x86_64, install the
build requirements and create both packages with:

```bash
python3 -m pip install -r requirements-build.txt
bash build_linux.sh
bash build_appimage.sh
bash build_deb.sh
```

The scripts create `dist/CSVCompare-Linux-x86_64.zip`,
`dist/CSVCompare-Linux-x86_64.AppImage`, and
`dist/CSVCompare-Linux-amd64.deb`, and copy the standalone icon to
`dist/csvviewer.svg`. The AppImage embeds that icon and is a single executable
file; make it executable if needed, then run
`./CSVCompare-Linux-x86_64.AppImage`. To install the Debian package, run
`sudo apt install ./CSVCompare-Linux-amd64.deb`; launch CSV Compare from the
desktop application menu. The `.deb` targets Debian/Ubuntu-family x86_64
systems. Windows and macOS ZIPs contain their standalone app, this README, and
the SVG icon; extract and launch `CSVCompare.exe` on Windows or `./CSVCompare`
on macOS.

The SVG is also set as the Qt application/window icon and is bundled into the
PyInstaller executable so it appears in the running app on supported desktops.
Windows builds receive a native `.ico` executable icon, and macOS builds
receive a native `.icns` app icon.
