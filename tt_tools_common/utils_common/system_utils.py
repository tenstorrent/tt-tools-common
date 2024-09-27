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
from typing import Union
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
    if int(driver.split(".")[1]) < minimum_driver_version:
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
        "Driver": "TTKMD " + get_driver_version(),
    }


def system_compatibility() -> dict:
    """
    Return compatibility checklist for the system
    """
    host_info = get_host_info()
    checklist = {}
    if host_info["OS"] == "Linux":
        if distro.id() == "ubuntu":
            distro_version = float(".".join(distro.version_parts()[:2]))
            print(distro_version)
            if distro_version >= 20.04:
                checklist["OS"] = (True, "Pass")
            else:
                checklist["OS"] = (False, "Recommended Ubuntu 20.04+")
        else:
            checklist["OS"] = (False, "Recommended Ubuntu 20.04+")
    else:
        checklist["OS"] = (False, "Recommended Ubuntu 20.04+")

    if host_info["Driver"]:
        checklist["Driver"] = (True, "Pass")
    else:
        checklist["Driver"] = (False, "Fail, no driver")
    if psutil.virtual_memory().total >= 32 * 1e9:
        checklist["Memory"] = (True, "Pass")
    else:
        checklist["Memory"] = (False, "Recommended 32GB+")

    # Due do how Arm PCIe device rescans are handled, we can't perform a Wormhole reset on Arm systems
    if host_info["Platform"].startswith("arm") or host_info["Platform"].startswith(
        "aarch"
    ):
        checklist["WH Reset"] = (
            False,
            "Not supported on Arm",
        )
    else:
        checklist["WH Reset"] = (True, "Pass")

    # GS reset is supported on all systems since it doesn't depend on a PCIe re-scan
    checklist["GS Reset"] = (True, "Pass")
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
            version[
                "Failed to fetch"
            ] = "There was an error connecting to the server. Please check your internet connection."
        except requests.exceptions.Timeout:
            version[
                "Failed to fetch"
            ] = "Timeout error. It seems the server is taking too long to respond."
        except requests.exceptions.RequestException:
            version["Failed to fetch"] = "Something unexpected happened."

    if show_sw_ver:
        return version

    return sw_ver
