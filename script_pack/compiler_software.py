#!/usr/bin/env python3
import concurrent.futures
import os
import platform
import subprocess

def create_shared_object(path):
    subprocess.run(['cythonize', '-i', '-3', path])

def compile_list_of_pyxfiles(single_or_list):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        (single_or_list, executor.map(create_shared_object, single_or_list))

class CythonCompiler:
    def __init__(self, source_filename, subfolder=None, force_update=False, spare_work_files=True):
        """
        :param source_filename: this is __file__ from launching program
        :param force: bool, force overwrite
        :param spare_work_files: bool, dont delete anything
        """
        self.force_update = force_update
        self.spare_work_files = spare_work_files

        if platform.system() == "Windows":
            source_dir = os.path.realpath(source_filename)[0:os.path.realpath(source_filename).rfind('\\')]
        else:
            source_dir = os.path.realpath(source_filename)[0:os.path.realpath(source_filename).rfind('/')]

        if subfolder:
            source_dir += '/' + subfolder

        self.source_dir = os.path.abspath(os.path.expanduser(source_dir))
        self.prepare_compiling()

    def prepare_compiling(self):
        pre_state_files = self.pre_cleanup()
        self.force_update_job(delete_extensions=['.so'])
        pyx_files = self.find_files_of_interest(extensions=['.pyx'])
        compile_list_of_pyxfiles(single_or_list=pyx_files)
        self.post_cleanup(keep_files=pre_state_files, save_extensions=['.so'])

    def force_update_job(self, delete_extensions):
        """
        if self.force_update == True these files are deleted from hdd
        :param delete_extensions: list with extensions
        """
        if not self.force_update or self.spare_work_files:
            return

        for walk in os.walk(self.source_dir):
            for file in walk[2]:

                file_complete_path = os.path.abspath(os.path.expanduser(f'{walk[0]}/{file}'))

                for ext in delete_extensions:
                    if file.lower().find(ext) > -1 and file[-len(ext):len(file)].lower() == ext:
                        os.remove(file_complete_path)

    def post_cleanup(self, keep_files, save_extensions):
        """
        after compiling, we delete temporary files (mostly C-files)
        :param keep_files: prestate-files
        :param save_extensions: list
        """
        if self.spare_work_files:
            return

        for walk in os.walk(self.source_dir):
            for file in walk[2]:
                delete = True

                file_complete_path = os.path.abspath(os.path.expanduser(f'{walk[0]}/{file}'))

                if file_complete_path in keep_files:
                    continue

                for ext in save_extensions:
                    if file.lower().find(ext) > -1 and file[-len(ext):len(file)].lower() == ext:
                        delete = False

                if not delete:
                    continue

                os.remove(file_complete_path)

    def pre_cleanup(self):
        """
        saves the files present in self.source_dir
        :return: list with files
        """
        pre_state = []
        for walk in os.walk(self.source_dir):
            for file in walk[2]:
                current_file = os.path.abspath(os.path.expanduser(f'{walk[0]}/{file}'))
                pre_state.append(current_file)

        return pre_state

    def find_files_of_interest(self, extensions):
        """
        returns a list of files that was hit from your white_extensions and white_dirs
        meaning all trash files are excluded from the list
        :param extensions list with extensions ie [.pyx]
        :return: list of files
        """
        save_files = []
        for walk in os.walk(self.source_dir):
            for file in walk[2]:

                current_file = os.path.abspath(os.path.expanduser(f'{walk[0]}/{file}'))

                for ext in extensions:
                    if file.lower().find(ext) > -1 and file[-len(ext):len(file)].lower() == ext:
                        save_files.append(current_file)

        return save_files