#!/usr/bin/env python3
# ↑ This tells the computer this is a Python program

"""
Digantara Test Automation — Gradio GUI Framework

╔══════════════════════════════════════════════════════════════════════════════╗
║                      COMPLETE DOCUMENTATION SUMMARY                          ║
║                    For Non-Technical Documentation Reviews                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

─────────────────────────────────────────────────────────────────────────────── 
WHAT THIS PROGRAM DOES (In Simple Terms)
───────────────────────────────────────────────────────────────────────────────

This program provides a user-friendly web interface to run different test suites
on circuit boards. It's like a dashboard where you can:
  • Select which board you want to test
  • Choose which test to run (Load Transient, Power Sequencing, etc.)
  • See live output as the test runs
  • Save or delete the results

WHY THIS MATTERS:
Instead of typing complicated commands in a terminal, engineers can use buttons
and dropdowns in a clean web interface to control all test automation.

───────────────────────────────────────────────────────────────────────────────
HOW IT WORKS (Step-by-Step)
───────────────────────────────────────────────────────────────────────────────

1. PROGRAM DISCOVERS BOARDS AUTOMATICALLY
   ├─ Scans each test suite folder for files like "CPU_config.json"
   ├─ File name pattern: <BOARDNAME>_config.json
   └─ To add a new board: just drop its config file in the suite folder
   
2. USER OPENS THE GUI IN WEB BROWSER
   ├─ Left panel: Board, Test Suite, and Options dropdowns
   ├─ Right panel: Live test output display
   └─ Buttons: Run, Stop, Send (to answer test prompts)

3. USER SELECTS BOARD AND TEST SUITE
   ├─ Board dropdown auto-populates from discovered boards
   ├─ Suite dropdown shows only tests available for that board
   └─ Instruments required for the test appear in sidebar

4. USER CLICKS "RUN"
   ├─ Program launches the test script as a subprocess
   ├─ Captures all output line-by-line in real-time
   ├─ Displays in scrollable log window
   └─ Can send text to test via "Send" button if test asks for input

5. TEST COMPLETES
   ├─ Status shows "PASS" or "FAIL"
   ├─ "Keep Results" / "Delete Results" buttons appear
   └─ User decides whether to save or discard outputs

───────────────────────────────────────────────────────────────────────────────
FILE STRUCTURE AND KEY COMPONENTS
───────────────────────────────────────────────────────────────────────────────

LINES 1: #!/usr/bin/env python3
   └─ Special line telling operating system this is a Python script

LINES 3-56: PROGRAM DESCRIPTION
   └─ Overview of what the program does and how the GUI works

LINES 60-100: IMPORT STATEMENTS
   └─ Brings in helper tools/libraries the program depends on
   └─ Examples: gradio (web UI framework), subprocess (running test scripts)

LINES 110-150: PROJECT LAYOUT
   └─ Defines where test suites are located and their names
   └─ Lists which tests support which test modes
   └─ Maps short names (psu, dmm, scope) to human-readable labels

LINES 160-190: BOARD & SUITE DISCOVERY FUNCTIONS
   └─ discover_boards(suite_dir): Scans folder for *_config.json files
   └─ get_available_boards(): Lists all boards across all test suites
   └─ get_suites_for_board(): Shows which tests support a given board
   └─ get_config_path(): Finds the config file for board+suite combination

LINES 200-250: CONFIGURATION READING
   └─ get_rails_for_suite(): Extracts voltage rails to test from config
   └─ _instrument_info_html(): Creates visual list of required instruments

LINES 260-290: LOG RENDERING
   └─ _log_html(): Converts test output lines into styled HTML display
   └─ Auto-scrolls log window to bottom on every update

LINES 300-330: SUBPROCESS STATE MANAGEMENT
   └─ _active_proc: Stores reference to currently running test process
   └─ _proc_lock: Prevents multiple tests from running simultaneously
   └─ _last_run_dir: Tracks where most recent test results were saved

LINES 340-370: COMMAND BUILDING
   └─ _build_cmd(): Constructs the Python command to launch test script
   └─ Includes arguments like --headless, --output, --mode, --rails

LINES 380-500: TEST LAUNCHER (Generator Function)
   └─ launch_test(): Main function that runs a selected test
   └─ Validates user selections (board and suite must be picked)
   └─ Builds subprocess with proper encoding (UTF-8) and stdio piping
   └─ Yields (html_output, status, save_button_state) on each line
   └─ Searches for "Results saved:" pattern to track output folder

LINES 510-550: TEST CONTROL FUNCTIONS
   └─ send_to_test(): Sends user text to test via stdin (for prompts)
   └─ stop_test(): Terminates currently running test process
   └─ keep_results(): Marks test results as approved (keeps them)
   └─ delete_results(): Removes test results folder (Windows or Python)

LINES 560-590: FOLDER BROWSER DIALOG
   └─ browse_output_dir(): Opens native folder-picker using tkinter
   └─ Returns chosen path or current path if dialog cancelled

LINES 600-630: CSS STYLING
   └─ Custom styles for status box, save buttons, layout spacing

LINES 640-800: GRADIO USER INTERFACE CONSTRUCTION
   └─ build_gui(): Creates web interface with all controls
   └─ Left column: Dropdowns, output directory, Run/Stop buttons
   └─ Right column: Status display, live log, Send box, Save/Delete buttons
   └─ Event handlers: Board/Suite changes trigger UI updates
   └─ Click handlers: Wire buttons to their functions

LINES 810-830: ENTRY POINT
   └─ if __name__ == "__main__": Launch the GUI in browser

───────────────────────────────────────────────────────────────────────────────
CONFIGURATION AUTO-DISCOVERY PATTERN
───────────────────────────────────────────────────────────────────────────────

To add a new board to the test framework:
  1. Create a config file: CPU_config.json (or SENSOR_config.json, etc.)
  2. Copy it to each test suite folder that supports this board:
     ├─ Input_Range_OVP/CPU_config.json
     ├─ Load_Transient/CPU_config.json
     ├─ Power_Sequencing/CPU_config.json
     └─ Steady_State_Ripple/CPU_config.json
  3. NO code changes needed — GUI auto-discovers the new board
  4. Board appears in dropdown immediately on next GUI restart

To remove a board:
  • Delete the *_config.json files from test suite folders
  • Board disappears from dropdown automatically

This design makes the system extensible without requiring programmer intervention.

───────────────────────────────────────────────────────────────────────────────
ENCODING NOTE
───────────────────────────────────────────────────────────────────────────────

Subprocess stdout is opened with encoding='utf-8' and errors='replace' to handle
international characters and binary data safely across Windows/Linux/Mac.
This prevents UnicodeDecodeError when test scripts output non-ASCII bytes.
"""

import html as _html                           # ← Library for escaping HTML special characters
import json                                     # ← Library for reading/writing JSON files (config loading)
import datetime                                  # ← Library for timestamps in saved metadata
import os                                       # ← Library for environment variables and file operations
import re                                       # ← Library for regular expressions (pattern matching in output)
import shutil                                   # ← Library for high-level file operations (folder deletion)
import subprocess                               # ← Library for launching and controlling external processes (test scripts)
import sys                                      # ← Library for system-specific parameters (Python executable path)
import threading                                # ← Library for thread-safe locks (prevent simultaneous tests)
from pathlib import Path                        # ← Library for modern file path handling (cross-platform)

