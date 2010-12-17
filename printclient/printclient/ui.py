

import os
import sys
import traceback
import datetime
import logging
import threading
import Queue

import wx
import  wx.lib.newevent

from .api import PrintServerAPI
#~ from .testapi import PrintServerAPI


MENU_LOG = wx.NewId()
MENU_PAUSE = wx.NewId()
MENU_RESTORE = wx.NewId()
MENU_SETTINGS = wx.NewId()
MENU_CLOSE = wx.NewId()


DEFAULT_CONFIG = dict(
    server_url='http://localhost:8080/printers/test/jobs/',
    #~ gsprint='c:\Program Files\Ghostgum\gsview\gsprint.exe',
    printer='', orientation=0, copies=1, duplex=0,
    username='', password='',
)


def save_config(**kw):
    conf = wx.ConfigBase.Get()
    for a, v in kw.iteritems():
        if isinstance(v, int):
            conf.WriteInt(a, v)
        elif isinstance(v, basestring):
            conf.Write(a, v)


def load_config(**kw):
    conf = wx.ConfigBase.Get()
    res = {}
    for a, v in kw.iteritems():
        if isinstance(v, int):
            n = conf.ReadInt(a, v)
        elif isinstance(v, basestring):
            n = conf.Read(a, v)
        else:
            if __debug__: raise TypeError, type(v)
        res[a] = n
    return res


class PrintClientFrame(wx.Frame):
    
    title = "Print Service"
    
    wait_time = 500
    pause = False
    settings_dialog = None
    
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, -1, title, size = (970, 720),
                          style=wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        
        self.config = load_config(**DEFAULT_CONFIG)
        
        self.api = PrintServerAPI(self.config)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.check_button = wx.Button(self, wx.NewId(), 'Check')
        h_sizer.Add(self.check_button, flag=wx.RIGHT, border=5)

        self.clear_button = wx.Button(self, wx.NewId(), 'Clear')
        h_sizer.Add(self.clear_button, flag=wx.RIGHT, border=5)
        
        self.next_check_text = wx.StaticText(self, -1, '')
        h_sizer.Add(self.next_check_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.GROW|wx.EXPAND, border=5)
        
        self.log = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE|wx.TE_READONLY)
        wx.Log_SetActiveTarget(wx.LogTextCtrl(self.log))
        self.sizer.Add(self.log, 1, flag=wx.ALL|wx.GROW|wx.EXPAND, border=0)

        self.taskbar_icon = PrintClientTaskBarIcon(self)
        
        icon = self.taskbar_icon.MakeIcon(
            wx.ImageFromBitmap(
                wx.ArtProvider.GetBitmap(wx.ART_PRINT, wx.ART_OTHER, (16, 16))
            )
        )
        self.SetIcon(icon)

        self.SetMinSize((640,480))
        self.Centre(wx.BOTH)
        
        self.check_button.Bind(wx.EVT_BUTTON, self.on_check)
        self.clear_button.Bind(wx.EVT_BUTTON, self.on_clear)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.SetSizer(self.sizer)
        
        self.next_check = datetime.datetime.now()
        wx.CallLater(500, self.process)
    
    def info(self, message):
        wx.LogMessage(message)
        logging.info(message)

    def error(self, message):
        wx.LogError(message)
        logging.error(message)
    
    next_check = None
    
    def process(self, force=False):
        if not force and self.pause:
            self.wait_time = 500
            wx.CallLater(500, self.process)
        elif force or datetime.datetime.now() >= self.next_check:
            try:
                jobs = self.api.list_jobs()
            except Exception, E:
                self.error('Failed fetching job list')
                logging.exception(E)
                if not force:
                    self.set_wait_time(3000)
                    wx.CallLater(3000, self.process)
            else:
                if jobs:
                    for job in jobs:
                        try:
                            job.fetch()
                        except Exception, E:
                            self.error('Failed fetching job -- %s' % getattr(job, 'url', None))
                            logging.exception(E)
                        else:
                            try:
                                self.print_job(job)
                            except Exception, E:
                                self.error('Failed printing job -- %s' % getattr(job, 'url', None))
                                logging.exception(E)
                            else:
                                self.info('Job printed successfully -- %s' % getattr(job, 'url', None))
                                self.delete_job(job)
                    if not force:
                        self.set_wait_time(500)
                else:
                    if not force:
                        time = self.wait_time * 2
                        if time > 300000:
                            time = 300000
                        self.set_wait_time(time)
                if not force:
                    wx.CallLater(500, self.process)
    
    def set_wait_time(self, time):
        self.wait_time = time
        self.next_check = next_check = datetime.datetime.now() + datetime.timedelta(microseconds=time)
        text = 'Next check on: %s' % next_check.strftime('%d-%m-%Y %H:%M:%S')
        self.next_check_text.SetLabel(text)
    
    def on_close(self, event):
        self.Hide()
    
    def on_clear(self, event):
        self.log.Clear()
    
    def on_check(self, event):
        self.process(True)
    
    def print_job(self, job):
        #~ return 
        try:
            from .util import gsprint
        except ImportError:
            pass
        else:
            gsprint(job.file_name, self.info, 'gs/gsprint.exe', **self.config)
    
    def delete_job(self, job, repeat=5):
        try:
            job.delete()
        except Exception, E:
            self.error('Failed deleting job -- %s' % getattr(job, 'url', None))
            logging.exception(E)
            if repeat:
                wx.CallLater(2000, self.delete_job, job, repeat-1)
        else:
            self.info('Job deleted -- %s' % getattr(job, 'url', None))
            wx.CallLater(120000, self.delete_temp_file, job)
    
    def delete_temp_file(self, job):
        try:
            os.remove(job.file_name)
        except Exception, E:
            logging.exception(E)


