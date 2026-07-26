EMPTY = 0
BLACK = 1
WHITE = 2


class GoBoard:
    def __init__(self, size=19, komi=6.5):
        self.size = size
        self.komi = komi
        self.board = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.current_player = BLACK
        self.history = []
        self.captures = {BLACK: 0, WHITE: 0}
        self.last_move = None
        self.ko_point = None
        self.move_count = 0
        self.passes = 0
        self.game_over = False
        self.result = None

    def copy(self):
        new_board = GoBoard(self.size, self.komi)
        new_board.board = [row[:] for row in self.board]
        new_board.current_player = self.current_player
        new_board.history = [h.copy() if isinstance(h, dict) else h for h in self.history]
        new_board.captures = self.captures.copy()
        new_board.last_move = self.last_move
        new_board.ko_point = self.ko_point
        new_board.move_count = self.move_count
        new_board.passes = self.passes
        new_board.game_over = self.game_over
        new_board.result = self.result
        return new_board

    def _get_neighbors(self, x, y):
        neighbors = []
        if x > 0:
            neighbors.append((x - 1, y))
        if x < self.size - 1:
            neighbors.append((x + 1, y))
        if y > 0:
            neighbors.append((x, y - 1))
        if y < self.size - 1:
            neighbors.append((x, y + 1))
        return neighbors

    def _get_group(self, x, y):
        color = self.board[x][y]
        if color == EMPTY:
            return [], []
        visited = set()
        group = []
        liberties = set()
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            if self.board[cx][cy] == EMPTY:
                liberties.add((cx, cy))
                continue
            if self.board[cx][cy] != color:
                continue
            group.append((cx, cy))
            for nx, ny in self._get_neighbors(cx, cy):
                if (nx, ny) not in visited:
                    stack.append((nx, ny))
        return group, list(liberties)

    def _remove_group(self, group):
        for x, y in group:
            self.board[x][y] = EMPTY
        return len(group)

    def _board_state_key(self):
        rows = []
        for row in self.board:
            rows.append(tuple(row))
        return (tuple(rows), self.current_player)

    def is_valid_move(self, x, y, player=None):
        if player is None:
            player = self.current_player
        if self.game_over:
            return False
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return False
        if self.board[x][y] != EMPTY:
            return False
        if self.ko_point == (x, y):
            return False
        test_board = self.copy()
        test_board.board[x][y] = player
        opponent = WHITE if player == BLACK else BLACK
        captured_any = False
        for nx, ny in test_board._get_neighbors(x, y):
            if test_board.board[nx][ny] == opponent:
                group, liberties = test_board._get_group(nx, ny)
                if len(liberties) == 0:
                    test_board._remove_group(group)
                    captured_any = True
        _, self_liberties = test_board._get_group(x, y)
        if len(self_liberties) == 0 and not captured_any:
            return False
        return True

    def play_move(self, x, y):
        if not self.is_valid_move(x, y):
            return False, None
        self.history.append({
            'board': [row[:] for row in self.board],
            'current_player': self.current_player,
            'captures': self.captures.copy(),
            'last_move': self.last_move,
            'ko_point': self.ko_point,
            'move_count': self.move_count,
            'passes': self.passes,
        })
        self.board[x][y] = self.current_player
        opponent = WHITE if self.current_player == BLACK else BLACK
        captured_stones = []
        for nx, ny in self._get_neighbors(x, y):
            if self.board[nx][ny] == opponent:
                group, liberties = self._get_group(nx, ny)
                if len(liberties) == 0:
                    captured_stones.extend(group)
                    self._remove_group(group)
        self.captures[self.current_player] += len(captured_stones)
        if len(captured_stones) == 1:
            cx, cy = captured_stones[0]
            _, new_liberties = self._get_group(x, y)
            if len(new_liberties) == 1 and new_liberties[0] == (cx, cy):
                self.ko_point = (cx, cy)
            else:
                self.ko_point = None
        else:
            self.ko_point = None
        self.last_move = (x, y)
        self.move_count += 1
        self.passes = 0
        self.current_player = opponent
        return True, captured_stones

    def pass_move(self):
        if self.game_over:
            return False
        self.history.append({
            'board': [row[:] for row in self.board],
            'current_player': self.current_player,
            'captures': self.captures.copy(),
            'last_move': self.last_move,
            'ko_point': self.ko_point,
            'move_count': self.move_count,
            'passes': self.passes,
        })
        self.passes += 1
        self.move_count += 1
        self.last_move = None
        self.ko_point = None
        if self.passes >= 2:
            self.game_over = True
            self.result = self.calculate_score()
        self.current_player = WHITE if self.current_player == BLACK else BLACK
        return True

    def undo(self):
        if len(self.history) == 0:
            return False
        state = self.history.pop()
        self.board = state['board']
        self.current_player = state['current_player']
        self.captures = state['captures']
        self.last_move = state['last_move']
        self.ko_point = state['ko_point']
        self.move_count = state['move_count']
        self.passes = state['passes']
        self.game_over = False
        self.result = None
        return True

    def get_legal_moves(self):
        moves = []
        for x in range(self.size):
            for y in range(self.size):
                if self.is_valid_move(x, y):
                    moves.append((x, y))
        return moves

    def count_territory(self):
        visited = [[False for _ in range(self.size)] for _ in range(self.size)]
        black_territory = 0
        white_territory = 0
        black_stones = 0
        white_stones = 0
        for x in range(self.size):
            for y in range(self.size):
                if self.board[x][y] == BLACK:
                    black_stones += 1
                elif self.board[x][y] == WHITE:
                    white_stones += 1
        for x in range(self.size):
            for y in range(self.size):
                if not visited[x][y] and self.board[x][y] == EMPTY:
                    region = []
                    borders = set()
                    stack = [(x, y)]
                    while stack:
                        cx, cy = stack.pop()
                        if visited[cx][cy]:
                            continue
                        visited[cx][cy] = True
                        if self.board[cx][cy] != EMPTY:
                            borders.add(self.board[cx][cy])
                            continue
                        region.append((cx, cy))
                        for nx, ny in self._get_neighbors(cx, cy):
                            if not visited[nx][ny]:
                                stack.append((nx, ny))
                    if len(borders) == 1:
                        owner = list(borders)[0]
                        if owner == BLACK:
                            black_territory += len(region)
                        elif owner == WHITE:
                            white_territory += len(region)
        return {
            'black_stones': black_stones,
            'white_stones': white_stones,
            'black_territory': black_territory,
            'white_territory': white_territory,
            'black_captures': self.captures[BLACK],
            'white_captures': self.captures[WHITE],
        }

    def calculate_score(self):
        territory = self.count_territory()
        black_score = territory['black_territory'] + territory['black_captures']
        white_score = territory['white_territory'] + territory['white_captures'] + self.komi
        winner = None
        margin = 0
        if black_score > white_score:
            winner = BLACK
            margin = black_score - white_score
        elif white_score > black_score:
            winner = WHITE
            margin = white_score - black_score
        else:
            winner = 0
            margin = 0
        return {
            'black_score': black_score,
            'white_score': white_score,
            'winner': winner,
            'margin': margin,
            'territory': territory,
        }

    def get_stone_color(self, x, y):
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return None
        return self.board[x][y]

    @staticmethod
    def coord_to_gtp(x, y, size=19):
        letters = 'ABCDEFGHJKLMNOPQRST'
        col = letters[y]
        row = str(size - x)
        return f'{col}{row}'

    @staticmethod
    def gtp_to_coord(gtp_str, size=19):
        gtp_str = gtp_str.strip().upper()
        if not gtp_str:
            return None
        letters = 'ABCDEFGHJKLMNOPQRST'
        col_char = gtp_str[0]
        if col_char not in letters:
            return None
        y = letters.index(col_char)
        try:
            row_num = int(gtp_str[1:])
        except ValueError:
            return None
        x = size - row_num
        if x < 0 or x >= size or y < 0 or y >= size:
            return None
        return (x, y)

    @staticmethod
    def color_to_str(color):
        if color == BLACK:
            return 'black'
        elif color == WHITE:
            return 'white'
        return 'empty'

    @staticmethod
    def str_to_color(s):
        s = s.lower().strip()
        if s in ('black', 'b'):
            return BLACK
        elif s in ('white', 'w'):
            return WHITE
        return EMPTY
