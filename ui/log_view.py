# ui/log_view.py
from datetime import datetime
from textual.widget import Widget
from textual.widgets import Log, Input, Label
from textual.app import ComposeResult
from textual.binding import Binding

_FILTER_CYCLE = ["all", "wifi", "bt", "gps"]
_FILTER_PREFIXES = {
    "wifi": ("[+WIFI]", "[-WIFI]", "[RSSI]"),
    "bt":   ("[+BT]", "[-BT]", "[+BLE]", "[-BLE]"),
    "gps":  ("[GPS]",),
}


class LogScreen(Widget):
    BINDINGS = [
        Binding("f", "cycle_filter", "Filter"),
        Binding("/", "focus_search", "Search"),
        Binding("escape", "clear_search", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self._all_events: list[str] = []
        self._filter = "all"
        self._search = ""

    def compose(self) -> ComposeResult:
        yield Label("filter: all | search: ''", id="log-status")
        yield Input(placeholder="search…", id="search-input")
        yield Log(id="event-log", auto_scroll=True)

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False

    def add_event(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"{timestamp} {message}"
        self._all_events.append(entry)
        if self._matches(entry):
            self.query_one("#event-log", Log).write_line(entry)

    def _matches(self, entry: str) -> bool:
        if self._filter != "all":
            prefixes = _FILTER_PREFIXES.get(self._filter, ())
            if not any(p in entry for p in prefixes):
                return False
        if self._search and self._search.lower() not in entry.lower():
            return False
        return True

    def _rerender(self) -> None:
        log = self.query_one("#event-log", Log)
        log.clear()
        for entry in self._all_events:
            if self._matches(entry):
                log.write_line(entry)

    def _update_status(self) -> None:
        self.query_one("#log-status", Label).update(
            f"filter: {self._filter} | search: '{self._search}'"
        )

    def action_cycle_filter(self) -> None:
        idx = _FILTER_CYCLE.index(self._filter)
        self._filter = _FILTER_CYCLE[(idx + 1) % len(_FILTER_CYCLE)]
        self._rerender()
        self._update_status()

    def action_focus_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.display = True
        search_input.focus()

    def action_clear_search(self) -> None:
        self._search = ""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        search_input.display = False
        self._rerender()
        self._update_status()

    def on_input_changed(self, event: Input.Changed) -> None:
        self._search = event.value
        self._rerender()
        self._update_status()
