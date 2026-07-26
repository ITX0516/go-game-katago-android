import json
import os


DEFAULT_CONFIG = {
    'katago_path': '',
    'config_path': '',
    'model_path': '',
    'analysis_threads': 2,
    'board_size': 19,
    'komi': 6.5,
    'player_color': 'black',
    'ai_level': 'medium',
    'show_coordinates': True,
    'show_last_move': True,
    'show_captures': True,
}


class Config:
    def __init__(self, config_file=None):
        if config_file is None:
            config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        self.config_file = config_file
        self._config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self._config.update(user_config)
            except Exception:
                pass

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key, default=None):
        return self._config.get(key, default)

    def set(self, key, value):
        self._config[key] = value

    def __getitem__(self, key):
        return self._config[key]

    def __setitem__(self, key, value):
        self._config[key] = value
