from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint, Qt
from PyQt5.QtGui                  import QColor, QKeySequence, QPen, QPixmap
from PyQt5.QtWidgets              import QShortcut, QSizePolicy
from bscripts.database_stuff      import DB, sqlite
from bscripts.file_handling       import FileArchiveManager
from bscripts.file_handling       import check_for_pdf_assistance
from bscripts.file_handling       import extract_from_zip_or_pdf
from bscripts.file_handling       import get_thumbnail_from_zip_or_database
from bscripts.tricks              import tech as t
from functools                    import partial
from script_pack.preset_colors    import *
from script_pack.settings_widgets import CheckableAndGlobalHighlight
from script_pack.settings_widgets import GLOBALDeactivate, GOD
from script_pack.settings_widgets import HighlightRadioBoxGroup
from script_pack.settings_widgets import UniversalSettingsArea
import math
import os
import pickle
import time

class ReadingMenu(HighlightRadioBoxGroup):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place=place, *args, **kwargs)

    def post_init(self):
        self.button.setMouseTracking(True)
        self.textlabel.setMouseTracking(True)

        self.directives['activation'] = [
            dict(object=self.textlabel, color=TXT_SHINE),
            dict(object=self.button, background=BTN_SHINE),
        ]

        self.directives['deactivation'] = [
            dict(object=self.textlabel, color=TXT_SHADE),
            dict(object=self.button, background=TXT_DARKTRANS),
        ]

        self.signal_global_gui_change(directive='deactivation')

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.button_clicked()
        elif ev.button() == 2:
            self.killsignal.finished.emit()

class ChangePage(ReadingMenu):
    def button_clicked(self):
        """
        beware that this is a hack, change_page goes to
        different parental fn depending on inheritance
        """
        self.change_page()
        self.killsignal.finished.emit()

class LastPage(ReadingMenu):
    def button_clicked(self):
        _, __, total = self.current_and_how_many_pages()
        if total:
            self.show_this_page(index=total - 1, next=True)
        else:
            self.slaves_can_alter = False
            self.textlabel.setText('FILE ERROR')
            t.correct_broken_font_size(self.textlabel)
            t.style(self.textlabel, color='red')
            t.style(self.button, background='orange')
            return

        self.killsignal.finished.emit()

class AutoChangePage(ReadingMenu):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place=place, *args, **kwargs)
        self.sleep_time = 3
        self.activation_toggle(force=True, save=False)
        signal = t.signals('reading')
        signal.finished.connect(self.quit)

    def quit(self):
        self.activation_toggle(force=False, save=False)

    def modify_sleep(self, modify):
        self.sleep_time += modify
        if self.sleep_time < 1:
            self.sleep_time = 1

    def button_clicked(self, virgin=True):
        primary, secondary, total = self.current_and_how_many_pages()
        if not self.activated or not total:
            self.quit()
            return

        if primary+1 == total or secondary+1 == total:
            self.quit()
            return

        if virgin:
            moretime = QShortcut(QKeySequence('ctrl+up'), self.pixmap_object)
            moretime.activated.connect(partial(self.modify_sleep, +1))

            lesstime = QShortcut(QKeySequence('ctrl+down'), self.pixmap_object)
            lesstime.activated.connect(partial(self.modify_sleep, -1))

            esc = QShortcut(QKeySequence('ctrl+q'), self.pixmap_object)
            esc.activated.connect(self.quit)

        self.goto_next_page()
        t.start_thread(
            self.dummy, worker_arguments=self.sleep_time,
            finished_function=self.button_clicked, finished_arguments=False
        )

class BookmarkDeleteSaveButton(CheckableAndGlobalHighlight):

    def default_event_colors(self):
        self.directives['activation'] = [
            dict(object=self.textlabel, background=TXT_DARKTRANS, color='white'),
            dict(object=self.button, background=BTN_SHINE, color=BTN_SHINE),
        ]

        self.directives['deactivation'] = [
            dict(object=self.textlabel, background=TXT_DARKTRANS, color=BTN_SHADE),
            dict(object=self.button, background=TXT_SHADE, color=BTN_SHADE),
        ]

    def unpack_bookmarks(self):
        if self.database[DB.comics.bookmarks]:
            b = pickle.loads(self.database[DB.comics.bookmarks])
        else:
            b = {}
        return b

    def update_bookmark_database(self, dictionary):
        if not dictionary:
            data = None
        else:
            data = pickle.dumps(dictionary)

        query = 'update comics set bookmarks = (?) where id is (?)'
        values = data, self.database[0]
        sqlite.execute(query=query, values=values)
        self.database = sqlite.refresh_db_input('comics', self.database)

    def save_this_bookmark(self):
        def show_bookmark_button(self):
            for i in self.large_page.bookmarks['buttons']:
                if i.bookmark_id == self.bookmark_id:
                    return

            self.large_page.parent.database = sqlite.refresh_db_input('comics', self.database)
            self.large_page.parent.show_bookmarks(only_this_bookmark_id=self.bookmark_id)
            self.parent.raise_()

        def generate_bookmark_id(self, b, page):
            """
            currently using self.type as bookmark_id so this
            function may be overcautious, but if future
            change this may fix an unvanted experience
            :param b: bookmark_dictionary
            :param page: int
            :return: md5 hash (uuid4 + time.time + salt)
            """
            if self.bookmark_id:
                return self.bookmark_id

            bookmark_id = t.md5_hash_string(random=True, upper=True)
            while bookmark_id.upper() in b[page]:
                bookmark_id = t.md5_hash_string(random=True, upper=True)

            return bookmark_id

        def reset_button(self):
            def change_back_to_save():
                self.textlabel.setText('SAVE')
            def dummy():
                time.sleep(2)

            self.textlabel.setText('DONE')
            t.start_thread(dummy, finished_function=change_back_to_save)

        def generate_pickle(text, pctx, pcty, b, bookmark_id):
            c = dict(x=round(pctx, 4), y=round(pcty, 4))

            for k, v in c.items():
                if v > 1:
                    c[k] = 0.9999
                elif v < 0:
                    c[k] = 0.0001

            b[page][bookmark_id] = dict(text=text, x=c['x'], y=c['y'], time=round(time.time()))

        def save_cordinates(self, bookmark_widget):
            if self.parent_button:
                evx = self.parent_button.pos().x()
                evy = self.parent_button.pos().y()
            else:
                evx = bookmark_widget.pos().x()
                evy = bookmark_widget.pos().y()

            return evx, evy

        text = self.textedit.toPlainText().strip()
        self.database = sqlite.refresh_db_input('comics', self.database)  # important

        b = self.unpack_bookmarks()

        total_w = self.pixmap_object.width()
        total_h = self.pixmap_object.height()

        for i in self.large_page.bookmarks['widgets']:

            if i.bookmark_id != self.bookmark_id: # not parent (self is a button only with limited access)
                continue

            evx, evy = save_cordinates(self, i)

            primary, secondary, _ = self.current_and_how_many_pages()

            if secondary:
                page_one_x_ends = total_w * self.pixmap_object.primary[1]
                page_two_x_start = total_w * self.pixmap_object.secondary[0]

                if evx > page_two_x_start:
                    page = secondary
                    pctx = evx - page_two_x_start
                    pctx = pctx / (total_w - page_two_x_start)
                    pcty = evy / total_h
                else:
                    page = primary
                    pctx = evx / page_one_x_ends
                    pcty = evy / total_h

            else:
                page = primary
                pctx = evx / total_w
                pcty = evy / total_h

            if page not in b:
                b[page] = {}

            bookmark_id = generate_bookmark_id(self, b, page)
            generate_pickle(text, pctx, pcty, b, bookmark_id)
            self.update_bookmark_database(dictionary=b)
            show_bookmark_button(self)
            reset_button(self)
            break

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.save_this_bookmark()