import gradio as gr                             # ← Gradio library for building web UI with Python

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Section explains where all test suites are located and how they're named
# ─────────────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent                    # ← Get the folder where this script is located

# ← Dictionary mapping user-friendly test names to their folder paths and launcher scripts
SUITES: dict[str, tuple[Path, str]] = {
    "Input Range / OVP":   (ROOT / "Input_Range_OVP",    "run_input_range_ovp_test.py"),      # ← Input Range test suite location
    "Load Transient":      (ROOT / "Load_Transient",      "run_load_transient_test.py"),       # ← Load Transient test suite location
    "Power Sequencing":    (ROOT / "Power_Sequencing",    "run_power_sequencing_test.py"),     # ← Power Sequencing test suite location
    "Steady-State Ripple": (ROOT / "Steady_State_Ripple", "run_steady_state_ripple_test.py"),  # ← Steady-State Ripple test suite location
}

# ← Dictionary mapping test suite names to their available test modes
SUITE_MODES: dict[str, list[str]] = {
    "Input Range / OVP":   ["full", "fixed", "sweep"],                           # ← OVP test can run full, fixed, or sweep mode
    "Power Sequencing":    ["full", "config1", "config2", "capture", "reanalyze"],  # ← Power Sequencing test modes
}

# ← Dictionary mapping short instrument names to human-readable labels for the sidebar
_INSTR_LABELS: dict[str, str] = {
    "psu":             "Power Supply",                   # ← Label for psu instrument
    "dmm":             "Digital Multimeter",             # ← Label for dmm instrument
    "scope":           "Oscilloscope",                   # ← Label for scope instrument
    "electronic_load": "Electronic Load",                # ← Label for electronic_load instrument
}

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Functions that auto-scan folders for board config files
# ─────────────────────────────────────────────────────────────────────────────

def discover_boards(suite_dir: Path) -> dict[str, Path]:
    # ← Scan the test suite directory for all *_config.json files
    return {p.stem.replace("_config", ""): p  # ← Extract board name from filename, store Path object
            for p in sorted(suite_dir.glob("*_config.json"))}  # ← Find all config files and sort by name


def get_available_boards() -> list[str]:
    # ← Collect all unique boards across all test suites
    boards: set[str] = set()  # ← Use a set to avoid duplicate board names
    for suite_dir, _ in SUITES.values():  # ← Loop through each test suite's directory
        boards |= set(discover_boards(suite_dir).keys())  # ← Add boards from this suite to the set
    return sorted(boards)  # ← Return boards in alphabetical order


def get_suites_for_board(board: str) -> list[str]:
    # ← Find which test suites support a given board
    return [name for name, (d, _) in SUITES.items()  # ← Iterate through suite names and folders
            if board in discover_boards(d)]  # ← Only include suites that have this board's config


def get_config_path(board: str, suite: str) -> Path | None:
    # ← Find the config file path for a specific board+suite combination
    info = SUITES.get(suite)  # ← Look up the suite in the SUITES dictionary
    if not info:  # ← If suite not found, return None
        return None  # ← Exit early with None
    return discover_boards(info[0]).get(board)  # ← Find board config in suite folder


def get_rails_for_suite(suite: str, cfg_path: Path) -> list[str] | None:
    # ← Extract voltage rail names from config file (only for certain suites)
    if suite not in ("Load Transient", "Steady-State Ripple"):  # ← Check if suite supports rails
        return None  # ← Return None if this suite doesn't have rails
    try:  # ← Wrap in try-except to handle file reading errors
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))  # ← Read and parse JSON config file
        key = "rail_configs" if suite == "Load Transient" else "rails"  # ← Use correct key for suite type
        return [r["name"] for r in cfg.get(key, [])]  # ← Extract rail names from config, default to empty list
    except Exception:  # ← If anything fails
        return None  # ← Return None gracefully


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Reads config files and builds the HTML sidebar showing required instruments
# ─────────────────────────────────────────────────────────────────────────────