class PrintSettingsDialog(wx.Dialog):
    
    title = "Settings"
    
    def __init__(self, parent, config={}):
        wx.Dialog.__init__(self, parent, -1, title=self.title,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE)
        
        self.config = config
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        
        #~ h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        #~ h_sizer.Add(wx.StaticText(self, -1, 'gsprint location: '), flag=wx.ALIGN_CENTER_VERTICAL)
        #~ self.gsprint = wx.TextCtrl(self, -1, size=(400,-1))
        #~ h_sizer.Add(self.gsprint)
        #~ self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, -1, 'Server URL: '), flag=wx.ALIGN_CENTER_VERTICAL)
        self.server_url = wx.TextCtrl(self, -1, size=(400,-1))
        h_sizer.Add(self.server_url)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, -1, 'Username: '), flag=wx.ALIGN_CENTER_VERTICAL)
        self.username = wx.TextCtrl(self, -1, size=(400,-1))
        h_sizer.Add(self.username)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, -1, 'Password: '), flag=wx.ALIGN_CENTER_VERTICAL)
        self.password = wx.TextCtrl(self, -1, size=(400,-1), style=wx.TE_PASSWORD)
        h_sizer.Add(self.password)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, -1, 'Printer: '), flag=wx.ALIGN_CENTER_VERTICAL)
        #~ self.printer = wx.TextCtrl(self, -1, size=(400,-1))
        self.printer = wx.Choice(self, -1, size=(400, -1))
        h_sizer.Add(self.printer)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(wx.StaticText(self, -1, 'Copies: '), flag=wx.ALIGN_CENTER_VERTICAL)
        self.copies = wx.SpinCtrl(self, -1, "", size=(400, -1))
        self.copies.SetRange(1, 100)
        self.copies.SetValue(1)
        h_sizer.Add(self.copies)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.orientation = wx.RadioBox(
            self, -1, "Orientation", wx.DefaultPosition, wx.DefaultSize,
            ['Portrait', 'Landscape'], 2, wx.RA_SPECIFY_COLS
        )
        h_sizer.Add(self.orientation, flag=wx.ALL, border=5)
        self.duplex = wx.RadioBox(
            self, -1, "Duplex", wx.DefaultPosition, wx.DefaultSize,
            ['No', 'Horizontal', 'Vertical'], 3, wx.RA_SPECIFY_COLS
        )
        h_sizer.Add(self.duplex, flag=wx.ALL, border=5)
        self.sizer.Add(h_sizer, flag=wx.ALL|wx.ALIGN_RIGHT, border=5)
        
        
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ok = wx.Button(self, wx.ID_OK, 'OK')
        h_sizer.Add(self.ok, flag=wx.ALL, border=5)
        self.cancel = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        h_sizer.Add(self.cancel, flag=wx.ALL, border=5)
        self.sizer.Add(h_sizer, flag=wx.ALL, border=5)
        self.ok.Bind(wx.EVT_BUTTON, self.on_button)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_button)
        
        self.SetSizerAndFit(self.sizer)
        
        self.Bind(wx.EVT_WINDOW_DESTROY, self.on_destroy)
        
        self.boot()
        
        self.Centre(wx.BOTH)
        
    
    def boot(self):
        self.username.SetValue(self.config['username'])
        self.password.SetValue(self.config['password'])
        self.copies.SetValue(self.config['copies'])
        self.orientation.SetSelection(int(self.config['orientation']))
        self.duplex.SetSelection(int(self.config['duplex']))
        self.server_url.SetValue(self.config['server_url'])
        #~ self.gsprint.SetValue(self.config['gsprint'])
        try:
            from .util import list_printers
        except ImportError:
            self.printers = printers = []
        else:
            self.printers = printers = list_printers()
        for i,p in enumerate(printers):
            self.printer.Append(p['name'])
            if p['name'] == self.config['printer']:
                self.printer.SetSelection(i)
    
    def save(self):
        if self.printers:
            printer = self.printers[self.printer.GetSelection()]['name']
        else:
            printer = ''
        self.config.update(
            dict(copies=int(self.copies.GetValue()),
                 orientation=self.orientation.GetSelection(),
                 duplex=int(self.duplex.GetSelection()),
                 server_url=self.server_url.GetValue(),
                 #~ gsprint=self.gsprint.GetValue(),
                 username=self.username.GetValue(),
                 password=self.password.GetValue(),
                 printer=printer)
        )
        save_config(**self.config)
        
    def on_button(self,  event):
        if event.GetEventObject() is self.ok:
            self.save()
        self.Destroy()
    
    def on_destroy(self, event):
        self.GetParent().settings_dialog = None
        event.Skip()


