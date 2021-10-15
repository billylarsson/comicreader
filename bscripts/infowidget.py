from bscripts.file_handling import unzipper
from bscripts.compare_images import ImageComparer
from bscripts.cv_guess import GUESSComicVineID
from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint, Qt
from PyQt5.QtGui                  import QKeySequence, QPixmap
from PyQt5.QtWidgets              import QShortcut
from bscripts.comic_drawing       import ComicWidget, Cover, PAGE
from bscripts.comicvine_stuff     import comicvine
from bscripts.database_stuff      import DB, sqlite
from bscripts.file_handling       import FileArchiveManager
from bscripts.file_handling       import check_for_pdf_assistance
from bscripts.file_handling       import concurrent_cbx_to_webp_convertion
from bscripts.file_handling       import concurrent_pdf_to_webp_convertion
from bscripts.file_handling       import extract_from_zip_or_pdf
from bscripts.file_handling       import get_thumbnail_from_zip_or_database
from bscripts.tricks              import tech as t
from functools                    import partial
from script_pack.preset_colors    import *
from script_pack.settings_widgets import ExecutableLookCheckable
from script_pack.settings_widgets import FolderSettingsAndGLobalHighlight
from script_pack.settings_widgets import GLOBALDeactivate, GOD
from script_pack.settings_widgets import HighlightRadioBoxGroup
from script_pack.settings_widgets import UniversalSettingsArea
import copy
import os
import pickle
import shutil

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
        self.parent.position_relatives()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.parent.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.parent.quit()

