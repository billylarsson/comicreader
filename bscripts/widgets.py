from PyQt5                        import QtCore, QtGui, QtWidgets
from script_pack.settings_widgets import CheckableLCD, CheckableWithSignal, CheckBoxSignalGroup,CheckableWidget,HighlightRadioBoxGroup
from script_pack.settings_widgets import ExecutableLookCheckable, GOD
from script_pack.settings_widgets import UniversalSettingsArea
from bscripts.file_handling        import generate_cover_from_image_file
from bscripts.file_handling        import hash_all_unhashed_comics
from bscripts.file_handling        import scan_for_new_comics
from bscripts.tricks               import tech as t
from PyQt5.QtCore   import QPoint, Qt
import os, sys
from script_pack.settings_widgets import GLOBALDeactivate

TEXTSIZE = 14

class POPUPTool(GLOBALDeactivate):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place=place, *args, **kwargs)

        self.directives['activation'] = [
            dict(object=self, background='white', color='white'),
        ]

        self.directives['deactivation'] = [
            dict(object=self, background='gray', color='white'),
        ]

        self.activation_toggle(force=False, save=False)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls() and len(ev.mimeData().urls()) == 1:
            file = ev.mimeData().urls()[0]
            file = file.path()
            if os.path.isfile(file):
                splitter = file.split('.')
                if splitter[-1].lower() in {'webp', 'jpg', 'jpeg', 'png', 'gif'}:
                    ev.accept()
        return


    def dropEvent(self, ev):
        if ev.mimeData().hasUrls() and ev.mimeData().urls()[0].isLocalFile():
            if len(ev.mimeData().urls()) == 1:
                ev.accept()

                files = []

                for i in ev.mimeData().urls():
                    t.tmp_file('pixmap_' + self.type, hash=True, extension='webp', delete=True)
                    t.tmp_file(i.path(),              hash=True, extension='webp', delete=True)

                    tmp_nail = generate_cover_from_image_file(
                        i.path(), store=False, height=self.height(), width=self.width())

                    files.append(tmp_nail)

                for c in range(len(files)-1,-1,-1):
                    with open(files[c], 'rb') as f:
                        files[c] = f.read()

                if files:
                    t.save_config(self.type, files, image=True)
                    t.set_my_pixmap(self)

class TOOLSearch(POPUPTool):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        self.activation_toggle(force=True, save=False)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.activation_toggle(save=False)
            self.show_searchwidget()

        if ev.button() == 2:
            self.main.search_comics()

    def show_searchwidget(self):
        """
        this creates the searchbar and puts it into focus
        this searchbar is always reused instead of recreating
        """
        def search_widget_settings(self):
            """
            sets strong, restores previous search and connects returnPressed shortcut
            """
            self.main.le_primary_search.type = 'le_primary_search'
            t.style(self.main.le_primary_search)
            self.main.le_primary_search.setFocusPolicy(QtCore.Qt.StrongFocus)
            self.main.le_primary_search.setFocus()
            self.main.le_primary_search.returnPressed.connect(self.main.search_comics)

            rv = t.config('last_query')
            if rv:
                if type(rv) == str:
                    self.main.le_primary_search.setText(rv)
                else:
                    self.main.le_primary_search.setText("")

        if self.activated:
            if 'le_primary_search' in dir(self.main):
                self.main.le_primary_search.show()
                self.main.le_primary_search.raise_()
                self.main.le_primary_search.setFocus()
                return

            self.main.le_primary_search = QtWidgets.QLineEdit(self.main)
            search_widget_settings(self)
            self.main.le_primary_search.show()
            t.pos(self.main.le_primary_search, coat=self, width=300, rightof=self, x_margin=1)
        else:
            self.main.le_primary_search.hide()

