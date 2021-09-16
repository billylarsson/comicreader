import pathlib
from PIL                    import Image
from pdf2image              import convert_from_path, pdfinfo_from_path
from bscripts.database_stuff import DB, sqlite
from bscripts.tricks         import tech as t
from zipfile                import BadZipFile, ZipFile
import copy
import concurrent.futures
import platform
import os
import pickle
import rarfile
import shutil
import time

def extract_from_zip_or_pdf(file=None, database=None, index=0):
    if not file and database:
        file = database[DB.comics.local_path]

    if not file:
        return False

    rv = check_for_pdf_assistance(pdf_file=file, index=index)
    if not rv:
        rv = unzipper(zip_file=file, database=database, index=index)

    return rv

def unzipper(zip_file=None, database=None, index=0, filename=None):
    """
    if filename:
        then everything else is overridden, filename extracted and returned
    else:
        unpacks the index from the zip_file
        if not database, a database input will be created
        also if database and database doesnt have any file_contents
        the database/file is indexed and database updated

    :param zip_file: string
    :param database: db(tuple)
    :param index: int(page)
    :param extract_location: string full path
    :return: extract location or False
    """
    def hack_unrar(rarobject, rarinfo, destination_path):

        def helper(name, flags):
            return os.open(name, flags)

        with rarobject.open(rarinfo, 'r') as src:
            with open(destination_path, 'wb', opener=helper) as dst:
                shutil.copyfileobj(src, dst)

    def generate_file_to_extract(filedictionary, index):
        good_files = filedictionary['good_files']
        bad_files = filedictionary['bad_files']
        all_files = good_files + bad_files
        good_files.sort()

        if index < len(good_files):
            return good_files[index], good_files, bad_files, all_files
        else:
            return False, good_files, bad_files, all_files

    files_in_the_zip = 1000
    file_to_extract = None


    if zip_file and filename:
        loc_source = t.separate_file_from_folder(zip_file)
        file_to_extract = filename

    elif database:
        loc_source = t.separate_file_from_folder(database[DB.comics.local_path])
        if not database[DB.comics.file_contents]:
            fa = FileArchiveManager(database=database, autoinit=False)
            fa.make_database(path=loc_source.full_path)
            database = fa.database

        if not database[DB.comics.file_contents]:
            return False

        fd = pickle.loads(database[DB.comics.file_contents])
        file_to_extract, good_files, bad_files, all_files = generate_file_to_extract(fd, index)
        files_in_the_zip = len(good_files)

    elif zip_file:
        loc_source = t.separate_file_from_folder(zip_file)
        fa = FileArchiveManager(path=zip_file)
        filecontents = fa.list_archive(path=loc_source)
        if filecontents:
            fd = fa.separate_files(filecontents)
            file_to_extract, good_files, bad_files, all_files = generate_file_to_extract(fd, index)
            files_in_the_zip = len(good_files)

        if not filecontents:
            return False

    if not file_to_extract:
        return False

    extract_folder = t.tmp_folder(loc_source.full_path, hash=True, reuse=True)
    extract_file = t.zero_prefiller(index, len(str(files_in_the_zip)))

    ext = file_to_extract.split('.')
    ext = ext[-1]

    loc_destination = t.separate_file_from_folder(extract_folder + '/' + extract_file + '.' + ext)

    if os.path.exists(loc_destination.full_path) and os.path.getsize(loc_destination.full_path) > 0:
        return loc_destination.full_path

    try:
        zf = ZipFile(loc_source.full_path)
        single_file = zf.getinfo(file_to_extract)
        single_file.filename = loc_destination.filename
        zf.extract(single_file, loc_destination.folder)

    except BadZipFile:

        try:
            rf = rarfile.RarFile(loc_source.full_path)
            single_file = rf.getinfo(file_to_extract)
            hack_unrar(rf, single_file, loc_destination.full_path)

        except rarfile.NotRarFile:
            return False
        except rarfile.BadRarFile:
            return False
        except:
            return False
    except:
        return False
    finally:
        if not os.path.exists(loc_destination.full_path):
            return False
        elif os.path.getsize(loc_destination.full_path) == 0:
            os.remove(loc_destination.full_path)
            return False

    return loc_destination.full_path

