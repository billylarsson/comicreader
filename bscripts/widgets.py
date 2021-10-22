import random
from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint
from PyQt5.QtGui                  import QColor, QPen
from bscripts.comicvine_stuff     import comicvine
from bscripts.database_stuff      import DB, sqlite
from bscripts.tricks              import tech as t
from script_pack.preset_colors    import *
from script_pack.settings_widgets import CheckableLCD, ExecutableLookCheckable, CheckableAndGlobalHighlight
from script_pack.settings_widgets import FolderSettingsAndGLobalHighlight
from script_pack.settings_widgets import GLOBALDeactivate, GOD
from script_pack.settings_widgets import HighlightRadioBoxGroup, POPUPTool
from script_pack.settings_widgets import UniversalSettingsArea
import os
import sys

TEXTSIZE = 14

class TOOLSearch(POPUPTool):
    def __init__(self, place, *args, **kwargs):
        super().__init__(place, *args, **kwargs)
        self.activation_toggle(force=True, save=False)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
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
            t.pos(self.main.le_primary_search, coat=self, width=300, after=self, x_margin=1)
        else:
            self.main.le_primary_search.hide()

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

class TITLE(QtWidgets.QLabel):
    def __init__(self, place, child, title, killsignal, width):
        super().__init__(place)
        self.child = child
        self.killsignal_name = killsignal
        self.sort_label = GOD(place)
        self.child.sort_label = self.sort_label
        t.pos(self, size=[width,30], move=[30,30])
        self.draw_rectangles()
        self.label = QtWidgets.QLabel(self)
        t.style(self.label, background='transparent', color=TXT_SHINE)
        t.pos(self.label, inside=self, margin=4)
        self.label.setText(title)
        self.label.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignHCenter)
        t.correct_broken_font_size(self.label)
        self.show()


    def draw_sorting_menus(self, publishers=False, volumes=False):
        class SortRadio(HighlightRadioBoxGroup):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.activated = False

        class SortName(SortRadio):
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if publishers:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.signal.sort_publishers_by_name.emit()

                    elif volumes:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_volumes(sort_by_name=True, refresh=False)

        class SortCount(SortRadio):
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if publishers:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.signal.sort_publishers_by_amount.emit()

                    elif volumes:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_volumes(sort_by_amount=True, refresh=False)

        class SortRating(SortRadio):
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if publishers:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.signal.sort_publishers_by_rating.emit()

                    elif volumes:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_volumes(sort_by_rating=True, refresh=False)

        self.sort_labels = []
        cycle = [
            dict(type='p_sort_name', widget=SortName, tooltip='SORT BY NAME'),
            dict(type='p_sort_count', widget=SortCount, tooltip='SORT BY AMOUNT IN COLLECTION'),
            dict(type='p_sort_rating', widget=SortRating, tooltip='SORT BY RATING (no rating will be discounted for)'),
        ]

        for dictionary in cycle:

            type = dictionary['type']
            widget = dictionary['widget']
            tooltip = dictionary['tooltip']

            label = widget(self.sort_label, type=type + self.label.text(), signalgroup='_pubsort' + self.label.text())
            label.setToolTip(tooltip)
            label.signal = self.child.signal

            label.show_publishers = self.child.show_publishers
            label.show_volumes = self.child.show_volumes

            if not self.sort_labels:
                t.pos(label, size=[10, 10], move=[2,2])
            else:
                t.pos(label, coat=self.sort_labels[-1], after=self.sort_labels[-1], x_margin=2)

            self.sort_labels.append(label)

            label.button = GOD(label, type=type)
            label.textlabel = GOD(label, type=type)
            label.textlabel.hide()
            t.pos(label.button, inside=label)
            label.post_init()

        self.sort_labels[-1].fall_back_to_default(self.sort_labels, 'p_sort_name' + self.label.text())
        w = self.sort_labels[-1].geometry().right() - 1
        t.pos(self.sort_label, width=w, height=self.sort_labels[-1], add=4)
        t.pos(self.sort_label, above=self)

    def draw_rectangles(self):
        pm = QtGui.QPixmap(self.width(), self.height())
        pm.fill(QtCore.Qt.black)
        painter = QtGui.QPainter(pm)

        whitepen = QPen()
        whitepen.setWidth(1)
        wcol = QColor()
        wcol.setRgb(170,170,170)
        whitepen.setColor(wcol)

        graypen = QPen()
        graypen.setWidth(3)
        gcol = QColor()
        gcol.setRgb(40,40,40)
        graypen.setColor(gcol)

        darkgraypen = QPen()
        darkgraypen.setWidth(1)
        dgcol = QColor()
        dgcol.setRgb(110,110,110)
        darkgraypen.setColor(dgcol)

        painter.setPen(whitepen)
        painter.drawRect(0,0,self.width()-1, self.height()-1)

        painter.setPen(graypen)
        painter.drawRect(3,3,self.width()-6, self.height()-6)

        painter.setPen(darkgraypen)
        painter.drawRect(4,4,self.width()-8, self.height()-8)

        painter.end()
        self.setPixmap(pm)

    def position_child_at_bottom(self):
        t.pos(self.child, below=self, y_margin=5)
        t.pos(self.sort_label, above=self)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self):
            del self.old_position

    def mouseMoveEvent(self, ev):
        if ev.button() == 2:
            return

        delta = QPoint(ev.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = ev.globalPos()
        self.position_child_at_bottom()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.old_position = ev.globalPos()
        if ev.button() == 2:
            self.killsignal = t.signals(self.killsignal_name, delete_afterwards=True)
            self.killsignal.finished.emit()


class CVIDFileBrowse(GLOBALDeactivate):
    def __init__(self, place, data, text, *args, **kwargs):
        super().__init__(place=place, *args, **kwargs)
        self.data = data
        self.setText('  ' + text)
        self.activation_toggle(force=False, save=False)

    def post_init(self):
        self.default_event_colors()
        self.signal_global_gui_change('deactivation')
        t.correct_broken_font_size(self, shorten=True, presize=True, maxsize=self.textsize)
        self.tooltip_generator()

    def tooltip_generator(self):
        tooltip = ""
        if 'volume_percentage' in self.data and self.data['volume_percentage']:
            tooltip += f"Carries {round(self.data['volume_percentage'] * 100, 2)}% of all paired volumes"
            tooltip += f" ({self.data['volumes_count']} of {self.data['total_volume_count']})"

            if 'average_rating' in self.data and self.data['average_rating']:
                rating = round(self.data['average_rating'], 2)
                tooltip += f"\nAverage rating among all rated volumes from this publisher: {rating}"

        elif 'issue_count' in self.data and self.data['issue_count']:
            perc = self.data['issue_count'] / self.data['total_issues']
            perc = round(perc, 2)
            tooltip += f"Carries {self.data['issue_count']} issues, {perc}% of "
            tooltip += f"this publishers {self.data['total_issues']} paired issues."

            if 'average_rating' in self.data and self.data['average_rating']:
                rating = round(self.data['average_rating'], 2)
                tooltip += f"\nAverage rating among all rated issues from this volume: {rating}"

        self.setToolTip(tooltip)

    def default_event_colors(self):
        self.directives['activation'] = [
            dict(object=self, color=TXT_SHINE, background='rgb(20,20,20)'),
        ]

        self.directives['deactivation'] = [
            dict(object=self, color=TXT_SHADE, background='rgb(10,10,10)'),
        ]

class BrowseFile(CVIDFileBrowse):
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.main.search_comics(highjack=[self.data['database']])

    def default_event_colors(self):
        loc = t.separate_file_from_folder(self.data['database'][DB.comics.local_path])

        if self.data['database'][DB.comics.comic_id]:
            BACK_ON = 'rgb(20,20,60)'
            BACK_OFF = 'rgb(10,10,50)'
        else:
            BACK_ON = 'rgb(20,20,20)'
            BACK_OFF = 'rgb(10,10,10)'

        if loc.ext.lower() == 'cbr':
            COL_ON = 'orange'
            COL_OFF = 'rgb(165, 85, 0)'
        else:
            COL_ON = 'orange'
            COL_OFF = 'rgb(255, 85, 0)'

        self.directives['activation'] = [
            dict(object=self, color=COL_ON, background=BACK_ON),
        ]
        self.directives['deactivation'] = [
            dict(object=self, color=COL_OFF, background=BACK_OFF),
        ]

class BrowseFolder(CVIDFileBrowse):
    def draw_files(self, filedict):
        for path, database in filedict.items():
            if not database:
                continue

            self.signal.drawfile.emit(dict(path=path, database=database))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'dummy' in self.data:
            rv = t.separate_file_from_folder(self.data['path'])
            if rv.parent:
                if rv.parent in self.base_folders or rv.folder in self.base_folders:
                    t.close_and_pop(self.parent.files)
                    for i in self.base_folders:
                        self.signal.drawfolder.emit(dict(path=i))

                    return
                else:
                    self.data['path'] = rv.parent

        for count, walk in enumerate(os.walk(self.data['path'])):
            current_dir = walk[0]
            loc = t.separate_file_from_folder(current_dir)
            folders = [current_dir + loc.sep + x for x in walk[1]]
            folders.sort()

            t.close_and_pop(self.parent.files)
            self.parent.draw_dummy(dict(path=current_dir, dummy=True))

            for i in folders:
                self.signal.drawfolder.emit(dict(path=i))

            white_extensions = {'pdf', 'cbz', 'cbr'}
            whitefiles = []
            for file in walk[2]:
                f = file.split('.')
                if len(f) > 1:
                    if f[-1].lower() in white_extensions:
                        whitefiles.append(file)

            files = {current_dir + loc.sep + x: None for x in sorted(whitefiles)}
            comics = sqlite.execute('select * from comics', all=True)

            for db in comics:
                for path,v in files.items():

                    if v:
                        continue

                    if db[DB.comics.local_path] == path:
                        files[path] = db
                        if not [v for k,v in files.items() if not v]:
                            self.draw_files(files)
                            return
                        break

            self.draw_files(files)
            return


class BrowseVolume(CVIDFileBrowse):
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        results = t.sort_by_number(self.data['issues'], DB.comics.issue_number)
        self.main.search_comics(highjack=results)

class BrowsePublisher(CVIDFileBrowse):
    def create_volume_widget(self):
        killsignal = 'kill_volume_widget' + str(self.data['publisher_id'])
        title = self.data['publisher_name']

        self.volume_widget = PUBtoVOLtoISSUEScroll(
            self.main.back, self.main, parent=self, title=title, killsignal=killsignal)
        self.volume_widget.title.draw_sorting_menus(volumes=True)

        self.volume_widget.data = self.data
        t.pos(self.volume_widget.title, after=self.parent.parent)
        self.volume_widget.title.position_child_at_bottom()

        if t.config('p_sort_name' + title):
            wa = (True,)
        elif t.config('p_sort_count' + title):
            wa = (False,True,)
        elif t.config('p_sort_rating' + title):
            wa = (False, False, True,)
        else:
            wa = (False, False, False,)

        t.start_thread(self.volume_widget.show_volumes, name='comicvine', threads=1, worker_arguments=wa)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.slaves_can_alter = False
            self.create_volume_widget()

        else:
            killsignal = 'kill_volume_widget' + str(self.data['publisher_id'])
            signal = t.signals(killsignal, delete_afterwards=True)
            signal.finished.emit()

class PUBtoVOLtoISSUEScroll(QtWidgets.QScrollArea):
    def __init__(self, place, main, parent, title, killsignal='kill_publisher_widget', width=300):
        super().__init__(place)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.parent = parent
        self.publishers = {}
        self.scrollarea = self
        self.backplate = self.BackPlate(place=self, parent=self, main=main)
        self.pubs = self.backplate.pubs
        self.vols = self.backplate.vols
        self.files = self.backplate.files
        self.setWidget(self.backplate)
        self.title = TITLE(main.back, child=self, title=title, killsignal=killsignal, width=width)
        t.pos(self, width=self.title, below=self.title, y_margin=5)

        self.killsignal = t.signals(killsignal)
        self.killsignal.finished.emit() # close any previous dupe
        self.killsignal.finished.connect(self.killswitch)

        self.signal = t.signals('PVI_show_this' + title, reset=True)

        self.signal.drawpublisher.connect(self.backplate.draw_publisher)
        self.signal.drawvolume.connect(self.backplate.draw_volume)
        self.signal.drawfolder.connect(self.backplate.draw_folder)
        self.signal.drawfile.connect(self.backplate.draw_file)

        self.signal.sort_publishers_by_name.connect(self.reorganize_publishers_by_name)
        self.signal.sort_publishers_by_amount.connect(self.reorganize_publishers_by_amount)
        self.signal.sort_publishers_by_rating.connect(self.reorganize_publishers_by_rating)

        self.signal.sort_volumes_by_name.connect(self.reorganize_volumes_by_name)
        self.signal.sort_volumes_by_amount.connect(self.reorganize_volumes_by_amount)
        self.signal.sort_volumes_by_rating.connect(self.reorganize_volumes_by_rating)

        self.show()

        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setLineWidth(1)
        t.style(self, background='rgb(130,130,130)')

    def killswitch(self):
        self.parent.slaves_can_alter = True
        self.parent.signal_global_gui_change(directive='deactivation')
        self.parent.activation_toggle(force=False, save=False)
        self.sort_label.close()
        self.backplate.close()
        self.title.close()
        self.close()

    class BackPlate(QtWidgets.QWidget):
        def __init__(self, place, parent, main):
            super().__init__(place)
            self.scrollarea = parent
            self.parent = parent
            self.main = main
            self.pubs = []
            self.vols = []
            self.files = []

        def standard_positioning(self, object, container):
            if not container:
                t.pos(object, size=[self.parent.title.width(),30])
                backup = object.text()
                object.setText('RANDOM TEXT THIS LONG')
                object.textsize = t.correct_broken_font_size(object)
                object.setText(backup)
            else:
                t.pos(object, coat=container[-1], below=container[-1], y_margin=1)
                object.textsize = container[-1].textsize

            prebottom = object.geometry().bottom()
            t.pos(self, inside=self.scrollarea, height=prebottom)

            if self.height() < self.main.height() * 0.5:
                t.pos(self.scrollarea, width=object)
                t.pos(self.scrollarea, height=prebottom, add=4)

            object.post_init()
            container.append(object)

        def draw_dummy(self, data):
            widget = BrowseFolder(
                self, type='_dummy..', main=self.main, data=data, text='..')

            widget.signal = self.parent.signal
            widget.base_folders = self.parent.base_folders
            self.standard_positioning(widget, container=self.files)

        def draw_file(self, data):
            loc = t.separate_file_from_folder(data['path'])
            widget = BrowseFile(
                self, type='_folder' + data['path'], main=self.main, data=data, text=loc.filename)

            widget.signal = self.parent.signal
            self.standard_positioning(widget, container=self.files)

        def draw_folder(self, data):
            loc = t.separate_file_from_folder(data['path'])
            if loc.subfolder:
                widget = BrowseFolder(
                    self, type='_folder' + data['path'], main=self.main, data=data, text=loc.subfolder)

                widget.signal = self.parent.signal
                self.standard_positioning(widget, container=self.files)

        def draw_volume(self, data):
            volume_id = data['volume_id']
            volume_name = data['volume_name']

            widget = BrowseVolume(
                self, type='_vol' + str(volume_id), data=data, main=self.main, text=volume_name)

            self.standard_positioning(widget, container=self.vols)

        def draw_publisher(self, publisher_id):
            pub = self.parent.publishers[publisher_id]
            widget = BrowsePublisher(
                self, type='_pub' + str(publisher_id), data=pub, main=self.main, text=pub['publisher_name'])

            self.standard_positioning(widget, container=self.pubs)


    def show_volumes(self, sort_by_name=False, sort_by_amount=False, sort_by_rating=False, refresh=True):
        def delete_previous(self):
            if refresh:
                t.close_and_pop(self.vols)

        def volumes_quick_by_name(self, emit_later):
            tmp = [(x['volume_name'], x,) for x in emit_later]
            tmp.sort(key=lambda x: x[0].lower())
            for i in tmp:
                self.signal.drawvolume.emit(i[1])

        def volumes_quick_by_amount(self, emit_later):
            tmp = [(len(x['issues']), x,) for x in emit_later]
            tmp.sort(key=lambda x: x[0], reverse=True)
            for i in tmp:
                self.signal.drawvolume.emit(i[1])

        def volumes_quick_by_rating(self, emit_later, inject_rating_only=False):
            rt = []
            for i in emit_later:
                ratings = [x[DB.comics.rating] for x in i['issues'] if x[DB.comics.rating]]

                if not ratings:
                    average_rating = 0
                else:
                    average_rating = sum(ratings) / len(ratings)

                rt.append((average_rating, i,))
                if inject_rating_only:
                    i['average_rating'] = average_rating

            if inject_rating_only:
                return

            rt.sort(key=lambda x:x[0], reverse=True)
            for i in rt:
                self.signal.drawvolume.emit(i[1])

        def generate_percentage_data(self, emit_later):
            volumes_quick_by_rating(self, emit_later, inject_rating_only=True)
            tmp = [(len(x['issues']), x,) for x in emit_later]
            total = sum([x[0] for x in tmp])
            for i in emit_later:
                i['percentage'] = len(i['issues']) / total
                i['issue_count'] = len(i['issues'])
                i['total_issues'] = total

        def post_drawn_volumes_sorting(self, emit_later):
            if emit_later:  # dev_mode
                generate_percentage_data(self, emit_later)
                if sort_by_name:
                    volumes_quick_by_name(self, emit_later)
                elif sort_by_amount:
                    volumes_quick_by_amount(self, emit_later)
                elif sort_by_rating:
                    volumes_quick_by_rating(self, emit_later)

            elif sort_by_name:
                self.signal.sort_volumes_by_name.emit()
            elif sort_by_amount:
                self.signal.sort_volumes_by_amount.emit()
            elif sort_by_rating:
                self.signal.sort_volumes_by_rating.emit()

        if not refresh:
            post_drawn_volumes_sorting(self, False)
            return

        delete_previous(self)
        emit_later = []

        for volid in self.data['volumes']:
            data = sqlite.execute('select * from volumes where volume_id = (?)', volid)
            if not data:
                comicvine(volume=volid, update=True)
                data = sqlite.execute('select * from volumes where volume_id = (?)', volid)

            if not data or not data[DB.volumes.volume_name]:
                continue

            d = dict(
                publisher_id=self.data['publisher_id'],
                publisher_name=self.data['publisher_name'],
                volume_name=data[DB.volumes.volume_name],
                issues=self.data['sorted_volumes'][volid],
                volume_id=volid,
            )

            # will redraw later down the line, quicker experience but can appear frozen therefore its a dev thingey
            if t.config('dev_mode'):
                if sort_by_name or sort_by_amount or sort_by_rating:
                    emit_later.append(d)
                    continue

            self.signal.drawvolume.emit(d)

        post_drawn_volumes_sorting(self, emit_later)


    def sort_and_stack_under_each_others(self, tmplist, sorted=False):
        """
        takes list with tubples and sort them by index 0 and places them by index 1
        :param tmplist: [(string_name, object_widget,), (string_name, object_widget,)]
        """
        if not sorted:
            tmplist.sort(key=lambda x: x[0].lower())

        top = [x[1].geometry().top() for x in tmplist]
        top.sort()

        for count, i in enumerate(tmplist):
            if count == 0:
                t.pos(i[1], top=top[0])
            else:
                t.pos(i[1], below=tmplist[count-1][1], y_margin=1)

    def reorganize_volumes_by_name(self):
        self.wait_for_job_to_finish(vols=True)
        tmp = [(x.data['volume_name'], x,) for x in self.vols]
        self.sort_and_stack_under_each_others(tmplist=tmp)

    def reorganize_volumes_by_amount(self):
        self.wait_for_job_to_finish(vols=True)
        tmp = [(len(x.data['issues']), x,) for x in self.vols]
        tmp.sort(key=lambda x:x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=tmp, sorted=True)

    def reorganize_volumes_by_rating(self):
        self.wait_for_job_to_finish(vols=True)

        rt = []
        for i in self.vols:
            ratings = [x[DB.comics.rating] for x in i.data['issues'] if x[DB.comics.rating]]

            if not ratings:
                average_rating = 0
            else:
                average_rating = sum(ratings) / len(ratings)

            rt.append((average_rating, i,))

        rt.sort(key=lambda x: x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=rt, sorted=True)

    def wait_for_job_to_finish(self, pubs=False, vols=False):
        if pubs:
            freezestop = t.keep_track(name='reorgpubs', restart=True)
            while len(self.pubs) != len(self.publishers) and freezestop.runtime < 5:
                pass
        elif vols:
            freezestop = t.keep_track(name='reorgvols', restart=True)
            while len(self.vols) != len(self.data['volumes']) and freezestop.runtime < 5:
                pass

    def reorganize_publishers_by_name(self):
        self.wait_for_job_to_finish(pubs=True)
        tmp = [(x.data['publisher_name'], x,) for x in self.pubs]
        self.sort_and_stack_under_each_others(tmplist=tmp)

    def reorganize_publishers_by_amount(self):
        self.wait_for_job_to_finish(pubs=True)
        tmp = [(len(x.data['volumes']), x,) for x in self.pubs]
        tmp.sort(key=lambda x: x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=tmp, sorted=True)

    def reorganize_publishers_by_rating(self):
        self.wait_for_job_to_finish(pubs=True)

        rd = {}
        rl = []
        for publisher in self.pubs:
            rd.update({publisher: []})
            for volume_id in publisher.data['sorted_volumes']:
                rd[publisher] += [x for x in publisher.data['sorted_volumes'][volume_id] if x[DB.comics.rating]]

        for publisher, lst in rd.items():
            if not lst:
                average_rating = 0
            else:
                average_rating = [x[DB.comics.rating] for x in lst]
                average_rating = sum(average_rating) / len(lst)

            rl.append((average_rating, publisher,))

        rl.sort(key=lambda x: x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=rl, sorted=True)

    def show_publishers(self, sort_by_name=False, sort_by_amount=False, sort_by_rating=False, refresh=True):
        """
        this is usually a thread of its own, drawing publisher one
        and one but can be highjacked when pressing sorting buttons

        if publisher name is not locally know a comicvine request is made
        therefore they may appear one and one with a short delay inbetween

        :param sort_by_name: bool
        :param sort_by_amount: bool
        :param refresh: does not redraw widget, reuses the old ones
        """
        def delete_previous(self):
            if refresh:
                t.close_and_pop(self.pubs)

        def fetch_data():
            query = 'select * from comics where publisher_id is not null and comic_id is not null and volume_id is not null'
            data = sqlite.execute(query, all=True)
            if not data:
                # fetches one random comic with an comic_id just to show that things are working
                tmp_query = 'select * from comics where comic_id is not null'
                tmp_data = sqlite.execute(tmp_query, one=True)
                if tmp_data:
                    comicvine(issue=tmp_data, update=True)
                    data = sqlite.execute(query, all=True)

            data.sort(key=lambda x: x[DB.comics.volume_id])
            data.sort(key=lambda x: x[DB.comics.publisher_id])
            return data

        def get_and_add_publisher_data(self, publisher_id):
            p = sqlite.execute('select * from publishers where publisher_id = (?)', publisher_id)
            if not p:
                comicvine(publisher=i, update=True)  # this should update the requested publisher
                p = sqlite.execute('select * from publishers where publisher_id = (?)', publisher_id)

            if p:
                self.publishers.update(
                    {publisher_id:
                        dict(
                            publisher_name=p[DB.publishers.publisher_name],
                            publisher_id=publisher_id,
                            issues=0,
                            volumes=[],
                        )})

        def add_volume_issue_count(self, issue, publisher_id):
            self.publishers[publisher_id]['issues'] += 1
            volume_id = issue[DB.comics.volume_id]
            if volume_id not in self.publishers[publisher_id]['volumes']:
                self.publishers[publisher_id]['volumes'].append(volume_id)

            if 'sorted_volumes' not in self.publishers[publisher_id]:
                self.publishers[publisher_id].update(dict(sorted_volumes={ }))

            if volume_id not in self.publishers[publisher_id]['sorted_volumes']:
                self.publishers[publisher_id]['sorted_volumes'].update({volume_id: []})

            self.publishers[publisher_id]['sorted_volumes'][volume_id].append(issue)

        def publishers_quick_by_name(self):
            tmp = [(self.publishers[x]['publisher_name'], self.publishers[x]['publisher_id'],) for x in self.publishers]
            tmp.sort(key=lambda x: x[0].lower())
            for i in tmp:
                self.signal.drawpublisher.emit(i[1])

        def publishers_quick_by_amount(self):
            tmp = [(len(self.publishers[x]['volumes']), self.publishers[x]['publisher_id'],) for x in self.publishers]
            tmp.sort(key=lambda x: x[0], reverse=True)
            for i in tmp:
                self.signal.drawpublisher.emit(i[1])

        def publishers_quick_by_rating(self, inject_rating_only=False):
            rd = {}
            rl = []
            for publisher_id in self.publishers:

                rd.update({publisher_id: []})

                for volume_id in self.publishers[publisher_id]['sorted_volumes']:

                    all_issues_for_volume_id = self.publishers[publisher_id]['sorted_volumes'][volume_id]
                    rd[publisher_id] += [x for x in all_issues_for_volume_id if x[DB.comics.rating]]

            for publisher_id, lst in rd.items():
                if not lst:
                    average_rating = 0
                else:
                    average_rating = [x[DB.comics.rating] for x in lst]
                    average_rating = sum(average_rating) / len(lst)

                rl.append((average_rating, publisher_id,))
                self.publishers[publisher_id]['average_rating'] = average_rating

            rl.sort(key=lambda x:x[0], reverse=True)

            for i in rl:
                if inject_rating_only:
                    self.publishers[i[1]]['publisher_rating'] = i[0]
                else:
                    self.signal.drawpublisher.emit(i[1])

        def generate_percentage_data(self):
            tmp = [(len(self.publishers[x]['volumes']), self.publishers[x]['publisher_id'],) for x in self.publishers]
            total = sum([x[0] for x in tmp])
            for i in tmp:
                self.publishers[i[1]]['volumes_count'] = i[0]
                self.publishers[i[1]]['volume_percentage'] = i[0] / total
                self.publishers[i[1]]['total_volume_count'] = total

            publishers_quick_by_rating(self, inject_rating_only=True)

        def post_drawing_publishers_sorting(self):
            """
            this has to be done after all publishers have been
            draw because we dont know whats what before they're
            all refreshed if needed from comicvine servers
            """
            # this is a little bit better experienced but it can appears to be frozen if comcivine refresh is needed
            if t.config('dev_mode'):
                generate_percentage_data(self)
                if sort_by_name:
                    publishers_quick_by_name(self)
                elif sort_by_amount:
                    publishers_quick_by_amount(self)
                elif sort_by_rating:
                    publishers_quick_by_rating(self)
            else:
                if sort_by_name:
                    self.signal.sort_publishers_by_name.emit()
                elif sort_by_amount:
                    self.signal.sort_publishers_by_amount.emit()
                elif sort_by_rating:
                    self.signal.sort_publishers_by_rating.emit()

        data = fetch_data()

        if not data:
            return

        self.publishers = {}
        delete_previous(self)

        for count, i in enumerate(data):
            publisher_id = i[DB.comics.publisher_id]

            if publisher_id not in self.publishers:
                get_and_add_publisher_data(self, publisher_id)

            if publisher_id in self.publishers:
                add_volume_issue_count(self, i, publisher_id)

            if count+1 == len(data) or data[count+1][DB.comics.publisher_id] != publisher_id:

                if t.config('dev_mode'): # redrawing later in fn:post_drawing_publishers_sorting
                    if sort_by_name or sort_by_amount or sort_by_rating:
                        continue

                self.signal.drawpublisher.emit(publisher_id)

        post_drawing_publishers_sorting(self)

class TOOLPublisher(POPUPTool):

    def create_publisher_widget(self):
        """
        makes a TITLE thats makes the entire widget movable, under the title there's a scrollarea
        there all publishers will be show. each publisher is checked to comicvine servers and
        refreshed if nessesary resulting in there may be some lag while drawing them. THEREFORE
        sorting publishers event doesnt happen until AFTER they're all drawn to achieve the effect
        that they'll be drawn one and one when refreshed because sorting is not really possible
        until we know all names!
        """
        title = 'PUBLISHERS'
        self.publisher_widget = PUBtoVOLtoISSUEScroll(self.main.back, self.main, parent=self, title=title)
        self.publisher_widget.title.draw_sorting_menus(publishers=True)

        if t.config('p_sort_name' + title):
            wa = (True,)
        elif t.config('p_sort_count' + title):
            wa = (False, True,)
        elif t.config('p_sort_rating' + title):
            wa = (False, False, True,)
        else:
            wa = (False, False, False,) # silly i know, but it works

        t.start_thread(self.publisher_widget.show_publishers, name='comicvine', threads=1, worker_arguments=wa)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.create_publisher_widget()

        else:
            signal = t.signals('kill_publisher_widget', delete_afterwards=True)
            signal.finished.emit()

class TOOLFolders(POPUPTool):
    def create_browser_widget(self):
        title = 'ALL FILES AND FOLDERS'
        self.browser_widget = PUBtoVOLtoISSUEScroll(
            self.main.back, self.main, parent=self, title=title, killsignal='kill_browser_widget', width=700)
        self.browser_widget.sort_label.close()
        cycle = [
            dict(conf='comic_folder', key=1, files=[]),
            dict(conf='NSFW_folder', key=2, files=[]),
            dict(conf='magazine_folder', key=3, files=[])
        ]

        self.browser_widget.base_folders = []
        for dictionary in cycle:
            folders = t.config(dictionary['conf'])
            if not folders:
                continue

            for i in folders:
                if os.path.exists(i):
                    self.browser_widget.base_folders.append(i)

        self.browser_widget.base_folders.sort()

        for folder in self.browser_widget.base_folders:
            self.browser_widget.signal.drawfolder.emit(dict(path=folder, root=True))

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.create_browser_widget()

        else:
            signal = t.signals('kill_browser_widget', delete_afterwards=True)
            signal.finished.emit()

class TOOLSort(POPUPTool):
    def show_sorting_tools(self):

        d1 = [
            dict(
                text='SORT FILE NAME', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                kwargs=dict(
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
            dict(
                text='SORT BY NUMBER', textsize=TEXTSIZE, post_init=True,
                widget=HighlightRadioBoxGroup,
                tooltip='can easially result in bad experience when mixing paired and unpaired comics',
                kwargs=dict(
                    signalgroup='sort_modes_group',
                    type='sort_by_number', )
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
                dict(object=self.button, background=BTN_SHINE, color=BTN_SHINE),
            ]

            self.directives['deactivation'] = [
                dict(object=self.textlabel, color=BTN_SHADE),
                dict(object=self.button, background=BTN_SHADE, color=BTN_SHADE),
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
                text='SHOW YOUR HIGHEST RATED VOLUMES', textsize=TEXTSIZE,
                widget=self.ShowAllRated, button_width_factor=2.5, post_init=True,
                text_color='gray', button_color='darkCyan',
                kwargs=dict(type='all_volumes_with_rated_issue', extravar=dict(
                    killswitch=self.killswitch
                ))
            ),
            dict(
                text='SHOW THOSE WITH UNREAD ISSUES', textsize=TEXTSIZE,
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
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.move(1,1)
        self.set_position()
        self.activation_toggle(save=False)
        self.how_much_is_the_fish()
        t.set_my_pixmap(self)

    def how_much_is_the_fish(self):
        if not self.activated:
            self.main.showMaximized()
        else:
            self.main.showNormal()

    def set_position(self):
        t.pos(self, right=dict(left=self.main.quitter), x_margin=1)

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle()
        if ev.button() == 1:
            self.how_much_is_the_fish()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        pass

class TOOLQuit(POPUPTool):
    def __init__(self, place, type=None):
        super().__init__(place, type=type)
        self.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        t.set_my_pixmap(self)
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

class TOOLComicvine(POPUPTool):
    class APIKey(FolderSettingsAndGLobalHighlight):
        def post_init(self):
            self.manage_delete_button(create=True, text="")
            self.delete_button.setToolTip('delete API key')
            self.delete_button.mousePressEvent = self.delete_cv_key

            key = t.config(self.type, curious=True)

            if type(key) == str:
                self.lineedit.setText('X' * len(key))

            self.lineedit.textChanged.connect(self.text_changed)

        def text_changed(self):
            text = self.lineedit.text().strip()

            if not text:
                self.manage_save_button(delete=True)

            elif text.lower().find('bruce wayne') != -1:
                key = t.config(self.type, curious=True)
                if type(key) == str and key.lower().find('bruce wayne') == -1:
                    self.lineedit.setText(key)

            elif not self.manage_save_button(create=True, text='SAVE'):
                self.save_button.mousePressEvent = self.save_api_key

        def save_api_key(self, *args, **kwargs):
            text = self.lineedit.text().strip()

            if len(text) > 30 and text.find(' ') == -1:
                t.save_config(self.type, text)
                self.lineedit.setText('API KEY SAVED!')
                self.manage_save_button(delete=True)

        def delete_cv_key(self, *args, **kwargs):
            t.save_config(self.type, None, delete=True)

    class Scan50(GLOBALDeactivate, ExecutableLookCheckable):
        def post_init(self):
            self.button.setMouseTracking(True)
            self.textlabel.setMouseTracking(True)

            self.directives['activation'] = [
                dict(object=self.textlabel, color='white'),
                dict(object=self.button, background=BTN_SHINE, color=BTN_SHINE),
            ]

            self.directives['deactivation'] = [
                dict(object=self.textlabel, color=BTN_SHADE),
                dict(object=self.button, background=BTN_SHADE, color=BTN_SHADE),
            ]
        def special(self):
            return True

        def start_next_job(self, first_run=False):
            if not first_run:

                if 'suggested_candidate' in dir(self.infowidget):
                    if 'cycle' in dir(self.infowidget.suggested_candidate):
                        sqlite_id = self.infowidget.database[0]
                        self.diffdata[sqlite_id] = self.infowidget.suggested_candidate.cycle

                self.infowidget.quit()

            ready = [(dict(database=x['database'], usable=None, used=False, count=0)) for x in self.que if x['active']]
            if ready:
                self.main.draw_list_comics = ready
                self.main.draw_from_comiclist()

                for i in self.que:
                    i['active'] = False

            for i in self.que:
                if not i['used']:
                    i['active'] = True
                    i['used'] = True

                    signalname = 'infowidget_signal_' + str(i['database'][0])
                    self.signal = t.signals(signalname, reset=True)
                    self.signal.autopair_complete.connect(self.start_next_job)

                    from bscripts.infowidget import INFOWidget
                    self.infowidget = INFOWidget(
                        self.main.back, self, self.main, type='info_widget', database=i['database'], scan50=True)

                    break

            t.start_thread(
                self.main.dummy, worker_arguments=1, threads=1, name='diffdata', finished_function=self.show_diffdata)

        def show_diffdata(self):
            for dbid, cycle in self.diffdata.items():
                for i in self.main.widgets['main']:
                    if i.database[0] != dbid:
                        continue

                    if 'diffdata' in dir(i):
                        continue

                    i.diffdata = []
                    for d in cycle:
                        text = d['text']
                        value = round(d['value'] * 100)
                        if not value:
                            continue

                        if not i.diffdata:
                            label = t.pos(new=i, width=i.cover, height=i.height() * 0.05, bottom=i.cover, left=i.cover)
                            label.setText(text)
                            label.fontsize = t.correct_broken_font_size(label)
                            w = label.fontMetrics().boundingRect(label.text()).width()
                            t.pos(label, width=w * 2.4)
                            prelabel = label
                        else:
                            prelabel = i.diffdata[-1]
                            label = t.pos(new=i, coat=prelabel, above=prelabel, y_margin=1)
                            label.setText(text)

                        i.diffdata.append(label)

                        rlabel = t.pos(new=label, inside=label, width=label, sub=3)
                        rlabel.setAlignment(QtCore.Qt.AlignRight)
                        rlabel.setText(str(value) + '%')

                        t.style(label,
                                background='rgba(20,20,20,210)', color='rgb(180,180,190)', font=i.diffdata[0].fontsize)
                        t.style(rlabel, background='transparent', color='gray', font=i.diffdata[0].fontsize)

                        label.setFrameShape(QtWidgets.QFrame.Box)
                        label.setLineWidth(1)

                    header = t.pos(new=i, coat=label, height=label, add=10, above=label, y_margin=2)
                    t.style(header, background='rgba(20,20,20,210)', color='rgb(180,180,190)')
                    header.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
                    header.setFrameShape(QtWidgets.QFrame.Box)
                    header.setLineWidth(2)

                    for d in cycle:
                        if d['text'] == 'TOTAL':
                            if t.config('comicvine_autopair_threshold'):
                                if d['value'] * 100 >= t.config('comicvine_autopair_threshold'):
                                    header.setText('AUTO-PAIRED')
                                    break

                            header.setText('PROPOSED ONLY')

                    t.correct_broken_font_size(header)

        def button_clicked(self):
            data = sqlite.execute('select * from comics where comic_id is null and type is 1', all=True)
            random.shuffle(data)
            if data:
                que_amount = t.config('scan_50_now') or 10
                #self.que = [dict(used=False, database=x, active=False) for count, x in enumerate(data) if count < que_amount]
                self.diffdata = {}
                self.main.reset_widgets('main')
                self.que = []
                for i in data:
                    if os.path.exists(i[DB.comics.local_path]):
                        self.que.append(dict(used=False, database=i, active=False))
                    if len(self.que) >= que_amount:
                        break

                self.start_next_job(first_run=True)

        def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
            self.activation_toggle()
            self.button_clicked()

    def show_cv_settings(self):
        self.blackgray = UniversalSettingsArea(self.main)

        d1 = [
            dict(
                text='API KEY',
                widget=self.APIKey,
                shrink_to_text=True,
                settingscanvas=self.blackgray,
                multiple_folders=False,
                hide_button=True,
                alignment=True,
                kwargs=dict(
                    type='comicvine_key',
                )
            )
        ]
        d2 = [
            dict(
                text='SUGGEST COMICVINE ID',
                tooltip='tries the filename and first page color data against comicvine servers',
                textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight,
                post_init=True,
                kwargs=dict(
                    type='comicvine_suggestion'
                )),
            dict(
                text='SHOW CANDIDATE DETAILS',
                tooltip='theres some data based on the suggestions, this data is shown on the cover of the suggestion, some may find this annoying',
                textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight,
                post_init=True,
                kwargs=dict(
                    type='comicvine_show_suggestion_details'
                )),
        ]

        d3 = [
            dict(
                text='AUTOPAIR THRESHOLD',
                tooltip='if this matchrate is meet the comic is paired directly without notice and interaction',
                textsize=TEXTSIZE,
                widget=CheckableLCD,
                max_value=100,
                min_value=1,
                post_init=True,
                kwargs=dict(
                    type='comicvine_autopair_threshold',
                )),
        ]
        d4 = [
            dict(
                text='LOWER THRESHOLD',
                tooltip='lowest matchrate percentage to make such suggestion',
                textsize=TEXTSIZE,
                max_value=100,
                min_value=1,
                kwargs=dict(
                    type='comicvine_lower_threshold'
                )),
        ]

        d5 = [
            dict(
                text='AUTOPAIR NEW COMICS',
                tooltip='makes sense to do less than 50 at the time since comicvine servers will scream at you if you pull from them to offen (will only try unpaired)',
                textsize=TEXTSIZE,
                widget=self.Scan50,
                post_init=True,
                kwargs=dict(
                    type='_scan_50_now'
                )),
        ]

        header = self.blackgray.make_header(title='COMICVINE')
        set1 = self.blackgray.make_this_into_folder_settings(d1)
        set2 = self.blackgray.make_this_into_checkable_buttons(d2, canvaswidth=330)
        set3 = self.blackgray.make_this_into_checkable_button_with_LCDrow(d3, canvaswidth=330)
        set4 = self.blackgray.make_this_into_LCDrow(d4, canvaswidth=330)
        set5 = self.blackgray.make_this_into_checkable_buttons(d5, canvaswidth=270)

        t.pos(set1, below=header, y_margin=3)
        t.pos(set2, below=set1, y_margin=5)
        t.pos(set3, below=set2, y_margin=5)
        t.pos(set5, below=set3, y_margin=5)
        t.pos(set4, below=set5, y_margin=5)

        # todo lazy fix, not nessesary to fix but this is very ugly codewise >
        d6 = [
            dict(
                text='',
                textsize=TEXTSIZE,
                max_value=100,
                min_value=1,
                kwargs=dict(
                    type='scan_50_now'
                )),
        ]
        set6 = self.blackgray.make_this_into_LCDrow(d6, canvaswidth=330)
        t.pos(set6, top=set5, right=set4)
        tmp = t.pos(new=set5, background='black', width=2, height=set5, right=set5)
        t.pos(new=tmp, size=[2, 1], move=[0, 1], background='gray')
        t.pos(new=tmp, size=[2, 1], move=[0, tmp.height()-2], background='gray')
        set5.raise_()
        # todo lazy fix, not nessesary to fix but this is very ugly codewise <

        t.pos(self.blackgray, under=self, move=[10,10])
        self.blackgray.expand_me([x for x in self.blackgray.blackgrays])


    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.show_cv_settings()

        elif 'blackgray' in dir(self):
            self.blackgray.close()
            del self.blackgray

class TOOLCVIDnoID(GOD):

    def __init__(self, place, *args, **kwargs):
        super().__init__(place)
        t.style(self, background='transparent', color='transparent')

    def post_init(self):
        class ShowNotShow(HighlightRadioBoxGroup):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.activation_toggle(save=False)

            def create_button(self):
                self.button = GOD(self, type=self.type)
                t.pos(self.button, inside=self, margin=1)
                self.textlabel = QtWidgets.QLabel(self)
                self.textlabel.hide()

        w = self.width() / 3 - 2
        paired = ShowNotShow(self, type='show_paired', signalgroup='pair_no_pair')
        paired.setToolTip('show ONLY tagged comics')
        unpaired = ShowNotShow(self, type='show_unpaired', signalgroup='pair_no_pair')
        unpaired.setToolTip('show ONLY untagged comics')
        both = ShowNotShow(self, type='show_both', signalgroup='pair_no_pair')
        both.setToolTip('show both tagged and untagged comics')

        self.labels = []

        for i in [paired, unpaired, both]:
            if not self.labels:
                t.pos(i, width=w, height=self, right=self.width())
            else:
                t.pos(i, coat=self.labels[-1], before=self.labels[-1], x_margin=1)
            i.create_button()
            i.post_init()
            self.labels.append(i)
            i.labels = self.labels

        self.labels[-1].fall_back_to_default(self.labels, 'show_both')

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
                widget=CheckableAndGlobalHighlight,
                post_init=True,
                kwargs=dict(
                    type='webp_4kdownsize'
            )),
            dict(
                text='MAKE MD5 FILE',
                tooltip='for PDF to CBZ conversions there wont be any individual file sums because those wont offer any usefull data',
                textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight,
                post_init=True,
                kwargs=dict(
                    type='webp_md5file'
            )),
            dict(
                text='DELETE SPAM',
                tooltip='be cautious, this will remove what it thinks is spam, not what you think is spam!',
                textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight,
                post_init=True,
                kwargs=dict(
                    type='delete_spam'
                )),
            dict(
                text='DELETE SOURCE',
                textsize=TEXTSIZE,
                widget=CheckableAndGlobalHighlight,
                post_init=True,
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

