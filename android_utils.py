import os
import sys
import shutil


def is_android():
    try:
        from jnius import autoclass
        return True
    except ImportError:
        pass
    return 'ANDROID_ARGUMENT' in os.environ or hasattr(sys, 'getandroidapilevel')


def get_app_dir():
    if is_android():
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            files_dir = activity.getFilesDir().getAbsolutePath()
            return files_dir
        except Exception:
            pass
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except Exception:
            pass
    return os.path.dirname(os.path.abspath(__file__))


def get_external_dir():
    if is_android():
        try:
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            ext_dir = activity.getExternalFilesDir(None)
            if ext_dir:
                return ext_dir.getAbsolutePath()
        except Exception:
            pass
        try:
            from android.storage import primary_external_storage_path
            return primary_external_storage_path()
        except Exception:
            pass
    return os.path.dirname(os.path.abspath(__file__))


def get_katago_dir():
    base = get_app_dir()
    katago_dir = os.path.join(base, 'katago')
    if not os.path.exists(katago_dir):
        os.makedirs(katago_dir, exist_ok=True)
    return katago_dir


def get_assets_dir():
    if is_android():
        return '/data/data/org.example.gogame/files/app/assets/katago'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'assets', 'katago')


def ensure_executable(path):
    if path and os.path.exists(path):
        try:
            st = os.stat(path)
            os.chmod(path, st.st_mode | 0o111)
            return True
        except Exception:
            return False
    return False


def copy_assets_katago():
    assets_dir = get_assets_dir()
    target_dir = get_katago_dir()
    if not os.path.exists(assets_dir):
        return False, f'Assets directory not found: {assets_dir}'
    os.makedirs(target_dir, exist_ok=True)
    copied = 0
    try:
        for item in os.listdir(assets_dir):
            src = os.path.join(assets_dir, item)
            dst = os.path.join(target_dir, item)
            if os.path.isfile(src):
                if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                    shutil.copy2(src, dst)
                    copied += 1
                if item.startswith('katago') and not item.endswith('.cfg') and not item.endswith('.gz'):
                    ensure_executable(dst)
    except Exception as e:
        return False, str(e)
    return True, f'Copied {copied} files'


def find_katago_executable():
    katago_dir = get_katago_dir()
    candidates = []
    if os.path.exists(katago_dir):
        for f in sorted(os.listdir(katago_dir)):
            if f == 'README.txt' or f.endswith('.cfg') or f.endswith('.gz'):
                continue
            full = os.path.join(katago_dir, f)
            if os.path.isfile(full):
                candidates.append(full)
    extra_paths = [
        '/data/local/tmp/katago',
        '/system/bin/katago',
    ]
    for p in extra_paths:
        if os.path.exists(p):
            candidates.append(p)
    for path in candidates:
        ensure_executable(path)
    return candidates[0] if candidates else ''


def find_model_file():
    katago_dir = get_katago_dir()
    if not os.path.exists(katago_dir):
        return ''
    for f in sorted(os.listdir(katago_dir)):
        if f.endswith('.bin.gz') or f.endswith('.txt.gz'):
            return os.path.join(katago_dir, f)
    return ''


def find_config_file():
    katago_dir = get_katago_dir()
    if not os.path.exists(katago_dir):
        return ''
    for f in sorted(os.listdir(katago_dir)):
        if f.endswith('.cfg') or f.endswith('.toml'):
            return os.path.join(katago_dir, f)
    default = os.path.join(katago_dir, 'default_gtp.cfg')
    if os.path.exists(default):
        return default
    return ''


def auto_detect_paths():
    copy_assets_katago()
    return {
        'katago_path': find_katago_executable(),
        'model_path': find_model_file(),
        'config_path': find_config_file(),
    }