def _instrument_info_html(board: str, suite: str) -> str:
    # ← Build HTML showing which instruments are required for the test
    if not board or not suite:  # ← If board or suite not selected
        return ""  # ← Return empty string (nothing to display)
    
    cfg_path = get_config_path(board, suite)  # ← Get the config file path
    if cfg_path is None:  # ← If config doesn't exist
        return ""  # ← Return empty string
    
    try:  # ← Wrap in try-except for safety
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))  # ← Read and parse JSON config
    except Exception:  # ← If file read fails
        return ""  # ← Return empty string

    addrs: dict = cfg.get("instrument_addresses", {})  # ← Get instrument_addresses from config, default to empty dict
    if not addrs:  # ← If no instruments listed
        return ""  # ← Return empty string

    labels = []  # ← List of human-readable instrument names
    for key in addrs:
        if key.startswith("_"):
            continue
        labels.append(_INSTR_LABELS.get(key, key.replace("_", " ").title()))

    if not labels:
        return ""

    rows_html = "".join(
        f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;"
        f"color:var(--t-txt);font-size:0.82em;'>"
        f"<span style='width:4px;height:4px;border-radius:50%;"
        f"background:var(--t-acc);display:inline-block;flex-shrink:0;'></span>"
        f"{_html.escape(lbl)}</div>"
        for lbl in labels
    )
    return (
        f"<div style='background:var(--t-surf);border:1px solid var(--t-bdr);"
        f"border-left:2px solid var(--t-acc);border-radius:6px;"
        f"padding:10px 14px;margin-top:10px;'>"
        f"<div style='color:var(--t-txd);font-size:0.62em;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;'>Required Instruments</div>"
        f"{rows_html}</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Converts test output lines to styled HTML that auto-scrolls to bottom
# ─────────────────────────────────────────────────────────────────────────────

_LOG_STYLE = (
    "height:460px;overflow-y:auto;"
    "background:var(--t-panel);"
    "font-family:ui-monospace,'Cascadia Code','Fira Code','Consolas',monospace;"
    "font-size:0.82em;"
    "padding:14px 16px;"
    "white-space:pre-wrap;"
    "border:1px solid var(--t-bdr);"
    "border-radius:6px;"
    "line-height:1.75;"
)

_SCROLL_SNIPPET = (
    '<img src="#" style="display:none" onerror="'
    "(function(){var d=document.getElementById('_diglog');"
    "if(d){d.scrollTop=d.scrollHeight;}})()"
    '">'
)

def _classify_line(raw: str) -> str:
    s = raw.strip()
    if not s:
        return "color:var(--t-txt);"
    upper = s.upper()
    if "PASS" in upper and "FAIL" not in upper:
        return "color:#10b981;font-weight:600;"
    if "FAIL" in upper:
        return "color:#ef4444;font-weight:600;"
    if "ERROR" in upper or "exception" in s.lower() or "traceback" in s.lower():
        return "color:#f59e0b;font-weight:600;"
    if s.startswith(("─", "━", "═")) or (len(s) > 4 and s == s[0] * len(s) and s[0] in "=-"):
        return "color:var(--t-txg);"
    if s.startswith(("Board:", "Suite:", "Config:", "Output:", "Command:", "Results saved:")):
        return "color:var(--t-acc2);font-weight:600;"
    return "color:var(--t-txt);"

def _log_html(lines: list[str], placeholder: str = "(No output yet)") -> str:
    if not lines:
        body = f"<span style='color:var(--t-txg);font-style:italic;'>{_html.escape(placeholder)}</span>"
    else:
        parts = []
        for line in lines:
            css = _classify_line(line)
            parts.append(f"<span style='{css}'>{_html.escape(line)}</span>")
        body = "".join(parts)
    return (
        f'<div id="_diglog" style="{_LOG_STYLE}">{body}</div>'
        + _SCROLL_SNIPPET
    )


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Tracks which test process is currently running (prevents multiple simultaneous tests)
# ─────────────────────────────────────────────────────────────────────────────

_active_proc: subprocess.Popen | None = None  # ← Stores the currently running test process (or None if idle)
_proc_lock    = threading.Lock()              # ← Lock to prevent race conditions between threads
_last_run_dir: Path | None = None             # ← Stores the path to the most recent test results folder


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Builds the command-line arguments passed to test suite launcher scripts
# ─────────────────────────────────────────────────────────────────────────────

def _build_cmd(suite: str, mode: str | None, rails: list[str] | None,
               output_dir: str) -> list[str]:
    # ← Construct the command-line arguments to run the test suite script
    suite_dir, runner = SUITES[suite]  # ← Get test suite folder and runner script name
    cmd = [sys.executable, str(suite_dir / runner),  # ← Start with Python executable and script path
           "--headless", "--output", output_dir or "gui_results"]  # ← Add headless mode and output directory
    
    if mode and suite in SUITE_MODES:  # ← If a test mode is selected and this suite supports modes
        cmd += ["--mode", mode]  # ← Add the mode argument
    
    if rails and suite == "Load Transient":  # ← If rails selected and this is Load Transient test
        cmd += ["--rails", ",".join(rails)]  # ← Add rails as comma-separated list
    elif rails and suite == "Steady-State Ripple":  # ← If rails selected and this is Steady-State Ripple test
        cmd += ["--rails"] + rails  # ← Add each rail as separate argument
    
    return cmd  # ← Return the complete command list


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Main test launcher - spawns subprocess and streams output in real-time
# ─────────────────────────────────────────────────────────────────────────────

def _results_html(log_lines: list[str]) -> str:
    """Combine multi-rail (RESULT_ROW) and power-sequencing (SEQ_RESULT_ROW) tables into one HTML block."""
    parts = []
    multi_rows = _parse_result_rows(log_lines)
    if multi_rows:
        parts.append(_build_results_table_html(multi_rows))
    seq_rows = _parse_seq_result_rows(log_lines)
    if seq_rows:
        parts.append(_build_seq_results_table_html(seq_rows))
    return "".join(parts)


def launch_test(board, suite, mode, rails, output_dir):
    """
    Generator → yields (log_html, status, save_row_update, results_html) on every new line.
    stdin is piped so the user can unblock in-test prompts via the Send button.
    """
    global _active_proc, _last_run_dir  # ← Declare as global so we can modify them

    # ← Validate that user has selected both board and test suite
    if not board or not suite:
        yield _log_html([], "Select a board and suite first."), _status_html("Error"), gr.update(visible=False), ""
        return

    cfg_path = get_config_path(board, suite)
    if cfg_path is None:
        yield _log_html([], f"No config for {board} / {suite}."), _status_html("Error"), gr.update(visible=False), ""
        return

    with _proc_lock:
        if _active_proc is not None and _active_proc.poll() is None:
            yield _log_html([], "A test is already running — click Stop first."), _status_html("Running"), gr.update(visible=False), ""
            return

    # ← Build the command-line arguments for the test script
    cmd = _build_cmd(suite, mode, rails, output_dir)  # ← Get command list
    env = {**os.environ, "DIGANTARA_CONFIG": str(cfg_path), "PYTHONUTF8": "1"}  # ← Set up environment variables

    # ← Create the header text that displays test configuration
    header = [
        f"Board      : {board}\n",  # ← Show selected board name
        f"Suite      : {suite}\n",  # ← Show selected test suite name
        f"Config     : {cfg_path.name}\n",  # ← Show config filename
        f"Output dir : {output_dir or 'gui_results'}\n",  # ← Show output directory
        f"Command    : {' '.join(cmd[2:])}\n",  # ← Show the command being run (skip python exe and path)
        "─" * 60 + "\n",  # ← Draw a line separator
    ]
    yield _log_html(header), _status_html("Running"), gr.update(visible=False), ""

    # ← Spawn the test process
    try:  # ← Wrap in try-except to catch subprocess errors
        with _proc_lock:  # ← Acquire lock for thread safety
            _active_proc = subprocess.Popen(
                cmd,  # ← Command list to run
                stdout=subprocess.PIPE,  # ← Capture stdout as pipe
                stderr=subprocess.STDOUT,  # ← Redirect stderr to stdout
                stdin=subprocess.PIPE,  # ← lets Send button reply to in-test prompts
                text=True, bufsize=1,  # ← Treat output as text, line-buffered
                encoding='utf-8', errors='replace',  # ← Use UTF-8 encoding, replace invalid chars
                env=env, cwd=str(ROOT),  # ← Set environment and working directory
            )
    except Exception as exc:  # ← If subprocess launch fails
        yield _log_html(header + [f"\nFailed to launch: {exc}\n"]), _status_html("Error"), gr.update(visible=False), ""
        return  # ← Stop execution

    # ← Read output from the test process line-by-line
    log_lines = list(header)  # ← Start log with header
    _last_run_dir = None  # ← Initialize last run directory to None

    for line in _active_proc.stdout:  # ← Loop through each line of output
        log_lines.append(line)  # ← Add this line to the log
        m = re.search(r"Results saved[:\s]+(.+)", line)  # ← Search for "Results saved:" pattern
        if m:  # ← If pattern found
            p = Path(m.group(1).strip())  # ← Extract path from the match
            _last_run_dir = p if p.is_absolute() else ROOT / p  # ← Store path (absolute or relative to ROOT)
        yield _log_html(log_lines), _status_html("Running"), gr.update(visible=False), _results_html(log_lines)

    # ← Wait for process to complete and check exit code
    _active_proc.wait()  # ← Wait for process to finish
    rc = _active_proc.returncode  # ← Get the exit code (0 = success, non-zero = failure)
    status = "PASS" if rc == 0 else "FAIL"  # ← Set status based on exit code

    # ← Add exit information to log
    log_lines += ["\n" + "─" * 60 + "\n", f"Process exited with code {rc}\n"]  # ← Show exit code

    # ← Determine if we should show the Save/Delete buttons
    show_save = bool(_last_run_dir and _last_run_dir.exists())  # ← Show buttons only if results folder exists
    if show_save:  # ← If results folder exists
        log_lines += [
            f"\nRun folder : {_last_run_dir}\n",  # ← Show results folder path
            "Choose below whether to keep or delete the results.\n",  # ← Instructions
        ]

    yield _log_html(log_lines), _status_html(status), gr.update(visible=show_save), _results_html(log_lines)

    # ← Clean up: mark process as None so a new test can run
    with _proc_lock:  # ← Acquire lock for thread safety
        _active_proc = None  # ← Clear the process reference


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Sends user input to test process stdin (for answering in-test prompts)
# ─────────────────────────────────────────────────────────────────────────────

def send_to_test(text: str) -> str:
    # ← Send user input to the test process to answer prompts
    """Write user text (+ newline) to subprocess stdin — unblocks in-test input() calls."""
    with _proc_lock:  # ← Acquire lock for thread safety
        proc = _active_proc  # ← Get reference to active process
    
    if proc and proc.poll() is None:  # ← If process exists and is still running
        try:  # ← Wrap in try-except for error handling
            proc.stdin.write((text or "") + "\n")  # ← Write text and newline to stdin
            proc.stdin.flush()  # ← Flush buffer to ensure data is sent immediately
        except Exception:  # ← If write fails
            pass  # ← Silently ignore the error
    
    return ""  # ← Return empty string to clear the input box


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Stop button handler - terminates running test process
# ─────────────────────────────────────────────────────────────────────────────

def stop_test() -> str:
    # ← Terminate the currently running test
    with _proc_lock:  # ← Acquire lock for thread safety
        if _active_proc and _active_proc.poll() is None:  # ← If process exists and is still running
            _active_proc.terminate()  # ← Send SIGTERM to terminate process gracefully
            return _log_html([], "Test stopped by user.")  # ← Return stop message
    
    return _log_html([], "No test is running.")  # ← Return message if no test running


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Keep results - two-step flow: show comments form, then confirm & save
# ─────────────────────────────────────────────────────────────────────────────

def on_keep_click() -> tuple:
    # Step 1: hide the Keep/Delete row, reveal the comments form
    return gr.update(visible=False), gr.update(visible=True)


def confirm_keep(tester_name: str, board_serial: str,
                 board: str, suite: str, comments: str) -> tuple:
    # Step 2: write test_metadata.json to the run folder, then tidy up the UI
    path = _last_run_dir
    if path and path.exists():
        metadata = {
            "tester_name":  tester_name.strip() or "Unknown",
            "board_serial": board_serial.strip() or "N/A",
            "board_type":   board  or "N/A",
            "test_suite":   suite  or "N/A",
            "comments":     comments.strip(),
            "saved_at":     datetime.datetime.now().isoformat(timespec="seconds"),
        }
        (path / "test_metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
    return (
        _log_html([], f"Results saved:\n{path}"),
        gr.update(visible=False),  # hide comments form
        "",                         # clear comments textbox
    )


def on_cancel_keep() -> tuple:
    # User changed their mind — put the Keep/Delete buttons back
    return gr.update(visible=True), gr.update(visible=False)


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Delete results button - removes test output folder (with OS compatibility)
# ─────────────────────────────────────────────────────────────────────────────

def delete_results() -> tuple[str, gr.update]:
    # ← User chose to delete the test results
    global _last_run_dir  # ← Declare as global so we can modify it
    
    path = _last_run_dir  # ← Get the results folder path
    if not path or not path.exists():  # ← If path doesn't exist
        return _log_html([], "Run folder not found — nothing to delete."), gr.update(visible=False)  # ← Show error
    
    try:  # ← Try Windows-specific deletion first (more reliable on network drives)
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)],  # ← Use Windows rmdir command
                       capture_output=True, timeout=5)  # ← Suppress output, wait up to 5 seconds
    except Exception:  # ← If Windows method fails
        pass  # ← Continue to Python method
    
    if path.exists():  # ← If folder still exists (Windows delete failed)
        shutil.rmtree(path, ignore_errors=True)  # ← Use Python's rmtree to delete recursively
    
    # ← Create message based on whether deletion succeeded
    msg = (f"Could not fully delete {path}\n(OneDrive still syncing — delete manually)"  # ← If OneDrive is syncing
           if path.exists() else f"Results deleted:\n{path}")  # ← Or success message
    
    if not path.exists():  # ← If deletion succeeded
        _last_run_dir = None  # ← Clear the global variable
    
    return _log_html([], msg), gr.update(visible=False)  # ← Return message and hide buttons


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Native folder browser dialog using tkinter (Windows/Mac/Linux compatible)
# ─────────────────────────────────────────────────────────────────────────────

