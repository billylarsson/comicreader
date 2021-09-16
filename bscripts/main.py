from PyQt5                   import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore            import QPoint, Qt
from PyQt5.QtGui             import QKeySequence
from PyQt5.QtWidgets         import QShortcut
from bscripts.comic_drawing  import ComicWidget
from bscripts.database_stuff import DB, sqlite
from bscripts.file_handling import scan_for_new_comics
from bscripts.tricks         import tech as t
from bscripts.widgets        import TOOLBatch, TOOLDev
from bscripts.widgets        import TOOLMaxiMini, TOOLQuit, TOOLReading
from bscripts.widgets        import TOOLSearch, TOOLSettings, TOOLSort,TOOLRank,TOOLWEBP
import os
import sys
import time

class LSComicreaderMain(QtWidgets.QMainWindow):
    def __init__(self):
        super(LSComicreaderMain, self).__init__()
        uic.loadUi('./gui/main_v4.ui', self)
        self.setWindowTitle('Comicreader Longsnabel v0.0.1')
        t.style(self, name='main')
        self.widgets = dict(main=[], info=[])
        self.draw_list_comics = []
        # TRIGGERS >
        self.draw_more_from_comiclist = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.draw_more_from_comiclist.activated.connect(self.draw_from_comiclist_spacebar)
        # TRIGGERS <
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.qgrip = QtWidgets.QSizeGrip(self, styleSheet='background-color:rgba(0,0,0,0)')
        self.resize(1920, 1280)

        if t.config('autoupdate_library'):
            t.start_thread(scan_for_new_comics, name='update_library', threads=1)

        self.show()

        self.create_tool_buttons()
        self.devmode(sleep=20)


    def devmode(self, sleep):
        if not 'devmode' in sys.argv:
            return

        def dum():
            if sleep and type(sleep) == int:
                for count in range(sleep, -1, -1):
                    time.sleep(1)
                    self.quitter.clear()
                    self.quitter.setText(str(count))

        def import_db():
            import sqlite3
            import copy
            old_db = sqlite3.connect('/home/plutonergy/Documents/Comicreader/comicreader_database.sqlite')
            old_cur = old_db.cursor()
            old_cur.execute('select * from comics')
            data = old_cur.fetchall()
            query, org_values = sqlite.empty_insert_query('comics')
            execute_many = []
            for i in data:
                values = copy.copy(org_values)
                values[DB.comics.local_path] = i[13]
                values[DB.comics.volume_id] = i[1]
                values[DB.comics.comic_id] = i[7]
                values[DB.comics.rating] = i[2]
                values[DB.comics.publisher_id] = i[16]
                values[DB.comics.issue_number] = i[10]
                values[DB.comics.type] = 1
                execute_many.append(tuple(values))

            sqlite.execute(query, execute_many)





        def kill():
            if 'fuck_this_duck' in dir(self):
                if self.fuck_this_duck == -1:
                    return

                del self.fuck_this_duck
                t.start_thread(dum, finished_function=kill, name="dfucker")
                print("RESTARTING KILL TIMER")
            else:
                print("KILLING AFTER:", sleep, 'seconds')
                sys.exit()

        print("STARTING TIMER:", sleep, 'seconds')
        #self.le_primary_search.setText("adult collection")
        self.search_comics()
        #import_db()
        t.start_thread(dum, finished_function=kill, name="dfucker")
        # from bscripts.file_handling import concurrent_cbx_to_webp_convertion
        # t.start_thread(concurrent_cbx_to_webp_convertion)

    def create_tool_buttons(self):
        """
        creates the buttons that are visible on the bar
        """
        dlist = [
            dict(config='tool_searcher', widget=TOOLSearch, widthmultiplyer=1),
            dict(config='tool_settings', widget=TOOLSettings, widthmultiplyer=1),
            dict(config='tool_sorter', widget=TOOLSort, widthmultiplyer=1),
            dict(config='tool_reader', widget=TOOLReading, widthmultiplyer=1),
            dict(config='tool_dev', widget=TOOLDev, widthmultiplyer=1),
            dict(config='tool_webp', widget=TOOLRank, widthmultiplyer=1),
            dict(config='tool_ranking', widget=TOOLWEBP, widthmultiplyer=1),
            dict(config='tool_batch', widget=TOOLBatch, widthmultiplyer=1),

        ]

        for count, d in enumerate(dlist):
            conf = d['config']
            widget = d['widget']

            label = widget(self, type=conf)

            d.update(dict(label=label))

            if count == 0:
                x = self.back.geometry().top() - 2
                t.pos(label, size=(x, x,), move=(1, 1,))
                label.show_searchwidget()

            else:
                prelabel = dlist[count - 1]['label']
                if count == 1:
                    t.pos(label, coat=prelabel, rightof=self.le_primary_search, x_margin=1)
                else:
                    t.pos(label, coat=prelabel, rightof=prelabel, x_margin=1)
                    t.pos(label, width=label.width() * d['widthmultiplyer'])

            t.set_my_pixmap(label)

        self.quitter = TOOLQuit(self, type='quit_button')
        self.minmax = TOOLMaxiMini(self, main=self, type='minimaxi')


    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        # this is the grip that resizes the window
        if 'qgrip' in dir(self):
            self.qgrip.setGeometry(self.width()-30, self.height() - 30, self.width(), 30)

        if 'quitter' in dir(self):
            self.quitter.set_position()

        if 'minmax' in dir(self):
            self.minmax.set_position()

    def dummy(self, sleep=0):
        if sleep and type(sleep) == int:
            time.sleep(sleep)
        else:
            return True

    def save_search_query(self):
        text = self.le_primary_search.text().strip()
        t.save_config('last_query', text)

    def filter_all_comics(self):
        """
        includes the comics of your search query and NSFW/PDF settings
        :return: list
        """
        text = self.le_primary_search.text().strip()
        comics = sqlite.execute('select * from comics', all=True)

        if not comics and t.config('autoupdate_library'):
            scan_for_new_comics()
            comics = sqlite.execute('select * from comics', all=True)

        results = t.uni_search(comics, text, DB.comics.local_path)
        results = t.uni_sort(results)
        return results

    def show_rated_volumes(self):
        v_dict = {}
        rv_dict = {}

        data = sqlite.execute('select * from comics where volume_id is not NULL', all=True)
        data.sort(key=lambda x:x[DB.comics.volume_id])
        for i in data:

            if i[DB.comics.volume_id] not in v_dict:
                v_dict.update({i[DB.comics.volume_id]: []})

            v_dict[i[DB.comics.volume_id]].append(i)

        for eachvol, eachlist in v_dict.items():
            eachlist = t.uni_sort(eachlist)

            if not eachlist:
                continue

            tmp = []
            rateiter = 0

            if t.config('only_volumes_with_unread_issue'):
                data = [i for i in eachlist if not i[DB.comics.rating]]
                if not data:
                    continue # at least one unrated (unread) comic needed to pass test

            for i in eachlist:
                if i[DB.comics.rating] != None:
                    tmp.append(i[DB.comics.rating])

            for count in tmp:
                rateiter += count

            try: rv_dict[eachlist[0]] = rateiter / len(tmp)
            except ZeroDivisionError: rv_dict[eachlist[0]] = 0
            except IndexError: pass

        rv_dict = {k: v for k, v in sorted(rv_dict.items(), key=lambda item: item[1], reverse=True)}

        self.draw_list_comics = []

        for count, i in enumerate(rv_dict):
            self.draw_list_comics.append(dict(database=i, usable=None, used=False, count=count))

        if self.draw_list_comics:
            self.reset_widgets('main')
            self.batcher.stop_drawing(reset=True)
            self.draw_from_comiclist()

    def search_comics(self):
        """
        makes a dictionary with jobs that are passed along to draw engine
        """
        self.save_search_query()
        results = self.filter_all_comics()

        if results:
            self.le_primary_search.clearFocus()
            self.draw_list_comics = []

            for count, i in enumerate(results):
                self.draw_list_comics.append(dict(database=i, usable=None, used=False, count=count))

            self.reset_widgets('main')
            self.batcher.stop_drawing(reset=True)
            self.draw_from_comiclist()

    def reset_widgets(self, widgets=None, all=False):
        """
        closes and pops items inside self.widgets['widgets']
        :param widgets: key
        :param all: closes and pops everything inside self.widgets
        """
        def close_and_pop(self, key):
            for count in range(len(self.widgets[key]) -1, -1, -1):
                self.widgets[key][count].close()
                self.widgets[key].pop(count)

        for key in self.widgets:
            if all or key == widgets:
                close_and_pop(self, key)

        if widgets == 'main' and 'status' in dir(self.batcher):
            self.batcher.status.close()
            del self.batcher.status


    def get_wt_ht(self, key='main'):
        """
        returns width taken and height taken AND:
        NEW Width + NEW Height if you need new row
        :param key: self.widgets['key']
        :return: tuple
        """
        wt = 1 # width taken
        ht = 1 # height taken
        nw = 1 # next approved width
        nh = 1 # next approved height

        for count in range(len(self.widgets[key]) - 1, -1, -1):
            widget = self.widgets[key][count]
            if widget.geometry().top() >= ht: # height taken
                ht = widget.geometry().top()

                if widget.geometry().right() > wt: # width taken
                    wt = widget.geometry().right() + 2

                if widget.geometry().bottom() > nh: # next height
                    nh = widget.geometry().bottom() + 2

        return wt, ht, nw, nh

    def get_repositioned(self, key='main'):
        """
        iters self.widgets['key'] and returns
        all that ARE NOT .setGeometry() yet
        :param key: string
        :return: list with widgets that are to be set
        """
        rv = []
        for count in range(len(self.widgets[key]) - 1, -1, -1):
            widget = self.widgets[key][count]
            if not widget.repositioned:
                rv.append(widget)
        if rv:
            rv.reverse()

        return rv

    def resize_scrollcanvas(self):
        wt,ht,nw,nh = self.get_wt_ht()
        if self.scrollcanvas_main.height() != nh:
            self.scrollcanvas_main.setMinimumSize(self.scrollcanvas_main.width(), nh)

    def cleanup_batch_status(self):
        def shrink_text_size(self):
            for count in range(24,5,-1):
                t.style(self.batch_status, font=str(count) + 'pt')
                self.batch_status.show()
                w = self.batch_status.fontMetrics().boundingRect(self.batch_status.text()).width()
                h = self.batch_status.fontMetrics().boundingRect(self.batch_status.text()).height()
                if self.batcher.height() >= h + 2 or count == 6:
                    t.pos(self.batch_status, width=w, height=self.batcher)
                    break

        def create_new_batch_status_label(self):
            if 'batch_status' not in dir(self):
                self.batch_status = t.pos(new=self, coat=self.batcher, rightof=self.batcher)

        def deal_with_failed(self, failed):
            if failed:
                print("HEY!, you forgot faild:", failed)
                for i in [x for x in self.draw_list_comics if x['usable'] == False and not x['used']]:
                    print(i)

        drawn = len([x for x in self.draw_list_comics if x['used']])
        faild = len([x for x in self.draw_list_comics if x['usable'] == False and not x['used']])
        total = len(self.draw_list_comics)

        create_new_batch_status_label(self)
        self.batch_status.setText(f" SHOWING {drawn} of {total} ")
        shrink_text_size(self)
        deal_with_failed(self, faild)
        self.batcher.set_current_position()

    def draw_comics_cleanup(self):
        """
        cleanupstep that shows the pixmap for all
        comics that are'nt yet showing a cover, show counter
        """
        for i in self.widgets['main']:
            t.start_thread(self.dummy, finished_function=[
                i.cover.set_pixmap, i.make_box_of_details, self.resize_scrollcanvas
            ])

        self.cleanup_batch_status()

    def check_if_usable_is_legal(self, db_dictionary):
        """
        alters the dictionary and sets the usable=bool accordingly
        usable being if the file it self exists and if its the corret
        extension (you dont want PDF, PDF files are returned as unusable)
        :param db_dictionary: dict(database, usable, used...)
        :return:
        """

        if not self.batcher.check_if_database_is_within_range(db_dictionary['count']):
            return False

        if db_dictionary['usable'] == None: # meaning this is the first time we se this db_dictionary
            db_dictionary['usable'] = os.path.exists(db_dictionary['database'][DB.comics.local_path])

        if db_dictionary['usable'] and not t.config('pdf_support'): # exclude or include PDF-files
            loc = t.separate_file_from_folder(db_dictionary['database'][DB.comics.local_path])
            if loc.ext.lower() == 'pdf':
                db_dictionary['usable'] = False

        if db_dictionary['usable']: # final check, if database appears in self.widgets['main'] returns False
            for i in self.widgets['main']:
                if i.database == db_dictionary['database']:
                    db_dictionary['usable'] = False # no longer usable
                    db_dictionary['used'] = True # already been used
                    break

        return db_dictionary['usable']

    def draw_from_comiclist_spacebar(self):
        """
        pressing spacebar draws another batch.
        batch size is reset and drawing start
        """
        self.batcher.stop_drawing(reset=True)
        self.draw_from_comiclist()

    def draw_from_comiclist(self):
        """
        always goes threw the entire list and askes
        fn:check_if_usable_is_legal for True or False
        """
        for i in self.draw_list_comics:

            if not self.check_if_usable_is_legal(i):
                continue

            self.draw_this_comic(i['database'])
            return

        self.draw_comics_cleanup()

    def within_batch_range(self):
        """
        if batchs-size is reached either we finnish
        drawing the rest of the row or we goto cleanup
        :return: bool
        """
        if self.batcher.stop_drawing():
            if t.config('fill_row'):
                self.fill_row()
            else:
                self.draw_comics_cleanup()
            return False # jobs done
        return True # carry on

    def draw_this_comic(self, database):
        """
        first asks if within batch range, then draw :param database
        :param database: db_tuple
        :return: if batch done, else thread goes again
        """
        if not self.within_batch_range():
            return # jobs done

        widget = ComicWidget(self.scrollcanvas_main, self, 'comic')
        self.widgets['main'].append(widget)
        widget.database = database
        widget.repositioned = False
        widget.post_init()
        widget.make_cover(cover_height=t.config('cover_height'))
        widget.set_position()
        t.start_thread(self.dummy, finished_function=self.draw_from_comiclist)

    def fill_row(self, floodlimit=20):
        """
        this means that batch size is exceeding to fill the entire row
        the floodlimit is for dev purposes so that we dont do a thousand without stop
        :param floodlimit: int
        """
        for i in self.draw_list_comics:
            if not self.check_if_usable_is_legal(i):
                continue

            self.fill_row_with_this_comic(i['database'], floodlimit=floodlimit)
            break

    def check_if_all_are_positioned(self):
        """
        returns True if there are widgets that are'nt yet positioned correctly
        :return: bool
        """
        wlist = self.get_repositioned()
        if not wlist:
            self.draw_comics_cleanup()
            return True

    def check_if_widget_made_it_into_same_row(self, widget):
        """
        if widget made it into the same row, return True
        else: we close and pop it and returns False
        :param widget: object
        :return: bool
        """
        if widget.set_position():
            for count, i in enumerate(self.widgets['main']):
                if i == widget:
                    widget.close()
                    self.widgets['main'].pop(count)
                    self.draw_comics_cleanup()
                    return False
        return True

    def fill_row_with_this_comic(self, database, floodlimit):
        """
        this is part of something a bit complicated that seems to be working
        :param database: db_tuple
        :param floodlimit: int
        :return: if jobs good, else thread goes again
        """
        if self.check_if_all_are_positioned():
            return True

        else: # we make a new widget an stick it with the others

            widget = ComicWidget(self.scrollcanvas_main, self, 'comic')
            self.widgets['main'].append(widget)
            widget.database = database
            widget.repositioned = False
            widget.post_init()
            widget.make_cover(cover_height=t.config('cover_height'))

            if not self.check_if_widget_made_it_into_same_row(widget):
                return True # last widget ended up in a new row, we pop it and jobs done

            elif not t.config('squeeze_mode') or floodlimit < 1:
                self.draw_comics_cleanup()
                return True

            else: # thread goes on

                t.start_thread(self.dummy, finished_function=self.fill_row, finished_arguments=(floodlimit - 1))

    def mouseMoveEvent(self, event):
        if event.button() == 2 or 'old_position' not in dir(self):
            return

        delta = QPoint(event.globalPos() - self.old_position)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_position = event.globalPos()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() == 1:
            self.old_position = ev.globalPos()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        if 'old_position' in dir(self):
            del self.old_position
