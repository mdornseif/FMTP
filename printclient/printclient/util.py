
#~ import subprocess
import logging
import win32print
import win32api


PRINTER_TYPE_LIST = [
    (win32print.PRINTER_ENUM_SHARED, 'shared'),
    (win32print.PRINTER_ENUM_LOCAL, 'local'),
    (win32print.PRINTER_ENUM_CONNECTIONS, 'network')
]


def list_printers():
    printers = []
    default_printer_name = win32print.GetDefaultPrinter()
    for printer_type in PRINTER_TYPE_LIST:
        try:
            for flags, description, name, comment in list(win32print.EnumPrinters(printer_type[0], None, 1)):
                printer = dict(
                    name=name,
                    description=description,
                    comment=comment,
                    type=printer_type[1],
                    flags=flags,
                    is_default=name==default_printer_name,
                )
                printers.append(printer)
        except:
            pass
    return printers


def gsprint(file_name, log, gsprint, printer, orientation, duplex, copies, **config):
    params = ''
    if printer:
        params += ' -printer "%s"' % printer
    if orientation:
        params += ' -landscape'
    else:
        params += ' -portrait'
    if duplex == 1:
        params += ' -duplex_vertical'
    if duplex == 2:
        params += ' -duplex_horizontal'
    if copies > 1:
        params += ' -copies %d' % copies
    logging.info('executing: %s with args %s' % (gsprint, params + ' ' + file_name))
    win32api.ShellExecute(
        0,
        'open',
        '"' + gsprint + '"',
        params + ' ' + file_name,
        '.',
        0
    )
    #~ proc = subprocess.Popen(
        #~ ['"' + config['gsprint'] + '"'] + params.split(),
        #~ stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
        #~ shell=True,
    #~ )
    #~ stdout, stderr = proc.communicate()
    #~ if proc.returncode:
        #~ msg = '%s exited with return code %s!' % (params, proc.returncode)
        #~ log(msg)
        #~ log(stdout)


if __name__ == '__main__':
    print list_printers()