def browse_output_dir(current: str) -> str:
    # ← Open a native folder browser dialog and return the chosen path
    """Open a native folder-picker dialog and return the chosen path."""
    try:  # ← Wrap in try-except in case tkinter is not available
        import tkinter as tk  # ← Import tkinter for native dialogs
        from tkinter import filedialog  # ← Import file dialog module
        
        root = tk.Tk()  # ← Create a root window
        root.withdraw()  # ← Hide the root window (we only want the dialog)
        root.wm_attributes("-topmost", True)  # ← Make dialog appear on top of other windows
        
        initial = current.strip() if current.strip() else str(ROOT)  # ← Use current dir or ROOT as default
        
        folder = filedialog.askdirectory(  # ← Show folder picker dialog
            title="Select folder to save test results",  # ← Dialog title
            initialdir=initial,  # ← Start in this directory
        )
        
        root.destroy()  # ← Clean up the root window
        
        if folder:  # ← If user selected a folder (not cancelled)
            return folder  # ← Return the chosen folder path
    except Exception:  # ← If tkinter is unavailable or something fails
        pass  # ← Silently ignore and fall through
    
    return current  # ← Return unchanged if cancelled or tkinter unavailable


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Results table parsing and rendering (for multi-rail SENSOR tests)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_result_rows(lines: list[str]) -> dict:
    """
    Scan log lines for 'RESULT_ROW: <json>' markers emitted by the multi-rail
    test sequence.  Returns:
        { vin_str: { rail_name: {"label": str, "vout": float|None, "status": str} } }
    """
    rows: dict = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("RESULT_ROW:"):
            continue
        try:
            data = json.loads(line[len("RESULT_ROW:"):].strip())
        except Exception:
            continue
        vin  = str(data.get("vin", "?"))
        rail = data.get("rail", "?")
        if vin not in rows:
            rows[vin] = {}
        rows[vin][rail] = {
            "label":  data.get("label", rail),
            "vout":   data.get("vout"),   # float or None
            "status": data.get("status", "?"),
        }
    return rows


# ← Styling constants for the results table
_TBL_WRAP  = (
    "margin-top:18px;overflow-x:auto;"
    "animation:dta-fadein .35s ease both;"
)
_TBL_TITLE = (
    "color:var(--t-acc2);font-weight:700;margin-bottom:10px;font-size:0.78em;"
    "text-transform:uppercase;letter-spacing:2px;"
    "font-family:ui-monospace,'Cascadia Code',monospace;"
    "padding-bottom:8px;border-bottom:1px solid var(--t-bdr);"
)
_TBL_CSS   = (
    "border-collapse:collapse;width:100%;"
    "font-family:ui-monospace,'Cascadia Code','Fira Code','Consolas',monospace;"
    "font-size:0.83em;"
    "background:var(--t-surf);color:var(--t-txt);"
    "border-radius:7px;overflow:hidden;"
)
_TH_CSS    = (
    "background:var(--t-elev);color:var(--t-txd);padding:9px 16px;"
    "text-align:left;border-bottom:1px solid var(--t-bdr);"
    "font-weight:700;font-size:0.75em;text-transform:uppercase;letter-spacing:1.5px;"
)
_TD_CSS    = "padding:8px 16px;border-bottom:1px solid var(--t-bdr2);color:var(--t-txt);"
_PASS_CSS  = "color:#10b981;font-weight:700;"
_FAIL_CSS  = "color:#ef4444;font-weight:700;"
_ERR_CSS   = "color:#f59e0b;font-weight:700;"