class BookmarkDeleteButton(BookmarkDeleteSaveButton):
    def default_event_colors(self):
        self.directives['activation'] = [
            dict(object=self.textlabel, background=TXT_DARKTRANS, color='white'),
            dict(object=self.button, background=BTN_SHINE, color=BTN_SHINE),
        ]

        self.directives['deactivation'] = [
            dict(object=self.textlabel, background=TXT_DARKTRANS, color=BTN_SHADE),
            dict(object=self.button, background=TXT_SHADE, color=BTN_SHADE),
        ]

    def delete_this_bookmark(self):
        self.database = sqlite.refresh_db_input('comics', self.database)
        for i in self.large_page.bookmarks['widgets']:

            if i.bookmark_id != self.bookmark_id: # not parent (self is a button only with limited access)
                continue

            b = self.unpack_bookmarks()
            for page in b:

                if self.bookmark_id in b[page]:

                    b[page].pop(self.bookmark_id)

                    if b[page] == {}: # no bookmarks left, dont save empty page entry
                        b.pop(page)

                    self.update_bookmark_database(dictionary=b)
                    break

            for category in ['buttons', 'widgets']:
                for count, i in enumerate(self.large_page.bookmarks[category]):
                    if self.bookmark_id == i.bookmark_id:
                        self.large_page.bookmarks[category].pop(count)
                        i.close()
            return

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.delete_this_bookmark()

def make_bookmark(large_page, bookmark_id=False, parent_button=None):

    class U(UniversalSettingsArea):
        def pop_self_from_parents_list(self):
            for count, i in enumerate(self.parent.bookmarks['widgets']):
                if i == self:
                    self.parent.bookmarks['widgets'].pop(count)
                    return

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.old_position = ev.globalPos()
            if ev.button() == 2:
                self.pop_self_from_parents_list()
                self.close()

    if not bookmark_id:
        bookmark_id = t.md5_hash_string(random=True, upper=True)

    set = U(large_page, type='_bmk' + bookmark_id)
    set.bookmark_id = bookmark_id
    set.setToolTip('RIGHT CLICK TO CLOSE')

    set.textedit = QtWidgets.QTextEdit(set)

    t.style(set.textedit, background=TXT_DARKTRANS, color=TXT_SHINE)
    set.blackgrays = [set.textedit]
    set.textedit.show()

    d1 = [
        dict(
            text='SAVE',
            widget=BookmarkDeleteSaveButton,
            text_background=TXT_DARKTRANS,
            shrink_to_text=dict(margin=2),
            post_init=True,

            kwargs=dict(
                type='_savbtn' + bookmark_id,
                extravar=dict(
                    database=large_page.parent.database,
                    current_and_how_many_pages=large_page.current_and_how_many_pages,
                    pixmap_object=large_page.parent.pixmap_object,
                    textedit=set.textedit,
                    large_page=large_page,
                    parent_button=parent_button,
                    bookmark_id=bookmark_id,
                    parent=set,
                )
            )
        )
    ]

    d2 = [
        dict(
            text='DELETE',
            widget=BookmarkDeleteButton,
            text_background=TXT_DARKTRANS,
            shrink_to_text=dict(margin=2),
            post_init=True,

            kwargs=dict(
                type='_delbtn' + bookmark_id,
                extravar=dict(
                    database=large_page.parent.database,
                    parent_button=parent_button,
                    large_page=large_page,
                    bookmark_id=bookmark_id,
                    parent=set,
                )
            )
        )
    ]

    header = set.make_header(title='ADD/REMOVE BOOKMARK', width=200, height=20, background=TXT_DARKTRANS)

    bg1 = set.make_this_into_checkable_buttons(d1, canvaswidth=130, toolsheight=20)
    bg2 = set.make_this_into_checkable_buttons(d2, canvaswidth=130, toolsheight=20)

    t.pos(header, move=[30, 0])
    t.pos(bg1, below=header, y_margin=3)
    t.pos(bg2, after=bg1, x_margin=3)
    t.pos(header, left=bg1, right=bg2)
    t.pos(set.textedit, top=dict(bottom=bg1), y_margin=3, width=bg2.geometry().right() + 30, height=300)
    t.correct_broken_font_size(header)
    set.expand_me([x for x in set.blackgrays])

    return set

class NewBookmark(ReadingMenu):
    def button_clicked(self):
        set = make_bookmark(self.parent)
        self.parent.bookmarks['widgets'].append(set)
        t.pos(set, top=self.parent.reading_menu, left=self.parent.reading_menu)
        self.killsignal.finished.emit()


