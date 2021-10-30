# comicreader

![Screenshot from 2021-10-08 21-22-22](https://user-images.githubusercontent.com/59517785/136614432-e6602d61-dc0a-4c6a-a251-6c847edd9698.png)

<h3>If you're on Windows i assume all you need to do is to run Comicreader.exe. 
  
  Goto the RELEASE-area to download the zipped file containing with the executable</h3>

Downloading the executable release will probably not provide the latest changes to the Comicreader, downloading and launching the PY-files directly will.

* Batch Comicvine auto pairing added
* Batch PDF conversion added
* Batch WEBP conversion added
* Added opt-in so that it pairs with Comicvine servers while converting to WEBP
* Added support for multiple screens so to speak, very experimental!


INSTALLATION:

1: Install Python: 
https://www.python.org/downloads/

2: Install dependencies from its unpacked directory type:
pip install -r requirements.txt --user

Microsoft Windows

3.a: You may want to install WinRAR and provide the path in this programs configurations area.
https://www.rarlab.com/download.htm

3.b: You may want to install 7-Zip instead of WinRAR (but as for now WinRAR is more compatible even though I personally oppose WinRAR for other reasons)
https://www.7-zip.org/download.html

3.c: If you want PDF support you may want to download Poppler and point the program its binaries ie c:\Program Files\poppler-0.68.0\bin\
http://blog.alivate.com.au/poppler-windows/

4:
Linux only: sudo apt install unrar seems to do good for RARsupport

RUNNING:

1a: Unpack the zipfile and run Comicreader.exe (Windows only)

1b: start the program from a command prompt, from its unpacked directory type: python comicreader.py 
the first thing you should do is to enter the CONFIG/SETTINGS area and provide the folders you want it to scan for comics from.
click the update library button and then you can freeley search for comics in the search bar, right clicking a comic opens a window where you can do small things to the comic such as give it a rating, convert it to WEBP, rename the file, delete the file so on so forth.
left clicking the comic starts reading it, pressing left/right to change page, change reading modes by pressing 1,2,3,4... right click for bookmarks.

NOTE: I dont own a copy of Windows myself, therefore testing for Windows during developement is very limited, please report unplesant behavior.
