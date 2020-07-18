# -*- coding: utf-8 -*-
"""
Manages a simple streaming radio player on Windows or Raspberry Pi.

The program relies on VLC to do most of the work, and thus acts as a
specialized front end to VLC designed to make running streaming audio as
simple as possible.

The pregram requires a working installed version of VLC.

The program currently provides no mechanism to control VLC's volume, so volume must
be controlled externally. The oroginal setup for this program used either
(1) the built in wondows volume controls, or (2) a set of external, powered
speakers connected to the audio jack of the Raspberry Pi, with independent
volume control. If neither of those is possible, it is also possible to set 
and forget the volume by listening to a tune through VLC's standard GUI. 
Volume settings are preserved between VLC sessions.

The program also provides a very simple interface to playlists stored in
CSV files. 

It's worth pointing out that CSV files produced on windows,
especially using Excel, may NOT be in UTF-8, which is the default coding on the
Raspberry Pi.  So far, what I have seen is only one character -- some sort of 
end of file marker -- that is problematic coming from my installation of Excel.
The inappropriate character can be removed in a good text editor, such as
Notepad ++. Appreantly google sheets and Open office both handle this properly.

"""
import os
import subprocess
from datetime import datetime
import logging
import csv

import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import showwarning #,showinfo, showerror
from tkinter.messagebox import askokcancel

####################################
# Configuration Constants
####################################
#TODO:  create a confuguration file so this starts up each time with
# the options in force when the program was last closed.
PLYLISTFN = 'plylist.csv'
PROGPATH = 'C:/Program Files (x86)/VideoLAN/VLC/vlc.exe'
PLAYER_CMD = "cvlc"
LOG_FILENAME = 'logging.txt'
ICONNAME = 'violin_icon.png'
TITLE= 'Play Radio'

BACKCOLOR = "Seashell2" #"Lemon Chiffon" #"AntiqueWhite4" #  
THMCOLOR = "AntiqueWhite2"
LGTCOLOR = "Seashell2"
HLTCOLOR = "AntiqueWhite1"#"Floral White"
FONTCOLOR = 'NavajoWhite4'

##################################
# Set up logging
##################################
logging.basicConfig(
    filename=LOG_FILENAME,
    level=logging.DEBUG,
    format='%(asctime)s: (%(threadName)-10s): %(message)s')

logger = logging.getLogger('mylogger')
logger.debug('Starting log')
logger.debug(datetime.now().strftime('%d-%b-%Y (%H:%M:%S)'))


