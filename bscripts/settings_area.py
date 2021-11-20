from PyQt5                        import QtGui
from bscripts.database_stuff      import sqlite
from bscripts.file_handling       import hash_all_unhashed_comics
from bscripts.file_handling       import scan_for_new_comics
from bscripts.tricks              import tech as t
from script_pack.settings_widgets import CheckBoxSignalGroup
from script_pack.settings_widgets import CheckableAndGlobalHighlight
from script_pack.settings_widgets import ExecutableLookCheckable
from script_pack.settings_widgets import FolderSettingsAndGLobalHighlight
from script_pack.settings_widgets import GLOBALDeactivate, POPUPTool
from script_pack.settings_widgets import UniversalSettingsArea

TEXTSIZE = 14

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
        class FillRowSqueeze(CheckBoxSignalGroup, CheckableAndGlobalHighlight):
            def special(self):
                if self.type == 'squeeze_mode':
                    return False

                if not t.config('squeeze_mode') and self.activated:
                    t.style(self.button, background='orange')
                    return True

            def checkgroup_signal(self, signal):
                if self.type == 'fill_row' and signal == 'squeeze_mode':
                    self.activation_toggle(force=self.activated, save=False)

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    self.activation_toggle()
                    self.signalgroup.checkgroup_master.emit(self.type)

        class PATHExtenders(FolderSettingsAndGLobalHighlight):
            def special(self):
                if self.activated:
                    rv = t.config(self.type, curious=True)

                    if rv and type(rv) == list:
                        t.style(self.button, background='green')
                    else:
                        t.style(self.button, background='orange')
                else:
                    t.style(self.button, background='gray')
                return True

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    self.activation_toggle()

        dict_with_checkables = [
            dict(
                text="SHOW COMICS", textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='else excluding files marked as Comics',
                kwargs = dict(type='show_comics'),
            ),
            dict(
                text='SHOW MAGAZINES', maxsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='else excluding files marked as Magazines',
                kwargs = dict(type='show_magazines'),

            ),
            dict(
                text='SHOW NSFW', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='else excluding files marked as porn',
                kwargs = dict(type='show_NSFW')
            ),
            dict(
                text='SQUEEZE MODE', textsize=TEXTSIZE,
                widget=FillRowSqueeze, post_init=True,
                tooltip='contract/expand covers until they claim all space in full rows (looks good, but only tries to honor aspekt ratio)',
                kwargs = dict(signalgroup='squeeze_fill_group', type='squeeze_mode'),
            ),
            dict(
                text='FILLING ROW', textsize=TEXTSIZE,
                widget=FillRowSqueeze, post_init=True,
                tooltip='exceeding limit until row is full, requires Squeeze Mode (looks better)',
                kwargs = dict(signalgroup='squeeze_fill_group', type='fill_row'),
            ),
            dict(
                text='COVER BLOB', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='stores thumbnails into database (100x faster loading speed next time you browse the same item at the cost of increasing local databse by ~25kb per item (depending on thumbnail size))',
                kwargs = dict(type='cover_blob'),
            ),
            dict(
                text='COVERS PRE-DRAW', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
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
                widget=FolderSettingsAndGLobalHighlight,
                kwargs = dict(type='comic_folder')),
            dict(
                text='MAGAZINES', textsize=TEXTSIZE,
                widget=FolderSettingsAndGLobalHighlight,
                tooltip='regular magazines folder ...',
                kwargs = dict(type='magazine_folder')),
            dict(
                text='NSFW FOLDER', textsize=TEXTSIZE,
                tooltip='found a mouse ...',
                widget=FolderSettingsAndGLobalHighlight,
                kwargs=dict(type='NSFW_folder')),
            dict(
                text='CACHE FOLDER', textsize=TEXTSIZE,
                widget=FolderSettingsAndGLobalHighlight,
                tooltip='must exist! (else fallback to systems-tmp)',
                kwargs = dict(type='cache_folder', multiple_folders=False)),
        ]

        dict_with_cover_details = [
            dict(
                text='RATING', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                kwargs = dict(type='show_ratings')),
            dict(
                text='READING PROGRESS', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip="shows a progress bar from left to right according to the current highest pagenumber you've opened",
                kwargs = dict(type='show_reading_progress')),
            dict(
                text='PAGES AND SIZE', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                kwargs = dict(type='show_page_and_size')),
            dict(
                text='UNTAGGED FLAG', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='if we cannot find a comicvine id with this file, a small square is positioned in the upper right corner indicating that',
                kwargs = dict(type='show_untagged_flag')
            )
        ]

        full_shade = [
            dict(
                text='SHADE SURROUNDINGS', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='when you study or read an issue, all surroudings are darkley shaded, looks good.',
                kwargs = dict(type='shade_surroundings')),
        ]
        class DEVMODE(CheckableAndGlobalHighlight):

            def special(self):
                if self.activated:
                    t.style(self.button, background='pink')
                    t.style(self.textlabel, color='pink')
                else:
                    t.style(self.button, background='gray')
                    t.style(self.textlabel, color='gray')

                return True

            def default_event_colors(self):
                self.directives['activation'] = [
                    dict(object=self.textlabel, color='lightBlue'),
                    dict(object=self.button, background='lightBlue', color='pink'),
                ]

                self.directives['deactivation'] = [
                    dict(object=self.textlabel, color='gray'),
                    dict(object=self.button, background='gray', color='gray'),
                ]

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.activation_toggle()
                sqlite.dev_mode = self.activated

        dev_mode = [
            dict(
                text='DEVELOPER FEATURES', textsize=TEXTSIZE,
                shrink_to_text=True,
                widget=DEVMODE, post_init=True,
                tooltip='source code explains (experience can be buggy, keep this of for improved stability)',
                kwargs = dict(type='dev_mode')),
        ]

        dict_with_pdf_things = [
            dict(
                text = 'PDF SUPPORT', textsize=TEXTSIZE, widget=PATHExtenders,
                tooltip = "this may not be a plesent experience since it depends on poppler path. if your'e on windows, i'd say you doomed if you dont know what you're doing and i suggest you leave this in the red",
                kwargs = dict(type='pdf_support', multiple_folders=False)),
        ]

        dict_with_unpackers = [
            dict(
                text = 'WinRAR', textsize=TEXTSIZE, widget=PATHExtenders,
                tooltip = "if you're on windows and want CBR file support you need to either have WinRAR.exe in you systems path or provide it here",
                kwargs = dict(type='winrar_support', multiple_folders=False)),
            dict(
                text='7-Zip', textsize=TEXTSIZE, widget=PATHExtenders,
                tooltip="alternative to WinRAR",
                kwargs=dict(type='zip7_support', multiple_folders=False)),
        ]

        dict_with_autoupdate = [
            dict(
                text = 'LIBRARY AUTOUPDATE', textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip = "autoupdates on start and when you close settings panel",
                kwargs = dict(type='autoupdate_library')),
        ]

        dict_update_hash = [
            dict(
                text='SCAN FOR NEW FILES', textsize=TEXTSIZE-2, button_width_factor=2.2,
                button_color='darkCyan', text_color='gray', post_init=True,
                widget=self.UpdateLibrary, button_text='',
                tooltip='updates library in the background',
                kwargs = dict(type='_update_library')),
        ]

        dict_parse_for_cvid = [
            dict(
                text='PARSE UNPARSED FILES', textsize=TEXTSIZE-2, button_width_factor=2.2,
                button_color='darkCyan', text_color='gray', post_init=True,
                widget=self.HashUnHashed, button_text='',
                tooltip='iters all unitered comics for comicvine id (comictagger), we do this once per file as long as MD5 is checked (thats how we track such event for now, if MD5 is not checked all files will be processed next time again, and again, and again...)',
                kwargs = dict(type='_parse_unparsed')),
        ]

        dict_md5_comic = [
            dict(
                text='HASH MD5 FROM NEW FILES', textsize=TEXTSIZE-2,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='first time an item is to be shown to user an MD5 checksum is initiated and stored into database, this is conveniet when keeping track of multiple files and sharing ratings with friends',
                kwargs = dict(type='md5_files')),

            dict(
                text='SEARCH ZIP FOR CVID', textsize=TEXTSIZE-2,
                widget=CheckableAndGlobalHighlight, post_init=True,
                tooltip='searches the file contents for comicvine id (comictagger)',
                kwargs = dict(type='comictagger_file'))
        ]

        self.main.settings = UniversalSettingsArea(self.main, type='settings', activation_toggle=self.activation_toggle)

        blackgray1 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_checkables, canvaswidth=250)
        blackgray2 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_cover_details, canvaswidth=250)
        blackgray3 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_paths)
        blackgray4 = self.main.settings.make_this_into_LCDrow(headersdictionary=dict_with_lcdrow, canvaswidth=250)
        blackgray5 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_pdf_things)
        blackgray5_1 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_unpackers)
        blackgray6 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_update_hash, canvaswidth=300)
        blackgray7 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_md5_comic)
        blackgray8 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_autoupdate)
        blackgray9 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=full_shade)
        blackgray10 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dev_mode)
        blackgray11 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_parse_for_cvid, canvaswidth=300)

        header = self.main.settings.make_header(title='SETTINGS')

        t.pos(blackgray2, below=blackgray1, y_margin=10)
        t.pos(blackgray6, after=blackgray1, x_margin=10)
        t.pos(blackgray3, below=blackgray6, left=blackgray6, y_margin=10)
        t.pos(blackgray4, below=blackgray2, y_margin=10)
        t.pos(blackgray5, left=blackgray3, below=blackgray3, y_margin=10)
        t.pos(blackgray5_1, left=blackgray3, below=blackgray5, y_margin=10)
        t.pos(blackgray8, left=blackgray5, below=blackgray5_1, y_margin=10)
        t.pos(blackgray7, below=blackgray8, y_margin=10, left=blackgray8)
        t.pos(blackgray9, below=blackgray4, y_margin=10)
        t.pos(blackgray10, below=blackgray9, y_margin=10)
        t.pos(blackgray11, after=blackgray6, x_margin=10)

        t.pos(header, right=blackgray3, bottom=blackgray6)

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