class EachPage(QtWidgets.QLabel):
    def __init__(self, place, parent):
        super().__init__(place)
        self.parent = parent
        self.parent.current_and_how_many_pages = self.current_and_how_many_pages
        self.bookmarks = dict(buttons=[], widgets=[])

    def current_and_how_many_pages(self):
        database = self.parent.database
        if database[DB.comics.file_contents]:
            files = pickle.loads(database[DB.comics.file_contents])
            return self.parent.who_am_primary, self.parent.who_am_secondary, len(files['good_files'])

        else:
            rv = check_for_pdf_assistance(database[DB.comics.local_path], pagecount=True)

            if rv:
                return self.parent.who_am_primary, self.parent.who_am_secondary, rv

        return self.parent.who_am_primary, self.parent.who_am_secondary, False

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.parent.old_position = ev.globalPos()

        if ev.button() == 2:
            if 'reading_menu' in dir(self):
                self.reading_menu.close()
                del self.reading_menu

            signal = t.signals(name='_close_menu' + str(self.parent.database[0]), reset=True)

            d1 = [
                dict(
                    text='BOOKMARK',
                    widget=NewBookmark,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    kwargs=dict(
                        type='_page_new_bookmark',
                        extravar=dict(
                            parent=self,
                            killsignal=signal,
                        )
                    ),
                )]
            d2 = [
                dict(
                    text='NEXT PAGE',
                    widget=ChangePage,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    kwargs=dict(
                        type='_next_page',
                        extravar=dict(
                            change_page=self.parent.goto_next_page,
                            killsignal=signal,
                        )
                    )
                ),
                dict(
                    text='PREV PAGE',
                    widget=ChangePage,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    kwargs=dict(
                        type='_prev_page',
                        extravar=dict(
                            change_page=self.parent.goto_previous_page,
                            killsignal=signal,
                        )
                    )
                )]
            d3 = [
                dict(
                    text='FIRST PAGE',
                    widget=ChangePage,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    kwargs=dict(
                        type='_first_page',
                        extravar=dict(
                            change_page=self.parent.show_this_page,
                            killsignal=signal,
                        )
                    )
                ),
                dict(
                    text='LAST PAGE',
                    widget=LastPage,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    kwargs=dict(
                        type='_last_page',
                        extravar=dict(
                            show_this_page=self.parent.show_this_page,
                            current_and_how_many_pages=self.current_and_how_many_pages,
                            killsignal=signal,
                        )
                    )
                ),
                dict(
                    text='3s PAGE TURN',
                    widget=AutoChangePage,
                    post_init=True,
                    button_width_factor=2,
                    maxsize=12,
                    tooltip='changes page every 3 seconds\nPRESS CTRL+Q to stop\nCTRL+UP / DOWN change speed',
                    kwargs=dict(
                        type='_autocycle_3_sec',
                        extravar=dict(
                            goto_next_page=self.parent.goto_next_page,
                            current_and_how_many_pages=self.current_and_how_many_pages,
                            dummy=self.parent.main.dummy,
                            pixmap_object=self.parent.pixmap_object
                        )
                    )
                ),
            ]

            def generate_menu_title(self):
                primary, secondary, total = self.current_and_how_many_pages()
                title = f"PAGE {primary + 1}"

                if secondary:
                    title += f" and {secondary + 1}"
                if total:
                    title += f" of {total}"

                return title

            set = UniversalSettingsArea(self)

            title = generate_menu_title(self)
            header = set.make_header(title=title, width=200, height=22)

            bg1 = set.make_this_into_checkable_buttons(d1, canvaswidth=200)
            bg2 = set.make_this_into_checkable_buttons(d2, canvaswidth=200)
            bg3 = set.make_this_into_checkable_buttons(d3, canvaswidth=200)

            xpos = ev.pos().x()
            ypos = ev.pos().y()

            t.pos(set, move=[xpos-50, ypos-30])
            t.pos(bg1, below=header, y_margin=3)
            t.pos(bg2, below=bg1, y_margin=5)
            t.pos(bg3, below=bg2, y_margin=5)

            set.expand_me([x for x in set.blackgrays])

            signal.finished.connect(lambda: set.close())

            self.reading_menu = set


    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        _, two_pages, __ = self.current_and_how_many_pages()

        if not two_pages and self.width() > self.height():
            two_pages = True

        x = self.parent.x()
        y = self.parent.y()

        if not two_pages and self.parent.reading_position_one_page != (x,y,):
            self.parent.reading_position_one_page = (x,y,)
            t.save_config('reading_position_one_page', self.parent.reading_position_one_page)

        elif two_pages and self.parent.reading_position_two_page != (x,y,):
            self.parent.reading_position_two_page = (x,y,)
            t.save_config('reading_position_two_page', self.parent.reading_position_two_page)

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self.parent):
            return

        delta = QPoint(event.globalPos() - self.parent.old_position)
        self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
        self.parent.old_position = event.globalPos()

