# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains functions used to do a PCIe level reset for Wormhole chip.
"""

import os
import sys
import time
import fcntl
import struct
from typing import List
from pyluwen import PciChip
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR
from tt_tools_common.utils_common.tools_utils import read_refclk_counter
from tt_tools_common.utils_common.system_utils import (
    check_driver_version,
    get_host_info,
    is_driver_version_at_least,
    get_driver_version
)
from tt_tools_common.reset_common.chip_reset import ChipReset


class WHChipReset:
    """Class to perform a chip level reset on WH PCIe boards"""

    # WH magic numbers for reset
    TENSTORRENT_IOCTL_MAGIC = 0xFA
    TENSTORRENT_IOCTL_RESET_DEVICE = (TENSTORRENT_IOCTL_MAGIC << 8) | 6
    TENSTORRENT_RESET_DEVICE_RESTORE_STATE = 0
    TENSTORRENT_RESET_DEVICE_RESET_PCIE_LINK = 1
    A3_STATE_PROP_TIME = 0.03
    POST_RESET_MSG_WAIT_TIME = 2
    MSG_TRIGGER_SPI_COPY_LtoR = 0x50
    MSG_TYPE_ARC_STATE3 = 0xA3
    MSG_TYPE_TRIGGER_RESET = 0x56

    def reset_device_ioctl(self, interface_id: int, flags: int) -> bool:
        dev_path = f"/dev/tenstorrent/{interface_id}"
        dev_fd = os.open(
            dev_path, os.O_RDWR | os.O_CLOEXEC
        )  # Raises FileNotFoundError and other appropriate exceptions.
        try:
            reset_device_in_struct = "II"
            reset_device_out_struct = "II"
            reset_device_struct = reset_device_in_struct + reset_device_out_struct

            input_size_bytes = struct.calcsize(reset_device_in_struct)
            output_size_bytes = struct.calcsize(reset_device_out_struct)
            reset_device_buf = bytearray(
                struct.pack(reset_device_struct, output_size_bytes, flags, 0, 0)
            )
            fcntl.ioctl(
                dev_fd, self.TENSTORRENT_IOCTL_RESET_DEVICE, reset_device_buf
            )  # Raises OSError

            output_buf = reset_device_buf[input_size_bytes:]
            _, result = struct.unpack(reset_device_out_struct, output_buf)

            return result == 0
        finally:
            os.close(dev_fd)

    def full_lds_reset(
        self, pci_interfaces: List[int], reset_m3: bool = False, silent: bool = False
    ) -> List[PciChip]:
        """Performs a full LDS reset of a list of chips"""
        
        # Use new reset for driver version >= 2.4.1
        if is_driver_version_at_least(get_driver_version(), "2.4.1"):
            return ChipReset().full_lds_reset(pci_interfaces, reset_m3, silent)

        if not silent:
            print(
                CMD_LINE_COLOR.YELLOW,
                "Notice: Using legacy WH reset implementation. This will be removed in a later version.",
                "Please upgrade tt-kmd to version 2.4.1 or newer to use the updated reset sequence.",
                CMD_LINE_COLOR.ENDC
            )

        # Check the driver version and bail if link reset cannot be supported
        check_driver_version(operation="board reset")

        # Due to how Arm systems deal with PCIe device rescans, WH device resets don't work on that platform.
        # Check for platform and bail if it's Arm
        platform = get_host_info()["Platform"]
        if platform.startswith("arm") or platform.startswith("aarch"):
            print(
                CMD_LINE_COLOR.RED,
                "Cannot perform WH board reset on Arm systems, please reboot the system to reset the boards. Exiting...",
                CMD_LINE_COLOR.ENDC,
            )
            sys.exit(1)

        # Remove duplicates from the input list of PCI interfaces
        pci_interfaces = list(set(pci_interfaces))
        if not silent:
            print(
                f"{CMD_LINE_COLOR.BLUE} Starting PCI link reset on WH devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
            )

        for pci_interface in pci_interfaces:
            self.reset_device_ioctl(
                pci_interface, self.TENSTORRENT_RESET_DEVICE_RESET_PCIE_LINK
            )
        pci_chips = [PciChip(pci_interface=interface) for interface in pci_interfaces]
        refclk_list = []
        fail = False
        # Trigger resets for all chips in order
        for chip in pci_chips:
            # Collect the arc refclk for the chip before sending reset arc messages
            try:
                refclk_list.append(read_refclk_counter(chip))
            except Exception as e:
                # If we get to this point means ioctl reset isn't enough to reset the chip
                # This is a fatal error, we should exit and recommend user to reboot the system
                print(
                    CMD_LINE_COLOR.RED,
                    "Failed to recover WH chip, please reboot the system to reset the chip. Exiting...",
                    CMD_LINE_COLOR.ENDC,
                )
                sys.exit(1)
            # Trigger A3 safe state. A3 is a safe state where there are no more pending regulator requests.
            chip.arc_msg(self.MSG_TYPE_ARC_STATE3, wait_for_done=True)
            time.sleep(self.A3_STATE_PROP_TIME)
            # Triggers M3 board level reset by sending arc msg.
            if reset_m3:
                chip.arc_msg(self.MSG_TYPE_TRIGGER_RESET, wait_for_done=False, arg0=3)
            else:
                chip.arc_msg(self.MSG_TYPE_TRIGGER_RESET, wait_for_done=False)

        time.sleep(self.POST_RESET_MSG_WAIT_TIME)

        for i, (chip, pci_interface) in enumerate(zip(pci_chips, pci_interfaces)):
            self.reset_device_ioctl(
                pci_interface, self.TENSTORRENT_RESET_DEVICE_RESTORE_STATE
            )
            current_refclk = read_refclk_counter(chip)
            if refclk_list[i] < current_refclk:
                print(
                    CMD_LINE_COLOR.RED,
                    f"Reset for PCI {pci_interface} didn't go through! Refclk didn't reset. Value before: {refclk_list[i]}, value after: {current_refclk}",
                    CMD_LINE_COLOR.ENDC,
                )
                fail = True

        if fail:
            print(
                CMD_LINE_COLOR.YELLOW,
                "Reset failed for one or more boards, returning with non-zero exit code",
                CMD_LINE_COLOR.ENDC,
            )
            sys.exit(1)
        else:
            #  All went well print success message
            if not silent:
                print(
                    f"{CMD_LINE_COLOR.GREEN} Finishing PCI link reset on WH devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
                )

        return pci_chips
