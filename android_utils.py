import os
import sys
import shutil


def is_android():
    return 'ANDROID_ARGUMENT' in os.environ or hasattr(sys, 'getandroidapilevel')


def get_app_dir():
    if is_android():
        from android.storage import app_storage_path
        return app_storage_path()
    return os.path.dirname(os.path.abspath(__file__))


def get_files_dir():
    if is_android():
        from android.storage import primary_external_storage_path
        try:
            return primary_external_storage_path()
        except Exception:
            return get_app_dir()
    return os.path.dirname(os.path.abspath(__file__))


def get_katago_dir():
    base = get_app_dir()
    katago_dir = os.path.join(base, 'katago')
    if not os.path.exists(katago_dir):
        os.makedirs(katago_dir, exist_ok=True)
    return katago_dir


def get_katago_executable_path():
    katago_dir = get_katago_dir()
    candidates = [
        os.path.join(katago_dir, 'katago'),
        os.path.join(katago_dir, 'katago-arm64'),
        os.path.join(katago_dir, 'katago-android'),
        '/data/local/tmp/katago',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                os.chmod(path, 0o755)
            except Exception:
                pass
            return path
    return ''


def get_default_model_path():
    katago_dir = get_katago_dir()
    for f in os.listdir(katago_dir) if os.path.exists(katago_dir) else []:
        if f.endswith('.bin.gz') or f.endswith('.txt.gz'):
            return os.path.join(katago_dir, f)
    return ''


def get_default_config_path():
    katago_dir = get_katago_dir()
    config_path = os.path.join(katago_dir, 'default_gtp.cfg')
    if os.path.exists(config_path):
        return config_path
    return ''


def ensure_executable(path):
    if path and os.path.exists(path):
        try:
            st = os.stat(path)
            os.chmod(path, st.st_mode | 0o111)
            return True
        except Exception:
            return False
    return False


def copy_assets_to_app_dir(asset_dir, target_dir=None):
    if target_dir is None:
        target_dir = get_katago_dir()
    if not os.path.exists(asset_dir):
        return False
    os.makedirs(target_dir, exist_ok=True)
    for item in os.listdir(asset_dir):
        src = os.path.join(asset_dir, item)
        dst = os.path.join(target_dir, item)
        if os.path.isfile(src):
            if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
                shutil.copy2(src, dst)
                if item.startswith('katago'):
                    ensure_executable(dst)
    return True
