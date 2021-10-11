from bscripts.file_handling import unzipper
from bscripts.compare_images import ImageComparer
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
        self.signal = t.signals('guess' + str(self.database[0]))
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
        self.year = self.extract_year()
        self.issuenumber = self.extract_issue_number()
        self.volumename = self.extract_volume_name()

        if not self.volumename:
            self.signal.finished.emit()
            return False

        #elif self.issuenumber and self.volumename and self.year:
        else:
            if not self.search_comicvine():
                self.signal.finished.emit()

    def standard_volumes_search(self):
        filters = {}

        filters.update(dict(name=self.volumename.strip().split(' ')))

        vol_rv = comicvine(search='volumes', filters=filters)

        if not vol_rv:
            return False

        if len(vol_rv) >= 100:
            for offset in [100,200,300,400,500]:
                add_vol = comicvine(search='volumes', filters=filters, offset=offset)
                if add_vol:
                    vol_rv += add_vol
                if not add_vol or len(add_vol) != 100:
                    break

        if self.issuenumber:
            vol_rv = [str(x['id']) for x in vol_rv if x['count_of_issues'] >= self.issuenumber]
        else:
            vol_rv = [str(x['id']) for x in vol_rv]

        return vol_rv

    def fetch_best_candidate(self, candidates):
        org_image = unzipper(database=self.database, index=0)

        lap = []
        for i in candidates:
            rgb = ImageComparer(org_image, i['cover'])
            gray = ImageComparer(org_image, i['cover'], grayscale=True)
            quicktotal = (rgb.total + gray.total) / 2
            lap.append(
                (quicktotal, dict(
                used=False, cover=i['cover'], comic_id=i['comic_id'], rgb=rgb, grayscale=gray, total=quicktotal),))

        lap.sort(key=lambda x:x[0], reverse=True)
        return [x[1] for x in lap]

    def search_comicvine(self):
        vol_rv = self.standard_volumes_search()
        if not vol_rv:
            return False

        filters = {}

        filters.update(dict(volume='|'.join(vol_rv)))

        if self.year:
            cv_year = self.generate_cv_year()
            filters.update(dict(cover_date=cv_year))

        if self.issuenumber:
            filters.update(dict(issue_number=self.issuenumber))

        free_rv = comicvine(search='issues', filters=filters, sort_by='cover_date')

        if not free_rv:
            return False

        spamtracker = t.keep_track(name='cv_guesser', restart=True)
        candidates = []
        for i in free_rv:

            comic_id = i['id']
            if sqlite.execute('select * from comics where comic_id = (?)', values=comic_id):
                continue

            if self.year:
                if i['cover_date'] and str(i['cover_date'][0:4]) != str(self.year):
                    continue

            cover = t.download_file(i['image']['small_url'])
            candidates.append(dict(cover=cover, comic_id=comic_id))

            if spamtracker.count() >= 10:
                break

        if candidates:
            winners = self.fetch_best_candidate(candidates=candidates)
            self.signal.candidates.emit(winners)

        self.signal.finished.emit()
        return False
