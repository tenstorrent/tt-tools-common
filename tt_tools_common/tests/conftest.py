# SPDX-FileCopyrightText: © 2025 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0

import pytest
from pyluwen import detect_chips


@pytest.fixture()
def devices():
    """Return devices detected on the system."""
    return detect_chips()
