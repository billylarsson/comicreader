from bscripts.database_stuff import sqlite
import time
import platform
from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint
from bscripts.file_handling       import generate_cover_from_image_file
from bscripts.file_handling       import hash_all_unhashed_comics
from bscripts.file_handling       import scan_for_new_comics
from bscripts.tricks              import tech as t
from script_pack.settings_widgets import CheckBoxSignalGroup
from script_pack.settings_widgets import CheckableAndGlobalHighlight
from script_pack.settings_widgets import POPUPTool
from script_pack.settings_widgets import CheckableLCD, ExecutableLookCheckable
from script_pack.settings_widgets import FolderSettingsAndGLobalHighlight
from script_pack.settings_widgets import GLOBALDeactivate
from script_pack.settings_widgets import HighlightRadioBoxGroup
from script_pack.settings_widgets import UniversalSettingsArea
from script_pack.preset_colors import *
import os
import sys
from PyQt5                        import QtCore, QtGui, QtWidgets
from PyQt5.QtCore                 import QPoint, Qt
from PyQt5.QtGui                  import QColor, QKeySequence, QPen, QPixmap
from bscripts.database_stuff import DB, sqlite
from bscripts.comicvine_stuff import comicvine
from script_pack.settings_widgets import GOD

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
    def __init__(self, place, child, title, killsignal):
        super().__init__(place)
        self.child = child
        self.killsignal_name = killsignal
        self.sort_label = GOD(place)
        self.child.sort_label = self.sort_label
        t.pos(self, size=[300,30], move=[30,30])
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
                        self.show_publishers(sort_by_name=True, refresh=False)

                    elif volumes:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_volumes(sort_by_name=True, refresh=False)

        class SortCount(SortRadio):
            def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
                if ev.button() == 1:
                    if publishers:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_publishers(sort_by_amount=True, refresh=False)

                    elif volumes:
                        self.enslave_me_signal.deactivate.emit(self.type)
                        self.show_volumes(sort_by_amount=True, refresh=False)

        class SortRating(SortRadio):
            pass

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

    def default_event_colors(self):
        self.directives['activation'] = [
            dict(object=self, color=TXT_SHINE, background='rgb(20,20,20)'),
        ]

        self.directives['deactivation'] = [
            dict(object=self, color=TXT_SHADE, background='rgb(10,10,10)'),
        ]

class BrowseFile(CVIDFileBrowse):
    pass