_TBL_ROW_HOVER = (
    "<style>#_dta_tbl tr:hover td{background:rgba(59,130,246,.05)!important;}</style>"
)


def _parse_seq_result_rows(lines: list[str]) -> list[dict]:
    """
    Scan log lines for 'SEQ_RESULT_ROW: <json>' markers emitted by the power-
    sequencing test.  Returns a list of dicts in emission order:
        [{"rail": str, "threshold_v": float, "measured_ms": float|None,
          "status": str, "config": str}, ...]
    """
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith("SEQ_RESULT_ROW:"):
            continue
        try:
            data = json.loads(line[len("SEQ_RESULT_ROW:"):].strip())
            rows.append(data)
        except Exception:
            continue
    return rows


def _build_seq_results_table_html(rows: list[dict]) -> str:
    """
    Build an HTML table for power-sequencing results.
    Columns: Rail | 90% Voltage | Measured Time (ms) | Pass/Fail
    Rows are grouped under their Config label.
    """
    if not rows:
        return ""

    # Group rows by config label, preserving order
    configs: dict[str, list[dict]] = {}
    for r in rows:
        cfg = r.get("config", "")
        configs.setdefault(cfg, []).append(r)

    th_base = _TH_CSS
    td_base = _TD_CSS
    cfg_hdr = (
        "background:var(--t-elev);color:var(--t-acc2);padding:7px 16px;"
        "border-bottom:1px solid var(--t-bdr);font-style:italic;font-size:0.80em;font-weight:600;"
    )

    headers = ["Rail", "90% Voltage", "Measured Time (ms)", "Pass/Fail"]
    th_row  = "".join(f"<th style='{th_base}'>{h}</th>" for h in headers)
    thead   = f"<thead><tr>{th_row}</tr></thead>"

    tbody_parts = []
    for cfg_label, cfg_rows in configs.items():
        if cfg_label:
            tbody_parts.append(
                f"<tr><td colspan='4' style='{cfg_hdr}'>{cfg_label}</td></tr>"
            )
        for r in cfg_rows:
            rail    = r.get("rail", "?")
            thr_v   = r.get("threshold_v")
            meas_ms = r.get("measured_ms")
            status  = r.get("status", "?")

            thr_str  = f"{thr_v:.3f} V" if thr_v is not None else "—"
            meas_str = f"{meas_ms:.3f}" if meas_ms is not None else "N/A"

            if status == "PASS":
                s_css = _PASS_CSS
            elif status == "FAIL":
                s_css = _FAIL_CSS
            else:
                s_css = _ERR_CSS

            cells = (
                f"<td style='{td_base}'>{rail}</td>"
                f"<td style='{td_base}'>{thr_str}</td>"
                f"<td style='{td_base}'>{meas_str}</td>"
                f"<td style='{td_base}{s_css}'>{status}</td>"
            )
            tbody_parts.append(f"<tr>{cells}</tr>")

    tbody = f"<tbody>{''.join(tbody_parts)}</tbody>"
    tbl   = f"<table id='_dta_tbl' style='{_TBL_CSS}'>{thead}{tbody}</table>"
    return (
        _TBL_ROW_HOVER
        + f"<div style='{_TBL_WRAP}'>"
        + f"<div style='{_TBL_TITLE}'>Results</div>"
        + tbl
        + "</div>"
    )


def _build_results_table_html(rows: dict) -> str:
    """
    Build an HTML table from parsed result rows.
    Columns: VIN (V) | <label for each rail> | Status
    """
    if not rows:
        return ""

    # Collect ordered rail names and their display labels
    rail_order:  list[str] = []
    rail_labels: dict[str, str] = {}
    for vin_data in rows.values():
        for rail_name, info in vin_data.items():
            if rail_name not in rail_order:
                rail_order.append(rail_name)
                rail_labels[rail_name] = info.get("label", rail_name)

    # Build header row
    th = "".join(f"<th style='{_TH_CSS}'>{h}</th>" for h in (
        ["VIN (V)"] + [rail_labels[r] for r in rail_order] + ["Status"]
    ))
    thead = f"<thead><tr>{th}</tr></thead>"

    # Sort VIN values numerically
    try:
        sorted_vins = sorted(rows.keys(), key=float)
    except ValueError:
        sorted_vins = sorted(rows.keys())

    tbody_rows = []
    for vin in sorted_vins:
        vin_data   = rows[vin]
        statuses   = [vin_data.get(r, {}).get("status", "?") for r in rail_order]
        if all(s == "PASS" for s in statuses):
            overall, s_css = "PASS", _PASS_CSS
        elif any(s == "FAIL" for s in statuses):
            overall, s_css = "FAIL", _FAIL_CSS
        else:
            overall, s_css = statuses[0] if len(statuses) == 1 else "?", _ERR_CSS

        cells = f"<td style='{_TD_CSS}'>{vin}</td>"
        for r in rail_order:
            vout = vin_data.get(r, {}).get("vout")
            cells += f"<td style='{_TD_CSS}'>{f'{vout:.4f}' if vout is not None else '—'}</td>"
        cells += f"<td style='{_TD_CSS}{s_css}'>{overall}</td>"
        tbody_rows.append(f"<tr>{cells}</tr>")

    tbody = f"<tbody>{''.join(tbody_rows)}</tbody>"

    return (
        _TBL_ROW_HOVER
        + f"<div style='{_TBL_WRAP}'>"
        + f"<div style='{_TBL_TITLE}'>Results</div>"
        + f"<table id='_dta_tbl' style='{_TBL_CSS}'>{thead}{tbody}</table>"
        + "</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: CSS styling rules for Gradio UI elements (status box, buttons, layout)
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
/* == Theme variables (Orbital default) ===================================== */
:root {
    --t-bg:    #020617;
    --t-panel: #0a0f1e;
    --t-surf:  #0c1220;
    --t-elev:  #0f172a;
    --t-bdr:   #1a2540;
    --t-bdr2:  #0f1a2e;
    --t-acc:   #2563eb;
    --t-acc2:  #4fc3f7;
    --t-txt:   #8892a4;
    --t-txh:   #c8d6ea;
    --t-txd:   #4a5f7a;
    --t-txg:   #2d4060;
}

/* == Base ================================================================= */
.gradio-container {
    background : var(--t-bg) !important;
    max-width  : 100%    !important;
    padding    : 0       !important;
    font-family: ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif !important;
}
footer { display:none !important; }
.main  { padding:20px 24px !important; max-width:100% !important; }

/* Strip Gradio's default block chrome */
.block,.gr-block,.form {
    background:transparent !important; border:none !important;
    padding:0 !important; margin:0 !important; box-shadow:none !important;
}

/* == Inputs ================================================================ */
textarea, input[type="text"], input[type="number"] {
    background   : var(--t-surf) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px    !important;
    color        : var(--t-txh) !important;
    font-size    : 0.87em  !important;
    transition   : border-color .15s, box-shadow .15s !important;
}
textarea:focus, input:focus {
    border-color : var(--t-acc) !important;
    box-shadow   : 0 0 0 3px rgba(59,130,246,.1) !important;
    outline      : none    !important;
}

/* == Labels ================================================================ */
label span, .label-wrap span {
    color          : var(--t-txd) !important;
    font-size      : 0.72em  !important;
    font-weight    : 700     !important;
    text-transform : uppercase !important;
    letter-spacing : 1.1px   !important;
}

/* == Dropdowns ============================================================= */
select {
    background   : var(--t-surf) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px     !important;
    color        : var(--t-txh) !important;
}

/* == Rail checkboxes ======================================================= */
fieldset, .gr-checkbox-group {
    background   : var(--t-surf) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px !important;
    padding      : 8px !important;
}

/* == RUN =================================================================== */
#run-btn > button {
    background    : var(--t-acc) !important;
    color         : #fff    !important;
    border        : none    !important;
    border-radius : 6px     !important;
    font-weight   : 600     !important;
    letter-spacing: 0.4px   !important;
    transition    : background .15s, box-shadow .15s, transform .1s !important;
    box-shadow    : 0 1px 2px rgba(0,0,0,.4),
                    inset 0 1px 0 rgba(255,255,255,.07) !important;
}
#run-btn > button:hover  {
    background : var(--t-acc2) !important;
    box-shadow : 0 4px 14px rgba(59,130,246,.35) !important;
    transform  : translateY(-1px) !important;
}
#run-btn > button:active { transform:translateY(0) scale(0.98) !important; }

