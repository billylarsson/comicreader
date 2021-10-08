from PIL                     import Image
from PyQt5                   import QtCore, QtWidgets
from PyQt5.Qt                import QObject, QRunnable, QThreadPool
from PyQt5.QtCore            import pyqtSignal, pyqtSlot
from PyQt5.QtGui             import QPixmap
from bscripts.database_stuff import DB, sqlite
from functools               import partial
from urllib.request          import Request, urlopen
import hashlib
import os
import pathlib
import pickle
import platform
import random
import shutil
import sys
import tempfile
import time
import traceback
import uuid

default_dict = dict(
    settings=dict(
        batch_size=dict(active=True, value=10),
        cover_height=dict(active=True, value=360),

        sort_by_file_added=dict(active=True, value=None),
        reverse_sort=dict(active=True, value=None),

        fill_row=dict(active=True, value=None),
        show_untagged_flag=dict(active=True, value=None),
        pre_squeeze=dict(active=True, value=None),
        cover_blob=dict(active=True, value=None),
        squeeze_mode=dict(active=True, value=None),

        show_NSFW=dict(active=True, value=None),
        show_comics=dict(active=True, value=None),
        show_magazines=dict(active=True, value=None),

        reading_mode_one=dict(active=True, value=None),

        webp_4kdownsize=dict(active=False, value=None),
        webp_md5file=dict(active=False, value=None),
        webp_quality=dict(active=True, value=80),
        webp_method=dict(active=True, value=6),

        comictagger_file=dict(active=True, value=None),
        autoupdate_library=dict(active=True, value=None),

        show_reading_progress=dict(active=True, value=None),
        show_page_and_size=dict(active=True, value=None),
        show_ratings=dict(active=True, value=None),

        shade_surroundings=dict(active=True, value=None),


    ),
    stylesheets=dict(
        main=dict(active=True, value='background-color: rgb(15,15,15) ; color: white')
    ),
    images=dict(
        tool_searcher=dict(active=True, value=['./img/search.webp']),
        tool_settings=dict(active=True, value=['./img/config.webp']),
        tool_sorter=dict(active=True, value=['./img/sort.webp']),
        tool_reader=dict(active=True, value=['./img/mode.webp']),
        tool_publisher=dict(active=True, value=['./img/publishers.webp']),
        tool_ranking=dict(active=True, value=['./img/rank.webp']),
        tool_webp=dict(active=True, value=['./img/webp.webp']),
        tool_batch=dict(active=True, value=['./img/batch.webp']),
        windows_error=dict(active=True, value=['./img/windows_error.webp']),
        linux_error=dict(active=True, value=['./img/linux_error.webp']),
        tool_comicvine=dict(active=True, value=['./img/comicvine.webp']),
        download_error=dict(active=True, value=['./img/download_error.webp']),
        quit_button=dict(active=True, value=['./img/quit.webp']),
        minimaxi=dict(active=True, value=['./img/minmax.webp']),
    )
)

if platform.system() == 'Windows':
    for winrar_path in ['C:\\Program Files\\WinRAR', 'C:\\Program Files (x86)\\WinRAR']:
        if os.path.exists(winrar_path):
            default_dict['settings'].update(dict(winrar_support=dict(active=True, value=[winrar_path])))

    for zip7_path in ['C:\\Program Files\\7-Zip', 'C:\\Program Files (x86)\\7-Zip']:
        if os.path.exists(zip7_path):
            default_dict['settings'].update(dict(zip7_support=dict(active=True, value=[zip7_path])))

