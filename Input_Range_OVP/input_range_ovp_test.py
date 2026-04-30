# This first line (the "shebang") tells Linux/macOS to run this file using Python 3; it is harmless on Windows
#!/usr/bin/env python3
# This module-level docstring describes the overall purpose of this file, the test phases it performs, its output structure, configuration file requirements, and the instruments it uses
"""
Input Range and OVP Test

Characterises the complete power input behaviour of the DUT:
  1. Prompts the operator to connect DMM probes on the DUT output.
  2. Fixed Vin tests — PSU holds each configured voltage, DMM reads Vout,
     Pass/Fail result recorded.
  3. Sweep test — PSU ramps 0 -> Vmax -> 0 in configurable steps. DMM reads
     continuously. Two graphs are saved.
  4. Reports generated in a timestamped run folder:
       reports/  — CSV, JSON, and TXT summary
       plots/    — PSU and DMM waveform graphs

All settings are read from input_range_ovp_config.json (same folder).
That file is mandatory — the program exits if it is missing or has invalid JSON.

Instruments:
  - Keithley Power Supply (keithley_power_supply.KeithleyPowerSupply)
  - Keithley DMM6500     (keithley_dmm.KeithleyDMM6500)
"""

# Load the 'sys' library which provides access to system-level operations such as exiting the program and modifying the Python module search path
import sys
# Load the 'csv' library which allows the program to read and write comma-separated-value files (spreadsheets) for storing test results
import csv
# Load the 'json' library which allows the program to read and write JSON files, used for the configuration file and result reports
import json
# Load the 'time' library which provides timing functions such as sleep (pause) and measuring elapsed time
import time
# Load the 'logging' library which allows the program to write timestamped event records to a log file for tracing and debugging
import logging
# Load the 'datetime' library which provides tools for working with dates and times, used for timestamping the results folder and log entries
import datetime
# Import 'Path' from the 'pathlib' library, which provides an object-oriented cross-platform way to work with file and directory paths
from pathlib import Path
# Import 'dataclass' and 'field' from the 'dataclasses' library; 'dataclass' is a decorator that creates data-holding classes with minimal code, and 'field' lets you specify default values
from dataclasses import dataclass, field
# Import type hints from the 'typing' library: 'List' for a list, 'Optional' for a value that may be None, 'Tuple' for a fixed-length pair of values
from typing import List, Optional, Tuple

# Add the parent directory (one level above this file's folder) to the module search path so shared libraries like instrument_control can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

# Attempt to import the matplotlib graphing library; if it is not installed, the program will still run but will skip graph generation
try:
    # Import the top-level matplotlib module so we can configure its backend before importing pyplot
    import matplotlib
    # Set matplotlib to use the 'Agg' backend, which renders graphs to image files without needing a screen or graphical display
    matplotlib.use('Agg')
    # Import the pyplot sub-module which provides the functions used to draw graphs (lines, axes, labels, etc.)
    import matplotlib.pyplot as plt
    # Import the dates sub-module from matplotlib, which provides formatting tools for time-axis graphs
    import matplotlib.dates as mdates
    # Set a flag to True indicating that matplotlib was successfully imported and graphs can be generated
    _MATPLOTLIB_AVAILABLE = True
# If matplotlib is not installed, catch the ImportError silently
except ImportError:
    # Set the flag to False so the rest of the code knows to skip any graph-generation steps
    _MATPLOTLIB_AVAILABLE = False

# Import the KeithleyPowerSupply class from the instrument_control module so the program can control the Keithley bench power supply
from instrument_control.keithley_power_supply import KeithleyPowerSupply
# Import the KeithleyDMM6500 class from the instrument_control module so the program can control the Keithley digital multimeter
from instrument_control.keithley_dmm import KeithleyDMM6500

# [Blank line for visual separation]

# ═════════════════════════════════════════════════════════════════════════════
# CONFIG LOADING — reads board config once at startup
# ═════════════════════════════════════════════════════════════════════════════

# If the DIGANTARA_CONFIG environment variable is set (e.g. by the Gradio GUI launching this
# module via subprocess), use that path so the correct board config (CPU, SENSOR, IAP, …) is
# loaded without modifying this file.  If the variable is absent the default CPU config in the
# same folder is used, so the runner still works when invoked directly from the terminal.
import os as _os
_env_cfg = _os.environ.get("DIGANTARA_CONFIG")
_CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path(__file__).parent / "CPU_config.json"

# [Blank line for visual separation]

# [Blank line for visual separation]
def _load_config(path: Path = _CONFIG_PATH) -> dict:
    # This function reads the JSON configuration file and returns its contents as a Python dictionary; if the file is missing or broken it immediately stops the program with a clear error message
    """
    Load the JSON config file. Exits the program if the file is missing or
    contains invalid JSON — the config is mandatory, not optional.
    """
    # Begin a try block to attempt opening and parsing the configuration file
    try:
        # Open the configuration file in read mode using UTF-8 character encoding to support all characters
        with open(path, "r", encoding="utf-8") as f:
            # Parse the JSON text from the file into a Python dictionary
            cfg = json.load(f)
        # Print a confirmation message showing the name of the config file that was loaded
        print(f"Loaded config from {path.name}")
        # Return the loaded configuration dictionary to the caller
        return cfg
    # If the file does not exist at the expected location, catch the error and report it clearly
    except FileNotFoundError:
        # Print an error message telling the engineer the config file was not found
        print(f"ERROR: Config file not found: {path}")
        # Print a helpful explanation of where the file needs to be placed
        print(f"       This file is required. Ensure {_CONFIG_PATH.name} is in the same folder.")
        # Exit the program immediately with error code 1, since the test cannot run without configuration
        sys.exit(1)
    # If the file exists but contains invalid JSON syntax, catch the error and report it clearly
    except json.JSONDecodeError as e:
        # Print an error message showing the specific JSON parsing error
        print(f"ERROR: Config file has invalid JSON: {e}")
        # Tell the engineer to fix the configuration file before running the test again
        print(f"       Fix {_CONFIG_PATH.name} before running the test.")
        # Exit the program immediately with error code 1
        sys.exit(1)

# [Blank line for visual separation]

# Call _load_config() once when this module is first imported and store the result in _CFG; every class and function in this file uses this global variable for all configuration settings
_CFG = _load_config()   # loaded once; every class/function below uses _CFG

# [Blank line for visual separation]

# ═════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═════════════════════════════════════════════════════════════════════════════

# Define FixedVinPoint as a dataclass — a lightweight container that holds one fixed-voltage test specification: what input voltage to apply and what output voltage is expected
@dataclass
class FixedVinPoint:
    # Store the input voltage (in volts) that the power supply will be set to during this test point
    vin_v: float
    # Store the output voltage (in volts) that the DUT is expected to produce at this input voltage
    expected_vout_v: float
    # Store the allowed tolerance (in volts) around the expected output voltage; defaults to ±0.1 V
    vout_tolerance_v: float = 0.1

# [Blank line for visual separation]

# [Blank line for visual separation]
# Define FixedVinResult as a dataclass that stores the measured result for one fixed-voltage test point, including what was expected, what was measured, and whether it passed or failed
@dataclass
class FixedVinResult:
    # Store the input voltage (in volts) that was applied during this test point
    vin_v: float
    # Store the output voltage (in volts) that the DMM actually measured; None if the measurement failed
    vout_v: Optional[float]
    # Store the output voltage (in volts) that was expected for this input
    expected_vout_v: float
    # Store the tolerance (in volts) that was allowed around the expected value
    vout_tolerance_v: float
    # Store the outcome of this test point as a text string: "PASS", "FAIL", or "ERROR"
    status: str   # "PASS", "FAIL", or "ERROR"

    # Define a method that converts this result object into a plain Python dictionary, suitable for writing to a JSON report file
    def to_dict(self) -> dict:
        # Return a dictionary containing all the result fields with their values
        return {
            # Include the input voltage that was applied
            'vin_v': self.vin_v,
            # Include the measured output voltage
            'vout_v': self.vout_v,
            # Include the expected output voltage for reference
            'expected_vout_v': self.expected_vout_v,
            # Include the tolerance window that was used for the pass/fail decision
            'vout_tolerance_v': self.vout_tolerance_v,
            # Include the final pass/fail/error status string
            'status': self.status,
        }

# [Blank line for visual separation]