class TOOLSettings(POPUPTool):
    def trigger_settingswidget(self):
        if self.activated:
            self.create_reusable_settingswidget()
            self.main.settings.move(100, 100)

        elif 'settings' in dir(self.main):
            self.main.settings.close()
            del self.main.settings


    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)
        self.trigger_settingswidget()

    def create_reusable_settingswidget(self):
        """
        creates a large settingsarea and then makes three smaller
        settingsboxes inside that area and places them around for
        more indepth about the how-to see UniversalSettingsArea
        """
        class FillRow(CheckBoxSignalGroup):
            def special(self):
                if not t.config('squeeze_mode') and self.activated:
                    t.style(self.button, background='orange')
                    return True

            def checkgroup_signal(self, signal):
                if signal == 'squeeze_mode':
                    self.activation_toggle(force=self.activated)

        dict_with_checkables = [
            dict(
                text="SHOW COMICS", textsize=TEXTSIZE,
                tooltip='else excluding files marked as Comics',
                kwargs = dict(type='show_comics'),
            ),
            dict(
                text='SHOW MAGAZINES', textsize=TEXTSIZE,
                tooltip='else excluding files marked as Magazines',
                kwargs = dict(type='show_magazines'),

            ),
            dict(
                text='SHOW NSFW', textsize=TEXTSIZE,
                tooltip='else excluding files marked as porn',
                kwargs = dict(type='show_NSFW')
            ),
            dict(
                text='SQUEEZE MODE', textsize=TEXTSIZE,
                widget=CheckableWithSignal,
                tooltip='contract/expand covers until they claim all space in full rows (looks good, but only tries to honor aspekt ratio)',
                kwargs = dict(signalgroup='squeeze_fill_group', type='squeeze_mode'),
            ),
            dict(
                text='FILLING ROW', textsize=TEXTSIZE,
                widget=FillRow, tooltip='exceeding limit until row is full, requires Squeeze Mode (looks better)',
                kwargs = dict(signalgroup='squeeze_fill_group', type='fill_row'),
            ),
            dict(
                text='COVER BLOB', textsize=TEXTSIZE,
                tooltip='stores thumbnails into database (100x faster loading speed next time you browse the same item at the cost of increasing local databse by ~25kb per item (depending on thumbnail size))',
                kwargs = dict(type='cover_blob'),
            ),
            dict(
                text='COVERS PRE-DRAW', textsize=TEXTSIZE,
                tooltip='show covers when prepositioning covers (takes a millisecond per item on a good computer)',
                kwargs = dict(type='pre_squeeze')
            ),
            ]

        dict_with_lcdrow = [
            dict(
                text='COVER HEIGHT', textsize=TEXTSIZE,
                kwargs = dict(type='cover_height')),
            dict(
                text='BATCH SIZE', textsize=TEXTSIZE,
                kwargs = dict(type='batch_size')),
        ]

        dict_with_paths = [
            dict(
                text='COMICS FOLDER', textsize=TEXTSIZE,
                tooltip='CBZ files',
                kwargs = dict(type='comic_folder')),
            dict(
                text='NSFW FOLDER', textsize=TEXTSIZE,
                tooltip='found a mouse ...',
                kwargs = dict(type='NSFW_folder')),
            dict(
                text='MAGAZINES', textsize=TEXTSIZE,
                tooltip='regular magazines folder ...',
                kwargs = dict(type='magazine_folder')),
            dict(
                text='CACHE FOLDER', textsize=TEXTSIZE,
                tooltip='must exist! (else fallback to systems-tmp)',
                kwargs = dict(type='cache_folder')),
        ]

        dict_with_cover_details = [
            dict(
                text='RATING', textsize=TEXTSIZE,
                kwargs = dict(type='show_ratings')),
            dict(
                text='READING PROGRESS', textsize=TEXTSIZE,
                tooltip="shows a progress bar from left to right according to the current highest pagenumber you've opened",
                kwargs = dict(type='show_reading_progress')),
            dict(
                text='PAGES AND SIZE', textsize=TEXTSIZE,
                kwargs = dict(type='show_page_and_size')),
            dict(
                text='UNTAGGED FLAG', textsize=TEXTSIZE,
                tooltip='if we cannot find a comicvine id with this file, a small square is positioned in the upper right corner indicating that',
                kwargs = dict(type='show_untagged_flag')
            )
        ]

        dict_with_pdf_things = [
            dict(
                text = 'PDF SUPPORT', textsize=TEXTSIZE,
                tooltip = "this may not be a plesent experience since it depends on poppler path. if your'e on windows, i'd say you doomed if you dont know what you're doing and i suggest you leave this in the red",
                kwargs = dict(type='pdf_support')),
        ]

        dict_with_autoupdate = [
            dict(
                text = 'LIBRARY AUTOUPDATE', textsize=TEXTSIZE,
                tooltip = "autoupdates on start and when you close settings panel",
                kwargs = dict(type='autoupdate_library')),
        ]

        dict_update_hash = [
            dict(
                text='SCAN FOR NEW FILES NOW', textsize=TEXTSIZE, button_width_factor=3,
                button_color='darkCyan', text_color='gray', post_init=True,
                widget=self.UpdateLibrary, button_text='',
                tooltip='updates library in the background',
                kwargs = dict(type='_update_library')),
        ]

        dict_md5_comic = [
            dict(
                text='HASH MD5 FROM NEW FILES', textsize=TEXTSIZE,
                tooltip='first time an item is to be shown to user an MD5 checksum is initiated and stored into database, this is conveniet when keeping track of multiple files and sharing ratings with friends',
                kwargs = dict(type='md5_files')),

            dict(
                text='EXTRACT COMIC ID FROM ZIP', textsize=TEXTSIZE,
                tooltip='searches the file contents for comicvine id (comictagger)',
                kwargs = dict(type='comictagger_file'))
        ]

        self.main.settings = UniversalSettingsArea(self.main, type='settings', activation_toggle=self.activation_toggle)

        blackgray1 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_checkables)
        blackgray2 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_cover_details)
        blackgray3 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_paths)
        blackgray4 = self.main.settings.make_this_into_LCDrow(headersdictionary=dict_with_lcdrow)
        blackgray5 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_pdf_things)
        blackgray6 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_update_hash, canvaswidth=350)
        blackgray7 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_md5_comic)
        blackgray8 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_autoupdate)


        header = self.main.settings.make_header(title='SETTINGS')

        t.pos(blackgray2, below=blackgray1, y_margin=10)
        t.pos(blackgray6, rightof=blackgray1, x_margin=10)
        t.pos(blackgray3, below=blackgray6, left=blackgray6, y_margin=10)
        t.pos(blackgray4, below=blackgray2, y_margin=10)
        t.pos(blackgray5, left=blackgray3, below=blackgray3, y_margin=10)
        t.pos(blackgray8, left=blackgray5, below=blackgray5, y_margin=10)
        t.pos(blackgray7, below=blackgray8, y_margin=10, left=blackgray8)

        t.pos(header, right=blackgray3, above=blackgray6.geometry().bottom())

        self.main.settings.expand_me(self.main.settings.blackgrays)

        signal = t.signals(self.type, reset=True)
        signal.activated.connect(self.before_close_event)

    def before_close_event(self):
        if not self.activated and t.config('autoupdate_library'):
            t.start_thread(scan_for_new_comics, name='update_library', threads=1)

    class UpdateLibrary(GLOBALDeactivate, ExecutableLookCheckable):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.activation_toggle(force=False)

        def post_init(self):
            self.button.setMouseTracking(True)
            self.textlabel.setMouseTracking(True)

            self.directives['activation'] = [
                dict(object=self.textlabel, color='white'),
                dict(object=self.button, background='cyan', color='cyan'),
            ]

            self.directives['deactivation'] = [
                dict(object=self.textlabel, color='gray'),
                dict(object=self.button, background='darkCyan', color='darkCyan'),
            ]

        def special(self):
            return True

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self.running_job: # jobs running
                return

            self.slaves_can_alter = False
            self.running_job = True
            self.start_job(signalgroup='updating_library_job')
            t.start_thread(scan_for_new_comics,
                           finished_function=self.jobs_done, name='update_library', threads=1, worker_arguments=False)

    class HashUnHashed(GLOBALDeactivate, ExecutableLookCheckable):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.activation_toggle(force=False)

        def post_init(self):
            self.button.setMouseTracking(True)
            self.textlabel.setMouseTracking(True)

            self.directives['activation'] = [
                dict(object=self.textlabel, color='white'),
                dict(object=self.button, background='cyan', color='cyan'),
            ]

            self.directives['deactivation'] = [
                dict(object=self.textlabel, color='gray'),
                dict(object=self.button, background='darkCyan', color='darkCyan'),
            ]

        def special(self):
            return True

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if self.running_job: # jobs running
                return

            self.running_job = True
            self.start_job(signalgroup='hash_unhashed_job')
            t.start_thread(
                hash_all_unhashed_comics,
                finished_function=self.jobs_done,
                name='long_time', threads=1
            )

