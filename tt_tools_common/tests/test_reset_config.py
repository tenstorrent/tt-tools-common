# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test for generating reset config file
"""
import json
from pyluwen import detect_chips
from tt_tools_common.reset_common.reset_utils import (
    generate_reset_logs,
    parse_reset_input,
)
from tt_tools_common.ui_common.themes import CMD_LINE_COLOR


def main():
    devices = detect_chips()
    file = generate_reset_logs(devices)
    print(
        CMD_LINE_COLOR.BLUE,
        f"Generated default reset config file for this host: {file}",
        CMD_LINE_COLOR.ENDC,
    )

    file = generate_reset_logs(devices, "test_reset_config.json")
    print(
        CMD_LINE_COLOR.BLUE,
        f"Generated input reset config file for this host: {file}",
        CMD_LINE_COLOR.ENDC,
    )
    print(
        CMD_LINE_COLOR.PURPLE,
        f"Parsed output: {file}",
        CMD_LINE_COLOR.ENDC,
    )
    json_data = parse_reset_input(file)
    json_formatted_str = json.dumps(json_data, indent=2)
    print(json_formatted_str)
    nb_host_pci_idx_list = []
    for entry in json_data["wh_mobo_reset"]:
        if "nb_host_pci_idx" in entry.keys() and entry["nb_host_pci_idx"]:
            nb_host_pci_idx_list.extend(entry["nb_host_pci_idx"])
    print("nb_host_pci_idx_list: ", list(set(nb_host_pci_idx_list)))
    pci_idx = parse_reset_input("0,1,2,3")
    print(
        CMD_LINE_COLOR.PURPLE,
        f"Example pci index input: {file}",
        CMD_LINE_COLOR.ENDC,
    )
    print(pci_idx)


if __name__ == "__main__":
    main()