# [Blank line for visual separation]
# Define SweepSample as a dataclass that stores one data point captured during the input voltage sweep test
@dataclass
class SweepSample:
    # Store the number of seconds elapsed since the sweep test started
    elapsed_s: float
    # Store the actual wall-clock date and time when this sample was taken
    real_time: datetime.datetime
    # Store the voltage level (in volts) that the power supply was commanded to output at this step
    psu_setpoint_v: float
    # Store the actual voltage (in volts) that the power supply measured at its own terminals
    psu_measured_v: float
    # Store the current (in amps) that the power supply was delivering at this moment
    psu_current_a: float
    # Store the output voltage (in volts) measured by the DMM at the DUT output terminal
    dmm_v: float

# [Blank line for visual separation]

# [Blank line for visual separation]
# Define SweepResult as a dataclass that stores the overall outcome of the input voltage sweep test
@dataclass
class SweepResult:
    # Store a human-readable description of the voltage range swept, e.g. "0 - 30V"
    vin_range: str
    # Store the average DUT output voltage (in volts) measured across all operating-range samples
    vout_v: float
    # Store the expected DUT output voltage (in volts) for comparison
    expected_vout_v: float
    # Store the overall sweep result as a text string: "PASS", "FAIL", "ERROR", or "NOT_RUN"
    status: str   # "PASS", "FAIL", "ERROR", or "NOT_RUN"
    # Store the list of individual data samples collected during the sweep; defaults to an empty list
    samples: List[SweepSample] = field(default_factory=list)

    # Define a method that converts this sweep result into a plain Python dictionary for writing to JSON reports
    def to_dict(self) -> dict:
        # Return a dictionary with the key fields from the sweep result
        return {
            # Include the voltage range description string
            'vin_range': self.vin_range,
            # Include the average measured output voltage
            'vout_v': self.vout_v,
            # Include the expected output voltage
            'expected_vout_v': self.expected_vout_v,
            # Include the pass/fail/error status
            'status': self.status,
            # Include the total number of data samples captured during the sweep
            'sample_count': len(self.samples),
        }

# [Blank line for visual separation]

# ═════════════════════════════════════════════════════════════════════════════
# CONFIG BUILDER HELPERS
# ═════════════════════════════════════════════════════════════════════════════

# Define a helper function that reads the fixed-Vin test point list from the configuration dictionary and returns it as a list of FixedVinPoint objects
def _build_fixed_vin_tests(cfg: dict) -> List[FixedVinPoint]:
    # This function converts the raw JSON list of fixed test points into typed Python objects; it exits the program if the list is empty or missing
    """Build the fixed Vin test point list from the JSON config."""
    # Extract the "fixed_vin_tests" list from the config dictionary; return an empty list if the key is absent
    raw = cfg.get("fixed_vin_tests", [])
    # Check if the list is empty or missing; this section is mandatory so exit with an error if not found
    if not raw:
        # Print an error message explaining which key is missing from the config file
        print("ERROR: 'fixed_vin_tests' section missing from input_range_ovp_config.json")
        # Exit the program immediately since the test cannot run without test point definitions
        sys.exit(1)
    # For multi-rail configs (output_rails present) expected_vout_v is supplied per-rail, not per test point.
    is_multi_rail = bool(cfg.get("output_rails"))
    # Build and return a list of FixedVinPoint objects by looping through each entry in the raw JSON list
    return [
        # Create a FixedVinPoint object for each valid entry (entries without a 'vin_v' key are skipped as they are comment-only)
        FixedVinPoint(
            # Set the input voltage from the JSON entry
            vin_v=pt["vin_v"],
            # For multi-rail configs expected_vout_v is overridden per-rail; use 0.0 as a placeholder here
            expected_vout_v=pt.get("expected_vout_v", 0.0),
            # Set the tolerance from the JSON entry; default to 0.1 V if not specified
            vout_tolerance_v=pt.get("vout_tolerance_v", 0.1),
        )
        # Iterate over each raw entry in the list
        for pt in raw
        # Only include entries that have a 'vin_v' key — entries without one are treated as JSON comments
        if "vin_v" in pt   # skip comment-only entries that lack a vin_v key
    ]

# [Blank line for visual separation]

# Define a helper that reads the output_rails list from config for multi-rail (SENSOR) testing.
# Returns None for single-rail configs (e.g. CPU) so existing code paths are unchanged.
def _build_output_rails(cfg: dict):
    """Return list of rail dicts if output_rails is in config, else None."""
    raw = cfg.get("output_rails")
    if not raw:
        return None
    return [r for r in raw if "name" in r]   # skip comment-only entries


# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST CLASS
# ═════════════════════════════════════════════════════════════════════════════