def generate_cover_from_image_file(path,
                                   database=None,
                                   store=False,
                                   width=None,
                                   height=None,
                                   quality=70,
                                   method=6,
                                   delete=True
                                   ):
    """
    opens the file generate a thumbnail according to params and stores it in database
    :param path: string
    :param database: db_tuple
    :param store: bool: as blob in database
    :param width: int
    :param height: int
    :param quality: int
    :param method: int
    :param delete: bool: deletes source
    :return: full_path
    """
    def store_into_database(tmp_file):
        if store and database and not database[DB.comics.cover]:
            with open(tmp_file, 'rb') as file:
                blob = file.read()
                query = 'update comics set cover = (?) where id = (?)'
                sqlite.execute(query, values=(blob, database[0],))

    if database:
        tmp_file = t.tmp_file('thumbnail_id_' + t.zero_prefiller(database[0]), extension='webp', reuse=True)
    else:
        tmp_file = t.tmp_file(path, reuse=True, hash=True, extension='webp')

    if os.path.exists(tmp_file):
        if not os.path.getsize(tmp_file):
            os.remove(tmp_file)
        else:
            store_into_database(tmp_file=tmp_file)

            if delete and os.path.exists(path):
                os.remove(path)

            return tmp_file

    try: image = Image.open(path)
    except FileNotFoundError: return False

    if width and height: # uses the largest
        if height > width:
            width = round(image.size[0] * (height / image.size[1]))
        else:
            height = round(image.size[1] * (width / image.size[0]))
    elif width:
        height = round(image.size[1] * (width / image.size[0]))
    elif height:
        width = round(image.size[0] * (height / image.size[1]))
    else:
        width = image.size[0]
        height = image.size[1]

    image_size = width, height
    image.thumbnail(image_size, Image.ANTIALIAS)
    image.save(tmp_file, 'webp', method=method, quality=quality)

    store_into_database(tmp_file=tmp_file)

    if delete and os.path.exists(path):
        os.remove(path)

    return tmp_file

def blob_image_from_database(database):
    """
    extracts blob image from database an return where its saved
    :param database: db_tuple
    :return: string full_path
    """
    tmpfile = t.tmp_file('thumbnail_id_' + t.zero_prefiller(database[0]), extension='webp', reuse=True)
    loc = t.separate_file_from_folder(tmpfile)
    if not os.path.exists(tmpfile):
        with open(loc.full_path, 'wb') as output_file:
            output_file.write(database[DB.comics.cover])
    return loc.full_path

def check_for_pdf_assistance(pdf_file, index=0, pagecount=False, dry_run=False, pagecheck=True):
    """
    if extension is PDF file and index is to be found in the PDF
    file its extracted and returned as a list with a signle JPEG file.
    if outoutfile exceeds 20mb assuming attack and reprocessing with 100dpi

    :param pagecheck: doesnt check page avilibility befroce extracting
    :param dry_run: returns the filename if tends to use without extracting
    :param pdf_file: string
    :param index: int
    :param cover: bool: resizes the image
    :return: list with single jpeg file
    """
    loc = t.separate_file_from_folder(pdf_file)
    if not loc or not loc.ext.lower() == 'pdf':
        return False

    poppler_path = None # todo poppler!!

    if pagecheck or pagecount:
        rv = pdfinfo_from_path(pdf_file, poppler_path=poppler_path)
        if rv and rv['Pages'] and index < rv['Pages']:
            if pagecount:
                return rv['Pages']
        else:
            return False

    tmp_file = t.tmp_folder(hash=True, reuse=True, folder_of_interest=pdf_file)
    tmp_file += '/' + t.zero_prefiller(index)
    tmp_loc = t.separate_file_from_folder(tmp_file)
    final_jpeg_file = tmp_loc.full_path + '.jpg'

    if dry_run:
        return final_jpeg_file

    if os.path.exists(final_jpeg_file) and os.path.getsize(final_jpeg_file) > 0:
        return final_jpeg_file

    kwargs = dict(
        dpi=200,
        first_page=index,
        last_page=index + 1,
        fmt='jpeg',
        output_file=tmp_loc.filename,
        output_folder=tmp_loc.folder,
        paths_only=True,
        jpegopt=dict(quality=100, optimize=True),
        poppler_path=poppler_path,
        single_file=True,
    )

    image_list = convert_from_path(pdf_file, **kwargs)

    if image_list:
        loc = t.separate_file_from_folder(image_list[0])
        return loc.full_path



