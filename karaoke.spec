# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file cho Karaoke Manager
# Build: pyinstaller karaoke.spec --clean

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ─── Dữ liệu cần đưa vào bundle ──────────────────────────────────────────────
datas = [
    # Toàn bộ Django project (templates, static, migrations, v.v.)
    (os.path.join('karaoke_app', 'templates'),     os.path.join('karaoke_app', 'templates')),
    (os.path.join('karaoke_app', 'static'),        os.path.join('karaoke_app', 'static')),
    (os.path.join('karaoke_app', 'staticfiles'),   os.path.join('karaoke_app', 'staticfiles')),
    (os.path.join('karaoke_app', 'karaoke'),       os.path.join('karaoke_app', 'karaoke')),
    (os.path.join('karaoke_app', 'core'),          os.path.join('karaoke_app', 'core')),
    # Django built-in templates và static
    *collect_data_files('django', includes=['**/*.html', '**/*.css', '**/*.js']),
    # escpos capabilities.json (bắt buộc khi import escpos)
    *collect_data_files('escpos'),
]

# ─── Hidden imports Django cần ────────────────────────────────────────────────
hiddenimports = [
    # Django core
    'django.contrib.admin',
    'django.contrib.admin.apps',
    'django.contrib.auth',
    'django.contrib.auth.apps',
    'django.contrib.contenttypes',
    'django.contrib.contenttypes.apps',
    'django.contrib.sessions',
    'django.contrib.sessions.apps',
    'django.contrib.sessions.backends.db',
    'django.contrib.messages',
    'django.contrib.messages.apps',
    'django.contrib.staticfiles',
    'django.contrib.staticfiles.apps',
    'django.template.loaders.filesystem',
    'django.template.loaders.app_directories',
    'django.template.backends.django',
    'django.db.backends.sqlite3',
    # App modules
    'core',
    'core.apps',
    'core.models',
    'core.admin',
    'core.decorators',
    'core.pricing',
    'core.printing',
    'core.urls',
    'core.views',
    'core.views.auth',
    'core.views.rooms',
    'core.views.payment',
    'core.views.reports',
    'core.views.admin_views',
    'core.management',
    'core.management.commands',
    'core.management.commands.create_admin',
    'core.migrations',
    'core.migrations.0001_initial',
    'core.migrations.0002_activitylog',
    'core.migrations.0003_cancel_room',
    # Django management commands
    'django.core.management.commands.migrate',
    'django.contrib.staticfiles.management.commands.collectstatic',
    # Django password hashers
    'django.contrib.auth.hashers',
    'django.contrib.auth.password_validation',
    # Django middleware & handlers
    'django.core.handlers.wsgi',
    'django.contrib.sessions.middleware',
    'django.contrib.messages.storage.fallback',
    'django.contrib.messages.storage.cookie',
    'django.contrib.messages.storage.session',
    # Third-party
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.writer.excel',
    'escpos',
    'escpos.printer',
    'PIL',
    'PIL.Image',
    # SQLite
    '_sqlite3',
    # Windows printing
    'win32print',
    'win32api',
    'pywintypes',
    # Django utils
    'django.utils.timezone',
    'django.utils.translation',
    'django.utils.encoding',
    'sqlparse',
    'asgiref',
    'asgiref.sync',
    'asgiref.local',
]

a = Analysis(
    ['launcher.py'],
    pathex=['.', 'karaoke_app'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KaraokeManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # False = ẩn cửa sổ CMD, chạy nền như ứng dụng Windows
    icon=None,          # Thay bằng 'icon.ico' nếu có
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KaraokeManager',
)
