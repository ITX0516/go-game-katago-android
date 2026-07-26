import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
from go_board import GoBoard, BLACK, WHITE, EMPTY
from katago_engine import KataGoEngine
from config import Config


class GoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("围棋对弈 - Katago")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)
        self.config = Config()
        self.board = GoBoard(
            size=self.config.get('board_size', 19),
            komi=self.config.get('komi', 6.5)
        )
        self.engine = None
        self.engine_connected = False
        self.thinking = False
        self.player_color = BLACK if self.config.get('player_color', 'black') == 'black' else WHITE
        self.ai_color = WHITE if self.player_color == BLACK else BLACK
        self.cell_size = 30
        self.margin = 40
        self.stone_radius = 13
        self.hover_pos = None
        self.move_history_text = None
        self._init_ui()
        self._bind_events()
        self._update_status()

    def _init_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_frame = ttk.Frame(main_frame, width=250)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        self.canvas = tk.Canvas(
            left_frame,
            bg='#DEB887',
            highlightthickness=0
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self._draw_board()
        info_frame = ttk.LabelFrame(right_frame, text="游戏信息", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_var = tk.StringVar(value="准备就绪")
        ttk.Label(info_frame, textvariable=self.status_var, wraplength=220).pack(anchor=tk.W)
        ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self.current_player_var = tk.StringVar(value="当前: 黑方")
        ttk.Label(info_frame, textvariable=self.current_player_var).pack(anchor=tk.W)
        self.move_count_var = tk.StringVar(value="手数: 0")
        ttk.Label(info_frame, textvariable=self.move_count_var).pack(anchor=tk.W)
        captures_frame = ttk.Frame(info_frame)
        captures_frame.pack(fill=tk.X, pady=5)
        self.black_captures_var = tk.StringVar(value="黑提子: 0")
        self.white_captures_var = tk.StringVar(value="白提子: 0")
        ttk.Label(captures_frame, textvariable=self.black_captures_var).pack(side=tk.LEFT)
        ttk.Label(captures_frame, textvariable=self.white_captures_var).pack(side=tk.RIGHT)
        control_frame = ttk.LabelFrame(right_frame, text="操作", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        btn_grid = ttk.Frame(control_frame)
        btn_grid.pack(fill=tk.X)
        ttk.Button(btn_grid, text="新对局", command=self.new_game).grid(row=0, column=0, sticky=tk.EW, padx=2, pady=2)
        ttk.Button(btn_grid, text="悔棋", command=self.undo_move).grid(row=0, column=1, sticky=tk.EW, padx=2, pady=2)
        ttk.Button(btn_grid, text="停一手", command=self.pass_move).grid(row=1, column=0, sticky=tk.EW, padx=2, pady=2)
        ttk.Button(btn_grid, text="认输", command=self.resign).grid(row=1, column=1, sticky=tk.EW, padx=2, pady=2)
        ttk.Button(btn_grid, text="计算胜负", command=self.calculate_score).grid(row=2, column=0, sticky=tk.EW, padx=2, pady=2)
        ttk.Button(btn_grid, text="切换执子", command=self.toggle_color).grid(row=2, column=1, sticky=tk.EW, padx=2, pady=2)
        btn_grid.columnconfigure(0, weight=1)
        btn_grid.columnconfigure(1, weight=1)
        engine_frame = ttk.LabelFrame(right_frame, text="Katago引擎", padding=10)
        engine_frame.pack(fill=tk.X, pady=(0, 10))
        self.engine_status_var = tk.StringVar(value="状态: 未连接")
        ttk.Label(engine_frame, textvariable=self.engine_status_var).pack(anchor=tk.W)
        engine_btn_frame = ttk.Frame(engine_frame)
        engine_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(engine_btn_frame, text="连接引擎", command=self.connect_engine).pack(side=tk.LEFT, padx=2)
        ttk.Button(engine_btn_frame, text="断开连接", command=self.disconnect_engine).pack(side=tk.LEFT, padx=2)
        ttk.Button(engine_frame, text="引擎设置", command=self.engine_settings).pack(fill=tk.X, pady=2)
        history_frame = ttk.LabelFrame(right_frame, text="棋谱记录", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True)
        self.history_text = tk.Text(history_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.history_text.pack(fill=tk.BOTH, expand=True)
        history_scroll = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_text.yview)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_text.config(yscrollcommand=history_scroll.set)

    def _bind_events(self):
        self.canvas.bind('<Configure>', lambda e: self._draw_board())
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<Leave>', lambda e: self._clear_hover())
        self.canvas.bind('<Button-1>', self._on_click)

    def _draw_board(self):
        self.canvas.delete('all')
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        if width < 100 or height < 100:
            return
        size = self.board.size
        max_cell_width = (width - 2 * self.margin) / (size - 1)
        max_cell_height = (height - 2 * self.margin) / (size - 1)
        self.cell_size = min(max_cell_width, max_cell_height)
        self.stone_radius = self.cell_size * 0.45
        board_width = self.cell_size * (size - 1)
        board_height = self.cell_size * (size - 1)
        self.offset_x = (width - board_width) / 2
        self.offset_y = (height - board_height) / 2
        for i in range(size):
            x0 = self.offset_x
            y0 = self.offset_y + i * self.cell_size
            x1 = self.offset_x + (size - 1) * self.cell_size
            y1 = y0
            self.canvas.create_line(x0, y0, x1, y1, fill='#333333', width=1)
        for j in range(size):
            x0 = self.offset_x + j * self.cell_size
            y0 = self.offset_y
            x1 = x0
            y1 = self.offset_y + (size - 1) * self.cell_size
            self.canvas.create_line(x0, y0, x1, y1, fill='#333333', width=1)
        star_points = self._get_star_points()
        for x, y in star_points:
            px = self.offset_x + y * self.cell_size
            py = self.offset_y + x * self.cell_size
            r = self.cell_size * 0.08
            self.canvas.create_oval(px - r, py - r, px + r, py + r, fill='#333333')
        if self.config.get('show_coordinates', True):
            letters = 'ABCDEFGHJKLMNOPQRST'
            for i in range(size):
                x = self.offset_x + i * self.cell_size
                self.canvas.create_text(x, self.offset_y - self.margin * 0.6,
                                        text=letters[i], font=('Arial', int(self.cell_size * 0.35)))
                self.canvas.create_text(x, self.offset_y + (size - 1) * self.cell_size + self.margin * 0.6,
                                        text=letters[i], font=('Arial', int(self.cell_size * 0.35)))
            for i in range(size):
                y = self.offset_y + i * self.cell_size
                num = str(size - i)
                self.canvas.create_text(self.offset_x - self.margin * 0.6, y,
                                        text=num, font=('Arial', int(self.cell_size * 0.35)))
                self.canvas.create_text(self.offset_x + (size - 1) * self.cell_size + self.margin * 0.6, y,
                                        text=num, font=('Arial', int(self.cell_size * 0.35)))
        self._draw_stones()

    def _get_star_points(self):
        size = self.board.size
        points = []
        if size == 9:
            positions = [2, 4, 6]
        elif size == 13:
            positions = [3, 6, 9]
        elif size == 19:
            positions = [3, 9, 15]
        else:
            return points
        for i in positions:
            for j in positions:
                points.append((i, j))
        return points

    def _draw_stones(self):
        for x in range(self.board.size):
            for y in range(self.board.size):
                color = self.board.get_stone_color(x, y)
                if color != EMPTY:
                    self._draw_stone(x, y, color)
        if self.config.get('show_last_move', True) and self.board.last_move:
            lx, ly = self.board.last_move
            px = self.offset_x + ly * self.cell_size
            py = self.offset_y + lx * self.cell_size
            r = self.stone_radius * 0.35
            color = '#FF0000' if self.board.get_stone_color(lx, ly) == BLACK else '#FF0000'
            self.canvas.create_oval(px - r, py - r, px + r, py + r, outline=color, width=2)
        if self.hover_pos and not self.thinking and not self.board.game_over:
            hx, hy = self.hover_pos
            if self.board.is_valid_move(hx, hy):
                self._draw_stone(hx, hy, self.board.current_player, alpha=0.4)

    def _draw_stone(self, x, y, color, alpha=1.0):
        px = self.offset_x + y * self.cell_size
        py = self.offset_y + x * self.cell_size
        r = self.stone_radius
        if color == BLACK:
            fill = '#1a1a1a'
            outline = '#000000'
            if alpha < 1.0:
                fill = '#666666'
        else:
            fill = '#F5F5F5'
            outline = '#888888'
            if alpha < 1.0:
                fill = '#D0D0D0'
        self.canvas.create_oval(px - r, py - r, px + r, py + r,
                                fill=fill, outline=outline, width=1)
        if alpha >= 1.0 and color == WHITE:
            highlight_r = r * 0.3
            self.canvas.create_oval(px - r * 0.5 - highlight_r, py - r * 0.5 - highlight_r,
                                    px - r * 0.5 + highlight_r, py - r * 0.5 + highlight_r,
                                    fill='#FFFFFF', outline='')

    def _pixel_to_coord(self, px, py):
        x = round((py - self.offset_y) / self.cell_size)
        y = round((px - self.offset_x) / self.cell_size)
        if x < 0 or x >= self.board.size or y < 0 or y >= self.board.size:
            return None
        bx = self.offset_x + y * self.cell_size
        by = self.offset_y + x * self.cell_size
        dist = ((px - bx) ** 2 + (py - by) ** 2) ** 0.5
        if dist > self.cell_size * 0.5:
            return None
        return (x, y)

    def _on_mouse_move(self, event):
        coord = self._pixel_to_coord(event.x, event.y)
        if coord != self.hover_pos:
            self.hover_pos = coord
            self._draw_stones()

    def _clear_hover(self):
        self.hover_pos = None
        self._draw_stones()

    def _on_click(self, event):
        if self.thinking or self.board.game_over:
            return
        if self.board.current_player != self.player_color:
            return
        coord = self._pixel_to_coord(event.x, event.y)
        if coord is None:
            return
        x, y = coord
        if not self.board.is_valid_move(x, y):
            return
        self._play_move(x, y)

    def _play_move(self, x, y):
        player = self.board.current_player
        success, captured = self.board.play_move(x, y)
        if not success:
            return
        if self.engine_connected:
            try:
                self.engine.play_move(x, y, player)
            except Exception as e:
                messagebox.showerror("引擎错误", f"同步到引擎失败: {e}")
        self._update_history()
        self._draw_board()
        self._update_status()
        if self.board.game_over:
            self._show_game_result()
            return
        if self.engine_connected and self.board.current_player == self.ai_color and not self.thinking:
            self._request_ai_move()

    def pass_move(self):
        if self.thinking or self.board.game_over:
            return
        if self.board.current_player != self.player_color:
            return
        self.board.pass_move()
        if self.engine_connected:
            try:
                self.engine.send_command(f'play {GoBoard.color_to_str(self.player_color)} pass')
            except Exception:
                pass
        self._update_history()
        self._draw_board()
        self._update_status()
        if self.board.game_over:
            self._show_game_result()
            return
        if self.engine_connected and self.board.current_player == self.ai_color and not self.thinking:
            self._request_ai_move()

    def undo_move(self):
        if self.thinking:
            return
        if not self.board.history:
            return
        undo_count = 1
        if self.engine_connected and self.board.move_count > 1:
            undo_count = 2
        for _ in range(undo_count):
            if not self.board.undo():
                break
        if self.engine_connected:
            try:
                for _ in range(undo_count):
                    self.engine.undo()
            except Exception:
                pass
        self._update_history()
        self._draw_board()
        self._update_status()

    def resign(self):
        if self.board.game_over:
            return
        if not messagebox.askyesno("认输", "确定要认输吗？"):
            return
        self.board.game_over = True
        winner = self.ai_color
        self.board.result = {
            'winner': winner,
            'margin': 0,
            'resign': True,
        }
        self._update_status()
        winner_str = "黑方" if winner == BLACK else "白方"
        messagebox.showinfo("对局结束", f"{winner_str}胜（对方认输）")

    def calculate_score(self):
        result = self.board.calculate_score()
        if result['winner'] == BLACK:
            winner_str = f"黑方胜 {result['margin']:.1f} 目"
        elif result['winner'] == WHITE:
            winner_str = f"白方胜 {result['margin']:.1f} 目"
        else:
            winner_str = "和棋"
        msg = (
            f"对局结果: {winner_str}\n\n"
            f"黑方得分: {result['black_score']:.1f} 目\n"
            f"  领地: {result['territory']['black_territory']} 目\n"
            f"  提子: {result['territory']['black_captures']} 子\n\n"
            f"白方得分: {result['white_score']:.1f} 目\n"
            f"  领地: {result['territory']['white_territory']} 目\n"
            f"  提子: {result['territory']['white_captures']} 子\n"
            f"  贴目: {self.board.komi} 目"
        )
        messagebox.showinfo("计算结果", msg)

    def new_game(self):
        if self.thinking:
            return
        if self.board.move_count > 0 and not messagebox.askyesno("新对局", "确定要开始新对局吗？当前对局记录将丢失。"):
            return
        self.board = GoBoard(
            size=self.config.get('board_size', 19),
            komi=self.config.get('komi', 6.5)
        )
        if self.engine_connected:
            try:
                self.engine.set_board_size(self.board.size)
                self.engine.set_komi(self.board.komi)
                self.engine.clear_board()
            except Exception as e:
                messagebox.showerror("引擎错误", f"重置引擎失败: {e}")
        self._update_history()
        self._draw_board()
        self._update_status()
        if self.engine_connected and self.ai_color == BLACK:
            self._request_ai_move()

    def toggle_color(self):
        if self.thinking:
            return
        if self.board.move_count > 0 and not messagebox.askyesno("切换执子", "切换执子将重新开始对局，确定吗？"):
            return
        self.player_color = WHITE if self.player_color == BLACK else BLACK
        self.ai_color = BLACK if self.ai_color == WHITE else WHITE
        self.config.set('player_color', 'black' if self.player_color == BLACK else 'white')
        self.config.save()
        self.new_game()

    def _request_ai_move(self):
        if self.thinking or not self.engine_connected:
            return
        self.thinking = True
        self._update_status()
        t = threading.Thread(target=self._ai_move_thread, daemon=True)
        t.start()

    def _ai_move_thread(self):
        try:
            result = self.engine.gen_move(self.ai_color)
            self.root.after(0, lambda: self._on_ai_move(result))
        except Exception as e:
            self.root.after(0, lambda: self._on_ai_error(e))

    def _on_ai_move(self, result):
        self.thinking = False
        if result == 'resign':
            self.board.game_over = True
            self.board.result = {'winner': self.player_color, 'margin': 0, 'resign': True}
            winner_str = "黑方" if self.player_color == BLACK else "白方"
            self._update_status()
            messagebox.showinfo("对局结束", f"{winner_str}胜（对方认输）")
            return
        if result == 'pass':
            self.board.pass_move()
            self._update_history()
            self._draw_board()
            self._update_status()
            if self.board.game_over:
                self._show_game_result()
            return
        x, y = result
        success, captured = self.board.play_move(x, y)
        if not success:
            messagebox.showerror("AI错误", "AI生成了无效着法")
            return
        self._update_history()
        self._draw_board()
        self._update_status()
        if self.board.game_over:
            self._show_game_result()

    def _on_ai_error(self, error):
        self.thinking = False
        self._update_status()
        messagebox.showerror("AI错误", f"AI思考出错: {error}")

    def _show_game_result(self):
        if self.board.result:
            result = self.board.result
        else:
            result = self.board.calculate_score()
        if result.get('resign'):
            winner_str = "黑方" if result['winner'] == BLACK else "白方"
            msg = f"对局结束\n\n{winner_str}胜（对方认输）"
        else:
            if result['winner'] == BLACK:
                winner_str = f"黑方胜 {result['margin']:.1f} 目"
            elif result['winner'] == WHITE:
                winner_str = f"白方胜 {result['margin']:.1f} 目"
            else:
                winner_str = "和棋"
            msg = (
                f"对局结束\n\n"
                f"结果: {winner_str}\n\n"
                f"黑方: {result['black_score']:.1f} 目\n"
                f"白方: {result['white_score']:.1f} 目\n"
                f"贴目: {self.board.komi} 目"
            )
        messagebox.showinfo("对局结束", msg)

    def connect_engine(self):
        if self.thinking:
            return
        if self.engine_connected:
            return
        katago_path = self.config.get('katago_path', '')
        if not katago_path:
            messagebox.showinfo("提示", "请先在引擎设置中配置Katago路径")
            self.engine_settings()
            katago_path = self.config.get('katago_path', '')
            if not katago_path:
                return
        try:
            self.engine = KataGoEngine(
                katago_path=katago_path,
                config_path=self.config.get('config_path', ''),
                model_path=self.config.get('model_path', ''),
                analysis_threads=self.config.get('analysis_threads', 2),
                board_size=self.board.size,
                komi=self.board.komi,
            )
            self.engine.start()
            self.engine_connected = True
            self._sync_board_to_engine()
            self._update_status()
            messagebox.showinfo("成功", "Katago引擎已连接")
            if self.board.current_player == self.ai_color and not self.board.game_over:
                self._request_ai_move()
        except Exception as e:
            self.engine_connected = False
            self.engine = None
            messagebox.showerror("连接失败", f"无法连接Katago引擎:\n{e}\n\n请检查Katago路径配置是否正确。")

    def disconnect_engine(self):
        if self.thinking:
            return
        if not self.engine_connected:
            return
        try:
            self.engine.stop()
        except Exception:
            pass
        self.engine = None
        self.engine_connected = False
        self._update_status()

    def _sync_board_to_engine(self):
        if not self.engine_connected:
            return
        self.engine.clear_board()
        moves = self._get_move_list()
        for color, move in moves:
            if move == 'pass':
                self.engine.send_command(f'play {GoBoard.color_to_str(color)} pass')
            else:
                x, y = move
                self.engine.play_move(x, y, color)

    def _get_move_list(self):
        moves = []
        if len(self.board.history) == 0:
            if self.board.last_move:
                player = BLACK
                moves.append((player, self.board.last_move))
            return moves
        prev_board = None
        player = BLACK
        for state in self.board.history:
            curr_board = state['board']
            if prev_board is not None:
                found = False
                for x in range(self.board.size):
                    for y in range(self.board.size):
                        if prev_board[x][y] == EMPTY and curr_board[x][y] != EMPTY:
                            moves.append((player, (x, y)))
                            found = True
                            break
                    if found:
                        break
                if not found:
                    moves.append((player, 'pass'))
                player = WHITE if player == BLACK else BLACK
            prev_board = [row[:] for row in curr_board]
        if prev_board is not None:
            curr_board = self.board.board
            found = False
            for x in range(self.board.size):
                for y in range(self.board.size):
                    if prev_board[x][y] == EMPTY and curr_board[x][y] != EMPTY:
                        moves.append((player, (x, y)))
                        found = True
                        break
                if found:
                    break
            if not found and self.board.move_count > len(self.board.history):
                moves.append((player, 'pass'))
        return moves

    def engine_settings(self):
        SettingsDialog(self.root, self.config, self._on_settings_changed)

    def _on_settings_changed(self):
        if self.engine_connected:
            self.disconnect_engine()
        new_size = self.config.get('board_size', 19)
        new_komi = self.config.get('komi', 6.5)
        if new_size != self.board.size or new_komi != self.board.komi:
            if self.board.move_count > 0:
                if messagebox.askyesno("设置变更", "棋盘大小或贴目变更，需要重新开始对局吗？"):
                    self.new_game()

    def _update_status(self):
        player_str = "黑方" if self.board.current_player == BLACK else "白方"
        self.current_player_var.set(f"当前: {player_str}")
        self.move_count_var.set(f"手数: {self.board.move_count}")
        self.black_captures_var.set(f"黑提子: {self.board.captures[BLACK]}")
        self.white_captures_var.set(f"白提子: {self.board.captures[WHITE]}")
        if self.engine_connected:
            engine_str = "状态: 已连接"
        else:
            engine_str = "状态: 未连接"
        self.engine_status_var.set(engine_str)
        if self.thinking:
            self.status_var.set("AI思考中...")
        elif self.board.game_over:
            self.status_var.set("对局结束")
        elif self.board.current_player == self.player_color:
            self.status_var.set("轮到你落子")
        else:
            self.status_var.set("轮到对方落子")

    def _update_history(self):
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete('1.0', tk.END)
        moves = self._get_move_list()
        lines = []
        move_num = 1
        for i, (color, move) in enumerate(moves):
            color_str = '黑' if color == BLACK else '白'
            if move == 'pass':
                move_str = '停一手'
            else:
                x, y = move
                move_str = GoBoard.coord_to_gtp(x, y, self.board.size)
            if i % 2 == 0:
                lines.append(f"{move_num:3d}. {color_str}{move_str}")
            else:
                if lines:
                    lines[-1] += f"  {color_str}{move_str}"
                else:
                    lines.append(f"     {color_str}{move_str}")
                move_num += 1
        if lines:
            self.history_text.insert(tk.END, '\n'.join(lines))
        self.history_text.config(state=tk.DISABLED)


class SettingsDialog:
    def __init__(self, parent, config, on_changed=None):
        self.config = config
        self.on_changed = on_changed
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("引擎设置")
        self.dialog.geometry("450x380")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self._init_ui()

    def _init_ui(self):
        frame = ttk.Frame(self.dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Katago 可执行文件路径:").grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        path_frame = ttk.Frame(frame)
        path_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        self.katago_path_var = tk.StringVar(value=self.config.get('katago_path', ''))
        ttk.Entry(path_frame, textvariable=self.katago_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览...", command=self._browse_katago).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(frame, text="配置文件路径 (可选):").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        config_frame = ttk.Frame(frame)
        config_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        self.config_path_var = tk.StringVar(value=self.config.get('config_path', ''))
        ttk.Entry(config_frame, textvariable=self.config_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(config_frame, text="浏览...", command=self._browse_config).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(frame, text="权重模型路径 (可选):").grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        model_frame = ttk.Frame(frame)
        model_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        self.model_path_var = tk.StringVar(value=self.config.get('model_path', ''))
        ttk.Entry(model_frame, textvariable=self.model_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(model_frame, text="浏览...", command=self._browse_model).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10)
        ttk.Label(frame, text="分析线程数:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.threads_var = tk.IntVar(value=self.config.get('analysis_threads', 2))
        ttk.Spinbox(frame, from_=1, to=32, textvariable=self.threads_var, width=10).grid(row=7, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="棋盘大小:").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.board_size_var = tk.IntVar(value=self.config.get('board_size', 19))
        size_combo = ttk.Combobox(frame, textvariable=self.board_size_var, values=[9, 13, 19], state='readonly', width=10)
        size_combo.grid(row=8, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="贴目:").grid(row=9, column=0, sticky=tk.W, pady=5)
        self.komi_var = tk.DoubleVar(value=self.config.get('komi', 6.5))
        komi_combo = ttk.Combobox(frame, textvariable=self.komi_var, values=[0, 3.5, 5.5, 6.5, 7.5], width=10)
        komi_combo.grid(row=9, column=1, sticky=tk.W, pady=5)
        ttk.Separator(frame, orient=tk.HORIZONTAL).grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=10)
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=11, column=0, columnspan=2, sticky=tk.EW)
        ttk.Button(btn_frame, text="确定", command=self._ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.RIGHT)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _browse_katago(self):
        path = filedialog.askopenfilename(title="选择 Katago 可执行文件")
        if path:
            self.katago_path_var.set(path)

    def _browse_config(self):
        path = filedialog.askopenfilename(title="选择配置文件",
                                          filetypes=[("配置文件", "*.cfg *.toml *.json"), ("所有文件", "*.*")])
        if path:
            self.config_path_var.set(path)

    def _browse_model(self):
        path = filedialog.askopenfilename(title="选择权重模型文件",
                                          filetypes=[("模型文件", "*.bin.gz *.txt.gz"), ("所有文件", "*.*")])
        if path:
            self.model_path_var.set(path)

    def _ok(self):
        self.config.set('katago_path', self.katago_path_var.get().strip())
        self.config.set('config_path', self.config_path_var.get().strip())
        self.config.set('model_path', self.model_path_var.get().strip())
        self.config.set('analysis_threads', int(self.threads_var.get()))
        self.config.set('board_size', int(self.board_size_var.get()))
        self.config.set('komi', float(self.komi_var.get()))
        self.config.save()
        if self.on_changed:
            self.on_changed()
        self.dialog.destroy()

    def _cancel(self):
        self.dialog.destroy()
