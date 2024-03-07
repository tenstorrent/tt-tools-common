# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

"""
This file contains functions used to do a galaxy reset.
"""

import sys
import threading
import requests
import time
from typing import Optional
from tqdm import tqdm

from tt_tools_common.utils_common.system_utils import check_driver_version
from tt_tools_common.reset_common.wh_reset import WHChipReset
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR


class GalaxyReset:
    """Class to perform galaxy reset operations"""

    def threaded_mobo_reset(self, mobo_dict_list, function, args=()):
        """Threaded function to perform mobo reset operations concurrently"""

        class ThreadWrapper(threading.Thread):
            """
            Wrapper class to allow exceptions to be raised from threads,
            needed because exceptions raised in threads will simply cause
            the thread to exit and not stop the program
            """

            def __init__(self, target, args):
                threading.Thread.__init__(self)
                self.target = target
                self.args = args
                self.exc = None

            def run(self):
                try:
                    self.target(*self.args)
                except Exception as e:
                    self.exc = e

        # Thread the function on all mobos
        all_threads = []
        for mobo_dict in mobo_dict_list:
            t = ThreadWrapper(target=function, args=(mobo_dict,) + args)
            all_threads.append(t)
            t.start()

        for t in all_threads:
            t.join()

        # If any exceptions were raised, print them and exit
        exceptions = [t.exc for t in all_threads if t.exc is not None]
        if exceptions:
            for e in exceptions:
                print(e)
            sys.exit(1)

    def mobo_address_generator(self, mobo: str, command: str):
        """Generate url and auth for mobo given a command"""
        url = f"http://{mobo}:8000/{command}"
        auth = ("admin", "admin")
        return url, auth

    def get_server_version(self, mobo):
        # Try to get the server version, but some servers may not have the /about endpoint so defaulting to 0.0.0
        response_url, response_auth = self.mobo_address_generator(mobo, "about")
        try:
            response = requests.get(response_url, auth=response_auth, timeout=30)
            response.raise_for_status()

            response = response.json()
            server_version = tuple(map(int, response["version"].split(".")))
        except Exception:
            server_version = (0, 0, 0)

        return server_version

    def server_communication(
        self,
        post: bool,
        mobo: str,
        command: str,
        data: Optional[dict] = None,
        check_error: bool = True,
    ):
        """Function to communicate with the server and handle errors and exceptions"""
        response_url, response_auth = self.mobo_address_generator(mobo, command)
        if post:
            response = requests.post(response_url, auth=response_auth, json=data)
        else:
            response = requests.get(
                response_url,
                auth=response_auth,
            )

        try:
            exception = None
            response_json = {}  # Initializing just in case...

            # No response for successful shutdown/modules and boot/modules
            if response.text != "":
                response_json = response.json()

            if (
                "error" in response_json
            ):  # Error for boot, shutdown/modules, boot/modules
                exception = f"{mobo} request {command} returned with error {response_json['error']}"
            elif (
                "exception" in response_json and response_json["exception"] is not None
            ):  # Exception for boot/progress
                exception = f"{mobo} request {command} returned with exception {response_json['exception']}"
        except requests.exceptions.HTTPError as e:
            exception = f"{mobo} request {command} failed with HTTP error {e}, response {response.text}"
        except Exception as e:
            # This is somewhat of an unexpected error, so we want to raise it immediately
            raise Exception(
                f"{mobo} request {command} failed with exception {response.text}"
            )
        finally:
            if check_error and exception is not None:
                raise Exception(f"{CMD_LINE_COLOR.RED}{exception}{CMD_LINE_COLOR.ENDC}")

        return response_json

    def credo_boot(self, mobo_dict):
        # Function for booting credos concurrently
        mobo = mobo_dict["mobo"]
        if "credo" in mobo_dict.keys():
            credo_ports = mobo_dict["credo"]
        else:
            print(
                CMD_LINE_COLOR.BLUE,
                f"{mobo} - No credos to be booted, moving on ...",
                CMD_LINE_COLOR.ENDC,
            )
            return
        if "disabled_ports" in mobo_dict.keys():
            disable_ports = mobo_dict["disabled_ports"]
        else:
            disable_ports = []

        server_version = self.get_server_version(mobo)

        # disable_ports is really only a feature for 1.3.2 and above, so if the server version is less than that, then
        # output a message and ignore the disable_ports flag
        boot_data = {"groups": None, "credo": True, "retimer_sel": credo_ports}
        if server_version >= (1, 3, 2):
            boot_data["disable_sel"] = disable_ports
        elif server_version < (1, 3, 2) and disable_ports is not None:
            print(
                f"{CMD_LINE_COLOR.RED}Warning: port disable is only available for server version 1.3.2 and above, ignoring flag for {mobo}{CMD_LINE_COLOR.ENDC}"
            )

        print(CMD_LINE_COLOR.BLUE, f"{mobo} - Booting credo ...", CMD_LINE_COLOR.ENDC)
        self.server_communication(True, mobo, "boot", boot_data)

    def wait_for_boot_complete(self, mobo_dict, mobo_list, timeout=600):
        """Function to wait for boot completion of the server and update progress bar accordingly"""
        mobo = mobo_dict["mobo"]
        # Do a check for the server version, if it is >= 0.3.0, then the boot command is posted and
        # we need to do a while loop to check for boot progress
        server_version = self.get_server_version(mobo)
        if server_version < (0, 3, 0):
            return

        # Derive position from mobo_list
        position = mobo_list.index(mobo)
        progress_bar = tqdm(
            total=100, bar_format="{desc} [{elapsed}]", position=position
        )

        # Get the update percentage and update the progress bar
        time_start = time.time()
        boot_progress = 0.0
        progress_bar.set_description_str(
            f"{mobo} - Waiting for server boot to complete... {boot_progress:6.2f}%"
        )
        while boot_progress < 100.0:
            if time.time() - time_start > timeout:
                raise Exception(
                    f"{CMD_LINE_COLOR.RED}{mobo} - Boot timeout, please power cycle the galaxy and try boot again{CMD_LINE_COLOR.ENDC}"
                )

            response = self.server_communication(False, mobo, "boot/progress")

            boot_progress = float(response["boot_percent"])

            # If the server version is >= 1.3.2, then we have a more verbose display of boot status
            if server_version >= (1, 3, 2):
                extra_info = f" ({response['step']})"
            else:
                extra_info = ""

            progress_bar.set_description_str(
                f"{mobo} - Waiting for server boot to complete... {boot_progress:6.2f}%{extra_info}"
            )
            time.sleep(1)

    def shutdown_modules(self, mobo_dict):
        # Function for shutting down modules concurrently

        mobo = mobo_dict["mobo"]
        print(
            CMD_LINE_COLOR.PURPLE,
            f"{mobo} - Turning off modules ...",
            CMD_LINE_COLOR.ENDC,
        )
        self.server_communication(
            True, mobo, "shutdown/modules", {"groups": None}, check_error=False
        )

    def boot_modules(self, mobo_dict):
        # Function for booting modules concurrently
        mobo = mobo_dict["mobo"]
        print(
            CMD_LINE_COLOR.PURPLE,
            f"{mobo} - Turning on modules ...",
            CMD_LINE_COLOR.ENDC,
        )
        self.server_communication(True, mobo, "boot/modules", {"groups": None})

    def warm_reset_mobo(self, mobo_dict_list):
        """Warm boot mobos in dict list form json file"""
        check_driver_version("boot mobo")

        #  Credo boot if needed
        self.threaded_mobo_reset(mobo_dict_list, self.credo_boot)

        # Poll for boot completion status if needed
        mobo_list = [entry["mobo"] for entry in mobo_dict_list]
        self.threaded_mobo_reset(
            mobo_dict_list, self.wait_for_boot_complete, (mobo_list,)
        )

        # Shutdown modules
        self.threaded_mobo_reset(mobo_dict_list, self.shutdown_modules)

        # Link reset the NB host connected to the mobo
        nb_host_pci_idx_list = []
        for entry in mobo_dict_list:
            if "nb_host_pci_idx" in entry.keys() and entry["nb_host_pci_idx"]:
                nb_host_pci_idx_list.extend(entry["nb_host_pci_idx"])
        if nb_host_pci_idx_list:
            # remove duplicate entries
            nb_host_pci_idx_list = list(set(nb_host_pci_idx_list))
            WHChipReset().full_lds_reset(nb_host_pci_idx_list)

        # Boot modules after reset
        self.threaded_mobo_reset(mobo_dict_list, self.boot_modules)

    def mobo_reset_from_json(self, json_dict):
        """Parse pci_list from reset json and init mobo reset"""
        if "wh_mobo_reset" in json_dict.keys():
            mobo_dict_list = []
            for mobo_dict in json_dict["wh_mobo_reset"]:
                if "MOBO NAME" not in mobo_dict["mobo"]:
                    mobo_dict_list.append(mobo_dict)
            # If any mobos - do the reset
            if mobo_dict_list:
                self.warm_reset_mobo(mobo_dict_list)
