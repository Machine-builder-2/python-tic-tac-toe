from SmartSocket import connections
import random
import time


Event = connections.BasicEvent

SERVER_ADDRESS = (connections.getLocalIP(), 7871)

SERVER = connections.SERVER(SERVER_ADDRESS)
system = connections.ServerClientSystem(SERVER)
print("Server:",system.server)
print(f"Hosting on: {SERVER_ADDRESS[0]}:{SERVER_ADDRESS[1]}")


class Game(object):
    def __init__(self) -> None:
        self.running = False
        self.player_clients = [None, None]
        self.player_turn = 1
        self.board = [[0,0,0],[0,0,0],[0,0,0]]

        self.timeout = 0
    
    def set_players(self, player_1, player_2):
        self.player_clients[0] = player_1
        self.player_clients[1] = player_2
        self.player_turn = random.randint(1,2)
    
    def is_conn_part_of(self, conn):
        return conn==self.player_clients[0][0] or conn==self.player_clients[1][0]

    def conns_connected(self):
        return [self.player_clients[0][0], self.player_clients[1][0]]
    
    def send_to_players(self, system, obj):
        for player_conn in self.conns_connected():
            system.send_to_conn(player_conn, obj)
    
    def swap_turn(self):
        if self.player_turn == 1:
            self.player_turn = 2
        else: 
            self.player_turn = 1
    
    def reset_timeout(self):
        self.timeout = time.time()+25


running_games = []

def find_game_with_player(player_conn):
    found_game = None
    for game in running_games:
        if game.is_conn_part_of(from_c):
            found_game = game
            break
    return found_game


waiting_clients = []


server_running = True
while server_running:

    new_clients, new_messages, disconnected = system.main()

    for new_client in new_clients:
        conn, addr = new_client
        system.send_to_conn(conn, Event('waiting'))
        waiting_clients.append(new_client)
    
    while 1:
        if len(waiting_clients) < 2:
            break

        player_1 = waiting_clients.pop(0)
        player_2 = waiting_clients.pop(0)

        new_game = Game()
        new_game.set_players(player_1, player_2)
        running_games.append(new_game)
        new_game.send_to_players(system, Event('joined'))
        new_game.reset_timeout()

    for msg in new_messages:

        if msg.is_dict:
            msg_o = Event(msg)
            print(f"New message {str(msg_o.event)}")

            event = msg_o.event
            from_c = msg_o.from_conn

            found_game = find_game_with_player(from_c)
            
            try:
                if found_game is not None:
                    if msg_o.is_i('click_tile'):
                        coord = msg_o.get('coord')
                        if coord is not None:
                            player_index = 1 if msg_o.from_conn == found_game.player_clients[0][0] else 2
                            if found_game.player_turn == player_index:
                                # allow the player to make a turn
                                board = found_game.board
                                if board[coord[1]][coord[0]] == 0:
                                    board[coord[1]][coord[0]] = player_index
                                    found_game.send_to_players(system,
                                    Event('update_board', coord=coord, value=player_index))
                                    found_game.swap_turn()
                                    print(f"move made, it is now player {found_game.player_turn}'s turn")
                                    new_game.reset_timeout()
            
            except:
                print("ERROR")

        else:
            print(f"New message: is_dict:{msg.is_dict}, is_pickled:{msg.is_pickled}")

    current_time = time.time()
    end_games = []
    for game in running_games:
        if current_time > game.timeout:
            end_games.append((game, "timeout"),)

    for client in disconnected:
        conn = client[0]
        in_game = find_game_with_player(conn)
        if in_game is not None:
            end_games.append((in_game, 'disconnect'),)

        print(f"Client disconnected {client[1][0]}:{client[1][1]}")
    
    for game,reason in end_games:
        print('end game')

        game.send_to_players(system, Event(reason))

        for client in game.player_clients:
            if client in system.clients:
                if not client in waiting_clients:
                    waiting_clients.append(client)
        
        running_games.remove(game)