class EditEntryDialog(tk.Toplevel):
    '''A Popup Dialog class for editing a single Playlist Entry.

    Useage: pass a dictionary to the constructor containing
        'Name',
        'Description', and
        'url' entries.
     After the popup closes, the dictionary contains edited values.
     This does no error checking.
     '''
    #TODO:  Consider making a copy of the dictionary and returning that instead
    #       of editing the dictionary in place.
    
    def __init__(self, master, thedict=None):
        """
        master == the calling window.
        msg = <str> the message to be displayed
        thedict = dictionary containing "Name", "Description"and "url" slots
        (providing a sequence for dict_key creates an entry for user input)
        """
        tk.Toplevel.__init__(self, master)

        self.title('Edit these entries.')
        self.master = master
        self.resizable(False, False)
        self.thedict = thedict
        self._build_dialog()

        self.geometry("+%d+%d" % (self.master.winfo_rootx()+10,
                                  self.master.winfo_rooty()+10))

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.bind("<Return>", self.entries_to_dict)
        self.bind("<Escape>", self.cancel)

        self.name.focus_set()  # Set focus to first slot in dialog
        self.grab_set()        # Keep focus until dismissed
        self.transient(master) # A subwindow of my parent
        self.wait_window(self) # wait intil window is destroyed

    def _build_dialog(self):

        frm = tk.Frame(self, borderwidth=4, relief='ridge',
                       bg=THMCOLOR)
        frm.grid(row=0, column=0)

        label1 = tk.Label(frm, text="Name", justify=tk.LEFT,
                          bg=THMCOLOR)
        label1.grid(row=1, column=0, sticky=tk.W)

        label2 = tk.Label(frm, text="Description", justify=tk.LEFT,
                          bg=THMCOLOR)
        label2.grid(row=2, column=0, sticky=tk.W)

        label3 = tk.Label(frm, text="URL  (NOT HTTPS://)", justify=tk.LEFT,
                          bg=THMCOLOR)
        label3.grid(row=3, column=0, sticky=tk.W)

        self.name = tk.Entry(frm, width=25,
                             bg=LGTCOLOR)
        self.name.grid(row=1, column=1, columnspan=2,
                       padx=5, pady=5,
                       sticky=tk.W)
        self.name.insert(1, self.thedict['Name'])

        self.descr = tk.Entry(frm, width=75,
                              bg=LGTCOLOR)
        self.descr.grid(row=2, column=1, columnspan=2,
                        padx=5, pady=5,
                        sticky=tk.W)
        self.descr.insert(1, self.thedict['Description'])

        self.url = tk.Entry(frm, width=75,
                            bg=LGTCOLOR)
        self.url.grid(row=3, column=1, columnspan=2,
                      padx=5, pady=5,
                      sticky=tk.W)
        self.url.insert(1, self.thedict['url'])

        submit_button = tk.Button(frm, text='Submit', width=10, border=3,
                                  command=self.entries_to_dict,
                                  bg=THMCOLOR)
        submit_button.grid(row=4, column=1, sticky=tk.EW)

        cancel_button = tk.Button(frm, text='Cancel', width=10, border=3,
                                  command=self.cancel,
                                  bg=THMCOLOR)
        cancel_button.grid(row=4, column=2, sticky=tk.EW)

    def entries_to_dict(self, event=None):
        '''Convert entries in the dialog into a dictionary andclose dialog.'''
        #TODO:  add validation code here
        self.withdraw()
        self.update_idletasks()
        self.thedict['Name'] = self.name.get()
        self.thedict['Description'] = self.descr.get()
        self.thedict['url'] = self.url.get()
        self.cancel()

    def cancel(self, event=None):
        '''Close the  dialog without returning values.'''
        # Should this return a Falsie value?
        self.master.focus_set()
        self.destroy()

