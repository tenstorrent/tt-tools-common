# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains common utilities used by all tt-tools.
"""
import os
import sys
import time
from typing import List
import importlib.resources
from yaml import safe_load
from pyluwen import PciChip, detect_chips_fallible
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR


def init_fw_defines(chip_name: str = "wormhole", tool_name: str = "tt_smi"):
    """
    Loads the fw_defines.yaml with arc msg definitions from the chip's data directory.
    """
    fw_defines = safe_load(
        get_chip_data(chip_name, "fw_defines.yaml", False, tool_name)
    )
    return fw_defines


def int_to_bits(x):
    return list(filter(lambda b: x & (1 << b), range(x.bit_length())))


def get_chip_data(chip_name, file, internal: bool, tool_name="tt_smi"):
    """
    Helper function to load a file from the chip's data directory.
    """
    with importlib.resources.path(f"{tool_name}", "") as path:
        if chip_name not in ["wormhole", "grayskull"]:
            raise Exception("Only support fw messages for Wh or GS chips")
        prefix = chip_name
        if internal:
            prefix = f".ignored/{prefix}"
        else:
            prefix = f"data/{prefix}" if not ".data" in tool_name else prefix
        return open(str(path.joinpath(f"{prefix}/{file}")))


def get_board_type(board_id: str) -> str:
    """
    Get board type from board ID string.
    Ex:
        Board ID: AA-BBBBB-C-D-EE-FF-XXX
                   ^     ^ ^ ^  ^  ^   ^
                   |     | | |  |  |   +- XXX
                   |     | | |  |  +----- FF
                   |     | | |  +-------- EE
                   |     | | +----------- D
                   |     | +------------- C = Revision
                   |     +--------------- BBBBB = Unique Part Identifier (UPI)
                   +--------------------- AA
    """
    serial_num = int(f"0x{board_id}", base=16)
    upi = (serial_num >> 36) & 0xFFFFF
    rev = (serial_num >> 32) & 0xF

    if upi == 0x1:
        if rev == 0x2:
            return "E300_R2"
        elif rev in (0x3, 0x4):
            return "E300_R3"
        else:
            return "N/A"
    elif upi == 0x3:
        # Formerly E300_105
        return "e150"
    elif upi == 0x7:
        return "e75"
    elif upi == 0x8:
        return "NEBULA_CB"
    elif upi == 0xA:
        # Formerly E300_X2
        return "e300"
    elif upi == 0xB:
        return "GALAXY"
    elif upi == 0x14:
        # Formerly NEBULA_X2
        return "n300"
    elif upi == 0x18:
        # Formerly NEBULA_X1
        return "n150"
    else:
        return "N/A"


def hex_to_date(hexdate: int, include_time=True):
    """Converts a date given in hex from format 0xYMDDHHMM to string YYYY-MM-DD HH:MM"""
    if hexdate == 0 or hexdate == 0xFFFFFFFF:
        return "N/A"

    year = (hexdate >> 28 & 0xF) + 2020
    month = hexdate >> 24 & 0xF
    day = hexdate >> 16 & 0xFF
    hour = hexdate >> 8 & 0xFF
    minute = hexdate & 0xFF

    date = f"{year:04}-{month:02}-{day:02}"

    if include_time:
        date += f" {hour:02}:{minute:02}"

    return date


def init_logging(log_folder: str):
    """Create tt-mod log folders if they don't exist"""
    if not os.path.isdir(log_folder):
        os.mkdir(log_folder)


def semver_to_hex(semver: str):
    """Converts a semantic version string from format 10.15.1 to hex 0x0A0F0100"""
    major, minor, patch = semver.split(".")
    byte_array = bytearray([0, int(major), int(minor), int(patch)])
    return f"{int.from_bytes(byte_array, byteorder='big'):08x}"


def date_to_hex(date: int):
    """Converts a given date string from format YYYYMMDDHHMM to hex 0xYMDDHHMM"""
    year = int(date[0:4]) - 2020
    month = int(date[4:6])
    day = int(date[6:8])
    hour = int(date[8:10])
    minute = int(date[10:12])
    byte_array = bytearray([year * 16 + month, day, hour, minute])
    return f"{int.from_bytes(byte_array, byteorder='big'):08x}"


