from PIL             import Image
from bscripts.tricks import tech as t
import os
import shutil

class ImageComparer:
    def __init__(self, image_one, image_two, grayscale=False, delete=True):
        """
        this class is messy and you'll get headache if you try to capture it in full, therefore
        you should just give it two image paths and look for the results thats stored in
        self.total, red, green, blue, total and so on (see fn:sum_job())

        class is normally two separate instances, once for RGB and once for GRAYSCALE results.

        :param image_one:  string (local path)
        :param image_two:  string (local path)
        :param grayscale: bool
        :param delete: bool
        """
        self.tmpfolder = None
        self.delete = delete
        self.grayscale = grayscale
        self.org_image_one = image_one
        self.org_image_two = image_two
        self.start_job()

    def start_job(self, grayscale=None):
        if grayscale != None:
            self.grayscale = grayscale

        self.reset_work()
        self.make_both_images_same_size()
        self.make_slices()
        self.slice_results = self.get_values()
        self.sum_job()
        if self.delete:
            shutil.rmtree(self.tmpfolder)

    def pop_worst_slice(self, times=1):
        """
        sots the slice_results list and pops the lowest one times x
        :param times: int
        """
        for c in range(times):
            total = [self.slice_results[k]['total'] for k in self.slice_results]
            total.sort()

            for slicenumber in self.slice_results: # pops worst slice
                if self.slice_results[slicenumber]['total'] == total[0]:
                    self.slice_results.pop(slicenumber)
                    break

    def sum_job(self):
        """
        sets self.variable according to cycle list(s) so each result is easy accessable
        from the object itself, this is used later on in the program.
        dont like the try case here but ocatinally the whole spectrum arent accounted
        """
        self.pop_worst_slice(times=2) # pops the worst two

        if self.grayscale:
            cycle = ['total', 'black', 'colors', 'file_size']
        else:
            cycle = ['total', 'red', 'green', 'blue', 'colors', 'file_size']

        for i in cycle:
            setattr(self, i, 0)
            try:
                total = [self.slice_results[k][i] for k in self.slice_results]
                setattr(self, i, sum(total) / len(total))
            except KeyError:
                continue

    def reset_work(self):
        """
        there was an idea to reuse same object but that idea wasnt fulfiled,
        but theres no harm done in having a fn that creates the dictionary
        """
        if self.tmpfolder and os.path.exists(self.tmpfolder):
            shutil.rmtree(self.tmpfolder)

        self.tmpfolder = t.tmp_folder()

        self.work = dict(
            original_images=[self.org_image_one, self.org_image_two],
            loaded_originals=[],
            saved_resized=[],
            loaded_resized=[],
            loaded_slices=[],
            saved_slices=[]
        )

    def get_values(self):
        """
        this is all rewritten but ideas come from the first version of this comicreader.
        i havent put much thougth into the logic i had back then, even though this might
        improve if i did have a re-look into it.

        i am currently unable to comment on everything that happens here, meaning later
        me should probably reuse without glancing to much at this or rewrite it as done
        twice already, but in short a dictionary is created thats thrown around and
        collects all the nessesary colors, sizes and differences for each slice and the
        dictionary is returned and set as a self.slice_results
        """
        def get_colors(slice):
            maxcolors = 16800
            colors = slice.getcolors(maxcolors=maxcolors)
            while not colors:
                maxcolors = maxcolors * 2
                colors = slice.getcolors(maxcolors=maxcolors)
                if maxcolors > 10000000000:
                    break
            return colors

        def color_difference(one, two):
            if len(one) < len(two):
                lendiff = len(one) / len(two)
            else:
                lendiff = len(two) / len(one)
            return lendiff

        def insert_color_differences(slice1, slice2, compare, count):
            col1 = get_colors(slice1)
            col2 = get_colors(slice2)

            lendiff = color_difference(col1, col2)
            compare[count]['colors'] = lendiff

        def insert_histogram_differences(self, slice1, slice2, compare, count):
            if self.grayscale:
                try:
                    b1, w1 = slice1.split()
                    b2, w2 = slice2.split()
                    cycle = [['black', b1, b2]]
                except ValueError:
                    return False
            else:
                try:
                    r1, g1, b1 = slice1.split()
                    r2, g2, b2 = slice2.split()
                    cycle = [['red', r1, r2], ['green', g1, g2], ['blue', b1, b2]]
                except ValueError:
                    return False

            for i in cycle:
                hist1 = i[1].histogram()
                hist2 = i[2].histogram()

                rgb = i[0]

                diffs = []
                if len(hist1) == len(hist2):
                    for cc in range(len(hist1)):

                        h1 = hist1[cc]
                        h2 = hist2[cc]

                        if h1 > h2:
                            if not h2:
                                h2 = 1
                            diffs.append(h2 / h1)

                        elif h1 < h2:
                            if not h1:
                                h1 = 1
                            diffs.append(h1 / h2)

                        else:
                            diffs.append(1)

                    if sum(diffs):
                        compare[count][rgb] = sum(diffs) / len(diffs)

                else:
                    compare[count][rgb] = None
            return True

        def insert_entropy_differences(slice1, slice2, compare, count):
            en1 = slice1.entropy()
            en2 = slice2.entropy()
            if en1 < en2:
                compare[count]['entropy'] = en1 / en2
            else:
                compare[count]['entropy'] = en2 / en1

        def slice_file_sizes(self, compare):
            slicepaths_one = self.work['saved_slices'][0]
            slicepaths_two = self.work['saved_slices'][1]

            for count in compare:
                size1 = os.path.getsize(slicepaths_one[count])
                size2 = os.path.getsize(slicepaths_two[count])

                if size1 < size2:
                    diff = size1 / size2
                else:
                    diff = size2 / size1

                compare[count]['file_size'] = diff

        compare = {}
        group1 = self.work['loaded_slices'][0]
        group2 = self.work['loaded_slices'][1]

        for count in range(len(group1)):
            compare[count] = {}

            sl1 = group1[count]
            sl2 = group2[count]

            insert_color_differences(slice1=sl1, slice2=sl2, compare=compare, count=count)
            insert_histogram_differences(self, slice1=sl1, slice2=sl2, compare=compare, count=count)
            insert_entropy_differences(slice1=sl1, slice2=sl2, compare=compare, count=count)

        for count in compare:
            slice = compare[count]
            total = [v for k,v in slice.items() if v]
            sum_total = sum(total) / len(total)
            slice['total'] = sum_total

        slice_file_sizes(self, compare)

        return compare

    def make_both_images_same_size(self):
        """
        there was some struggle here and even from that struggle i wasnt
        fully able to always have the images tucked to the same size
        """
        width = 99999
        height = 99999

        for i in self.work['original_images']:
            if self.grayscale:
                im = Image.open(i).convert('LA')
            else:
                im = Image.open(i)

            self.work['loaded_originals'].append(im)

            if im.size[0] <= width:
                width = im.size[0] - 5
            if im.size[1] <= height:
                height = im.size[1] - 5

        for i in self.work['loaded_originals']:
            size = width, height
            i.thumbnail(size, Image.ANTIALIAS)

            tmpfile = t.tmp_file(tmp_folder=self.tmpfolder, new=True, extension='webp')
            i.save(tmpfile, 'webp', quality=50, optimize=False)

            self.work['saved_resized'].append(tmpfile)
            self.work['loaded_resized'].append(i)

    def make_slices(self):
        """
        this makes 12 slices from each image and fills self.work with
        each loaded slice and each slice's path, we need this later on
        when we compare sizes and such.
        """
        for c in range(len(self.work['loaded_resized'])):
            self.work['loaded_slices'].append([])
            self.work['saved_slices'].append([])

            image = self.work['loaded_resized'][c]
            im_width = image.size[0]
            im_height = image.size[1]

            left = 0
            top = 0
            right = (im_width / 3) - 1
            bottom = (im_height / 4) - 1

            for cc in range(12):

                if cc > 0:
                    if right + (im_width / 3) - 1 > im_width:
                        left = 0
                        top += (im_height / 4) - 1
                        right = (im_width / 3) - 1
                        bottom += (im_height / 4) - 1
                    else:
                        left += (im_width / 3) - 1
                        right += (im_width / 3) - 1

                cropped_image = image.crop((int(left),int(top),int(right),int(bottom)))

                tmpfile = t.tmp_file(tmp_folder=self.tmpfolder, new=True, extension='webp')
                cropped_image.save(tmpfile, 'webp', quality=50, optimize=False)

                self.work['loaded_slices'][c].append(cropped_image)
                self.work['saved_slices'][c].append(tmpfile)
