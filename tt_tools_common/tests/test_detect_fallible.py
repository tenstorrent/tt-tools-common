# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test for detect_chips_fallible
"""
from pyluwen import detect_chips
from tt_tools_common.utils_common.tools_utils import detect_chips_with_callback
from tt_tools_common.reset_common.wh_reset import WHChipReset


def main():
    devices = detect_chips_with_callback()

    wh_pci_idx = []
    devices = detect_chips()
    for i, dev in enumerate(devices):
        if dev.as_wh() and not dev.is_remote():
            wh_pci_idx.append(i)

    WHChipReset().full_lds_reset(pci_interfaces=wh_pci_idx)
    devices = detect_chips_with_callback()


if __name__ == "__main__":
    main()
