
import wx
from printclient.ui import PrintClientApp

from logging.config import fileConfig
fileConfig('logging.ini')

app = PrintClientApp(False)
app.MainLoop()