class DIRECTPOSITION:
    @staticmethod
    def digit(value):
        if type(value) == int or type(value) == float:
            return True

    @staticmethod
    def set_hw(widget, w, h):
        widget.resize(int(w), int(h))

    @staticmethod
    def set_geo(widget, x, y, w, h):
        widget.setGeometry(int(x), int(y), int(w), int(h))

    @staticmethod
    def extra(**kwargs):
        """
        ie: extra(dict(y_margin=kwgs))
        returns y_margin if such key are present
        :param kwargs: dictionary[key] = all_kwargs_from_parent
        :return: the value or 0
        """
        if not kwargs:
            return 0

        for master_key, slave_list in kwargs.items():

            for orders in slave_list:

                for k,v in orders.items():

                    if k == master_key:
                        return v

        return 0

    @staticmethod
    def width(widget, args, kwgs):

        if POS.digit(args):
            w = args
            h = widget.height()
        else:
            w = args.width()
            h = widget.height()

        POS.set_hw(widget, w + POS.extra(add=kwgs), h)

    @staticmethod
    def height(widget, args, kwgs):

        if POS.digit(args):
            w = widget.width()
            h = args
        else:
            w = widget.width()
            h = args.height()

        POS.set_hw(widget, w, h + POS.extra(add=kwgs))

    @staticmethod
    def size(widget, args, kwgs):
        """
        :param args: list/tuple with len(2) or widget
        """
        if type(args) == list or type(args) == tuple:
            w = args[0]
            h = args[1]

        else:
            w = args.width()
            h = args.height()

        POS.set_hw(widget, w + POS.extra(add=kwgs), h + POS.extra(add=kwgs))

    @staticmethod
    def inside(working_widget, parent, kwgs):
        """
        you can "coat" a widget that resides within its parent and
        using margins while doing so, but you cannot "coat" parent
        :param parent: must be a widget
        """
        margin = POS.extra(margin=kwgs)
        x, y = 0 + margin, 0 + margin
        w = parent.width() - margin * 2
        h = parent.height() - margin * 2
        POS.set_geo(working_widget, x,y,w,h)

    @staticmethod
    def coat(working_widget, sister_widget, kwgs):
        """
        for two widgets that share the same parent you can coat one ontop
        the other to get their exact cordinates, this is very suitable.
        """
        margin = POS.extra(margin=kwgs)
        x = sister_widget.geometry().left() + margin
        y = sister_widget.geometry().top() + margin
        w = sister_widget.width() - margin * 2
        h = sister_widget.height() - margin * 2
        POS.set_geo(working_widget, x, y, w, h)

    @staticmethod
    def top(widget, args, kwgs):
        """
        read fn:left for same logic, basically if bottom is represented in kwgs its performed
        here as well meaning widget at will can stretch or shrink to reach bottom-destination
        """
        if not POS.digit(args):
            if type(args) == dict:
                if next(iter(args)) == 'top':
                    args = args['top'].geometry().top()
                else:
                    args = args['bottom'].geometry().bottom() + 1
            else:
                args = args.geometry().top()

        y_margin = POS.extra(y_margin=kwgs)

        x = widget.geometry().left()
        y = args + y_margin
        w = widget.width()
        h = widget.height()

        POS.set_geo(widget, x, y ,w, h)

        bottom = POS.extra(bottom=kwgs)

        if bottom:

            if not POS.digit(bottom):

                if type(bottom) == dict:
                    if next(iter(bottom)) == 'bottom':
                        bottom = bottom['bottom'].geometry().bottom()
                    else:
                        bottom = bottom['top'].geometry().top() - 1
                else:
                    bottom = bottom.geometry().bottom()

            fill = bottom - widget.geometry().bottom() - y_margin
            POS.set_hw(widget, widget.width(), widget.height() + fill)

    @staticmethod
    def bottom(widget, args, kwgs):
        """ read fn:top """

        top = POS.extra(top=kwgs)

        if top: # rights task performed in fn:left
            return

        if not POS.digit(args):
            if type(args) == dict:
                if next(iter(args)) == 'bottom':
                    args = args['bottom'].geometry().bottom() + 1
                else:
                    args = args['top'].geometry().top()
            else:
                args = args.geometry().bottom() + 1

        y_margin = POS.extra(y_margin=kwgs)

        x = widget.geometry().left()
        y = args - widget.height() - y_margin
        w = widget.width()
        h = widget.height()

        POS.set_geo(widget, x, y ,w, h)

    @staticmethod
    def left(widget, args, kwgs):
        """
        if argument is int moves widget to start from the argument pixel, if its an object
        then using that objects leftest pixel. if arguemnt is a dictionary(left=sister_widget)
        her's leftest pixel is used, however if dictionary(right=sister_widget) then it will
        be that rightest pixel plus one, assuming we want to start NEXT TO sisters widget.

        if right is somewhere within kwgs, right is dealt with within
        here and no changes will occur when it actually reaches fn:right

        x_margin simply moves the widget forward for that amount of pixels
        but if both left and right changes occurs simultaniously here, x_margin
        will actually shrink the finished position to honor both side margin-symetry

        :param args: int, dictionary or widget
        """
        if not POS.digit(args):

            if type(args) == dict:
                if next(iter(args)) == 'left':
                    args = args['left'].geometry().left() # assume left to left means sharing same pixel
                else:
                    args = args['right'].geometry().right() + 1 # assume left want to position NEXT to right position
            else:
                args = args.geometry().left()

        x_margin = POS.extra(x_margin=kwgs)

        x = args + x_margin
        y = widget.geometry().top()
        w = widget.width()
        h = widget.height()

        POS.set_geo(widget, x, y, w, h)

        right = POS.extra(right=kwgs)

        if right:

            if not POS.digit(right):

                if type(right) == dict:
                    if next(iter(right)) == 'left':
                        right = right['left'].geometry().left() - 1 # assume right want to position BEFORE left position
                    else:
                        right = right['right'].geometry().right() # assume right to right means sharing same pixel
                else:
                    right = right.geometry().right()

            fill = right - widget.geometry().right() - x_margin
            POS.set_hw(widget, widget.width() + fill, widget.height())

    @staticmethod
    def right(widget, args, kwgs):
        """ read fn:left """
        left = POS.extra(left=kwgs)

        if left: # rights task performed in fn:left
            return

        if not POS.digit(args):

            if type(args) == dict:
                if next(iter(args)) == 'left':
                    args = args['left'].geometry().left() - 1  # assume right want to position BEFORE left position
                else:
                    args = args['right'].geometry().right()  # assume right to right means sharing same pixel
            else:
                args = args.geometry().right()

        x_margin = POS.extra(x_margin=kwgs)

        x = args - widget.width() + 1 - x_margin # because we count start (zero) as first pixel
        y = widget.geometry().top()
        w = widget.width()
        h = widget.height()

        POS.set_geo(widget, x, y, w, h)

    @staticmethod
    def after(working_widget, preceeding_widget, kwgs):
        """
        position widget after preceeding_widget,
        y cordinates will be honored
        :param preceeding_widget: must be a widget
        """
        x_margin = POS.extra(x_margin=kwgs)
        x = preceeding_widget.geometry().right() + 1 + x_margin # because we count start (zero) as first pixel
        y = preceeding_widget.geometry().top()
        w = working_widget.width()
        h = working_widget.height()
        POS.set_geo(working_widget, x,y,w,h)

    @staticmethod
    def before(working_widget, following_widget, kwgs):
        """
        position widget before following_widget,
        y cordinates will be honored
        :param preceeding_widget: must be a widget
        """
        x_margin = POS.extra(x_margin=kwgs)
        x = following_widget.geometry().left() - working_widget.width() - 1 - x_margin  # subtracting first pixel
        y = following_widget.geometry().top()
        w = working_widget.width()
        h = working_widget.height()
        POS.set_geo(working_widget, x,y,w,h)

    @staticmethod
    def above(working_widget, widget_under, kwgs):
        """
        position widget above the widget under it, honoring x cordinates
        :param widget_above: must be a widget
        """
        y_margin = POS.extra(y_margin=kwgs)
        x = widget_under.geometry().left()
        y = widget_under.geometry().top() - working_widget.height() - y_margin
        w = working_widget.width()
        h = working_widget.height()
        POS.set_geo(working_widget, x,y,w,h)

    @staticmethod
    def below(working_widget, widget_above, kwgs):
        """
        position widget below the widget above it, honoring x cordinates
        :param widget_above: must be a widget
        """
        y_margin = POS.extra(y_margin=kwgs)
        x = widget_above.geometry().left()
        y = widget_above.geometry().bottom() + 1 + y_margin # not sharing same pixel
        w = working_widget.width()
        h = working_widget.height()
        POS.set_geo(working_widget, x,y,w,h)

    @staticmethod
    def under(*args):
        POS.below(*args)

    @staticmethod
    def center(widget, args, kwgs):
        pointa = args[0]
        pointb = args[1]

        if not POS.digit(pointa):
            if type(pointa) == dict:
                if next(iter(pointa)) == 'left':
                    pointa = pointa['left'].geometry().left()
                else:
                    pointa = pointa['right'].geometry().right()
            else:
                pointa = pointa.geometry().right()

        if not POS.digit(pointb):
            if type(pointb) == dict:
                if next(iter(pointb)) == 'left':
                    pointb = pointb['left'].geometry().left()
                else:
                    pointb = pointb['right'].geometry().right()
            else:
                pointb = pointb.geometry().left()

        rest = pointb - pointa - widget.width()
        rest = rest * 0.5

        x = pointa + rest
        y = widget.geometry().top()
        w = widget.width()
        h = widget.height()

        POS.set_geo(widget, x,y,w,h)

    @staticmethod
    def between(widget, list_with_two_widgets, kwgs):
        """
        if third index == True or 'x' widget is inserted between 0 and 1 in the row
        if third index == False or 'y' widget is put between 0 and 1 stacked on top of each others
        :param list_with_two_widgets: object, object, string/bool (defaults to True, honoring x)
        """
        if list_with_two_widgets[-1] in {False, 'y'}:
            pointa = list_with_two_widgets[0].geometry().bottom() + 1 # else same pixel
            pointb = list_with_two_widgets[1].geometry().top()

            rest = (pointb - pointa) - widget.height()

            if rest > 1:
                x = widget.geometry().left()
                y = pointa + (rest * 0.5)
                POS.set_geo(widget, x, y, widget.width(), widget.height())

        else:
            pointa = list_with_two_widgets[0].geometry().right()
            pointb = list_with_two_widgets[1].geometry().left() + 1 # else same pixel

            rest = (pointb - pointa) - widget.width()

            if rest > 1:
                x = pointa + (rest * 0.5)
                y = widget.geometry().top()
                POS.set_geo(widget, x, y, widget.width(), widget.height())

    @staticmethod
    def move(widget, args, kwgs):
        """
        moving cordinates will be calculated from current position
        :param args: list or tuple
        """
        x = widget.geometry().left() + args[0]
        y = widget.geometry().top() + args[1]
        w = widget.width()
        h = widget.height()
        POS.set_geo(widget, x,y,w,h)

    @staticmethod
    def background(widget, args, kwgs):
        tech.style(widget, background=args)

    @staticmethod
    def color(widget, args, kwgs):
        tech.style(widget, color=args)

    @staticmethod
    def font(widget, args, kwgs):
        if POS.digit(args):
            args = str(args) + 'pt'
        tech.style(widget, font=args)

