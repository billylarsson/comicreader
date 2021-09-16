# from PyQt5                        import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore                 import QPoint, Qt
# from PyQt5.QtGui                  import QColor, QKeySequence, QPen, QPixmap
# from PyQt5.QtWidgets              import QShortcut
# from bscripts.database_stuff      import DB, sqlite
# from bscripts.file_handling import extract_from_zip_or_pdf
# from bscripts.tricks              import tech as t
# from script_pack.settings_widgets import GOD
# import os
# import pathlib
# import sys
# from bscripts.comic_drawing import ComicWidget
#
# class INFOWidget(GOD):
#     def __init__(self, place, parent, main, type, database):
#         super().__init__(place=place, main=main, type=type)
#         self.parent = parent
#         self.database = database
#         esc = QShortcut(QKeySequence(Qt.Key_Escape), self)
#         esc.activated.connect(self.quit)
#         self.post_init()
#
#     def set_pixmap(self):
#         path = extract_from_zip_or_pdf(database=self.database)
#
#         if not path:
#             return False
#
#         cover_height = t.config('cover_height')
#         pixmap = QPixmap(self.path).scaledToHeight(cover_height)
#
#         if pixmap.width() > cover_height * 3:
#             pixmap = QPixmap(self.path).scaled(cover_height, cover_height * 3)
#
#     def post_init(self):
#         print(self.main.back.geometry())
#         self.set_pixmap()
#
#     def quit(self):
#         self.close()