# Define the main test class that encapsulates all logic for the Input Range and OVP test sequence
class InputRangeOVPTest:
    # This class connects to the power supply and digital multimeter, runs both test phases, generates graphs and reports, and returns an overall PASS/FAIL result
    """
    Runs the Input Range and OVP test sequence.

    All configuration is read from input_range_ovp_config.json via _CFG.

    Output directory structure (mirrors Load Transient convention):

        <output_dir>/run_YYYYMMDD_HHMMSS/
            input_range_ovp_test.log
            reports/
                input_range_ovp_results_TIMESTAMP.csv
                input_range_ovp_results_TIMESTAMP.json
                input_range_ovp_summary_TIMESTAMP.txt
            plots/
                psu_sweep_TIMESTAMP.png
                dmm_sweep_TIMESTAMP.png

    Usage:
        test   = InputRangeOVPTest()
        passed = test.run()
    """

    # Class-level attributes loaded from JSON — available before instantiation
    # (used by the runner to display config without constructing the test object)
    # Build the fixed-Vin test point list at class definition time from the global config so it is available immediately without creating a test object
    FIXED_VIN_TESTS = _build_fixed_vin_tests(_CFG)
    # For multi-rail configs (e.g. SENSOR board) this holds the ordered list of rail dicts; None for single-rail (CPU)
    OUTPUT_RAILS = _build_output_rails(_CFG)

    # Define the constructor that reads all settings from the global config, sets up the output folder structure, and configures the logger
    def __init__(self, output_dir: str = None):
        # Record the exact date and time when this test object was created, used for timestamping all output files
        self._test_start_time = datetime.datetime.now()
        # Initialise the end-time variable to None; it will be set when the test finishes
        self._test_end_time: Optional[datetime.datetime] = None

        # ── Read sections from _CFG ───────────────────────────────────────────
        # Extract the instrument addresses section from the config dictionary
        instr    = _CFG.get("instrument_addresses", {})
        # Extract the instrument settings section from the config dictionary
        settings = _CFG.get("instrument_settings", {})
        # Extract the test parameters section from the config dictionary
        p        = _CFG.get("test_parameters", {})

        # ── VISA auto-detection ───────────────────────────────────────────────
        # Try to auto-detect the PSU and DMM on the VISA bus first.
        # If detection succeeds the discovered address is used; if it fails
        # (no instrument found or pyvisa not available) we fall back to the
        # address hardcoded in the config file.
        _detected_psu_addr: Optional[str] = None
        _detected_dmm_addr: Optional[str] = None
        try:
            from visa_auto_detect import detect_input_range_ovp_instruments
            print("\nAuto-detecting instruments on VISA bus...")
            _detected_psu_addr, _detected_dmm_addr = detect_input_range_ovp_instruments()
        except ImportError:
            pass  # visa_auto_detect not available — use config addresses

        # Use detected address when available, otherwise fall back to config
        self._psu_address = _detected_psu_addr if _detected_psu_addr else instr.get("psu")
        self._dmm_address = _detected_dmm_addr if _detected_dmm_addr else instr.get("dmm")
        # Read the power supply channel number from the config; default to channel 1 if not specified
        self._psu_channel       = settings.get("psu_channel", 1)
        # Read the communication timeout for the power supply in milliseconds; default to 10 seconds
        self._psu_timeout_ms    = settings.get("psu_timeout_ms", 10000)
        # Read the communication timeout for the DMM in milliseconds; default to 30 seconds
        self._dmm_timeout_ms    = settings.get("dmm_timeout_ms", 30000)

        # Read the maximum current the power supply is allowed to deliver, in amps
        self._psu_current_limit_a    = p["psu_current_limit_a"]
        # Read the over-voltage protection level in volts — the PSU will cut output if this is exceeded
        self._psu_ovp_level_v        = p["psu_ovp_level_v"]
        # Read the number of seconds to wait after setting a new fixed input voltage before taking a reading
        self._fixed_vin_settle_s     = p["fixed_vin_settle_time_s"]
        # Read the starting voltage (in volts) for the sweep test
        self._sweep_start_v          = p["sweep_start_v"]
        # Read the maximum voltage (in volts) that the sweep will ramp up to
        self._sweep_max_v            = p["sweep_max_v"]
        # Read the step size (in volts) between each voltage level during the sweep
        self._sweep_step_v           = p["sweep_step_v"]
        # Read the time (in seconds) to hold at each voltage step before moving to the next
        self._step_dwell_s           = p["step_dwell_time_s"]
        # Read the time interval (in seconds) between consecutive DMM readings during the sweep
        self._dmm_read_interval_s    = p["dmm_read_interval_s"]
        # Read the time (in seconds) to wait after changing voltage before measuring, to allow the output to settle
        self._step_settle_s          = p["step_settle_time_s"]
        # Read the minimum input voltage (in volts) at which the DUT is expected to be operating; samples below this are excluded from the pass/fail calculation
        self._sweep_vin_min_op_v     = p["sweep_vin_min_operating_v"]
        # Read the expected output voltage (in volts) that the DUT should maintain during the sweep
        self._sweep_expected_vout_v  = p["sweep_expected_vout_v"]
        # Read the allowed tolerance (in volts) around the expected sweep output voltage for the pass/fail check
        self._sweep_vout_tolerance_v = p["sweep_vout_tolerance_v"]
        # Read the NPLC (Number of Power Line Cycles) setting for the DMM; higher values give more accurate but slower readings
        self._dmm_nplc               = p["dmm_nplc"]

        # ── Resolve output directory ──────────────────────────────────────────
        # Check if an output directory was provided; if not, read the default from the config file
        if output_dir is None:
            # Read the output directory section from the config
            out_cfg = _CFG.get("output_dir", {})
            # Extract the path string, handling both dictionary-style and string-style config values
            output_dir = (
                # If the config value is a dictionary, read its 'path' key; otherwise use a default name
                out_cfg.get("path", "input_range_ovp_results")
                if isinstance(out_cfg, dict)
                else str(out_cfg)
            )

        # Format the current date and time as a compact string like "20250415_143022" for use in folder and file names
        timestamp = self._test_start_time.strftime("%Y%m%d_%H%M%S")
        # Store the timestamp string as an instance variable for use by report and plot generation methods
        self._timestamp = timestamp

        # Build the path to the timestamped run folder where all results for this test run will be saved
        self._run_dir    = Path(output_dir) / f"run_{timestamp}"
        # Build the path to the reports subfolder inside the run folder
        self._reports_dir = self._run_dir / "reports"
        # Build the path to the plots subfolder inside the run folder
        self._plots_dir   = self._run_dir / "plots"

        # Attempt to create all three output directories; if any creation fails, fall back to a local folder next to this script
        try:
            # Loop through each of the three directory paths
            for d in [self._run_dir, self._reports_dir, self._plots_dir]:
                # Create the directory, also creating any missing parent directories; do nothing if it already exists
                d.mkdir(parents=True, exist_ok=True)
        # If the folder cannot be created due to a permissions problem or OS error, use a fallback location
        except (PermissionError, OSError) as e:
            # Build the fallback path in the same folder as this script file
            fallback = Path(__file__).resolve().parent / "input_range_ovp_results"
            # Rebuild the run directory path using the fallback location
            self._run_dir     = fallback / f"run_{timestamp}"
            # Rebuild the reports path using the fallback location
            self._reports_dir = self._run_dir / "reports"
            # Rebuild the plots path using the fallback location
            self._plots_dir   = self._run_dir / "plots"
            # Create all three fallback directories
            for d in [self._run_dir, self._reports_dir, self._plots_dir]:
                # Create each fallback directory, creating parent directories as needed
                d.mkdir(parents=True, exist_ok=True)
            # Warn the engineer that the original output path failed and a fallback is being used
            print(f"  WARNING: Could not write to '{output_dir}' ({e}). Falling back to: {fallback}")

        # ── Logging ───────────────────────────────────────────────────────────
        # Create (or retrieve an existing) named logger for this test class
        self._logger = logging.getLogger(self.__class__.__name__)
        # Build the full path for the log file inside the run directory
        log_path = self._run_dir / "input_range_ovp_test.log"
        # Only attach a new file handler if the logger does not already have one (prevents duplicate log entries if this class is instantiated more than once)
        if not self._logger.handlers:
            # Create a file handler that will write log messages to the log file using UTF-8 encoding
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            # Set the log message format to include timestamp, log level, logger name, and the message
            fh.setFormatter(logging.Formatter(
                '%(asctime)s  %(levelname)-8s  %(name)s: %(message)s',
                datefmt='%H:%M:%S'
            ))
            # Attach the file handler to the logger so messages are written to the log file
            self._logger.addHandler(fh)
            # Set the minimum severity level to DEBUG so that all messages (debug, info, warning, error) are recorded
            self._logger.setLevel(logging.DEBUG)
        # Write the run directory path to the log as the first entry for traceability
        self._logger.info(f"Run directory: {self._run_dir}")

        # ── Instrument handles ────────────────────────────────────────────────
        # Initialise the power supply handle to None; it will be set when _connect_instruments() is called
        self._psu: Optional[KeithleyPowerSupply] = None
        # Initialise the DMM handle to None; it will be set when _connect_instruments() is called
        self._dmm: Optional[KeithleyDMM6500] = None

    # ─────────────────────────────────────────────────────────────
    # Instrument helpers
    # ─────────────────────────────────────────────────────────────

    # Define the method that establishes USB connections to both instruments and configures the power supply channel
    def _connect_instruments(self) -> bool:
        # Print a status message to inform the engineer that instrument connection is starting
        print("\n  Connecting instruments...")

        # Create the power supply connection object and attempt to connect to it using the configured address and timeout
        self._psu = KeithleyPowerSupply(self._psu_address, timeout_ms=self._psu_timeout_ms)
        # Attempt to open the USB connection to the power supply; if it fails, report the error and return False
        if not self._psu.connect():
            # Print an error message showing which address the connection attempt was made to
            print(f"  ERROR: Failed to connect to PSU at {self._psu_address}")
            # Return False to signal that instrument connection failed and the test cannot proceed
            return False
        # Print a confirmation message showing the power supply model that was identified
        print(f"  PSU connected  — model: {self._psu.model}")

        # Create the DMM connection object and attempt to connect to it using the configured address and timeout
        self._dmm = KeithleyDMM6500(self._dmm_address, timeout_ms=self._dmm_timeout_ms)
        # Attempt to open the USB connection to the DMM; if it fails, report the error and return False
        if not self._dmm.connect():
            # Print an error message showing which address the connection attempt was made to
            print(f"  ERROR: Failed to connect to DMM at {self._dmm_address}")
            # Return False to signal that instrument connection failed
            return False
        # Print a confirmation message that the DMM is connected
        print("  DMM connected")

        # Configure the power supply channel with zero volts, the current limit, and OVP level, with output disabled for safety
        ok = self._psu.configure_channel(
            # Specify which channel on the power supply to configure
            channel=self._psu_channel,
            # Start with zero volts — the output will ramp up later during the test
            voltage=0.0,
            # Apply the current limit from the config to protect the DUT
            current_limit=self._psu_current_limit_a,
            # Apply the OVP level from the config so the supply cuts off if voltage exceeds the limit
            ovp_level=self._psu_ovp_level_v,
            # Leave the output disabled so no voltage is applied until the test explicitly enables it
            enable_output=False
        )
        # Check if the channel configuration succeeded
        if not ok:
            # Print an error message if the PSU refused to accept the configuration
            print("  ERROR: PSU channel configuration failed")
            # Return False to signal that instrument setup failed
            return False

        # Print a confirmation showing the channel configuration that was applied
        print(f"  PSU CH{self._psu_channel} configured: 0 V / {self._psu_current_limit_a} A / OVP {self._psu_ovp_level_v} V")
        # Return True to signal that both instruments are connected and configured successfully
        return True

    # Define the method that safely disconnects both instruments, turning off the power supply output before closing the connection
    def _disconnect_instruments(self):
        # Attempt to safely turn off the power supply and close its connection
        try:
            # Check that the power supply handle exists and the connection is still open
            if self._psu and self._psu.is_connected:
                # Turn off all power supply outputs to ensure no voltage is applied to the DUT after the test
                self._psu.disable_all_outputs()
                # Close the USB connection to the power supply
                self._psu.disconnect()
        # If any error occurs during PSU disconnection, log it but continue to try to disconnect the DMM
        except Exception as e:
            # Write a warning to the log file describing the disconnection error
            self._logger.warning(f"PSU disconnect error: {e}")
        # Attempt to close the DMM connection
        try:
            # Check that the DMM handle exists and the connection is marked as open
            if self._dmm and self._dmm._is_connected:
                # Close the USB connection to the DMM
                self._dmm.disconnect()
        # If any error occurs during DMM disconnection, log it
        except Exception as e:
            # Write a warning to the log file describing the DMM disconnection error
            self._logger.warning(f"DMM disconnect error: {e}")

    # Define a convenience method that sets the power supply output voltage on the configured channel
    def _psu_set_v(self, voltage: float):
        # Send the voltage set command to the power supply for the configured channel
        self._psu.set_voltage(self._psu_channel, voltage)

    # Define a convenience method that reads both voltage and current from the power supply and returns them as a pair
    def _psu_measure(self) -> Tuple[float, float]:
        # Ask the power supply to measure the actual output voltage on the configured channel
        v = self._psu.measure_voltage(self._psu_channel)
        # Ask the power supply to measure the actual output current on the configured channel
        i = self._psu.measure_current(self._psu_channel)
        # Return the voltage and current as a pair; substitute 0.0 if either measurement returned None
        return (v or 0.0), (i or 0.0)

    # Define a convenience method that performs a fast DC voltage measurement using the DMM and returns the result
    def _dmm_read_fast(self) -> float:
        # Ask the DMM to take a fast DC voltage measurement
        val = self._dmm.measure_dc_voltage_fast()
        # Return the measured value, or 0.0 if the DMM returned None (indicating a measurement failure)
        return val if val is not None else 0.0

    # ─────────────────────────────────────────────────────────────
    # Operator prompt
    # ─────────────────────────────────────────────────────────────

    # Define the method that pauses the test and asks the engineer to connect the DMM probes to the DUT output before measurements begin
    def _prompt_probe_setup(self):
        # Print a blank line for visual spacing before the prompt
        print()
        # Print the top border of the prompt box using equals signs
        print("  " + "=" * 58)
        # Print the prompt heading to draw the engineer's attention
        print("  PROBE SETUP — ACTION REQUIRED")
        # Print the bottom border of the heading
        print("  " + "=" * 58)
        # Print a blank line for spacing
        print()
        # Print the instruction to connect the DMM probes to the DUT output terminals
        print("  Connect DMM probes to the DUT OUTPUT:")
        # Print the instruction for the positive (HI) lead connection
        print("    + (HI) lead  ->  VOUT positive terminal")
        # Print the instruction for the negative (LO) lead connection
        print("    - (LO) lead  ->  GND / VOUT return")
        # Print a blank line for spacing
        print()
        # Remind the engineer that the PSU leads should already be connected to the input
        print("  PSU leads should already be on DUT INPUT (VIN).")
        # Print a blank line for spacing
        print()
        # Block and wait for the engineer to press Enter, confirming the probes are connected
        input("  Press ENTER when probes are connected and ready... ")
        # Print a blank line after the prompt for visual separation
        print()

    # ─────────────────────────────────────────────────────────────
    # Phase 1 — Fixed Vin tests
    # ─────────────────────────────────────────────────────────────

    # Define the method that runs Phase 1: applies each configured fixed input voltage and checks that the DUT output voltage is within tolerance
    def run_fixed_vin_tests(self) -> List[FixedVinResult]:
        # Initialise an empty list to collect the result of each fixed-voltage test point
        results: List[FixedVinResult] = []

        # Print a blank line for visual spacing
        print()
        # Print the phase heading separator
        print("  -- Phase 1: Fixed Vin Tests ----------------------------------------")
        # Print the column headers for the results table, with fixed-width columns
        print(f"  {'VIN (V)':<12} {'VOUT (V)':<14} {'EXPECTED (V)':<16} {'STATUS'}")
        # Print a separator line under the column headers
        print("  " + "-" * 54)

        # Set the power supply to 0 V before enabling the output, to avoid a sudden voltage spike
        self._psu_set_v(0.0)
        # Enable the power supply output so it begins delivering voltage to the DUT
        self._psu.enable_channel_output(self._psu_channel)
        # Wait half a second for the output to stabilise before setting the first test voltage
        time.sleep(0.5)

        # Loop through each fixed-voltage test point defined in the configuration
        for point in self.FIXED_VIN_TESTS:
            # Begin a try block so that a failure at one test point is recorded as ERROR rather than crashing the test
            try:
                # Print the current action (setting the voltage) without a newline so the result can overwrite it
                print(f"  Setting Vin = {point.vin_v:.1f} V ...", end='', flush=True)
                # Set the power supply voltage to the value specified for this test point
                self._psu_set_v(point.vin_v)
                # Wait for the configured settle time to allow the DUT output to stabilise at the new input voltage
                time.sleep(self._fixed_vin_settle_s)

                # Take a fast DC voltage measurement from the DMM at the DUT output
                vout = self._dmm_read_fast()
                # Calculate how far the measured voltage deviates from the expected value
                deviation = abs(vout - point.expected_vout_v)
                # Decide PASS or FAIL: use whichever tolerance is larger — the configured value or 5% of expected
                _eff_tol = max(point.vout_tolerance_v, point.expected_vout_v * 0.05)
                status = "PASS" if deviation <= _eff_tol else "FAIL"

                # Append a result record for this test point to the results list
                results.append(FixedVinResult(
                    # Store the input voltage that was applied
                    vin_v=point.vin_v, vout_v=vout,
                    # Store the expected output voltage
                    expected_vout_v=point.expected_vout_v,
                    # Store the tolerance window
                    vout_tolerance_v=point.vout_tolerance_v,
                    # Store the PASS or FAIL verdict
                    status=status
                ))
                # Overwrite the "Setting..." line with the actual measured values and status in a formatted table row
                print(f"\r  {point.vin_v:<12.1f} {vout:<14.4f} {point.expected_vout_v:<16.1f} {status}")

            # If any error occurs during this test point (e.g. instrument communication failure), record it as ERROR
            except Exception as e:
                # Write the error details to the log file for diagnostic purposes
                self._logger.error(f"Fixed Vin test error at {point.vin_v} V: {e}")
                # Append an ERROR result with None for the measured voltage since measurement failed
                results.append(FixedVinResult(
                    # Store the input voltage that was being tested
                    vin_v=point.vin_v, vout_v=None,
                    # Store the expected voltage for reference
                    expected_vout_v=point.expected_vout_v,
                    # Store the tolerance for reference
                    vout_tolerance_v=point.vout_tolerance_v,
                    # Mark the status as ERROR
                    status="ERROR"
                ))
                # Print the error row in the table, showing "N/A" for the measured value
                print(f"\r  {point.vin_v:<12.1f} {'N/A':<14} {point.expected_vout_v:<16.1f} ERROR")

        # Set the power supply back to 0 V after all test points are complete, for safety
        self._psu_set_v(0.0)
        # Wait half a second before disabling the output
        time.sleep(0.5)
        # Turn off the power supply output
        self._psu.disable_channel_output(self._psu_channel)
        # Print a closing separator line under the results table
        print("  " + "-" * 54)
        # Print a blank line after the table
        print()
        # Return the list of all fixed-voltage test results to the caller
        return results

    # ─────────────────────────────────────────────────────────────
    # Phase 2 — Sweep test
    # ─────────────────────────────────────────────────────────────

    # Define the helper method that builds the list of voltage setpoints for the sweep (ramp up then ramp back down)
    def _build_sweep_setpoints(self) -> List[float]:
        # Create an empty list that will hold all the voltage values for the upward ramp
        setpoints_up: List[float] = []
        # Start from the configured sweep start voltage
        v = self._sweep_start_v
        # Loop, adding one step at a time, until the max voltage is reached (with a tiny epsilon to handle floating-point rounding)
        while v <= self._sweep_max_v + 1e-9:
            # Append the current voltage rounded to 6 decimal places to avoid floating-point noise
            setpoints_up.append(round(v, 6))
            # Increment the voltage by the configured step size
            v += self._sweep_step_v
        # If the last value in the upward list is less than the max voltage, add the max voltage explicitly
        if setpoints_up[-1] < self._sweep_max_v:
            # Append the exact max voltage as the final upward step
            setpoints_up.append(round(self._sweep_max_v, 6))
        # Build the downward ramp by reversing the upward list but excluding the peak value (which is already at the end of the up ramp)
        setpoints_down = list(reversed(setpoints_up[:-1]))
        # Concatenate the upward and downward ramps to form the full sweep profile
        return setpoints_up + setpoints_down

    # Define the method that executes Phase 2: ramps the input voltage from 0 to max and back, continuously logging DMM and PSU readings
    def run_sweep_test(self) -> SweepResult:
        # Generate the complete list of voltage setpoints for the sweep
        setpoints = self._build_sweep_setpoints()
        # Count the total number of steps in the sweep
        total_steps = len(setpoints)

        # Print a blank line for visual spacing
        print()
        # Print the phase heading separator
        print("  -- Phase 2: Vin Sweep ----------------------------------------------")
        # Print the sweep voltage range in a readable format
        print(f"  {self._sweep_start_v:.0f} V  ->  {self._sweep_max_v:.0f} V  ->  {self._sweep_start_v:.0f} V")
        # Print the step size, dwell time, and DMM reading interval for this sweep
        print(f"  Step: {self._sweep_step_v:.1f} V  |  Dwell: {self._step_dwell_s:.1f} s  |  DMM interval: {self._dmm_read_interval_s:.2f} s")
        # Print the total number of voltage steps in the sweep
        print(f"  Total steps: {total_steps}")
        # Print a blank line for spacing
        print()

        # Initialise an empty list to store each data sample collected during the sweep
        samples: List[SweepSample] = []
        # Record the monotonic time at the start of the sweep, used to compute elapsed time for each sample
        sweep_start = time.monotonic()

        # Set the power supply to 0 V before enabling, to avoid applying a sudden voltage to the DUT
        self._psu_set_v(0.0)
        # Enable the power supply output so it can begin ramping
        self._psu.enable_channel_output(self._psu_channel)
        # Wait half a second for the output to stabilise at 0 V before starting the ramp
        time.sleep(0.5)

        # Loop through each voltage setpoint in the sweep profile
        for idx, setpoint in enumerate(setpoints):
            # Command the power supply to output the next setpoint voltage
            self._psu_set_v(setpoint)
            # Wait the configured settle time to allow the DUT output to stabilise before measuring
            time.sleep(self._step_settle_s)
            # Measure the actual PSU output voltage and current at this step
            psu_v, psu_i = self._psu_measure()

            # Calculate the time at which the dwell period for this step ends
            dwell_end = time.monotonic() + self._step_dwell_s
            # Keep taking DMM readings until the dwell period expires
            while time.monotonic() < dwell_end:
                # Calculate how many seconds have elapsed since the sweep started
                elapsed = time.monotonic() - sweep_start
                # Record the current wall-clock time for the timestamp field in this sample
                rt = datetime.datetime.now()
                # Take a fast DC voltage reading from the DMM at the DUT output
                dmm_v = self._dmm_read_fast()
                # Append this data sample to the samples list
                samples.append(SweepSample(
                    # Store elapsed time since sweep start
                    elapsed_s=elapsed, real_time=rt,
                    # Store the commanded voltage for this step
                    psu_setpoint_v=setpoint, psu_measured_v=psu_v,
                    # Store the measured PSU current and the DMM output voltage
                    psu_current_a=psu_i, dmm_v=dmm_v
                ))
                # Print the current status line showing step number, set voltage, measured PSU voltage, and DMM output; '\r' overwrites the same line each iteration
                print(
                    f"\r  [{idx+1:>3}/{total_steps}] "
                    f"Vin set={setpoint:.1f}V  "
                    f"Vin meas={psu_v:.2f}V  "
                    f"Vout={dmm_v:.4f}V  ",
                    # Use end='' so the cursor stays on the same line
                    end='', flush=True
                )
                # Wait the configured DMM read interval before taking the next sample
                time.sleep(self._dmm_read_interval_s)

        # Print a newline after the status line loop ends so subsequent output starts on a new line
        print()

        # Set the power supply back to 0 V after the sweep is complete
        self._psu_set_v(0.0)
        # Wait half a second before disabling the output
        time.sleep(0.5)
        # Turn off the power supply output
        self._psu.disable_channel_output(self._psu_channel)

        # Filter the samples to only include those where the input voltage was within the operating range
        op_samples = [s for s in samples if s.psu_setpoint_v >= self._sweep_vin_min_op_v]
        # Analyse the operating-range samples if any exist
        if op_samples:
            # Extract the list of DMM output voltages from the operating-range samples
            vout_vals = [s.dmm_v for s in op_samples]
            # Calculate the average output voltage across all operating-range samples
            avg_vout  = sum(vout_vals) / len(vout_vals)
            # Check whether every output voltage reading was within the specified tolerance of the expected value
            # Use whichever tolerance is larger — the configured value or 5% of the expected voltage
            _sweep_eff_tol = max(self._sweep_vout_tolerance_v, self._sweep_expected_vout_v * 0.05)
            in_spec   = all(abs(v - self._sweep_expected_vout_v) <= _sweep_eff_tol for v in vout_vals)
            # Set status to PASS if all readings were in spec, FAIL otherwise
            status    = "PASS" if in_spec else "FAIL"
        # If no samples fell within the operating voltage range, report an error
        else:
            # Set average voltage to 0 and status to ERROR since no usable data was collected
            avg_vout, status = 0.0, "ERROR"

        # Build a human-readable string describing the input voltage range that was swept
        vin_range = f"{int(self._sweep_start_v)} - {int(self._sweep_max_v)}V"
        # Print the sweep summary showing the voltage range, average output, and pass/fail status
        print(f"  Sweep: VIN={vin_range}  Vout_avg={avg_vout:.4f}V  {status}")

        # Return a SweepResult object containing the summary of the sweep test
        return SweepResult(
            # Store the input voltage range description
            vin_range=vin_range,
            # Store the average output voltage rounded to 4 decimal places
            vout_v=round(avg_vout, 4),
            # Store the expected output voltage for comparison in reports
            expected_vout_v=self._sweep_expected_vout_v,
            # Store the pass/fail/error status
            status=status,
            # Store all collected data samples for graph generation
            samples=samples
        )

    # ─────────────────────────────────────────────────────────────
    # Plotting  (saved to plots/ subdirectory)
    # ─────────────────────────────────────────────────────────────

    # Define the method that generates and saves two graphs from the sweep data: one for PSU voltage and current, one for DMM output voltage
    def _plot_sweep(self, sweep: SweepResult):
        # Check if matplotlib is available; if not, skip graph generation with a warning
        if not _MATPLOTLIB_AVAILABLE:
            # Inform the engineer that graphs cannot be generated because matplotlib is not installed
            print("  WARNING: matplotlib not installed — skipping plots")
            # Exit the method early since there is nothing to plot
            return
        # Check if any samples were collected; skip plotting if the sweep produced no data
        if not sweep.samples:
            # Exit the method early — no data means no graphs
            return

        samp       = sweep.samples
        times      = [s.elapsed_s      for s in samp]
        setpoints  = [s.psu_setpoint_v for s in samp]
        psu_v      = [s.psu_measured_v for s in samp]
        psu_i      = [s.psu_current_a  for s in samp]
        dmm_v      = [s.dmm_v          for s in samp]
        real_times = [s.real_time      for s in samp]

        sweep_title = f"{int(self._sweep_start_v)}-{int(self._sweep_max_v)}V Vin"

        # Digantara dark theme
        _BG      = "#0a0f1e"
        _PANEL   = "#0c1220"
        _GRID    = "#1a2540"
        _TEXT    = "#8892a4"
        _BLUE    = "#2563eb"
        _CYAN    = "#4fc3f7"

        plt.rcParams.update({
            "figure.facecolor":  _BG,
            "axes.facecolor":    _PANEL,
            "axes.edgecolor":    _GRID,
            "axes.labelcolor":   _TEXT,
            "axes.titlecolor":   "#c8d6ea",
            "axes.titlesize":    10,
            "axes.labelsize":    9,
            "axes.grid":         True,
            "grid.color":        _GRID,
            "grid.alpha":        0.6,
            "grid.linestyle":    "--",
            "xtick.color":       _TEXT,
            "ytick.color":       _TEXT,
            "xtick.labelsize":   8,
            "ytick.labelsize":   8,
            "legend.facecolor":  _PANEL,
            "legend.edgecolor":  _GRID,
            "legend.labelcolor": _TEXT,
            "legend.fontsize":   8,
            "text.color":        _TEXT,
            "savefig.facecolor": _BG,
        })

        def _watermark(fig):
            fig.text(0.99, 0.01, "Digantara Research & Technologies",
                     ha='right', va='bottom', fontsize=6.5,
                     color="#1e2d47", style='italic', transform=fig.transFigure)
            fig.text(0.01, 0.01, f"Run: {self._timestamp}",
                     ha='left', va='bottom', fontsize=6.5,
                     color="#1e2d47", transform=fig.transFigure)

        fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor=_BG)
        fig1.suptitle(sweep_title, fontweight='bold', color="#c8d6ea", fontsize=11)
        ax1.plot(times, setpoints, '--', color=_CYAN, linewidth=1.2, label='Setpoint', alpha=0.7)
        ax1.plot(times, psu_v,     '-',  color=_BLUE, linewidth=1.8, label='Measured')
        ax1.set_xlabel("Time (s)"); ax1.set_ylabel("Voltage (V)")
        ax1.set_title("CH1 Voltage — Live Execution Data")
        ax1.legend(); ax1.set_ylim(bottom=-0.5)
        ax2.plot(times, psu_i, '-', color=_BLUE, linewidth=1.8)
        ax2.set_xlabel("Time (s)"); ax2.set_ylabel("Current (A)")
        ax2.set_title("CH1 Current — Live Execution Data")
        ax2.set_ylim(bottom=0)
        _watermark(fig1)
        plt.tight_layout()
        p1 = self._plots_dir / f"psu_sweep_{self._timestamp}.png"
        fig1.savefig(str(p1), dpi=1200, bbox_inches='tight', facecolor=_BG)
        plt.close(fig1)
        print(f"  Saved: plots/{p1.name}")

        fig2, ax3 = plt.subplots(figsize=(10, 5), facecolor=_BG)
        fig2.suptitle(sweep_title, fontweight='bold', color="#c8d6ea", fontsize=11)
        ax3.plot_date(real_times, dmm_v, '-', color=_BLUE, linewidth=1.8, xdate=True)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        fig2.autofmt_xdate()
        ax3.set_xlabel("Time"); ax3.set_ylabel("Measurement Value (V)")
        ax3.set_title(f"DMM Output — {sweep_title}")
        ax3.set_ylim(bottom=-0.05)
        _watermark(fig2)
        plt.tight_layout()
        p2 = self._plots_dir / f"dmm_sweep_{self._timestamp}.png"
        fig2.savefig(str(p2), dpi=1200, bbox_inches='tight', facecolor=_BG)
        plt.close(fig2)
        print(f"  Saved: plots/{p2.name}")

    # ─────────────────────────────────────────────────────────────
    # Report generation  (CSV + JSON + TXT in reports/ subdir)
    # ─────────────────────────────────────────────────────────────

    # Define the method that writes all three report files (CSV, JSON, and plain-text summary) and returns the overall PASS/FAIL verdict
    def _generate_reports(self, fixed: List[FixedVinResult], sweep: SweepResult) -> str:
        """
        Generate three report files in reports/:
          - input_range_ovp_results_TIMESTAMP.csv
          - input_range_ovp_results_TIMESTAMP.json
          - input_range_ovp_summary_TIMESTAMP.txt
        Returns the overall verdict string ("PASS" / "FAIL").
        """
        # Record the time when report generation started, which serves as the official test end time
        self._test_end_time = datetime.datetime.now()
        # Store the timestamp string in a local variable for convenient use when naming files
        ts = self._timestamp

        # Compute the overall verdict: PASS only if every fixed-Vin result passed AND the sweep passed
        all_pass = (
            # Check that every fixed-Vin result has a status of "PASS"
            all(r.status == "PASS" for r in fixed)
            # AND the sweep result also has a status of "PASS"
            and sweep.status == "PASS"
        )
        # Set the overall verdict string to "PASS" or "FAIL"
        verdict = "PASS" if all_pass else "FAIL"

        # ── CSV ───────────────────────────────────────────────────────────────
        # Build the file path for the CSV report
        csv_path = self._reports_dir / f"input_range_ovp_results_{ts}.csv"
        # Open the CSV file for writing with no extra blank lines (newline='') and UTF-8 encoding
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            # Create a CSV writer object that will format rows as comma-separated text
            w = csv.writer(f)
            # Write the header row with column names
            w.writerow(['Phase', 'Vin_V', 'Vout_V', 'Expected_V', 'Tolerance_V', 'Status'])
            # Write one row per fixed-Vin result
            for r in fixed:
                # Format the measured output voltage to 4 decimal places, or "N/A" if measurement failed
                vout_str = f"{r.vout_v:.4f}" if r.vout_v is not None else "N/A"
                # Write the fixed-Vin result row
                w.writerow(['FIXED', r.vin_v, vout_str, r.expected_vout_v, r.vout_tolerance_v, r.status])
            # Write the sweep result as a single summary row
            w.writerow(['SWEEP', sweep.vin_range, f"{sweep.vout_v:.4f}",
                        sweep.expected_vout_v, self._sweep_vout_tolerance_v, sweep.status])
        # Write a log entry confirming the CSV file was saved
        self._logger.info(f"CSV report saved: {csv_path}")
        # Print a confirmation to the terminal
        print(f"  Saved: reports/{csv_path.name}")

        # ── JSON ──────────────────────────────────────────────────────────────
        # Build the file path for the JSON report
        json_path = self._reports_dir / f"input_range_ovp_results_{ts}.json"
        # Calculate the total test duration in seconds
        duration = (self._test_end_time - self._test_start_time).total_seconds()
        # Build the full report data dictionary
        report_data = {
            # Include test metadata in the 'test_info' section
            'test_info': {
                # Include the name of this test for identification
                'test_name': 'Input Range and OVP Test',
                # Include the test start time in ISO 8601 format
                'start_time': self._test_start_time.isoformat(),
                # Include the test end time in ISO 8601 format
                'end_time': self._test_end_time.isoformat(),
                # Include the total duration rounded to 1 decimal place
                'duration_seconds': round(duration, 1),
                # Include the VISA address of the power supply used
                'psu_address': self._psu_address,
                # Include the VISA address of the DMM used
                'dmm_address': self._dmm_address,
                # Include the power supply channel number used
                'psu_channel': self._psu_channel,
                # Include the current limit that was applied
                'current_limit_a': self._psu_current_limit_a,
                # Include the OVP level that was set
                'ovp_level_v': self._psu_ovp_level_v,
            },
            # Include the list of fixed-Vin results, each converted to a dictionary
            'fixed_vin_results': [r.to_dict() for r in fixed],
            # Include the sweep result converted to a dictionary
            'sweep_result': sweep.to_dict(),
            # Include the overall pass/fail verdict
            'overall_result': verdict,
        }
        # Open the JSON report file for writing with UTF-8 encoding
        with open(json_path, 'w', encoding='utf-8') as f:
            # Write the report data dictionary to the file with 2-space indentation for readability
            json.dump(report_data, f, indent=2)
        # Write a log entry confirming the JSON file was saved
        self._logger.info(f"JSON report saved: {json_path}")
        # Print a confirmation to the terminal
        print(f"  Saved: reports/{json_path.name}")

        # ── TXT summary ───────────────────────────────────────────────────────
        # Build the file path for the plain-text summary report
        txt_path = self._reports_dir / f"input_range_ovp_summary_{ts}.txt"
        # Open the text summary file for writing
        with open(txt_path, 'w', encoding='utf-8') as f:
            # Create a shorthand alias '_w' for the file's write method to keep the following lines concise
            _w = f.write
            # Write the top border of the summary
            _w("=" * 65 + "\n")
            # Write the report title
            _w("  INPUT RANGE AND OVP TEST — RESULTS SUMMARY\n")
            # Write the border below the title
            _w("=" * 65 + "\n")
            # Write the test date and time
            _w(f"  Date / Time    : {self._test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            # Write the power supply VISA address
            _w(f"  PSU Address    : {self._psu_address}\n")
            # Write the DMM VISA address
            _w(f"  DMM Address    : {self._dmm_address}\n")
            # Write the channel number that was used
            _w(f"  PSU Channel    : CH{self._psu_channel}\n")
            # Write the current limit that was applied
            _w(f"  Current Limit  : {self._psu_current_limit_a:.2f} A\n")
            # Write the OVP level that was set
            _w(f"  OVP Level      : {self._psu_ovp_level_v:.1f} V\n")
            # Write a separator before the results table
            _w("=" * 65 + "\n\n")

            # Write the results section heading
            _w("  Results\n")
            # Write a separator under the heading
            _w("  " + "-" * 60 + "\n")
            # Write the column headers for the results table
            _w(f"  {'PHASE':<10} {'VIN (V)':<14} {'VOUT (V)':<14} {'EXPECTED (V)':<16} {'STATUS'}\n")
            # Write a separator under the column headers
            _w("  " + "-" * 60 + "\n")
            # Write one row per fixed-Vin result
            for r in fixed:
                # Format the measured output voltage to 4 decimal places, or "N/A" if measurement failed
                vout_str = f"{r.vout_v:.4f}" if r.vout_v is not None else "N/A"
                # Write the fixed-Vin result row with aligned columns
                _w(f"  {'FIXED':<10} {str(r.vin_v):<14} {vout_str:<14} {r.expected_vout_v:<16.1f} {r.status}\n")
            # Write the sweep result as a single summary row
            _w(f"  {'SWEEP':<10} {sweep.vin_range:<14} {sweep.vout_v:<14.4f} {sweep.expected_vout_v:<16.1f} {sweep.status}\n")
            # Write a separator after the results table
            _w("  " + "-" * 60 + "\n\n")

            # Write the sweep configuration section heading
            _w("  Sweep Configuration\n")
            # Write a separator under the heading
            _w("  " + "-" * 60 + "\n")
            # Write the sweep start voltage
            _w(f"  Start voltage      : {self._sweep_start_v:.1f} V\n")
            # Write the sweep maximum voltage
            _w(f"  Max voltage        : {self._sweep_max_v:.1f} V\n")
            # Write the voltage step size
            _w(f"  Step size          : {self._sweep_step_v:.1f} V\n")
            # Write the dwell time at each step
            _w(f"  Step dwell time    : {self._step_dwell_s:.2f} s\n")
            # Write the DMM read interval
            _w(f"  DMM read interval  : {self._dmm_read_interval_s:.2f} s\n")
            # Write the total number of DMM samples collected during the sweep
            _w(f"  Total DMM samples  : {len(sweep.samples)}\n\n")

            # Write the overall result border
            _w("=" * 65 + "\n")
            # Write the overall PASS or FAIL verdict prominently
            _w(f"  OVERALL RESULT : {verdict}\n")
            # Write the closing border
            _w("=" * 65 + "\n")

        # Write a log entry confirming the text summary was saved
        self._logger.info(f"Summary saved: {txt_path}")
        # Print a confirmation to the terminal
        print(f"  Saved: reports/{txt_path.name}")

        # Return the overall verdict string ("PASS" or "FAIL") to the caller
        return verdict

    # ─────────────────────────────────────────────────────────────
    # Multi-rail helpers  (SENSOR board — two output rails)
    # ─────────────────────────────────────────────────────────────

    def _prompt_rail_connection(self, rail: dict):
        """Ask the operator to move DMM probes to the specified output rail."""
        label      = rail.get("label", rail.get("name", "?"))
        test_point = rail.get("test_point", "")
        print()
        print("  " + "=" * 58)
        print(f"  CONNECT DMM TO: {label}")
        print("  " + "=" * 58)
        print()
        if test_point:
            print(f"  Test point : {test_point}")
        print()
        print("    + (HI) lead  ->  VOUT+ terminal  (positive)")
        print("    - (LO) lead  ->  GND / return")
        print()
        input("  Press ENTER when probes are connected and ready... ")
        print()

    def _generate_multi_rail_reports(self, all_results: dict, rail_names: list,
                                     vin_values: list, verdict: str):
        """Write CSV, JSON, and TXT summary for a multi-rail fixed-VIN test run."""
        self._test_end_time = datetime.datetime.now()
        ts       = self._timestamp
        duration = (self._test_end_time - self._test_start_time).total_seconds()

        # ── CSV ───────────────────────────────────────────────────────────────
        csv_path = self._reports_dir / f"input_range_ovp_results_{ts}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(
                ['VIN_V']
                + [f"VOUT_{n}_V" for n in rail_names]
                + [f"STATUS_{n}" for n in rail_names]
                + ['OVERALL_STATUS']
            )
            for vin in vin_values:
                row_pass = all(
                    all_results[vin].get(n, FixedVinResult(0, None, 0, 0, 'ERROR')).status == 'PASS'
                    for n in rail_names
                )
                row = [vin]
                for n in rail_names:
                    r = all_results[vin].get(n)
                    row.append(f"{r.vout_v:.4f}" if r and r.vout_v is not None else "N/A")
                for n in rail_names:
                    r = all_results[vin].get(n)
                    row.append(r.status if r else "ERROR")
                row.append("PASS" if row_pass else "FAIL")
                w.writerow(row)
        self._logger.info(f"CSV report saved: {csv_path}")
        print(f"  Saved: reports/{csv_path.name}")

        # ── JSON ──────────────────────────────────────────────────────────────
        json_path = self._reports_dir / f"input_range_ovp_results_{ts}.json"
        rows_out = []
        for vin in vin_values:
            entry: dict = {"vin_v": vin, "rails": {}}
            for n in rail_names:
                r = all_results[vin].get(n)
                entry["rails"][n] = r.to_dict() if r else {"status": "NOT_RUN"}
            rows_out.append(entry)
        report_data = {
            "test_info": {
                "test_name":        "Input Range and OVP Test (Multi-Rail — SENSOR)",
                "start_time":       self._test_start_time.isoformat(),
                "end_time":         self._test_end_time.isoformat(),
                "duration_seconds": round(duration, 1),
                "psu_address":      self._psu_address,
                "dmm_address":      self._dmm_address,
                "psu_channel":      self._psu_channel,
                "current_limit_a":  self._psu_current_limit_a,
                "ovp_level_v":      self._psu_ovp_level_v,
            },
            "multi_rail_results": rows_out,
            "overall_result":     verdict,
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        self._logger.info(f"JSON report saved: {json_path}")
        print(f"  Saved: reports/{json_path.name}")

        # ── TXT summary ───────────────────────────────────────────────────────
        txt_path = self._reports_dir / f"input_range_ovp_summary_{ts}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            _w = f.write
            _w("=" * 70 + "\n")
            _w("  INPUT RANGE AND OVP TEST (MULTI-RAIL) — RESULTS SUMMARY\n")
            _w("=" * 70 + "\n")
            _w(f"  Date / Time    : {self._test_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            _w(f"  PSU Address    : {self._psu_address}\n")
            _w(f"  DMM Address    : {self._dmm_address}\n")
            _w(f"  PSU Channel    : CH{self._psu_channel}\n")
            _w(f"  Current Limit  : {self._psu_current_limit_a:.2f} A\n")
            _w(f"  OVP Level      : {self._psu_ovp_level_v:.1f} V\n")
            _w("=" * 70 + "\n\n")
            col_w = 14
            header = f"  {'VIN (V)':<10}" + "".join(f"  {n:<{col_w}}" for n in rail_names) + "  STATUS\n"
            _w(header)
            _w("  " + "-" * (10 + len(rail_names) * (col_w + 2) + 8) + "\n")
            for vin in vin_values:
                row_pass = all(
                    all_results[vin].get(n, FixedVinResult(0, None, 0, 0, 'ERROR')).status == 'PASS'
                    for n in rail_names
                )
                vout_cols = ""
                for n in rail_names:
                    r = all_results[vin].get(n)
                    v_str = f"{r.vout_v:.4f}" if r and r.vout_v is not None else "N/A"
                    vout_cols += f"  {v_str:<{col_w}}"
                _w(f"  {vin:<10.1f}{vout_cols}  {'PASS' if row_pass else 'FAIL'}\n")
            _w("  " + "-" * (10 + len(rail_names) * (col_w + 2) + 8) + "\n\n")
            _w("=" * 70 + "\n")
            _w(f"  OVERALL RESULT : {verdict}\n")
            _w("=" * 70 + "\n")
        self._logger.info(f"Summary saved: {txt_path}")
        print(f"  Saved: reports/{txt_path.name}")
        print(f"\n  Results saved: {self._run_dir}")

    def _run_multi_rail_sequence(self) -> bool:
        """
        Execute the multi-rail fixed-VIN test sequence (SENSOR board).
        For each rail in OUTPUT_RAILS: prompts operator to connect DMM, applies
        each VIN from FIXED_VIN_TESTS, reads VOUT, records PASS/FAIL.
        Prints RESULT_ROW: JSON lines that the Gradio GUI parses into the
        results table.
        """
        print()
        print(f"  Run directory : {self._run_dir.resolve()}")

        try:
            if not self._connect_instruments():
                return False

            vin_values = [pt.vin_v for pt in self.FIXED_VIN_TESTS]
            rail_names = [r["name"] for r in self.OUTPUT_RAILS]

            # all_results[vin][rail_name] = FixedVinResult
            all_results: dict = {v: {} for v in vin_values}

            for rail in self.OUTPUT_RAILS:
                rail_name   = rail["name"]
                label       = rail.get("label", rail_name)
                test_point  = rail.get("test_point", "")
                expected_v  = rail["expected_vout_v"]
                tolerance_v = rail.get("vout_tolerance_v", 0.1)

                self._prompt_rail_connection(rail)

                print(f"\n  -- Rail: {label}  (test point: {test_point}) --")
                print(f"  {'VIN (V)':<12} {'VOUT (V)':<14} {'EXPECTED (V)':<16} {'STATUS'}")
                print("  " + "-" * 54)

                self._psu_set_v(0.0)
                self._psu.enable_channel_output(self._psu_channel)
                time.sleep(0.5)

                for vin in vin_values:
                    try:
                        print(f"  Setting Vin = {vin:.1f} V ...", end='', flush=True)
                        self._psu_set_v(vin)
                        time.sleep(self._fixed_vin_settle_s)

                        vout      = self._dmm_read_fast()
                        deviation = abs(vout - expected_v)
                        _eff_tol  = max(tolerance_v, expected_v * 0.05)
                        status    = "PASS" if deviation <= _eff_tol else "FAIL"

                        result = FixedVinResult(
                            vin_v=vin, vout_v=vout,
                            expected_vout_v=expected_v,
                            vout_tolerance_v=tolerance_v,
                            status=status,
                        )
                        all_results[vin][rail_name] = result

                        print(f"\r  {vin:<12.1f} {vout:<14.4f} {expected_v:<16.1f} {status}")
                        # Emit machine-readable result line for GUI table
                        import json as _json
                        print(
                            "RESULT_ROW: " + _json.dumps({
                                "vin":    vin,
                                "rail":   rail_name,
                                "label":  label,
                                "vout":   round(vout, 4),
                                "status": status,
                            }),
                            flush=True,
                        )

                    except Exception as exc:
                        self._logger.error(f"Rail {rail_name}, Vin={vin}: {exc}")
                        result = FixedVinResult(
                            vin_v=vin, vout_v=None,
                            expected_vout_v=expected_v,
                            vout_tolerance_v=tolerance_v,
                            status="ERROR",
                        )
                        all_results[vin][rail_name] = result
                        print(f"\r  {vin:<12.1f} {'N/A':<14} {expected_v:<16.1f} ERROR")
                        import json as _json
                        print(
                            "RESULT_ROW: " + _json.dumps({
                                "vin":    vin,
                                "rail":   rail_name,
                                "label":  label,
                                "vout":   None,
                                "status": "ERROR",
                            }),
                            flush=True,
                        )

                # Power down between rails for safe probe swap
                self._psu_set_v(0.0)
                time.sleep(0.5)
                self._psu.disable_channel_output(self._psu_channel)
                print("  " + "-" * 54)

            # ── Merged summary table ──────────────────────────────────────────
            col_w = 14
            print()
            print("  -- MULTI-RAIL SUMMARY --")
            hdr = f"  {'VIN (V)':<12}" + "".join(f"  {n:<{col_w}}" for n in rail_names) + "  STATUS"
            print(hdr)
            print("  " + "-" * (12 + len(rail_names) * (col_w + 2) + 8))

            overall_pass = True
            for vin in vin_values:
                row_pass = all(
                    all_results[vin].get(n, FixedVinResult(0, None, 0, 0, 'ERROR')).status == 'PASS'
                    for n in rail_names
                )
                overall_pass = overall_pass and row_pass
                vout_cols = ""
                for n in rail_names:
                    r = all_results[vin].get(n)
                    v_str = f"{r.vout_v:.4f}" if r and r.vout_v is not None else "N/A"
                    vout_cols += f"  {v_str:<{col_w}}"
                print(f"  {vin:<12.1f}{vout_cols}  {'PASS' if row_pass else 'FAIL'}")
            print("  " + "-" * (12 + len(rail_names) * (col_w + 2) + 8))

            verdict = "PASS" if overall_pass else "FAIL"
            print()
            print("  " + "=" * 50)
            print(f"  OVERALL RESULT : {verdict}")
            print("  " + "=" * 50)

            # ── Reports ───────────────────────────────────────────────────────
            print()
            print("  Writing reports...")
            self._generate_multi_rail_reports(all_results, rail_names, vin_values, verdict)
            print(f"  Run folder     : {self._run_dir}")
            print()
            return overall_pass

        except KeyboardInterrupt:
            print("\n\n  Test interrupted by user.")
            return False
        except Exception as exc:
            self._logger.error(f"Unhandled exception: {exc}", exc_info=True)
            print(f"\n  ERROR: {exc}")
            return False
        finally:
            print("  Disconnecting instruments...")
            self._disconnect_instruments()

    # ─────────────────────────────────────────────────────────────
    # Top-level entry point
    # ─────────────────────────────────────────────────────────────

    # Define the top-level method that orchestrates the complete test sequence from start to finish and returns True if all tests passed
    def run(self) -> bool:
        # This docstring is read by the Python help system and external tools to describe this method
        """Execute the full test sequence. Returns True if all tests pass."""
        # For multi-rail configs (e.g. SENSOR board) delegate to the dedicated sequence.
        if self.OUTPUT_RAILS:
            return self._run_multi_rail_sequence()

        # Print a blank line for visual spacing before the run directory path
        print()
        # Print the path to the run directory where all results are being saved
        print(f"  Run directory : {self._run_dir.resolve()}")

        # Begin the main try block that runs the full test; any unexpected exception is caught and logged
        try:
            # Attempt to connect to both instruments; if this fails, return False immediately
            if not self._connect_instruments():
                # Return False to indicate that the test could not start due to instrument connection failure
                return False

            # Ask the engineer to connect the DMM probes to the DUT output before measurements begin
            self._prompt_probe_setup()

            # Run Phase 1 (fixed input voltage tests) and store the list of results
            fixed_results = self.run_fixed_vin_tests()
            # Run Phase 2 (input voltage sweep) and store the sweep result
            sweep_result  = self.run_sweep_test()

            # Print a blank line before the plotting status message
            print()
            # Inform the engineer that graph generation is starting
            print("  Generating plots...")
            # Generate and save the two sweep graphs from the collected data
            self._plot_sweep(sweep_result)

            # Print a blank line before the report writing status message
            print()
            # Inform the engineer that report files are being written
            print("  Writing reports...")
            # Generate all three report files and get back the overall verdict string
            verdict = self._generate_reports(fixed_results, sweep_result)

            # Print a blank line before the final result display
            print()
            # Print the top border of the result box
            print("  " + "=" * 50)
            # Print the overall PASS or FAIL verdict prominently
            print(f"  OVERALL RESULT : {verdict}")
            # Print the bottom border of the result box
            print("  " + "=" * 50)
            # Print the location of the results folder for easy access
            print(f"  Run folder     : {self._run_dir}")
            # Print a trailing blank line
            print()
            # Return True if the overall verdict is PASS, False if FAIL
            return verdict == "PASS"

        # If the engineer presses Ctrl+C during the test, catch the interrupt and exit gracefully
        except KeyboardInterrupt:
            # Print a clear message informing the engineer the test was stopped
            print("\n\n  Test interrupted by user.")
            # Return False since the test did not complete normally
            return False

        # Catch any other unexpected exception that was not handled elsewhere
        except Exception as e:
            # Write the full exception details to the log file including a stack trace for debugging
            self._logger.error(f"Unhandled exception: {e}", exc_info=True)
            # Print the error message to the terminal
            print(f"\n  ERROR: {e}")
            # Return False since the test did not complete successfully
            return False

        # The finally block always runs, whether the test passed, failed, or was interrupted
        finally:
            # Inform the engineer that the instruments are being disconnected
            print("  Disconnecting instruments...")
            # Call the disconnect method to safely turn off the power supply and close all connections
            self._disconnect_instruments()