POS = DIRECTPOSITION()

class ViktorinoxTechClass:
    def __init__(self):
        self.techdict = {}

    @staticmethod
    def pos(widget=None, kwgs=None, new=False, **kwargs):
        def subraction_to_addition():
            """
            if 'sub' in kwargs it will make sub into add and makes sure the value
            is negative due human logic, yeah this can become buggy later on
            """
            if 'sub' in kwargs:
                if kwargs['sub'] > 0:
                    kwargs['add'] = -kwargs['sub']
                else:
                    kwargs['add'] = kwargs['sub']

        subraction_to_addition()

        if not kwgs:
            kwgs = [kwargs]

        if new:
            widget = QtWidgets.QLabel(new, lineWidth=0, midLineWidth=0)
            widget.show()

        for args in kwgs:
            for k, v in args.items():
                fn = getattr(POS, k, False)

                if not fn:
                    continue

                fn(widget, v, kwgs)

        return widget


    @staticmethod
    def separate_file_from_folder(local_path):
        """
        local_path can already be THIS object
        :param local_path must be full path including filename
        :return: object.string: full_path, db_folder, filename, naked_filename, sep (separator)
        """
        if type(local_path) != str:
            return local_path

        local_path = os.path.abspath(os.path.expanduser(local_path))

        class LOCATIONS:
            full_path = local_path
            subfolder = None
            parent = None

            if platform.system() != "Windows":
                sep = '/'
            else:
                sep = '\\'

            _tmp = local_path.split(sep)

            if os.path.isfile(full_path) or not os.path.exists(full_path):
                filename = _tmp[-1]
                _tmp.pop(-1)
                if _tmp:
                    subfolder = _tmp[-1]

                folder = sep.join(_tmp)

                _tmp = filename.split('.')

                if len(_tmp) > 1:
                    ext = _tmp[-1]
                    naked_filename = filename[0:-len(ext)-1]
                else:
                    ext = ""
                    naked_filename = filename

            else:
                folder = full_path
                subfolder = _tmp[-1]
                if len(_tmp) > 1:
                    parent = sep.join(_tmp[0:-1])


        return LOCATIONS

    @staticmethod
    def header(browser='firefox', operatingsystem='linux', architecture='x86_64', randominize=False):
        user_agets = dict(
            firefox=dict(
                windows=dict(
                    x86=['Mozilla/5.0 (Windows NT 6.1; rv:10.0) Gecko/20100101 Firefox/10.0'],
                    x64=['Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:10.0) Gecko/20100101 Firefox/10.0']),
                mac=dict(
                    x86_x64=['Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:10.0) Gecko/20100101 Firefox/10.0'],
                    powerPC=['Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:10.0) Gecko/20100101 Firefox/10.0']),
                linux=dict(
                    i686=['Mozilla/5.0 (X11; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0'],
                    x86_64=['Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0'],
                    mobile=['Mozilla/5.0 (Maemo; Linux armv7l; rv:10.0) Gecko/20100101 Firefox/10.0 Fennec/10.0']),
                android=dict(
                    phone=['Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0'],
                    tablet=['Mozilla/5.0 (Android 4.4; Tablet; rv:41.0) Gecko/41.0 Firefox/41.0']),
                ios=dict(
                    iphone=['Mozilla/5.0 (iPhone; CPU iPhone OS 8_3 like Mac OS X) AppleWebKit/600.1.4 \
                    (KHTML, like Gecko) FxiOS/1.0 Mobile/12F69 Safari/600.1.4'],
                    ipad=['Mozilla/5.0 (iPad; CPU iPhone OS 8_3 like Mac OS X) AppleWebKit/600.1.4 \
                    (KHTML, like Gecko) FxiOS/1.0 Mobile/12F69 Safari/600.1.4']),
            ))

        agentstrings = []

        if randominize:
            for browsers in user_agets:
                for operatingsystems in user_agets[browsers]:
                    for architectures in user_agets[browsers][operatingsystems]:
                        agentstrings += user_agets[browsers][operatingsystems][architectures]
            random.shuffle(agentstrings)

        else:
            if architecture not in user_agets[browser][operatingsystem]:
                for key in user_agets[browser][operatingsystem].keys():
                    agentstrings = user_agets[browser][operatingsystem][key]
                    break
            else:
                agentstrings = user_agets[browser][operatingsystem][architecture]

        header = {'User-Agent' : agentstrings[0]}
        return header

    @staticmethod
    def download_file(url, file=None, reuse=True, header=None):
        """
        downloads a file, if file already exists, its is NOT redownloaded
        if the downloaded file is 0 bytes, its removed, returning False
        :param url: string
        :param file: string, None (autogenerate tmpfile)
        :param header: will use default header if not specified
        :return: bool
        """

        if not file:
            if reuse:
                file = tech.tmp_file(file_of_interest=url, reuse=True, hash=True)
            else:
                file = tech.tmp_file(new=True)

        loc = tech.separate_file_from_folder(file)

        if os.path.exists(loc.full_path):
            return loc.full_path

        elif not os.path.exists(loc.folder):
            pathlib.Path(loc.folder).mkdir(parents=True)

        if header:
            headers = tech.header(**header)
        else:
            headers = tech.header()

        spamfriendly = 5
        while not os.path.exists(loc.full_path) and spamfriendly:
            spamfriendly -= 1

            url = Request(url, headers=headers)

            try: webpage = urlopen(url).read()
            except: return False

            with open(loc.full_path, 'wb') as new_file:
                new_file.write(webpage)

            if os.path.exists(loc.full_path):
                if os.path.getsize(loc.full_path) > 0:
                    return loc.full_path
                else:
                    os.remove(loc.full_path)

        print("ERROR Could not download:", url)
        return False

    @staticmethod
    def save_image_as_blob(image_path, md5, width=None, height=None, quality=70, method=1):
        image = Image.open(image_path)

        if width:
            height = round(image.size[1] * (width / image.size[0]))
        elif height:
            width = round(image.size[0] * (height / image.size[1]))
        else:
            width = image.size[0]
            height = image.size[1]

        image_size = width, height
        image.thumbnail(image_size, Image.ANTIALIAS)

        tmp_file = tech.tmp_file(part1='webpcover_', part2='.webp', new=True)
        image.save(tmp_file, 'webp', method=method, quality=quality)

        with open(tmp_file, 'rb') as file:
            blob = file.read()
            query = 'update files set cover = (?) where md5 = (?)'
            sqlite.w(query, values=md5, blob=blob)

        os.remove(tmp_file)

    @staticmethod
    def md5_hash_string(string=None, random=False, upper=False):
        if random or not string and not random:
            salt = 'how_much_is_the_fi2H'
            string = str(uuid.uuid4()) + str(time.time()) + salt + (string or "")

        hash_object = hashlib.md5(string.encode())
        rv = hash_object.hexdigest()

        if upper:
            rv = rv.upper()

        return rv

    @staticmethod
    def md5_hash_file(local_path, partial_file=False):
        hash_md5 = hashlib.md5()
        with open(local_path, "rb") as f:
            for count, chunk in enumerate(iter(lambda: f.read(4096), b"")):
                hash_md5.update(chunk)
                if partial_file and count > partial_file:
                    break

        return hash_md5.hexdigest()

    @staticmethod
    def zero_prefiller(value, lenght=5):
        string = str(value)
        string = ('0' * (lenght - len(string))) + string
        return string

    def threadpool(self, threads=1, name='threadpool', timeout=30000):
        if 'threadpools' not in self.techdict:
            self.techdict['threadpools'] = {}

        if name not in self.techdict['threadpools']:
            threadpool = QThreadPool(maxThreadCount=threads, expiryTimeout=timeout)
            self.techdict['threadpools'][name] = threadpool

        return self.techdict['threadpools'][name]

    def start_thread(self,
                     worker_function,
                     worker_arguments=None,
                     finished_function=None,
                     finished_arguments=None,
                     threads=1,
                     name='threadpool'
                     ):

        if worker_arguments:
            # makes sure the arguents are put into a tuple
            if type(worker_arguments) != tuple:
                worker_arguments = (worker_arguments,)
            thread = Worker(partial(worker_function, *worker_arguments))

        else:
            thread = Worker(partial(worker_function))

        if finished_function:

            if type(finished_function) != list:
                # makes finished function(s) into a list in case multiple launches are requested
                finished_function = [finished_function]

            for launcher in finished_function:

                if finished_arguments != None:
                    # makes sure the arguents are put into a tuple
                    if type(finished_arguments) != tuple:
                        finished_arguments = (finished_arguments,)
                    thread.signals.finished.connect(partial(launcher, *finished_arguments))

                else:
                    thread.signals.finished.connect(partial(launcher))

        threadpool = tech.threadpool(name=name, threads=threads)
        threadpool.start(thread)

    @staticmethod
    def retrieve_setting(index):
        """
        :param index: integer
        :return: column
        """
        data = sqlite.execute('select * from settings where id is 1', one=True)
        if data:
            return data[index]

    @staticmethod
    def tmp_file(
            file_of_interest=None,
            hash=False,
            reuse=False,
            days=False,
            delete=False,
            new=False,
            extension=None,
            part1=None, part2=None
        ):
        """
        :param file_of_interest: string can be anything fuck_a_duck.txt
        :param reuse, doesnt delete file if its present, uses cache
        :param days int, file is no more than x days to reuse
        :param part1, part2 becomes part1_0004_part2.webp with new=True
        :param new, keeps old files and puts a counter on/in new filename
        :param if extension, its added AFTER hashing
        :return: full path (string)
        """
        tmp_folder = tech.tmp_folder(folder_of_interest='tmp_files', reuse=True)

        if part1 and part2:
            if file_of_interest:
                file_of_interest += part1 + part2
            else:
                file_of_interest = part1 + part2

        if not file_of_interest:
            md5 = tech.md5_hash_string(str(time.time()) + os.environ['PROGRAM_NAME'] + 'tmp_file')
            file_of_interest = md5.upper()

        if hash:
            file_of_interest = tech.md5_hash_string(file_of_interest)

        if extension and extension[0] != '.':
            extension = '.' + extension

        if extension:
            file_of_interest += extension

        complete_path = tmp_folder + '/' + file_of_interest
        complete_path = os.path.abspath(os.path.expanduser(complete_path))

        def delete_file_checker(complete_path):
            if os.path.exists(complete_path):
                if days:
                    if os.path.getmtime(complete_path) < time.time() - (days * 86400):
                        os.remove(complete_path)
                        return

                if delete:
                    os.remove(complete_path)
                    return

        delete_file_checker(complete_path) # deletes first

        if reuse:
            return complete_path

        if os.path.exists(complete_path):
            if os.path.isfile(complete_path):
                try:
                    if not new:
                        os.remove(complete_path)
                except PermissionError:
                    pass
                except IsADirectoryError:
                    pass
                finally:

                    def zero_prefiller(value, lenght=4):
                        string = str(value)
                        string = ('0' * (lenght - len(string))) + string
                        return string

                    counter = 0
                    while os.path.exists(complete_path):
                        counter += 1
                        if part1 and part2:
                            _tmp_path = tmp_folder + '/' + part1 + zero_prefiller(counter) + part2
                            _tmp_path = os.path.abspath(os.path.expanduser(_tmp_path))
                        else:
                            _tmp_path = complete_path + '_' + zero_prefiller(counter)

                        if extension:
                            _tmp_path += extension

                        if not os.path.exists(_tmp_path):
                            complete_path = _tmp_path

        return complete_path

    @staticmethod
    def tmp_folder(
            folder_of_interest=None,
            reuse=False,
            delete=False,
            hash=False,
            create_dir=True,
            return_base=False,
        ):
        """
        generates a temporary folder for user
        i prefer to keep my trash inside /mnt/ramdisk
        if conflict, 0,1,2,3 + _ can be added to the END of the file
        :param folder_of_interest: string or none
        :param reuse: bool -> doesnt delete folder if its present, uses cache
        :param delete: bool -> will rmtree the folder before treating
        :param hash: bool -> md5 hashing folder_or_interest for clean dirs
        :return: full path (string)
        """
        if not folder_of_interest:
            md5 = tech.md5_hash_string(str(time.time()) + os.environ['PROGRAM_NAME'] + 'tmp_folder')
            folder_of_interest = md5.upper()

        elif folder_of_interest and hash:
            md5 = tech.md5_hash_string(folder_of_interest)
            folder_of_interest = md5.upper()

        user_basedir = tech.config('cache_folder') # overrides os.environ['TMP_DIR']
        if user_basedir and os.path.exists(user_basedir[0]):
            base_dir = user_basedir[0]

        elif os.path.exists(os.environ['TMP_DIR']):
            base_dir = os.environ['TMP_DIR']

        else:
            base_dir = tempfile.gettempdir()

        complete_dir = base_dir + '/' + os.environ['PROGRAM_NAME'] + '/' + folder_of_interest
        complete_dir = os.path.abspath(os.path.expanduser(complete_dir))

        if os.path.exists(complete_dir) and not reuse:
            try:
                if delete:
                    shutil.rmtree(complete_dir)
            except PermissionError:
                pass
            except NotADirectoryError:
                pass
            finally:
                counter = 0
                while os.path.exists(complete_dir):
                    counter += 1
                    tmp = complete_dir + '_' + str(counter)
                    if not os.path.exists(tmp):
                        complete_dir = tmp

        if not os.path.exists(complete_dir) and create_dir:
            pathlib.Path(complete_dir).mkdir(parents=True)

        if return_base:
            return base_dir
        else:
            return complete_dir

    @staticmethod
    def correct_broken_font_size(object, presize=True, maxsize=14, minsize=5, x_margin=10, y_margin=0, shorten=False):
        if presize:
            tech.style(object, font=str(maxsize) + 'pt')

        if shorten:
            for count in range(100):
                object.show()
                if object.fontMetrics().boundingRect(object.text()).width() + x_margin > object.width():
                    text = object.text()
                    object.setText(text[0:-3] + '..')
                else:
                    return

        for count in range(maxsize,minsize,-1):
            object.show()
            if object.fontMetrics().boundingRect(object.text()).width() + x_margin > object.width():
                tech.style(object, font=str(count) + 'pt')
            elif object.fontMetrics().boundingRect(object.text()).height() + y_margin > object.height():
                tech.style(object, font=str(count) + 'pt')
            else:
                return count + 1

    @staticmethod
    def NSFW_magz_comics_includer(fromlist):
        NSFW = tech.config('show_NSFW')
        magazines = tech.config('show_magazines')
        comic = tech.config('show_comics')

        for count in range(len(fromlist) - 1, -1, -1):
            if fromlist[count][DB.comics.type] == DB.comics.NSFW and not NSFW:
                fromlist.pop(count)
            elif fromlist[count][DB.comics.type] == DB.comics.magazine  and not magazines:
                fromlist.pop(count)
            elif fromlist[count][DB.comics.type] == DB.comics.comic and not comic:
                fromlist.pop(count)

    @staticmethod
    def uni_search(fromlist, userinput, key):
        """
        makes list of userinput and searches
        each key for each part of the userinput
        :param fromlist:
        :param userinput:
        :param key:
        :return: drawlist
        """
        searchlist = userinput.strip().lower().split()
        drawlist = []
        tech.NSFW_magz_comics_includer(fromlist)

        if searchlist:
            for datacount, eachsource in enumerate(fromlist):
                source = str(eachsource[key])
                for usercount, eachinput in enumerate(searchlist):

                    if source == None or eachinput == None:
                        continue

                    search_value = source.lower().find(eachinput)

                    if search_value != -1:
                        source = source[0:search_value] + source[search_value+len(eachinput):]
                        if usercount == len(searchlist) -1:
                            drawlist.append(fromlist[datacount])
                    else:
                        break
        else:
            return fromlist

        return drawlist

    @staticmethod
    def sort_by_number(fromlist, key, reverse=False):
        rvdict = {}
        for i in fromlist:

            if i[key] == '½':
                rvdict[i] = 0.5

            elif i[key] != None:
                try:
                    rvdict[i] = float(i[key])
                except TypeError:
                    rvdict[i] = 0
                except ValueError:
                    rvdict[i] = 0
            else:
                rvdict[i] = 999999999

        rv = []
        for db,_ in {k: v for k, v in sorted(rvdict.items(), key=lambda item: item[1], reverse=reverse)}.items():
            rv.append(db)

        return rv

    @staticmethod
    def uni_sort(fromlist):
        if not fromlist:
            return fromlist

        rest = None
        reverse = tech.config('reverse_sort') or False

        if tech.config('sort_by_size'):
            rest = [x for x in fromlist if not x[DB.comics.file_size]]
            fromlist = [x for x in fromlist if x[DB.comics.file_size]]
            fromlist.sort(key=lambda x: x[DB.comics.file_size], reverse=reverse)

        elif tech.config('sort_by_file_added'):
            rest = [x for x in fromlist if not x[DB.comics.file_date]]
            fromlist = [x for x in fromlist if x[DB.comics.file_date]]
            fromlist.sort(key=lambda x: x[DB.comics.file_date], reverse=reverse)

        elif tech.config('sort_by_rating'):
            rest = [x for x in fromlist if not x[DB.comics.rating]]
            fromlist = [x for x in fromlist if x[DB.comics.rating]]
            fromlist.sort(key=lambda x: x[DB.comics.rating], reverse=reverse)

        elif tech.config('sort_by_date_added'):
            fromlist.sort(key=lambda x: x[0], reverse=reverse)

        else:
            sorted_list = []
            tmp = {}

            for i in fromlist:
                highest = i[DB.comics.local_path].rfind('/')
                if i[DB.comics.local_path].find('\\') > highest:
                    highest = i[DB.comics.local_path].find('\\')

                filename = i[DB.comics.local_path][highest + 1:]
                tmp.update({filename: i})

            if tmp:
                sorted_tmp = {k: v for k, v in sorted(tmp.items(), key=lambda item: item[0], reverse=reverse)}
                sorted_list = [v for k, v in sorted_tmp.items()]

            return sorted_list

        if rest and reverse:
            fromlist += rest
        elif rest:
            fromlist = rest + fromlist

        return  fromlist

    def keep_track(self,
                   name='default',
                   starting_lives=5,
                   margin=0.2,
                   restart=False,
                   count=False,
                   report=False,
                   start=False, stop=False, halt=False,
                   ):

        if 'keep_track' not in self.techdict:
            self.techdict['keep_track'] = {}

        if name not in self.techdict['keep_track'] or restart:

            class TRACKER:
                def __init__(self, starting_lives, margin):
                    self.lives_left = starting_lives
                    self.counter = 0
                    self.margin = margin
                def count(self, report=False):
                    self.counter += 1
                    if tech.config('dev_mode'):
                        if self.counter >= self.lives_left:
                            print(f'The {self.lives_left} limit reached, current count: {self.counter}')
                        elif report:
                            print(f'Current count {self.counter} (limit: {self.lives_left})')
                def start(self):
                    self.start_time = time.time()
                def stop(self):
                    self.time_taken = self.start_time - time.time()
                    if self.time_taken > self.margin:
                        self.lives_left -= 1
                        if tech.config('dev_mode'):
                            print("Lives left:", self.lives_left)
                def runtime(self):
                    active = time.time() - self.start_time
                    if active < 0 or active > 36000:
                        return 0.01
                    return active
                def halt(self):
                    if self.lives_left < 0:
                        return True

            self.techdict['keep_track'][name] = TRACKER(starting_lives=starting_lives, margin=margin)

        tracker = self.techdict['keep_track'][name]

        if start:
            tracker.start()
        elif count:
            tracker.count(report=report)
        elif stop:
            tracker.stop()
        elif halt:
            return tracker.halt()

        return tracker

    def config(self, setting, theme=None, stylesheet=False, image=False, curious=False):
        """
        if theme=None the logic is to ask dictionary['default_theme'] for theme
        if not found it falls back to 'default' theme. settings are stored in
        dictionary['theme']['settings'] for pure settings and stylesheets inside
        dictionary['theme']['stylesheets']
        :param setting: string
        :param theme: string or anything that can be a dict.key()
        :param curious: if True, will return value even if active == False
        :return: value or False (instead of None)
        """
        def default_values(setting, stylesheet=False, image=False):
            """
            default values are given here
            :param setting: string
            :return: value or False
            """
            if stylesheet:
                if setting in default_dict['stylesheets']:
                    return default_dict['stylesheets'][setting]
            elif image:
                if setting in default_dict['images']:
                    return default_dict['images'][setting]
            else:
                if setting in default_dict['settings']:
                    return default_dict['settings'][setting]
            return False

        if 'config' in self.techdict:
            data = self.techdict['config']
        else:
            config = tech.retrieve_setting(DB.settings.config)
            if not config:
                data = {}
            elif config:
                data = pickle.loads(config)
                if type(data) != dict:
                    data = {}

                self.techdict.update(dict(config=data))

        c = dict(current_theme='default', default=default_dict)
        for key,val in c.items():
            if key not in data:
                data.update({key:val})

        if not theme:
            theme = data['current_theme']

        c = dict(
            settings=default_dict['settings'],
            stylesheets=default_dict['stylesheets'],
            images=default_dict['images'],
        )
        for key,val in c.items():
            if key not in data[theme]:
                data[theme].update({key:val})

        self.techdict['config'] = data

        if stylesheet:
            if setting in data[theme]['stylesheets']:
                rv = data[theme]['stylesheets'][setting]
            else:
                rv = default_values(setting, stylesheet=True)

        elif image:
            if setting in data[theme]['images']:
                rv = data[theme]['images'][setting]
            else:
                rv = default_values(setting, image=True)

        else:
            if setting in data[theme]['settings']:
                rv = data[theme]['settings'][setting]
            else:
                rv = default_values(setting)

        if rv:
            if rv['active']:
                if rv['value']:
                    return rv['value']
                else:
                    return rv['active']
            elif curious:
                return rv['value']
            else:
                return rv['active']


    def save_config(self, setting, value, delete=False, stylesheet=False, image=False, total_reset=False):
        """
        :param delete: pops the key before storing
        :param setting: string
        :param stylesheet: bool, if True point to dict['stylesheets'] else dict['settings']
        :param value: string, int, whatever fits a dictionary
        :return: value or False (instead of None)
        """
        tech.config('dummy') # activates self.techdict['config']
        theme = self.techdict['config']['current_theme']

        if setting[0] == '_': # we dont save under/dunder types
            return False
        elif stylesheet:
            subkey = 'stylesheets'
        elif image:
            subkey = 'images'
        else:
            subkey = 'settings'

        if setting in self.techdict['config'][theme][subkey]:
            savedict = self.techdict['config'][theme][subkey][setting]
        else:
            savedict = dict(active=True, value=None)

        if type(value) == bool:
            savedict['active'] = value
        else:
            savedict['value'] = value

        self.techdict['config'][theme][subkey][setting] = savedict

        if delete:
            self.techdict['config'][theme][subkey].pop(setting)

        data = pickle.dumps(self.techdict['config'])

        if total_reset:
            sqlite.execute('update settings set config = null where id is 1')
        else:
            sqlite.execute('update settings set config = (?) where id is 1', values=data)

    @staticmethod
    def close_and_pop(thislist):
        for count in range(len(thislist) - 1, -1, -1):
            thislist[count].close()
            thislist.pop(count)

    @staticmethod
    def set_my_pixmap(widget, name=None, path=None):
        def set_this(path):
            pixmap = QPixmap(path).scaled(
                widget.width(), widget.height(), transformMode=QtCore.Qt.SmoothTransformation)

            widget.clear()
            widget.setPixmap(pixmap)

        if path and os.path.exists(path):
            set_this(path)
            return True

        elif not name and 'type' in dir(widget):
            name = widget.type

        if not name:
            return False

        path_blob_or_list = tech.config(name, image=True)
        if not path_blob_or_list:
            return False

        if type(path_blob_or_list) == str and os.path.exists(path_blob_or_list):
            set_this(path_blob_or_list)
            return True

        elif type(path_blob_or_list) == list:
            random.shuffle(path_blob_or_list)
            for count in range(len(path_blob_or_list)-1,-1,-1):
                if type(path_blob_or_list[count]) == str and not os.path.exists(path_blob_or_list[count]):
                    path_blob_or_list.pop(count)

            for i in path_blob_or_list:
                if type(i) == str:
                    set_this(i)
                    return True

                else:
                    tmp_file = tech.tmp_file('pixmap_' + name, hash=True, extension='webp', reuse=True)
                    if os.path.exists(tmp_file):
                        set_this(tmp_file)
                        return True

                    with open(tmp_file, 'wb') as f:
                        f.write(path_blob_or_list[0])

                    set_this(tmp_file)
                    return True

    @staticmethod
    def style(widget, set=True, save=False, name=None, background=None, color=None, font=None, delete=False, border=None, tooltip=False):
        """
        if save is True, the set part wont happen
        if name is given, will request, save or set 'stylesheet_name'
        if name isnt given looks into widget.type and requests 'stylesheet_type'
        if any background,color,font thoes are set but not saved: background='green' font='8pt'
        :param widget: object
        :param set: bool
        :param save: bool
        :param name: string
        :return: bool or string.styleSheet()
        """

        def make_stylesheet(widget):

            if widget.styleSheet() and widget.styleSheet().find('{') > -1: # meaning we've processed this before
                dictstyle = make_dictstylesheet(widget.styleSheet())
                return dictstyle

            elif widget.styleSheet(): # meaning it should only be one stylesheet
                if tooltip:
                    stylesheet = make_string_stylesheet([])
                    stylesheet = 'QToolTip{' + stylesheet + '}'
                    stylesheet += widget.metaObject().className() + '{' + widget.styleSheet() + '}'
                else:
                    stylelist = widget.styleSheet().split(';')
                    stylesheet = make_string_stylesheet(stylelist)
                    stylesheet = widget.metaObject().className() + '{' + stylesheet + '}'
            else:
                stylesheet = make_string_stylesheet([])
                if tooltip:
                    stylesheet = 'QToolTip{' + stylesheet + '}'
                else:
                    stylesheet = widget.metaObject().className() + '{' + stylesheet + '}'

            return stylesheet

        def make_dictstylesheet(old_stylesheet):
            stylesdict = {}
            parts = old_stylesheet.split('}')
            for part in parts:
                head_tail = part.split('{')

                head_tail = [x for x in head_tail if len(x) > 0]
                if not head_tail:
                    continue

                head = head_tail[0]
                head.strip()
                tail = head_tail[1]
                tail.strip()

                if tooltip and head != 'QToolTip': # no change to 'base' stylesheet
                    stylesdict[head] = '{' + tail + '}'

                elif not tooltip: # makes new as if nothing happened
                    stylelist = tail.split(';')
                    newtail = make_string_stylesheet(stylelist)
                    stylesdict[head] = '{' + newtail + '}'

            if tooltip and 'QToolTip' not in stylesdict:
                stylesdict['QToolTip'] = '{' + make_string_stylesheet([]) + '}'

            stylesheet = ""
            for k,v in stylesdict.items():
                stylesheet += k + v

            return stylesheet

        def make_string_stylesheet(stylelist):
            final = {
                'background-color:': background,
                'color:': color,
                'font:': font,
                'border:': border,
            }

            for i in stylelist:
                parts = i.split(':')
                parts = [x for x in parts if len(x) > 0]

                key = parts[0] + ':'.strip()
                value = parts[1].strip()

                if key in final and not final[key]:
                    final[key] = value

            rv = ""
            for k,v in final.items():
                if not v:
                    continue
                else:
                    rv += k + v + ';'

            return rv.rstrip(';')

        # <<======ABOVE:ME=======<{ [                TOP              ] ==============================<<
        # >>======================= [               FLOOR             ] }>============BELOW:ME========>>

        if not name:
            if 'type' in dir(widget) and type(widget.type) == str:
                name = widget.type

        if delete and name:
            tech.save_config(name, None, delete, stylesheet=True)

        elif save:
            stylesheet = widget.styleSheet()
            if not stylesheet:
                stylesheet = make_stylesheet(widget)

            if name and stylesheet:
                tech.save_config(name, stylesheet, stylesheet=True)
                return True
            else:
                return False
        elif set:
            if background or color or font:
                new = make_stylesheet(widget)
                widget.setStyleSheet(new)
                return new

            if name:
                stylesheet = tech.config(name, stylesheet=True)
                if stylesheet:
                    widget.setStyleSheet(stylesheet)
                    return stylesheet
                else:
                    return False

    def signals(self, name=None, reset=False, delete_afterwards=False, delete=False):
        if 'signals' not in self.techdict:
            self.techdict.update(dict(signals={ }))

        if name == None:
            name = 0
            while name in self.techdict['signals']:
                name += 1

        if name not in self.techdict['signals'] and not delete:
            self.techdict['signals'][name] = WorkerSignals()
            self.techdict['signals'][name].name = name

        elif name in self.techdict['signals'] and delete:
            self.techdict['signals'].pop(name)
            return

        elif name in self.techdict['signals'] and reset:
            self.techdict['signals'][name] = WorkerSignals()
            self.techdict['signals'][name].name = name

        if delete_afterwards:
            rv = self.techdict['signals'][name]
            self.techdict['signals'].pop(name)
            return rv

        return self.techdict['signals'][name]

