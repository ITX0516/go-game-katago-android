import os
import sys
import threading

# Font setup - MUST be before any Kivy imports
def _find_chinese_font():
    candidates = [
        '/system/fonts/NotoSansCJK-Regular.ttc',
        '/system/fonts/NotoSansSC-Regular.otf',
        '/system/fonts/DroidSansFallback.ttf',
        '/system/fonts/NotoSansSC-VF.ttf',
        '/system/fonts/NotoSansCJK-VF.ttf',
        '/system/fonts/NotoSerifCJK-Regular.ttc',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    if os.path.exists('/system/fonts/'):
        try:
            for f in sorted(os.listdir('/system/fonts/')):
                lower = f.lower()
                if any(k in lower for k in ['cjk', 'sc-', 'sans-sc', 'fallback', 'chinese', 'hei', 'micro']):
                    p = os.path.join('/system/fonts/', f)
                    if os.path.isfile(p):
                        return p
        except Exception:
            pass
    return None

_chinese_font = _find_chinese_font()

# Set default font in Kivy config BEFORE importing any Kivy module
if _chinese_font:
    from kivy.config import Config
    Config.set('kivy', 'default_font', [_chinese_font, _chinese_font, _chinese_font, _chinese_font])

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from go_board import GoBoard, BLACK, WHITE, EMPTY
from katago_engine import KataGoEngine
from config import Config
import android_utils


class BoardWidget(Widget):
    def __init__(self, **kwargs):
        super(BoardWidget, self).__init__(**kwargs)
        self.board = None
        self.hover_pos = None
        self.show_coordinates = True
        self.show_last_move = True
        self.cell_size = 0
        self.offset_x = 0
        self.offset_y = 0
        self.touch_down_pos = None
        self.on_move_played = None
        self.bind(size=self._on_size, pos=self._on_size)

    def set_board(self, board):
        self.board = board
        self._update_geometry()
        self.canvas.ask_update()

    def _on_size(self, *args):
        self._update_geometry()
        self.canvas.ask_update()

    def _update_geometry(self):
        if not self.board:
            return
        size = self.board.size
        w = self.width
        h = self.height
        margin = dp(20)
        max_cell_w = (w - 2 * margin) / (size - 1) if size > 1 else w
        max_cell_h = (h - 2 * margin) / (size - 1) if size > 1 else h
        self.cell_size = min(max_cell_w, max_cell_h)
        board_w = self.cell_size * (size - 1)
        board_h = self.cell_size * (size - 1)
        self.offset_x = (w - board_w) / 2
        self.offset_y = (h - board_h) / 2

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

    def _coord_to_pixel(self, x, y):
        px = self.offset_x + y * self.cell_size
        py = self.offset_y + x * self.cell_size
        return px, py

    def _pixel_to_coord(self, px, py):
        if self.cell_size == 0 or self.board is None:
            return None
        x = round((py - self.offset_y) / self.cell_size)
        y = round((px - self.offset_x) / self.cell_size)
        if x < 0 or x >= self.board.size or y < 0 or y >= self.board.size:
            return None
        bx, by = self._coord_to_pixel(x, y)
        dist = ((px - bx) ** 2 + (py - by) ** 2) ** 0.5
        if dist > self.cell_size * 0.5:
            return None
        return (x, y)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.touch_down_pos = touch.pos
            return True
        return super(BoardWidget, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and self.touch_down_pos:
            dx = abs(touch.pos[0] - self.touch_down_pos[0])
            dy = abs(touch.pos[1] - self.touch_down_pos[1])
            if dx < dp(10) and dy < dp(10):
                coord = self._pixel_to_coord(*touch.pos)
                if coord and self.on_move_played:
                    self.on_move_played(coord[0], coord[1])
            self.touch_down_pos = None
            return True
        self.touch_down_pos = None
        return super(BoardWidget, self).on_touch_up(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self.hover_pos = self._pixel_to_coord(*touch.pos)
            self.canvas.ask_update()
            return True
        return super(BoardWidget, self).on_touch_move(touch)

    def redraw(self):
        self._draw_board()

    def _draw(self, *args):
        pass

    def on_size(self, *args):
        self._draw_board()

    def _draw_board(self, *args):
        self.canvas.before.clear()
        self.canvas.clear()
        if not self.board:
            return
        self._update_geometry()
        if self.cell_size == 0:
            return
        with self.canvas.before:
            Color(0.87, 0.72, 0.53, 1)
            Rectangle(pos=self.pos, size=self.size)
        with self.canvas:
            size = self.board.size
            Color(0.2, 0.2, 0.2, 1)
            for i in range(size):
                x0 = self.offset_x
                y0 = self.offset_y + i * self.cell_size
                x1 = self.offset_x + (size - 1) * self.cell_size
                y1 = y0
                Line(points=[x0, y0, x1, y1], width=1)
            for j in range(size):
                x0 = self.offset_x + j * self.cell_size
                y0 = self.offset_y
                x1 = x0
                y1 = self.offset_y + (size - 1) * self.cell_size
                Line(points=[x0, y0, x1, y1], width=1)
            star_points = self._get_star_points()
            for sx, sy in star_points:
                px, py = self._coord_to_pixel(sx, sy)
                r = self.cell_size * 0.08
                Color(0.2, 0.2, 0.2, 1)
                Ellipse(pos=(px - r, py - r), size=(2 * r, 2 * r))
            stone_r = self.cell_size * 0.45
            for x in range(size):
                for y in range(size):
                    color = self.board.get_stone_color(x, y)
                    if color != EMPTY:
                        px, py = self._coord_to_pixel(x, y)
                        if color == BLACK:
                            Color(0.1, 0.1, 0.1, 1)
                        else:
                            Color(0.95, 0.95, 0.95, 1)
                        Ellipse(pos=(px - stone_r, py - stone_r), size=(2 * stone_r, 2 * stone_r))
                        if color == WHITE:
                            Color(0.7, 0.7, 0.7, 1)
                            Line(ellipse=(px - stone_r, py - stone_r, 2 * stone_r, 2 * stone_r), width=1)
            if self.show_last_move and self.board.last_move:
                lx, ly = self.board.last_move
                px, py = self._coord_to_pixel(lx, ly)
                r = stone_r * 0.35
                Color(1, 0, 0, 1)
                Line(ellipse=(px - r, py - r, 2 * r, 2 * r), width=2)


class GoGameApp(App):
    def __init__(self, **kwargs):
        super(GoGameApp, self).__init__(**kwargs)
        self.config = Config()
        self._auto_detect_katago()
        self.board = GoBoard(
            size=self.config.get('board_size', 19),
            komi=self.config.get('komi', 6.5)
        )
        self.engine = None
        self.engine_connected = False
        self.thinking = False
        self.player_color = BLACK if self.config.get('player_color', 'black') == 'black' else WHITE
        self.ai_color = WHITE if self.player_color == BLACK else BLACK
        self.board_widget = None
        self.status_label = None
        self.info_label = None

    def _auto_detect_katago(self):
        current_path = self.config.get('katago_path', '')
        if current_path and os.path.exists(current_path):
            return
        try:
            paths = android_utils.auto_detect_paths()
            if paths.get('katago_path') and not current_path:
                self.config.set('katago_path', paths['katago_path'])
            if paths.get('model_path') and not self.config.get('model_path', ''):
                self.config.set('model_path', paths['model_path'])
            if paths.get('config_path') and not self.config.get('config_path', ''):
                self.config.set('config_path', paths['config_path'])
            if paths.get('katago_path'):
                self.config.save()
        except Exception:
            pass

    def build(self):
        Window.clearcolor = get_color_from_hex('#F5F5F5')
        self.title = '围棋对弈'
        root = BoxLayout(orientation='vertical', padding=dp(5), spacing=dp(5))
        top_bar = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
        self.status_label = Label(text='准备就绪', size_hint_x=None, width=dp(150),
                                  font_size=dp(14), color=get_color_from_hex('#333333'))
        top_bar.add_widget(self.status_label)
        top_bar.add_widget(Widget())
        self.info_label = Label(text='黑方先行', font_size=dp(14), color=get_color_from_hex('#333333'))
        top_bar.add_widget(self.info_label)
        root.add_widget(top_bar)
        self.board_widget = BoardWidget()
        self.board_widget.set_board(self.board)
        self.board_widget.on_move_played = self._on_board_touch
        root.add_widget(self.board_widget)
        info_bar = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(10), padding=[dp(10), 0])
        self.move_count_label = Label(text='手数: 0', font_size=dp(12), color=get_color_from_hex('#666666'))
        self.black_captures_label = Label(text='黑提: 0', font_size=dp(12), color=get_color_from_hex('#666666'))
        self.white_captures_label = Label(text='白提: 0', font_size=dp(12), color=get_color_from_hex('#666666'))
        info_bar.add_widget(self.move_count_label)
        info_bar.add_widget(self.black_captures_label)
        info_bar.add_widget(self.white_captures_label)
        root.add_widget(info_bar)
        btn_grid = GridLayout(cols=4, size_hint_y=None, height=dp(50), spacing=dp(3), padding=dp(3))
        btns = [
            ('新局', self.new_game),
            ('悔棋', self.undo_move),
            ('停一手', self.pass_move),
            ('认输', self.resign),
            ('计算', self.calculate_score),
            ('换边', self.toggle_color),
            ('连接AI', self.toggle_engine),
            ('设置', self.show_settings),
        ]
        for text, callback in btns:
            def _safe_callback(c=callback):
                def _wrapper(instance):
                    try:
                        c()
                    except Exception as e:
                        self._show_message('错误', str(e))
                return _wrapper
            btn = Button(text=text, font_size=dp(12), on_press=_safe_callback())
            btn_grid.add_widget(btn)
        root.add_widget(btn_grid)
        Clock.schedule_once(self._init_board, 0.1)
        return root

    def _init_board(self, dt):
        self._update_status()
        self.board_widget.redraw()

    def _on_board_touch(self, x, y):
        if self.thinking or self.board.game_over:
            return
        if self.board.current_player != self.player_color:
            return
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
            except Exception:
                pass
        self._update_ui()
        if self.board.game_over:
            self._show_game_result()
            return
        if self.engine_connected and self.board.current_player == self.ai_color and not self.thinking:
            self._request_ai_move()

    def pass_move(self, *args):
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
        self._update_ui()
        if self.board.game_over:
            self._show_game_result()
            return
        if self.engine_connected and self.board.current_player == self.ai_color and not self.thinking:
            self._request_ai_move()

    def undo_move(self, *args):
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
        self._update_ui()

    def resign(self, *args):
        if self.board.game_over:
            return
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text='确定要认输吗？'))
        popup = Popup(title='认输', content=content, size_hint=(0.8, 0.4),
                      auto_dismiss=False)
        btn_box = BoxLayout(spacing=dp(10))
        yes_btn = Button(text='确定', on_press=lambda b: self._do_resign(popup))
        no_btn = Button(text='取消', on_press=lambda b: popup.dismiss())
        btn_box.add_widget(yes_btn)
        btn_box.add_widget(no_btn)
        content.add_widget(btn_box)
        popup.open()

    def _do_resign(self, popup):
        popup.dismiss()
        self.board.game_over = True
        winner = self.ai_color
        self.board.result = {'winner': winner, 'margin': 0, 'resign': True}
        self._update_status()
        winner_str = '黑方' if winner == BLACK else '白方'
        self._show_message('对局结束', f'{winner_str}胜（对方认输）')

    def calculate_score(self, *args):
        result = self.board.calculate_score()
        if result['winner'] == BLACK:
            winner_str = f'黑方胜 {result["margin"]:.1f} 目'
        elif result['winner'] == WHITE:
            winner_str = f'白方胜 {result["margin"]:.1f} 目'
        else:
            winner_str = '和棋'
        msg = (
            f'结果: {winner_str}\n\n'
            f'黑方: {result["black_score"]:.1f} 目\n'
            f'  领地: {result["territory"]["black_territory"]} 目\n'
            f'  提子: {result["territory"]["black_captures"]} 子\n\n'
            f'白方: {result["white_score"]:.1f} 目\n'
            f'  领地: {result["territory"]["white_territory"]} 目\n'
            f'  提子: {result["territory"]["white_captures"]} 子\n'
            f'  贴目: {self.board.komi} 目'
        )
        self._show_message('计算结果', msg)

    def new_game(self, *args):
        if self.thinking:
            return
        if self.board.move_count > 0:
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
            content.add_widget(Label(text='确定要开始新对局吗？\n当前对局记录将丢失。'))
            popup = Popup(title='新对局', content=content, size_hint=(0.8, 0.4),
                          auto_dismiss=False)
            btn_box = BoxLayout(spacing=dp(10))
            yes_btn = Button(text='确定', on_press=lambda b: self._do_new_game(popup))
            no_btn = Button(text='取消', on_press=lambda b: popup.dismiss())
            btn_box.add_widget(yes_btn)
            btn_box.add_widget(no_btn)
            content.add_widget(btn_box)
            popup.open()
        else:
            self._do_new_game(None)

    def _do_new_game(self, popup):
        if popup:
            popup.dismiss()
        self.board = GoBoard(
            size=self.config.get('board_size', 19),
            komi=self.config.get('komi', 6.5)
        )
        self.board_widget.set_board(self.board)
        if self.engine_connected:
            try:
                self.engine.set_board_size(self.board.size)
                self.engine.set_komi(self.board.komi)
                self.engine.clear_board()
            except Exception:
                pass
        self._update_ui()
        if self.engine_connected and self.ai_color == BLACK:
            self._request_ai_move()

    def toggle_color(self, *args):
        if self.thinking:
            return
        if self.board.move_count > 0:
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
            content.add_widget(Label(text='切换执子将重新开始对局，确定吗？'))
            popup = Popup(title='切换执子', content=content, size_hint=(0.8, 0.4),
                          auto_dismiss=False)
            btn_box = BoxLayout(spacing=dp(10))
            yes_btn = Button(text='确定', on_press=lambda b: self._do_toggle_color(popup))
            no_btn = Button(text='取消', on_press=lambda b: popup.dismiss())
            btn_box.add_widget(yes_btn)
            btn_box.add_widget(no_btn)
            content.add_widget(btn_box)
            popup.open()
        else:
            self._do_toggle_color(None)

    def _do_toggle_color(self, popup):
        if popup:
            popup.dismiss()
        self.player_color = WHITE if self.player_color == BLACK else BLACK
        self.ai_color = BLACK if self.ai_color == WHITE else WHITE
        self.config.set('player_color', 'black' if self.player_color == BLACK else 'white')
        self.config.save()
        self._do_new_game(None)

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
            Clock.schedule_once(lambda dt: self._on_ai_move(result), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_ai_error(str(e)), 0)

    def _on_ai_move(self, result):
        self.thinking = False
        if result == 'resign':
            self.board.game_over = True
            self.board.result = {'winner': self.player_color, 'margin': 0, 'resign': True}
            winner_str = '黑方' if self.player_color == BLACK else '白方'
            self._update_ui()
            self._show_message('对局结束', f'{winner_str}胜（对方认输）')
            return
        if result == 'pass':
            self.board.pass_move()
            self._update_ui()
            if self.board.game_over:
                self._show_game_result()
            return
        if result is None or not isinstance(result, tuple) or len(result) != 2:
            self._show_message('AI错误', f'AI返回了无效结果: {result}')
            return
        x, y = result
        success, captured = self.board.play_move(x, y)
        if not success:
            self._show_message('AI错误', 'AI生成了无效着法')
            return
        self._update_ui()
        if self.board.game_over:
            self._show_game_result()

    def _on_ai_error(self, error):
        self.thinking = False
        self._update_status()
        self._show_message('AI错误', f'AI思考出错: {error}')

    def _show_game_result(self):
        if self.board.result:
            result = self.board.result
        else:
            result = self.board.calculate_score()
        if result.get('resign'):
            winner_str = '黑方' if result['winner'] == BLACK else '白方'
            msg = f'{winner_str}胜（对方认输）'
        else:
            if result['winner'] == BLACK:
                winner_str = f'黑方胜 {result["margin"]:.1f} 目'
            elif result['winner'] == WHITE:
                winner_str = f'白方胜 {result["margin"]:.1f} 目'
            else:
                winner_str = '和棋'
            msg = (
                f'结果: {winner_str}\n\n'
                f'黑方: {result["black_score"]:.1f} 目\n'
                f'白方: {result["white_score"]:.1f} 目\n'
                f'贴目: {self.board.komi} 目'
            )
        self._show_message('对局结束', msg)

    def toggle_engine(self, *args):
        if self.thinking:
            return
        if self.engine_connected:
            self._disconnect_engine()
        else:
            self._connect_engine()

    def _connect_engine(self):
        katago_path = self.config.get('katago_path', '')
        if not katago_path:
            self._show_message('提示', '请先在设置中配置Katago路径')
            return
        if not os.path.isfile(katago_path):
            self._show_message('错误', f'Katago文件不存在:\n{katago_path}')
            return
        self.status_label.text = '正在连接...'
        t = threading.Thread(target=self._connect_engine_thread, daemon=True)
        t.start()

    def _connect_engine_thread(self):
        try:
            katago_path = self.config.get('katago_path', '')
            engine = KataGoEngine(
                katago_path=katago_path,
                config_path=self.config.get('config_path', ''),
                model_path=self.config.get('model_path', ''),
                analysis_threads=self.config.get('analysis_threads', 2),
                board_size=self.board.size,
                komi=self.board.komi,
            )
            engine.start()
            Clock.schedule_once(lambda dt: self._on_engine_connected(engine), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_engine_connect_failed(str(e)), 0)

    def _on_engine_connected(self, engine):
        self.engine = engine
        self.engine_connected = True
        self._sync_board_to_engine()
        self._update_status()
        if self.board.current_player == self.ai_color and not self.board.game_over:
            self._request_ai_move()

    def _on_engine_connect_failed(self, error):
        self.engine = None
        self.engine_connected = False
        self._update_status()
        self._show_message('连接失败', f'无法连接Katago引擎:\n{error}')

    def _disconnect_engine(self):
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
                try:
                    self.engine.send_command(f'play {GoBoard.color_to_str(color)} pass')
                except Exception:
                    pass
            else:
                x, y = move
                try:
                    self.engine.play_move(x, y, color)
                except Exception:
                    pass

    def _get_move_list(self):
        moves = []
        if len(self.board.history) == 0:
            if self.board.last_move:
                moves.append((BLACK, self.board.last_move))
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

    def show_settings(self, *args):
        SettingsPopup(self.config, self._on_settings_changed).open()

    def _on_settings_changed(self):
        if self.engine_connected:
            self._disconnect_engine()
        new_size = self.config.get('board_size', 19)
        new_komi = self.config.get('komi', 6.5)
        if new_size != self.board.size or new_komi != self.board.komi:
            if self.board.move_count > 0:
                self._show_message('设置变更', '棋盘大小或贴目已变更，新对局将生效')
            else:
                self.board = GoBoard(size=new_size, komi=new_komi)
                self.board_widget.set_board(self.board)
                self._update_ui()

    def _update_ui(self):
        self.board_widget.redraw()
        self._update_status()

    def _update_status(self):
        player_str = '黑方' if self.board.current_player == BLACK else '白方'
        self.info_label.text = f'当前: {player_str}'
        self.move_count_label.text = f'手数: {self.board.move_count}'
        self.black_captures_label.text = f'黑提: {self.board.captures[BLACK]}'
        self.white_captures_label.text = f'白提: {self.board.captures[WHITE]}'
        if self.thinking:
            self.status_label.text = 'AI思考中...'
        elif self.board.game_over:
            self.status_label.text = '对局结束'
        elif self.engine_connected:
            self.status_label.text = 'AI已连接'
        else:
            self.status_label.text = '未连接AI'

    def _show_message(self, title, message):
        try:
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
            content.add_widget(Label(text=str(message)))
            popup = Popup(title=str(title), content=content, size_hint=(0.85, 0.5))
            btn = Button(text='确定', size_hint_y=None, height=dp(40),
                         on_press=lambda b: popup.dismiss())
            content.add_widget(btn)
            popup.open()
        except Exception:
            pass