class PAGE(QtWidgets.QLabel):
    def __init__(self, main=None, database=None, index=0, file=None):
        super().__init__()
        self.setLineWidth(0)
        self.setMidLineWidth(0)

        self.main = main

        self.reading_position_one_page = t.config('reading_position_one_page') or (0,0,)
        self.reading_position_two_page = t.config('reading_position_two_page') or (0,0,)

        self.setWindowFlags(Qt.FramelessWindowHint)

        self.pixmap_object = EachPage(self, parent=self)

        self.pixmap_object.setScaledContents(True)
        self.pixmap_object.setLineWidth(0)
        self.pixmap_object.setMidLineWidth(0)

        self.base_layout = QtWidgets.QVBoxLayout(self)
        self.base_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setFrameStyle(0)
        self.scroll_area.setWidgetResizable(True)

        self.scroll_area_contents = QtWidgets.QWidget()

        self.content_layout = QtWidgets.QGridLayout(self.scroll_area_contents)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area.setWidget(self.scroll_area_contents)

        self.base_layout.addWidget(self.scroll_area)

        self.v_scroller = self.scroll_area.verticalScrollBar()
        self.v_scroller.setStyleSheet("width:0")

        self.h_scroller = self.scroll_area.horizontalScrollBar()
        self.h_scroller.setStyleSheet("width:0")

        self.page_turn_shortcut_left = QShortcut(QKeySequence('left'), self)
        self.page_turn_shortcut_left.activated.connect(self.goto_previous_page)
        self.page_turn_shortcut_right = QShortcut(QKeySequence("right"), self)
        self.page_turn_shortcut_right.activated.connect(self.goto_next_page)

        modes = dict(
            reading_mode_one='1',
            reading_mode_two='2',
            reading_mode_three='3',
            reading_mode_four='4',
        )

        for k, v in modes.items():
            change_mode_triggered = QShortcut(QKeySequence(v), self)
            change_mode_triggered.activated.connect(partial(self.mode_change, modes=modes, value=k))

        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.quit)

        self.main.shadehandler()
        self.show()

        self.post_init(database, file, index)
        if not self.show_this_page(index=self.who_am_primary, next=True):
            self.close()

    def quit(self):
        """
        if open infowidget from the same database
        shade not closed (signal not emitted)
        """
        signal = t.signals('reading')
        signal.finished.emit()
        self.close()

        for i in self.main.widgets['info']:
            if i.database[0] == self.database[0]:
                return

        signal = t.signals('shade')
        signal.quit.emit()

    def post_init(self, database, file, index):
        self.who_am_primary = index
        self.who_am_secondary = False

        if file and not database:
            self.file = file
            data = sqlite.execute('select * from comics where local_path = (?)', file)
            if data:
                self.database = data
            else:
                self.database = None

        elif database:
            self.database = database
            self.file = self.database[DB.comics.local_path]

    def mode_change(self, modes, value):
        signalgroup = t.signals('reading_modes')
        signalgroup.checkgroup_master.emit(value)

        for mode,_ in modes.items():
            if mode == value:
                t.save_config(mode, True)
            else:
                t.save_config(mode, False)

        self.show_this_page(index=self.who_am_primary, next=True)

    def goto_previous_page(self):
        self.who_am_primary -= 1
        self.show_this_page(self.who_am_primary, previous=True)

    def goto_next_page(self):
        self.who_am_primary += 1
        if not self.show_this_page(self.who_am_primary, next=True):
            self.who_am_primary += -1

    def attach_qgrip_to_image(self):
        self.qgrip = QtWidgets.QSizeGrip(self.pixmap_object, styleSheet='background-color:rgba(0,0,0,0)')
        self.qgrip.setGeometry(self.width() - 30, self.height() - 30, self.width(), 30)
        self.qgrip.show()

    def set_pixmap_mode_one(self, imgfile):
        width, height = self.get_screen_size()

        self.pixmap = QPixmap(imgfile).scaledToHeight(height, QtCore.Qt.SmoothTransformation)

        if self.pixmap.width() > width:
            self.pixmap = QPixmap(imgfile).scaledToWidth(width, QtCore.Qt.SmoothTransformation)

        self.pixmap_object.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.pixmap_object.setPixmap(self.pixmap)
        self.content_layout.addWidget(self.pixmap_object)
        t.pos(self, size=[self.pixmap.width(), self.pixmap.height()])
        self.attach_qgrip_to_image()

        self.pixmap_object.primary = 0, 0.9999
        self.pixmap_object.secondary = False
        self.who_am_secondary = False

    def set_pixmap_mode_two(self, imgfile):
        width, height = self.get_screen_size()

        self.pixmap = QPixmap(imgfile).scaledToWidth(width, QtCore.Qt.SmoothTransformation)

        self.pixmap_object.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.pixmap_object.setPixmap(self.pixmap)
        self.content_layout.addWidget(self.pixmap_object)
        t.pos(self, size=[width, height])
        self.attach_qgrip_to_image()

        self.pixmap_object.primary = 0, 0.9999
        self.pixmap_object.secondary = False
        self.who_am_secondary = False

    def set_pixmap_mode_three(self, index=0, next=False, previous=False):

        def get_next_pages(self):
            if index == 0:
                prm, nxt = 0, 1

            elif next:
                if index == self.who_am_secondary:
                    prm, nxt = 1, 2
                else:
                    prm, nxt = 0, 1

            elif previous:
                if self.who_am_primary == self.who_am_secondary:
                    prm, nxt = -2, -1
                else:
                    prm, nxt = -1, 0

            return prm, nxt

        def unpack_files_return_two_or_show_one(self, index, next, primary_diff, next_diff):
            primary = extract_from_zip_or_pdf(database=self.database, index=index + primary_diff)
            secondary = extract_from_zip_or_pdf(database=self.database, index=index + next_diff)

            if not primary and not secondary:
                return False, None, None

            elif not primary and next:
                return False, None, None

            elif not primary and previous:
                self.who_am_secondary = False
                self.who_am_primary = index + next_diff
                self.set_pixmap_mode_one(secondary)
                return True, None, None

            return True, primary, secondary

        def put_together_primary_and_secondary(self):
            width, height = self.get_screen_size()
            primarypixmap = QPixmap(primary).scaledToHeight(height, QtCore.Qt.SmoothTransformation)

            if secondary:

                secondarypixmap = QPixmap(secondary).scaledToHeight(height, QtCore.Qt.SmoothTransformation)

                if primarypixmap.width() + secondarypixmap.width() < width:

                    def merge_two_side_by_side_spacersize(self, spacer=0):
                        pm = QtGui.QPixmap(primarypixmap.width() + spacer + secondarypixmap.width(), height)
                        pm.fill(QtCore.Qt.black)

                        painter = QtGui.QPainter(pm)

                        prmsize = QtCore.QRectF(0, 0, primarypixmap.width(), primarypixmap.height())
                        secsize = QtCore.QRectF(
                            primarypixmap.width() + spacer, 0, secondarypixmap.width(), secondarypixmap.height())

                        painter.drawPixmap(prmsize, primarypixmap, QtCore.QRectF(primarypixmap.rect()))
                        painter.drawPixmap(secsize, secondarypixmap, QtCore.QRectF(secondarypixmap.rect()))

                        if t.config('draw_outlines'):
                            pen = QPen()
                            pen.setWidth(3)
                            col = QColor()
                            col.setRgb(40,40,40)
                            pen.setColor(col)
                            painter.setPen(pen)

                            painter.drawRect(0, 0, primarypixmap.width(), height - 3)
                            painter.drawRect(primarypixmap.width() + spacer, 0, secondarypixmap.width()-2, height - 3)

                        self.pixmap = pm
                        self.pixmap_object.setPixmap(self.pixmap)

                        self.pixmap_object.primary = 0, primarypixmap.width() / pm.width() # x percent
                        self.pixmap_object.secondary = (primarypixmap.width() + spacer) / pm.width(), 1

                        self.content_layout.addWidget(self.pixmap_object)

                        t.pos(self, size=[pm.width(), pm.height()])
                        self.attach_qgrip_to_image()

                        painter.end()

                        self.who_am_primary = index + prm
                        self.who_am_secondary = index + nxt

                    if t.config('reading_mode_three'): # sewed side by side
                        merge_two_side_by_side_spacersize(self, spacer=0)
                        return True

                    elif t.config('reading_mode_four'):
                        spaceleft = width - (primarypixmap.width() + secondarypixmap.width())
                        if spaceleft >= 25:
                            spaceleft = 25

                        merge_two_side_by_side_spacersize(self, spacer=spaceleft)
                        return True

                else:
                    self.who_am_secondary = False
                    if previous:
                        self.who_am_primary = index + nxt
                        self.set_pixmap_mode_one(secondary)
                    else:
                        self.who_am_primary = index + prm
                        self.set_pixmap_mode_one(primary)
                    return True
            else:
                self.who_am_secondary = False
                self.who_am_primary = index + prm
                self.set_pixmap_mode_one(primary)
                return True

        prm, nxt = get_next_pages(self)

        status, primary, secondary = unpack_files_return_two_or_show_one(self,
                                                            index=index, next=next, primary_diff=prm, next_diff=nxt)
        if not status:
            return False

        put_together_primary_and_secondary(self)
        return True

    def get_screen_size(self):
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        height = screen.height()
        width = screen.width()
        return width, height

    def show_this_page(self, index=0, next=False, previous=False):
        if not 'database' in dir(self):
            return False
        else:
            self.database = sqlite.refresh_db_input('comics', self.database)

        if not self.database:
            return False

        if not os.path.exists(self.database[DB.comics.local_path]):
            return

        if index < 0:
            self.who_am_primary = 0
            return

        elif t.config('reading_mode_two'):
            page = extract_from_zip_or_pdf(database=self.database, index=index)
            if not page:
                return False

            self.pixmap_object.clear()
            self.set_pixmap_mode_two(page)

        elif t.config('reading_mode_three') or t.config('reading_mode_four'):
            if not self.set_pixmap_mode_three(index=index, next=next, previous=previous):
                return False

        else: # fallback to reading_mode_one
            page = extract_from_zip_or_pdf(database=self.database, index=index)
            if not page:
                return False

            self.pixmap_object.clear()
            self.set_pixmap_mode_one(page)

        self.clear_bookmarks()
        self.show_bookmarks()
        self.cleanup()
        return True

    def clear_bookmarks(self):
        for category in ['buttons', 'widgets']:
            for i in range(len(self.pixmap_object.bookmarks[category])-1,-1,-1):
                self.pixmap_object.bookmarks[category][i].close()
                self.pixmap_object.bookmarks[category].pop(i)

    def show_bookmarks(self, only_this_bookmark_id=False):
        """
        makes a small bookmark button on the image thats clickable and opening the bookmark widget
        :param only_this_bookmark_id: will ONLY draw this bookmark and ignoring others
        """
        class MoveBookMark(QtWidgets.QLabel):
            def __init__(self, place):
                """
                this is unsmart solution for moving bookmark button around.
                8 pixel width on each end makes button movable instead of clickable
                """
                super().__init__(place)
                self.parent = place
                self.show()

            def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 2:
                    return

                if 'old_position' not in dir(self.parent):
                    return

                delta = QPoint(ev.globalPos() - self.parent.old_position)
                self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
                self.parent.old_position = ev.globalPos()

            def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
                pass

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.parent.old_position = ev.globalPos()

        class ShowSavedBookmarkButton(GLOBALDeactivate):
            def __init__(self, place, database, bookmark_id, *args, **kwargs):
                """
                given database and bookmark_id it will unpack bookmarks dictionary
                and iter until it finds bookmark id and then draw it self
                :param database: tuple
                :param bookmark_id: string
                """
                super().__init__(place=place, *args, **kwargs)

                self.parent.bookmarks['buttons'].append(self)

                self.database = database
                self.bookmark_id = bookmark_id
                self.showing_child_widget = False
                self.setFrameShape(QtWidgets.QFrame.Box)
                self.setLineWidth(2)
                self.setText('BOOKMARK')
                self.default_event_colors()
                self.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                t.style(self, background=BTN_OFF, color=TXT_BLACK)
                t.pos(self, size=[80,20])
                t.correct_broken_font_size(self, maxsize=13)
                self.make_movalbe_ends()

            def make_movalbe_ends(self):
                """
                makes edge-handles to move self around
                """
                for i in [8, self.width()]:
                    move_label = MoveBookMark(self)
                    t.pos(move_label, inside=self, width=8, right=i)
                    t.style(move_label, background='transparent')

            def load_dictionary_show_widget(self):

                def make_nice_position(self, set):
                    t.pos(set, top=dict(bottom=self), left=dict(right=self), y_margin=10)

                    if set.geometry().right() > self.parent.geometry().right():
                        t.pos(set, right=self, x_margin=10)

                    if set.geometry().bottom() > self.parent.geometry().bottom():
                        t.pos(set, bottom=dict(top=self), y_margin=10)

                b = pickle.loads(self.database[DB.comics.bookmarks])
                for page in b:
                    for bookmark_id, values in b[page].items():
                        if bookmark_id == self.bookmark_id:
                            set = make_bookmark(self.parent, bookmark_id=bookmark_id, parent_button=self)
                            set.textedit.setText(values['text'])
                            self.parent.bookmarks['widgets'].append(set)
                            make_nice_position(self, set)
                            self.showing_child_widget = True
                            return

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if self.type:
                    for i in self.parent.bookmarks['widgets']:
                        if i.bookmark_id == self.bookmark_id:
                            if self.showing_child_widget:
                                self.showing_child_widget = False
                                i.hide()
                            else:
                                self.showing_child_widget = True
                                i.show()
                            return

                self.database = sqlite.refresh_db_input('comics', self.database)

                if not self.database[DB.comics.bookmarks]:
                    return

                self.load_dictionary_show_widget()

            def default_event_colors(self):
                self.directives['activation'] = [
                    dict(object=self, background=BTN_SHINE, color=TXT_BLACK),
                ]

                self.directives['deactivation'] = [
                    dict(object=self, background=BTN_OFF, color=TXT_BLACK),
                ]

        if not self.database[DB.comics.bookmarks]:
            return

        b = pickle.loads(self.database[DB.comics.bookmarks])

        primary, secondary, _ = self.pixmap_object.current_and_how_many_pages()

        self.pixmap_object.show()

        def get_width_height_page_one_x_end(self):
            total_w = self.pixmap.width()
            total_h = self.pixmap.height()
            page_one_x_ends = total_w * self.pixmap_object.primary[1]
            return total_w, total_h, page_one_x_ends

        def position_primary_bookmark(self, bookmark):
            total_w, total_h, page_one_x_ends = get_width_height_page_one_x_end(self)
            x = page_one_x_ends * vv['x']
            y = total_h * vv['y']
            t.pos(bookmark, left=x, top=y)

        def position_secondary_bookmark(self, bookmark):
            total_w, total_h, page_one_x_ends = get_width_height_page_one_x_end(self)
            page_two_x_start = total_w * self.pixmap_object.secondary[0]
            page_two_pixels = total_w - page_two_x_start

            x = page_two_x_start + (page_two_pixels * vv['x'])
            y = total_h * vv['y']
            t.pos(bookmark, left=x, top=y)

        def make_primary_bookmark(self, exclusive_bookmark, bookmark_id, database):
            if exclusive_bookmark and bookmark_id != exclusive_bookmark:
                return

            bm = ShowSavedBookmarkButton(
                self.pixmap_object, type='_bm_btn' + kk, bookmark_id=bookmark_id, database=database)
            position_primary_bookmark(self, bookmark=bm)

        def make_secondary_bookmark(self, exclusive_bookmark, bookmark_id, database):
            if exclusive_bookmark and bookmark_id != exclusive_bookmark:
                return

            bm = ShowSavedBookmarkButton(
                self.pixmap_object, type='_bm_btn' + kk, bookmark_id=bookmark_id, database=database)
            position_secondary_bookmark(self, bookmark=bm)

        for k,v in b.items():

            if k == primary and not secondary:
                for kk, vv in b[k].items():
                    make_primary_bookmark(
                        self, exclusive_bookmark=only_this_bookmark_id, bookmark_id=kk, database=self.database)

            elif secondary:

                if k == primary:
                    for kk, vv in b[k].items():
                        make_primary_bookmark(
                            self, exclusive_bookmark=only_this_bookmark_id, bookmark_id=kk, database=self.database)

                elif k == secondary:
                    for kk, vv in b[k].items():
                        make_secondary_bookmark(self, only_this_bookmark_id, bookmark_id=kk, database=self.database)

    def cleanup(self):

        def update_current_page_progress(self):
            query = 'update comics set last_opened = (?) where id is (?)'
            values = (int(time.time()), self.database[0],)
            sqlite.execute(query=query, values=values)

            if not self.database[DB.comics.current_page] or self.database[DB.comics.current_page] < self.who_am_primary:
                query = 'update comics set current_page = (?) where id is (?)'
                values = (self.who_am_primary, self.database[0],)
                sqlite.execute(query=query, values=values)

                self.database = sqlite.execute('select * from comics where id is (?)', self.database[0], one=True)

        def set_scroller_and_position(self):
            self.v_scroller.setValue(0)

            _, two_pages, __ = self.current_and_how_many_pages()

            if not two_pages and self.width() > self.height():
                two_pages = True

            if not two_pages:
                x, y = self.reading_position_one_page[0], self.reading_position_one_page[1]
                self.setGeometry(x, y, self.width(), self.height())
            else:
                x, y = self.reading_position_two_page[0], self.reading_position_two_page[1]
                self.setGeometry(x, y, self.width(), self.height())

        set_scroller_and_position(self)
        update_current_page_progress(self)
        self.setWindowTitle(f"{self.database[DB.comics.local_path]} page: {self.database[DB.comics.current_page]}")

        pages = self.who_am_primary, self.who_am_secondary or -1
        for k, v in dict(_close_menu=None, _refresh_page_squares=None, _lit_my_square=pages).items():
            signal = t.signals(name=k + str(self.database[0]))
            if v:
                signal.pagenumbers.emit(v)  # closing reading menu, refresh pagecounts (not beautiful, lazy)
            else:
                signal.finished.emit()  # closing reading menu, refresh pagecounts (not beautiful, lazy)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # this is the grip that resizes the window
        if 'qgrip' in dir(self):
            self.qgrip.setGeometry(self.width()-30, self.height() - 30, self.width(), 30)