def get_thumbnail_from_zip_or_database(zip_file=None, database=None, index=0, proxy=True, store=False, height=300):
    """
    if file already present as file or blob in the databse those are returned
    otherwise this extracts file from index in CBZ or PDF file and generate a
    thumbnail from it. thumbnail can be stored as a blob.
    :param zip_file: string
    :param database: db_tuple
    :param index: int
    :param proxy: todo return premade image
    :param store: as a blob inside db_tuple
    :param height: thumbnail height
    :return: string full_path
    """
    if database and not zip_file:
        zip_file = database[DB.comics.local_path]

    if database and database[DB.comics.cover] != None:
        thumbnail_path = blob_image_from_database(database)
        return thumbnail_path

    jpeg_from_pdf = check_for_pdf_assistance(zip_file, index)
    if jpeg_from_pdf:
        thumbnail_path = generate_cover_from_image_file(
            jpeg_from_pdf, height=height, database=database, store=store)
        return thumbnail_path

    elif zip_file:
        file = unzipper(zip_file=zip_file, database=database, index=index)
        if file and os.path.exists(file):
            thumbnail_path = generate_cover_from_image_file(
                file, height=height, database=database, store=store)
            return thumbnail_path
        elif proxy:
            print("You forgot to code cover-proxy!")

class FileArchiveManager:
    def __init__(self, path=None, database=None, md5=False, autoinit=True):
        if database:
            self.database = database

        if autoinit and path and not database:
            self.make_database(path=path, md5=md5)

    def make_database(self, path, md5=False):
        """
        :param path: string
        :param md5: bool, can be overridden, but True always wins
        """
        loc = t.separate_file_from_folder(path)
        filecontents = self.list_archive(path=loc)

        if not md5:
            md5 = t.config('md5_files') # False argument is overridden by global settings

        if not filecontents:
            return False

        def preparations():
            query, values = sqlite.empty_insert_query(table='comics')
            filedictionary = self.separate_files(filecontents=filecontents)

            values[DB.comics.local_path] = loc.full_path
            values[DB.comics.file_size] = os.path.getsize(loc.full_path)
            values[DB.comics.file_date] = int(os.path.getmtime(loc.full_path))
            values[DB.comics.file_contents] = pickle.dumps(filedictionary)

            return query, values, filedictionary

        def previous_md5_file():
            """
            there can be a len(32).md5 file in the cbz, then use that as md5
            """
            for file in filedictionary['bad_files']:
                parts = file.split('.')

                if parts[-1] == 'md5' and len(parts[0]) == 32:
                    values[DB.comics.md5] = parts[0]

        def make_new_md5():
            if md5 and not values[DB.comics.md5]:
                values[DB.comics.md5] = t.md5_hash_file(loc.full_path)

        def reuse_same_inputs():
            """
            if values[md5] and input found in database, they
            are identical and therefore reuses the same data
            """
            if values[DB.comics.md5]:  # share duplicates values among each others
                check_query = 'select * from comics where md5 = (?)'
                new_values = (values[DB.comics.md5],)

                parent = sqlite.execute(check_query, new_values)
                if parent:
                    for count, value in enumerate(parent):
                        if count > 0 and value:
                            values[count] = value

        def delete_previous_before_inserting():
            if values[0]:
                sqlite.execute('delete from comics where id = (?)', values[0])

        def comic_id_inside_file():
            """
            if sha256xxxxxxxxx.... .md5 its file is unpacked searched for comicvine id
            and the filename is used as md5 without actually checksuming the file
            (you're unsafe and unsure about this files checksum if you are CIA or NASA)
            if ComicInfo.xml in file it will be unpacked and searched for comicvine id
            :return:
            """
            if not values[DB.comics.comic_id] or not values[DB.comics.md5]:

                comic_id, md5 = self.process_found_md5_file(path, filedictionary)

                if not values[DB.comics.md5] and md5:
                    values[DB.comics.md5] = md5
                if not values[DB.comics.comic_id] and comic_id:
                    values[DB.comics.comic_id] = comic_id

            if not values[DB.comics.comic_id]:

                comic_id = self.check_for_comictag(path, filedictionary)

                if comic_id:
                    values[DB.comics.comic_id] = comic_id

        query, values, filedictionary = preparations()
        previous_md5_file()
        make_new_md5()
        reuse_same_inputs()

        if 'database' in dir(self): # soft update
            for count, value in enumerate(self.database):
                if self.database[count]:
                    values[count] = self.database[count]

        comic_id_inside_file()
        delete_previous_before_inserting()
        rowid = sqlite.execute(query, values)

        if rowid:
            values[0] = rowid
            self.database = tuple(values)

    def check_for_comictag(self, path, filedictionary=None):
        """
        :param path: string
        :param filedictionary: dictionary
        :return: None or comicvine id from ComicInfo.xml
        """
        if not t.config('comictagger_file'):
            return None

        if not filedictionary and path:
            filecontents = self.list_archive(path=path)
            if filecontents:
                filedictionary = self.separate_files(filecontents=filecontents)

        if not filedictionary or not filedictionary['bad_files']:
            return None

        for i in filedictionary['bad_files']:
            loc = t.separate_file_from_folder(i)

            if loc.filename.lower() == 'comicinfo.xml':
                xmlfile_location = unzipper(path, filename=i)

                with open(xmlfile_location, 'r', encoding="utf-8") as f:
                    content = list(f)
                    for xml in content:

                        if xml.find('comicvine.gamespot.com') == -1:
                            continue

                        elif xml.find('<Web>') == -1 or xml.find('</Web>') == -1:
                            continue

                        cv_link = xml[xml.find('<Web>') + len('<Web>'):xml.find('</Web>')]

                        if cv_link.rfind('-') != -1:
                            cvid = cv_link[cv_link.rfind('-') + 1:cv_link.rfind('</Web>')]
                            cvid = cvid.replace('/', "").strip()
                            return cvid
        return None


    def process_found_md5_file(self, path, filedictionary=None):
        """
        :param path: string
        :param filedictionary: dictionary
        :return: None, None or comicvine_id, md5-string from sha256xxxxx..... .md5
        """
        if not t.config('comictagger_file'):
            return None, None

        if not filedictionary and path:
            filecontents = self.list_archive(path=path)
            if filecontents:
                filedictionary = self.separate_files(filecontents=filecontents)

        if not filedictionary or not filedictionary['bad_files']:
            return None, None

        for i in filedictionary['bad_files']:
            loc = t.separate_file_from_folder(i)

            if len(loc.filename) == 36 and loc.ext.lower() == 'md5':
                md5_file = unzipper(path, filename=i)

                with open(md5_file, 'r') as f:
                    try: text = list(f)
                    except UnicodeDecodeError:
                        return None, None

                    for ii in text:
                        if ii.find('; comicvine id:') != -1:
                            comic_id_string = ii.replace('; comicvine id:', "")
                            comic_id_string.replace('\n', "")
                            comic_id_string.replace(" ", "")
                            md5 = loc.filename.split('.')
                            return comic_id_string, md5[0]
        return None, None

    def list_archive(self, path=None):

        def read_zipfile(path):
            if not os.path.exists(path):
                return False
            try:
                zf = ZipFile(path)
                fl = list(zf.namelist())
                return fl

            except BadZipFile:
                try:
                    rf = rarfile.RarFile(path)
                    fl = list(rf.namelist())
                    return fl
                except rarfile.NotRarFile:
                    return False
                except rarfile.BadRarFile:
                    return False
                except:
                    return False

        if path:
            loc = t.separate_file_from_folder(path)
            filecontents = read_zipfile(path=loc.full_path)
        elif 'database' in dir(self):
            path = self.database[DB.comics.local_path]
            loc = t.separate_file_from_folder(path)
            filecontents = read_zipfile(path=loc.full_path)
        else:
            filecontents = False

        return filecontents

    def separate_files(self, filecontents):
        bad_files = []
        good_files = []

        extensionlist = {'png', 'jpg', 'bmp', 'gif', 'jpeg', 'webp'}

        for file in filecontents: # separates files from folders and good from bad extensions
            parts = file.split('.')

            if parts[-1].lower() not in extensionlist:
                bad_files.append(file)
                continue
            else:
                good_files.append(file)

        max = 3 # separeates files if less tham max begins with z or if less than max contains the word tag
        for gatechecker in {'z', 'tag'}:
            check = 0
            for times in range(2):
                for count in range(len(good_files) -1, -1, -1):
                    file = good_files[count]
                    parts = file.split('/')

                    if gatechecker == 'z' and parts[-1][0].lower() == gatechecker \
                            or gatechecker == 'tag' and parts[-1].lower().find(gatechecker) > -1:

                        if times == 0:
                            check += 1

                        elif times == 1 and check <= max:
                            bad_files.append(file)
                            good_files.pop(count)

        return dict(good_files=good_files, bad_files=bad_files)

    @staticmethod
    def get_filecontents(database):
        if not database[DB.comics.file_contents]:
            FA = FileArchiveManager(database=database)
            FA.make_database(path=database[DB.comics.local_path])
            database = FA.database

        if not database[DB.comics.file_contents]:
            return False

        fd = pickle.loads(database[DB.comics.file_contents])

        if fd and fd['good_files']:
            return fd['good_files']
        else:
            return False