class SelectItemDialog(tk.Toplevel):
    # basic idea is that if I pass in a dict, and alter entries, we can examine
    # that dictionary externally
    def __init__(self, master, playlist=None):
        """
        master == the calling window.
        msg = <str> a message to be displayed
        playlist - -a list of dicts containing "Name", "Description" and "url" slots
        """
        tk.Toplevel.__init__(self, master)
        self.playlist = playlist
        self._dialog()
        #self.resizable(False, False)
        self.grab_set()
        self.transient(master)
        self.wait_window(self)

    def _dialog(self):
        frm = tk.Frame(self, borderwidth=4, relief=tk.RIDGE, bg=THMCOLOR)
        frm.grid(row=0, column=0, sticky=tk.NSEW)

        label = tk.Label(frm, text='Select An Item to Edit...',
                         bg=THMCOLOR,
                         font=('sanserif', 10))
        label.grid(row=0, column=0)

       # A separate sub-frame for the listbox and scrollbar
        lstbxframe = tk.Frame(frm, borderwidth=4, relief=tk.RIDGE,
                              bg=THMCOLOR)
        lstbxframe.grid(row=1, column=0, sticky=tk.NSEW)

        self.lstbx = tk.Listbox(lstbxframe, width=50,
                                bg=THMCOLOR,
                                fg=FONTCOLOR,
                                font=('sanserif', 10))
        for item in self.playlist:
            self.lstbx.insert(tk.END, item['Name'])
        self.lstbx.select_set(0)
        self.lstbx.grid(row=0, column=0, sticky=tk.NSEW)

        scrollbar = tk.Scrollbar(lstbxframe, bg=THMCOLOR)
        scrollbar.grid(row=0, column=1, sticky=(tk.NSEW))

        self.lstbx.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.lstbx.yview)

        # And a subframe for the control buttons
        toolbar = tk.Frame(frm, bg=THMCOLOR)
        toolbar.grid(row=2, column=0, sticky=tk.EW)

        #tk.Label(toolbar, text ='Testing').grid(row=0, column=0)

        select_for_edit_button = tk.Button(toolbar, text='Edit',
                                           command=self._examine,
                                           bg=THMCOLOR)
        select_for_edit_button.grid(row=2, column=0, sticky=tk.EW)

        close_button = tk.Button(toolbar, text='Close',
                                 command=self._close,
                                 bg=THMCOLOR)
        close_button.grid(row=2, column=1, sticky=tk.EW)

        add_button = tk.Button(toolbar, text='Add',
                               command=self._add,
                               bg=THMCOLOR)
        add_button.grid(row=3, column=0, sticky=tk.EW)

        delete_button = tk.Button(toolbar, text='Delete',
                                  command=self._delete_sel,
                                  bg=THMCOLOR)
        delete_button.grid(row=3, column=1, sticky=tk.EW)

        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)
        frm.columnconfigure(index=0, weight=1)
        frm.rowconfigure(index=0, weight=0)
        frm.rowconfigure(index=1, weight=1)
        frm.rowconfigure(index=2, weight=0)

        lstbxframe.columnconfigure(index=0, weight=1)
        lstbxframe.columnconfigure(index=1, weight=0)
        lstbxframe.rowconfigure(index=0, weight=1)
        toolbar.columnconfigure(index=0, weight=1)
        toolbar.columnconfigure(index=1, weight=1)

    def _examine(self):
        '''Open item in popup dialog for editing'''
        which = int(self.lstbx.curselection()[0])
        EditEntryDialog(self, self.playlist[which])

    def _add(self):
        '''Add new item to playlist'''
        newdict = {'Name':'', 'Description':'', 'url':''}
        EditEntryDialog(self, newdict)
        self.playlist.append(newdict)
        self.lstbx.insert(tk.END, newdict['Name'])

    def _delete_sel(self):
        ''''Delete selected item from playlist'''
        which = int(self.lstbx.curselection()[0])
        del self.playlist[which]
        self.lstbx.delete(which)

    def _close(self):
        '''Close the dialog box'''
        # Can put dialog closing code in here.
        self.destroy()

class Playlist_manager():
    ''' Simple Playlist Manager Class.
    This class manages a playlist, alowing loading, editing, and saving simple
    CSV file playlists.

    The loaded or altered playlist is accessible as an attribute of the manager.
    '''
    def __init__(self, fn=PLYLISTFN, fdir=None):
        self.plname = fn
        self.pldir = fdir
        if self.pldir is not None:
            self.plpath = os.path.join(self.pldir, self.plname)
        else:
            self.plpath = self.plname
        self.playlist = self.playlist_from_path(self.plpath)

    def playlist_from_path(self, path):
        '''Load a playlist from a file and return it.
        This does NOT alter the active playlist of the Playlist Manager'''
        # We keep a plylist as part of the manager principally to
        # enable us to edit the active playlist without loading.
        plylist = []
        try:
            with open(path, 'r') as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    plylist.append(row)
            return plylist
        except IOError:
            logger.warning('Can not open selected playlist.')
            return None

    def save_playlist(self):
        '''Ask the user to suggest where to save the current playlist'''
        d = os.getcwd() if self.pldir is None else self.pldir
        opts = {'initialdir':d,
                'filetypes' :(("CSV File", "*.csv"),
                              ("Text File", "*.txt"),
                              ("All Files", "*.*")),
                'defaultextension' : '.csv'}
        plylst_path = asksaveasfilename(opts)
        try:
            with open(plylst_path, 'w') as f:
                writer = csv.DictWriter(f, fieldnames=["Name", "Description", "url"])
                for row in self.playlist:
                    writer.writerow(row)
        except FileNotFoundError:
            logger.error('File Not Found:', plylst_path)
            showwarning('File Error', 'Requested File not found')

    def select_playlist(self):
        '''Ask the user to select a playlist and attempt to load it'''
        d = os.getcwd() if self.pldir is None else self.pldir
        opts = {'initialdir':d,
                'filetypes' :(("CSV File", "*.csv"),
                              ("Text File", "*.txt"),
                              ("All Files", "*.*")),
                'defaultextension' : '.csv'}
        plylst_path = askopenfilename(**opts)
        if os.path.isfile(plylst_path):
            self.playlist = self.playlist_from_path(plylst_path)
            return True
        else:
            return False

    def edit_playlist(self):
        '''Edit the current playlist via popup dialogs'''
        SelectItemDialog(None, self.playlist)