class SettingsPopup(Popup):
    def __init__(self, config, on_changed=None, **kwargs):
        super(SettingsPopup, self).__init__(**kwargs)
        self.config = config
        self.on_changed = on_changed
        self.title = '设置'
        self.size_hint = (0.9, 0.85)
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        self.katago_path_input = TextInput(
            text=self.config.get('katago_path', ''),
            hint_text='Katago 可执行文件路径',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(Label(text='Katago 路径:', halign='left', size_hint_y=None, height=dp(20)))
        content.add_widget(self.katago_path_input)
        self.config_path_input = TextInput(
            text=self.config.get('config_path', ''),
            hint_text='配置文件路径 (可选)',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(Label(text='配置文件:', halign='left', size_hint_y=None, height=dp(20)))
        content.add_widget(self.config_path_input)
        self.model_path_input = TextInput(
            text=self.config.get('model_path', ''),
            hint_text='权重模型路径 (可选)',
            multiline=False,
            size_hint_y=None,
            height=dp(40),
        )
        content.add_widget(Label(text='模型路径:', halign='left', size_hint_y=None, height=dp(20)))
        content.add_widget(self.model_path_input)
        detect_btn = Button(
            text='🔍 自动检测 Katago',
            size_hint_y=None,
            height=dp(40),
            on_press=self._auto_detect,
        )
        content.add_widget(detect_btn)
        size_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        size_box.add_widget(Label(text='棋盘大小:', size_hint_x=None, width=dp(80)))
        self.size_spinner = Spinner(
            text=str(self.config.get('board_size', 19)),
            values=['9', '13', '19'],
        )
        size_box.add_widget(self.size_spinner)
        content.add_widget(size_box)
        komi_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        komi_box.add_widget(Label(text='贴目:', size_hint_x=None, width=dp(80)))
        self.komi_spinner = Spinner(
            text=str(self.config.get('komi', 6.5)),
            values=['0', '3.5', '5.5', '6.5', '7.5'],
        )
        komi_box.add_widget(self.komi_spinner)
        content.add_widget(komi_box)
        threads_box = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        threads_box.add_widget(Label(text='分析线程:', size_hint_x=None, width=dp(80)))
        self.threads_input = TextInput(
            text=str(self.config.get('analysis_threads', 2)),
            multiline=False,
            input_filter='int',
        )
        threads_box.add_widget(self.threads_input)
        content.add_widget(threads_box)
        content.add_widget(Widget())
        btn_box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(10))
        ok_btn = Button(text='保存', on_press=self._save)
        cancel_btn = Button(text='取消', on_press=lambda b: self.dismiss())
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(ok_btn)
        content.add_widget(btn_box)
        self.content = content

    def _auto_detect(self, *args):
        try:
            paths = android_utils.auto_detect_paths()
            if paths['katago_path']:
                self.katago_path_input.text = paths['katago_path']
            if paths['model_path']:
                self.model_path_input.text = paths['model_path']
            if paths['config_path']:
                self.config_path_input.text = paths['config_path']
            if not paths['katago_path']:
                self._show_toast('未找到 Katago，请手动填写路径')
            else:
                self._show_toast('检测成功！')
        except Exception as e:
            self._show_toast(f'检测失败: {e}')

    def _show_toast(self, msg):
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.clock import Clock
        content = BoxLayout(padding=dp(20))
        content.add_widget(Label(text=msg))
        toast = Popup(title='提示', content=content, size_hint=(0.7, 0.2), auto_dismiss=True)
        toast.open()
        Clock.schedule_once(lambda dt: toast.dismiss(), 2)

    def _save(self, *args):
        self.config.set('katago_path', self.katago_path_input.text.strip())
        self.config.set('config_path', self.config_path_input.text.strip())
        self.config.set('model_path', self.model_path_input.text.strip())
        self.config.set('board_size', int(self.size_spinner.text))
        self.config.set('komi', float(self.komi_spinner.text))
        try:
            threads = int(self.threads_input.text)
            if threads < 1:
                threads = 1
            self.config.set('analysis_threads', threads)
        except ValueError:
            pass
        self.config.save()
        if self.on_changed:
            self.on_changed()
        self.dismiss()


if __name__ == '__main__':
    GoGameApp().run()