def scan_for_new_comics(quick=True):
    cycle = [
        dict(conf='comic_folder', key=1, files=[]),
        dict(conf='NSFW_folder', key=2, files=[]),
        dict(conf='magazine_folder', key=3, files=[])
    ]

    white_extensions = {'pdf', 'cbz', 'cbr'}

    for dictionary in cycle:
        folders = t.config(dictionary['conf'])

        if not folders:
            continue

        for folder in folders:
            if not folder or not os.path.exists(folder):
                continue

            for walk in os.walk(folder):
                for file in walk[2]:
                    loc = t.separate_file_from_folder(walk[0] + '/' + file)

                    if loc.ext not in white_extensions:
                        continue

                    dictionary['files'].append(loc.full_path)

    comics = sqlite.execute('select * from comics', all=True)
    query, org_values = sqlite.empty_insert_query('comics')
    many_values = []

    progress = dict(
        start=time.time(),
        last_emit=time.time()-1.1,
        current=0,
        total=0,
        signal=t.signals('updating_library_job')
    )

    tot = [x['files'] for x in cycle]
    for i in tot:
        progress['total'] += len(i)

    def make_sqlite_tuple(file, many_values):
        """
        :param file: string, full_path
        :param many_values: list
        """
        values = copy.copy(org_values)
        values[DB.comics.type] = dictionary['key']
        values[DB.comics.file_size] = os.path.getsize(file)
        values[DB.comics.file_date] = int(os.path.getmtime(file))
        values[DB.comics.local_path] = file

        many_values.append(tuple(values))

    def emit_progress(progress):
        if quick:
            return

        progress['current'] += 1
        if time.time() - progress['last_emit'] > 1:
            progress['signal'].progress.emit(progress)


    for dictionary in cycle:
        for file in dictionary['files']:
            if not comics:
                make_sqlite_tuple(file, many_values)

            for count, i in enumerate(comics):
                if i[DB.comics.local_path] == file:
                    comics.pop(count)
                    break

                elif count+1 == len(comics):
                    make_sqlite_tuple(file, many_values)

            emit_progress(progress)

    if many_values:
        sqlite.execute(query, many_values)