class Controls(tk.Frame):
    """Simple tkinter-based GUI"""
    # This class should be platform independent. All the platform
    # dependent pieces shuld be housed in to Player

    def __init__(self, master, player, playlistmanager):
        tk.Frame.__init__(self, master, bg=BACKCOLOR)
        self.parent=master
        self.parent.title('TITLE')
        self.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.parent.resizable(False, False)
        self.player = player
        self.manager = playlistmanager
        self.plst = self.manager.playlist
        self.ischanged = False       # is playlist altered?  Not clear if this
                                     # is best place o store this
        self.active = 0   # for now, default to first item in the list.
        self._gui()
        self.bind("<Map>",self.frame_mapped)
        self.change()     # This fires up the player with the current selection



    def _gui(self):
        '''Build a GUI containing Control buttons'''

        # Set rows as expanding to fit space available.
        # Layout is three rows, Top and bottom with frames holding buttons.
        # The middle row holds a listbox and a scrollbar.
        self.grid_rowconfigure(index=0, weight=0)
        self.grid_rowconfigure(index=1, weight=0)
        self.grid_rowconfigure(index=2, weight=1)
        self.grid_rowconfigure(index=3, weight=0)
        self.grid_columnconfigure(index=0, weight=1)
        self.grid_columnconfigure(index=1, weight=0)

        def hover(event):
            event.widget.config(bg=HLTCOLOR)

        def unHover(event):
            event.widget.config(bg=THMCOLOR)
            
        def unHoverBar(event):
            event.widget.config(bg=LGTCOLOR)


        ###########################
        # Mock Top Bar
        ###########################
        self.topbar = tk.Label(self, text='Simple Streaming Radio',
                               font=("sanserif", "12"), 
                               relief=tk.RAISED, bd=0, height=2,
                               bg=LGTCOLOR)
        self.topbar.grid(row=0, column=0, columnspan=2,
                         sticky=(tk.N, tk.W, tk.E, tk.S))
        
        self.topbar.bind("<Button-1>", self.startMove)
        self.topbar.bind("<ButtonRelease-1>", self.stopMove)
        self.topbar.bind("<B1-Motion>", self.moving)
        self.topbar.bind("<Enter>", hover)
        self.topbar.bind("<Leave>", unHoverBar)

        ##########################
        # Top Toolbar
        ##########################
        top_toolbar = tk.Frame(self, relief=tk.FLAT, bd=3,
                               bg=BACKCOLOR)
        top_toolbar.grid(column=0, row=1, columnspan=2, padx=0, pady=0,
                         sticky=(tk.N, tk.W, tk.E, tk.S))

        minimizebutton = tk.Button(top_toolbar, text="Minimize",
                               width=20, command=self._minimize,
                               bg=THMCOLOR)
        minimizebutton.grid(column=0, columnspan=2,
                            row=0, padx=6, pady=2,
                            sticky=tk.W+tk.E)
        minimizebutton.bind("<Enter>", hover)
        minimizebutton.bind("<Leave>", unHover)

        listbutton = tk.Button(top_toolbar, text="Select Playlist",
                               width=20, command=self._change_playlist,
                               bg=THMCOLOR)
        listbutton.grid(column=0, row=2, padx=6, pady=2,
                        sticky=tk.W+tk.E)
        listbutton.bind("<Enter>", hover)
        listbutton.bind("<Leave>", unHover)
        
        editbutton = tk.Button(top_toolbar, text="Manage Playlist",
                               width=20, command=self._edit_playlist,
                               bg=THMCOLOR)
        editbutton.grid(column=1, row=2, padx=6, pady=2,
                        sticky=tk.W+tk.E)
        editbutton.bind("<Enter>", hover)
        editbutton.bind("<Leave>", unHover)
 
        top_toolbar.grid_columnconfigure(index=0, weight=1)
        top_toolbar.grid_columnconfigure(index=1, weight=1)



        # Listbox and Scrollbar
        self.listbox = tk.Listbox(self, selectmode=tk.EXTENDED,
                                  relief=tk.GROOVE, bd=8,
                                  fg=FONTCOLOR,
                                  bg=THMCOLOR,
                                  font=("sanserif", "12"))

        for item in self.plst:
            self.listbox.insert(tk.END, item['Name'])
        self.listbox.select_set(self.active)
        self.listbox.grid(column=0, row=2, padx=8, pady=0,
                          sticky=(tk.N, tk.W, tk.E, tk.S))

        scrollbar = tk.Scrollbar(self, relief=tk.FLAT, bd=6,
                                 bg=THMCOLOR)
        scrollbar.grid(column=1, row=2,  padx=8, pady=0,
                       sticky=(tk.N, tk.W, tk.E, tk.S))

        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        #################################
        # Bottom Toolbar
        #################################
        bottom_toolbar = tk.Frame(self, relief=tk.FLAT, bd=3,
                                  bg=BACKCOLOR)
        bottom_toolbar.grid(column=0, row=3, columnspan=2, padx=4, pady=0,
                            sticky=tk.NSEW)
        # Build a couple of buttons in the toolbar
        playbutton = tk.Button(bottom_toolbar, text="Play Selected",
                               width=20, command=self.change,
                               bg=THMCOLOR)
        playbutton.grid(column=0, row=0, padx=6, pady=2,
                        sticky=tk.W+tk.E)
        playbutton.bind("<Enter>", hover)
        playbutton.bind("<Leave>", unHover)

        quitbutton = tk.Button(bottom_toolbar, text="Quit",
                               width=20, command=self.Quit,
                               bg=THMCOLOR)
        quitbutton.grid(column=1, row=0, padx=6, pady=2,
                        sticky=tk.W+tk.E)
        quitbutton.bind("<Enter>", hover)
        quitbutton.bind("<Leave>", unHover)
        

        bottom_toolbar.grid_columnconfigure(index=0, weight=1)
        bottom_toolbar.grid_columnconfigure(index=1, weight=1)

    def _changeselection(self):
        """Select which alternative stream to play and return the URL"""
        # It is possible to get here without a selection
        try:
            which = int(self.listbox.curselection()[0])
            if which is not None:
                logger.debug("Changing Streams In Mid Horse")
                selected = self.plst[which]
                self.target = selected['url']
                self.active = which
                return self.target
        except IndexError:
            logger.debug('Nothing selected')
            return None

    def Quit(self):
        ''''Quit the Application'''
        if self.ischanged:
            if askokcancel("Playlist has been altered", "Save current playlist?"):
                self.manager.save_playlist()
        self.player.close()
        m = self.master
        self.destroy()
        m.destroy()

    def startMove(self, event):
        '''Record starting position of cursor in preapration for dragging'''
        self.x = event.x
        self.y = event.y

    def stopMove(self, event):
        '''Clear iniital position of cursor after dragging'''
        self.x = None
        self.y = None

    def moving(self,event):
        '''Move the window by dragging the cursor.'''
        x = (event.x_root - self.x)
        y = (event.y_root - self.y)
        self.parent.geometry("+%s+%s" % (x, y))

    def frame_mapped(self,e):
        ''' Reclaim control of the window and return Window to visibility'''
        self.parent.update_idletasks()
        self.parent.deiconify()
        if self.player.platform == 'nt':
            self.parent.overrideredirect(True)
        
    def _minimize(self):
        self.parent.update_idletasks()
        if self.player.platform == 'nt':  
            self.parent.overrideredirect(False)
        self.parent.iconify()

    # def play(self):
    #     '''Dispatch play command to the Player'''
    #     # This method is unused, and appeats to do nothing on windows.
    #     self.player.play(self.player.target)

    def stop(self):
        '''Dispatch stop command to the Player'''
        # this appears to do nothing on Windows
        self.player.pause()

    def _change_playlist(self):
        ''' Dispatch change playlist command to the List Manager'''
        if self.manager.select_playlist():
            self.plst = self.manager.playlist
            self.listbox.delete(0, tk.END)
            for item in self.plst:
                self.listbox.insert(tk.END, item['Name'])
            self.ischanged = False

    def _edit_playlist(self):
        ''' Dispatch edit playlist command to the list manager'''
        self.manager.edit_playlist()
        if askokcancel("Confirm", "Keep playlist changes?"):
            self.plst = self.manager.playlist
            self.listbox.delete(0, tk.END)
            for item in self.plst:
                self.listbox.insert(tk.END, item['Name'])
            self.ischanged = True

    def change(self):
        '''Dispatch request to player to play current selection.

        Also functions as the default "play" method from the GUI, since
        the Player starts a new subprocess to change streams.
        '''
        url = self._changeselection()
        if url is not None:
            self.player.change(url)