class Cover(GOD):
    def __init__(self, place, main=None, type=None):
        super().__init__(place, main=main, type=type)
        self.setMouseTracking(True)


    def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'readme_button' in dir(self.parent):
            self.parent.readme_button.toggle(ev)

    def set_pixmap(self, force=False, pixmap=None):
        """
        :param force: overrides stop (bool) in self.showing_pixmap
        :param pixmap: QPixmap
        """
        if force or pixmap:
            self.clear()

        if self.showing_pixmap and not force and not pixmap:
            return

        if not pixmap:
            pixmap = QPixmap(self.path).scaled(
                self.width(), self.height(), transformMode=QtCore.Qt.SmoothTransformation)

        self.setPixmap(pixmap)
        self.showing_pixmap = True

    def first_reize(self, cover_height):
        """
        uses the default size from settings an resizes the image according to that
        then sets the parent size to suit the child.
        the image isnt actually shown here if the settings doesnt alow it to be
        preshown, image instead may be set once the fn:fill_row commands it
        """
        pixmap = QPixmap(self.path).scaledToHeight(cover_height)

        if pixmap.width() > cover_height * 3:
            pixmap = QPixmap(self.path).scaled(cover_height, cover_height * 3)

        t.pos(self.parent, size=pixmap, add=2) # sets parent to suit childs geometry
        t.pos(self, inside=self.parent, margin=1) # then center child within parent
        self.preshow_images(pixmap=pixmap) # give global settings opportunity to preshow pixmap

    def preshow_images(self, pixmap=None, force=False):
        """
        duing first drawing the covers are shown even if
        the widget maybe is cleared during second positioning
        :param pixmap: QPixmap
        """
        if t.config('pre_squeeze'): # shows images duing prepositioning
            if pixmap or force:
                self.set_pixmap(pixmap=pixmap, force=force)

    def second_resize(self):
        """
        fn:fill_row has decided size and sets
        it now and forces the set_pixmap along the way
        """
        t.pos(self, inside=self.parent, margin=1)
        self.set_pixmap(force=True)

