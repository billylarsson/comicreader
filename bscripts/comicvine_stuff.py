from bscripts.database_stuff import DB, sqlite
from bscripts.tricks         import tech as t
import copy
import json
import os
import requests
import time


class CVConnect:
    def __init__(self):
        self.reset()

    def reset(self):

        self.subdirs = []
        self.filters = []
        self.fields = []
        self.response = None
        self.url = None
        self.filename = None
        self.new_download = False

    def add_to_url(self, value):
        self.subdirs.append(str(value))

    def add_filter_to_url(self, key, value):
        self.filters.append({str(key): str(value)})

    def add_field_to_url(self, value):
        self.fields.append(str(value))

    def genereate_final_url(self):
        if not self.url:
            self.url = 'https://comicvine.gamespot.com/api'
        else:
            return # already been generated

        for i in self.subdirs:

            if self.url[-1] != '/':
                self.url += '/'

            if i[0] == '/':
                self.url += i[1:]

            else:
                self.url += i

        self.url += '?api_key=' + t.config('comicvine_key')

        for count, d in enumerate(self.filters):
            for key, value in d.items():
                if count == 0:
                    self.url += '&filter='
                else:
                    self.url += ','

                self.url += key + ':' + value

        self.url += '&sort=id:desc&format=json'

    def generate_filename(self, reuse=True, days=7, delete=False):
        if not self.filename:
            self.filename = t.tmp_file(self.url, hash=True, reuse=reuse, days=days, delete=delete, extension='json')
        else:
            return # already been generated

    def store_jsondata(self):
        if not self.response:
            return False

        if self.response.status_code == 200:
            try: jsondata = self.response.json()
            except ValueError: jsondata = {'number_of_page_results' : 0}

            if jsondata['number_of_page_results'] > 0:

                with open(self.filename, 'w') as f:
                    json.dump(jsondata, f)

                return True

    def load_results(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as raw:
                data = json.load(raw)

            if type(data) != dict or 'results' not in data:
                os.remove(self.filename)
                rv = False

            elif type(data['results']) == dict:
                rv = [data['results']]

            elif type(data['results']) == list:
                rv = [x for x in data['results']]
            else:
                rv = False

            if rv and len(rv) == 1:
                return rv[0]

            else:
                return rv

    def check_cache(self):
        if not self.filename:
            if not self.url:
                self.genereate_final_url()
            self.generate_filename()

        if os.path.exists(self.filename):
            return True

    def download(self, force=False):
        if not self.filename or not self.url:
            self.genereate_final_url()
            self.generate_filename()

        if force or not self.check_cache():
            retry_count = 5
            while retry_count > 0:
                retry_count -= 1

                if t.config('dev_mode'):
                    print("DOWNLOADING FROM COMICVINE!", self.filename, self.url)
                try:
                    self.response = requests.get(self.url, headers=t.header())

                    if self.response.status_code == 200:
                        if self.store_jsondata():
                            self.new_download = True  # indicates that we have downloaded new data

                        break # will always break if resone == 200
                    else:
                        if t.config('dev_mode'):
                            print("SUPER IMPORTANT", self.response.status_code)
                        break

                except ConnectionError:
                    time.sleep(1)
        else:
            if t.config('dev_mode'):
                print("USING COMICVINE CACHE:", self.filename)

        rv = self.load_results()
        if rv:
            return rv

def extra_update():
    tracker = t.keep_track('_extra_update', start=True)
    if tracker.halt():
        return

    query = 'select * from issue_volume_publisher'
    finedata = sqlite.execute(query=query, all=True)

    fouldata = sqlite.execute(query='select * from comics', all=True)
    fouldata = [x for x in fouldata if x[DB.comics.comic_id] and not x[DB.comics.volume_id]]

    for missing in fouldata:
        for existing in finedata:
            if existing[DB.issue_volume_publisher.comic_id] == missing[DB.comics.comic_id]:
                query = 'update comics set volume_id = (?) where id is (?)'
                values = existing[DB.issue_volume_publisher.volume_id], missing[0]
                sqlite.execute(query=query, values=values)

                if not missing[DB.comics.publisher_id]:
                    query = 'update comics set publisher_id = (?) where id is (?)'
                    values = existing[DB.issue_volume_publisher.publisher_id], missing[0]
                    sqlite.execute(query=query, values=values)

    tracker.stop()

def issue_vol_pub(volume_id, cvjson):
    publisher_id = cvjson['publisher']['id']

    query = 'select * from issue_volume_publisher where volume_id = (?)'
    data = sqlite.execute(query=query, values=volume_id, all=True)
    all_comic_id = [x[DB.issue_volume_publisher.comic_id] for x in data]

    executemany = []
    query, org_values = sqlite.empty_insert_query('issue_volume_publisher')

    for i in cvjson['issues']:

        if i['id'] in all_comic_id:
            continue

        values = copy.copy(org_values)

        values[DB.issue_volume_publisher.comic_id] = i['id']
        values[DB.issue_volume_publisher.publisher_id] = publisher_id
        values[DB.issue_volume_publisher.volume_id] = volume_id
        executemany.append(tuple(values))

    if executemany:
        sqlite.execute(query=query, values=executemany)

def download_volumedata(volume_id):
    cv = CVConnect()
    cv.add_to_url('volume/4050-' + str(volume_id))
    rv = cv.download()
    return rv, cv

def download_all_volumes_from_publisher(publisher_id):
    cv = CVConnect()
    cv.add_to_url('publisher/4010-' + str(publisher_id))
    rv = cv.download()
    return rv

def update_publisher_volumes(issue_data_or_publisher_id):
    if type(issue_data_or_publisher_id) != int:
        rv, _ = download_volumedata(volume_id=issue_data_or_publisher_id['volume']['id'])
        if rv and rv['publisher']['id']:
            publisher_id = rv['publisher']['id']
        else:
            return
    else:
        publisher_id = issue_data_or_publisher_id

    many_volumes = []
    query, org_values = sqlite.empty_insert_query('volumes')
    rv = download_all_volumes_from_publisher(publisher_id=publisher_id)

    if not rv:
        return publisher_id

    org_volumes = sqlite.execute('select * from volumes where publisher_id = (?)', (publisher_id,), all=True)
    org_volumes = [x[DB.volumes.volume_id] for x in org_volumes]

    for i in rv['volumes']:

        volume_id = int(i['id'])
        volume_name = str(i['name'])

        if volume_id in org_volumes:
            continue

        values = copy.copy(org_values)
        values[DB.volumes.volume_id] = volume_id
        values[DB.volumes.volume_name] = volume_name
        values[DB.volumes.publisher_id] = publisher_id
        many_volumes.append(tuple(values))

    if many_volumes:
        sqlite.execute(query, many_volumes)

    return publisher_id

def update_issue(cvdata, comic_id_or_dbinput):
    if type(comic_id_or_dbinput) == int:
        database = sqlite.execute('select * from comics where comic_id = (?)', comic_id_or_dbinput)
        if not database:
            return False
    else:
        database = comic_id_or_dbinput

    if not cvdata:
        return

    if cvdata['issue_number'] and not database[DB.comics.issue_number]:
        query = 'update comics set issue_number = (?) where id is (?)'
        values = (cvdata['issue_number'], database[0],)
        sqlite.execute(query=query, values=values)

    if cvdata['volume']['id'] and not database[DB.comics.volume_id]:
        query = 'update comics set volume_id = (?) where id is (?)'
        values = (cvdata['volume']['id'], database[0],)
        sqlite.execute(query=query, values=values)

    if cvdata['volume']['id'] and not database[DB.comics.publisher_id]:
        publisher_id = update_publisher_volumes(issue_data_or_publisher_id=cvdata)
        if publisher_id:
            query = 'update comics set publisher_id = (?) where id is (?)'
            values = (publisher_id, database[0],)
            sqlite.execute(query=query, values=values)

    else: # also updates volumes if this cannot be found in databasse after updating issue
        data = sqlite.execute('select * from volumes where volume_id = (?)', cvdata['volume']['id'])
        if not data:
            update_publisher_volumes(issue_data_or_publisher_id=cvdata)

def comicvine(
        issue=False,
        volume=False,
        publisher=False,
        filters=None,
        fields=None,
        force=False,
        update=False,
        ):

    if not t.config('comicvine_key'):
        return False

    if issue:
        if type(issue) != int:
            comic_id = issue[DB.comics.comic_id]
        else:
            comic_id = issue

        if not comic_id:
            return False

        cv = CVConnect()
        cv.add_to_url('issues')
        cv.add_filter_to_url(key='id', value=comic_id)
        rv = cv.download(force=force)

        if update:
            update_issue(cvdata=rv, comic_id_or_dbinput=issue)

        return rv

    elif volume:
        if type(volume) != int:
            volume_id = volume[DB.comics.comic_id]
        else:
            volume_id = volume

        if not volume_id:
            return False

        rv, cv = download_volumedata(volume_id=volume_id)

        if update:
            issue_vol_pub(volume_id=volume_id, cvjson=rv)

            data = sqlite.execute('select * from volumes where volume_id = (?)', volume_id)
            if not data:
                update_publisher_volumes(issue_data_or_publisher_id=rv['publisher']['id'])

            extra_update()

        return rv


"""
        if 'fields' in kwargs:
            for eachfield in kwargs['fields']:
                if self.cv_dict['fields'] == "":
                    self.cv_dict['fields'] = '&fields=' + str(eachfield)
                else:
                    self.cv_dict['fields'] += ',' + str(eachfield)

        if 'filter' in kwargs:
            for eachform in kwargs['filter']:
                for eachkey in kwargs['filter'][eachform]:
                    if self.cv_dict['filter'] == "":
                        self.cv_dict['filter'] = '&filter=' + str(eachform) + ':' + str(eachkey)
                    else:
                        self.cv_dict['filter'] += ',' + str(eachform) + ':' + str(eachkey)

 https://comicvine.gamespot.com/api/issues?api_key=XXX&filter=id:856444&sort=id:desc&format=json
 
"""
