from bscripts.file_handling import concurrent_pdf_to_webp_convertion, concurrent_cbx_to_webp_convertion
import pickle
import shutil
import os
import time
import shutil
from PyQt5                   import QtCore, QtGui, QtWidgets
from PyQt5.QtCore            import QPoint, Qt
from PyQt5.QtGui             import QColor, QImage, QKeySequence, QPainter
from PyQt5.QtGui             import QPalette, QPen, QPixmap
from PyQt5.QtPrintSupport    import QPrintDialog, QPrinter
from PyQt5.QtWidgets         import QAction, QLabel, QMainWindow, QMessageBox
from PyQt5.QtWidgets         import QScrollArea, QShortcut, QSizePolicy
from bscripts.database_stuff import DB, sqlite
from bscripts.file_handling  import FileArchiveManager, check_for_pdf_assistance, extract_from_zip_or_pdf
from bscripts.file_handling  import get_thumbnail_from_zip_or_database, unzipper
from bscripts.tricks         import tech as t
#from bscripts.widgets        import GOD
from functools               import partial
from script_pack.settings_widgets import UniversalSettingsArea, HighlightRadioBoxGroup, FolderSettingsWidget,ExecutableLookCheckable, GLOBALDeactivate, GOD
import math
import os

class PAGE(QtWidgets.QLabel):
    def __init__(self, main=None, database=None, index=0, file=None):
        super().__init__()
        self.setLineWidth(0)
        self.setMidLineWidth(0)

        self.main = main

        if t.config('prefered_reading_position'):
            self.prefered_reading_position = t.config('prefered_reading_position')
        else:
            self.prefered_reading_position = (0,0,)

        self.setWindowFlags(Qt.FramelessWindowHint)

        self.pixmap_object = QtWidgets.QLabel(self)

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

        self.show()

        self.post_init(database, file, index)
        self.show_this_page(index=self.who_am_primary, next=True)

    def quit(self):
        self.close()

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
        self.show_this_page(self.who_am_primary, next=True)

    def attach_qgrip_to_image(self):
        self.qgrip = QtWidgets.QSizeGrip(self, styleSheet='background-color:rgba(0,0,0,0)')
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

    def set_pixmap_mode_two(self, imgfile):
        width, height = self.get_screen_size()

        self.pixmap = QPixmap(imgfile).scaledToWidth(width, QtCore.Qt.SmoothTransformation)

        self.pixmap_object.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.pixmap_object.setPixmap(self.pixmap)
        self.content_layout.addWidget(self.pixmap_object)
        t.pos(self, size=[width, height])
        self.attach_qgrip_to_image()

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
                        secsize = QtCore.QRectF(primarypixmap.width() + spacer, 0, secondarypixmap.width(), secondarypixmap.height())

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

                        self.pixmap_object.setPixmap(pm)

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
        if not os.path.exists(self.database[DB.comics.local_path]):
            self.database = sqlite.refresh_db_input('comics', self.database)
            if not os.path.exists(self.database[DB.comics.local_path]):
                return

        if index < 0:
            self.who_am_primary = 0
            return

        elif t.config('reading_mode_two'):
            page = extract_from_zip_or_pdf(database=self.database, index=index)
            if not page:
                return False

            self.clear()
            self.set_pixmap_mode_two(page)

        elif t.config('reading_mode_three') or t.config('reading_mode_four'):
            if not self.set_pixmap_mode_three(index=index, next=next, previous=previous):
                return False

        else: # fallback to reading_mode_one
            page = extract_from_zip_or_pdf(database=self.database, index=index)
            if not page:
                return False

            self.clear()
            self.set_pixmap_mode_one(page)

        self.cleanup()

    def cleanup(self):

        # def when_done(self):
        #     """
        #     this is a dev thingey, removes PDF unpackables afterwards
        #     """
        #     loc = t.separate_file_from_folder(self.file)
        #     if loc.ext.lower() == 'pdf' and t.config('single_pdf2webp'):
        #         signal = t.signals('now_showing_page(s)', reset=True)
        #         signal.finished.emit()

        def update_current_page_progress(self):
            if not self.database[DB.comics.current_page] or self.database[DB.comics.current_page] < self.who_am_primary:
                sqlite.execute(
                    'update comics set current_page = (?) where id is (?)', (self.who_am_primary, self.database[0],))

                self.database = sqlite.execute('select * from comics where id is (?)', self.database[0], one=True)

        def set_scroller_and_position(self):
            self.v_scroller.setValue(0)
            x, y = self.prefered_reading_position[0], self.prefered_reading_position[1]
            self.setGeometry(x, y, self.width(), self.height())

        set_scroller_and_position(self)
        update_current_page_progress(self)
        #t.start_thread(self.main.dummy, worker_arguments=1, finished_function=when_done, finished_arguments=self)
        self.setWindowTitle(f"{self.database[DB.comics.local_path]} page: {self.database[DB.comics.current_page]}")


    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        x = self.x()
        y = self.y()

        self.prefered_reading_position = (x,y,)
        t.save_config('prefered_reading_position', self.prefered_reading_position)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # this is the grip that resizes the window
        if 'qgrip' in dir(self):
            self.qgrip.setGeometry(self.width()-30, self.height() - 30, self.width(), 30)

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self):
            return
        delta = QPoint(event.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = event.globalPos()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.old_position = ev.globalPos()


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
                database=self.database, index=0, store=t.config('cover_blob'), height=cover_height)
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
                        y_margin=1,
                        height=4 * enhancefactor,
                        width=width + extra,
                        background=color,
                        move=[0,0]
                    )

                elif c != 10:
                    t.pos(star, coat=self.stars[-1], rightof=self.stars[-1], x_margin=1, background=color)
                else:
                    t.pos(star, coat=self.stars[-1], background=color)
                    t.pos(star, left=self.stars[-1].geometry().right() + 2, right=self.cover.geometry().right() + 2)

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

        l = t.pos(new=self.cover, size=[8,8], right=self.cover.geometry().right() - 1, move=[0,1])
        l.setToolTip('FILE HAS NOT YET BEEN TAGGED')
        l.setFrameShape(QtWidgets.QFrame.Box)
        l.setLineWidth(1)
        t.style(l, background='rgba(50,50,50,50)', color='rgba(80,80,80,200)')
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
        t.pos(pages, width=self.width() + 2, height=height, below=starting_coordinates, move=[-1,0], y_margin=1)
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
        try: print("showing local path", self.database[DB.comics.local_path])
        except: pass
        if ev.button() == 1:
            # close all other white surrounding labels than self
            for i in self.main.widgets['main']:
                if i != self and i.activated:
                    i.toggle_and_show_active_event()

            self.toggle_and_show_active_event()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if self.database:
            self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)

        if not self.database:
            self.draw_white_lines(color='red', force=True, width=3)
            return

        for count, i in enumerate(self.main.widgets['info']):
            if not i.database:
                continue

            if i.database[0] == self.database[0]:
                i.close()
                self.main.widgets['info'].pop(count)
                break

        infowidget = INFOWidget(self.main.back, self, self.main, type='info_widget', database=self.database)
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

    def make_box_of_details(self, first=False, enhancefactor=1):

        if t.config('squeeze_mode') and first:
            return

        if 'box_been_set' in dir(self) and self.box_been_set:
            return

        self.box_been_set = []
        start_from = self.cover

        if t.config('show_ratings'):
            self.show_rating(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.stars[-1]

        if t.config('show_reading_progress'):
            self.current_page_process(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.page_label

        if t.config('show_page_and_size'):
            self.make_size_and_page_label(starting_coordinates=start_from, enhancefactor=enhancefactor)
            start_from = self.size_pages_label

        if t.config('show_untagged_flag'):
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

class INFOCoverWidget(Cover):
    def __init__(self, place, main=None, type=None):
        super().__init__(place=place, main=main, type=type)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self.parent):
            del self.parent.old_position

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self.parent):
            return

        delta = QPoint(event.globalPos() - self.parent.old_position)
        self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
        self.parent.old_position = event.globalPos()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.parent.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.parent.quit()

