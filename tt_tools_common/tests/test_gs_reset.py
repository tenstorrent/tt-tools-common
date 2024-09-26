# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Reset test for GS Tensix reset
"""
from pyluwen import detect_chips
from tt_tools_common.reset_common.gs_tensix_reset import GSTensixReset


def main():
    devices = detect_chips()
    for i, dev in enumerate(devices):
        if dev.as_gs():
            print(f"Resetting GS chip {i}...")
            GSTensixReset(dev).tensix_reset()


if __name__ == "__main__":
    main()
