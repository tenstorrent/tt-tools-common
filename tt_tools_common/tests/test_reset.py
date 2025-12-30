# SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test suite for chip reset
"""
import pytest

from tt_tools_common.reset_common.chip_reset import ChipReset

@pytest.mark.requires_hardware
def test_full_lds_reset(devices):
    """Test full LDS reset on all detected chips."""
    pci_interfaces = list(range(len(devices)))
    ChipReset().full_lds_reset(pci_interfaces=pci_interfaces)