class TOOLBatch(POPUPTool):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        self.main.batcher = self

    def check_if_database_is_within_range(self, count):
        """
        :param count: int count from current comic asking for approval
        :return: bool True for approval
        """
        if not self.activated: # window itself
            return True

        if not self.batch.activated: # button
            return True

        if count >= self.batch.get_current_value(): # LCD function
            return True
        else:
            return False

    def stop_drawing(self, reset=False):
        """
        each time we come in here batchcount is subtracted by one
        and once it goes below 0 it resets it self and returnes
        True for stop drawing!
        :param reset: if True batchsize is set back to default
        :return: bool False == continue to draw
        """
        if reset or 'batchtracker' not in dir(self):
            self.batchtracker = t.config('batch_size')
            if reset:
                return

        self.batchtracker += -1

        if self.batchtracker >= 0:
            return False
        else:
            self.batchtracker = t.config('batch_size')
            return True

    def get_highest_drawed_index(self):
        """
        :return: int highest drawn index
        """
        highest = 0
        for i in self.main.draw_list_comics:
            if i['used'] and i['count'] > highest:
                highest = i['count']

        return highest + 1  # humans dont know we start at zero

    def set_current_position(self):
        """
        sets the HIGHEST drawn index
        """
        if not self.activated:
            return

        high = self.get_highest_drawed_index()
        self.batch.max_value = len(self.main.draw_list_comics)
        self.batch.set_new_value(direct_value=high) # LCD function

    def show_start_from_gui(self):
        """
        creates a gui that shows you current HIGHEST index you've drawn,
        you can change this index and next time you draw it will start from
        that index. once you close this window the feature will be deactivated
        """
        if not self.activated:
            return False

        if not self.main.draw_list_comics:
            self.activation_toggle(force=False, save=False)
            return False

        if not 'batch' in dir(self): # return LCD's can be found in the labels key()
            d = [
                dict(
                    text='START FROM',
                    widget=CheckableLCD,
                    kwargs=dict(type='_start_from')
                )
            ]

            class U(UniversalSettingsArea):

                def mouseMoveEvent(self, event):
                    if event.button() == 2 or 'old_position' not in dir(self):
                        return

                    delta = QPoint(event.globalPos() - self.old_position)
                    self.move(self.x() + delta.x(), self.y() + delta.y())
                    self.old_position = event.globalPos()

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    self.old_position = ev.globalPos()
                    if ev.button() == 2:
                        self.activation_toggle(force=False, save=False)
                        self.hide()

            self.batch_settings = U(self.main, activation_toggle=self.activation_toggle)
            header = self.batch_settings.make_header(title='BATCH OPERATOR', width=160)
            set1 = self.batch_settings.make_this_into_checkable_button_with_LCDrow(d, canvaswidth=250)
            t.pos(set1, below=header, y_margin=3)
            t.pos(self.batch_settings, left=self, below=self, y_margin=6)
            self.batch_settings.expand_me([x for x in self.batch_settings.blackgrays])

            batchlabel = d[0]['label']
            self.batch = batchlabel

            self.set_current_position()
            self.batch.activation_toggle(force=True, save=False)
            self.batch_settings.activation_toggle(force=True, save=False)

        elif 'batch_settings' in dir(self):
            self.batch_settings.activation_toggle(force=True, save=False)
            self.batch_settings.show()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        """
        activates and shows batch gui, when you click it second time it will close again
        """
        self.activation_toggle(save=False)

        if ev.button() == 1:
            if self.activated:
                self.show_start_from_gui()
            elif 'batch_settings' in dir(self):
                self.batch_settings.hide()

        elif ev.button() == 2:
            print("YES")



