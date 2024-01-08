# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains common utilities used by all tt-tools.
"""
import os
import importlib.resources
from yaml import safe_load


def init_fw_defines(chip, tool_name="tt_smi"):
    """
    Loads the fw_defines.yaml with arc msg definitions from the chip's data directory.
    """
    fw_defines = safe_load(get_chip_data(chip, "fw_defines.yaml", False, tool_name))
    return fw_defines


def int_to_bits(x):
    return list(filter(lambda b: x & (1 << b), range(x.bit_length())))


def get_chip_data(chip, file, internal: bool, tool_name="tt_smi"):
    """
    Helper function to load a file from the chip's data directory.
    """
    with importlib.resources.path(f"{tool_name}", "") as path:
        if chip.as_wh() is not None:
            prefix = "wormhole"
        elif chip.as_gs() is not None:
            prefix = "grayskull"
        else:
            raise Exception("Only support fw messages for Wh or GS chips")
        if internal:
            prefix = f".ignored/{prefix}"
        else:
            prefix = f"data/{prefix}"
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


def init_logging(log_folder: str):
    """Create log folders if they don't exist"""
    if not os.path.isdir(log_folder):
        os.mkdir(log_folder)