class INFOWidget(ComicWidget):
    def __init__(self, place, parent, main, type, database, scan50=False):
        super().__init__(place=place, main=main, type=type)

        self.parent = parent
        self.database = database
        self.relatives = []
        self.scan50 = scan50

        if scan50:
            self.signal = t.signals('infowidget_signal_' + str(self.database[0]), reset=False)
            self.hide()
        else:
            self.signal = t.signals('infowidget_signal_' + str(self.database[0]), reset=True)

        self.setFrameStyle(QtWidgets.QFrame.Box|QtWidgets.QFrame.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(2)
        t.style(self, tooltip=True, border='black', color='black', background='white')

        self.activation_toggle(force=True, save=False)
        esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc.activated.connect(self.quit)

        self.signal.buildrelative.connect(self.create_relative)
        self.signal.pickrelatives.connect(self.pick_relatives)
        self.signal.volumelabel.connect(self.init_volumes_label)

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

    def re_init(self, new_database):
        self.database = new_database

        self.close_and_pop_list('box_been_set')
        self.close_and_pop_list('small_info_widgets')
        self.close_and_pop_list('relatives')
        self.close_and_pop_list('volumeslabel')

        for i in ['cover', 'read_beginning']:
            if i in dir(self):
                container = getattr(self, i)
                container.close()
                delattr(self, i)

        self.post_init()

    def close_and_pop_list(self, variable):
        if variable in dir(self) and getattr(self, variable):
            container = getattr(self, variable)
            if type(container) == list:
                t.close_and_pop(container)
            else:
                container.close()
                delattr(self, variable)

    def post_init(self):

        def generate_global_signal(self):
            global_signal = '_global_on_off_' + str(self.database[0])
            return global_signal

        def make_cover_and_cover_details(self):
            cover_height = t.config('cover_height') * 2
            cover = extract_from_zip_or_pdf(database=self.database)
            self.make_cover(cover_height=cover_height, coverfile=cover)
            self.cover.first_reize(cover_height=cover_height)
            t.pos(self.cover, move=[5, 5])
            self.make_box_of_details(enhancefactor=3, force=True)
            t.pos(self.size_pages_label, move=[1, 0], width=self.size_pages_label, sub=-2)

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
                    dict(text='MAGAZINE', widget=ChangeType, post_init=True,
                         kwargs=dict(
                             type='_info_magazine',
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
            t.pos(set1, after=self.cover, x_margin=5)

            return set1

        def make_read_buttons(self):
            class ReadBTN(GLOBALDeactivate):
                def __init__(self, place, main, type, page=0):
                    super().__init__(place=place, main=main, type=type, global_signal=global_signal)
                    self.activation_toggle(force=False, save=False)
                    self.page = page

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    page = PAGE(main=self.main, database=self.parent.database, index=self.page)
                    self.main.pages_container.append(page)

            def make_beginning_button(self):
                read_beginning = ReadBTN(self, main=self.main, type='_read_start_btn', page=0)
                t.pos(read_beginning, after=self.cover, x_margin=5, height=40, width=set1)
                t.style(read_beginning, background='black', color='gray')
                read_beginning.setLineWidth(2)
                read_beginning.setFrameShape(QtWidgets.QFrame.Box)
                read_beginning.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                return read_beginning

            def make_read_last_previous_page_button(self):
                read_from = ReadBTN(self, main=self.main, type='_read_from_btn', page=current_page)
                t.pos(read_from, coat=read_beginning)
                t.pos(read_beginning, width=read_beginning.width() * 0.5 - 2)
                t.pos(read_from, left=dict(right=read_beginning), right=read_from.geometry().right(), x_margin=2)
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

            if current_page and current_page > 1 and True == False: # ignoring this mode but keeping code
                read_from = make_read_last_previous_page_button(self)
                return read_beginning, read_from
            else:
                read_beginning.setText('READ FROM BEGINNING')
                t.correct_broken_font_size(read_beginning, maxsize=36)
                return read_beginning, None

        def make_local_path_widget(self):
            class LocalPathLE(FolderSettingsAndGLobalHighlight):
                def post_init(self):
                    t.pos(self.lineedit, left=self.button, right=self.lineedit.geometry().right())

                    for i in [self.button, self._bframe, self.textlabel]:
                        i.hide()

                    self.dir_pixel = []
                    self.lineedit.textChanged.connect(self.text_changed)

                    self.create_small_folder_pixles(path=self.database[DB.comics.local_path])
                    loc = t.separate_file_from_folder(self.database[DB.comics.local_path])
                    self.lineedit.setText(loc.full_path)

                    if os.path.exists(self.database[DB.comics.local_path]):
                        self.activation_toggle(force=True, save=False)

                    else:
                        self.activation_toggle(force=False, save=False)

                class DELBTN(HighlightRadioBoxGroup):
                    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                        if ev.button() == 1:
                            if os.path.exists(self.database[DB.comics.local_path]):
                                os.remove(self.database[DB.comics.local_path])

                            sqlite.execute('delete from comics where id is (?)', self.database[0])
                            self.parent.parent.quit()

                class CANCELBTN(HighlightRadioBoxGroup):
                    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                        if ev.button() == 1:
                            self.parent.confirm_delete.close()
                            self.parent.cancel_delete.close()
                            del self.parent.confirm_delete
                            del self.parent.cancel_delete

                def delete_button_mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    if 'cancel_delete' in dir(self):
                        return

                    def make_confirm_button(self):
                        self.confirm_delete = self.DELBTN(self.lineedit, type='_confdel', global_signal=global_signal)
                        self.confirm_delete.parent = self.parent
                        self.confirm_delete.database = self.database
                        t.style(self.confirm_delete, background=TXT_DARKTRANS, color='darkGray')

                        self.confirm_delete.directives['activation'] = [
                            dict(object=self.confirm_delete, background='rgb(200,50,50)', color='white')
                        ]
                        self.confirm_delete.directives['deactivation'] = [
                            dict(object=self.confirm_delete, background=TXT_DARKTRANS, color='darkGray')
                        ]

                        self.confirm_delete = t.pos(
                            self.confirm_delete, inside=self.lineedit, width=self.lineedit.width() * 0.5)

                        self.confirm_delete.setText('DELETE THIS FILE FROM YOUR COMPUTER')
                        self.confirm_delete.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
                        t.correct_broken_font_size(self.confirm_delete)

                    def make_cancel_button(self):

                        self.cancel_delete = self.CANCELBTN(self.lineedit, type='_confren', global_signal=global_signal)
                        t.style(self.cancel_delete, background=TXT_DARKTRANS, color='darkGray')

                        self.cancel_delete.directives['activation'] = [
                            dict(object=self.cancel_delete, background='lightBlue', color='black')
                        ]
                        self.cancel_delete.directives['deactivation'] = [
                            dict(object=self.cancel_delete, background=TXT_DARKTRANS, color='darkGray')
                        ]

                        self.cancel_delete = t.pos(self.cancel_delete, inside=self.lineedit)
                        self.cancel_delete = t.pos(
                            self.cancel_delete, left=dict(right=self.confirm_delete), width=self.confirm_delete)

                        self.cancel_delete.setText("I'VE CHANGED MY MIND!")
                        self.cancel_delete.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
                        self.cancel_delete.parent = self
                        t.correct_broken_font_size(self.cancel_delete)

                    make_confirm_button(self)
                    make_cancel_button(self)

                def save_button_mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:

                    def some_error(self):
                        self.save_button.slaves_can_alter = False
                        t.style(self.save_button, background='red', color='black')
                        self.save_button.setText('ERROR')

                    self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)


                    if self.database and not os.path.exists(self.database[DB.comics.local_path]):
                        some_error(self)
                        return

                    text = self.lineedit.text().strip()

                    if os.path.exists(text):
                        some_error(self)
                        return

                    try: shutil.move(self.database[DB.comics.local_path], text)
                    except:
                        some_error(self)
                        return

                    if not os.path.exists(text) or os.path.exists(self.database[DB.comics.local_path]):
                        some_error(self)
                        return

                    sqlite.execute('update comics set local_path = (?) where id is (?)', (text, self.database[0],))
                    self.database = sqlite.refresh_db_input(table='comics', db_input=self.database)
                    self.text_changed()

                def text_changed(self):
                    text = self.lineedit.text().strip()
                    local_path = self.database[DB.comics.local_path]

                    if self.text_path_exists() and text == local_path:
                        t.style(self.lineedit, background='black', color='white')
                        self.manage_save_button(delete=True)
                        self.manage_delete_button(create=True, text="")
                        self.delete_button.mousePressEvent = self.delete_button_mousePressEvent
                        self.delete_button.setToolTip('PERMANENTLY DELETE FILE')

                    elif not self.text_path_exists() and text != local_path:

                        if 'save_button' in dir(self) and not self.save_button.slaves_can_alter:
                            self.manage_save_button(delete=True)

                        self.manage_save_button(create=True, text='RENAME')
                        self.save_button.mousePressEvent = self.save_button_mousePressEvent
                        t.style(self.lineedit, background='black', color='gray')

                    else:
                        self.manage_save_button(delete=True)
                        t.style(self.lineedit, background='black', color='gray')

            set2 = UniversalSettingsArea(self, extravar=dict(fortifyed=True))
            e = [
                dict(text='LOCAL PATH',
                     widget=LocalPathLE,
                     kwargs=dict(
                         type='_info_local_path',
                         global_signal=global_signal,
                         multiple_folders=False,
                         extravar=dict(
                             database=self.database,
                             parent=set2,
                         )))
            ]

            b = set2.make_this_into_folder_settings(e, extend_le_til=set1.geometry().right())

            x_margin = -self.size_pages_label.lineWidth()
            t.pos(set2,
                  left=self.size_pages_label, x_margin=x_margin, top=dict(bottom=self.size_pages_label), y_margin=5)

            le = b.widgets[0]['le']
            le.setText(self.database[DB.comics.local_path])
            t.correct_broken_font_size(le)
            set2.expand_me(set2.blackgrays)

            self.local_path_widget = e[0]['label']
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
                        dict(object=self.textlabel, color=TXT_SHINE),
                    ]

                    self.directives['deactivation'] = [
                        dict(object=self.textlabel, color=TXT_SHADE),
                    ]
                    t.pos(self.textlabel, inside=self)

                def mute_label(self):
                    self.textlabel.setText("ALL FILES ARE WEBP")
                    self.button_clicked = lambda: 1 + 1

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
                        self.mute_label()
                        self.local_path_widget.database = self.database
                        self.local_path_widget.lineedit.setText(self.database[DB.comics.local_path])

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

                    t.pos(self.textlabel, left=dict(right=self.button), right=self, x_margin=self.lineWidth())
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
                    alignment=True,
                    hide_button=True,
                    button_width_factor=2.5,
                    button_text='', button_color='darkCyan', text_color='gray',
                    kwargs=dict(
                        type='_convert_pdf_to_cbz',
                        global_signal=global_signal,
                        extravar=dict(
                            database=self.database,
                            local_path_widget=self.local_path_widget,
                            parent=self,
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
                        dict(object=self.textlabel, color=TXT_SHINE),
                    ]

                    self.directives['deactivation'] = [
                        dict(object=self.textlabel, color=TXT_SHADE),
                    ]
                    if not self.mute_label_refresh_local_path():
                        t.pos(self.textlabel, inside=self)

                def mute_label_refresh_local_path(self):
                    if not self.webp_convertable_files():
                        self.textlabel.setText("ALL FILES ARE WEBP")
                        self.button_clicked = lambda: 1+1
                        self.local_path_widget.database = self.database
                        self.local_path_widget.lineedit.setText(self.database[DB.comics.local_path])
                        return True

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
                        self.mute_label_refresh_local_path()
                        return True

                    else: # they'll never share the same space
                        if both_files_are_different_extensions(self):
                            self.database = sqlite.refresh_db_input('comics', self.database)
                            self.webp_convertion_signal.finished.emit()
                            self.mute_label_refresh_local_path()
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

                    t.pos(self.textlabel, left=dict(right=self.button), right=self, x_margin=self.lineWidth())
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
                    alignment=True,
                    hide_button=True,
                    button_width_factor=2.5,
                    button_text='', button_color='darkCyan', text_color='gray',
                    kwargs=dict(
                        type='_convert_cbx_to_webp',
                        global_signal=global_signal,
                        extravar=dict(
                            database=self.database,
                            local_path_widget=self.local_path_widget,
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

        def make_small_page_squares(self, canvas, start_from=0):
            """
            creates small clickable squares for each page
            in the comic but batching them in sets of 50
            :param canvas: UniversalSettingsArea()
            :param start_from: int
            """
            for count in range(len(canvas.squares)-1,-1,-1):
                canvas.squares[count].close()
                canvas.squares.pop(count)

            self.database = sqlite.refresh_db_input('comics', self.database)
            good_files = FileArchiveManager.get_filecontents(database=self.database)
            if good_files:
                pagecount = len(good_files)
            else:
                loc = t.separate_file_from_folder(self.database[DB.comics.local_path])
                pagecount = check_for_pdf_assistance(pdf_file=loc.full_path, pagecount=True)

            if not pagecount:
                return False

            if start_from < 0:
                start_from = 0
            elif start_from >= pagecount:
                start_from = pagecount

            class PageSquare(GLOBALDeactivate):
                def __init__(self, place, count, database, *args, **kwargs):
                    super().__init__(place=place, *args, **kwargs)
                    self.pagecount = count
                    self.database = database
                    self.setLineWidth(1)
                    self.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                    self.setFrameShape(QtWidgets.QFrame.Box)
                    self.setText(str(self.pagecount + 1))
                    self.default_event_colors()
                    self.signal_global_gui_change(directive='deactivation')

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    """
                    left-clicking opens the pagenumber
                    when right-clicking the first square if its not the first in
                    the issue, will drawing from that page - 50 pages
                    (if negative its set to 0) same goes for the last square + 50.
                    """
                    if ev.button() == 1:
                        page = PAGE(main=self.main, database=self.database, index=self.pagecount)
                        self.main.pages_container.append(page)

                    elif ev.button() == 2:
                        if self == self.parent.squares[0] and self.pagecount != 0:
                            self.make_small_page_squares(
                                self=self.infowidget, canvas=self.canvas, start_from=self.pagecount-50)

                        elif self == self.parent.squares[-1] and self.pagecount+1 != self.total_pagecount:
                            self.make_small_page_squares(
                                self=self.infowidget, canvas=self.canvas, start_from=self.pagecount+1)

                def init_refresh_signal(self):
                    """
                    only given to the first of all squares acting as a master
                    for the entire group, when turning page refresing all
                    small squares starting from previous starting point.
                    """
                    signal = t.signals(name='_refresh_page_squares' + str(self.database[0]), reset=True)
                    signal.finished.connect(self.refresh_all_page_squares)
                    signal = t.signals(name='_lit_my_square' + str(self.database[0]), reset=True)
                    signal.pagenumbers.connect(self.lit_my_square)

                def lit_my_square(self, openpages):
                    """
                    iter self.canvas.squares and if pagecount in openpages
                    :param openpages: tuple (3,-1) -1 not used
                    """
                    for pagenum in openpages:
                        for i in self.canvas.squares:
                            if pagenum == i.pagecount:
                                t.style(i, background='yellow')

                def refresh_all_page_squares(self):
                    """fn:self.init_refresh_signal"""
                    self.make_small_page_squares(
                        self=self.infowidget, canvas=self.canvas, start_from=self.pagecount)

            class Unread(PageSquare):
                def default_event_colors(self):
                    self.setToolTip("seems like you have'nt viewed this page yet")

                    self.directives['activation'] = [
                        dict(object=self, background=UNREAD_B_1, color=UNREAD_C_1)]
                    self.directives['deactivation'] = [
                        dict(object=self, background=UNREAD_B_0, color=UNREAD_C_0)]

            class Bookmarked(PageSquare):
                def default_event_colors(self):
                    self.setToolTip("BOOKMARK HERE!")

                    self.directives['activation'] = [
                        dict(object=self, background=BOOKMARKED_B_1, color=BOOKMARKED_C_1)]
                    self.directives['deactivation'] = [
                        dict(object=self, background=BOOKMARKED_B_0, color=BOOKMARKED_C_0)]

            class Current(PageSquare):
                def default_event_colors(self):
                    self.setToolTip("this is the highest pagenumber you've opened so far")

                    self.directives['activation'] = [
                        dict(object=self, background=CURRENT_B_1, color=CURRENT_C_1)]
                    self.directives['deactivation'] = [
                        dict(object=self, background=CURRENT_B_0, color=CURRENT_C_0)]

            class Read(PageSquare):
                def default_event_colors(self):
                    self.setToolTip("based on the highest number of opened pages, we assume you've read preceeding pages")

                    self.directives['activation'] = [
                        dict(object=self, background=READ_B_1, color=READ_C_1)]
                    self.directives['deactivation'] = [
                        dict(object=self, background=READ_B_0, color=READ_C_0)]

            eachwidth = set1.width() / 10
            current = self.database[DB.comics.current_page] or 0

            if self.database[DB.comics.bookmarks]:
                bookmarks = pickle.loads(self.database[DB.comics.bookmarks])
            else:
                bookmarks = {}

            check = 10
            for count in range(start_from, start_from+50):

                if count >= pagecount:
                    break

                elif count in bookmarks:
                    squareclass = Bookmarked

                elif count == current:
                    squareclass = Current

                elif count < current:
                    squareclass = Read

                else:
                    squareclass = Unread

                square = squareclass(canvas,
                                     type='_page_square' + str(count),
                                     count=count,
                                     main=self.parent.main,
                                     database=self.database,
                                     extravar=dict(
                                         make_small_page_squares=make_small_page_squares,
                                         canvas=canvas,
                                         infowidget=self,
                                         total_pagecount=pagecount,
                                     ),
                                     )

                if not canvas.squares:
                    t.pos(square, size=[eachwidth-2,eachwidth-2], top=0, left=0)
                    square.init_refresh_signal()
                else:
                    if len(canvas.squares) == check:
                        check += 10
                        t.pos(square, coat=canvas.squares[0], below=canvas.squares[-1], left=0, y_margin=2)
                    else:
                        t.pos(square, coat=canvas.squares[0], after=canvas.squares[-1], x_margin=2)

                t.correct_broken_font_size(square)
                canvas.squares.append(square)

            return True

        def make_clean_database_button(self):
            class ClearDatabase(HighlightRadioBoxGroup, ExecutableLookCheckable):
                """
                NULL to all DB.comics.* except for id, type and local_path
                """
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.activation_toggle(force=False)

                def post_init(self):
                    self.button.setMouseTracking(True)
                    self.textlabel.setMouseTracking(True)

                    self.directives['activation'] = [
                        dict(object=self.textlabel, color=TXT_SHINE),
                    ]

                    self.directives['deactivation'] = [
                        dict(object=self.textlabel, color=TXT_SHADE),
                    ]

                def button_clicked(self):
                    data = list(self.database)
                    for count in range(1, len(data)):

                        if count == DB.comics.local_path or count == DB.comics.type:
                            continue

                        data[count] = None

                    query, _ = sqlite.empty_insert_query('comics')
                    sqlite.execute(query='delete from comics where id is (?)', values=data[0])
                    sqlite.execute(query=query, values=tuple(data))
                    self.re_init(self.database)

                def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                    if ev.button() == 1:
                        self.button_clicked()

            set6 = UniversalSettingsArea(self)
            clean = [
                dict(
                    text='RESET THIS ISSUE',
                    tooltip="erases rating, what page you're currently on, bookmarks, etc, etc...(soft changes only, file left untouched)",
                    widget=ClearDatabase,
                    hide_button=True,
                    alignment=True,
                    post_init=True,
                    kwargs=dict(
                        type='_clear_database',
                        global_signal=global_signal,
                        extravar=dict(
                            database=self.database,
                            re_init=self.re_init,
                        )
                    )
                )
            ]

            set6.make_this_into_checkable_buttons(clean, toolsheight=20, linewidth=1)

            return set6

        def make_small_page_squares_canvas(self):
            set5 = t.pos(new=self)
            set5.squares = []

            if not make_small_page_squares(self, canvas=set5, start_from=0):
                set5.close()
                return False

            expand_now(set5, set5.squares)
            return set5

        def expand_now(self, expandlater):
            for i in expandlater:
                if self.width() < i.geometry().right() + 5:
                    t.pos(self, width=i.geometry().right() + 5)

                if self.height() < i.geometry().bottom() + 5:
                    t.pos(self, height=i.geometry().bottom() + 5)

        def make_pairing_button(self):
            class PAIRButton(FolderSettingsAndGLobalHighlight):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)

                def post_init(self):
                    self.lineedit.setValidator(QtGui.QIntValidator(0,2147483647))
                    t.style(self.lineedit, font='14pt')
                    self.lineedit.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
                    self.lineedit.textChanged.connect(self.text_changed)
                    if self.database[DB.comics.comic_id]:
                        self.create_deletebutton()
                        self.lineedit.setText(str(self.database[DB.comics.comic_id] or ""))
                    else:
                        self.textlabel.setText('NO CVID')
                        t.correct_broken_font_size(self.textlabel)

                def delete_button_mousePressEvent(self, *args, **kwargs):
                    for i in ['comic_id', 'volume_id', 'publisher_id']:
                        query = f'update comics set {i} = (?) where id is (?)'
                        sqlite.execute(query=query, values=(None, self.database[0],))

                    self.database = sqlite.refresh_db_input('comics', self.database)
                    self.manage_delete_button(delete=True)
                    self.manage_save_button(create=True)
                    self.save_button.setToolTip(
                        'right clicking will avoid re-initing neighbours (faster exerience while less exerience)')
                    self.save_button.mousePressEvent = self.save_button_mousePressEvent

                def save_button_mousePressEvent(self, *args, **kwargs):
                    text = self.lineedit.text()
                    if text:
                        sqlite.execute('update comics set comic_id = (?) where id is (?)', (text, self.database[0],))
                        self.manage_save_button(delete=True)
                        self.textlabel.setText('PAIRED')
                        t.correct_broken_font_size(self.textlabel)
                        self.database = sqlite.refresh_db_input('comics', self.database)
                        self.manage_save_button(delete=True)
                        if args and args[0].button() == 2: # hack that doesnt re_init
                            return
                        else:
                            self.re_init(self.database)

                def create_deletebutton(self):
                    self.manage_delete_button(create=True, text="", tooltip='Clear comicvine ID')
                    self.delete_button.mousePressEvent = self.delete_button_mousePressEvent

                def text_changed(self):
                    text = self.lineedit.text()
                    if text and int(text) != self.database[DB.comics.comic_id]:
                        self.manage_save_button(create=True)
                        self.save_button.mousePressEvent = self.save_button_mousePressEvent
                    else:
                        self.manage_save_button(delete=True)

            def use_deletebutton_to_signal_when_cv_done(self, d):
                if 'delete_button' in dir(d[0]['label']):
                    def signal_jobs_done():
                        t.style(self.pair_delete_button, background=DARKRED)

                    self.pair_delete_button = d[0]['label'].delete_button
                    t.style(self.pair_delete_button, background='red')
                    # cvsignal = t.signals('cv_jobs_done' + str(self.database[0]), reset=True)
                    # cvsignal.finished.connect(lambda: t.style(delete_button, background=DARKRED))
                    self.signal.pair_deletebutton_jobs_done.connect(signal_jobs_done)

            set7 = UniversalSettingsArea(self,extravar=dict(fortifyed=True))
            t.pos(set7, height=36, above=set6, y_margin=3)

            d = [
                dict(
                    text='PAIRED',
                    hide_button=True,
                    alignment=True,
                    widget=PAIRButton,
                    post_init=True,
                    kwargs=dict(
                        type='_pair_button',
                        extravar=dict(
                            database=self.database,
                            re_init=self.re_init,
                    )))
            ]
            set7.make_this_into_folder_settings(d, toolsheight=30, extend_le_til=set6, labelwidth=80)
            set7.expand_me(set7.blackgrays)
            use_deletebutton_to_signal_when_cv_done(self, d)
            self.pair_button = set7
            self.pair_lineedit = d[0]['label'].lineedit
            self.pair_textlabel = d[0]['label'].textlabel
            self.pair_label = d[0]['label']
            return set7

        expandlater = []
        _changedict = dict(_info_comic=1, _info_nsfw=2, _info_magazine=3)
        global_signal = generate_global_signal(self)

        make_cover_and_cover_details(self)
        set1 = make_type_changer(self)
        self.read_beginning, read_from = make_read_buttons(self) # read_from can be None
        t.pos(set1, below=self.read_beginning, y_margin=5)

        set2 = make_local_path_widget(self)
        set3 = make_convert_from_pdf_button(self)
        if set3:
            t.pos(set3, below=set1, y_margin=5, left=set1, width=set1)
            expandlater.append(set3)

        set4 = make_convert_to_webp_button(self)
        if set4:
            t.pos(set4, below=set3 or set1, y_margin=5, left=set1, width=set1)
            expandlater.append(set4)

        set5 = make_small_page_squares_canvas(self)
        if set5:
            t.pos(set5, below=set4 or set3 or set1, y_margin=5)
            expandlater.append(set5)

        set6 = make_clean_database_button(self)
        t.pos(set6, width=set1, left=set1, bottom=dict(top=set2), y_margin=5)

        set7 = make_pairing_button(self)

        expandlater.append(set1)
        expandlater.append(set2)
        expandlater.append(set6)
        expandlater.append(set7)

        expand_now(self, expandlater)
        self.small_info_widgets = expandlater

        t.start_thread(self.update_comicvine, name='comicvine', threads=1)
        self.suggest_comic_id()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self):
            del self.old_position

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self):
            return

        delta = QPoint(event.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = event.globalPos()

        self.position_relatives()

    def position_relatives(self):
        for count, i in enumerate(self.relatives):
            if count == 0:
                t.pos(i, before=self, x_margin=3, top=self)
            else:
                t.pos(i, below=self.relatives[count-1], y_margin=3, right=self.relatives[count-1])

        if 'volumeslabel' in dir(self):
            if len(self.volumeslabel.volwidgets) >= 20:
                t.pos(self.volumeslabel, top=dict(bottom=self), y_margin=3, center=[self, self])
            else:
                t.pos(self.volumeslabel, top=dict(bottom=self), y_margin=3, left=self)

        if 'draw_volumes_button' in dir(self) and self.relatives:
            t.pos(self.draw_volumes_button,
                  width=self.relatives[0],
                  height=20,
                  above=self.relatives[0],
                  y_margin=3,
                  sub=2
                  )

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(force=True, save=False)

        if ev.button() == 1:
            self.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.quit()

    def refresh_volume_id(self, database):
        if database[DB.comics.comic_id] and not database[DB.comics.volume_id]:

            query = 'select * from issue_volume_publisher where comic_id = (?)'
            data = sqlite.execute(query, database[DB.comics.comic_id])

            if data:
                query = 'update comics set volume_id = (?) where comic_id = (?)'
                values = data[DB.issue_volume_publisher.volume_id], database[DB.comics.comic_id]
                sqlite.execute(query, values=values)

                query = 'update comics set publisher_id = (?) where comic_id = (?)'
                values = data[DB.issue_volume_publisher.publisher_id], database[DB.comics.comic_id]
                sqlite.execute(query, values=values)

            else:
                rv = comicvine(issue=database, update=True)
                return rv

    def generate_candidates_list(self, sorted_volume):
        candidates = []

        for count, i in enumerate(sorted_volume):
            candidates.append(dict(database=i, used=False, count=count, center=False))

        return candidates

    def create_center_candidate_data(self, candidates):
        if [x for x in candidates if x['center'] and x['used']]:
            return

        for dictionary in candidates:
            if dictionary['database'][0] == self.database[0]:
                dictionary['center'] = True
                dictionary['used'] = True

                height = t.config('cover_height') or 300
                thumb = get_thumbnail_from_zip_or_database(database=self.database, height=height)

                return dict(
                    database=self.database, image_path=thumb, center=True, count=dictionary['count'])

    def pick_relatives(self, candidates, maxrelatives=5):
        def usable_and_greater_or_shorter_candidate(self, candidates, candidate, greater=False, shorter=False):

            def find_center_candidate(candidates):
                for i in candidates:
                    if i['center']:
                        return i['count']

            def find_an_unupdated_local_comic_id(self, candidate):
                local_check_query = 'select * from comics where comic_id = (?)'
                data = sqlite.execute(local_check_query, candidate['database'][DB.comics.comic_id])

                if data:
                    self.refresh_volume_id(data)
                    candidate['database'] = data

            if candidate['used']:
                return False

            center_count = find_center_candidate(candidates)

            if greater:
                if candidate['count'] < center_count:
                    return False

            elif shorter:
                if candidate['count'] > center_count:
                    return False

            find_an_unupdated_local_comic_id(self, candidate)

            thumb = None
            rv = None

            if candidate['database'][0]:
                height = t.config('cover_height') or 300
                thumb = get_thumbnail_from_zip_or_database(database=candidate['database'], height=height, proxy=False)
            else:
                rv = comicvine(issue=candidate['database'])
                if rv:
                    thumb = t.download_file(url=rv['image']['small_url'])
                if not thumb:
                    thumb = t.config('download_error', image=True)

            if not thumb:
                return False

            candidate['used'] = True

            self.signal.buildrelative.emit(dict(
                database=candidate['database'], image_path=thumb, center=False, count=candidate['count'], cv=rv))
            return True

        while len([x for x in candidates if x['used']]) < maxrelatives:

            if not [x for x in candidates if not x['used']]:
                break

            if len([x for x in candidates if x['used']]) < maxrelatives:
                for count in range(len(candidates)):

                    if usable_and_greater_or_shorter_candidate(self, candidates, candidates[count], greater=True):
                        break

            if len([x for x in candidates if x['used']]) < maxrelatives:
                for count in range(len(candidates) - 1, -1, -1):

                    if usable_and_greater_or_shorter_candidate(self, candidates, candidates[count], shorter=True):
                        break

    def init_relatives(self, candidates):
        if len(candidates) < 2:
            return

        rv = self.create_center_candidate_data(candidates)
        if rv:
            self.signal.buildrelative.emit(rv)
            self.signal.pickrelatives.emit(candidates)

    def genereate_volume_sorted_by_issuenumbers(self):
        def delete_duplicants(data):
            """
            rules out multiple comic_id
            :param data: list
            """
            comic_ids = []
            for count in range(len(data) - 1, -1, -1):
                if data[count][DB.comics.comic_id] in comic_ids:
                    data.pop(count)
                else:
                    comic_ids.append(data[count][DB.comics.comic_id])

        def update_issuenumbers(cvdata, localdata):
            """
            if somehow an issue is missing issuenumber we fix that while
            we're here if we cannot the issue will be popped from list
            :param cvdata: comicvine data
            :param localdata: list
            """
            if cvdata and cvdata['issues']:
                for count in range(len(localdata)-1,-1,-1):

                    if localdata[count][DB.comics.issue_number]:
                        continue

                    if cvdata and cvdata['issues']:
                        for i in cvdata['issues']:

                            if i['id'] != localdata[count][DB.comics.comic_id]:
                                continue

                            if i['issue_number']:
                                query = 'update comics set issue_number = (?) where id = (?)'
                                sqlite.execute(query=query, values=(i['issue_number'], localdata[count][0],))

                                query = 'select * from comics where id is (?)'
                                localdata[count] = sqlite.execute(query=query, values=localdata[count][0])

                    if not localdata[count][DB.comics.issue_number]:
                        localdata.pop(count)

        sorted_volume = []
        volume_id = self.database[DB.comics.volume_id]
        publisher_id = self.database[DB.comics.publisher_id]

        cv_vols = comicvine(volume=volume_id, update=True)

        if cv_vols and cv_vols['issues']:
            query = 'select * from comics where volume_id = (?)'
            data = sqlite.execute(query=query, values=volume_id, all=True)
            delete_duplicants(data)
            update_issuenumbers(cvdata=cv_vols, localdata=data)

            _, org_values = sqlite.empty_insert_query('comics')
            comic_ids = [x[DB.comics.comic_id] for x in data]

            for i in cv_vols['issues']:

                if not i['issue_number']:
                    continue

                if i['id'] in comic_ids:
                    continue

                comic_ids.append(i['id'])
                values = copy.copy(org_values)

                values[DB.comics.comic_id] = i['id']
                values[DB.comics.issue_number] = i['issue_number']
                values[DB.comics.publisher_id] = publisher_id
                values[DB.comics.volume_id] = volume_id
                data.append(tuple(values))

            sorted_volume = t.sort_by_number(data, DB.comics.issue_number)

        return sorted_volume

    def create_relative(self, instructions):

        class RelativeWidget(GOD):
            def __init__(self, place, database, image_path, center, parent, count, cv=None, *args, **kwargs):
                super().__init__(place=place, *args, **kwargs)
                self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
                self.setLineWidth(1)
                self.setMidLineWidth(2)
                self.database = database
                self.parent = parent
                self.image_path = image_path
                self.center = center
                self.count = count
                self.comicvine_load = cv # if comicvine

                margin = self.lineWidth() + self.midLineWidth() + 1
                height = int(self.parent.height() * 0.2 - margin * 3)

                pixmap = QPixmap(self.image_path).scaledToHeight(height + 2, QtCore.Qt.SmoothTransformation)

                if pixmap.width() > height*3:
                    pixmap = QPixmap(self.image_path).scaled(height + 2, height * 3)

                t.pos(self, width=pixmap, height=pixmap, add=margin * 2)
                self.cover = t.pos(new=self, size=pixmap)
                self.cover.setPixmap(pixmap)
                t.pos(self.cover, inside=self, margin=margin)

                if not self.center or self.center and not database[0]:
                    self.shade = t.pos(new=self, inside=self)
                    t.style(self.shade, background='rgba(10,10,10,120)')

                if not database[0]:
                    h = self.cover.height() * 0.07
                    self.proxy = t.pos(new=self.shade, coat=self.cover, height=h, background='black')
                    t.pos(self.proxy, bottom=self.cover, y_margin=(self.cover.height() * 0.05))
                    self.proxy_label = t.pos(new=self.proxy, inside=self.proxy, margin=1, background='gray')
                    t.pos(self.proxy_label, width=self.proxy_label, add=2, move=[-1,0])
                    t.style(self.proxy_label, color='black')
                    self.proxy_label.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
                    self.proxy_label.setText('PROXY')
                    t.correct_broken_font_size(self.proxy_label)
                    self.setToolTip('DOWNLOADED COVER FROM COMICVINE, COULDNT FIND ISSUE AMONG YOUR FILES')

                    self.parent.signal.db_input.connect(self.found_local_candidate)

                    data = sqlite.execute('select * from comics where comic_id is null', all=True)
                    data = [x for x in data if x[DB.comics.type] == 1] # make real list if bug with sqlite thread
                    t.start_thread(self.find_local_candidate, worker_arguments=data)

                self.show()

            def found_local_candidate(self, total_and_db_input):
                """
                :param total_and_db_input:
                        is a tuple were index[0] is total percentage compare from
                        GUESSComicVineID and index[1] is real local sqlite_db_input
                """
                string = 'PROPOSING UPAIRED LOCAL FILE FOR Comicvine ID: ' + str(self.database[DB.comics.comic_id])
                self.setToolTip(string)
                t.style(self.shade, background='transparent')

                threshold = t.config('comicvine_autopair_threshold')
                if threshold != False and total_and_db_input[0] * 100 >= threshold:

                    query1 = 'update comics set comic_id = (?) where id is (?)'
                    query2 = 'update comics set volume_id = (?) where id is (?)'
                    query3 = 'update comics set publisher_id = (?) where id is (?)'
                    sqlite.execute(query1, values=(self.database[DB.comics.comic_id], total_and_db_input[1][0]),)
                    sqlite.execute(query2, values=(self.database[DB.comics.volume_id], total_and_db_input[1][0]), )
                    sqlite.execute(query3, values=(self.database[DB.comics.publisher_id], total_and_db_input[1][0]), )

                    self.proxy_label.setText('AUTO-PAIRED')
                    t.style(self.proxy_label, background=BTN_SHINE_GREEN)
                else:
                    self.proxy_label.setText('PROPOSAL')
                    t.style(self.proxy_label, background=BTN_SHINE)

                self.database = total_and_db_input[1]

            def find_local_candidate(self, data):
                if not self.comicvine_load:
                    return

                issue_number = self.comicvine_load['issue_number']
                volume_name = self.comicvine_load['volume']['name']
                cover_date = self.comicvine_load['cover_date']

                if not issue_number or not volume_name or not cover_date:
                    return

                candidates = []
                skeptic_candidates = []
                for i in data:
                    cv = GUESSComicVineID(database=i, autoinit=False)
                    iter_year = cv.extract_year()
                    if not iter_year:
                        continue

                    if cover_date[0:4] != str(iter_year):
                        continue

                    iter_issuenumber = cv.extract_issue_number()
                    if issue_number != str(iter_issuenumber):
                        continue

                    iter_volumename = cv.extract_volume_name_exclude_version_and_dash()
                    if iter_volumename.lower() != volume_name.lower():
                        if t.config('dev_mode'):
                            if volume_name.lower().find(iter_volumename.lower()) > -1:
                                skeptic_candidates.append(i)
                            elif iter_volumename.lower().find(volume_name.lower()) > -1:
                                skeptic_candidates.append(i)
                            else:
                                continue
                        else:
                            continue

                    candidates.append(i)

                if not candidates:
                    if skeptic_candidates:
                        candidates = skeptic_candidates
                    else:
                        return

                lap = []
                for count, candidate in enumerate(candidates):
                    if count > 10:
                        break

                    org_image = unzipper(database=candidate, index=0)

                    rgb = ImageComparer(org_image, self.image_path)
                    gray = ImageComparer(org_image, self.image_path, grayscale=True)

                    quicktotal = (rgb.total + gray.total) / 2
                    if quicktotal * 100 < t.config('comicvine_lower_threshold'):
                        continue

                    lap.append((quicktotal, candidate,))

                if lap:
                    lap.sort(key=lambda x: x[0], reverse=True)
                    self.parent.signal.db_input.emit(lap[0])

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if not self.database[0]:
                        self.proxy_label.setText('COMICVINE: ' + str(self.database[DB.comics.comic_id]))
                        self.proxy_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

                    else:
                        self.parent.re_init(self.database)

        neighbour = RelativeWidget(self.main.back, main=self.main, parent=self, type='_neighbour', **instructions)

        if instructions['center']:
            self.relatives.append(neighbour)
            self.signal.center_relative.emit()

        elif self.relatives[-1].count < instructions['count']:
            self.relatives.append(neighbour)

        else:
            self.relatives.insert(0, neighbour)

        self.position_relatives()

    def update_comicvine(self):

        if self.refresh_volume_id(self.database):
            self.database = sqlite.refresh_db_input('comics', self.database)

        if not self.database[DB.comics.volume_id]:
            return

        if self.scan50: # overwhelming to scan relatives while just finding its own id, plus theres a que
            return

        maxrelatives = 5 # todo make this number changable in a way so GUI scales niceley

        sorted_volume = self.genereate_volume_sorted_by_issuenumbers()
        candidates = self.generate_candidates_list(sorted_volume)
        self.init_relatives(candidates)

        job = dict(sorted_volume=sorted_volume, candidates=candidates)
        self.signal.volumelabel.emit(job)


    def init_volumes_label(self, job, maxvolumes=100, highjack=False):

        sorted_volume = job['sorted_volume']
        candidates = job['candidates']
        maxrelatives = len([x for x in candidates if x['used']])

        if len(candidates) < 2: # ignore if just one
            self.signal.pair_deletebutton_jobs_done.emit()
            return

        class SmallVolume(GLOBALDeactivate):
            def __init__(self, place, database, *args, **kwargs):
                super().__init__(place=place, *args, **kwargs)
                self.database = database
                self.setText(database[DB.comics.issue_number])
                self.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                self.styleme()
                t.correct_broken_font_size(self, y_margin=0, x_margin=2, minsize=10)


            def styleme(self):
                if self.database[0]:
                    normal_background = 'rgb(115,115,130)'
                    normal_color = UNREAD_C_1
                    self.setToolTip('PRESENT')
                else:
                    normal_background = 'rgb(100,100,100)'
                    normal_color = 'rgb(40,40,40)'
                    self.setToolTip('MISSING!')

                for i in self.relatives:
                    if i.database[DB.comics.comic_id] == self.database[DB.comics.comic_id]:
                        if i.center:
                            normal_background = CURRENT_B_1
                            normal_color = 'rgb(30,30,30)'
                            self.setToolTip('SELECTED')
                        elif self.database[0]:
                            normal_background = CURRENT_B_0
                            normal_color = 'rgb(30,30,30)'
                            self.setToolTip('PRESENT (shown in left side gallery)')
                        else:
                            normal_background = 'rgb(0,40,50)'
                            normal_color = 'rgb(140,140,140)'
                            self.setToolTip('MISSING (proxy viewable in gallery)')

                t.style(self, background=normal_background, color=normal_color)

                self.directives['activation'] = [
                    dict(object=self, background='lightBlue', color='black'),
                ]
                self.directives['deactivation'] = [
                    dict(object=self, background=normal_background, color=normal_color),
                ]

            def styleall(self, mousebutton=1):
                """
                if all five relatives-gallery are accounted for in the
                current volumelabel there's no need for a redraw and
                we use the current one and restyle them all instead

                if ev.button() == 2, a redraw will be enforced
                """
                cvids = [x.database[DB.comics.comic_id] for x in self.relatives]

                for cvid in cvids:
                    for count, i in enumerate(self.parent.volumeslabel.volwidgets):

                        if i.database[DB.comics.comic_id] == cvid and mousebutton != 2: # halts break to enforce redraw
                            break

                        elif count+1 == len(self.parent.volumeslabel.volwidgets): # redraw
                            sorted_volume = self.parent.genereate_volume_sorted_by_issuenumbers()
                            candidates = self.parent.generate_candidates_list(sorted_volume)
                            job = dict(sorted_volume=sorted_volume, candidates=candidates, highjack=True)
                            self.parent.close_and_pop_list('volumeslabel')
                            self.parent.init_volumes_label(job=job, highjack=self.database[DB.comics.comic_id])
                            return

                for i in self.parent.volumeslabel.volwidgets: # no redraw
                    i.styleme()

            def generate_cloud_thumb(self):
                """
                download and create a thumbnail from comicvine
                :return: string or None
                """
                thumb = None
                rv = comicvine(issue=self.database[DB.comics.comic_id])

                if rv:
                    thumb = t.download_file(url=rv['image']['small_url'])
                if not thumb:
                    thumb = t.config('download_error', image=True)

                return thumb

            def order_jobs_for_relatives_and_volumelabel(self, mousebutton=1, thumbnailpath=None):
                if not thumbnailpath:
                    thumbnailpath = self.generate_cloud_thumb()

                    if not thumbnailpath:  # error has occured, cannot please user, no gui update
                        return

                self.parent.close_and_pop_list('relatives')

                sorted_volume = self.parent.genereate_volume_sorted_by_issuenumbers()
                candidates = self.parent.generate_candidates_list(sorted_volume)

                def signal_bug_fix():
                    print("IF CRASH LOOK HERE!")
                    self.signal.center_relative.disconnect(signal_bug_fix)
                    self.parent.pick_relatives(candidates)
                    self.styleall(mousebutton)

                for can in candidates:
                    if can['database'][DB.comics.comic_id] == self.database[DB.comics.comic_id]:

                        can['center'] = True
                        can['used'] = True

                        self.signal.center_relative.connect(signal_bug_fix)

                        self.parent.signal.buildrelative.emit(dict(
                                                                    database=can['database'],
                                                                    image_path=thumbnailpath,
                                                                    count=can['count'],
                                                                    center=True,
                        ))
                        return True

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if self.database[0]: # local do
                    thumb = get_thumbnail_from_zip_or_database(database=self.database, proxy=False)
                    if thumb:
                        self.order_jobs_for_relatives_and_volumelabel(int(ev.button()), thumbnailpath=thumb)

                else: # proxy do
                    self.order_jobs_for_relatives_and_volumelabel(int(ev.button()))


        class VolumeLabel(GOD):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.resize(0,0)
                self.setFrameShape(QtWidgets.QFrame.Box)
                self.setLineWidth(2)
                self.volumes = []
                self.volwidgets = []
                t.style(self, background=TXT_DARKTRANS, color=UNREAD_C_0)

            def position_volumes(self):
                rowlimit = 20
                eachsize = int(self.parent.width() / rowlimit)

                for i in self.volumes:
                    vol = SmallVolume(self, database=i['database'], type='_smallvol' + str(i), extravar=dict(
                        relatives=self.parent.relatives,
                        parent=self.parent,
                    ))

                    if len(self.volwidgets) == 0:
                        t.pos(vol, size=[eachsize-2, 20], move=[3,3])
                    elif len(self.volwidgets) == rowlimit:
                        rowlimit += 20
                        t.pos(vol, coat=self.volwidgets[-1], under=self.volwidgets[-1], y_margin=2, left=3)
                    else:
                        t.pos(vol, coat=self.volwidgets[-1], after=self.volwidgets[-1], x_margin=2)

                    self.volwidgets.append(vol)

                for i in self.volwidgets:
                    if self.width() <= i.geometry().right():
                        t.pos(self, width=i.geometry().right() + 4)
                    if self.height() <= i.geometry().bottom():
                        t.pos(self, height=i.geometry().bottom() + 4)

                self.parent.position_relatives()

            def add_volume(self, dictionary):
                if dictionary['center']:
                    self.volumes.append(dictionary)
                elif dictionary['count'] > self.volumes[-1]['count']:
                    self.volumes.append(dictionary)
                else:
                    self.volumes.insert(0, dictionary)

        def generate_candidates_list(sorted_volume):
            candidates = []
            for count, i in enumerate(sorted_volume):
                candidates.append(dict(database=i, used=False, count=count, center=False))

            return candidates

        def add_if_usable(self, dictionary, greater=False, shorter=False):
            if dictionary['used']:
                return False

            if greater:
                if dictionary['count'] < self.volumeslabel.volumes[0]['count']:
                    return False

            elif shorter:
                if dictionary['count'] > self.volumeslabel.volumes[0]['count']:
                    return False

            dictionary['used'] = True
            self.volumeslabel.add_volume(dictionary=dictionary)
            return True

        self.volumeslabel = VolumeLabel(self.main.back, type='_volumelabel', main=self.main, extravar=dict(parent=self))

        volumes = generate_candidates_list(sorted_volume)

        for dictionary in volumes:

            if highjack and dictionary['database'][DB.comics.comic_id] != highjack:
                continue

            if not highjack and dictionary['database'][DB.comics.comic_id] != self.database[DB.comics.comic_id]:
                continue

            dictionary['center'] = True
            dictionary['used'] = True
            self.volumeslabel.add_volume(dictionary=dictionary)
            break

        while len(self.volumeslabel.volumes) < maxvolumes:
            if not [x for x in volumes if not x['used']]:
                break

            if len(self.volumeslabel.volumes) < maxvolumes:
                for count in range(len(volumes)):
                    if add_if_usable(self, volumes[count], greater=True):
                        break

            if len(self.volumeslabel.volumes) < maxvolumes:
                for count in range(len(volumes)-1,-1,-1):
                    if add_if_usable(self, volumes[count], shorter=True):
                        break

        self.create_draw_all_volumes_button()
        self.volumeslabel.position_volumes()

        # cvsignal = t.signals('cv_jobs_done' + str(self.database[0]))
        # cvsignal.finished.emit()
        self.signal.pair_deletebutton_jobs_done.emit()

    def create_draw_all_volumes_button(self):
        class DrawVolumesButton(GLOBALDeactivate):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.setFrameShape(QtWidgets.QFrame.Box)
                self.setLineWidth(1)
                self.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                self.setText('SEND TO MAIN')
                t.correct_broken_font_size(self, x_margin=2, y_margin=0)
                self.signal_global_gui_change(directive='deactivation', color='gray') # todo large fix

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                volumes = [x['database'] for x in self.volumes if x['database'][0]]
                self.main.search_comics(volumes)

        if 'draw_volumes_button' in dir(self):
            return

        self.draw_volumes_button = DrawVolumesButton(
            self.main.back,
            main=self.main,
            type='_draw_volumes_button',
            extravar=dict(
                volumes=self.volumeslabel.volumes,
                relatives=self.relatives,
            ))

    def draw_suggested_comic(self, candidates):
        class Candidate(GOD):
            def __init__(self, *args, **kwargs):
                super().__init__(type='_irrelevant', *args, **kwargs)
                self.activation_toggle(force=False, save=False)
                self.labels = []

            def next_candidate_button(self, fn, candidatelist):
                class NEXTCANDIATE(GOD):
                    def __init__(self, place, *args, **kwargs):
                        super().__init__(place=place, *args, **kwargs)
                        t.pos(self, inside=place, margin=1)
                        t.style(self, background='transparent')
                    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                        self.draw_suggested_comic(self.candidates)

                if 'title' in dir(self):
                    self.title.setText('CLICK ME')
                    self.next = NEXTCANDIATE(self.title, type='_nextcandidatebtn',
                                         extravar=dict(
                                            draw_suggested_comic=fn,
                                            candidates=candidatelist))

            def show_diffdata(self, work):

                rgb = work['rgb']
                grayscale = work['grayscale']

                self.cycle = [
                    dict(text='TOTAL', value=(rgb.total + grayscale.total) / 2),
                    dict(text='SIZE', value=rgb.file_size),
                    dict(text='COLORS', value=rgb.colors),
                    dict(text='ENTROPY', value=rgb.entropy),
                    dict(text='GRAY(S)', value=grayscale.total),
                    dict(text='BLACK', value=grayscale.black),
                    dict(text='BLUE', value=rgb.blue),
                    dict(text='GREEN', value=rgb.green),
                    dict(text='RED', value=rgb.red),
                    dict(text='MATCH RATE', value=0),
                ]

                def position_header(self, label):
                    label.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                    t.pos(label,
                          coat=self.labels[-1], height=self.labels[-1], add=8, above=self.labels[-1], y_margin=1)
                    t.style(
                        label, background='rgba(10,10,10,220)', color='rgb(190,190,210)', font=self.labels[-1].font + 1)

                for count, i in enumerate(self.cycle):
                    text = i['text']
                    value = int(i['value'] * 100)

                    if not value:
                        continue

                    if not count or not self.labels:
                        w = self.width() * 0.5 - 6
                        h = self.height() * 0.05
                        if h < 14:
                            h = 14

                        x = self.height() - h - 2
                        label = t.pos(new=self, width=w, height=h, move=[3, x])
                    else:
                        label = t.pos(new=self, coat=self.labels[-1], above=self.labels[-1], y_margin=1)

                    label.setFrameShape(QtWidgets.QFrame.Box)
                    label.setLineWidth(1)
                    label.setText(text)
                    label.font = t.correct_broken_font_size(label)

                    rlabel = t.pos(new=label, inside=label, width=label, sub=3)
                    rlabel.setAlignment(QtCore.Qt.AlignRight)
                    rlabel.setText(str(value) + '%')
                    t.style(label, background='rgba(20,20,20,210)', color='rgb(180,180,190)')
                    t.style(rlabel, background='transparent', color='gray', font=label.font)

                    if count+1 == len(self.cycle):
                        rlabel.close()
                        position_header(self, label)
                        self.title = label

                    self.labels.append(label)

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.activation_toggle(save=False)
                if self.activated:
                    self.pair_lineedit.setText(str(self.comic_id))
                    for i in self.labels:
                        i.hide()
                else:
                    self.pair_lineedit.setText("")
                    for i in self.labels:
                        i.show()

        lower = t.config('comicvine_lower_threshold')
        if lower and not [x for x in candidates if x['total'] * 100 >= lower]:
            return

        if not [x for x in candidates if not x['used']]:
            for work in candidates:
                work['used'] = False

        for work in candidates:
            if work['used']:
                continue

            if lower and work in [x for x in candidates if x['total'] * 100 < lower]:
                continue

            work['used'] = True

            for i in ['suggested_candidate_title', 'suggested_candidate']:
                if i in dir(self):
                    getattr(self, i).close()

            path, comic_id = work['cover'], work['comic_id']
            pixmap = QPixmap(path).scaledToWidth(self.pair_button.width() - 2, QtCore.Qt.SmoothTransformation)
            if pixmap.height() > pixmap.width() * 3:
                pixmap = QPixmap(path).scaled(
                self.pair_button.width() - 2, self.pair_button.height() * 3, transformMode=QtCore.Qt.SmoothTransformation)

            label = Candidate(self)
            label.comic_id = comic_id
            label.pair_lineedit = self.pair_lineedit
            t.pos(label, size=pixmap, above=self.pair_button, y_margin=5, add=1)
            label.setFrameShape(QtWidgets.QFrame.Box)
            label.setLineWidth(1)
            t.style(label, background='gray', color='gray')
            label.setPixmap(pixmap)

            title = GLOBALDeactivate(self, type='_cvsuggesttitle')
            title.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
            title.setFrameShape(QtWidgets.QFrame.Box)
            title.setLineWidth(1)

            title = t.pos(title, width=label, height=20, above=label, y_margin=1)
            t.style(title, color='gray')
            title.setText('COMICVINE SUGGESTION')
            t.correct_broken_font_size(title)

            if t.config('comicvine_show_suggestion_details'):
                label.show_diffdata(work)

            label.candidates = candidates

            self.suggested_candidate = label
            self.suggested_candidate_title = title

            if t.config('comicvine_autopair_threshold'):
                if t.config('comicvine_autopair_threshold', curious=True) < work['total'] * 100:
                    self.pair_lineedit.setText(str(comic_id))
                    self.pair_label.save_button.mousePressEvent()
                    self.pair_textlabel.setText('AUTO\nPAIRED')
                    t.correct_broken_font_size(self.pair_textlabel, x_margin=1)
                    title.setText('READER AUTOMATICALLY PAIRED')
                    title.setToolTip('you can change this behavior under comicvine settings!')
                    t.correct_broken_font_size(title, x_margin=1)

            if len(candidates) > 1:
                if lower and len([x for x in candidates if x['total'] * 100 >= lower]) < 2:
                    break

                label.next_candidate_button(self.draw_suggested_comic, candidates)
            break

    def suggest_comic_id(self):
        if self.database[DB.comics.comic_id]:
            return

        elif self.database[DB.comics.type] != DB.comics.comic: # not comic as a type
            return

        elif not t.config('comicvine_suggestion'):
            return

        def signal_guess_finished():
            t.style(self.local_path_widget.delete_button, background=DARKRED)

        t.style(self.local_path_widget.delete_button, background='red')
        self.signal.candidates.connect(self.draw_suggested_comic)
        self.signal.path_deletebutton_jobs_done.connect(signal_guess_finished)
        t.start_thread(GUESSComicVineID,
                       worker_arguments=(self.database, True, self.signal,), name='comicvine', threads=1)

    def quit(self):
        self.signal.disconnect()

        for count in range(len(self.main.widgets['info']) - 1, -1, -1):
            if self.main.widgets['info'][count] != self:
                continue

            self.main.widgets['info'].pop(count)
            if not self.main.widgets['info'] and not self.main.pages_container:
                signal = t.signals('_mainshade')
                signal.quit.emit()

        self.close_and_pop_list('relatives')
        self.close_and_pop_list('volumeslabel')
        if 'draw_volumes_button' in dir(self):
            self.draw_volumes_button.close()

        self.close()