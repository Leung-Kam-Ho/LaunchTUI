#!/usr/bin/env python3
import plistlib
import subprocess
import os
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Static,
    Input,
    Button,
    Label,
)
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.binding import Binding
from textual.reactive import reactive


class DaemonDetails(Static):
    """Widget to display daemon details"""

    def show_daemon(self, daemon):
        if not daemon:
            self.update("No daemon selected")
            return

        details = f"[bold]Label:[/bold] {daemon['label']}\n"
        details += f"[bold]Status:[/bold] {daemon['status']}\n"
        details += f"[bold]Path:[/bold] {daemon['path']}\n"
        details += f"[bold]Program:[/bold] {daemon['program']}\n\n"

        # Add plist details
        plist_data = daemon["plist_data"]
        if "RunAtLoad" in plist_data:
            details += f"[bold]RunAtLoad:[/bold] {plist_data['RunAtLoad']}\n"
        if "KeepAlive" in plist_data:
            details += f"[bold]KeepAlive:[/bold] {plist_data['KeepAlive']}\n"
        if "StandardOutPath" in plist_data:
            details += (
                f"[bold]StandardOutPath:[/bold] {plist_data['StandardOutPath']}\n"
            )
        if "StandardErrorPath" in plist_data:
            details += (
                f"[bold]StandardErrorPath:[/bold] {plist_data['StandardErrorPath']}\n"
            )
        if "WorkingDirectory" in plist_data:
            details += (
                f"[bold]WorkingDirectory:[/bold] {plist_data['WorkingDirectory']}\n"
            )

        if "ProgramArguments" in plist_data:
            details += f"\n[bold]ProgramArguments:[/bold]\n"
            for arg in plist_data["ProgramArguments"]:
                details += f"  {arg}\n"

        self.update(details)


class LogContent(Static):
    """Widget to display stdout/stderr log content"""

    def show_logs(self, daemon):
        if not daemon:
            self.update("No daemon selected")
            return

        plist_data = daemon["plist_data"]
        content = "[bold]Log Content:[/bold]\n\n"

        # Display stdout content if available
        if "StandardOutPath" in plist_data:
            stdout_path = plist_data["StandardOutPath"]
            content += f"[bold]Standard Output ({stdout_path}):[/bold]\n"
            stdout_content = self.read_log_file(stdout_path)
            if stdout_content:
                content += stdout_content
            else:
                content += "No content or file not accessible\n"
            content += "\n"

        # Display stderr content if available
        if "StandardErrorPath" in plist_data:
            stderr_path = plist_data["StandardErrorPath"]
            content += f"[bold]Standard Error ({stderr_path}):[/bold]\n"
            stderr_content = self.read_log_file(stderr_path)
            if stderr_content:
                content += stderr_content
            else:
                content += "No content or file not accessible\n"
            content += "\n"

        # If no log paths configured
        if (
            "StandardOutPath" not in plist_data
            and "StandardErrorPath" not in plist_data
        ):
            content += "No StandardOutPath or StandardErrorPath configured in plist\n"

        self.update(content)

    def read_log_file(self, file_path: str) -> str:
        """Read content from a log file, returning last 50 lines if file exists"""
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    # Return last 50 lines to avoid overwhelming display
                    if len(lines) > 50:
                        lines = lines[-50:]
                        return f"[dim]... showing last 50 lines ...[/dim]\n" + "".join(
                            lines
                        )
                    else:
                        return "".join(lines)
            else:
                return f"File not found: {file_path}"
        except PermissionError:
            return f"Permission denied accessing: {file_path}"
        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"