class BrowseVolume(CVIDFileBrowse):
    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.main.search_comics(highjack=self.data['issues'])

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
            t.start_thread(
                self.volume_widget.show_volumes,
                name='comicvine',
                threads=1,
                worker_arguments=(True,),
            )
        elif t.config('p_sort_count' + title):
            t.start_thread(
                self.volume_widget.show_volumes,
                name='comicvine',
                threads=1,
                worker_arguments=(False,True,),
            ) # todo fix start_thread
        else:
            t.start_thread(
                self.volume_widget.show_volumes,
                name='comicvine',
                threads=1,
            )

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
    def __init__(self, place, main, parent, title, killsignal='kill_publisher_widget'):
        super().__init__(place)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.parent = parent
        self.scrollarea = self
        self.backplate = self.BackPlate(place=self, parent=self, main=main)
        self.pubs = self.backplate.pubs
        self.vols = self.backplate.vols
        self.setWidget(self.backplate)
        self.title = TITLE(main.back, child=self, title=title, killsignal=killsignal)
        t.pos(self, width=self.title, below=self.title, y_margin=5)

        self.killsignal = t.signals(killsignal)
        self.killsignal.finished.emit() # close any previous dupe
        self.killsignal.finished.connect(self.killswitch)

        self.signal = t.signals('PVI_show_this' + title, reset=True)
        self.signal.drawpublisher.connect(self.backplate.draw_publisher)
        self.signal.drawvolume.connect(self.backplate.draw_volume)
        self.signal.sort_publishers_by_name.connect(self.reorganize_publishers_by_name)
        self.signal.sort_publishers_by_amount.connect(self.reorganize_publishers_by_amount)
        self.signal.sort_volumes_by_name.connect(self.reorganize_volumes_by_name)
        self.signal.sort_volumes_by_amount.connect(self.reorganize_volumes_by_amount)

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

        def standard_positioning(self, object, container):
            if not container:
                t.pos(object, size=[300,30])
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


        def draw_volume(self, data):
            volume_id = data['volume_id']
            volume_name = data['volume_name']

            p = BrowseVolume(self, type='_vol' + str(volume_id), data=data, main=self.main, text=volume_name)

            self.standard_positioning(p, self.vols)

        def draw_publisher(self, publisher_id):
            pub = self.parent.publishers[publisher_id]
            p = BrowsePublisher(
                self, type='_pub' + str(publisher_id), data=pub, main=self.main, text=pub['publisher_name'])

            self.standard_positioning(p, self.pubs)


    def show_volumes(self, sort_by_name=False, sort_by_amount=False, refresh=True):
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

        if not refresh:
            if sort_by_name:
                self.signal.sort_volumes_by_name.emit()
            elif sort_by_amount:
                self.signal.sort_volumes_by_amount.emit()
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
                if sort_by_name or sort_by_amount:
                    emit_later.append(d)
                    continue

            self.signal.drawvolume.emit(d)

        if emit_later: # dev_mode
            if sort_by_name:
                volumes_quick_by_name(self, emit_later)
            elif sort_by_amount:
                volumes_quick_by_amount(self, emit_later)

        elif sort_by_name:
            self.reorganize_volumes_by_name()
        elif sort_by_amount:
            self.reorganize_volumes_by_amount()

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
        freezestop = t.keep_track(name='reorgvols', restart=True)
        while len(self.vols) != len(self.data['volumes']) and freezestop.runtime < 5:
            pass

        tmp = [(x.data['volume_name'], x,) for x in self.vols]
        self.sort_and_stack_under_each_others(tmplist=tmp)

    def reorganize_volumes_by_amount(self):
        freezestop = t.keep_track(name='reorgvols', restart=True)
        while len(self.vols) != len(self.data['volumes']) and freezestop.runtime < 5:
            pass

        tmp = [(len(x.data['issues']), x,) for x in self.vols]
        tmp.sort(key=lambda x:x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=tmp, sorted=True)

    def reorganize_publishers_by_name(self):
        freezestop = t.keep_track(name='reorgpubs', restart=True)
        while len(self.pubs) != len(self.publishers) and freezestop.runtime < 5:
            pass

        tmp = [(x.data['publisher_name'], x,) for x in self.pubs]
        self.sort_and_stack_under_each_others(tmplist=tmp)

    def reorganize_publishers_by_amount(self):
        freezestop = t.keep_track(name='reorgpubs', restart=True)
        while len(self.pubs) != len(self.publishers) and freezestop.runtime < 5:
            pass

        tmp = [(len(x.data['volumes']), x,) for x in self.pubs]
        tmp.sort(key=lambda x: x[0], reverse=True)
        self.sort_and_stack_under_each_others(tmplist=tmp, sorted=True)


    def show_publishers(self, sort_by_name=False, sort_by_amount=False, refresh=True):
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

        def check_sort_by_name_post(self):
            if sort_by_name:
                if t.config('dev_mode'):
                    publishers_quick_by_name(self)
                else:
                    self.signal.sort_publishers_by_name.emit()

        def check_sort_by_amount_post(self):
            if sort_by_amount:

                if t.config('dev_mode'):
                    publishers_quick_by_amount(self)
                else:
                    self.signal.sort_publishers_by_amount.emit()

        if not refresh:
            if sort_by_name:
                self.signal.sort_publishers_by_name.emit()

            elif sort_by_amount:
                self.signal.sort_publishers_by_amount.emit()

            return

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

                # will redraw later down the line, quicker experience but can appear frozen therefore its a dev thingey
                if t.config('dev_mode'):
                    if sort_by_name or sort_by_amount:
                        continue

                self.signal.drawpublisher.emit(publisher_id)

        check_sort_by_name_post(self)
        check_sort_by_amount_post(self)


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
        self.main.shadehandler()
        title = 'PUBLISHERS'
        self.publisher_widget = PUBtoVOLtoISSUEScroll(self.main.back, self.main, parent=self, title=title)
        self.publisher_widget.title.draw_sorting_menus(publishers=True)

        if t.config('p_sort_name' + title):
            t.start_thread(
                self.publisher_widget.show_publishers,
                name='comicvine',
                threads=1,
                worker_arguments=(True,),
            )
        elif t.config('p_sort_count' + title):
            t.start_thread(
                self.publisher_widget.show_publishers,
                name='comicvine',
                threads=1,
                worker_arguments=(False,True,),
            ) # todo fix start_thread
        else:
            t.start_thread(self.publisher_widget.show_publishers, name='comicvine', threads=1)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.create_publisher_widget()

        else:
            signal = t.signals('kill_publisher_widget', delete_afterwards=True)
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
        x = self.main.back.geometry().top() - 2
        t.pos(self, size=(60, x,), right=self.main.quitter.geometry().left(), x_margin=2)

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
        header = self.blackgray.make_header(title='COMICVINE')
        set1 = self.blackgray.make_this_into_folder_settings(d1)
        t.pos(set1, below=header, y_margin=3)
        t.pos(self.blackgray, under=self, move=[10,10])
        self.blackgray.expand_me([x for x in self.blackgray.blackgrays])


    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.activation_toggle(save=False)

        if self.activated:
            self.show_cv_settings()

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
                text='DELETE SPAM',
                tooltip='be cautious, this will remove what it thinks is spam, not what you think is spam!',
                textsize=TEXTSIZE,

                kwargs=dict(
                    type='delete_spam'
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


# class POPUPTool(GLOBALDeactivate):
#     def __init__(self, place, *args, **kwargs):
#         super().__init__(place=place, *args, **kwargs)
#
#         self.directives['activation'] = [
#             dict(object=self, background='rgba(200,50,50,150)'),
#         ]
#
#         self.directives['deactivation'] = [
#             dict(object=self, background=TXT_DARKTRANS),
#         ]
#
#         self.activation_toggle(force=False, save=False)
#         self.setAcceptDrops(True)
#         self.setMouseTracking(True)
#
#     def dragEnterEvent(self, ev):
#         if ev.mimeData().hasUrls() and len(ev.mimeData().urls()) == 1:
#             file = ev.mimeData().urls()[0]
#             file = file.path()
#             if os.path.isfile(file):
#                 splitter = file.split('.')
#                 if splitter[-1].lower() in {'webp', 'jpg', 'jpeg', 'png', 'gif'}:
#                     ev.accept()
#         return
#
#
#     def dropEvent(self, ev):
#         if ev.mimeData().hasUrls() and ev.mimeData().urls()[0].isLocalFile():
#             if len(ev.mimeData().urls()) == 1:
#                 ev.accept()
#
#                 files = []
#
#                 for i in ev.mimeData().urls():
#                     t.tmp_file('pixmap_' + self.type, hash=True, extension='webp', delete=True)
#                     t.tmp_file(i.path(),              hash=True, extension='webp', delete=True)
#
#                     tmp_nail = generate_cover_from_image_file(
#                         i.path(), store=False, height=self.height(), width=self.width())
#
#                     files.append(tmp_nail)
#
#                 for c in range(len(files)-1,-1,-1):
#                     with open(files[c], 'rb') as f:
#                         files[c] = f.read()
#
#                 if files:
#                     t.save_config(self.type, files, image=True)
#                     t.set_my_pixmap(self)



# class TOOLSettings(POPUPTool):
#     def trigger_settingswidget(self):
#         if self.activated:
#             self.create_reusable_settingswidget()
#             self.main.settings.move(100, 100)
#
#         elif 'settings' in dir(self.main):
#             self.main.settings.close()
#             del self.main.settings
#
#
#     def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#         self.activation_toggle(save=False)
#         self.trigger_settingswidget()
#
#     def create_reusable_settingswidget(self):
#         """
#         creates a large settingsarea and then makes three smaller
#         settingsboxes inside that area and places them around for
#         more indepth about the how-to see UniversalSettingsArea
#         """
#         class FillRowSqueeze(CheckBoxSignalGroup, CheckableAndGlobalHighlight):
#             def special(self):
#                 if self.type == 'squeeze_mode':
#                     return False
#
#                 if not t.config('squeeze_mode') and self.activated:
#                     t.style(self.button, background='orange')
#                     return True
#
#             def checkgroup_signal(self, signal):
#                 if self.type == 'fill_row' and signal == 'squeeze_mode':
#                     self.activation_toggle(force=self.activated, save=False)
#
#             def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#                 if ev.button() == 1:
#                     self.activation_toggle()
#                     self.signalgroup.checkgroup_master.emit(self.type)
#
#         class PATHExtenders(FolderSettingsAndGLobalHighlight):
#             def special(self):
#                 if self.activated:
#                     rv = t.config(self.type, curious=True)
#
#                     if rv and type(rv) == list:
#                         t.style(self.button, background='green')
#                     else:
#                         t.style(self.button, background='orange')
#                 else:
#                     t.style(self.button, background='gray')
#                 return True
#
#             def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#                 if ev.button() == 1:
#                     self.activation_toggle()
#
#         dict_with_checkables = [
#             dict(
#                 text="SHOW COMICS", textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='else excluding files marked as Comics',
#                 kwargs = dict(type='show_comics'),
#             ),
#             dict(
#                 text='SHOW MAGAZINES', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='else excluding files marked as Magazines',
#                 kwargs = dict(type='show_magazines'),
#
#             ),
#             dict(
#                 text='SHOW NSFW', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='else excluding files marked as porn',
#                 kwargs = dict(type='show_NSFW')
#             ),
#             dict(
#                 text='SQUEEZE MODE', textsize=TEXTSIZE,
#                 widget=FillRowSqueeze, post_init=True,
#                 tooltip='contract/expand covers until they claim all space in full rows (looks good, but only tries to honor aspekt ratio)',
#                 kwargs = dict(signalgroup='squeeze_fill_group', type='squeeze_mode'),
#             ),
#             dict(
#                 text='FILLING ROW', textsize=TEXTSIZE,
#                 widget=FillRowSqueeze, post_init=True,
#                 tooltip='exceeding limit until row is full, requires Squeeze Mode (looks better)',
#                 kwargs = dict(signalgroup='squeeze_fill_group', type='fill_row'),
#             ),
#             dict(
#                 text='COVER BLOB', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='stores thumbnails into database (100x faster loading speed next time you browse the same item at the cost of increasing local databse by ~25kb per item (depending on thumbnail size))',
#                 kwargs = dict(type='cover_blob'),
#             ),
#             dict(
#                 text='COVERS PRE-DRAW', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='show covers when prepositioning covers (takes a millisecond per item on a good computer)',
#                 kwargs = dict(type='pre_squeeze')
#             ),
#             ]
#
#         dict_with_lcdrow = [
#             dict(
#                 text='COVER HEIGHT', textsize=TEXTSIZE,
#                 kwargs = dict(type='cover_height')),
#             dict(
#                 text='BATCH SIZE', textsize=TEXTSIZE,
#                 kwargs = dict(type='batch_size')),
#         ]
#
#         dict_with_paths = [
#             dict(
#                 text='COMICS FOLDER', textsize=TEXTSIZE,
#                 tooltip='CBZ files',
#                 widget=FolderSettingsAndGLobalHighlight,
#                 kwargs = dict(type='comic_folder')),
#             dict(
#                 text='MAGAZINES', textsize=TEXTSIZE,
#                 widget=FolderSettingsAndGLobalHighlight,
#                 tooltip='regular magazines folder ...',
#                 kwargs = dict(type='magazine_folder')),
#             dict(
#                 text='NSFW FOLDER', textsize=TEXTSIZE,
#                 tooltip='found a mouse ...',
#                 widget=FolderSettingsAndGLobalHighlight,
#                 kwargs=dict(type='NSFW_folder')),
#             dict(
#                 text='CACHE FOLDER', textsize=TEXTSIZE,
#                 widget=FolderSettingsAndGLobalHighlight,
#                 tooltip='must exist! (else fallback to systems-tmp)',
#                 kwargs = dict(type='cache_folder', multiple_folders=False)),
#         ]
#
#         dict_with_cover_details = [
#             dict(
#                 text='RATING', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 kwargs = dict(type='show_ratings')),
#             dict(
#                 text='READING PROGRESS', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip="shows a progress bar from left to right according to the current highest pagenumber you've opened",
#                 kwargs = dict(type='show_reading_progress')),
#             dict(
#                 text='PAGES AND SIZE', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 kwargs = dict(type='show_page_and_size')),
#             dict(
#                 text='UNTAGGED FLAG', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='if we cannot find a comicvine id with this file, a small square is positioned in the upper right corner indicating that',
#                 kwargs = dict(type='show_untagged_flag')
#             )
#         ]
#
#         full_shade = [
#             dict(
#                 text='SHADE SURROUNDINGS', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='when you study or read an issue, all surroudings are darkley shaded, looks good.',
#                 kwargs = dict(type='shade_surroundings')),
#         ]
#         class DEVMODE(CheckableAndGlobalHighlight):
#
#             def special(self):
#                 if self.activated:
#                     t.style(self.button, background='pink')
#                     t.style(self.textlabel, color='pink')
#                 else:
#                     t.style(self.button, background='gray')
#                     t.style(self.textlabel, color='gray')
#
#                 return True
#
#             def default_event_colors(self):
#                 self.directives['activation'] = [
#                     dict(object=self.textlabel, color='lightBlue'),
#                     dict(object=self.button, background='lightBlue', color='pink'),
#                 ]
#
#                 self.directives['deactivation'] = [
#                     dict(object=self.textlabel, color='gray'),
#                     dict(object=self.button, background='gray', color='gray'),
#                 ]
#
#             def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#                 self.activation_toggle()
#                 sqlite.dev_mode = self.activated
#
#         dev_mode = [
#             dict(
#                 text='DEVELOPER FEATURES', textsize=TEXTSIZE,
#                 shrink_to_text=True,
#                 widget=DEVMODE, post_init=True,
#                 tooltip='source code explains',
#                 kwargs = dict(type='dev_mode')),
#         ]
#
#         dict_with_pdf_things = [
#             dict(
#                 text = 'PDF SUPPORT', textsize=TEXTSIZE, widget=PATHExtenders,
#                 tooltip = "this may not be a plesent experience since it depends on poppler path. if your'e on windows, i'd say you doomed if you dont know what you're doing and i suggest you leave this in the red",
#                 kwargs = dict(type='pdf_support', multiple_folders=False)),
#         ]
#
#         dict_with_unpackers = [
#             dict(
#                 text = 'WinRAR', textsize=TEXTSIZE, widget=PATHExtenders,
#                 tooltip = "if you're on windows and want CBR file support you need to either have WinRAR.exe in you systems path or provide it here",
#                 kwargs = dict(type='winrar_support', multiple_folders=False)),
#             dict(
#                 text='7-Zip', textsize=TEXTSIZE, widget=PATHExtenders,
#                 tooltip="alternative to WinRAR",
#                 kwargs=dict(type='zip7_support', multiple_folders=False)),
#         ]
#
#         dict_with_autoupdate = [
#             dict(
#                 text = 'LIBRARY AUTOUPDATE', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip = "autoupdates on start and when you close settings panel",
#                 kwargs = dict(type='autoupdate_library')),
#         ]
#
#         dict_update_hash = [
#             dict(
#                 text='SCAN FOR NEW FILES', textsize=TEXTSIZE, button_width_factor=2.2,
#                 button_color='darkCyan', text_color='gray', post_init=True,
#                 widget=self.UpdateLibrary, button_text='',
#                 tooltip='updates library in the background',
#                 kwargs = dict(type='_update_library')),
#         ]
#
#         dict_parse_for_cvid = [
#             dict(
#                 text='PARSE UNPARSED FILES', textsize=TEXTSIZE, button_width_factor=2.2,
#                 button_color='darkCyan', text_color='gray', post_init=True,
#                 widget=self.HashUnHashed, button_text='',
#                 tooltip='iters all unitered comics for comicvine id (comictagger), we do this once per file as long as MD5 is checked (thats how we track such event for now, if MD5 is not checked all files will be processed next time again, and again, and again...)',
#                 kwargs = dict(type='_parse_unparsed')),
#         ]
#
#         dict_md5_comic = [
#             dict(
#                 text='HASH MD5 FROM NEW FILES', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='first time an item is to be shown to user an MD5 checksum is initiated and stored into database, this is conveniet when keeping track of multiple files and sharing ratings with friends',
#                 kwargs = dict(type='md5_files')),
#
#             dict(
#                 text='SEARCH ZIP FOR CVID', textsize=TEXTSIZE,
#                 widget=CheckableAndGlobalHighlight, post_init=True,
#                 tooltip='searches the file contents for comicvine id (comictagger)',
#                 kwargs = dict(type='comictagger_file'))
#         ]
#
#         self.main.settings = UniversalSettingsArea(self.main, type='settings', activation_toggle=self.activation_toggle)
#
#         blackgray1 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_checkables, canvaswidth=250)
#         blackgray2 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_cover_details, canvaswidth=250)
#         blackgray3 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_paths)
#         blackgray4 = self.main.settings.make_this_into_LCDrow(headersdictionary=dict_with_lcdrow, canvaswidth=250)
#         blackgray5 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_pdf_things)
#         blackgray5_1 = self.main.settings.make_this_into_folder_settings(headersdictionary=dict_with_unpackers)
#         blackgray6 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_update_hash, canvaswidth=300)
#         blackgray7 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_md5_comic)
#         blackgray8 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_with_autoupdate)
#         blackgray9 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=full_shade)
#         blackgray10 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dev_mode)
#         blackgray11 = self.main.settings.make_this_into_checkable_buttons(headersdictionary=dict_parse_for_cvid, canvaswidth=300)
#
#         header = self.main.settings.make_header(title='SETTINGS')
#
#         t.pos(blackgray2, below=blackgray1, y_margin=10)
#         t.pos(blackgray6, after=blackgray1, x_margin=10)
#         t.pos(blackgray3, below=blackgray6, left=blackgray6, y_margin=10)
#         t.pos(blackgray4, below=blackgray2, y_margin=10)
#         t.pos(blackgray5, left=blackgray3, below=blackgray3, y_margin=10)
#         t.pos(blackgray5_1, left=blackgray3, below=blackgray5, y_margin=10)
#         t.pos(blackgray8, left=blackgray5, below=blackgray5_1, y_margin=10)
#         t.pos(blackgray7, below=blackgray8, y_margin=10, left=blackgray8)
#         t.pos(blackgray9, below=blackgray4, y_margin=10)
#         t.pos(blackgray10, below=blackgray9, y_margin=10)
#         t.pos(blackgray11, after=blackgray6, x_margin=10)
#
#         t.pos(header, right=blackgray3, bottom=blackgray6)
#
#         self.main.settings.expand_me(self.main.settings.blackgrays)
#
#         signal = t.signals(self.type, reset=True)
#         signal.activated.connect(self.before_close_event)
#
#     def before_close_event(self):
#         if not self.activated and t.config('autoupdate_library'):
#             t.start_thread(scan_for_new_comics, name='update_library', threads=1)
#
#     class UpdateLibrary(GLOBALDeactivate, ExecutableLookCheckable):
#         def __init__(self, *args, **kwargs):
#             super().__init__(*args, **kwargs)
#             self.activation_toggle(force=False)
#
#         def post_init(self):
#             self.button.setMouseTracking(True)
#             self.textlabel.setMouseTracking(True)
#
#             self.directives['activation'] = [
#                 dict(object=self.textlabel, color='white'),
#                 dict(object=self.button, background='cyan', color='cyan'),
#             ]
#
#             self.directives['deactivation'] = [
#                 dict(object=self.textlabel, color='gray'),
#                 dict(object=self.button, background='darkCyan', color='darkCyan'),
#             ]
#
#         def special(self):
#             return True
#
#         def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#             if self.running_job: # jobs running
#                 return
#
#             self.slaves_can_alter = False
#             self.running_job = True
#             self.start_job(signalgroup='updating_library_job')
#             t.start_thread(scan_for_new_comics,
#                            finished_function=self.jobs_done, name='update_library', threads=1, worker_arguments=False)
#
#     class HashUnHashed(GLOBALDeactivate, ExecutableLookCheckable):
#         def __init__(self, *args, **kwargs):
#             super().__init__(*args, **kwargs)
#             self.activation_toggle(force=False)
#
#         def post_init(self):
#             self.button.setMouseTracking(True)
#             self.textlabel.setMouseTracking(True)
#
#             self.directives['activation'] = [
#                 dict(object=self.textlabel, color='white'),
#                 dict(object=self.button, background='cyan', color='cyan'),
#             ]
#
#             self.directives['deactivation'] = [
#                 dict(object=self.textlabel, color='gray'),
#                 dict(object=self.button, background='darkCyan', color='darkCyan'),
#             ]
#
#         def special(self):
#             return True
#
#         def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
#             if self.running_job: # jobs running
#                 return
#
#             self.running_job = True
#             self.start_job(signalgroup='hash_unhashed_job')
#             t.start_thread(
#                 hash_all_unhashed_comics,
#                 finished_function=self.jobs_done,
#                 name='long_time', threads=1
#             )
