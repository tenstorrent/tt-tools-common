# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains common utilities used by all tt-tools.
"""
import os
import sys
import json
import psutil
import distro
import platform
import requests
from typing import Union, Tuple, Dict
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR

MINIMUM_DRIVER_VERSION_LDS_RESET = "1.26.0"
LOG_FOLDER = os.path.expanduser("~/.config/tenstorrent")

def get_size(size_bytes: int, suffix: str = "B") -> str:
    """
    Scale bytes to its proper format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if size_bytes < factor:
            return f"{size_bytes:.2f} {unit}{suffix}"
        size_bytes /= factor
    return "N/A"


def get_driver_version() -> Union[str, None]:
    """
    Get the version of the Tenstorrent driver
    """
    try:
        with open("/sys/module/tenstorrent/version", "r", encoding="utf-8") as f:
            driver = f.readline().rstrip()
    except Exception:
        driver = None

    return driver

def _parse_version_string(version_str: str) -> Tuple[int, int, int]:
    """
    Parse a version string into a tuple of (major, minor, patch) integers.
    Handles SemVer-like formats including pre-release identifiers and build metadata,
    e.g., "1.34", "1.34.0", "1.34.1-alpha", "1.2.3+build456", "1.4.0-rc1+build42".

    Pre-release identifiers (e.g., "-alpha") and build metadata (e.g., "+build456")
    are stripped to get the core (major, minor, patch) version for comparison.

    Versions with fewer than three numeric parts (e.g., "1.34") will have patch
    (and minor if applicable for a single "1") defaulted to 0.
    """
    if not version_str:
        raise ValueError("Version string cannot be empty")

    # Strip build metadata (text after first '+') first.
    core_version_str = version_str.split("+")[0]

    # Then, strip pre-release identifier (text after '-').
    main_version_part = core_version_str.split("-")[0]

    parts = main_version_part.split(".")

    if not parts or not parts[0]: # Check for empty string after split or no parts
        raise ValueError(f"Invalid version format: {version_str}")

    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except ValueError as e:
        raise ValueError(f"Version parts must be integers: {version_str}") from e

    return major, minor, patch

def is_driver_version_at_least(current_version: str, minimum_version: str) -> bool:
    """
    Check if the current driver version meets or exceeds the minimum required version.
    """
    if current_version is None:
        raise ValueError("No Tenstorrent driver detected! Please install the driver using tt-kmd: " +
            "https://github.com/tenstorrent/tt-kmd")
    
    current_tuple = _parse_version_string(current_version)
    minimum_tuple = _parse_version_string(minimum_version)

    # Python's tuple comparison works lexicographically, which is suitable for version numbers.
    # (1, 34, 0) is less than (1, 35, 0)
    # (1, 34, 0) is not less than (1, 34, 0)
    # (2, 0, 0) is greater than (1, 35, 0)
    return current_tuple >= minimum_tuple

def check_driver_version(
    operation: str, minimum_required_version_str: str = MINIMUM_DRIVER_VERSION_LDS_RESET
):
    """
    Check if the currently installed Tenstorrent driver version is sufficient
    for the specified operation and exit if not.

    Compares the current driver version against the minimum required version.
    Exits with a non-zero status code if:
    - No driver is detected.
    - Version strings are malformed.
    - The current driver version is older than the minimum required version.
    """
    current_driver_version_str = get_driver_version()

    try:
        if is_driver_version_at_least(current_driver_version_str, minimum_required_version_str):
            return  # Version is sufficient, continue normally
    except ValueError as e:
        print(
            f"{CMD_LINE_COLOR.RED}"
            f"Error parsing driver version. {e}"
            f"{CMD_LINE_COLOR.ENDC}"
        )
        sys.exit(1)

    # If we reach here, the version is insufficient
    print(
        f"{CMD_LINE_COLOR.RED}"
        f"Current driver version: {current_driver_version_str}"
        f"{CMD_LINE_COLOR.ENDC}"
    )
    print(
        f"{CMD_LINE_COLOR.RED}"
        f"Operation '{operation}' requires Tenstorrent driver version "
        f"{minimum_required_version_str} or greater. Your version is too old."
        f"{CMD_LINE_COLOR.ENDC}"
    )
    print(
        f"{CMD_LINE_COLOR.RED}"
        "Please update your driver using tt-kmd: https://github.com/tenstorrent/tt-kmd"
        f"{CMD_LINE_COLOR.ENDC}"
    )
    sys.exit(1)