/* == STOP ================================================================== */
#stop-btn > button {
    background   : transparent !important;
    color        : var(--t-txd) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px  !important;
    font-weight  : 600  !important;
    letter-spacing: 0.3px !important;
    transition   : all .18s ease !important;
}
#stop-btn > button:hover {
    color        : #ef4444 !important;
    border-color : rgba(239,68,68,.45) !important;
    background   : rgba(239,68,68,.06) !important;
    box-shadow   : 0 0 12px rgba(239,68,68,.12) !important;
    transform    : translateY(-1px) !important;
}
#stop-btn > button:active { transform:translateY(0) !important; }

/* == Utility buttons ======================================================= */
#browse-btn > button, #send-btn > button {
    background   : transparent !important;
    color        : var(--t-txd) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px  !important;
    font-size    : 0.83em !important;
    font-weight  : 500 !important;
    transition   : all .15s ease !important;
}
#browse-btn > button:hover, #send-btn > button:hover {
    color        : var(--t-txt)    !important;
    border-color : var(--t-txg)   !important;
    background   : rgba(59,130,246,.05) !important;
    transform    : translateY(-1px) !important;
}
#browse-btn > button:active, #send-btn > button:active { transform:translateY(0) !important; }

/* == Keep ================================================================== */
#keep-btn > button {
    background   : rgba(16,185,129,.08) !important;
    color        : #10b981    !important;
    border       : 1px solid rgba(16,185,129,.3) !important;
    border-radius: 6px !important;
    font-weight  : 700 !important;
    font-size    : .88em !important;
    letter-spacing: 0.3px !important;
    transition   : all .18s ease !important;
}
#keep-btn > button:hover {
    background   : rgba(16,185,129,.14) !important;
    border-color : rgba(16,185,129,.6) !important;
    box-shadow   : 0 0 14px rgba(16,185,129,.2) !important;
    transform    : translateY(-1px) !important;
}
#keep-btn > button:active { transform:translateY(0) !important; }

/* == Delete ================================================================ */
#delete-btn > button {
    background   : transparent !important;
    color        : var(--t-txd) !important;
    border       : 1px solid var(--t-bdr) !important;
    border-radius: 6px  !important;
    font-weight  : 600  !important;
    font-size    : .88em !important;
    letter-spacing: 0.3px !important;
    transition   : all .18s ease !important;
}
#delete-btn > button:hover {
    color        : #ef4444 !important;
    border-color : rgba(239,68,68,.4) !important;
    background   : rgba(239,68,68,.05) !important;
    transform    : translateY(-1px) !important;
}
#delete-btn > button:active { transform:translateY(0) !important; }

/* == Save row ============================================================== */
#save-row {
    border        : 1px solid rgba(16,185,129,.2) !important;
    border-radius : 8px  !important;
    padding       : 14px !important;
    margin-top    : 16px !important;
    background    : rgba(16,185,129,.03) !important;
}

/* == Animations ============================================================ */
@keyframes dta-pulse  { 0%,100%{opacity:1} 50%{opacity:.35} }
@keyframes dta-fadein { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }

/* == Theme switcher ======================================================== */
#theme-dd { max-width:160px !important; }
#theme-dd select { font-size:0.78em !important; border-radius:20px !important; padding:3px 8px !important; }
#theme-dd label span { display:none !important; }

/* == Comments / metadata form ============================================== */
#comments-form {
    border        : 1px solid rgba(16,185,129,.2) !important;
    border-radius : 8px  !important;
    padding       : 14px !important;
    margin-top    : 12px !important;
    background    : rgba(16,185,129,.02) !important;
    animation     : dta-fadein .25s ease both !important;
}
#confirm-save-btn > button {
    background    : #10b981 !important;
    color         : #fff    !important;
    border        : none    !important;
    border-radius : 6px     !important;
    font-weight   : 700     !important;
    letter-spacing: 0.4px   !important;
    transition    : all .18s ease !important;
}
#confirm-save-btn > button:hover {
    background    : #059669 !important;
    box-shadow    : 0 0 16px rgba(16,185,129,.3) !important;
    transform     : translateY(-1px) !important;
}
#confirm-save-btn > button:active { transform:translateY(0) !important; }
#cancel-save-btn > button {
    background    : transparent !important;
    color         : var(--t-txd) !important;
    border        : 1px solid var(--t-bdr) !important;
    border-radius : 6px !important;
    font-weight   : 500 !important;
    transition    : all .15s ease !important;
}
#cancel-save-btn > button:hover {
    color         : var(--t-txt) !important;
    border-color  : var(--t-txg) !important;
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Theme CSS overrides — each redefines the :root CSS variables
# ─────────────────────────────────────────────────────────────────────────────