def hex_to_semver(hexsemver: int):
    """Converts a semantic version string from format 0x0A0F0100 to 10.15.1"""
    if hexsemver == 0 or hexsemver == 0xFFFFFFFF:
        raise ValueError("hexsemver is invalid!")

    major = hexsemver >> 16 & 0xFF
    minor = hexsemver >> 8 & 0xFF
    patch = hexsemver >> 0 & 0xFF

    return f"{major}.{minor}.{patch}"


def hex_to_semver_eth(hexsemver: int):
    """Converts a semantic version string from format 0x061000 to 6.1.0"""
    if hexsemver == 0 or hexsemver == 0xFFFFFF:
        return "N/A"

    major = hexsemver >> 16 & 0xFF
    minor = hexsemver >> 12 & 0xF
    patch = hexsemver & 0xFFF

    return f"{major}.{minor}.{patch}"


def hex_to_semver_m3_fw(hexsemver: int):
    """Converts a semantic version string from format 0x0A0F0100 to 10.15.1"""
    if hexsemver == 0 or hexsemver == 0xFFFFFFFF:
        return "N/A"

    major = hexsemver >> 24 & 0xFF
    minor = hexsemver >> 16 & 0xFF
    patch = hexsemver >> 8 & 0xFF
    ver = hexsemver >> 0 & 0xFF

    return f"{major}.{minor}.{patch}.{ver}"

def hex_to_semver_zephyr_fw(hexsemver: int):
    """Converts a semantic version string from format 0x0A0F0100 to 10.15.1 or
    0x0A0F0101 to 10.15.1-rc1"""
    if hexsemver == 0 or hexsemver == 0xFFFFFFFF:
        return "N/A"

    major = hexsemver >> 24 & 0xFF
    minor = hexsemver >> 16 & 0xFF
    patch = hexsemver >> 8 & 0xFF
    rc_num = hexsemver >> 0 & 0xFF

    rc = ""
    # rc of 0 indicates a final release and requires no suffix
    # rc > 0 indicates a release candidate (i.e. -rc1, -rc2, etc)
    if rc_num > 0:
        rc = f"-rc{rc_num}"

    return f"{major}.{minor}.{patch}{rc}"


def init_logging(log_folder: str):
    """Create log folders if they don't exist"""
    if not os.path.isdir(log_folder):
        os.makedirs(log_folder)


# Show that the refclock counter (ARC_RESET.REFCLK_COUNTER_LOW/HIGH) is ticking at
# the expected frequency, independent of ARCLK.


def read_refclk_counter(chip) -> int:
    if chip.as_gs():
        return None
    high_addr = chip.axi_translate("ARC_RESET.REFCLK_COUNTER_HIGH").addr
    low_addr = chip.axi_translate("ARC_RESET.REFCLK_COUNTER_LOW").addr
    high1 = chip.axi_read32(high_addr)
    low = chip.axi_read32(low_addr)
    high2 = chip.axi_read32(high_addr)

    if high1 != high2:
        low = chip.axi_read32(low_addr)

    return (high2 << 32) | low


# Returns REFCLK_COUNTER rate in MHz
def refclk_counter_rate(chip, delay_interval: float = 0.1) -> float:
    before_refclk = read_refclk_counter(chip)
    before_ns = time.time_ns()

    time.sleep(delay_interval)

    after_refclk = read_refclk_counter(chip)
    after_ns = time.time_ns()

    return (after_refclk - before_refclk) * 1000 / (after_ns - before_ns)


def check_refclk_counter_read_speed(chip):
    loops = 100

    before_ns = time.time_ns()
    for _ in range(loops):
        read_refclk_counter(chip)
    after_ns = time.time_ns()

    if after_ns - before_ns > 100_000 * loops:
        us_per = (after_ns - before_ns) // (loops * 1000)
        print(f"REFCLK_COUNTER reads are unusually slow ({us_per}us).")


