"""Delivery planning helper. Scripts have no network access - the actual
mcp__BKPK__google_drive_create calls are made by the orchestrator (Claude),
per SKILL.md §8. This module only builds the plan and stages file bytes;
it never calls a Drive API itself.

The plan is derived entirely from `out_dir` + `period` using the exact same
naming convention `runner.py cmd_build` used to write the files (same
MANAGER_FILE_LABEL, same "Amex Spend {period} - {label}.xlsx" pattern) - the
manifest can never drift from what's actually on disk because it isn't
handed filenames by a caller, it reconstructs them the same way build did.
The orchestrator must use each entry's `filename` verbatim in its
google_drive_create call rather than retyping it - retyping is what
produced the naming bugs ("ConnorJT.xlsx", a missing " - ") on the first
real delivery.

UNVERIFIED as of 2026-07-01: BKPK's google_drive_create/modify schema was
never confirmed against a live connection (the BKPK MCP server was flaky/
disconnected every time this was checked during development). The plan
below assumes it mirrors the standard Drive API upload contract (binary
content + explicit mime type + parent folder id + a flag to disable
auto-conversion to a native Google Sheet) because that's what the sibling
mcp__Google_Drive__create_file tool exposes and it's a standard Drive API
v3 capability - but this has never been exercised end-to-end. The first
real delivery run MUST write to the finance-only folder first and a human
must open the result and confirm the native PivotTable is still intact
(conversion-to-Sheets would silently destroy it) before this is trusted
to write into any of the 8 manager folders.
"""
import base64
import os

DRIVE_FOLDERS = {
    "Jay Barker": "1aTqvD4oveHA6CNP1l6mRabkPijlHYdmw",
    "Connor/JT": "1rrT9419H4NIKw01K1U_dsaBU9tEGx8l6",
    "Jesse/Scott": "1dpQqMveOSrvQKmjTeJ9K93sXzNuezY8T",
    "Elias Kapetanopoulos": "1eP9Qfq-oIomdzi5Sp7FoscU0rnT2SPHM",
    "Ayaan Israni": "1EFtC2ErXeiNXNp64QPB2VrgDOdzJ7xPa",
    "Elyse Neumeier": "180cTKkuluMr5n-M8nxUIkHhLNy03jQWg",
    "Toni Manning": "1WJbdLg5TAkyfIl0cRlWJpUSlMdLm41AT",
    "Kevin Ebert": "1w8xDaQmX8lno_eggZAve6_7WaPl_FQ7M",
}
FINANCE_ONLY_FOLDER = "1BdBpI8J9LN3XUOKl4DwZGPr5OIMZ0Ka5"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Must match runner.py's MANAGER_FILE_LABEL exactly - duplicated rather than
# imported so this module has no dependency on runner.py's internals; if the
# two ever drift, build_delivery_plan's os.path.exists check below will fail
# loudly (missing file) instead of silently uploading the wrong thing.
MANAGER_FILE_LABEL = {
    "Jay Barker": "Jay", "Connor/JT": "Connor-JT", "Jesse/Scott": "Jesse-Scott",
    "Elias Kapetanopoulos": "Eli", "Ayaan Israni": "Ayaan",
    "Elyse Neumeier": "Elyse", "Toni Manning": "Toni", "Kevin Ebert": "Kevin",
}


def build_delivery_plan(out_dir, period):
    """Reconstructs the exact filenames `runner.py build` wrote to `out_dir`
    for the given `period` and pairs each with its Drive destination. Returns
    a list of {label, filename, local_path, folder_id} dicts - present this
    manifest for approval (root CLAUDE.md §3, SKILL.md §8) and then, on
    approval, upload each entry with `filename` used verbatim (never
    retyped) and disable_conversion_to_google_type=True.

    Raises FileNotFoundError if an expected file is missing from `out_dir`
    (e.g. period mismatch, or build.py wasn't actually re-run) rather than
    silently building a plan for files that don't exist.
    """
    plan = []
    for mgr, label in MANAGER_FILE_LABEL.items():
        filename = f"Amex Spend {period} - {label}.xlsx"
        local_path = os.path.join(out_dir, filename)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"expected manager file not found: {local_path}")
        plan.append({"label": f"{mgr} manager file", "filename": filename,
                     "local_path": local_path, "folder_id": DRIVE_FOLDERS[mgr]})

    for label, file_label in (("Master", "MASTER"), ("Exceptions", "Exceptions")):
        filename = f"Amex Spend {period} - {file_label}.xlsx"
        local_path = os.path.join(out_dir, filename)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"expected {label} file not found: {local_path}")
        plan.append({"label": label, "filename": filename,
                     "local_path": local_path, "folder_id": FINANCE_ONLY_FOLDER})

    return plan


def stage_base64(local_path):
    """Base64-encode a file for the orchestrator's google_drive_create call."""
    with open(local_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")