class INFOWidget(ComicWidget):
    def __init__(self, place, parent, main, type, database):
        super().__init__(place=place, main=main, type=type)

        self.parent = parent
        self.database = database
        self.activation_toggle(force=True, save=False)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.quit)
        self.post_init()

    def make_cover(self, coverfile=None, cover_height=500):
        """
        create the nessesary widgets sets standard sizes (may change when filling row)
        and preshow image if settings allows it
        :param coverfile: string (or None)
        """
        if not coverfile:
            coverfile = self.collect_thumbnail(coverfile)

        self.cover = INFOCoverWidget(self, self.main, type='cover')

        self.cover.activation_toggle = self.activation_toggle
        self.cover.activated = True

        self.cover.showing_pixmap = False
        self.cover.path = coverfile
        self.cover.first_reize(cover_height)
        self.make_box_of_details(first=True, enhancefactor=3)

    def post_init(self):

        def generate_global_signal(self):
            global_signal = '_global_on_off_' + str(self.database[0])
            return global_signal

        def make_cover_and_cover_details(self):
            cover_height = t.config('cover_height') * 2
            cover = extract_from_zip_or_pdf(database=self.database)
            self.make_cover(cover_height=cover_height, coverfile=cover)
            self.cover.first_reize(cover_height=cover_height)
            self.make_box_of_details(enhancefactor=3)
            t.pos(self.size_pages_label, move=[1, 0], width=self.size_pages_label.width() - 2)

        def make_type_changer(self):

            class ChangeType(HighlightRadioBoxGroup):

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    query = 'update comics set type = (?) where id is (?)'
                    values = (self._changedict[self.type], self.database[0],)
                    sqlite.execute(query, values)
                    self.enslave_me_signal.deactivate.emit(self.type)

            def generate_type_init_dictionary(self):

                d = [
                    dict(text='COMIC', widget=ChangeType, post_init=True,
                         kwargs=dict(
                             type='_info_comic',
                             signalgroup='info_comic_nsfw_magazines' + str(self.database[0]),
                             extravar=dict(database=self.database, _changedict=_changedict),
                             global_signal=global_signal,
                         )),

                    dict(text='NSFW', widget=ChangeType, post_init=True,
                         kwargs=dict(
                             type='_info_nsfw',
                             signalgroup='info_comic_nsfw_magazines' + str(self.database[0]),
                             extravar=dict(database=self.database, _changedict=_changedict),
                             global_signal=global_signal,
                         )),

                    dict(text='MAGAZINE', widget=ChangeType, post_init=True,
                         kwargs=dict(
                             type='_info_magazine',
                             signalgroup='info_comic_nsfw_magazines' + str(self.database[0]),
                             extravar=dict(database=self.database, _changedict=_changedict),
                             global_signal=global_signal,
                         )),
                ]
                return d

            def make_black_gray_area(self):
                set1 = UniversalSettingsArea(self,
                                             extravar=dict(
                                                 releasing=dict(
                                                     background='gray', color='black'),
                                                 holding=dict(
                                                     background='gray', color='black'),
                                             ))
                return set1

            def make_boxes_and_expand_frame(set1, dictionary):
                set1.make_this_into_checkable_buttons(dictionary, toolsheight=20, linewidth=2)
                set1.expand_me(set1.blackgrays)

            def set_defaults(self, dictionary):
                widgets = [x['label'] for x in dictionary]  # illustrates current category to gui
                for k, v in _changedict.items():
                    if v == self.database[DB.comics.type]:
                        widgets[0].fall_back_to_default(list_with_widgets=widgets, fallback_type=k)

                for i in widgets:  # cannot globaly alter activated
                    if i.activated:
                        i.slaves_can_alter = False

            set1 = make_black_gray_area(self)
            d = generate_type_init_dictionary(self)
            make_boxes_and_expand_frame(set1, dictionary=d)
            set_defaults(self, dictionary=d)
            t.pos(set1, rightof=self.cover, x_margin=5)

            return set1

        def make_read_buttons(self):
            class ReadBTN(GLOBALDeactivate):
                def __init__(self, place, main, type, page=0):
                    super().__init__(place=place, main=main, type=type, global_signal=global_signal)
                    self.activation_toggle(force=False, save=False)
                    self.page = page

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    PAGE(main=self.main, database=self.parent.database, index=self.page)

            def make_beginning_button(self):
                read_beginning = ReadBTN(self, main=self.main, type='_read_start_btn', page=0)
                t.pos(read_beginning, rightof=self.cover, x_margin=5, height=40, width=set1)
                t.style(read_beginning, background='black', color='gray')
                read_beginning.setLineWidth(2)
                read_beginning.setFrameShape(QtWidgets.QFrame.Box)
                read_beginning.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                return read_beginning

            def make_read_last_previous_page_button(self):
                read_from = ReadBTN(self, main=self.main, type='_read_from_btn', page=current_page)
                t.pos(read_from, coat=read_beginning)
                t.pos(read_beginning, width=read_beginning.width() * 0.5 - 2)
                t.pos(read_from, left=read_beginning.geometry().right() + 2, right=read_from)
                read_beginning.setText('OPEN PAGE 1')
                size = t.correct_broken_font_size(read_beginning, maxsize=36)
                t.style(read_beginning, font=str(size - 2) + 'pt')
                t.style(read_from, background='black', color='gray', font=str(size - 2) + 'pt')

                read_from.setText(f'OPEN PAGE {current_page+1}')
                read_from.setLineWidth(2)
                read_from.setFrameShape(QtWidgets.QFrame.Box)
                read_from.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                return read_from


            read_beginning = make_beginning_button(self)
            current_page = self.database[DB.comics.current_page]

            if current_page and current_page > 1:
                read_from = make_read_last_previous_page_button(self)
                return read_beginning, read_from
            else:
                read_beginning.setText('READ FROM BEGINNING')
                t.correct_broken_font_size(read_beginning, maxsize=36)
                return read_beginning, None




        class FolderSpecial(FolderSettingsWidget):

            #class BUTTON(GLOBALDeactivate, ExecutableLookCheckable):
            class BUTTON(HighlightRadioBoxGroup):
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
                        self.grand_parent.activation_toggle(force=False, save=False)
                        self.grand_parent.rename_delete_widget()
                        self.parent.close()

            class BUTTONRename(BUTTON):

                def button_clicked(self):
                    def some_error(self):
                        self.slaves_can_alter = False
                        self.button.setText('ERROR')
                        t.correct_broken_font_size(self.button)
                        t.style(self.button, background='red', color='black')
                        self.grand_parent.text_changed()

                    self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)

                    if self.database and not os.path.exists(self.database[DB.comics.local_path]):
                        some_error(self)
                        return False

                    text = self.grand_parent.lineedit.text().strip()

                    if os.path.exists(text):
                        some_error(self)
                        return False

                    try: shutil.move(self.database[DB.comics.local_path], text)
                    except:
                        some_error(self)
                        return False

                    if not os.path.exists(text) or os.path.exists(self.database[DB.comics.local_path]):
                        some_error(self)
                        return False

                    sqlite.execute('update comics set local_path = (?) where id is (?)', (text, self.database[0],))
                    self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)
                    self.grand_parent.database = self.database

                    self.button.setText('DONE!')
                    t.correct_broken_font_size(self.button)
                    t.style(self.button, background='green', color='black')
                    self.grand_parent.text_changed()

            class BUTTONDelete(BUTTON):
                def button_clicked(self):
                    def some_error(self):
                        self.slaves_can_alter = False
                        self.button.setText('ERROR')
                        t.correct_broken_font_size(self.button)
                        t.style(self.button, background='red', color='black')
                        self.grand_parent.text_changed()

                    def some_success(self):
                        sqlite.execute('delete from comics where id is (?)', self.database[0])
                        self.button.setText('DONE!')
                        t.correct_broken_font_size(self.button)
                        t.style(self.button, background='green', color='black')

                    self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)

                    if not self.database:
                        some_error(self)
                        return False

                    path = self.database[DB.comics.local_path]

                    if not os.path.exists(path):
                        some_error(self)
                        return False

                    try: os.remove(path)
                    except:
                        some_error(self)
                        return False

                    if os.path.exists(path):
                        some_error(self)
                        return False

                    some_success(self)

            def rename_delete_widget(self, ev=None):
                if 'delete_rename' in dir(self) or ev == None:
                    self.delete_rename.close()
                    del self.delete_rename

                    self.special()
                    return

                def generate_del_rename_init_dictionary(self):
                    d = [
                        dict(text='DELETE FILE',
                             widget=self.BUTTONDelete,
                             post_init=True,
                             button_width_factor=2.5,
                             button_text='', button_color='darkCyan', text_color='gray',

                             kwargs=dict(
                                 type='_info_delete',
                                 global_signal=global_signal,
                                 extravar=dict(
                                     database=self.database,
                                     grand_parent=self,
                                 ))),

                        dict(text='RENAME FILE',
                             widget=self.BUTTONRename,
                             post_init=True,
                             button_width_factor=2.5,
                             button_text='', button_color='darkCyan', text_color='gray',

                             kwargs=dict(
                                 type='_info_rename',
                                 global_signal=global_signal,
                                 extravar=dict(
                                     database=self.database,
                                     grand_parent=self,
                                 ))),
                    ]
                    return d

                t.style(self.button, background='lightGreen')

                set = UniversalSettingsArea(self.parent, extravar=dict(fortifyed=True, database=self.database))

                d = generate_del_rename_init_dictionary(self)
                set.make_this_into_checkable_buttons(d, toolsheight=20, canvaswidth=220)
                t.pos(set, left=ev.x(), above=self.parent.local_path.geometry().top())

                self.delete_rename = set

            def special(self):
                text = self.lineedit.text().strip()

                if text == self.database[DB.comics.local_path]:
                    t.style(self.button, background='green')
                    self.setToolTip('All seems good')

                elif not os.path.exists(text):
                    t.style(self.button, background='orange')
                    self.setToolTip('No conflict, rename?')

                elif os.path.exists(text):
                    t.style(self.button, background='gray')
                    self.setToolTip('Filename conflict')

                else:
                    t.style(self.button, background='red')
                    self.setToolTip('...')

                return True

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.activation_toggle(save=False)
                self.rename_delete_widget(ev)

        def make_local_path_widget(self):

            e = [
                dict(text='LOCAL PATH', widget=FolderSpecial,
                     kwargs=dict(
                         type='_info_local_path',
                         extravar=dict(
                             database=self.database,
                             parent=self,
                         )))
            ]

            set2 = UniversalSettingsArea(self, extravar=dict(fortifyed=True))

            b = set2.make_this_into_folder_settings(e, extend_le_til=set1.geometry().right())
            t.pos(set2, left=self, below=self, y_margin=5)

            le = b.widgets[0]['le']
            le.setText(self.database[DB.comics.local_path])
            t.correct_broken_font_size(le)
            set2.expand_me(set2.blackgrays)

            self.local_path = set2
            return set2

        def make_convert_from_pdf_button(self):
            loc = t.separate_file_from_folder(self.database[DB.comics.local_path])
            if loc.ext.lower() != 'pdf':
                return False

            class ConvertPDF(HighlightRadioBoxGroup, ExecutableLookCheckable):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.activation_toggle(force=False)

                def post_init(self):
                    self.button.setMouseTracking(True)
                    self.textlabel.setMouseTracking(True)

                    self.directives['activation'] = [
                        dict(object=self.textlabel, color='white'),
                        dict(object=self.button, background='cyan', color='black'),
                    ]

                    self.directives['deactivation'] = [
                        dict(object=self.textlabel, color='gray'),
                        dict(object=self.button, background='darkCyan', color='black'),
                    ]

                def special(self):
                    return True

                def conversion_success(self, tmpfile):
                    def generate_cbz_filename(self):
                        """
                        uses the same name as the PDF file but CBZ, if
                        file conflict it will enumerate untill resolves
                        :return: object, string
                        """
                        pdf = t.separate_file_from_folder(self.database[DB.comics.local_path])
                        destination = pdf.folder + pdf.sep + pdf.naked_filename + '.cbz'

                        count = -1
                        while os.path.exists(destination):
                            count += 1
                            destination = pdf.folder + pdf.sep + pdf.naked_filename + '_' + str(count) + '_.cbz'

                        return pdf, destination

                    def update_database(self, destination):
                        """
                        nullifies size and date from database to enforce that
                        they're updated next time it passes threw FileArchiveManager
                        :param destination: new filename.cbz
                        """
                        d = [
                            dict(
                                query='update comics set local_path = (?) where id is (?)',
                                values=(destination, self.database[0],)),
                            dict(
                                query='update comics set file_date = (?) where id is (?)',
                                values=(None, self.database[0],)),
                            dict(
                                query='update comics set file_size = (?) where id is (?)',
                                values=(None, self.database[0],)),
                        ]

                        for i in d:
                            sqlite.execute(query=i['query'], values=i['values'])

                        self.database = sqlite.refresh_db_input('comics', self.database)

                    def verify_file_is_solid(self):
                        """
                        by lending the FileArchiveManager class to generate a "new"
                        database, if we got files we assume everything worked out properly
                        :return: bool
                        """
                        fa = FileArchiveManager(database=self.database, autoinit=False)
                        fa.make_database(path=destination)
                        database = fa.database
                        if database[DB.comics.file_contents]:
                            return True

                    def reverse_database_changes(self, pdf_loc):
                        """
                        if error has occured, the database more
                        or less kind set back to the way it was
                        """
                        update_database(self, destination) # resets size and date
                        query = 'update comics set local_path = (?) where id is (?)'
                        values = pdf_loc.full_path, self.database[0]
                        sqlite.execute(query=query, values=values)

                    pdf, destination = generate_cbz_filename(self)
                    shutil.move(tmpfile, destination)
                    update_database(self, destination=destination)

                    if not verify_file_is_solid(self):
                        reverse_database_changes(self, pdf_loc=pdf)
                        self.pdf_convertion_signal.error.emit({})
                        return False

                    else:
                        if t.config('webp_delete_source_file'):
                            os.remove(pdf.full_path)

                        self.database = sqlite.refresh_db_input('comics', self.database)
                        self.pdf_convertion_signal.finished.emit()

                def setup_signal(self):
                    """
                    :return: puts signal in self and returns the name used
                    """
                    file = self.database[DB.comics.local_path]
                    signalname = '_pdf_convertion_' + file
                    self.pdf_convertion_signal = t.signals(signalname)
                    self.pdf_convertion_signal.file_delivery.connect(self.conversion_success)
                    return signalname

                def button_clicked(self):
                    if self.running_job != False:
                        self.running_job = None
                        return

                    signalname = self.setup_signal()
                    self.start_job(signalgroup=signalname)

                    t.start_thread(concurrent_pdf_to_webp_convertion, name='pdf_or_cbx_to_webp', threads=1,
                        worker_arguments=(
                            self.database[DB.comics.local_path], signalname, self.database[DB.comics.comic_id],))

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    if ev.button() == 1:
                        self.button_clicked()



            d = [
                dict(
                    text='CONVERT PDF TO CBZ (webp)',
                    widget=ConvertPDF,
                    post_init=True,
                    button_width_factor=2.5,
                    button_text='', button_color='darkCyan', text_color='gray',
                    kwargs=dict(
                        type='_convert_pdf_to_cbz',
                        global_signal=global_signal,
                        extravar=dict(
                            database=self.database,


                        ),
                    ))
            ]

            set3 = UniversalSettingsArea(self,
                                         extravar=dict(
                                                 releasing=dict(
                                                     background='gray', color='black'),
                                                 holding=dict(
                                                     background='gray', color='black'),
                                             ))

            set3.make_this_into_checkable_buttons(d, toolsheight=20, linewidth=1)
            return set3

        def make_convert_to_webp_button(self):
            loc = t.separate_file_from_folder(self.database[DB.comics.local_path])
            if loc.ext.lower() not in {'cbz', 'cbr'}:
                return False

            class ConvertToWEBP(HighlightRadioBoxGroup, ExecutableLookCheckable):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.activation_toggle(force=False)

                def post_init(self):
                    self.button.setMouseTracking(True)
                    self.textlabel.setMouseTracking(True)

                    self.directives['activation'] = [
                        dict(object=self.textlabel, color='white'),
                        dict(object=self.button, background='cyan', color='black'),
                    ]

                    self.directives['deactivation'] = [
                        dict(object=self.textlabel, color='gray'),
                        dict(object=self.button, background='darkCyan', color='black'),
                    ]

                def special(self):
                    return True

                def conversion_success(self, tmpfile):

                    def verify_file_is_solid(self, final_destination):
                        """
                        by lending the FileArchiveManager class to generate a "new"
                        database, if we got files we assume everything worked out properly
                        :return: bool
                        """
                        update_database(self, final_destination) # resets database first
                        fa = FileArchiveManager(database=self.database, autoinit=False)
                        fa.make_database(path=final_destination)
                        database = fa.database
                        if database[DB.comics.file_contents]:
                            return True

                    def update_database(self, destination):
                        """
                        nullifies size and date from database to enforce that
                        they're updated next time it passes threw FileArchiveManager
                        :param destination: new filename.cbz
                        """
                        d = [
                            dict(
                                query='update comics set local_path = (?) where id is (?)',
                                values=(destination, self.database[0],)),
                            dict(
                                query='update comics set file_date = (?) where id is (?)',
                                values=(None, self.database[0],)),
                            dict(
                                query='update comics set file_size = (?) where id is (?)',
                                values=(None, self.database[0],)),
                            dict(
                                query='update comics set file_contents = (?) where id is (?)',
                                values=(None, self.database[0],)),
                        ]

                        for i in d:
                            sqlite.execute(query=i['query'], values=i['values'])

                        self.database = sqlite.refresh_db_input('comics', self.database)

                    def generate_cbz_filename(self):
                        cbx = t.separate_file_from_folder(self.database[DB.comics.local_path])
                        destination = cbx.folder + cbx.sep + cbx.naked_filename + '.cbz'

                        count = -1
                        while os.path.exists(destination):
                            count += 1
                            destination = cbx.folder + cbx.sep + cbx.naked_filename + '_' + str(count) + '_.cbz'

                        return destination

                    def both_files_are_cbz(self):
                        original_location = t.separate_file_from_folder(self.database[DB.comics.local_path])

                        if original_location.ext.lower() == 'cbz':
                            backup_org_file = t.tmp_file(new=True)

                            shutil.move(original_location.full_path, backup_org_file) # moves org file to backup location
                            shutil.move(tmpfile, original_location.full_path) # moves new file to org file location

                            if not verify_file_is_solid(self, original_location.full_path):

                                os.remove(original_location.full_path) # deletes "new" file
                                shutil.move(backup_org_file, original_location.full_path) # copies org back to starting location
                                update_database(self, original_location.full_path) # revese previous reset
                                self.webp_convertion_signal.error.emit({})

                                return False

                            os.remove(backup_org_file) # finally, everything seems ok, delete org file
                            return True

                    def both_files_are_different_extensions(self):
                        org_file_path = self.database[DB.comics.local_path]
                        final_destination = generate_cbz_filename(self)
                        shutil.move(tmpfile, final_destination)

                        if not verify_file_is_solid(self, final_destination):
                            update_database(self, org_file_path)  # revese previous reset
                            os.remove(final_destination)  # deletes "new" file
                            self.webp_convertion_signal.error.emit({})

                            return False
                        os.remove(org_file_path)  # finally, everything seems ok, delete org file
                        return True

                    if both_files_are_cbz(self):
                        self.database = sqlite.refresh_db_input('comics', self.database)
                        self.webp_convertion_signal.finished.emit()
                        return True

                    else: # they'll never share the same space
                        if both_files_are_different_extensions(self):
                            self.database = sqlite.refresh_db_input('comics', self.database)
                            self.webp_convertion_signal.finished.emit()
                            return True


                def setup_signal(self):
                    """
                    :return: puts signal in self and returns the name used
                    """
                    file = self.database[DB.comics.local_path]
                    signalname = '_cbx_webp_convertion_' + file
                    self.webp_convertion_signal = t.signals(signalname)
                    self.webp_convertion_signal.file_delivery.connect(self.conversion_success)
                    return signalname

                def webp_convertable_files(self):
                    self.database = sqlite.refresh_db_input('comics', self.database)

                    if not self.database[DB.comics.file_contents]:
                        fa = FileArchiveManager(database=self.database, autoinit=False)
                        fa.make_database(path=self.database[DB.comics.local_path])
                        database = fa.database
                        if not database[DB.comics.file_contents]:
                            return -1
                        else:
                            self.database = database

                    fd = pickle.loads(self.database[DB.comics.file_contents])
                    if 'good_files' not in fd or not fd['good_files']:
                        return -1

                    for i in fd['good_files']:
                        loc = t.separate_file_from_folder(i)
                        if loc.ext.lower() != 'webp':
                            return True

                    return False

                def button_clicked(self):
                    def quick_error(self):
                        signalname = self.setup_signal()
                        self.start_job(signalgroup=signalname)
                        self.job_error(slave_can_alter=False)

                    if self.running_job != False:
                        self.running_job = None
                        return

                    if self.webp_convertable_files() == -1:
                        quick_error(self)
                        return False

                    elif not self.webp_convertable_files():
                        quick_error(self)
                        return False

                    signalname = self.setup_signal()
                    self.start_job(signalgroup=signalname)

                    t.start_thread(concurrent_cbx_to_webp_convertion, name='pdf_or_cbx_to_webp', threads=1,
                        worker_arguments=(
                            self.database[DB.comics.local_path], signalname, self.database[DB.comics.comic_id],))

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    if ev.button() == 1:
                        self.button_clicked()

            d = [
                dict(
                    text='CONVERT CBx TO WEBP (cbz)',
                    widget=ConvertToWEBP,
                    post_init=True,
                    button_width_factor=2.5,
                    button_text='', button_color='darkCyan', text_color='gray',
                    kwargs=dict(
                        type='_convert_cbx_to_webp',
                        global_signal=global_signal,
                        extravar=dict(
                            database=self.database,
                        ),
                    ))
            ]

            set4 = UniversalSettingsArea(self,
                                         extravar=dict(
                                             releasing=dict(
                                                 background='gray', color='black'),
                                             holding=dict(
                                                 background='gray', color='black'),
                                         ))

            set4.make_this_into_checkable_buttons(d, toolsheight=20, linewidth=1)
            return set4


        def expand_now(self, expandlater):
            for i in expandlater:
                if self.width() < i.geometry().right() + 5:
                    t.pos(self, width=i.geometry().right() + 5)

                if self.height() < i.geometry().bottom() + 5:
                    t.pos(self, height=i.geometry().bottom() + 5)

        expandlater = []
        _changedict = dict(_info_comic=1, _info_nsfw=2, _info_magazine=3)
        global_signal = generate_global_signal(self)

        make_cover_and_cover_details(self)
        set1 = make_type_changer(self)
        read_beginning, read_from = make_read_buttons(self) # read_from can be None
        t.pos(set1, below=read_beginning, y_margin=5)

        set2 = make_local_path_widget(self)
        set3 = make_convert_from_pdf_button(self)
        if set3:
            t.pos(set3, below=set1, y_margin=5, left=set1, width=set1)
            expandlater.append(set3)

        set4 = make_convert_to_webp_button(self)
        if set4:
            t.pos(set4, below=set3 or set1, y_margin=5, left=set1, width=set1)
            expandlater.append(set4)

        expandlater.append(set1)
        expandlater.append(set2)

        expand_now(self, expandlater)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self):
            del self.old_position

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self):
            return

        delta = QPoint(event.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = event.globalPos()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(force=True, save=False)
        if ev.button() == 1:
            self.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.quit()

    def quit(self):
        self.close()