class TOOLSort(POPUPTool):


    def show_sorting_tools(self):


        d1 = [
            dict(
                text='SORT FILE NAME', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                kwargs = dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_name')
            ),
            dict(
                text='SORT FILE SIZE', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                kwargs = dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_size')
            ),
            dict(
                text='SORT DATE ADDED', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                tooltip="Sorts by the time file was added to database, experience can be crazy...!",
                kwargs = dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_date_added')
            ),
            dict(
                text='SORT FILE DATE', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                tooltip="Sorts by the time file was last configured on your drive WHILE adding it to the database, even crazier experience...!",
                kwargs=dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_file_added')
            ),
            dict(
                text='SORT BY RATING', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                tooltip='Excludes comics WITHOUT rating\n"Kommer kränka någon!"',
                kwargs=dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_rating',)
            ),
        ]

        d2 =[
            dict(
                text='REVERSE ORDER', textsize=TEXTSIZE,
                kwargs=dict(type='reverse_sort')
            ),
        ]

        self.blackgray = UniversalSettingsArea(self.main, activation_toggle=self.activation_toggle)
        bg1 = self.blackgray.make_this_into_checkable_buttons(d1)
        bg2 = self.blackgray.make_this_into_checkable_buttons(d2)

        header = self.blackgray.make_header(title='SORTING ORDER', width=140)
        t.pos(bg1, below=header, y_margin=3)
        t.pos(header, right=bg1)

        t.pos(bg2, below=bg1, y_margin=10)
        self.blackgray.expand_me(self.blackgray.blackgrays)
        t.pos(self.blackgray, below=self, left=self, y_margin=10)

        widgets = [x['label'] for x in d1]
        widgets[0].fall_back_to_default(list_with_widgets=widgets, fallback_type='sort_by_name')


    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.show_sorting_tools()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray


class TOOLRank(POPUPTool):
    class BUTTON(GLOBALDeactivate, ExecutableLookCheckable):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.activation_toggle(force=False)

        def post_init(self):
            self.button.setMouseTracking(True)
            self.textlabel.setMouseTracking(True)

            self.directives['activation'] = [
                dict(object=self.textlabel, color='white'),
                dict(object=self.button, background='cyan', color='cyan'),
            ]

            self.directives['deactivation'] = [
                dict(object=self.textlabel, color='gray'),
                dict(object=self.button, background='darkCyan', color='darkCyan'),
            ]

        def special(self):
            return True

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            if ev.button() == 1:
                self.button_clicked()
            elif ev.button() == 2:
                self.killswitch()

    class ShowAllRated(BUTTON):
        def button_clicked(self):
            t.save_config('all_volumes_with_rated_issue', True)
            t.save_config('only_volumes_with_unread_issue', False)
            self.main.show_rated_volumes()

    class ShowAllRatedUnread(BUTTON):
        def button_clicked(self):
            t.save_config('all_volumes_with_rated_issue', False)
            t.save_config('only_volumes_with_unread_issue', True)
            self.main.show_rated_volumes()

    def show_volumebuttons(self):
        d =[
            dict(
                text='SHOW EARLIEST ISSUE OF HIGHEST RATED VOLUMES', textsize=TEXTSIZE,
                widget=self.ShowAllRated, button_width_factor=2.5, post_init=True,
                text_color='gray', button_color='darkCyan',
                kwargs=dict(type='all_volumes_with_rated_issue', extravar=dict(
                    killswitch=self.killswitch
                ))
            ),
            dict(
                text='SHOW ONLY THOSE WITH AT LEAST ONE UNREAD ISSUE', textsize=TEXTSIZE,
                widget=self.ShowAllRatedUnread, button_width_factor=2.5, post_init=True,
                text_color='gray', button_color='darkCyan',
                kwargs=dict(type='only_volumes_with_unread_issue', extravar=dict(
                    killswitch=self.killswitch
                ))
            ),
        ]

        self.blackgray = UniversalSettingsArea(self.main, type='volumes_shower')
        self.blackgray.make_this_into_checkable_buttons(d, canvaswidth=500)
        self.blackgray.expand_me(self.blackgray.blackgrays)
        t.pos(self.blackgray, below=self, left=self, y_margin=10)

    def killswitch(self):
        self.activation_toggle(save=False)

        if self.activated:
            self.show_volumebuttons()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.killswitch()

        elif ev.button() == 2:
            self.main.show_rated_volumes()

