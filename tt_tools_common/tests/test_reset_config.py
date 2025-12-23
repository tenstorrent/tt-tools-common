# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test for generating reset config file
"""
import os
import pytest

from tt_tools_common.reset_common.reset_utils import (
    generate_reset_logs,
    parse_reset_input,
    ResetType
)


def test_parse_reset_input_pci_indices():
    """Test parsing comma-separated PCI indices."""
    result = parse_reset_input(["0,1,2,3"])
    assert result.type == ResetType.ID_LIST
    assert result.value == [0, 1, 2, 3]


def test_parse_reset_input_single_index():
    """Test parsing single PCI index."""
    result = parse_reset_input(["0"])
    assert result.value == [0]
    assert result.type == ResetType.ID_LIST


def test_parse_reset_input_all():
    """Test parsing 'all' input."""
    result = parse_reset_input([])
    assert result.type == ResetType.ALL
    
    result = parse_reset_input(["all"])
    assert result.type == ResetType.ALL


def test_generate_reset_logs(devices, requires_hardware):
    """Test generating default reset logs."""
    file_path = generate_reset_logs(devices)
    assert file_path is not None
    assert os.path.exists(file_path)
        
    # Verify file can be parsed
    parsed = parse_reset_input([file_path])
    assert parsed is not None
    assert parsed.type == ResetType.CONFIG_JSON
