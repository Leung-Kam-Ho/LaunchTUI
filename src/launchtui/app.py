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


class LaunchTUIApp(App):
    """Textual UI for managing launch daemons"""

    CSS = """
    .container {
        height: 100%;
    }
    
    .left-panel {
        width: 80;
        height: 100%;
        border-right: solid $primary;
    }
    
    .right-panel {
        width: 1fr;
        height: 100%;
        padding: 1;
    }
    
    VerticalScroll {
        height: 100%;
    }
    
    .controls {
        height: 3;
        margin-bottom: 1;
    }
    
    .create-controls {
        height: 3;
        margin-top: 1;
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
        Binding("c", "clear_logs", "Clear Logs"),
        Binding("o", "open_folder", "Open Folder"),
        Binding("i", "open_editor", "Open Editor"),
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
                    yield Input(placeholder="Search daemons...", id="search")
                    yield DataTable(id="daemon_table", cursor_type="row")
                    yield Label("Create")
                    with Horizontal(classes="create-controls"):
                        yield Button("Agent", id="create_agent_btn", variant="success")
                        yield Button(
                            "Daemon", id="create_daemon_btn", variant="warning"
                        )

                with Vertical(classes="right-panel"):
                    with Horizontal(classes="controls"):
                        yield Button("Start", id="start_btn", variant="success")
                        yield Button("Stop", id="stop_btn", variant="error")
                        yield Button("Restart", id="restart_btn", variant="default")
                        yield Button("Clear Logs", id="clear_btn", variant="warning")
                        yield Button("Refresh", id="refresh_btn", variant="primary")

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
        elif button_id == "clear_btn":
            self.clear_logs()
        elif button_id == "create_agent_btn":
            self.create_agent()
        elif button_id == "create_daemon_btn":
            self.create_system_daemon()
        elif button_id == "refresh_btn":
            self.load_daemons()

    def filter_daemons(self, search_term: str) -> None:
        """Filter daemons based on search term"""
        table = self.query_one("#daemon_table", DataTable)
        table.clear()

        search_term = search_term.lower()
        self.filtered_daemons = []

        for daemon in self.daemons:
            if search_term in daemon["label"].lower():
                self.filtered_daemons.append(daemon)
                table.add_row(
                    daemon["label"],
                    daemon["status"],
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

    def action_clear_logs(self) -> None:
        """Action to clear logs"""
        self.clear_logs()

    def action_open_folder(self) -> None:
        """Action to open daemon folder in Finder"""
        self.open_folder()

    def action_open_editor(self) -> None:
        """Action to open plist file in editor"""
        self.open_editor()

    def clear_logs(self) -> None:
        """Clear the content of .err and .out files for the selected daemon"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        plist_data = self.selected_daemon["plist_data"]
        cleared_files = []

        try:
            # Clear stdout file if configured
            if "StandardOutPath" in plist_data:
                stdout_path = plist_data["StandardOutPath"]
                if os.path.exists(stdout_path):
                    with open(stdout_path, "w") as f:
                        f.truncate(0)
                    cleared_files.append(stdout_path)

            # Clear stderr file if configured
            if "StandardErrorPath" in plist_data:
                stderr_path = plist_data["StandardErrorPath"]
                if os.path.exists(stderr_path):
                    with open(stderr_path, "w") as f:
                        f.truncate(0)
                    cleared_files.append(stderr_path)

            if cleared_files:
                self.update_status(f"Cleared logs: {', '.join(cleared_files)}")
                # Refresh the log display
                self.show_daemon_details()
            else:
                self.update_status("No log files found to clear")

        except PermissionError:
            self.update_status("Permission denied clearing log files")
        except Exception as e:
            self.update_status(f"Error clearing logs: {str(e)}")

    def open_folder(self) -> None:
        """Open the folder containing the selected daemon's plist file in Finder"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        try:
            daemon_path = self.selected_daemon["path"]
            folder_path = os.path.dirname(daemon_path)

            # Open the folder in Finder
            subprocess.run(["open", folder_path], check=True, timeout=5)
            self.update_status(f"Opened folder: {folder_path}")
        except subprocess.CalledProcessError as e:
            self.update_status(f"Failed to open folder: {e}")
        except Exception as e:
            self.update_status(f"Error opening folder: {str(e)}")

    def open_editor(self) -> None:
        """Open the selected daemon's plist file in the default text editor"""
        if not self.selected_daemon:
            self.update_status("No daemon selected")
            return

        try:
            plist_path = self.selected_daemon["path"]

            # Open the file with the default text editor
            subprocess.run(["open", "-t", plist_path], check=True, timeout=5)
            self.update_status(f"Opened {os.path.basename(plist_path)} in editor")
        except subprocess.CalledProcessError as e:
            self.update_status(f"Failed to open editor: {e}")
        except Exception as e:
            self.update_status(f"Error opening editor: {str(e)}")

    def create_agent(self) -> None:
        """Create a new launch agent plist file"""
        try:
            # Default to user's LaunchAgents directory for new agents
            default_path = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(default_path, exist_ok=True)

            # Generate a unique filename
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            filename = f"com.user.agent.{unique_id}.plist"
            filepath = os.path.join(default_path, filename)

            # Create a basic plist template
            plist_template = {
                "Label": f"com.user.agent.{unique_id}",
                "ProgramArguments": ["/bin/bash", "-c", "echo 'Hello from agent'"],
                "RunAtLoad": False,
                "KeepAlive": False,
                "StandardOutPath": f"/tmp/com.user.agent.{unique_id}.out",
                "StandardErrorPath": f"/tmp/com.user.agent.{unique_id}.err",
            }

            # Write the plist file
            with open(filepath, "wb") as f:
                plistlib.dump(plist_template, f)

            self.update_status(f"Created new agent: {filename}")

            # Refresh the daemon list
            self.load_daemons()

            # Open the folder for the user to edit the file
            subprocess.run(["open", default_path], check=True, timeout=5)

        except Exception as e:
            self.update_status(f"Error creating agent: {str(e)}")

    def create_system_daemon(self) -> None:
        """Create a new system launch daemon plist file"""
        try:
            # Use system LaunchDaemons directory for new daemons
            default_path = "/Library/LaunchDaemons"

            # Check if we have write permissions
            if not os.access(default_path, os.W_OK):
                self.update_status(
                    f"Need sudo access to create daemon in {default_path}"
                )
                return

            # Generate a unique filename
            import uuid

            unique_id = str(uuid.uuid4())[:8]
            filename = f"com.system.daemon.{unique_id}.plist"
            filepath = os.path.join(default_path, filename)

            # Create a basic plist template for system daemon
            plist_template = {
                "Label": f"com.system.daemon.{unique_id}",
                "ProgramArguments": [
                    "/bin/bash",
                    "-c",
                    "echo 'Hello from system daemon'",
                ],
                "RunAtLoad": False,
                "KeepAlive": False,
                "StandardOutPath": f"/var/log/com.system.daemon.{unique_id}.out",
                "StandardErrorPath": f"/var/log/com.system.daemon.{unique_id}.err",
                "UserName": "root",
                "GroupName": "wheel",
            }

            # Write the plist file
            with open(filepath, "wb") as f:
                plistlib.dump(plist_template, f)

            self.update_status(f"Created new system daemon: {filename}")

            # Refresh the daemon list
            self.load_daemons()

            # Open the folder for the user to edit the file
            subprocess.run(["open", default_path], check=True, timeout=5)

        except Exception as e:
            self.update_status(f"Error creating system daemon: {str(e)}")


def main():
    app = LaunchTUIApp()
    app.run()


if __name__ == "__main__":
    main()
