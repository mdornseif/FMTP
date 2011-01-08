
import sys
import os
from distutils.core import setup
import py2exe

import wxversion
wxversion.select('2.8-unicode')
sys.path += ['c:/Python25/lib/site-packages/wx-2.8-msw-unicode']
sys.argv += ['py2exe', '-q']

PACKAGES = [
    'encodings', 'compiler',  'threading', 'Queue',
    'wx', 'subprocess',
    'pywintypes',
]
INCLUDES = [
    'wxversion', 'httplib', 'urllib2',
]
EXCLUDES = [
    'hotshot', 'win32gui', 'win32ui', 'PIL',
    'Tkinter', 'ImagingTk', 'PIL.ImagingTk', 'PIL._imagingtk',
    'Pyrex', 'mx', 'cairo', 'elementtree',
]


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.version = '0.1.0'
        self.company_name = "HUDORA"
        self.copyright = "(c) 2010 HUDORA"
        self.name = "IPS Client"

TARGET = Target(
    dest_base='ipsclient',
    script='run.py',
    description="""IPS Client - a client for a FMTP based printing system""",
    #~ other_resources=[
        #~ (24, 1, (RESOURCES_DIR / 'manifest.xml').bytes()),
    #~ ],
    #~ icon_resources = [
        #~ (1, 'database.ico'),
    #~ ],
)


setup(
    name="ipsclient",
    windows=[TARGET],
    data_files=[
        ('.', ['logging.ini']),
    ],
    options={
        "py2exe": {
            'compressed': 1,
            'optimize': 2,
            'packages': PACKAGES,
            'includes': INCLUDES,
            'excludes': EXCLUDES,
        }
    },
    zipfile='support/libs.zip',
)
os.remove("dist/support/UxTheme.dll")
os.remove("dist/w9xpopen.exe")
