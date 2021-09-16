#!/usr/bin/env python3
PROGRAM = 'LSComicreader'

import os
import platform
import sys

def set_enviorment_variables():
    """
    # * == set None for default value
    """
    os.environ['PROGRAM_NAME']         = PROGRAM
    os.environ['DATABASE_FILENAME']    = PROGRAM + '_database.sqlite'
    os.environ['DATABASE_FOLDER']      = '/home/plutonergy/Documents' # must exist, else: program-folder *
    os.environ['DATABASE_SUBFOLDER']   = PROGRAM # if preset, will be added to DATABASE_FOLDER *
    os.environ['TMP_DIR']              = '/mnt/ramdisk' # must exist, else: systems tmp-folder *
    os.environ['INI_FILENAME']         = 'settings.ini' # program-folder

def set_program_root_folder_in_eviorment():
    """
    also changes dir to __file__ directory
    """
    if __file__[-1] not in ['/', '\\']:
        if platform.system() == "Windows":
            os.chdir(os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('\\')])
            INI_FILE_DIR = os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('\\') + 1]
        else:
            os.chdir(os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('/')])
            INI_FILE_DIR = os.path.realpath(__file__)[0:os.path.realpath(__file__).rfind('/') + 1]

        os.environ['INI_FILE_DIR'] = INI_FILE_DIR

set_enviorment_variables()
set_program_root_folder_in_eviorment()

from bscripts.main import LSComicreaderMain
from PyQt5 import QtWidgets

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LSComicreaderMain()
    app.exec_()