def hash_all_unhashed_comics():
    comics = sqlite.execute('select * from comics where md5 is null', all=True)

    progress = dict(
        start=time.time(),
        last_emit=time.time()-1.1,
        current=0,
        total=len(comics),
        signal=t.signals('hash_unhashed_job'),
        stop=False,
    )

    def emit_progress(progress):
        progress['current'] += 1
        if time.time() - progress['last_emit'] > 1:
            progress['signal'].progress.emit(progress)

    for i in comics:
        if progress['stop']:
            break

        FA = FileArchiveManager(database=i)
        FA.make_database(i[DB.comics.local_path], md5=True)
        emit_progress(progress)

def concurrent_pdf_work(job):
    """
    job consists of a dictionary with file, index and webpfolder
    if the extracted jpeg file or final webp file are already in
    the decided folders, they're not reporcessed. webp quality
    settings are fetched from the gui or fallback to defaults
    :param job: dictionary
    :return: string filename or False
    """

    def pdf_path_and_webp_path(pdf_file):
        """
        makes a request what file location that will be used
        to extract the jpeg file so that the work can be reused.
        decides destinationpath based on dictionarys webpfolder
        index and the naked_filename of source file
        :param pdf_file: string
        :return: source_jpeg, destination_webp
        """
        path = check_for_pdf_assistance(pdf_file=pdf_file, index=pdf_index, dry_run=True, pagecheck=False)
        loc = t.separate_file_from_folder(path)
        final_destination = webpfolder + loc.sep + loc.naked_filename + '.webp'
        return path, final_destination

    def files_already_done():
        if os.path.exists(final_destination) and os.path.getsize(final_destination) > 0:
            if os.path.exists(path):
                os.remove(path)
            return final_destination

    def extract_pdf_file(path):
        """
        :param path: string
        :return: False if something fucked up
        """
        if not os.path.exists(path):
            path = check_for_pdf_assistance(pdf_file=pdf_file, index=pdf_index, pagecheck=False)

        if not path or not os.path.exists(path):
            return False

        return path

    def determine_webp_width_and_quality(path):
        """
        width is needed if we're reducing it to 4k
        :param path: string
        :return: string, int, int
        """
        image = Image.open(path)
        width = image.size[0]
        image.close()

        quality = t.config('webp_quality') or 70
        method = t.config('webp_method') or 6

        return width, quality, method


    pdf_file = job['file']
    pdf_index = job['index']
    webpfolder = job['webpfolder']

    path, final_destination = pdf_path_and_webp_path(pdf_file=pdf_file)

    if files_already_done():
        return final_destination

    path = extract_pdf_file(path)
    if not path:
        return False

    width, quality, method = determine_webp_width_and_quality(path)

    if width > 3840 and t.config('webp_4kdownsize'):
        f = generate_cover_from_image_file(path, width=3840, delete=True, quality=quality, method=method)
    else:
        f = generate_cover_from_image_file(path, width=width, delete=True, quality=quality, method=method)

    if not f:
        return False

    shutil.move(f, final_destination)

    return final_destination

