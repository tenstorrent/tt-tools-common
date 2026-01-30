# SPDX-FileCopyrightText: © 2024 Tenstorrent Inc.
# SPDX-License-Identifier: Apache-2.0
"""
Test suite for TT-Tools widgets and themes
"""
from typing import List, Tuple
import pytest
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical

from tt_tools_common.ui_common.widgets import (
    TTFooter,
    TTHeader,
    TTDataTable,
    TTMenu,
    TTConfirmBox,
)

from datetime import datetime

TextualKeyBindings = List[Tuple[str, str, str]]


class TTApp(App):
    """A Textual app example to test all tt_textual widgets for TT-Tools."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("b", "test_confirmbox", "Test Confirm Box"),
    ]

    CSS_PATH = "../ui_common/common_style.css"

    def __init__(
        self,
        app_name: str = "TT-App Example",
        app_version: str = "1.0.0",
        key_bindings: TextualKeyBindings = [],
    ) -> None:
        """Initialize the textual app."""
        super().__init__()
        self.app_name = app_name
        self.app_version = app_version

        if key_bindings:
            self.BINDINGS += key_bindings

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        data = {"Menu 1": 1, "Menu 2": 2, "Menu 3": 3}
        yield TTHeader(self.app_name, self.app_version)
        with Horizontal():
            with Vertical():
                yield TTMenu(title="Menu 1", data=data, id="menu_1")
                yield TTMenu(title="Menu 2", data=data, id="menu_2")
            yield TTDataTable(
                title="TT_DATA_TABLE_EXAMPLE",
                header=["Board ID", "Test NOC", "Test PCIE", "Time"],
                id="dt_example",
            )
            yield TTMenu(title="Right Menu", data=data, id="menu_3")
        yield TTFooter()

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        tt_dt = self.get_widget_by_id(id="dt_example")
        tt_dt.dt.add_rows(
            [
                [
                    f"{n}",
                    f"Status {n}",
                    f"This is description {n}",
                    datetime.now().strftime("%b %d %Y %I:%M:%S %p"),
                ]
                for n in range(42)
            ]
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_test_confirmbox(self) -> None:
        """An action to test the confirm box toggle."""
        self.push_screen(TTConfirmBox(text="Are you sure you want to...?"))


@pytest.fixture
def app():
    """Fixture that creates a test app instance."""
    return TTApp()


@pytest.mark.asyncio
async def test_app_creation(app):
    """Test that the app can be created."""
    assert app is not None
    assert app.app_name == "TT-App Example"
    assert app.app_version == "1.0.0"

# TODO: Add Textual tests
