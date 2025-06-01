class PlayerInfo:
    def __init__(self, server):
        self.server = server

    def get_connected_players(self):
        # This method should interact with the server to retrieve connected player information
        # For now, we will return a mock list of players
        return [
            {"name": "Player1", "uuid": "uuid-1", "location": "world"},
            {"name": "Player2", "uuid": "uuid-2", "location": "world"},
        ]

    def display_player_info(self):
        players = self.get_connected_players()
        for player in players:
            print(f"Name: {player['name']}, UUID: {player['uuid']}, Location: {player['location']}")