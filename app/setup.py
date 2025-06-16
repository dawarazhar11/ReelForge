from setuptools import setup

APP = ['hume.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['streamlit', 'PIL', 'numpy', 'websocket'],
    'plist': {
        'CFBundleName': 'AI Money Printer',
        'CFBundleDisplayName': 'AI Money Printer',
        'CFBundleIdentifier': 'com.aimoney.printer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 