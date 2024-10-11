# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Reset test for BH Tensix reset
"""
from pyluwen import detect_chips
from tt_tools_common.reset_common.bh_reset import BHChipReset


def main():
    bh_pci_idx = []
    devices = detect_chips()
    for i, dev in enumerate(devices):
        if dev.as_bh():
            bh_pci_idx.append(i)
            print(f"BH chip {i}...")

    BHChipReset().full_lds_reset(pci_interfaces=bh_pci_idx)


if __name__ == "__main__":
    main()
