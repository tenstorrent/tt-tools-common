# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains common utilities used by all tt-tools.
"""
import sys
import json
import psutil
import distro
import platform
import requests
from typing import Union, Tuple, Dict
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR

MINIMUM_DRIVER_VERSION_LDS_RESET = 26


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


def check_driver_version(
    operation: str, minimum_driver_version: str = MINIMUM_DRIVER_VERSION_LDS_RESET
):
    """
    Check if driver is beyond minimum version to perform resets
    Return non zero exit code and bail if version check fails
    """
    driver = get_driver_version()
    if driver is None:
        print(
            CMD_LINE_COLOR.RED,
            "No Tenstorrent driver detected! Please install driver using tt-kmd: https://github.com/tenstorrent/tt-kmd ",
            CMD_LINE_COLOR.ENDC,
        )
        sys.exit(1)
    if int(driver.split("-")[0].split(".")[1]) < minimum_driver_version:
        print(
            CMD_LINE_COLOR.RED,
            f"Current driver version: {driver}",
            CMD_LINE_COLOR.ENDC,
        )
        print(
            CMD_LINE_COLOR.RED,
            f"This script requires driver version to be greater than 1.{minimum_driver_version}, not continuing with {operation}",
            CMD_LINE_COLOR.ENDC,
        )
        print(
            CMD_LINE_COLOR.RED,
            "Please install correct driver version using tt-kmd: https://github.com/tenstorrent/tt-kmd ",
            CMD_LINE_COLOR.ENDC,
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
        if distro_version >= 20.04:
            checklist["Distro"] = host_info["Distro"]
        else:
            checklist["Distro"] = (host_info["Distro"], "20.04 or 22.04")
    else:
        checklist["Distro"] = (host_info["Distro"], "Ubuntu 20.04 or 22.04")

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


def get_sw_ver_info(show_sw_ver: bool, board_ids: str):
    # TODO: Implement call to server to pull latest SW versions
    """
    Get software version info.

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
    version = {}
    for board_id in board_ids:
        url = "https://cereal.tenstorrent.com?SerialNumber=" + board_id
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

    if show_sw_ver:
        return version

    return sw_ver
