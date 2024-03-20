# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test mobo reset using reset config file
"""
from tt_tools_common.reset_common.galaxy_reset import GalaxyReset
from tt_tools_common.reset_common.wh_reset import WHChipReset
from tt_tools_common.reset_common.reset_utils import (
    parse_reset_input,
)

# UPDATE THIS BEFORE RUNNING
INPUT_FILE = "~/.config/tenstorrent/reset_config.json"
WH_RESET_PCI_NUM = 4


def main():
    # SAMPLE MOBO RESET CONFIG

    # mobo = "mobo-ce-44"
    # credo = ["6:0", "6:1", "7:0", "7:1"]
    # disabled_ports = [
    #     "0:0",
    #     "0:1",
    #     "0:2",
    #     "1:0",
    #     "1:1",
    #     "1:2",
    #     "6:0",
    #     "6:1",
    #     "6:2",
    #     "0:0",
    #     "0:1",
    #     "7:2",
    # ]

    # mobo_dict_list = [{"mobo": mobo, "credo": credo, "disabled_ports": disabled_ports}]
    mobo_dict_list = parse_reset_input(INPUT_FILE)["wh_mobo_reset"]
    mobo_reset_obj = GalaxyReset()
    mobo_reset_obj.warm_reset_mobo(mobo_dict_list)
    # reset_obj = WHChipReset()
    # reset_obj.full_lds_reset(list(range(WH_RESET_PCI_NUM)))


if __name__ == "__main__":
    main()
