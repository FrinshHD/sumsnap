class ServerManagement:
    def __init__(self, server):
        self.server = server

    def start_server(self):
        # Logic to start the Minecraft server
        print("Starting the server...")
        # Example: self.server.start()

    def stop_server(self):
        # Logic to stop the Minecraft server
        print("Stopping the server...")
        # Example: self.server.stop()

    def restart_server(self):
        # Logic to restart the Minecraft server
        print("Restarting the server...")
        self.stop_server()
        self.start_server()

    def toggle_whitelist(self):
        # Logic to toggle the server's whitelist
        print("Toggling the whitelist...")
        # Example: self.server.toggle_whitelist()