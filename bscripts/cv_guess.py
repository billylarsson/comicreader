from bscripts.database_stuff import DB, sqlite
from bscripts.tricks import tech as t
from bscripts.comicvine_stuff import comicvine

class GUESSComicVineID:
    def __init__(self, database, autoinit=True):
        self.year = None
        self.volume = None
        self.publisher = None
        self.issuenumber = None
        self.cut = None

        self.loc = t.separate_file_from_folder(database[DB.comics.local_path])
        self.fname = self.loc.naked_filename
        self.database = database
        if autoinit:
            self.guess_my_id()

    def extract_year_with_parentesis(self):
        candidates = []
        for c in range(len(self.fname) - 5):
            if self.fname[c] != '(':
                continue

            if self.fname[c + 1] not in {'1','2'}:
                continue

            if self.fname[c + 5] != ')':
                continue

            year = self.fname[c + 1: c + 5]
            digitcheck = [x for x in year if x.isdigit()]

            if len(digitcheck) == 4 and year not in candidates:
                candidates.append(year)

        if len(candidates) == 1:
            self.cut_and_lowest_cut(candidates[0])
            return candidates[0]

    def extract_year_without_parentesis(self):
        candidates = []
        for c in range(len(self.fname) - 3):
            if self.fname[c] not in {'1','2'}:
                continue

            year = self.fname[c: c + 4]
            digitcheck = [x for x in year if x.isdigit()]

            if len(digitcheck) == 4 and year not in candidates:
                candidates.append(year)

        if len(candidates) == 1:
            self.cut_and_lowest_cut(candidates[0])
            return candidates[0]

    def extract_year(self):
        year = self.extract_year_with_parentesis()
        if not year:
            year = self.extract_year_without_parentesis()
        if year:
            return int(year)

    def generate_cv_year(self):
        if self.year:
            year = str(self.year) + '-1-1|' + str(self.year + 1) + '-1-1'
            return year

    def extract_issue_number(self):
        candidates = []
        chain = False
        if self.fname.lower().find('2000 ad') != -1 or self.fname.lower().find('2000ad') != -1:
            self.fname = self.fname.replace('2000', "ÖÖÖÖ")

        for c in range(1, len(self.fname)):
            if not chain:
                if self.fname[c-1] not in {'_','#',' ','('}:
                    continue

                if self.fname[c].isdigit():
                    candidates.append(self.fname[c])
                    chain = True

            elif chain:
                if not self.fname[c].isdigit():
                    break

                candidates[-1] += self.fname[c]

        if candidates:
            self.cut_and_lowest_cut(candidates[0])

            if self.fname.lower().find('2000 ad') != -1 or self.fname.lower().find('2000ad') != -1:
                self.fname = self.fname.replace('ÖÖÖÖ', '2000')

            for c in range(len(candidates[0])):
                if candidates[0][c] != '0':
                    return int(candidates[0][c:])

    def extract_volume_name(self):
        if self.cut:
            self.fname = self.fname[0:self.cut]

        replacedict = {'-': " ", ',': " ", "'s": "", "'": "", "  ": " "}
        for k,v in replacedict.items():
            self.fname = self.fname.replace(k,v)
        self.fname = self.fname.replace('  ', ' ')
        return self.fname

    def cut_and_lowest_cut(self, string):
        if not self.cut or self.fname.find(string) < self.cut and self.fname.find(string) > -1:
            self.cut = self.fname.find(string)
            if self.cut > 0:
                self.cut -= 1

        self.fname = self.fname.replace(string, "")

    def guess_my_id(self):
        #self.fname = 'Parasomnia 004 (2021) (digital) (Son of Ultron-Empire)'
        self.year = self.extract_year()
        cv_year = self.generate_cv_year()
        self.issuenumber = self.extract_issue_number()
        self.volumename = self.extract_volume_name()

        print('\nfilename:', self.loc.naked_filename, '\nyear:', self.year, '\nissuenumber:', self.issuenumber, '\nvolumename:',self.volumename)
        signal = t.signals('guess' + str(self.database[0]))
        if not self.issuenumber or not self.volumename:
            signal.finished.emit()
            return

        filters = {}

        filters.update(dict(issue_number=self.issuenumber))
        filters.update(dict(name=self.volumename.split(' ')))

        if cv_year:
            filters.update(dict(cover_year=cv_year))

        vol_rv = comicvine(search='volumes', filters=filters)

        if not vol_rv:
            signal.finished.emit()
            return

        if 'single_result' in vol_rv:
            vol_rv = [vol_rv]

        for c in range(len(vol_rv)-1,-1,-1):
            if vol_rv[c]['count_of_issues'] < self.issuenumber:
                vol_rv.pop(c)

        if not vol_rv:
            signal.finished.emit()
            return

        for volumes in vol_rv:
            volume_id = volumes['id']
            free_rv = comicvine(volume=volume_id)
            if not free_rv:
                signal.finished.emit()
                return

            for i in free_rv['issues']:
                if not str(self.issuenumber) == i['issue_number']:
                    continue

                comic_id = i['id']
                com_rv = comicvine(issue=comic_id)
                if not com_rv:
                    signal.finished.emit()
                    return

                _tmp = sqlite.execute('select * from comics where comic_id = (?)', values=comic_id)
                if _tmp:
                    continue

                cover = t.download_file(com_rv['image']['small_url'])
                signal.startjob.emit(dict(cover=cover, comic_id=comic_id))
                signal.finished.emit()
                return

        signal.finished.emit()





"""
 api/issues?api_key=XXX&filter=issue_number:8,cover_date:2021-1-1|2022-1-1,volume:133597|82422|80357&sort=id:desc&format=json
 api/volumes?api_key=XXX&filter=name:mirka,name:andolfo,name:sweet,name:paprika&sort=id:desc&format=json
"""