_THEME_CSS: dict[str, str] = {
    "Orbital": "",  # default — no override needed

    "Retro": """<style>
:root {
    --t-bg:    #020602; --t-panel: #030903; --t-surf: #040b04; --t-elev: #060e06;
    --t-bdr:   #0f2a0f; --t-bdr2: #081508;
    --t-acc:   #00cc44; --t-acc2: #00ff66;
    --t-txt:   #4d9960; --t-txh:  #80ff99; --t-txd:  #2d6b3d; --t-txg:  #1a3d22;
}
.gradio-container { background: #020602 !important; }
textarea, input[type="text"], input[type="number"] { color: #80ff99 !important; caret-color: #00ff66; }
#run-btn > button { background: #00aa33 !important; }
#run-btn > button:hover { background: #00cc44 !important; box-shadow: 0 4px 14px rgba(0,204,68,.35) !important; }
</style>""",

    "Amber": """<style>
:root {
    --t-bg:    #0c0700; --t-panel: #0f0900; --t-surf: #130b00; --t-elev: #170d00;
    --t-bdr:   #3d2200; --t-bdr2: #1f1100;
    --t-acc:   #e8900a; --t-acc2: #ffb830;
    --t-txt:   #8a6520; --t-txh:  #f0c040; --t-txd:  #5c4010; --t-txg:  #3d2a00;
}
.gradio-container { background: #0c0700 !important; }
textarea, input[type="text"], input[type="number"] { color: #f0c040 !important; caret-color: #ffb830; }
#run-btn > button { background: #c07000 !important; }
#run-btn > button:hover { background: #e8900a !important; box-shadow: 0 4px 14px rgba(232,144,10,.35) !important; }
</style>""",

    "Synthwave": """<style>
:root {
    --t-bg:    #0d0015; --t-panel: #130020; --t-surf: #170026; --t-elev: #1c002f;
    --t-bdr:   #3d0066; --t-bdr2: #1f0035;
    --t-acc:   #c026d3; --t-acc2: #06b6d4;
    --t-txt:   #9f6bc4; --t-txh:  #e879f9; --t-txd:  #5c3080; --t-txg:  #3d1f55;
}
.gradio-container { background: #0d0015 !important; }
textarea, input[type="text"], input[type="number"] { color: #e879f9 !important; caret-color: #c026d3; }
#run-btn > button { background: linear-gradient(135deg, #7c3aed, #c026d3) !important; }
#run-btn > button:hover { background: linear-gradient(135deg, #9333ea, #db2777) !important; box-shadow: 0 4px 14px rgba(192,38,211,.4) !important; }
</style>""",

    "Arctic": """<style>
:root {
    --t-bg:    #f0f4f8; --t-panel: #e2e8f0; --t-surf: #ffffff; --t-elev: #dce3ea;
    --t-bdr:   #cbd5e1; --t-bdr2: #e2e8f0;
    --t-acc:   #1d4ed8; --t-acc2: #0284c7;
    --t-txt:   #475569; --t-txh:  #0f172a; --t-txd:  #64748b; --t-txg:  #94a3b8;
}
.gradio-container { background: #f0f4f8 !important; }
.main { background: #f0f4f8 !important; }
textarea, input[type="text"], input[type="number"] {
    color: #0f172a !important;
    background: #ffffff !important;
    border-color: #cbd5e1 !important;
}
textarea:focus, input:focus { box-shadow: 0 0 0 3px rgba(29,78,216,.12) !important; }
select { color: #0f172a !important; }
label span, .label-wrap span { color: #64748b !important; }
#run-btn > button { background: #1d4ed8 !important; box-shadow: 0 1px 3px rgba(0,0,0,.15) !important; }
#run-btn > button:hover { background: #2563eb !important; box-shadow: 0 4px 14px rgba(29,78,216,.3) !important; }
</style>""",
}


def apply_theme(theme: str) -> str:
    return _THEME_CSS.get(theme, "")


# ── Status pill ──────────────────────────────────────────────────────────────
_STATUS_CFG: dict[str, tuple] = {
    "Ready":   ("var(--t-txd)", "var(--t-bdr)", "var(--t-surf)", ""),
    "Running": ("#3b82f6", "rgba(59,130,246,.35)",  "rgba(59,130,246,.07)",  "animation:dta-pulse 1.4s ease-in-out infinite;"),
    "PASS":    ("#10b981", "rgba(16,185,129,.4)",   "rgba(16,185,129,.07)",  ""),
    "FAIL":    ("#ef4444", "rgba(239,68,68,.4)",    "rgba(239,68,68,.07)",   ""),
    "Error":   ("#f59e0b", "rgba(245,158,11,.4)",   "rgba(245,158,11,.07)",  ""),
}

def _status_html(status: str) -> str:
    cfg = _STATUS_CFG.get(status, _STATUS_CFG["Ready"])
    color, border_color, bg_color, anim = cfg
    return (
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"padding:9px 16px;background:{bg_color};"
        f"border:1px solid {border_color};"
        f"border-radius:7px;transition:all .3s ease;{anim}'>"
        f"<div style='width:8px;height:8px;border-radius:50%;"
        f"background:{color};box-shadow:0 0 9px {color};flex-shrink:0;'></div>"
        f"<span style='color:{color};font-family:ui-monospace,Consolas,monospace;"
        f"font-size:0.78em;font-weight:700;letter-spacing:3px;"
        f"text-transform:uppercase;'>{status}</span>"
        f"</div>"
    )

def _section_header(title: str) -> str:
    return (
        f"<div style='color:var(--t-txd);font-size:0.63em;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:2px;"
        f"padding:16px 0 7px 0;border-bottom:1px solid var(--t-bdr2);margin-bottom:8px;'>{title}</div>"
    )

_HEADER_HTML = (
    "<div style='display:flex;align-items:center;gap:10px;"
    "padding:0 0 18px 0;border-bottom:1px solid #0f1a2e;margin-bottom:2px;'>"
    "<div style='width:7px;height:7px;border-radius:50%;background:#2563eb;"
    "box-shadow:0 0 12px rgba(37,99,235,.8);flex-shrink:0;'></div>"
    "<span style='color:#1e3050;font-size:0.7em;font-weight:700;"
    "letter-spacing:2.5px;text-transform:uppercase;'>Digantara</span>"
    "<span style='color:#0f1a2e;'> / </span>"
    "<span style='color:#64748b;font-size:0.88em;font-weight:600;"
    "letter-spacing:-0.2px;'>Test Automation</span>"
    "</div>"
)

