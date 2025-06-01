from textual.app import App
from textual.widgets import Static, ScrollView
import os

class LogsViewer(Static):
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = log_file_path
        self.log_lines = []

    def watch_logs(self):
        if os.path.exists(self.log_file_path):
            with open(self.log_file_path, 'r') as log_file:
                self.log_lines = log_file.readlines()
                self.update_display()

    def update_display(self):
        self.update("\n".join(self.log_lines[-20:]))  # Display the last 20 lines

    async def on_mount(self):
        self.set_interval(1, self.watch_logs)  # Check for new logs every second

class LogsViewerApp(App):
    def compose(self):
        log_file_path = "path/to/your/minecraft/server/logs/latest.log"  # Update with actual log file path
        yield ScrollView(LogsViewer(log_file_path))

if __name__ == "__main__":
    LogsViewerApp.run()