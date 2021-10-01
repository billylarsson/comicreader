
BTN_ON = 'green'
BTN_OFF = 'gray'
BTN_SHINE_GREEN = 'lightGreen'
BTN_SHINE = 'lightBlue'
BTN_SHADE = 'gray'

TXT_SHINE = 'white'
TXT_SHADE = 'gray'
TXT_BLACK = 'black'
TXT_DARKTRANS = 'rgba(30,30,30,245)'

DARKRED = 'rgb(115, 10, 10)'

JOB_SUCCESS = 'yellow'
JOB_STOPPED = 'orange'
JOB_ERROR = 'red'


UNREAD_B_1 = BTN_SHINE
UNREAD_C_1 = 'black'

UNREAD_B_0 = 'darkGray'
UNREAD_C_0 = 'gray'

BOOKMARKED_B_1 = 'yellow'
BOOKMARKED_C_1 = 'black'

BOOKMARKED_B_0 = 'orange'
BOOKMARKED_C_0 = 'black'

CURRENT_B_1 = 'cyan'
CURRENT_C_1 = 'black'

CURRENT_B_0 = 'darkCyan'
CURRENT_C_0 = 'black'

READ_B_1 = BTN_SHINE
READ_C_1 = 'black'

READ_B_0 = 'rgb(120,120,120)'
READ_C_0 = 'rgb(60,60,60)'

import os
from bscripts.tricks import tech as t
files = []
rows = 0
filecount = 0
for walk in os.walk('/home/plutonergy/Coding/PythonComicreader'):
    files += [walk[0] + '/' + x for x in walk[2]]
for i in files:
    loc = t.separate_file_from_folder(i)
    if loc.ext.lower() == 'py':
        filecount +=1
        with open(loc.full_path, 'r') as f:
            l = list(f)
            rows += len(l)

print(rows, filecount)