class PrintClientTaskBarIcon(wx.TaskBarIcon):
    
    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        icon = self.MakeIcon(
            wx.ImageFromBitmap(
                wx.ArtProvider.GetBitmap(wx.ART_PRINT, wx.ART_OTHER, (16, 16))
            )
        )
        self.SetIcon(icon, frame.title)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.on_activate)
        self.Bind(wx.EVT_MENU, self.on_activate, id=MENU_LOG)
        self.Bind(wx.EVT_MENU, self.on_pause, id=MENU_PAUSE)
        self.Bind(wx.EVT_MENU, self.on_settings, id=MENU_SETTINGS)
        self.Bind(wx.EVT_MENU, self.on_close, id=MENU_CLOSE)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(MENU_LOG, "View Log")
        menu.Append(MENU_PAUSE, 'Restore' if self.frame.pause else 'Pause')
        menu.Append(MENU_SETTINGS, "Settings")
        menu.Append(MENU_CLOSE,   "Close")
        return menu

    def MakeIcon(self, img):
        img = img.Scale(16, 16)
        icon = wx.IconFromBitmap(img.ConvertToBitmap())
        return icon

    def on_activate(self, evt):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
            self.frame.Maximize()
            self.frame.Raise()
        else:
            self.frame.Hide()
    
    def on_pause(self, evt):
        self.frame.pause = not self.frame.pause
        if self.frame.pause:
            self.frame.next_check_text.SetLabel('Paused')
    
    def on_close(self, evt):
        wx.CallAfter(self.close_app)
    
    def on_settings(self, event):
        if not self.frame.settings_dialog:
            dialog = PrintSettingsDialog(self.frame, self.frame.config)
            self.frame.settings_dialog = dialog
            dialog.Show()
    
    def close_app(self):
        if self.frame.settings_dialog:
            self.frame.settings_dialog.Destroy()
            self.frame.settings_dialog = None
        self.frame.Destroy()
        self.Destroy()


class PrintClientApp(wx.App):
    
    def OnInit(self):
        frame = PrintClientFrame(None, PrintClientFrame.title)
        self.SetVendorName('HUDORA')
        self.SetAppName("Print Service")
        frame.Hide()
        return True