def get_host_info() -> dict:
    """
        Reads and organizes host info
    Returns:
        dict: with host info
    """
    uname = platform.uname()
    svmem = psutil.virtual_memory()

    os: str = uname.system
    distro_name: str = distro.name(pretty=True)
    kernel: str = uname.release
    hostname: str = uname.node

    return {
        "OS": os,
        "Distro": distro_name,
        "Kernel": kernel,
        "Hostname": hostname,
        "Platform": uname.machine,
        "Python": platform.python_version(),
        "Memory": get_size(svmem.total),
        "Driver": "TT-KMD " + get_driver_version(),
    }

def get_host_compatibility_info() -> Dict[str, Union[str, Tuple]]:
    """
    Return host info with system compatibility notes

    Returns dict with str keys per-item. Values are str
    if the item is fully compatible, or tuple of str if
    not. The first element is the current state and the
    second element is the desired or recommended state.
    """
    host_info = get_host_info()
    checklist = {}
    full_os = f"{host_info['OS']} ({host_info['Platform']})"

    if host_info["OS"] == "Linux":
        checklist["OS"] = full_os
    else:
        checklist["OS"] = (full_os, "Linux (x86_64)")

    if distro.id() == "ubuntu":
        distro_version = float(".".join(distro.version_parts()[:2]))
        if distro_version >= 22:
            checklist["Distro"] = host_info["Distro"]
        else:
            checklist["Distro"] = (host_info["Distro"], "22.04 or 24.04")
    else:
        checklist["Distro"] = (host_info["Distro"], "Ubuntu 22.04 or 24.04")

    checklist["Kernel"] = host_info["Kernel"]
    checklist["Hostname"] = host_info["Hostname"]
    checklist["Python"] = host_info["Python"]

    if psutil.virtual_memory().total >= 32 * 1e9:
        checklist["Memory"] = host_info["Memory"]
    else:
        checklist["Memory"] = (host_info["Memory"], "32GB+")

    if host_info["Driver"]:
        checklist["Driver"] = host_info["Driver"]
    else:
        checklist["Driver"] = (host_info["Driver"], "TT-KMD v1.27+")

    return checklist

def get_sw_ver_flags():
    """
    Get the flags from the reset config file
    """
    if os.path.exists(f"{LOG_FOLDER}/reset_config.json"):
        try:
            # Attempt to parse as a JSON file
            with open(f"{LOG_FOLDER}/reset_config.json", "r") as json_file:
                data = json.load(json_file)
                disable_serial_report = data.get("disable_serial_report", False)
                disable_sw_version_report = data.get("disable_sw_version_report", False)
                return disable_serial_report, disable_sw_version_report
        except json.JSONDecodeError as e:
            return None, None
    else:
        return None, None

def get_sw_ver_from_url(board_id: str):
    url = "https://cereal.tenstorrent.com?SerialNumber=" + board_id
    version = {}
    try:
        r = requests.get(url)

        try:
            r_text = r.json()
        except json.JSONDecodeError:
            print("Error decoding json")
            version["Failed to fetch"] = "No response from server"
        else:
            if isinstance(r_text, dict):
                for key, value in r_text.items():
                    if isinstance(value, str) and isinstance(key, str):
                        version.update({key: value})
                version.update({"Buda": "0.9.80", "Metallium": "0.42.0"})
                # Fix up the keys with user-facing names
                version["TT-Metalium"] = version["Metallium"]
                del version["Metallium"]
                version["TT-Buda"] = version["Buda"]
                del version["Buda"]
            else:
                version["Failed to fetch"] = "Unexpected response from server"
    except requests.exceptions.HTTPError:
        version["Failed to fetch"] = "We encountered an HTTP error."
    except requests.exceptions.ConnectionError:
        version["Failed to fetch"] = (
            "There was an error connecting to the server. Please check your internet connection."
        )
    except requests.exceptions.Timeout:
        version["Failed to fetch"] = (
            "Timeout error. It seems the server is taking too long to respond."
        )
    except requests.exceptions.RequestException:
        version["Failed to fetch"] = "Something unexpected happened."

    return version

def get_sw_ver_info(show_sw_ver: bool, board_ids: str):
    """
    Get software version info.
    If reset_config is available on the system then parse the file and disable settings as specified
    Args:
        show_sw_ver (bool): Whether to show software version info. Will default to N/A if False.
    """
    sw_ver = {
        "Firmware Bundle": "N/A",
        "tt-smi": "N/A",
        "tt-flash": "N/A",
        "tt-kmd": "N/A",
        "TT-Buda": "N/A",
        "TT-Metalium": "N/A",
    }
    disable_serial_report, disable_sw_version_report = get_sw_ver_flags()

    if disable_sw_version_report or not show_sw_ver:
        # return default
        return sw_ver
    if disable_serial_report:
        sw_ver = get_sw_ver_from_url("")
    else:
        for board_id in board_ids:
            # get the query for all the boards
            sw_ver = get_sw_ver_from_url(board_id)
    return sw_ver
