"""
Nebulatro - py2app setup script
Creates a standalone macOS application bundle

DEVELOPMENT SETUP:
1. Create venv: python3 -m venv venv
2. Activate: source venv/bin/activate
3. Install deps: pip install -r requirements.txt
4. Install tkinter: brew install python-tk@3.13
5. Run: python3 nebulatro.py

BUILD STANDALONE APP:
1. Install py2app: pip install py2app
2. Build: python setup.py py2app
3. App created in: dist/Nebulatro.app
4. Move to Applications or run: open dist/Nebulatro.app

ICON (optional):
- Place app_icon.icns or app_icon.png in project root
- Icon will be included in build automatically

REBUILD:
- Clean: rm -rf build dist
- Build: python setup.py py2app
"""

from setuptools import setup

APP = ['nebulatro.py']
DATA_FILES = [
    'card_order_config.json',
    'resource_mapping.json',
    'sprite_loader.py',
]
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PIL', 'tkinter'],
    'includes': ['PIL.Image', 'PIL.ImageTk'],
    'resources': ['resources', 'assets'],
    'iconfile': 'app_icon.icns' if __import__('pathlib').Path('app_icon.icns').exists() else None,
    'plist': {
        'CFBundleName': 'Nebulatro',
        'CFBundleDisplayName': 'Nebulatro',
        'CFBundleIdentifier': 'com.nebulatro.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    }
}

setup(
    name='Nebulatro',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