def concurrent_pdf_to_webp_convertion(pdf_file, signalgroup='pdf_to_cbz_and_webp', comicvine_id=None):
    """
    uses all CPU's to convert a PDF to CBZ (webp)
    a signalgroup may be given but not nessesary.
    unpacks JPEG files individually into the default tmp_folder given
    and then converts those into a dedicated working_tmp_folder, then
    zips that folder into a zip file and returns that string in signal
    :param pdf_file: string
    :param signalgroup: string
    :return: pdf_converted_into_webp.cbz (signal.file_delivery.emit( filename ))
    :return: bool
    """

    def check_page_consitency_make_jobfile(pdf_file, progressdict):
        """
        generates the working dictionary, if there's no pagecount job fails
        :param pdf_file: string
        :param progressdict: dictionary
        :return: workinglist with one dictionary per page (job)
        """
        pagecount = check_for_pdf_assistance(pdf_file, pagecount=True)

        if not pagecount:
            return False

        progressdict['total'] = pagecount
        webpfolder = t.tmp_folder(folder_of_interest=pdf_file + 'pdfconvert', reuse=True, hash=True)
        pagelist = [dict(file=pdf_file, index=x, webpfolder=webpfolder) for x in range(pagecount)]

        return pagelist

    signal = t.signals(signalgroup)
    progressdict = dict(start=time.time(), total=0, current=0, last_emit=time.time(), stop=False)
    pagelist = check_page_consitency_make_jobfile(pdf_file, progressdict)

    if not pagelist:
        signal.error.emit(progressdict)
        return False

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(pagelist, executor.map(concurrent_pdf_work, pagelist)):
            if not rv:
                signal.error.emit(progressdict)
                return False

            else:
                progressdict['current'] += 1
                if time.time() - progressdict['last_emit'] > 1:
                    signal.progress.emit(progressdict)

                if progressdict['stop']:
                    signal.stop.emit(progressdict)
                    return False

    def compress_and_remove():
        """
        if theres as many files in the final directory as
        there are pages, its considered a successfull job
        :return: bool (and emits signal)
        """
        def make_md5_file():
            if t.config('webp_md5file'):
                loc_pdf = t.separate_file_from_folder(pdf_file)
                md5 = t.md5_hash_file(pdf_file)
                md5file = loc.folder + loc.sep + md5 + '.md5'
                with open(md5file, 'w') as crc_file:
                    crc_file.write('; original md5: ' + md5 + '\n')
                    crc_file.write('; original filesize in bytes: ' + str(os.path.getsize(pdf_file)) + '\n')
                    crc_file.write('; original filename: ' + loc_pdf.filename + '\n')
                    if comicvine_id:
                        crc_file.write('; comicvine id: ' + str(comicvine_id) + '\n')

        loc = t.separate_file_from_folder(rv)
        for f in os.walk(loc.folder):

            if len(f[2]) == progressdict['total']:
                make_md5_file()

                tmpfile = t.tmp_file(delete=True)
                zipfile = shutil.make_archive(tmpfile, 'zip', loc.folder)

                time.sleep(1)

                if platform.system() != "Windows":
                    os.sync()

                shutil.rmtree(loc.folder)
                signal.file_delivery.emit(zipfile)
                return True

    if not compress_and_remove():
        signal.error.emit(progressdict)

