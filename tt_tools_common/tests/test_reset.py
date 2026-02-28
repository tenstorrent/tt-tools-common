# SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Reset test for chip reset
"""
from pyluwen import detect_chips
from tt_tools_common.reset_common.chip_reset import ChipReset


def main():
    pci_interfaces = []
    devices = detect_chips()
    for i, _ in enumerate(devices):
        pci_interfaces.append(i)
        print(f"Chip {i}...")

    ChipReset().full_lds_reset(pci_interfaces=pci_interfaces)


if __name__ == "__main__":
    main()