class ComicWidget(GOD):
    def __init__(self, place, main=None, type=None):
        super().__init__(place, main=main, type=type)
        self.setMouseTracking(True)
        self.activated = False

    def post_init(self):
        t.style(self)

    def collect_thumbnail(self, coverfile):
        """
        requests the first index from the local_path
        within the database if coverfile is'nt present
        :param coverfile:
        :return: full_path
        """
        if not coverfile:
            cover_height = t.config('cover_height')
            coverfile = get_thumbnail_from_zip_or_database(
                database=self.database, index=0, height=cover_height)
        return coverfile

    def make_cover(self, coverfile=None, cover_height=500):
        """
        create the nessesary widgets sets standard sizes (may change when filling row)
        and preshow image if settings allows it
        :param coverfile: string (or None)
        """
        if not coverfile:
            coverfile = self.collect_thumbnail(coverfile)

        self.cover = Cover(self, self.main, type='cover')
        self.cover.showing_pixmap = False
        self.cover.path = coverfile
        self.cover.first_reize(cover_height)
        self.make_box_of_details(first=True)

    def current_page_process(self, starting_coordinates, current_page=-1, progress=0, enhancefactor=1):
        if current_page == -1:
            current_page = self.database[DB.comics.current_page]

        if current_page and current_page > 0:
            good_files = FileArchiveManager.get_filecontents(database=self.database)
            if good_files:
                progress = current_page / len(good_files)
                progress = self.width() * progress

        self.page_label = t.pos(
            new=self,
            below=starting_coordinates,
            left=self.cover,
            y_margin=1,
            width=progress,
            background='green',
            height=2*enhancefactor,
        )

        self.box_been_set.append(self.page_label)

    def show_rating(self, starting_coordinates, rating=-1, enhancefactor=1):
        """
        makes 10 stars, different appearnce if score
        :param rating: overriding self.database[DB.comics.rating]
        :return: list: self.stars
        """
        self.stars = []

        def calculate_each_space_and_rest():
            """
            calculates the least pixles each star can be in width
            there will be extra space left, this space is divided
            onto each stars width until none is left.
            :return: int: width
            """
            we = (self.width() - 18) / 10
            wf = math.floor(we)
            rest = (we - wf) * 10
            get_extra_space(set=True, restspace=rest)
            return wf

        def get_extra_space(set=False, restspace=0.0):
            """
            keeps track on how many pixels are left in account for extra size
            you get one pixel if there is one in account else you get 0 pixel.
            :param set: stores pixles in account
            :return: 1 or 0
            """
            if set:
                self._restspace = restspace

            if self._restspace >= 1:
                self._restspace -= 1
                return 1
            else:
                return 0

        class LittleStar(GOD):
            def __init__(self, place):
                super().__init__(place)
                self.parent = place
                self.setMouseTracking(True)

            def get_star_visuals(self, count, rating):
                if count <= rating:
                    color = 'rgb(210,210,210)'
                else:
                    color = 'rgb(50,50,50)'

                return color

            def set_all_stars_visuals(self):
                """
                the star that the mouse hovers upon is set
                and all preseedings the rest is not set
                """
                paint = True
                for i in self.parent.stars:

                    if paint:
                        color = self.get_star_visuals(1, 2)
                    else:
                        color = self.get_star_visuals(2, 1)

                    t.style(i, background=color)
                    if i == self:
                        paint = False

            def mouseMoveEvent(self, ev: QtGui.QMouseEvent) -> None:
                if not self.parent.activated or self.parent.metaObject().className() != 'INFOWidget':
                    return

                self.set_all_stars_visuals()

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                for count, i in enumerate(self.parent.stars):
                    if self == i:
                        sqlite.execute(
                            'update comics set rating = (?) where id is (?)', (count+1, self.parent.database[0],))

                        self.parent.database = sqlite.execute(
                            'select * from comics where id is (?)', self.parent.database[0])

        def make_stars(self, rating, starting_coordinates, enhancefactor=1):
            """
            sets one star after another with different appearances
            :param rating: int
            :return: list: self.stars
            """
            width = calculate_each_space_and_rest()

            for c in range(1, 11):
                extra = get_extra_space()
                star = LittleStar(self)
                color = star.get_star_visuals(count=c, rating=rating)

                if c == 1:
                    t.pos(
                        star,
                        below=starting_coordinates,
                        left=self.cover,
                        y_margin=1,
                        height=4 * enhancefactor,
                        width=width + extra,
                        background=color,
                        move=[0,0]
                    )

                elif c != 10:
                    t.pos(star, coat=self.stars[-1], after=self.stars[-1], x_margin=1, background=color)
                else:
                    t.pos(star, coat=self.stars[-1], background=color)
                    t.pos(star, left=self.stars[-1].geometry().right() + 2, right=self.cover)
                    t.pos(star, width=star, add=1) # not sure why yet

                self.stars.append(star)
                self.box_been_set.append(star)

        if rating == -1:
            rating = self.database[DB.comics.rating] or 0

        make_stars(self, rating=rating, starting_coordinates=starting_coordinates, enhancefactor=enhancefactor)

    def make_untagged_disturbing_label(self):
        """
        makes a small label at top right that indicates if this coic is tagged or not
        PDF files are excluded from this without the ability to change it in the gui
        """
        if self.database[DB.comics.comic_id]:
            return

        if t.separate_file_from_folder(self.database[DB.comics.local_path]).ext.lower() == 'pdf':
            return

        l = t.pos(new=self.cover, size=[6,6], left=-1, top=-1)
        l.setToolTip('FILE HAS NOT YET BEEN TAGGED')
        l.setFrameShape(QtWidgets.QFrame.Box)
        l.setLineWidth(1)
        t.style(l, background='transparent', color='rgba(80,80,80,100)')
        t.style(l, background='pink', color='black', border='black', tooltip=True)

        self.box_been_set.append(l)

    def make_size_and_page_label(self, starting_coordinates, enhancefactor=1):
        """
        i'm bleeding this 1 pixel each side to remove that border
        :return: self.size_pages_label
        """
        good_files = FileArchiveManager.get_filecontents(database=self.database)
        size_mb = round(os.path.getsize(self.database[DB.comics.local_path]) / 1000000)
        pages = t.pos(new=self)
        pages.setFrameShape(QtWidgets.QFrame.Box)
        pages.setLineWidth(1)
        pages.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)

        fontsize = str(8 * enhancefactor) + 'pt'
        color = 'rgb(210,210,210)'
        background = 'rgba(20,20,20,230)'

        if not good_files:
            loc = t.separate_file_from_folder(self.database[DB.comics.local_path])
            if loc.ext.lower() == 'pdf':
                pagecount = check_for_pdf_assistance(pdf_file=loc.full_path, pagecount=True)
                if pagecount:
                    pages.setText(f"{pagecount} PAGES   {size_mb} MB")
                    t.style(pages, background=background, color=color, font=fontsize)
                else:
                    pages.setText(f"PDF FILE {size_mb} MB")
                    t.style(pages, background=background, color=color, font=fontsize)
            else:
                pages.setText(f"ERROR READING FILE {size_mb} MB")
                t.style(pages, background=background, color=color, font=fontsize)
        else:
            pages.setText(f"{len(good_files)} PAGES   {size_mb} MB")
            t.style(pages, background=background, color=color, font=fontsize)

        height = pages.fontMetrics().boundingRect(pages.text()).height()
        top = dict(bottom=starting_coordinates)
        t.pos(pages, top=top, left=self.cover, right=self.cover, height=height, y_margin=1, x_margin=-2)

        self.size_pages_label = pages
        self.box_been_set.append(self.size_pages_label)

    def toggle_and_show_active_event(self):
        """
        makes four white labels surrounding the widget,
        these are closed before doing new ones if exists
        """

        def reset_non_set_rating(self):
            """
            resets stars according to self.database[DB.comics.rating]
            this is if user has changed rating but not confirmed it
            """
            if 'stars' in dir(self) and self.database:
                for count, star in enumerate(self.stars):
                    rating = self.database[DB.comics.rating] or 0
                    color = star.get_star_visuals(count+1, rating)
                    t.style(star, background=color)

        self.activation_toggle(save=False)
        reset_non_set_rating(self)
        self.draw_white_lines()

    def draw_white_lines(self, color='white', force=False, width=1):
        def close_previous_whites(self):
            if 'four_whites' in dir(self):
                for i in self.four_whites:
                    i.close()
            else:
                self.four_whites = []

        close_previous_whites(self)

        if self.activated or force:
            color = t.config('four_whites') or color
            # x-axis
            self.four_whites.append(
                t.pos(new=self, height=width, width=self, background=color))
            self.four_whites.append(
                t.pos(new=self, height=width, width=self, background=color, move=[0, self.height() - width]))
            # y-axis
            self.four_whites.append(
                t.pos(new=self, height=self, width=width, background=color))
            self.four_whites.append(
                t.pos(new=self, height=self, width=width, background=color, move=[self.width() - width, 0]))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            # close all other white surrounding labels than self
            for i in self.main.widgets['main']:
                if i != self and i.activated:
                    i.toggle_and_show_active_event()

            self.toggle_and_show_active_event()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        from bscripts.infowidget import INFOWidget

        if ev.button() == 1:
            if 'database' in dir(self) and self.database:
                self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)
                if self.database:
                    page = PAGE(main=self.main, database=self.database, index=0)
                    self.main.pages_container.append(page)
                else:
                    self.draw_white_lines(color='red', force=True, width=3)

            elif not 'database' in dir(self) or not self.database:
                self.draw_white_lines(color='red', force=True, width=3)
                return

        elif ev.button() == 2:
            if 'database' in dir(self) and self.database:
                self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)

            if not 'database' in dir(self) or not self.database:
                self.draw_white_lines(color='red', force=True, width=3)
                return

            for count, i in enumerate(self.main.widgets['info']):
                if not i.database:
                    continue

                if i.database[0] == self.database[0]:
                    i.close()
                    self.main.widgets['info'].pop(count)
                    break

            self.main.shadehandler()

            infowidget = INFOWidget(self.main.back, self, self.main, type='info_widget', database=self.database)
            infowidget.move(300,40)
            self.main.widgets['info'].append(infowidget)

    def delete_box_of_details(self, all=True):
        """
        when a single cover is left alone with a detailbox while using squeeze mode
        it should be redone at cleanup when processing next batch, else looks ugly
        todo this is a lazy fix!
        :param: all: True = deletes all non-squeezed boxes, False = just self (mine)
        """
        if t.config('squeeze_mode'):
            for i in self.main.get_repositioned():

                if not all and i != self:
                    continue

                if 'box_been_set' in dir(i) and i.box_been_set:
                    for count in range(len(i.box_been_set)-1,-1,-1):
                        i.box_been_set[count].close()
                        i.box_been_set.pop(count)

                    t.pos(i, height=i.cover, add=2)

    def make_box_of_details(self, first=False, enhancefactor=1, force=False):

        if t.config('squeeze_mode') and first:
            return

        if 'box_been_set' in dir(self) and self.box_been_set:
            return

        self.box_been_set = []
        start_from = self.cover

        if force or t.config('show_ratings'):
            self.show_rating(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.stars[-1]

        if force or t.config('show_reading_progress'):
            self.current_page_process(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.page_label

        if force or t.config('show_page_and_size'):
            self.make_size_and_page_label(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.size_pages_label

        if force or t.config('show_untagged_flag'):
            self.make_untagged_disturbing_label()

        t.pos(self, height=start_from.geometry().bottom() + 1)


    def set_position(self):
        self.delete_box_of_details() # new will be set

        wt, ht, nw, nh = self.main.get_wt_ht(key='main')

        parent_space = self.parent.width()
        wlist = self.main.get_repositioned()

        if self.width() + wt > parent_space and len(wlist) == 1: # new row, first widget
            self.setGeometry(nw, nh, self.width(), self.height())

        elif self.width() + wt <= parent_space: # >second widget enough room, no squeeze now
            self.setGeometry(wt, ht, self.width(), self.height())

        elif not t.config('squeeze_mode'): # this is kind of the usual way of showing images (but not LSC default)
            self.setGeometry(nw, nh, self.width(), self.height())

        else: # SQUEEZE WIDGETS
            def change_widget_and_cover(widget, each, grow, rest=0, follower=0, reposition=True):
                """
                :param each: int extra amount of pixles to add or subract
                :param grow: bool (if we shrink or expands the HEIGHT to reach symetri)
                :param rest: int 1 or 0 extra pixels added to the width eventually fills row niceley
                :param follower: if False meaning this is the first widget of the row, all others are "followers"
                :param reposition: bool, only the followers should be assigned True
                """
                wt, ht, nw, nh = self.main.get_wt_ht(key='main')
                w = widget.width() + each + rest

                if grow:
                    h = int(widget.height() + (each * 1.2))
                elif not grow:
                    h = int(widget.height() + (each * 0.8))

                if not follower:
                    wt = nw
                    ht = nh

                widget.repositioned = reposition
                widget.setGeometry(wt, ht, w, h)
                widget.cover.second_resize()
                widget.make_box_of_details(first=False) # meaning its second
                widget.show()

            def determine_if_grow(self):
                """
                determin if we should shrink widgets to fit one more or if we
                should grow the remaning becuse one extra takes to much space
                this based of the remaning space avalible in parents row
                :return: bool
                """
                if (parent_space - wt) * 2 > self.width():
                    grow = True
                else:
                    grow = False

                for count in range(len(wlist)-1,-1,-1):
                    wlist[count].hide()
                    if wlist[count] == self and grow:
                        self.setGeometry(0, 0, self.width(), self.height())
                        wlist.pop(count)
                    else:
                        wlist[count].setGeometry(0,0,wlist[count].width(),wlist[count].height())

                return grow

            def determine_rest(rest, count):
                """
                :param rest: int (posetive for grow negative for not grow)
                :param count: int (wlist iter)
                :return: int (1 or 0, the extra width to add to widget)
                """
                if rest > 0 and rest - count > 0: # grow is True
                    return 1
                elif rest < 0 and rest + count < 0: # grow is False
                    return 1
                else:
                    return 0

            if determine_if_grow(self): # skip last and grow previous to fill row
                space_left = parent_space - wt

                each = math.floor(space_left / len(wlist))
                rest = space_left - (each * len(wlist))

                for count, widget in enumerate(wlist):
                    change_widget_and_cover(widget, each, grow=True, rest=determine_rest(rest, count), follower=count)

                change_widget_and_cover(self, each=0, grow=-1, follower=False, reposition=False)
                return True # affects self.main.fill_row only

            else: # shrink all to squeeze one more
                space_exceed = (wt + self.width()) - self.parent.width() + 1

                each = math.ceil(space_exceed / len(wlist))
                rest = space_exceed - (each * len(wlist))

                for count, widget in enumerate(wlist):
                    change_widget_and_cover(widget, -each, grow=False, rest=determine_rest(rest, count), follower=count)