def concurrent_webp_work(job):
    def determine_webp_width_and_quality(path):
        """
        width is needed if we're reducing it to 4k
        :param path: string
        :return: string, int, int
        """
        try: image = Image.open(path)
        except:
            return False, False, False

        width = image.size[0]
        image.close()

        quality = t.config('webp_quality') or 70
        method = t.config('webp_method') or 6

        return width, quality, method

    def generate_loc(job):
        loc = t.separate_file_from_folder(job)
        loc.final_destination = loc.folder + loc.sep + loc.naked_filename + '.webp'
        return loc

    def duplicate_destination(loc):
        if os.path.exists(loc.final_destination) and os.path.getsize(loc.final_destination) > 0:
            return True  # destination exists, no conversion takes place

    def convert_file_to_webp(loc):
        width, quality, method = determine_webp_width_and_quality(path=loc.full_path)

        if not width:  # file is broken
            return False

        elif width > 3840 and t.config('webp_4kdownsize'):
            f = generate_cover_from_image_file(loc.full_path, width=3840, delete=False, quality=quality, method=method)

        else:
            f = generate_cover_from_image_file(loc.full_path, width=width, delete=False, quality=quality, method=method)

        return f

    loc = generate_loc(job)

    if duplicate_destination(loc):
        return False

    tmp_file = convert_file_to_webp(loc)

    if tmp_file and os.path.exists(tmp_file) and os.path.getsize(tmp_file) > 0:
        os.remove(loc.full_path)
        shutil.move(tmp_file, loc.final_destination)
        return loc.final_destination

    else:
        return False

