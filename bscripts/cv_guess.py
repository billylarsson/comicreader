from bscripts.file_handling import unzipper
from bscripts.compare_images import ImageComparer
from bscripts.database_stuff import DB, sqlite
from bscripts.tricks import tech as t
from bscripts.comicvine_stuff import comicvine

class GUESSComicVineID:
    def __init__(self, database, autoinit=True, signal=None):
        self.year = None
        self.volume = None
        self.publisher = None
        self.issuenumber = None
        self.cut = None
        self.finished = False

        self.loc = t.separate_file_from_folder(database[DB.comics.local_path])
        self.fname = self.loc.naked_filename
        self.database = database
        if autoinit:
            if signal:
                self.signal = signal
            else:
                self.signal = t.signals('infowidget_signal_' + str(self.database[0]))

            self.guess_my_id()

    def extract_year_with_parentesis(self):
        """
        normally the first try to capture year is within parentesis
        and assuming starting years are 1 and 2 ie (1979 and 2021)
        """
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
        """
        if the first try to access the year is failed, a second
        retry is done here ignoring parantesis around the numbers
        """
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
        # todo 2000 AD is a bitch, i'll need to re-think that idea later on
        """
        first round we accept and numbers after a  _,#,' ',(, if failed
        then a second round that accept numbers after V (such as Hulk V2)
        :return: int
        """
        def two_rounds(self, accept_version_as_number=False):
            candidates = []
            chain = False
            if self.fname.lower().find('2000 ad') != -1 or self.fname.lower().find('2000ad') != -1:
                self.fname = self.fname.replace('2000', "ÖÖÖÖ")

            for c in range(1, len(self.fname)):
                if not chain:
                    if accept_version_as_number:
                        continuestruct = {'v', 'V'}
                    else:
                        continuestruct = {'_', '#', ' ', '('}

                    if self.fname[c - 1] not in continuestruct:
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

                if self.fname.find('ÖÖÖÖ') != -1:
                    self.fname = self.fname.replace('ÖÖÖÖ', '2000')

                for c in range(len(candidates[0])):
                    if candidates[0][c] != '0':
                        return int(candidates[0][c:])

        issuenumber = two_rounds(self)
        if not issuenumber:
            issuenumber = two_rounds(self, accept_version_as_number=True)
        return issuenumber

    def extract_volume_name(self):
        """
        i dont know if this is lazy or smart, but we fokus only on the preceedings
        before year and issuenumbers and assume that is the volume name
        :return:
        """
        if self.cut:
            self.fname = self.fname[0:self.cut]

        replacedict = {',': " ", "'s": "", "'": "", "  ": " "}
        for k,v in replacedict.items():
            self.fname = self.fname.replace(k,v)
        self.fname = self.fname.replace('  ', ' ')
        return self.fname

    def extract_volume_name_exclude_version_and_dash(self):
        """
        removes the "PART" from volumename and then splits
        the volumename in two parts if there's a - (dash)
        in the name and use the first part as volumename
        """
        self.volumename = self.extract_volume_name()
        if self.volumename.find(' - '):
            no_dash = self.volumename.strip().split(' - ')
            name = no_dash[0].strip().split(' ')
        else:
            name = self.volumename.strip().split(" ")
        self.remove_obsticle_in_name(name, obsticle='v')
        self.remove_obsticle_in_name(name, obsticle='part')
        return " ".join(name)

    def cut_and_lowest_cut(self, string): # no idea what it does but seems to be used a lot
        if not self.cut or self.fname.find(string) < self.cut and self.fname.find(string) > -1:
            self.cut = self.fname.find(string)
            if self.cut > 0:
                self.cut -= 1

        self.fname = self.fname.replace(string, "")

    def emit_finished_signal(self):
        """
        toggles the red "button" in the infowidget when job's done
        """
        if not self.finished:
            self.finished = True
            self.signal.path_deletebutton_jobs_done.emit()
            self.signal.autopair_complete.emit()

    def guess_my_id(self):
        self.year = self.extract_year() # int
        self.issuenumber = self.extract_issue_number() # int
        self.volumename = self.extract_volume_name() # string

        if not self.volumename:
            self.emit_finished_signal()
            return False

        else:
            if not self.search_comicvine():
                self.emit_finished_signal()

    def remove_obsticle_in_name(self, nameslist, obsticle):
        """
        removes an entire word from the string (list) thats
        used when searching for volumename in comicvine
        :param nameslist: list
        :param obsticle: string
        :return: bool
        """
        if obsticle == 'v':
            for count, i in enumerate(nameslist):
                if i and len(i) < 4 and i[0].lower() == obsticle and i[-1].isdigit():
                    nameslist.pop(count)
                    return True
        else: # sure, i could save a row or two here if i wanted to
            for count, i in enumerate(nameslist):
                if i and i.lower() == obsticle:
                    nameslist.pop(count)
                    return True

    def standard_volumes_search(self):
        """
        performes comicvine requests, as of now works amazing!

        one straight up as the self.volumename has captured it.
        one while cutting out 'V' (suspect version) from the filename.
        one while using first part of the fname when splitting dash ' - '
        one while using first part if dash plus stripping 'PART' from fname

        then the results are paginated if the results are above 100, currently
        2000 results are captured. then all volume_id's with issuecount >= the
        found issuenumber are returned
        :return: list with volume_id's
        """
        def genereate_things(self):
            if self.volumename.find(' - '):
                no_dash = self.volumename.strip().split(' - ')
                pre_name = " ".join(no_dash)
                name = pre_name.strip().split(' ')
                return name, no_dash, pre_name
            else:
                name = self.volumename.strip().split(" ")
                return name, None, None

        def perform_search(self, name):
            self.filters = dict(name=name)
            vol_rv = comicvine(search='volumes', filters=self.filters)
            return vol_rv

        def second_search(self, name):
            if self.remove_obsticle_in_name(name, obsticle='v'):
                vol_rv = perform_search(self, name)
                return vol_rv

        def third_search(self, name):
            self.remove_obsticle_in_name(name, obsticle='v')
            vol_rv = perform_search(self, name)
            return vol_rv

        def fourth_search(self, name):
            if self.remove_obsticle_in_name(name, obsticle='part'):
                vol_rv = perform_search(self, name)
                return vol_rv

        def four_different_searches(self):
            name, no_dash, pre_name = genereate_things(self)
            vol_rv = perform_search(self, name)

            if not vol_rv:
                vol_rv = second_search(self, name)

            if not vol_rv:
                if self.volumename.find(' - ') > -1:
                    name = no_dash[0].strip().split(' ')
                    vol_rv = third_search(self, name)

            if not vol_rv:
                vol_rv = fourth_search(self, name)
            return vol_rv

        def paginate_results(self, vol_rv, times=20):
            for offset in [x * 100 for x in range(1, times)]:
                add_vol = comicvine(search='volumes', filters=self.filters, offset=offset)
                if add_vol:
                    vol_rv += add_vol
                if not add_vol or len(add_vol) != 100:
                    break

        vol_rv = four_different_searches(self)
        if not vol_rv:
            return False

        if len(vol_rv) >= 100:
            paginate_results(self, vol_rv)

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

        self.emit_finished_signal()
        return False
