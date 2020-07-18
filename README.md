# radiostreamer

Intr
Manages a simple streaming radio player on Windows or Raspberry Pi.  It has not
been tested on iOS or other (non-RPi) versions of linux.

The program creates a very simple radio streaming app. The app is based on the
idea that when listening to music, all you usually want to do is 
turn it on and listen.  With that in mind, the program opens a simple dialog
and starts playing a streaming radio station by spawning a VLC subprocess. 

The program requires a working installed version of VLC.

The app depends on VLC to do most of the work, and thus acts as a specialized
(and very simple) front end to VLC.  Once the VLC process is
running, you have almost no direct control of VLC.  In fact, when you change
stations, the app closes VLC and reopens a new instance, pointing to a new
streaming radio service.

The program currently provides no mechanism to control VLC's volume, so volume 
must be controlled externally. The original setup for this program used either
(1) the built in Windows volume controls, or (2) a set of external, powered
speakers connected to the audio jack of a DAC attached to a Raspberry Pi.  The
speakers have independentvvvolume control. Thus I had little incentive to 
figure out how to control volume through inter-process communications.

It is also possible to set and forget the volume by listening to a tune
through VLC's standard GUI. Volume settings are preserved between VLC sessions,
even headless ones.

The app provides a simple user interface that starts and stops the music, and 
allows you to select lists of stations, and make minor edits to them. These are
not the sophisticated playlists possible with VLC, but simple lists of 
streaming radio stations stored as CSV files.

The structure of the playlist is a CSV file with three columns, containing a
brief name for each station, a description, and its url.  The first row should
contain header information, as follows:

"Name", "Description", "url"

Currently, the app does not use the Description field. Note that for now, "url"
is all lower case.

It's worth pointing out that CSV files produced on Windows,
especially using Excel, may NOT be in UTF-8, which is the default coding on the
Raspberry Pi.  You may be better off using another program (Google sheets, 
OpenOffice and Notebook++ all work.)

# Configuration
You need to do some setup in the radiostreamer.py file to make this work on
your machine.  The following code, at the top of the program, sets global
configuration options.

``` Python
PLYLISTFN = 'plylist.csv'
PROGPATH = 'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe'
PLAYER_CMD = "cvlc"
LOG_FILENAME = 'logging.txt'
ICONNAME = 'violin_icon.png'
TITLE= 'Play Radio'
```
*  PLYLISTFN:  Name of startup playlist.  This playlist should be located in the 
    same directory as the python script.
*  PROGPATH: path to your VLC executable.
*  PLAYER_CMD:  The command needed to start VLC. This differs on linux and
    windows.
*  LOG_FILENAME:  ANme of log file.  Currently, the log file provides little
    useful information.
*  ICONNAME:  Name of (path to) program icon. This icon is used 
*  TITLE:  Title for the initial UI window.