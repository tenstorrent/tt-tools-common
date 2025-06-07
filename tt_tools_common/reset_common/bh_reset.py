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
    # check_driver_version,
    get_host_info,
)


class BHChipReset:
    """Class to perform a chip level reset on WH PCIe boards"""

    # WH magic numbers for reset
    TENSTORRENT_IOCTL_MAGIC = 0xFA
    TENSTORRENT_IOCTL_RESET_DEVICE = (TENSTORRENT_IOCTL_MAGIC << 8) | 6
    TENSTORRENT_RESET_DEVICE_RESTORE_STATE = 0
    TENSTORRENT_RESET_DEVICE_RESET_PCIE_LINK = 1
    TENSTORRENT_RESET_DEVICE_CONFIG_WRITE = 2
    A3_STATE_PROP_TIME = 0.03
    POST_RESET_MSG_WAIT_TIME = 2
    POST_RESET_DEV_WAIT_TIME = 0.1
    RESET_RETRY_DELAY = 0.00001
    MSG_TRIGGER_SPI_COPY_LtoR = 0x50
    MSG_TYPE_ARC_STATE3 = 0xA3
    MSG_TYPE_TRIGGER_RESET = 0x56

    def reset_device_ioctl(self, interface_id: int, flags: int) -> bool:
        dev_path = f"/dev/tenstorrent/{interface_id}"
        elapsed = 0
        start_time = time.time()
        while elapsed < self.POST_RESET_DEV_WAIT_TIME:
            try:
                dev_fd = os.open(
                    dev_path, os.O_RDWR | os.O_CLOEXEC
                )  # Raises FileNotFoundError and other appropriate exceptions.
                break
            except FileNotFoundError:
                elapsed = time.time() - start_time
                time.sleep(self.RESET_RETRY_DELAY)
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

        # TODO: FOR BH Check the driver version and bail if link reset cannot be supported
        # check_driver_version(operation="board reset")

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
                f"{CMD_LINE_COLOR.BLUE} Starting PCI link reset on BH devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
            )

        pci_bdf_list = {}

        post_reset_wait = self.POST_RESET_MSG_WAIT_TIME

        # Collect device bdf and trigger resets for all BH chips in order
        # it might take a few seconds before kernel module picks up a device
        elapsed = 0
        start_time = time.time()
        while elapsed < post_reset_wait:
            try:
                for pci_interface in pci_interfaces:
                    # TODO: Make this check fallible
                    chip = PciChip(pci_interface=pci_interface)
                    pci_bdf = chip.get_pci_bdf()
                    pci_bdf_list[pci_interface] = pci_bdf
                    if reset_m3:
                        # A full bmfw upgrade can take awhile
                        post_reset_wait = 60
                        chip.arc_msg(self.MSG_TYPE_TRIGGER_RESET, wait_for_done=False, arg0=3)
                    else:
                        self.reset_device_ioctl(
                            pci_interface, self.TENSTORRENT_RESET_DEVICE_CONFIG_WRITE
                        )
                break
            except FileNotFoundError:
                time.sleep(0.0001)
                elapsed = time.time() - start_time
                continue

        # check command.memory in config space to see if reset bit is set
        # 0 means config space reset happened correctly
        # 1 means config space reset didn't go through correctly

        completed = 0
        failures = 0
        files_map = {
            pci_interface:
                f"/sys/bus/pci/devices/{pci_bdf_list[pci_interface]}/config"
            for pci_interface in pci_interfaces
        }

        elapsed = 0
        start_time = time.time()
        all_start_time = None
        # Map of pci interface to reset bit
        reset_complete_bit_map = {
            pci_interface: False for pci_interface in pci_interfaces
        }
        can_early_exit = False

        print(
            f"Waiting for up to {post_reset_wait} seconds for asic to come back after reset"
        )
        while elapsed < post_reset_wait:
            try:
                for pci_interface, filename in files_map.items():
                    with open(filename, 'rb') as file:
                        command_memory_byte = os.pread(file.fileno(), 1, 4)
                        reset_bit = (
                            int.from_bytes(command_memory_byte, byteorder="little") >> 1
                        ) & 1
                        # Overwrite to store the last value
                        reset_complete_bit_map[pci_interface] = (
                            True if reset_bit == 0 else False
                        )
            except FileNotFoundError:
                time.sleep(self.RESET_RETRY_DELAY)
                elapsed = time.time() - start_time
                continue

            # During bmfw upgrade it may take awhile for the asic to go down after sending the message.
            # So to be safe only early exit if we know the asic has actually gone into reset
            if not all(reset_complete_bit_map.values()):
                can_early_exit = True

            if all(reset_complete_bit_map.values()):
                if can_early_exit:
                    break

            time.sleep(self.RESET_RETRY_DELAY)
            elapsed = time.time() - start_time

        # Check the last value of all the reset bits and report if any of them are not 0
        for pci_interface in pci_interfaces:
            if reset_complete_bit_map[pci_interface]:
                print(
                    f"{CMD_LINE_COLOR.GREEN} Config space reset completed for device {pci_interface} {CMD_LINE_COLOR.ENDC}"
                )
                completed += 1
            else:
                print(
                    f"{CMD_LINE_COLOR.RED} Config space reset not completed for device {pci_interface}! {CMD_LINE_COLOR.ENDC}"
                )
                failures += 1

        for pci_interface in pci_interfaces:
            self.reset_device_ioctl(
                pci_interface, self.TENSTORRENT_RESET_DEVICE_RESTORE_STATE
            )

        if failures > 0:
            sys.exit(failures)

        #  All went well print success message
        # other sanity checks go here
        if not silent:
            print(
                f"{CMD_LINE_COLOR.BLUE} Finishing PCI link reset on BH devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
            )

        pci_chips = [PciChip(pci_interface=interface) for interface in pci_interfaces]
        return pci_chips
