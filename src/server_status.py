class ServerStatus:
    def __init__(self, server_address):
        self.server_address = server_address
        self.status = None
        self.ping = None
        self.tps = None

    def query_status(self):
        # Logic to query the Minecraft server for its current status
        # This would typically involve sending a request to the server
        # and parsing the response to update self.status, self.ping, and self.tps
        pass

    def get_status(self):
        return {
            "status": self.status,
            "ping": self.ping,
            "tps": self.tps
        }