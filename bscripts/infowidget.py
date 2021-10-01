from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint, Qt
from PyQt5.QtGui                  import QKeySequence, QPixmap
from PyQt5.QtWidgets              import QShortcut
from bscripts.comicvine_stuff     import comicvine
from bscripts.database_stuff      import DB, sqlite
from bscripts.file_handling       import FileArchiveManager
from bscripts.file_handling       import check_for_pdf_assistance
from bscripts.file_handling       import concurrent_cbx_to_webp_convertion
from bscripts.file_handling       import concurrent_pdf_to_webp_convertion
from bscripts.file_handling       import extract_from_zip_or_pdf
from bscripts.file_handling       import get_thumbnail_from_zip_or_database
from bscripts.tricks              import tech as t
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
from bscripts.comic_drawing import Cover, ComicWidget, PAGE

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
    def __init__(self, place, parent, main, type, database):
        super().__init__(place=place, main=main, type=type)

        self.setFrameStyle(QtWidgets.QFrame.Box|QtWidgets.QFrame.Raised)
        self.setLineWidth(1)
        self.setMidLineWidth(2)
        t.style(self, tooltip=True, border='black', color='black', background='white')
        self.parent = parent
        self.database = database
        self.relatives = []
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

    def re_init(self, new_database):
        self.database = new_database

        self.close_and_pop_list('box_been_set')
        self.close_and_pop_list('small_info_widgets')
        self.close_and_pop_list('relatives')

        for i in ['cover']:
            if i in dir(self):
                container = getattr(self, i)
                container.close()
                delattr(self, i)

        self.post_init()

    def close_and_pop_list(self, variable):
        if variable in dir(self) and getattr(self, variable):
            container = getattr(self, variable)
            if type(container) == list:
                for count in range(len(container) - 1, -1, -1):
                    container[count].close()
                    container.pop(count)
            else:
                container.close()
                delattr(self, variable)

    def post_init(self):
        signal = t.signals('neighbour' + str(self.database[0]), reset=True)
        signal.neighbour.connect(self.create_relative)

        def generate_global_signal(self):
            global_signal = '_global_on_off_' + str(self.database[0])
            return global_signal


        def make_cover_and_cover_details(self):
            cover_height = t.config('cover_height') * 2
            cover = extract_from_zip_or_pdf(database=self.database)
            self.make_cover(cover_height=cover_height, coverfile=cover)
            self.cover.first_reize(cover_height=cover_height)
            t.pos(self.cover, move=[5, 5])
            self.make_box_of_details(enhancefactor=3)
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
                            self.parent.parent.close()

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
            return set7

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

        volumes_signal = t.signals('volumes_label' + str(self.database[0]), reset=True)
        volumes_signal.startjob.connect(self.init_volumes_label)

        t.start_thread(self.update_comicvine, name='comicvine', threads=1)

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
            t.pos(self.volumeslabel, top=dict(bottom=self), left=self, y_margin=3)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(force=True, save=False)

        if ev.button() == 1:
            self.old_position = ev.globalPos()
        elif ev.button() == 2:
            self.quit()

    def create_relative(self, instructions):

        class RelativeWidget(GOD):
            def __init__(self, place, database, image_path, center, parent, count, *args, **kwargs):
                super().__init__(place=place, *args, **kwargs)
                self.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Raised)
                self.setLineWidth(1)
                self.setMidLineWidth(2)
                self.database = database
                self.parent = parent
                self.image_path = image_path
                self.center = center
                self.count = count

                margin = self.lineWidth() + self.midLineWidth() + 1
                height = int(self.parent.height() * 0.2 - margin * 3)

                pixmap = QPixmap(self.image_path).scaledToHeight(height + 2, QtCore.Qt.SmoothTransformation)

                if pixmap.width() > height*3:
                    pixmap = QPixmap(self.image_path).scaled(height + 2, height * 3)

                t.pos(self, width=pixmap, height=pixmap, add=margin * 2)
                self.cover = t.pos(new=self, size=pixmap)
                self.cover.setPixmap(pixmap)
                t.pos(self.cover, inside=self, margin=margin)

                if not self.center:
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

                self.show()

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if not self.database[0]:
                        self.proxy_label.setText('COMICVINE: ' + str(self.database[DB.comics.comic_id]))
                        self.proxy_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

                    elif not self.center:
                        print(self.database)
                        self.parent.re_init(self.database)

        neighbour = RelativeWidget(self.main.back, main=self.main, parent=self, type='_neighbour', **instructions)

        if instructions['center']:
            self.relatives.append(neighbour)

        elif self.relatives[-1].count < instructions['count']:
            self.relatives.append(neighbour)

        else:
            self.relatives.insert(0, neighbour)

        self.position_relatives()

    def update_comicvine(self):
        signal = t.signals('neighbour' + str(self.database[0]))

        def refresh_volume_id(database):
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

            def update_issuenumbrs(cvdata, localdata):
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

            query = 'select * from comics where volume_id = (?)'
            data = sqlite.execute(query=query, values=volume_id, all=True)
            delete_duplicants(data)

            if data:

                cv_vols = comicvine(volume=volume_id, update=True)
                update_issuenumbrs(cvdata=cv_vols, localdata=data)

                if data and cv_vols and cv_vols['issues']:

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

        def generate_candidates_list(sorted_volume):
            candidates = []

            for count, i in enumerate(sorted_volume):
                candidates.append(dict(database=i, used=False, count=count, center=False))

            return candidates

        def create_center_candidate(self, candidates):
            for dictionary in candidates:
                if dictionary['database'][0] == self.database[0]:
                    dictionary['center'] = True
                    thumb = get_thumbnail_from_zip_or_database(database=self.database)
                    signal.neighbour.emit(dict(
                        database=self.database, image_path=thumb, center=True, count=dictionary['count']))

                    dictionary['used'] = True
                    break

        def find_center_candidate(candidates):
            for i in candidates:
                if i['center']:
                    return i['count']

        def usable_and_greater_or_shorter_candidate(candidates, candidate, greater=False, shorter=False):

            def find_an_unupdated_local_comic_id(candidate):
                local_check_query = 'select * from comics where comic_id = (?)'
                data = sqlite.execute(local_check_query, candidate['database'][DB.comics.comic_id])

                if data:
                    refresh_volume_id(data)
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

            find_an_unupdated_local_comic_id(candidate)

            thumb = None

            if candidate['database'][0]:
                thumb = get_thumbnail_from_zip_or_database(database=candidate['database'], proxy=False)
            else:
                rv = comicvine(issue=candidate['database'])
                if rv:
                    thumb = t.download_file(url=rv['image']['small_url'])
                if not thumb:
                    thumb = t.config('download_error', image=True)

            if not thumb:
                return False

            signal.neighbour.emit(dict(
                database=candidate['database'], image_path=thumb, center=False, count=candidate['count']))

            candidate['used'] = True
            return True

        def init_relatives(self, candidates, maxrelatives):
            if len(candidates) < 2:
                return

            create_center_candidate(self, candidates)

            while len([x for x in candidates if x['used']]) < maxrelatives:

                if not [x for x in candidates if not x['used']]:
                    break

                if len([x for x in candidates if x['used']]) < maxrelatives:
                    for count in range(len(candidates)):

                        if usable_and_greater_or_shorter_candidate(candidates, candidates[count], greater=True):
                            break

                if len([x for x in candidates if x['used']]) < maxrelatives:
                    for count in range(len(candidates)-1,-1,-1):

                        if usable_and_greater_or_shorter_candidate(candidates, candidates[count], shorter=True):
                            break

        if refresh_volume_id(self.database):
            self.database = sqlite.refresh_db_input('comics', self.database)

        if not self.database[DB.comics.volume_id]:
            return

        maxrelatives = 5 # todo make this number changable in a way so GUI scales niceley
        sorted_volume = genereate_volume_sorted_by_issuenumbers(self)

        candidates = generate_candidates_list(sorted_volume)
        init_relatives(self, candidates, maxrelatives=maxrelatives)

        volumes_signal = t.signals('volumes_label' + str(self.database[0]))
        job = dict(sorted_volume=sorted_volume, candidates=candidates)
        volumes_signal.startjob.emit(job)


    def init_volumes_label(self, job):
        sorted_volume = job['sorted_volume']
        candidates = job['candidates']
        maxrelatives = len([x for x in candidates if x['used']])

        if len(candidates) <= maxrelatives:
            return

        class SmallVolume(GOD):
            def __init__(self, place, database, relatives, *args, **kwargs):
                super().__init__(place=place, *args, **kwargs)
                self.database = database
                self.relatives = relatives
                self.setText(database[DB.comics.issue_number])
                self.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                self.styleme()

            def styleme(self):
                t.correct_broken_font_size(self, y_margin=0, x_margin=2)

                for i in self.relatives:
                    if i.database[DB.comics.comic_id] == self.database[DB.comics.comic_id]:
                        if i.center:
                            t.style(self, background=CURRENT_B_0, color=CURRENT_C_0)
                        elif self.database[0]:
                            t.style(self, background='rgb(50,50,150)', color='rgb(10,10,10)')
                        else:
                            t.style(self, background='rgb(50,50,75)', color='rgb(30,30,30)')

                if self.database[0]:
                    t.style(self, background='rgb(110,110,110)', color='rgb(30,30,30)')
                else:
                    t.style(self, background='rgb(50,30,30)', color='rgb(140,140,140)')

            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                self.close()

        class VolumeLabel(GOD):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.resize(0,0)
                self.volumes = []
                self.volwidgets = []

            def position_volumes(self):
                for count, i in enumerate(self.volumes):
                    vol = SmallVolume(self, database=i['database'], type='_smallvol', relatives=self.parent.relatives)
                    if count == 0:
                        eachsize = self.parent.width() / 20
                        t.pos(vol, size=[eachsize-2, 20])
                    else:
                        t.pos(vol, coat=self.volwidgets[-1], after=self.volwidgets[-1], x_margin=2)

                    self.volwidgets.append(vol)

                for i in self.volwidgets:
                    if self.width() < i.geometry().right():
                        t.pos(self, width=i.geometry().right())
                    if self.height() < i.geometry().bottom():
                        t.pos(self, height=i.geometry().bottom())

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

        self.volumeslabel = VolumeLabel(self.main.back, type='_volumelabel', main=self.main, extravar=dict(parent=self))

        maxvolumes = 100
        volumes = generate_candidates_list(sorted_volume)
        for dictionary in volumes:
            if dictionary['database'][0] == self.database[0]:
                dictionary['center'] = True
                dictionary['used'] = True
                self.volumeslabel.add_volume(dictionary=dictionary)
                break

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

        self.volumeslabel.position_volumes()


    def quit(self, signal=True):
        """
        if open page from the same database
        shade not closed (signal not emitted)
        """
        self.close_and_pop_list('relatives')
        self.close_and_pop_list('volumeslabel')

        self.close()

        for i in self.main.pages_container:
            if i.database[0] == self.database[0]:
                return

        if signal:
            shade_signal = t.signals('shade')
            shade_signal.quit.emit()