from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mahjong_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

class GomokuGame:
    def __init__(self):
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self.players = {}
        self.player_list = []
        self.current_turn = 0
        self.game_started = False
        self.move_history = []
        
    def start_game(self):
        if len(self.players) != 2:
            return False, "需要正好2个玩家"
        
        self.board = [[' ' for _ in range(15)] for _ in range(15)]
        self.player_list = list(self.players.keys())
        self.current_turn = 0
        self.game_started = True
        self.move_history = []
        
        self.players[self.player_list[0]]['symbol'] = '●'
        self.players[self.player_list[1]]['symbol'] = '○'
        
        return True, f"游戏开始！{self.players[self.player_list[0]]['name']}(●) vs {self.players[self.player_list[1]]['name']}(○)"
    
    def place_stone(self, player_id, row, col):
        if not self.game_started:
            return False, "游戏还未开始", None
        
        current_player_id = self.player_list[self.current_turn]
        if player_id != current_player_id:
            return False, f"现在是 {self.players[current_player_id]['name']} 的回合", None
        
        if row < 0 or row >= 15 or col < 0 or col >= 15:
            return False, "坐标超出范围 (0-14)", None
        
        if self.board[row][col] != ' ':
            return False, "该位置已有棋子", None
        
        symbol = self.players[player_id]['symbol']
        self.board[row][col] = symbol
        self.move_history.append((row, col, symbol))
        
        winner = self.check_winner(row, col, symbol)
        if winner:
            return True, f"恭喜 {self.players[player_id]['name']} 获胜！", 'win'
        
        self.current_turn = 1 - self.current_turn
        next_player = self.players[self.player_list[self.current_turn]]['name']
        return True, f"落子成功！轮到 {next_player}", None
    
    def check_winner(self, row, col, symbol):
        directions = [(0,1), (1,0), (1,1), (1,-1)]
        for dr, dc in directions:
            count = 1
            for direction in [1, -1]:
                r, c = row + dr * direction, col + dc * direction
                while 0 <= r < 15 and 0 <= c < 15 and self.board[r][c] == symbol:
                    count += 1
                    r += dr * direction
                    c += dc * direction
            if count >= 5:
                return True
        return False
    
    def get_board_display(self):
        lines = []
        lines.append('   ' + ' '.join([f'{i:X}' for i in range(15)]))
        for i, row in enumerate(self.board):
            lines.append(f'{i:X}  ' + ' '.join(row))
        return '\n'.join(lines)

game = GomokuGame()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    emit('message', {'data': '欢迎使用五子棋终端！输入 @h 查看命令'})

@socketio.on('command')
def handle_command(data):
    cmd = data.get('command', '').strip()
    player_id = request.sid
    
    if not cmd:
        return
    
    parts = cmd.split()
    command = parts[0].lower()
    
    if command == '@h' or command == 'help':
        help_text = """
可用命令:
  @j <名字>      - 加入游戏 (例: @j 小明)
  @s             - 开始游戏 (需要2人)
  @p <行> <列>   - 下棋 (例: @p 7 7 表示中心位置)
  @b             - 查看棋盘
  @l             - 查看玩家列表
  @m             - 查看历史记录
  @c             - 清屏
  @h             - 显示帮助

坐标说明: 行和列都是0-14 (用十六进制0-E表示)
"""
        emit('output', {'data': help_text})
    
    elif command == '@j':
        if len(parts) < 2:
            emit('output', {'data': '用法: @j <名字>'})
            return
        
        name = parts[1]
        if player_id in game.players:
            emit('output', {'data': f'你已经加入游戏，名字: {game.players[player_id]["name"]}'})
        elif len(game.players) >= 2:
            emit('output', {'data': '游戏已满，只能2人对战'})
        else:
            game.players[player_id] = {'name': name, 'symbol': ''}
            emit('output', {'data': f'{name} 加入游戏！'})
            socketio.emit('output', {'data': f'玩家 {name} 加入了游戏'})
    
    elif command == '@l':
        if not game.players:
            emit('output', {'data': '当前没有玩家'})
        else:
            player_list = '\n'.join([f"- {p['name']} {p.get('symbol', '')}" for p in game.players.values()])
            emit('output', {'data': f'当前玩家:\n{player_list}'})
    
    elif command == '@s':
        if player_id not in game.players:
            emit('output', {'data': '请先加入游戏 (@j <名字>)'})
            return
        
        success, msg = game.start_game()
        if success:
            socketio.emit('output', {'data': msg})
            board = game.get_board_display()
            socketio.emit('output', {'data': f'\n{board}'})
            current_player = game.players[game.player_list[0]]['name']
            socketio.emit('output', {'data': f'\n{current_player} 先手！'})
        else:
            emit('output', {'data': msg})
    
    elif command == '@b':
        if not game.game_started:
            emit('output', {'data': '游戏还未开始'})
            return
        
        board = game.get_board_display()
        emit('output', {'data': f'\n{board}'})
        if game.player_list:
            current_player = game.players[game.player_list[game.current_turn]]['name']
            emit('output', {'data': f'当前回合: {current_player}'})
    
    elif command == '@p':
        if player_id not in game.players:
            emit('output', {'data': '请先加入游戏 (@j <名字>)'})
            return
        
        if len(parts) < 3:
            emit('output', {'data': '用法: @p <行> <列> (例: @p 7 7)'})
            return
        
        try:
            row = int(parts[1], 16) if len(parts[1]) == 1 else int(parts[1])
            col = int(parts[2], 16) if len(parts[2]) == 1 else int(parts[2])
        except ValueError:
            emit('output', {'data': '坐标必须是数字 (0-14 或 0-E)'})
            return
        
        success, msg, result = game.place_stone(player_id, row, col)
        if success:
            socketio.emit('output', {'data': msg})
            board = game.get_board_display()
            socketio.emit('output', {'data': f'\n{board}'})
            if result == 'win':
                game.game_started = False
        else:
            emit('output', {'data': msg})
    
    elif command == '@m':
        if not game.move_history:
            emit('output', {'data': '还没有落子记录'})
        else:
            history = '\n'.join([f'{i+1}. ({r},{c}) {s}' for i, (r, c, s) in enumerate(game.move_history)])
            emit('output', {'data': f'落子历史:\n{history}'})
    
    elif command == '@c':
        emit('clear')
    
    else:
        emit('output', {'data': f'未知命令: {command}，输入 @h 查看帮助'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
