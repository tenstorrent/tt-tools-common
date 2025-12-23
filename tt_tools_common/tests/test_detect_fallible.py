# SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test suite for detect_chips_fallible
"""
import pytest

from pyluwen import detect_chips
from tt_tools_common.utils_common.tools_utils import detect_chips_with_callback
from tt_tools_common.reset_common.chip_reset import ChipReset


@pytest.fixture
def pci_indices():
    """Fixture that returns list of chip PCI indices"""
    pci_idx = []
    devices = detect_chips()
    for i, dev in enumerate(devices):
        if not dev.is_remote():
            pci_idx.append(i)
    return pci_idx


def test_detect_chips_with_callback(requires_hardware):
    """Test that detect_chips_with_callback returns devices."""
    devices = detect_chips_with_callback()
    assert devices is not None


def test_detect_chips_with_callback_after_reset(pci_indices, requires_hardware):
    """Test detect_chips_with_callback works after WH reset."""
    if not pci_indices:
        pytest.skip("No chips detected")
    
    ChipReset().full_lds_reset(pci_interfaces=pci_indices)
    devices = detect_chips_with_callback()
    assert devices is not None
