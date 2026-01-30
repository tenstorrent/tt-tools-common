# SPDX-FileCopyrightText: © 2026 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

import pytest

from tt_tools_common.utils_common.system_utils import (
    get_size,
    get_driver_version,
    _parse_version_string,
    is_driver_version_at_least
)


def test_get_size():
    """
    Test cases for get_size, which formats number of bytes into a string.
    """
    assert get_size(0) == "0.00 B"
    assert get_size(1024) == "1.00 KB"
    assert get_size(1024*1024) == "1.00 MB"
    assert get_size(1024*1024*1024) == "1.00 GB"
    assert get_size(1024*1024*1024*1024) == "1.00 TB"
    assert get_size(1024*1024*1024*1024*1024) == "1.00 PB"
    # Won't be able to handle 1 exabyte or higher
    assert get_size(1024*1024*1024*1024*1024*1024) == "N/A"
    # Examples from the docstring
    assert get_size(1253656) == "1.20 MB"
    assert get_size(1253656678) == "1.17 GB"


def test_parse_version_string():
    """
    Test cases for _parse_version_string, which parses a Tuple[int, int, int] from a version string.
    Test that a variety of allowed formats are parsed correctly. Test that various error cases raise the
    expected error.
    """
    # Allowed formats
    assert _parse_version_string("1") == (1, 0, 0)
    assert _parse_version_string("1.26") == (1, 26, 0)
    assert _parse_version_string("2.6.0") == (2, 6, 0)
    assert _parse_version_string("2.6.0-rc1") == (2, 6, 0)
    assert _parse_version_string("1.4.0-rc1+build42") == (1, 4, 0)
    assert _parse_version_string("1.2.3+build456") == (1, 2, 3)

    # Error cases
    with pytest.raises(ValueError, match="Version string cannot be empty"):
        _parse_version_string(None)
        _parse_version_string("")
    with pytest.raises(ValueError, match=r"Invalid version format: .*"):
        _parse_version_string(".")
        _parse_version_string(".............")
        _parse_version_string("not a version string")
    with pytest.raises(ValueError, match=r"Version parts must be integers: .*"):
        _parse_version_string("a.b.c")


@pytest.mark.requires_hardware
def test_get_driver_version():
    """
    Test get_driver_version. This reads the current kmd version on the system and tests that it is
    parseable. If it's not parseable, then I expect it to be None (no driver installed).
    """
    driver_version = get_driver_version()
    try:
        _parse_version_string(driver_version)
    except:
        assert driver_version is None


def test_is_driver_version_at_least():
    """Test is_driver_version_at_least. Should return first arg >= second arg."""
    with pytest.raises(ValueError):
        is_driver_version_at_least("a.b.c", "2.0.0")
    assert is_driver_version_at_least("1.34.0", "1.34.0")
    assert is_driver_version_at_least("2.0.0", "1.34.0")
    assert not is_driver_version_at_least("1.34.0", "1.35.0")
