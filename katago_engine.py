import subprocess
import threading
import queue
import time
import os
from go_board import GoBoard, BLACK, WHITE


class KataGoEngine:
    def __init__(self, katago_path, config_path=None, model_path=None,
                 analysis_threads=2, board_size=19, komi=6.5):
        self.katago_path = katago_path
        self.config_path = config_path
        self.model_path = model_path
        self.analysis_threads = analysis_threads
        self.board_size = board_size
        self.komi = komi
        self.process = None
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.reader_thread = None
        self.writer_thread = None
        self.running = False
        self.command_id = 0
        self._lock = threading.Lock()

    def is_available(self):
        if not self.katago_path:
            return False
        return os.path.isfile(self.katago_path)

    def start(self):
        if self.running:
            return True
        if not self.is_available():
            raise FileNotFoundError(f"Katago executable not found: {self.katago_path}")
        try:
            st = os.stat(self.katago_path)
            os.chmod(self.katago_path, st.st_mode | 0o111)
        except Exception:
            pass
        args = [self.katago_path, 'gtp']
        if self.config_path and os.path.exists(self.config_path):
            args.extend(['-config', self.config_path])
        if self.model_path and os.path.exists(self.model_path):
            args.extend(['-model', self.model_path])
        args.extend(['-analysis-threads', str(self.analysis_threads)])
        katago_dir = os.path.dirname(self.katago_path)
        try:
            env = os.environ.copy()
            env['LD_LIBRARY_PATH'] = f"{katago_dir}:{env.get('LD_LIBRARY_PATH', '')}"
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=katago_dir,
                env=env,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start Katago: {e}")
        self.running = True
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.writer_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.reader_thread.start()
        self.writer_thread.start()
        self._send_command('name')
        self._send_command('version')
        self._send_command(f'boardsize {self.board_size}')
        self._send_command(f'komi {self.komi}')
        self._send_command('clear_board')
        return True

    def stop(self):
        self.running = False
        if self.process:
            try:
                self.process.stdin.write('quit\n')
                self.process.stdin.flush()
            except Exception:
                pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        self.reader_thread = None
        self.writer_thread = None

    def _read_loop(self):
        try:
            while self.running and self.process:
                line = self.process.stdout.readline()
                if not line:
                    break
                self.output_queue.put(line.strip())
        except Exception:
            pass

    def _write_loop(self):
        try:
            while self.running and self.process:
                cmd = self.input_queue.get()
                if cmd is None:
                    break
                self.process.stdin.write(cmd + '\n')
                self.process.stdin.flush()
        except Exception:
            pass

    def _send_command(self, command):
        with self._lock:
            self.command_id += 1
            cmd_id = self.command_id
            full_cmd = f'{cmd_id} {command}'
            self.input_queue.put(full_cmd)
            response_lines = []
            while True:
                try:
                    line = self.output_queue.get(timeout=60)
                except queue.Empty:
                    raise TimeoutError(f"Timeout waiting for response to: {command}")
                if line.startswith(f'={cmd_id}'):
                    response_lines.append(line[len(f'={cmd_id}'):].strip())
                    break
                elif line.startswith(f'?{cmd_id}'):
                    error_msg = line[len(f'?{cmd_id}'):].strip()
                    raise RuntimeError(f"GTP error: {error_msg}")
                elif line.startswith('=') or line.startswith('?'):
                    continue
                else:
                    continue
            while True:
                try:
                    line = self.output_queue.get(timeout=0.1)
                    if not line:
                        break
                    if line.startswith('=') or line.startswith('?'):
                        self.output_queue.put(line)
                        break
                    response_lines.append(line)
                except queue.Empty:
                    break
            return '\n'.join(response_lines).strip()

    def send_command(self, command):
        return self._send_command(command)

    def clear_board(self):
        self._send_command('clear_board')

    def set_board_size(self, size):
        self.board_size = size
        self._send_command(f'boardsize {size}')

    def set_komi(self, komi):
        self.komi = komi
        self._send_command(f'komi {komi}')

    def play_move(self, x, y, color):
        gtp_coord = GoBoard.coord_to_gtp(x, y, self.board_size)
        color_str = 'black' if color == BLACK else 'white'
        self._send_command(f'play {color_str} {gtp_coord}')

    def gen_move(self, color):
        color_str = 'black' if color == BLACK else 'white'
        response = self._send_command(f'genmove {color_str}')
        response = response.strip().upper()
        if response == 'RESIGN':
            return 'resign'
        if response == 'PASS':
            return 'pass'
        coord = GoBoard.gtp_to_coord(response, self.board_size)
        if coord is None:
            raise RuntimeError(f"Invalid move from Katago: {response}")
        return coord

    def undo(self):
        self._send_command('undo')

    def final_score(self):
        return self._send_command('final_score')

    def show_board(self):
        return self._send_command('showboard')

    def list_commands(self):
        return self._send_command('list_commands')

    def analyze_position(self, board, max_visits=None):
        moves_str = ''
        for move in board.history:
            pass
        return None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
