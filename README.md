# CSV Comparison

A desktop CSV comparison tool with a modular PySide6 interface.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 csv_compare.py
```

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
loading one restores those paths in the File 1 and File 2 fields. History is stored in
`.csv_compare_history.json` in the project folder. Save a comparison with
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