tech = ViktorinoxTechClass()

class WorkerSignals(QObject):
    finished = pyqtSignal()
    quit = pyqtSignal()
    error = pyqtSignal(dict)
    result = pyqtSignal(object)
    progress = pyqtSignal(dict)
    checkgroup_master = pyqtSignal(str)
    deactivate = pyqtSignal(str)
    activate = pyqtSignal(str)
    stop = pyqtSignal(dict)
    file_delivery = pyqtSignal(str)
    activated = pyqtSignal(bool)
    neighbour = pyqtSignal(dict)
    pagenumbers = pyqtSignal(tuple)
    startjob = pyqtSignal(dict)
    volumelabel = pyqtSignal(dict)
    buildrelative = pyqtSignal(dict)
    pickrelatives = pyqtSignal(list)
    drawpublisher = pyqtSignal(int)
    drawvolume = pyqtSignal(dict)
    sort_publishers_by_name = pyqtSignal()
    sort_publishers_by_amount = pyqtSignal()
    sort_publishers_by_rating = pyqtSignal()
    sort_volumes_by_name = pyqtSignal()
    sort_volumes_by_amount = pyqtSignal()
    sort_volumes_by_rating = pyqtSignal()
    drawfolder = pyqtSignal(dict)
    drawfile = pyqtSignal(dict)

class Worker(QRunnable):
    def __init__(self, function):
        super(Worker, self).__init__()
        self.fn = function
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn()
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
