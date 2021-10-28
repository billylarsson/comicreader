from sqlalchemy      import create_engine, inspect
from sqlalchemy.pool import SingletonThreadPool, StaticPool
import copy
import os
import pathlib
import platform
import sys

class SQLite:
    def __init__(self, INI_FILENAME, INI_FILE_DIR, DATABASE_FILENAME, DATABASE_FOLDER, DATABASE_SUBFOLDER):
        """
        this is trying to get all sqlite reads and writes into a single
        class with a single thread, columns are stored in self.techdict
        :param INI_FILENAME: filename only (not full path)
        :param INI_FILE_DIR: direct string or __file__ from folder where ini will be
                        loaded/created (__file__ is user friendly, therefore used)
        :param DATABASE_FOLDER: ie /home/user/Documents (ignored if not exists)
        :param DATABASE_SUBFOLDER: ie COOLPROGRAM (ignored if not PARENT_DIRECTORY not exists)
        :param DATABASE_FILENAME: my_program.sqlite
        """
        # ------------------------------------ #
        self.INI_FILE          = INI_FILENAME
        self.INI_DIR           = INI_FILE_DIR
        self.NEW_APP_DIR       = DATABASE_SUBFOLDER
        self.PARENT_DIRECTORY  = DATABASE_FOLDER
        self.DATABASE_FILENAME = DATABASE_FILENAME
        self.INI_FULL_PATH     = os.path.abspath(os.path.expanduser(self.INI_DIR + self.INI_FILE))
        # ------------------------------------ #
        self.techdict = {}
        self.dev_mode = False
        # ------------------------------------ #
        self.engine = None
        # ------------------------------------ #
        self.init_connection_and_cursor()

    def init_connection_and_cursor(self):
        """
        changes the directory to the same as the file is run and looks for settings.ini
        such will be created if non exists and a row will be created with the path to the sqlite file
        a settings table will be created i use row 1 for that, so only one should ever be created
        if something isnt working, hard exit will be make sys.exit()
        """
        def get_db_folder_and_filename(local_path):
            """
            :param local_path must be full path including filename
            :return: object.string: full_path, db_folder, filename
            """
            class LOCATIONS:
                full_path = local_path
                if platform.system() != "Windows":
                    tmp_full_path = local_path.split('/')
                    filename = tmp_full_path[-1]
                    tmp_full_path.pop(-1)
                    db_folder = '/'.join(tmp_full_path)
                else:
                    tmp_full_path = local_path.split('\\')
                    filename = tmp_full_path[-1]
                    tmp_full_path.pop(-1)
                    db_folder = '\\'.join(tmp_full_path)

            return LOCATIONS

        def make_nessesary_folders(local_path):
            """
            makes proper subfolders
            :param local_path must be full path including filename
            """
            if not os.path.exists(local_path):
                loc = get_db_folder_and_filename(local_path)
                if loc.db_folder and not os.path.exists(loc.db_folder):
                    pathlib.Path(loc.db_folder).mkdir(parents=True)

        def ini_file_creation(self, force=False):
            """
            :param force: bool, if True INI_FILE will be overwritten
            """
            if not os.path.exists(self.INI_FULL_PATH) or force:
                with open(self.INI_FULL_PATH, 'w') as f:
                    db_file = self.DATABASE_FILENAME

                    if os.path.exists(self.PARENT_DIRECTORY):
                        if self.NEW_APP_DIR:
                            full_db_path = f'{self.PARENT_DIRECTORY}/{self.NEW_APP_DIR}/{db_file}'
                        else:
                            full_db_path = f'{self.PARENT_DIRECTORY}/{db_file}'
                    else:
                        full_db_path = db_file

                    full_db_path = os.path.abspath(os.path.expanduser(full_db_path))
                    f.write(f'local_database = "{full_db_path}"\n')
                    make_nessesary_folders(full_db_path)

                    f.close()

        def load_database(self):
            """
            iter each row from INI_FILE until it find both: 'local_database'
            AND 'sqlite' then loads the database and checks if table settings
            is preset or creates an empty settings-table
            :return: bool
            """
            with open(self.INI_FULL_PATH, 'r') as f:
                database_location = list(f)

                for row in database_location:
                    for database, dbdict in databases.items():

                        if len(row) < len(database):
                            continue

                        if database != 'local_database' or row[0:len(database)] != database:
                            continue

                        path_split = row.split('"')
                        local_path = [x for x in path_split if x.find('sqlite') > -1]

                        if not local_path:
                            return False

                        loc = get_db_folder_and_filename(local_path[0])

                        if not os.path.exists(loc.db_folder):
                            return False

                        if not os.path.exists(loc.full_path):
                            try:
                                pathlib.Path(loc.full_path).touch()
                                if os.path.exists(loc.full_path):
                                    try:
                                        os.remove(loc.full_path)
                                    except:
                                        print('Failed to modify:', loc.full_path)
                                        sys.exit()
                            except:
                                print('Failed to write:', loc.full_path)
                                sys.exit()

                        self.engine = create_engine('sqlite:///' + loc.full_path, connect_args=
                        dict(check_same_thread=False), poolclass=SingletonThreadPool)

                        try:
                            self.engine.execute('select * from settings where id is 1')
                        except:
                            query_one = 'create table settings (id INTEGER PRIMARY KEY AUTOINCREMENT)'
                            query_two = 'insert into settings values(?)'

                            try:
                                self.engine.execute(query_one)
                                self.engine.execute(query_two, (None,))
                            except:
                                print('SQLite table creation error!')
                                sys.exit()
                        finally:
                            return True

        databases = dict(
            local_database=dict(
                connection=self.engine, alchemy=True),
        )

        ini_file_creation(self)
        if not load_database(self):
            ini_file_creation(self, force=True)
            if not load_database(self):
                print('HARD QUIT!')
                sys.exit()

    def refresh_db_input(self, table, db_input=None, id=None):
        if db_input and len(db_input) > 0:
            id = db_input[0]
        elif not id:
            id = db_input

        rv = self.execute('select * from ' + table + ' where id is (?)', values=id, one=True)
        return rv

    def execute(self, query, values=None, one=False, all=False, autocommit=False):

        if query[0:len('select')].lower() == 'select':
            with self.engine.connect() as connection:
                if values:
                    data = connection.execute(query, values)
                else:
                    data = connection.execute(query)

            if all:
                return data.fetchall()
            elif data or one: # defaults to one
                return data.fetchone()
        else:
            if autocommit:
                with self.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
                    if values:
                        result = connection.execute(query, values)
                    else:
                        result = connection.execute(query)
            else:
                with self.engine.connect() as connection:
                    if values:
                        result = connection.execute(query, values)
                        self.dev_mode_print(query, values)
                    else:
                        result = connection.execute(query)

            return result.lastrowid

    def empty_insert_query(self, table):
        query = 'PRAGMA table_info("' + str(table,) + '")'
        tables = self.engine.execute(query)
        tables = [x for x in tables]
        query_part1 = "insert into " + table + " values"
        query_part2 = "(" + ','.join(['?'] * len(tables)) + ")"
        values = [None] * len(tables)

        return query_part1 + query_part2, values

    def sqlite_superfunction(self, connection, table, column, type):
        """
        if table isnt found one will be created for you, same is true for columns
        :param connection: sqlite3 connection (can be a string, this is for techdict key)
        :param table: string
        :param column: string
        :param type: string, integer, float
        :return: integer
        """
        if connection not in self.techdict:
            self.techdict.update({connection: { }})
        if table not in self.techdict[connection]:
            self.techdict[connection].update({table : { }})

        insp = inspect(connection)
        tables = insp.get_table_names()

        if table not in tables:
            query_create_new_table = 'create table ' + table + ' (id INTEGER PRIMARY KEY AUTOINCREMENT)'
            connection.execute(query_create_new_table)

        columns = insp.get_columns(table)

        for count, row in enumerate(columns):
            if row['name'] not in self.techdict[connection][table]:
                self.techdict[connection][table].update({row['name'] : count})

        if column in self.techdict[connection][table]:
            return self.techdict[connection][table][column]
        else:
            query_create_new_column = 'alter table ' + table + ' add column ' + column + ' ' + type.upper()
            connection.execute(query_create_new_column)
            return len(columns)

    def db_sqlite(self, table, column, type='text'):
        """
        close to unnessesary, but when you have a ton of DB.things it actually helps
        """

        return self.sqlite_superfunction(self.engine, table, column, type)

    def dev_mode_print(self, query, values, hide_bytes=True):
        if not self.dev_mode:
            return

        if type(values) == bytes and hide_bytes:
            print('SQLITE event QUERY:', query, ':::BYTES:::')

        elif type(values) == list or type(values) == tuple and hide_bytes:
            proxyvalues = copy.copy(values)
            proxyvalues = list(proxyvalues)
            for count in range(len(proxyvalues)):
                if type(proxyvalues[count]) == bytes:
                    proxyvalues[count] = ':::BYTES:::'
            print('SQLITE event QUERY:', query, proxyvalues)

        else:
            print('SQLITE event QUERY:', query, values)