def check_refclk_counter_rate(chip, expected_refclk: float, accuracy: float):
    observed_refclk = refclk_counter_rate(chip)
    # print(f"refclk {observed_refclk}MHz")
    if (
        abs(expected_refclk - observed_refclk) / min(expected_refclk, observed_refclk)
        > accuracy / 100
    ):
        return f"REFCLK_COUNTER outside of allowed range: {observed_refclk}"
    else:
        return None


def detect_chips_with_callback(
    local_only: bool = False,
    ignore_ethernet: bool = False,
    print_status: bool = True,
) -> List[PciChip]:
    """
    This will create a chip which only guarantees that you have communication with the chip.
    """

    chip_count = 0
    block_count = 0
    arc_count = 0
    dram_count = 0
    spinner = ["\\", "|", "/", "-"]

    last_draw = time.time()

    def chip_detect_callback(status):
        nonlocal chip_count, last_draw, block_count, arc_count, dram_count

        if status.new_chip():
            chip_count += 1
        elif status.correct_down():
            chip_count -= 1
        chip_count = max(chip_count, 0)

        # Move the cursor and delete the previous block of printed lines
        if block_count > 0 and print_status:
            print(f"\033[{block_count}A", end="", flush=True)
            print(f"\033[J", end="", flush=True)

        if print_status:
            print(
                f"\r{CMD_LINE_COLOR.PURPLE} Detected Chips: {CMD_LINE_COLOR.YELLOW}{chip_count}{CMD_LINE_COLOR.ENDC}\n",
                end="",
                flush=True,
            )
            block_count = 1

        # Prune and update the status string
        status_string = status.status_string()
        if status_string is not None and local_only is False and print_status is True:
            # remove empty lines
            for line in list(filter(None, status_string.splitlines())):
                # Up the counter for each line printed
                block_count += 1
                if "ARC" in line:
                    arc_count = arc_count + 1
                    # Spinner character is based on the number of ARCs detected
                    print(
                        f"\r{CMD_LINE_COLOR.BLUE} Detecting ARC: "
                        + f"{CMD_LINE_COLOR.YELLOW}{spinner[arc_count % len(spinner)]}{CMD_LINE_COLOR.ENDC}",
                        flush=True,
                    )
                elif "DRAM" in line:
                    dram_count = dram_count + 1
                    print(
                        f"\r{CMD_LINE_COLOR.BLUE} Detecting DRAM: "
                        + f"{CMD_LINE_COLOR.YELLOW}{spinner[dram_count % len(spinner)]}{CMD_LINE_COLOR.ENDC}",
                        flush=True,
                    )
                elif "ETH" in line:
                    import re

                    paren_pattern = r"\((.*?)\)"
                    bracket_pattern = r"\[(.*?)\]"
                    # Find substrings between parentheses
                    paren_substr = re.search(paren_pattern, line)
                    bracket_substr = re.search(bracket_pattern, line)
                    # Extract substring from matched group
                    bracket_substr = bracket_substr.group(1) if bracket_substr else ""
                    paren_substr = paren_substr.group(1) if paren_substr else ""
                    line = re.sub(paren_pattern, "", line)
                    print(
                        f"\r {CMD_LINE_COLOR.PURPLE}[{paren_substr}]{CMD_LINE_COLOR.BLUE}{line}: "
                        + f"{CMD_LINE_COLOR.YELLOW}{spinner[dram_count % len(spinner)]}{CMD_LINE_COLOR.ENDC}",
                        flush=True,
                    )
                else:
                    print(
                        f"\r{line}",
                        flush=True,
                    )

    output = []
    for device in detect_chips_fallible(
        local_only=local_only,
        continue_on_failure=False,
        callback=chip_detect_callback,
        noc_safe=ignore_ethernet,
    ):
        if not device.have_comms():
            raise Exception(
                f"Do not have communication with {device}, you should reset or remove this device from your system before continuing."
            )

        device = device.force_upgrade()
        output.append(device)

    return output