class TOOLMaxiMini(POPUPTool):
    def __init__(self, place, main=None, type=None):
        super().__init__(place, main=main, type=type)
        t.style(self, background='gray', color='black', font='14pt')
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.move(1,1)
        self.set_position()
        self.activation_toggle(save=False)
        self.how_much_is_the_fish()

    def how_much_is_the_fish(self):
        if not self.activated:
            self.main.showMaximized()
            self.setText('LARGE')
        else:
            self.main.showNormal()
            self.setText('SMALL')

    def set_position(self):
        x = self.main.back.geometry().top() - 2
        t.pos(self, size=(120, x,), right=self.main.quitter.geometry().left(), x_margin=2)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle()
        if ev.button() == 1:
            self.how_much_is_the_fish()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        pass

class TOOLQuit(POPUPTool):
    def __init__(self, place, type=None):
        super().__init__(place, type=type)
        t.style(self, background='gray', color='black', font='14pt')
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.setText('QUIT')
        self.move(1,1)
        self.set_position()

    def set_position(self):
        x = self.main.back.geometry().top() - 2
        t.pos(self, size=(120, x,), right=self.main.back)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            sys.exit()
        elif ev.button() == 2:
            if 'fuck_this_duck' in dir(self.main):
                self.main.fuck_this_duck = -1
            else:
                self.main.fuck_this_duck = 1

class TOOLDev(POPUPTool):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        self.activated = False

    def show_dev_tools(self):
        d = [
            dict(
                text='PDF-WEPB READ THREAD',
                tooltip='could be very unsatesfying reading experience',
                kwargs=dict(type='single_pdf2webp')),

        ]
        self.blackgray = UniversalSettingsArea(self.main, activation_toggle=self.activation_toggle)
        self.blackgray.make_this_into_checkable_buttons(d)
        self.blackgray.expand_me(self.blackgray.blackgrays)
        t.pos(self.blackgray, below=self, left=self, y_margin=10)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.show_dev_tools()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray


class TOOLReading(POPUPTool):

    def viewmodes(self):

        d1 = [
            dict(
                text='SINGLE FIT SCREEN', widget=HighlightRadioBoxGroup, textsize=TEXTSIZE, post_init=True,
                tooltip="shows one page scaled for height or width whichever shows takes most screen",
                kwargs=dict(
                    type='reading_mode_one',
                    signalgroup='reading_modes',
                )),
            dict(
                text='SINGLE MAX WIDTH', widget=HighlightRadioBoxGroup, textsize=TEXTSIZE, post_init=True,
                tooltip="shows one page scaled for width and you scroll down while reading",
                kwargs=dict(
                    type='reading_mode_two',
                    signalgroup='reading_modes',
                )),
            dict(
                text='SIDE BY SIDE', widget=HighlightRadioBoxGroup, textsize=TEXTSIZE, post_init=True,
                tooltip="shows up to two pages sewed together scaled for height",
                kwargs=dict(
                    type='reading_mode_three',
                    signalgroup='reading_modes',
                )),
            dict(
                text='SIDE SPACE SIDE', widget=HighlightRadioBoxGroup, textsize=TEXTSIZE, post_init=True,
                tooltip="shows up to two pages with some space in-between",
                kwargs=dict(
                    type='reading_mode_four',
                    signalgroup='reading_modes',
                )),
        ]

        d2 = [
            dict(text='DRAW OUTLINES', textsize=TEXTSIZE,
                 kwargs=dict(type='draw_outlines'),
                 )
        ]

        self.blackgray = UniversalSettingsArea(self.main, activation_toggle=self.activation_toggle)
        header = self.blackgray.make_header(title='VIEWING MODES', width=160)
        set1 = self.blackgray.make_this_into_checkable_buttons(d1)
        set2 = self.blackgray.make_this_into_checkable_buttons(d2)
        t.pos(set1, below=header, y_margin=3)
        t.pos(header, right=set1)
        t.pos(set2, below=set1, y_margin=5)
        self.blackgray.expand_me(self.blackgray.blackgrays)
        t.pos(self.blackgray, below=self, left=self, y_margin=10)

        widgets = [x['label'] for x in d1]
        widgets[0].fall_back_to_default(list_with_widgets=widgets, fallback_type='reading_mode_one')

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.viewmodes()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray

class TOOLWEBP(POPUPTool):
    def show_webp_settings(self):
        d1 = [
            dict(
                text='QUALITY',
                textsize=TEXTSIZE,
                lcds_in_this_row=3,
                max_value=100,
                min_value=10,

                kwargs=dict(
                    type='webp_quality',
                )),
            dict(
                text='MODE',
                textsize=TEXTSIZE,
                lcds_in_this_row=1,
                max_value=6,
                min_value=1,
                kwargs=dict(
                    type='webp_method'
            ))
        ]

        d2 = [
            dict(
                text='4K DOWNSIZE',
                textsize=TEXTSIZE,

                kwargs=dict(
                    type='webp_4kdownsize'
            )),
            dict(
                text='MAKE MD5 FILE',
                tooltip='for PDF to CBZ conversions there wont be any individual file sums because those wont offer any usefull data',
                textsize=TEXTSIZE,

                kwargs=dict(
                    type='webp_md5file'
            )),
            dict(
                text='DELETE SOURCE',
                textsize=TEXTSIZE,
                tooltip='delete source file once convertion is complete',

                kwargs=dict(
                    type='webp_delete_source_file'
            ))
          ]

        self.blackgray = UniversalSettingsArea(self.main, activation_toggle=self.activation_toggle)
        lcd = self.blackgray.make_this_into_LCDrow(d1, canvaswidth=200)
        header = self.blackgray.make_header(title='WEBP GLOBAL SETTINGS', width=lcd.width())
        chk = self.blackgray.make_this_into_checkable_buttons(d2, canvaswidth=250)

        t.pos(lcd, below=header, y_margin=3)
        t.pos(chk, below=lcd, y_margin=5)
        t.pos(lcd, right=chk)
        t.pos(header, right=chk)
        t.pos(self.blackgray, below=self, left=self, y_margin=10)
        self.blackgray.expand_me([x for x in self.blackgray.blackgrays])

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.show_webp_settings()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray