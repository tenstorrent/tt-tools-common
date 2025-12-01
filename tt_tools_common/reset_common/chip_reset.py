# SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains functions used to do a PCIe level reset for Blackhole or Wormhole chip.
"""

import os
import sys
import time
import fcntl
import struct
import glob
import subprocess
from enum import IntEnum
from typing import List
from pyluwen import PciChip
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR
import threading
from tt_tools_common.utils_common.system_utils import (
    check_driver_version,
    get_host_info,
)

class IoctlResetFlags(IntEnum):
    RESTORE_STATE = 0
    RESET_PCIE_LINK = 1
    CONFIG_WRITE = 2
    USER_RESET = 3
    ASIC_RESET = 4
    ASIC_DMC_RESET = 5
    POST_RESET = 6

def check_xen_hvm() -> bool:
    """Check if the system is a Xen HVM guest"""
    is_xen_hvm = False
    try:
        with open("/sys/hypervisor/type", "r") as f:
            hypervisor_type = f.read().strip()
        with open("/sys/hypervisor/guest_type", "r") as f:
            guest_type = f.read().strip()
        if hypervisor_type == "xen" and guest_type == "HVM":
            is_xen_hvm = True
    except FileNotFoundError:
        # One or both files do not exist
        pass
    except OSError:
        # Other OS-related errors (e.g., permission denied)
        pass
    # All other types of errors should throw an exception
    return is_xen_hvm

class ChipReset:
    """Class to perform a chip-level reset on WH and BH PCIe boards"""

    # magic numbers for reset
    TENSTORRENT_IOCTL_MAGIC = 0xFA
    TENSTORRENT_IOCTL_RESET_DEVICE = (TENSTORRENT_IOCTL_MAGIC << 8) | 6

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

    def wait_for_device_to_reappear(self, bdf: str, timeout: int = 10) -> int:
        print(
            CMD_LINE_COLOR.BLUE,
            f"Waiting for devices to reappear on pci bus...",
            CMD_LINE_COLOR.ENDC,)
        deadline = time.time() + timeout
        device_reappeared = False

        while time.time() < deadline and not device_reappeared:
            matches = glob.glob(f"/sys/bus/pci/devices/{bdf}/tenstorrent/tenstorrent!*")
            if matches:
                interface_id = int(os.path.basename(matches[0]).replace("tenstorrent!", ""))
                dev_path = f"/dev/tenstorrent/{interface_id}"
                if os.path.exists(dev_path):
                    device_reappeared = True

        if not device_reappeared:
            print(
                CMD_LINE_COLOR.RED,
                f"Timeout waiting for device at PCI index {interface_id} to reappear.",
                CMD_LINE_COLOR.ENDC,
            )
            sys.exit(1)

        return interface_id


    def full_lds_reset(
        self, pci_interfaces: List[int], reset_m3: bool = False, silent: bool = False, m3_delay: int = 20
    ) -> List[PciChip]:
        """Performs a full LDS reset of a list of chips. Xenstore filename is only used in Xen HVM mode."""

        # Check the driver version and bail if reset cannot be supported
        check_driver_version(operation="reset", minimum_required_version_str="2.4.1")

        # Due to how Arm systems deal with PCIe device rescans, WH device resets don't work on that platform.
        # Check for platform and bail if it's Arm
        platform = get_host_info()["Platform"]
        if platform.startswith("arm") or platform.startswith("aarch"):
            print(
                CMD_LINE_COLOR.RED,
                "Cannot perform board reset on Arm systems, please reboot the system to reset the boards. Exiting...",
                CMD_LINE_COLOR.ENDC,
            )
            sys.exit(1)

        # Remove duplicates from the input list of PCI interfaces
        pci_interfaces = list(set(pci_interfaces))
        if not silent:
            print(
                f"{CMD_LINE_COLOR.BLUE} Starting reset on devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
            )

        bdf_list = []

        for pci_interface in pci_interfaces:
            chip = PciChip(pci_interface=pci_interface)
            bdf = chip.get_pci_bdf()
            bdf_list.append(bdf)
            # Force garbage collection of the chip object to close any open file descriptors
            # This is necessary for dockerized containers
            del chip

        # check if the system is a Xen system
        xenstore_filenames = []
        if check_xen_hvm():
            # Validate and remember users sudo credentials for 5min
            print(
            f"{CMD_LINE_COLOR.YELLOW} User needs sudo privileges to write to xenstore. You may be prompted for your password. It will be cached for 5 minutes. {CMD_LINE_COLOR.ENDC}"
            )
            subprocess.run(["sudo", "-v"])
            # Run the subprocess with sudo privileges
            for pci_bdf in bdf_list:
                # Write 1 to xenstore to notify host that reset is starting.
                bdf_parts = pci_bdf.split(":")
                xenstore_filename = f"pci_hard_reset/{bdf_parts[1]}_{bdf_parts[2].split('.')[0]}-{bdf_parts[2].split('.')[1]}"
                xenstore_filenames.append(xenstore_filename)
                print(
                    f"{CMD_LINE_COLOR.PURPLE} Xen HVM system detected, writing 1 to Xenstore file {xenstore_filename} to indicate reset start.{CMD_LINE_COLOR.ENDC}"
                )
                result = subprocess.run(
                    ["sudo", "xenstore-write", f"{xenstore_filename}", "1"],
                    capture_output=True,
                    text=True
                )
                # Check the result
                if result.returncode != 0:
                    print(
                        f"{CMD_LINE_COLOR.RED} Failed to write to xenstore. Error: {result.stderr}. Please notify your system administrator about this. Still proceeding with reset ... {CMD_LINE_COLOR.ENDC}"
                    )

        for pci_interface in pci_interfaces:
            if not self.reset_device_ioctl(pci_interface, IoctlResetFlags.RESET_PCIE_LINK):
                print(
                    CMD_LINE_COLOR.YELLOW,
                    f"Warning: Secondary bus reset not completed for device at PCI index {pci_interface}. Continuing with reset.",
                    CMD_LINE_COLOR.ENDC
                )


        for pci_interface in pci_interfaces:
            if reset_m3:
                reset_flag = IoctlResetFlags.ASIC_DMC_RESET
            else:
                reset_flag = IoctlResetFlags.ASIC_RESET

            self.reset_device_ioctl(pci_interface, reset_flag)

        if check_xen_hvm():
            # Wait time of 5min after which we will timeout waiting for xenstore files to be removed
            xen_wait_time = 300
            if xenstore_filenames == []:
                print(
                    f"{CMD_LINE_COLOR.RED} No xenstore filenames found for Xen HVM reset - did we write to them?? Exiting... {CMD_LINE_COLOR.ENDC}"
                )
                sys.exit(1)
            # Check if xenstore files no longer exist, in parallel threads
            # Validate and remember users sudo credentials for 5min
            print(
            f"{CMD_LINE_COLOR.YELLOW} Revalidating sudo access... You might be prompted for your sudo password. {CMD_LINE_COLOR.ENDC}"
            )
            subprocess.run(["sudo", "-v"])
            def wait_for_xenstore_removal(xenstore_filename):
                print(
                    f"{CMD_LINE_COLOR.BLUE} Waiting for Xenstore file {xenstore_filename} to be removed by the host... {CMD_LINE_COLOR.ENDC}"
                )
                deadline = time.time() + xen_wait_time
                while time.time() < deadline:
                    result = subprocess.run(
                        ["sudo", "xenstore-read", f"{xenstore_filename}"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode != 0:
                        print(
                            f"{CMD_LINE_COLOR.GREEN} Xenstore file {xenstore_filename} has been removed by the host. Continuing... {CMD_LINE_COLOR.ENDC}"
                        )
                        return
                    time.sleep(1)
                print(
                    f"{CMD_LINE_COLOR.RED} Timeout waiting for xenstore file {xenstore_filename} to be removed. Exiting... {CMD_LINE_COLOR.ENDC}"
                )
                sys.exit(1)

            threads = []
            for xenstore_filename in xenstore_filenames:
                t = threading.Thread(target=wait_for_xenstore_removal, args=(xenstore_filename,))
                t.start()
                threads.append(t)
            for t in threads:
                t.join()


        post_reset_wait = m3_delay if reset_m3 else max(2, 0.4 * len(pci_interfaces))
        print(
            CMD_LINE_COLOR.BLUE,
            f"Waiting for {post_reset_wait} seconds for potential hotplug removal.",
            CMD_LINE_COLOR.ENDC
        )
        time.sleep(post_reset_wait)

        for pci_interface,bdf in zip(pci_interfaces,bdf_list):
            new_id = self.wait_for_device_to_reappear(bdf)

            if self.reset_device_ioctl(new_id, IoctlResetFlags.POST_RESET):
                print(
                    f"{CMD_LINE_COLOR.GREEN} Reset successfully completed for device at PCI index {pci_interface}. {CMD_LINE_COLOR.ENDC}"
                )
            else:
                print(
                    f"{CMD_LINE_COLOR.RED} Post-reset actions did not complete successfully for device at PCI index {pci_interface}. {CMD_LINE_COLOR.ENDC}"
                )
                sys.exit(1)

        # All went well print success message
        # other sanity checks go here
        if not silent:
            print(
                f"{CMD_LINE_COLOR.BLUE} Finishing reset on devices at PCI indices: {str(pci_interfaces)[1:-1]} {CMD_LINE_COLOR.ENDC}"
            )

        pci_chips = [PciChip(pci_interface=interface) for interface in pci_interfaces]
        return pci_chips