def concurrent_cbx_to_webp_convertion(cbxfile, signalgroup='_cbx_to_webp', comicvine_id=None):
    progressdict = dict(
        start=time.time(), total=0, current=0, last_emit=time.time(), stop=False, ignored=0, final_check=0)

    tmpfolder = t.tmp_folder(folder_of_interest=cbxfile + 'cbx', hash=True, delete=True)
    signal = t.signals(signalgroup)

    def extract_all_to(cbxfile, tmpfolder):
        try:
            zf = ZipFile(cbxfile)
            zf.extractall(tmpfolder)

        except BadZipFile:

            try:
                rf = rarfile.RarFile(cbxfile)
                rf.extractall(tmpfolder)

            except rarfile.BadRarFile:
                signal.error.emit(progressdict)
                return False
        return True

    def generate_loclist(tmpfolder):
        loc_files_to_convert = []
        extensionlist = {'png', 'jpg', 'bmp', 'gif', 'jpeg', 'webp'}

        for walk in os.walk(tmpfolder):
            for f in walk[2]:
                progressdict['final_check'] += 1

                file = walk[0] + '/' + f
                loc = t.separate_file_from_folder(file)

                if loc.ext.lower() in extensionlist and os.path.getsize(loc.full_path) > 0:
                    progressdict['total'] += 1
                    loc_files_to_convert.append(dict(locfile=loc, status=False))

        return loc_files_to_convert

    def prepare_md5_values(loc_files_to_convert):
        if t.config('webp_md5file'):
            for i in loc_files_to_convert:
                i['locfile'].org_md5 = t.md5_hash_file(i['locfile'].full_path)
                i['locfile'].org_filesize = os.path.getsize(i['locfile'].full_path)

    def generate_concurrent_joblist(loc_files_to_convert):
        return [x['locfile'].full_path for x in loc_files_to_convert]

    if not extract_all_to(cbxfile=cbxfile, tmpfolder=tmpfolder):
        return False

    loc_files_to_convert = generate_loclist(tmpfolder)

    if not loc_files_to_convert:
        signal.error.emit(progressdict)
        return False

    prepare_md5_values(loc_files_to_convert)
    joblist = generate_concurrent_joblist(loc_files_to_convert)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for _, rv in zip(joblist, executor.map(concurrent_webp_work, joblist)):

            if not rv: # this must not be bad, could simply be file already exists
                progressdict['ignored'] += 1

            else:
                progressdict['current'] += 1
                if time.time() - progressdict['last_emit'] > 1:
                    signal.progress.emit(progressdict)

                if progressdict['stop']:
                    signal.stop.emit(progressdict)
                    return False

    if progressdict['current'] == 0: # meaning no file has been processed, repack un-nessesary
        signal.error.emit(progressdict)
        return False

    def make_md5_file():
        if t.config('webp_md5file'):
            loc_cbx = t.separate_file_from_folder(cbxfile)
            md5 = t.md5_hash_file(cbxfile)
            md5file = tmpfolder + loc_cbx.sep + md5 + '.md5'
            with open(md5file, 'w') as crc_file:
                crc_file.write('; original md5: ' + md5 + '\n')
                crc_file.write('; original filesize in bytes: ' + str(os.path.getsize(cbxfile)) + '\n')
                crc_file.write('; original filename: ' + loc_cbx.filename + '\n')
                if comicvine_id:
                    crc_file.write('; comicvine id: ' + str(comicvine_id) + '\n')

                for i in loc_files_to_convert:
                    crcloc = i['locfile']

                    if os.path.exists(crcloc.full_path): # skips unconverted
                        continue

                    elif 'org_md5' not in dir(crcloc) or 'org_filesize' not in dir(crcloc): # settings changed midjob
                        continue

                    crc_file.write(crcloc.org_md5 + ':' + str(crcloc.org_filesize) + ':' + crcloc.filename + '\n')

    def compress_into_new_tmp_file(tmpfolder):
        def same_amount_of_files():
            allfiles = 0
            for walk in os.walk(tmpfolder):
                allfiles += len(walk[2])

            if progressdict['final_check'] == allfiles:
                return True

        if not same_amount_of_files():
            signal.error.emit(progressdict)
            return False

        make_md5_file()

        tmpfile = t.tmp_file(delete=True)
        zipfile = shutil.make_archive(tmpfile, 'zip', tmpfolder)

        time.sleep(1)

        if platform.system() != "Windows":
            os.sync()

        try:
            zf = ZipFile(zipfile)
            fl = list(zf.namelist())
            if len(fl) < progressdict['final_check']:
                return False

        except BadZipFile:
            return False

        shutil.rmtree(tmpfolder)
        signal.file_delivery.emit(zipfile)
        return True

    if not compress_into_new_tmp_file(tmpfolder):
        signal.error.emit(progressdict)














