class Player():
    """ Media player class. Playing is handled by VLC """
    def __init__(self, target=None):
        ''' Initialize the Player, but don't start playing anything'''
        logger.debug("Player Initializing")
        self.platform = os.name  #'nt' for windows, 'posix' for unix / linux / raspberry pi
        self.progpath = PROGPATH  # Only needed in Windows?
        self.player_cmd = PLAYER_CMD
        self.target = target
        self.process = None

    def __del__(self):
        self.close()

    def is_playing(self):
        '''Does the Player have a VLC subprocess?'''
        return bool(self.process)

    def play(self):
        """ Use a multimedia player to play a stream.

        Because of limitations in communicating with the VLC player
        this method closing the existing VLC instance and starts a new one
        pointed at the new target."""
        self.close()     # So this implementation closes any actilve VLC
                         # Instance
        if self.target:
            opts = self._build_start_opts()
            self.process = subprocess.Popen(opts, shell=False,
                                            stdout=subprocess.PIPE,
                                            stdin=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
        logger.debug("Player (Re)started")

    def close(self):
        """ exit pyradio (and kill mplayer instance) """
        logger.debug("Player shutting down...")
        if self.process is not None:
            self.process.kill()   # This kills the subprocess
            self.process.wait()
        self.process = None       # In the absence of the kill, this also
                                  # kills the subprocess.

    def _build_start_opts(self):
        """ Builds the options to pass to subprocess."""
        if self.platform == 'posix':
            opts = [self.player_cmd, "-Irc", "--quiet", self.target]
            return opts
        elif self.platform == 'nt':
            opts = [self.progpath, self.target, '-I rc']
            return opts
        else:
            raise 'Unknown Operatng System'

    def change(self, newtarget):
        """ change to next selection """
        self.target = newtarget
        self.play()

#TODO:  Refactor to bring playlist controls into the main interface
def start():
    plmgr = Playlist_manager(PLYLISTFN)

    plyr = Player()
    
    root = tk.Tk()
    root.geometry("250x275") #Width x Height
    root.attributes("-topmost", True)
    
    root.grid_rowconfigure(index=0, weight=1)
    root.grid_columnconfigure(index=0, weight=1)

    if plyr.platform == 'nt':    
        root.overrideredirect(1)

    photo = tk.PhotoImage(file = ICONNAME)
    root.iconphoto(True, photo)
    gui = Controls(root, plyr, plmgr)
    root.protocol("WM_DELETE_WINDOW", gui.Quit)

    gui.mainloop()

start()
