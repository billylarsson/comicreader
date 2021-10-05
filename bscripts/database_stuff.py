from script_pack.sqlite_handler import SQLite
import os

sqlite = SQLite(
    DATABASE_FILENAME=os.environ['DATABASE_FILENAME'],
    DATABASE_FOLDER=os.environ['DATABASE_FOLDER'],
    DATABASE_SUBFOLDER=os.environ['DATABASE_SUBFOLDER'],
    INI_FILENAME=os.environ['INI_FILENAME'],
    INI_FILE_DIR=os.environ['INI_FILE_DIR'],
)

class DB:
    class comics:
        bookmarks = sqlite.db_sqlite('comics', 'bookmarks', 'blob')
        comic_id = sqlite.db_sqlite('comics', 'comic_id', 'integer')
        cover = sqlite.db_sqlite('comics', 'cover', 'blob')
        current_page = sqlite.db_sqlite('comics', 'current_page', 'integer')
        file_contents = sqlite.db_sqlite('comics', 'file_contents', 'blob')
        file_date = sqlite.db_sqlite('comics', 'file_date', 'integer')
        file_size = sqlite.db_sqlite('comics', 'file_size', 'integer')
        issue_number = sqlite.db_sqlite('comics', 'issue_number')
        last_opened = sqlite.db_sqlite('comics', 'last_opened', 'integer')
        local_path = sqlite.db_sqlite('comics', 'local_path')
        md5 = sqlite.db_sqlite('comics', 'md5')
        publisher_id = sqlite.db_sqlite('comics', 'publisher_id', 'integer')
        rating = sqlite.db_sqlite('comics', 'rating', 'integer')
        rating_other = sqlite.db_sqlite('comics', 'rating_other', 'integer')
        type = sqlite.db_sqlite('comics', 'type', 'integer')  # 1=Comic, 2=Magazine, 3=NSFW
        volume_id = sqlite.db_sqlite('comics', 'volume_id', 'integer')

        NSFW = 2
        magazine = 3
        comic = 1

    class volumes:
        publisher_id = sqlite.db_sqlite('volumes', 'publisher_id', 'integer')
        volume_id = sqlite.db_sqlite('volumes', 'volume_id', 'integer')
        volume_name = sqlite.db_sqlite('volumes', 'volume_name')

    class publishers:
        publisher_id = sqlite.db_sqlite('publishers', 'publisher_id', 'integer')
        publisher_name = sqlite.db_sqlite('publishers', 'publisher_name')

    class issue_volume_publisher:
        comic_id = sqlite.db_sqlite('issue_volume_publisher', 'comic_id', 'integer')
        publisher_id = sqlite.db_sqlite('issue_volume_publisher', 'publisher_id', 'integer')
        volume_id = sqlite.db_sqlite('issue_volume_publisher', 'volume_id', 'integer')

    class settings:
        config =  sqlite.db_sqlite('settings', 'config', 'blob')