class LaunchDaemonApp(App):
    """Textual UI for managing launch daemons"""

    CSS = """
    .container {
        height: 100%;
    }
    
    .left-panel {
        width: 40%;
        height: 100%;
        border-right: solid $primary;
    }
    
    .right-panel {
        width: 60%;
        height: 100%;
        padding: 1;
    }
    
    VerticalScroll {
        height: 100%;
    }
    
    .controls {
        height: 3;
        dock: top;
    }
    
    .search {
        height: 3;
        dock: top;
    }
    
    DataTable {
        height: 1fr;
    }
    
    DaemonDetails {
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    LogContent {
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    .status {
        height: 3;
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "start_daemon", "Start"),
        Binding("t", "stop_daemon", "Stop"),
        Binding("e", "restart_daemon", "Restart"),
    ]

    selected_daemon = reactive(None)

    def __init__(self):
        super().__init__()
        self.launch_daemon_paths = [
            "/System/Library/LaunchDaemons",
            "/Library/LaunchDaemons",
            os.path.expanduser("~/Library/LaunchAgents"),
        ]
        self.daemons = []
        self.filtered_daemons = []
        self.status_message = "Ready"

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(classes="container"):
            with Horizontal():
                with Vertical(classes="left-panel"):
                    with Horizontal(classes="search"):
                        yield Label("Filter:")
                        yield Input(placeholder="Search daemons...", id="search")

                    yield DataTable(id="daemon_table", cursor_type="row")

                    with Horizontal(classes="controls"):
                        yield Button("Start", id="start_btn", variant="success")
                        yield Button("Stop", id="stop_btn", variant="error")
                        yield Button("Restart", id="restart_btn")
                        yield Button("Refresh", id="refresh_btn", variant="primary")

                with Vertical(classes="right-panel"):
                    with VerticalScroll():
                        yield Label("Details", id="details_label")
                        yield DaemonDetails("No daemon selected", id="details")
                        yield Label("Log Output", id="logs_label")
                        yield LogContent("No daemon selected", id="logs")

        yield Label(f"Status: {self.status_message}", id="status", classes="status")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app when mounted"""
        table = self.query_one("#daemon_table", DataTable)
        table.add_column("Label", key="label")
        table.add_column("Status", key="status")
        table.add_column("Program", key="program")

        search_input = self.query_one("#search", Input)
        search_input.focus()

        self.load_daemons()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes"""
        if event.input.id == "search":
            self.filter_daemons(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle daemon selection"""
        if event.row_key is not None and event.row_key.value is not None:
            index = int(event.row_key.value)
            self.selected_daemon = (
                self.filtered_daemons[index]
                if self.filtered_daemons
                else self.daemons[index]
            )
            self.show_daemon_details()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "start_btn":
            self.start_daemon()
        elif button_id == "stop_btn":
            self.stop_daemon()
        elif button_id == "restart_btn":
            self.restart_daemon()
        elif button_id == "refresh_btn":
            self.load_daemons()

    def filter_daemons(self, search_term: str) -> None:
        """Filter daemons based on search term"""
        table = self.query_one("#daemon_table", DataTable)
        table.clear()

        search_term = search_term.lower()
        self.filtered_daemons = []

        for daemon in self.daemons:
            if (
                search_term in daemon["label"].lower()
                or search_term in daemon["program"].lower()
            ):
                self.filtered_daemons.append(daemon)
                table.add_row(
                    daemon["label"],
                    daemon["status"],
                    daemon["program"],
                    key=str(len(self.filtered_daemons) - 1),
                )

    def load_daemons(self) -> None:
        """Load all daemons from the configured paths"""
        self.daemons = []
        table = self.query_one("#daemon_table", DataTable)
        table.clear()

        for path in self.launch_daemon_paths:
            if os.path.exists(path):
                try:
                    for item in os.listdir(path):
                        if item.endswith(".plist") and not item.startswith("com.apple"):
                            full_path = os.path.join(path, item)
                            daemon_info = self.parse_plist(full_path)
                            if daemon_info:
                                self.daemons.append(daemon_info)
                                table.add_row(
                                    daemon_info["label"],
                                    daemon_info["status"],
                                    daemon_info["program"],
                                    key=str(len(self.daemons) - 1),
                                )
                except PermissionError:
                    self.update_status(f"Permission denied accessing {path}")
                except Exception as e:
                    self.update_status(f"Error loading {path}: {str(e)}")

        self.update_status(f"Loaded {len(self.daemons)} daemons")
        self.filter_daemons(self.query_one("#search", Input).value)

    def parse_plist(self, plist_path: str) -> dict | None:
        """Parse a plist file and extract daemon information"""
        try:
            with open(plist_path, "rb") as f:
                plist_data = plistlib.load(f)

            label = plist_data.get("Label", os.path.basename(plist_path))
            program = plist_data.get(
                "Program",
                plist_data.get("ProgramArguments", [""])[0]
                if "ProgramArguments" in plist_data
                else "",
            )

            status = self.get_service_status(label)

            return {
                "label": label,
                "path": plist_path,
                "program": program,
                "status": status,
                "plist_data": plist_data,
            }
        except Exception as e:
            print(f"Error parsing {plist_path}: {e}")
            return None

    def get_service_status(self, label: str) -> str:
        """Get the status of a service using launchctl"""
        try:
            result = subprocess.run(
                ["launchctl", "list", label], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        pid = parts[0]
                        if pid == "-":
                            return "Stopped"
                        else:
                            return f"Running (PID: {pid})"
            return "Unknown"
        except Exception:
            return "Unknown"

    def show_daemon_details(self) -> None:
        """Display details of the selected daemon"""
        if self.selected_daemon:
            details = self.query_one("#details", DaemonDetails)
            details.show_daemon(self.selected_daemon)

            logs = self.query_one("#logs", LogContent)
            logs.show_logs(self.selected_daemon)

    def update_status(self, message: str) -> None:
        """Update the status bar"""
        self.status_message = message
        status_label = self.query_one("#status", Label)
        status_label.update(f"Status: {message}")

    def start_daemon(self) -> None:
        """Start the selected daemon"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        try:
            label = self.selected_daemon["path"]
            subprocess.run(
                ["launchctl", "bootstrap", "system", label], check=True, timeout=10
            )
            self.update_status(f"Started {label}")
            self.load_daemons()  # Refresh status
        except subprocess.CalledProcessError as e:
            self.update_status(f"Failed to start {self.selected_daemon['label']}: {e}")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")

    def stop_daemon(self) -> None:
        """Stop the selected daemon"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        try:
            label = self.selected_daemon["path"]
            subprocess.run(
                ["launchctl", "bootout", "system", label], check=True, timeout=10
            )
            self.update_status(f"Stopped {label}")
            self.load_daemons()  # Refresh status
        except subprocess.CalledProcessError as e:
            self.update_status(f"Failed to stop {self.selected_daemon['label']}: {e}")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")

    def restart_daemon(self) -> None:
        """Restart the selected daemon"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        try:
            label = self.selected_daemon["path"]
            subprocess.run(
                ["launchctl", "bootout", "system", label], check=True, timeout=10
            )
            subprocess.run(
                ["launchctl", "bootstrap", "system", label], check=True, timeout=10
            )
            self.update_status(f"Restarted {label}")
            self.load_daemons()  # Refresh status
        except subprocess.CalledProcessError as e:
            self.update_status(
                f"Failed to restart {self.selected_daemon['label']}: {e}"
            )
        except Exception as e:
            self.update_status(f"Error: {str(e)}")

    def action_refresh(self) -> None:
        """Action to refresh daemons"""
        self.load_daemons()

    def action_start_daemon(self) -> None:
        """Action to start daemon"""
        self.start_daemon()

    def action_stop_daemon(self) -> None:
        """Action to stop daemon"""
        self.stop_daemon()

    def action_restart_daemon(self) -> None:
        """Action to restart daemon"""
        self.restart_daemon()


def main():
    app = LaunchDaemonApp()
    app.run()


if __name__ == "__main__":
    main()