def build_gui() -> gr.Blocks:
    # ← Build the Gradio web interface with all controls and layouts
    all_boards     = get_available_boards()  # ← Get list of all discovered boards
    default_board  = all_boards[0] if all_boards else None  # ← Use first board as default
    default_suites = get_suites_for_board(default_board) if default_board else []  # ← Get suites for default board
    default_suite  = default_suites[0] if default_suites else None  # ← Use first suite as default

    with gr.Blocks(
        title="Digantara Test Automation",
        theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate"),
        css=_CSS,
    ) as demo:

        theme_css = gr.HTML(value="", visible=True)

        with gr.Row(elem_classes=["header-row"]):
            with gr.Column(scale=4):
                gr.HTML(value=_HEADER_HTML)
            with gr.Column(scale=1, min_width=120):
                theme_dd = gr.Dropdown(
                    choices=["Orbital", "Retro", "Amber", "Synthwave", "Arctic"],
                    value="Orbital",
                    label="Theme",
                    elem_id="theme-dd",
                )

        with gr.Row(equal_height=False):

            # ── Left panel: config controls ────────────────────────────────
            with gr.Column(scale=1, min_width=260):

                board_dd = gr.Dropdown(
                    choices=all_boards, value=default_board,
                    label="Board Under Test",
                    info="Auto-detected from *_config.json files",
                )
                suite_dd = gr.Dropdown(
                    choices=default_suites, value=default_suite,
                    label="Test Suite",
                    info="Only suites with a config for the selected board appear here",
                )
                instr_html = gr.HTML(value="")

                mode_dd = gr.Dropdown(
                    choices=[], label="Mode", visible=False,
                )
                rails_cb = gr.CheckboxGroup(
                    choices=[], label="Rails", visible=False,
                )

                gr.HTML(value=_section_header("Test Session"))
                tester_name_tb = gr.Textbox(
                    label="Engineers Name",
                    placeholder="Your name…",
                    lines=1,
                )
                board_serial_tb = gr.Textbox(
                    label="Board Serial / Batch #",
                    placeholder="e.g. CPU-001, SN-2024-A3…",
                    lines=1,
                )

                gr.HTML(value=_section_header("Output"))
                with gr.Row():
                    output_tb = gr.Textbox(
                        value="gui_results",
                        placeholder="Results folder…",
                        show_label=False, lines=1, scale=4,
                    )
                    browse_btn = gr.Button("Browse", scale=1, size="sm",
                                           elem_id="browse-btn")

                gr.HTML(value="<div style='height:8px'></div>")
                with gr.Row():
                    run_btn  = gr.Button("Run",  variant="primary", size="lg",
                                          elem_id="run-btn")
                    stop_btn = gr.Button("Stop", variant="secondary", size="lg",
                                          elem_id="stop-btn")

            # ── Right panel: output & results ──────────────────────────────
            with gr.Column(scale=2):

                status_box = gr.HTML(value=_status_html("Ready"))

                gr.HTML(value="<div style='height:10px'></div>")
                log_html = gr.HTML(value=_log_html([], "(No output yet)"))

                gr.HTML(value="<div style='height:6px'></div>")
                with gr.Row():
                    send_tb = gr.Textbox(
                        placeholder="Press Send (or Enter) to continue — type here only if the test is asking a question",
                        label="", lines=1, scale=5,
                    )
                    send_btn = gr.Button("Send", scale=1, size="sm",
                                         elem_id="send-btn")

                results_html = gr.HTML(value="")

                with gr.Row(elem_id="save-row", visible=False) as save_row:
                    keep_btn   = gr.Button("Keep Results",   variant="primary",
                                           elem_id="keep-btn")
                    delete_btn = gr.Button("Delete Results", variant="stop",
                                           elem_id="delete-btn")

                with gr.Column(elem_id="comments-form", visible=False) as comments_form:
                    comments_tb = gr.Textbox(
                        label="Test Comments",
                        placeholder="Observations, anomalies, pass conditions, anything noteworthy…",
                        lines=3,
                    )
                    with gr.Row():
                        confirm_save_btn = gr.Button("Confirm & Save", variant="primary",
                                                     elem_id="confirm-save-btn")
                        cancel_save_btn  = gr.Button("← Back",
                                                     elem_id="cancel-save-btn")

        # ── Event handlers and wiring ──────────────────────────────────────────

        # ← Handler function when board dropdown changes
        def on_board_change(board):
            # ← Update suite dropdown when board selection changes
            suites = get_suites_for_board(board)  # ← Get suites available for this board
            new_suite = suites[0] if suites else None  # ← Select first suite as default
            return (
                gr.update(choices=suites, value=new_suite),  # ← Update suite dropdown
                _instrument_info_html(board, new_suite),  # ← Update instruments sidebar
            )

        # ← Handler function when suite dropdown changes
        def on_suite_change(board, suite):
            # ← Update mode and rails dropdowns when suite selection changes
            if not board or not suite:  # ← If board or suite not selected
                return (gr.update(choices=[], value=None,  visible=False),  # ← Clear mode dropdown
                        gr.update(choices=[], value=[],    visible=False),  # ← Clear rails checkboxes
                        "")  # ← Clear instruments sidebar
            
            modes  = SUITE_MODES.get(suite)  # ← Get available modes for this suite
            cfgp   = get_config_path(board, suite)  # ← Get config path
            rails  = get_rails_for_suite(suite, cfgp) if cfgp else None  # ← Get available rails from config
            return (
                gr.update(choices=modes or [], value=modes[0] if modes else None,  # ← Update modes dropdown
                          visible=bool(modes)),  # ← Show only if suite has modes
                gr.update(choices=rails or [], value=rails or [],  # ← Update rails checkboxes
                          visible=bool(rails)),  # ← Show only if suite has rails
                _instrument_info_html(board, suite),  # ← Update instruments sidebar
            )

        # ← Wire board dropdown change event to handler
        board_dd.change(on_board_change,  inputs=board_dd,            outputs=[suite_dd, instr_html])
        
        # ← Wire suite dropdown change event to handler
        suite_dd.change(on_suite_change,  inputs=[board_dd, suite_dd], outputs=[mode_dd, rails_cb, instr_html])

        # ← Wire browse button to folder picker
        browse_btn.click(browse_output_dir, inputs=output_tb, outputs=output_tb)

        # ← Wire Run button to test launcher
        run_btn.click(
            fn=launch_test,
            inputs=[board_dd, suite_dd, mode_dd, rails_cb, output_tb],
            outputs=[log_html, status_box, save_row, results_html],
        )
        
        # ← Wire Stop button to test stopper
        stop_btn.click(fn=stop_test, outputs=log_html)  # ← Update log with stop message

        # ← Wire Send button to input handler
        send_btn.click(fn=send_to_test, inputs=send_tb, outputs=send_tb)  # ← Send input and clear box
        
        # ← Wire textbox Enter key to input handler (same function)
        send_tb.submit( fn=send_to_test, inputs=send_tb, outputs=send_tb)  # ← Send on Enter key

        # ← Keep: hide save row, reveal comments form
        keep_btn.click(fn=on_keep_click, outputs=[save_row, comments_form])

        # ← Cancel: put save row back, hide comments form
        cancel_save_btn.click(fn=on_cancel_keep, outputs=[save_row, comments_form])

        # ← Confirm & Save: write metadata.json, clear form, show confirmation
        confirm_save_btn.click(
            fn=confirm_keep,
            inputs=[tester_name_tb, board_serial_tb, board_dd, suite_dd, comments_tb],
            outputs=[log_html, comments_form, comments_tb],
        )

        # ← Delete Results button
        delete_btn.click(fn=delete_results, outputs=[log_html, save_row])

        # ← Initialize interface when page loads
        demo.load(fn=on_suite_change, inputs=[board_dd, suite_dd],  # ← Call suite change handler with default values
                  outputs=[mode_dd, rails_cb, instr_html])  # ← Update these outputs

        # ← Wire theme dropdown to inject CSS variable overrides
        theme_dd.change(fn=apply_theme, inputs=theme_dd, outputs=theme_css)

    return demo  # ← Return the completed interface


# ─────────────────────────────────────────────────────────────────────────────
# ↓ BELOW: Entry point - initializes and launches the web application
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ← Script entry point (runs when file is executed directly)
    print("Digantara Test Automation GUI")  # ← Print startup message
    print(f"Project root : {ROOT}")  # ← Print the project folder location
    boards = get_available_boards()  # ← Scan for available boards
    print(f"Boards found : {', '.join(boards) if boards else 'none'}")  # ← Print discovered boards
    build_gui().launch(inbrowser=True)  # ← Build the interface and launch in default web browser
