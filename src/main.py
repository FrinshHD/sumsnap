from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from dashboard import Dashboard

class MinecraftServerMonitorApp(App):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Dashboard()  # <-- parentheses to instantiate
        yield Footer()

if __name__ == "__main__":
    MinecraftServerMonitorApp().run()