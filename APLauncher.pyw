from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox, filedialog, Canvas
from types import new_class
import zipfile
from PIL import ImageTk, Image
from urllib.request import urlretrieve
from urllib.error import *
from zipfile import ZipFile
from tarfile import TarFile
import ttkbootstrap
import tkinter
import os
import sys
import json
import requests
import subprocess
import threading
import re
import shutil
import datetime
import time
import hashlib
import webbrowser
import traceback
import getpass
import logging
import socketserver
import platform
import psutil
import math
import webview
import uuid

__version__ = "1.0"

def send_error_report(fatal=False):
    try:
        with open(f"launcher_logs/error.log") as log:
            tb = log.read()
            tb.replace(getpass.getuser(), "<USER>")
    except FileNotFoundError:
        return
    if fatal:
        errtype = "crash"
    else:
        errtype = "bug"
    messagebox.showinfo("Report issue", f"Please report this {errtype} by creating an issue on Github.")
    if messagebox.askyesno("Report issue", f"Would you like to automatically open an issue?"):
        newline = "\n"
        body = f"(insert description of bug here)%0A***%0ALog contents:%0A```%0A{tb.replace(newline, '%0A')}%0A```"
        url = f"https://github.com/SpacePython12/AP-Launcher/issues/new?body={body}"
        webbrowser.open(url)

class ProcessBoundText(ScrolledText):

    def __init__(self, master=None, **kw):
        ScrolledText.__init__(self, master, **kw)

    def monitor(self, proc: subprocess.Popen):
        while proc.poll() is None:
            line = proc.stdout.readline()
            self.config(state="normal")
            self.insert("end", line)
            self.config(state="disabled")
            self.see("end")
            self.update_idletasks()
        self.delete("1.0", "end")
        self.insert("end", proc.stdout.read())

class OtherPage(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.themeframe = Frame(self)
        self.themeframe.grid(column=0, row=0, sticky="nsew")
        self.themelabel = Label(self.themeframe, text="Choose a theme: ")
        self.themelabel.grid(column=0, row=0, sticky="nsew")
        self.themevar = StringVar(self)
        self.themevar.set(THEME.theme_use())
        self.themebox = Combobox(self.themeframe, textvariable=self.themevar)
        self.themebox["values"] = [x for x in THEME.theme_names()]
        self.themebox.bind("<<ComboboxSelected>>", lambda x: self.update_theme())
        self.themebox.grid(column=1, row=0, sticky="nsew")
        self.titlelabel = Label(self, text=f"Links:", anchor="w")
        self.titlelabel.grid(column=0, row=1, sticky="nsew")
        self.bugreportlabel = Label(self, text="     Found a bug? Report it here!", foreground="blue", cursor="hand2")
        self.bugreportlabel.grid(column=0, row=3, sticky="nsew")
        self.bugreportlabel.bind("<Button-1>", lambda e: self.open_link("https://github.com/SpacePython12/AP-Launcher/issues/new?assignees=&labels=&template=bug_report.md&title="))
        self.suggestionlabel = Label(self, text="     Have a suggestion? Tell us here!", foreground="blue", cursor="hand2")
        self.suggestionlabel.grid(column=0, row=4, sticky="nsew")
        self.suggestionlabel.bind("<Button-1>", lambda e: self.open_link("https://github.com/SpacePython12/AP-Launcher/issues/new?assignees=&labels=&template=feature_request.md&title"))

    def open_link(self, url):
        webbrowser.open_new(url)

    def config(self, **kw):
        super().config(**kw)
        self.titlelabel.config(**kw)
        self.bugreportlabel.config(**kw)
        self.suggestionlabel.config(**kw)

    def update_theme(self):
        THEME.theme_use(self.themevar.get())

class LabeledEntry(Frame):

    def __init__(self, parent, text: str="", defaultval: str="", elength=20, hidden=None):
        super().__init__(parent)
        self.label = Label(self, text=text)
        self.entryvar = StringVar(self)
        self.entryvar.set(defaultval)
        self.entry = Entry(self, textvariable=self.entryvar, width=elength)
        if not hidden is None:
            self.entry.config(show=hidden)

    def grid(self, column, row, sticky=""):
        """Syncs the .grid() fucntion across all of the internal widgets"""
        super().grid(column=column, row=row)
        if sticky == "":
            super().grid(column=column, row=row)
            self.label.grid(column=0, row=0)
            self.entry.grid(column=1, row=0)
        else:
            super().grid(column=column, row=row, sticky=sticky)
            self.label.grid(column=0, row=0, sticky=sticky)
            self.entry.grid(column=1, row=0, sticky=sticky)

    def get(self):
        return self.entryvar.get()

    def set(self, val):
        self.entryvar.set(val)

    def config(self, **kw):
        self.label.config(**kw)
        super().config(**kw)
        self.entry.config(**kw)

class App:

    def __init__(self):
        global THEME
        logger.info(f"Version: {__version__}")
        machineinfo = f"OS: {platform.system()}"
        logger.info(machineinfo)
        logger.info("AP Launcher has started, now initalizing window.")
        self.win = Tk()
        THEME = ttkbootstrap.Style()
        self.win.title(f"AP Launcher v{__version__}")
        self.win.rowconfigure(0, weight=1)
        self.win.columnconfigure(0, weight=1)
        self.tabs = Notebook(self.win)
        self.tabs.grid(column=0, row=0, sticky="nsew")
        self.tabs.rowconfigure(0, weight=1)
        self.tabs.columnconfigure(0, weight=1)
        self.minecraftdir = OS_SPECIFICS["default_minecraft_dir"]
        self.win.protocol("WM_DESTROY_WINDOW", lambda: self.on_closing())
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.on_closing())
        self.accounts = self.get_accounts()
        self.mainframe = Frame(self.win)
        self.mainframe.rowconfigure(0, weight=1)
        self.mainframe.columnconfigure(0, weight=1)
        self.tabs.add(self.mainframe, text="Versions", sticky="nsew")
        logger.info("Cleaning up any leftover update files...")
        if not os.path.isdir("assets"):
            os.mkdir("assets")
        if not os.path.isdir("temp"):
            os.mkdir("temp")
        try:
            os.remove(f"APLauncher_old{OS_SPECIFICS['defaultext']}")
            os.remove(f"launcher_process_old{OS_SPECIFICS['defaultext']}")
            logger.info("Update files cleaned up.")
        except:
            logger.info("No update files found.")
            pass
        logger.info("Downloading background and icon...")
        try:
            urlretrieve(url="https://raw.github.com/SpacePython12/AP-Launcher/main/assets/background.png", filename="assets/background.png")
            urlretrieve(url="https://raw.github.com/SpacePython12/AP-Launcher/main/assets/icon.ico", filename="assets/icon.ico")
            logger.info("Retrieved background and icon successfully.")
        except HTTPError:
            logger.info("Unable to retrieve background and icon, using cached.")
            pass
        except URLError:
            logger.info("Unable to retrieve background and icon, using cached.")
            pass
        self.background = ImageTk.PhotoImage(Image.open("assets/background.png"))
        self.icon = Image.open("assets/icon.ico")
        self.icon = ImageTk.PhotoImage(self.icon)
        self.win.iconphoto(True, self.icon)
        self.background2 = Canvas(self.mainframe, width=self.background.width(), height=self.background.height(), bd=0)
        self.background2.grid(column=0, row=0, sticky="nsew")
        self.background2.bind("<Configure>", lambda e: threading.Thread(None, target=lambda: self.resize_widgets(e)).start())
        self.versionvar = StringVar()
        self.get_versions()
        logger.info("Reading cache file...")
        try:
            self.cache = json.load(open("cache.json"))
            self.cache["launcherVersion"] = __version__
            json.dump(self.cache, open("cache.json", "w"))
            logger.info("Successfully read cache.")
        except FileNotFoundError:
            self.cache = {
                    "launcherVersion": __version__,
                    "username": "",
                    "accessid": {
                        "id": "",
                        "expiresAt": 0,
                        "msId": "",
                        "msRefreshId": "",
                        "msIdExpiresAt": 0,
                    },
                    "premium": False,
                    "selectedVersion": None,
                    "theme": "darkly"
                }
            logger.info("No cache file found.")
            json.dump(self.cache, open("cache.json", "w"))
        if type(self.cache["selectedVersion"]) is type(list()):
            self.versionvar.set(f'{self.cache["selectedVersion"][0]} ({self.cache["selectedVersion"][1]})')
        elif type(self.cache["selectedVersion"]) is type(None):
            try:
                self.versionvar.set(self.versions[0])
            except IndexError:
                pass
        if self.cache["accessid"]["expiresAt"] is None:
            self.cache["accessid"]["expiresAt"] = 0
        if int(self.cache["accessid"]["expiresAt"]) < int(time.time()):
            self.cache["accessid"]["id"] = ""
        if not "theme" in self.cache.keys():
            self.cache["theme"] = "darkly"
        self.accesstoken = self.cache["accessid"]["id"]
        self.username = self.cache["username"]
        self.accounttype = "microsoft"
        self.premium = self.cache["premium"]
        THEME.theme_use(self.cache["theme"])
        self.buttonframe = Frame(self.mainframe, padding=(10, 10))
        self.background2.create_window((0, 0), window=self.buttonframe, anchor="s")
        self.login_frame = Frame(self.buttonframe)
        self.login_frame.grid(column=0, row=0)
        self.connect_label = Label(self.login_frame, text=" Premium mode:  ")
        self.connect_label.grid(column=2, row=0)
        self.connect_var = IntVar(self.login_frame)
        self.connect_var.set(self.premium)
        self.connect_box = Checkbutton(self.login_frame, variable=self.connect_var)
        self.connect_box.grid(column=3, row=0)
        self.username_var = StringVar(self.login_frame)
        self.username_var.set(str(self.username))
        self.username_label = Label(self.login_frame, text="Username: ")
        self.username_label.grid(column=0, row=0)
        self.username_entry = Entry(self.login_frame, textvariable=self.username_var)
        self.username_entry.grid(column=1, row=0)
        self.login_button = Button(self.buttonframe, text="Login", command=lambda: self.login(self.username_var.get(), premium=bool(self.connect_var.get())))
        self.login_button.grid(column=2, row=0)
        self.toggle_premium_mode(self.username_label, self.username_entry, self.connect_var)
        self.connect_box.config(command=lambda: self.toggle_premium_mode(self.username_label, self.username_entry, self.connect_var))        
        self.versionlabel = Label(self.buttonframe, text="  Version:  ")
        self.versionlabel.grid(column=3, row=0)
        self.versionlist = Combobox(self.buttonframe, textvariable=self.versionvar, width=30, state="readonly")
        self.versionlist.grid(column=4, row=0)
        self.versionlist["values"] = self.versions
        self.playbutton = Button(self.win, text="\nPlay\n", command=lambda: self.start_game())
        self.playbutton.grid(column=0, row=2, sticky="nsew")
        self.playcontext = Menu(self.win, tearoff=0)
        self.playcontext.add_command(label="Kill Process", command=lambda: self.kill_process())
        self.playcontext.entryconfigure(0, state="disabled")
        self.playbutton.bind("<Button-3>", lambda x: self.do_popup(x))
        self.processframe = Frame(self.win)
        self.processframe.rowconfigure(0, weight=1)
        self.processframe.columnconfigure(0, weight=1)
        self.tabs.add(self.processframe, text="Game Output", sticky="nsew")
        self.processtext = ProcessBoundText(self.processframe, state="disabled")
        self.processtext.grid(column=0, row=0, sticky="nsew")
        self.profileframe = Frame(self.win, padding=5)
        self.profileframe.columnconfigure(0, weight=1)
        self.tabs.add(self.profileframe, text="Profiles")
        self.profileselect = Frame(self.profileframe)
        self.profileselect.grid(column=0, row=0, sticky="nsew")
        self.profilelabel = Label(self.profileselect, text="Profile: ")
        self.profilelabel.grid(column=0, row=0, sticky="nsew")
        self.profilelist = Combobox(self.profileselect, textvariable=self.versionvar, state="readonly")
        self.profilelist.grid(column=1, row=0, sticky="nsew")
        self.profilelist["values"] = self.versions
        try:
            self.profname = LabeledEntry(self.profileframe, "Name: ", self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["name"])
        except KeyError:
            self.profname = LabeledEntry(self.profileframe, "Name: ", "")
        self.profname.grid(column=0, row=1, sticky="nsew")
        self.profgamedir = LabeledEntry(self.profileframe, "Game Directory: ", self.minecraftdir, elength=30)
        self.profgamedir.grid(column=0, row=2, sticky="nsew")
        self.profjavadir = LabeledEntry(self.profileframe, "Java Directory: ", os.path.join(OS_SPECIFICS["java_home"], "bin", OS_SPECIFICS["java_executable"]), elength=30)
        self.profjavadir.grid(column=0, row=3, sticky="nsew")
        self.jvmargs = "-Xmx2G"
        if "javaArgs" in self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]:
            self.jvmargs = self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["javaArgs"]
        self.allocramraw = re.search(r"\-Xmx[0-9]+[MG]", self.jvmargs).group(0)[4:]
        if self.allocramraw[-1] == "M":
            self.scale = 0
        elif self.allocramraw[-1] == "G":
            self.scale = 1
        self.allocram = DoubleVar(self.win)
        self.allocram.set((float(self.allocramraw[:-1])))
        self.allocramlabel = Label(self.profileframe, text=f"Allocated RAM: {self.allocram.get()} GB", anchor="nw")
        self.allocramlabel.grid(column=0, row=4, sticky="nsew")
        self.allocramslider = tkinter.Scale(self.profileframe, from_=1.0, to=round(psutil.virtual_memory().total/(1024.**3), 1), resolution=0.1, showvalue=False, orient="horizontal", variable=self.allocram, command=self.update_alloc_ram, length=200)
        self.allocramslider.grid(column=0, row=5, sticky="nw")
        self.profsave = Button(self.profileframe, text="Save")
        self.profsave.grid(column=0, row=6, sticky="w")
        self.proftrans = Label(self.profileframe, text="OR")
        self.proftrans.grid(column=0, row=7, sticky="w")
        self.profadd = Button(self.profileframe, text="Import new version", command=lambda: self.open_install_archive())
        self.profadd.grid(column=0, row=8, sticky="w")
        self.availableversion = StringVar(self.win)
        self.availableversionlist = Combobox(self.profileframe, textvariable=self.availableversion, state="readonly")
        self.profadd = Button(self.profileframe, text="Create new version", command=lambda: self.add_available_versions())
        self.profadd.grid(column=0, row=10, sticky="w")
        self.update_profiles(self.versionvar.get())
        self.profilelist.bind("<<ComboboxSelected>>", lambda x: self.update_profiles(self.versionvar.get()))
        self.otherpage = OtherPage(self.win)
        self.otherpage.columnconfigure(0, weight=1)
        self.tabs.add(self.otherpage, text="Other")
        logger.info("Successfully initiated window.")

    def update_alloc_ram(self, e):
        self.allocramlabel.config(text=f"Allocated RAM: {round(self.allocram.get(), 1)} GB")
        oldarg = re.search(r"\-Xmx[0-9]+[MG]", self.jvmargs).group(0)
        if not self.allocram.get().is_integer():
            suffix = "M"
            self.jvmargs = self.jvmargs.replace(oldarg, f"-Xmx{round(self.allocram.get()*1024)}{suffix}")
        else:
            suffix = "G"
            self.jvmargs = self.jvmargs.replace(oldarg, f"-Xmx{int(self.allocram.get())}{suffix}")
    
    def resize_widgets(self, e):
        self.bgfile = Image.open("assets/background.png")
        self.bgfile = self.bgfile.resize((self.background2.winfo_width(), self.background2.winfo_height()), Image.ANTIALIAS)
        self.background = ImageTk.PhotoImage(self.bgfile)
        self.background2.create_image(0, 0, image=self.background, anchor="nw")
        self.background2.update()
        self.background2.create_window((int(self.background.width()/2), self.background.height()-5), window=self.buttonframe, anchor="s")

    def kill_process(self):
        """Kills the running Minecraft process."""
        try:
            subprocess.Popen(f'taskkill /FI "WindowTitle eq Minecraft*" /T /F', shell=True)
            subprocess.Popen(f'taskkill /IM launcher_process{OS_SPECIFICS["defaultext"]} /T /F', shell=True)
        except:
            messagebox.showerror("Error", "Unable to stop the process.")
            return
        else:
            messagebox.showinfo("Success", "The process was successfully terminated.")

    def do_popup(self, event):
        """Popup handler for the process killer"""
        try:
            self.playcontext.tk_popup(event.x_root, event.y_root)
        finally:
            self.playcontext.grab_release()

    def on_closing(self):
        """Saves info before the window is closed"""
        logger.info("Window has been closed, saving cache and profiles...")
        self.cache["theme"] = THEME.theme_use()
        json.dump(self.accounts, open(os.path.join(self.minecraftdir, "launcher_profiles.json"), "w"), indent=2)
        json.dump(self.cache, open("cache.json", "w"), indent=2)
        self.win.withdraw()
        threading.Thread(None, target=self.update_version, daemon=False).start()
        sys.exit()

    def get_versions(self):
        """Get all available versions and parses them"""
        profiles = list(self.accounts["profiles"].keys())
        versions = []
        occurences = {}
        for profile in profiles:
            name = self.accounts["profiles"][profile]["name"]
            if name in versions:
                if name in occurences.keys():
                    occurences[name] = occurences[name] + 1
                    name = f"{name} ({occurences[name]})"
                    self.accounts[profile]["name"] = name
                else:
                    occurences[name] = 1
                    name = f"{name} ({occurences[name]})"
                    self.accounts[profile]["name"] = name
            versions.append(f'{name} ({self.accounts["profiles"][profile]["lastVersionId"]})')
        self.profiles = profiles
        self.versions = versions
        self.nametoprofile = self.generate_nametoprofile()

    def generate_nametoprofile(self):
        """Generates a key for name to id conversion to make my life easier"""
        out = {}
        for version in self.versions:
            for profile in self.profiles:
                if version == f'{self.accounts["profiles"][profile]["name"]} ({self.accounts["profiles"][profile]["lastVersionId"]})':
                    out[version] = profile
        return out

    def get_accounts(self):
        """Gets launcher profiles"""
        return json.load(open(os.path.join(self.minecraftdir, "launcher_profiles.json")))

    def update_profiles(self, name):
        """Updates special game arguments"""
        try:
            self.profname.set(self.accounts["profiles"][self.nametoprofile[name]]["name"])
        except:
            pass
        try:
            self.profgamedir.set(self.accounts["profiles"][self.nametoprofile[name]]["gameDir"])
        except:
            pass
        try:
            self.profjavadir.set(self.accounts["profiles"][self.nametoprofile[name]]["javaDir"])
        except:
            pass
        try:
            self.jvmargs = self.accounts["profiles"][self.nametoprofile[name]]["javaArgs"]
        except:
            pass

    def save_profile(self, name):
        """Saves the selected profile."""
        self.accounts["profiles"][self.nametoprofile[name]] = {"name": self.profname.get(), "type": "custom", "lastVersionId": self.accounts["profiles"][self.nametoprofile[name]]["lastVersionId"], "gameDir": self.profgamedir.get(), "javaDir": self.profjavadir.get()}
        self.get_versions()
        self.versionlist["values"] = self.versions
        self.profilelist["values"] = self.versions
        if self.jvmargs != "-Xmx2G":
            self.accounts["profiles"][self.nametoprofile[name]]["javaArgs"] = self.jvmargs
        else:
            self.accounts["profiles"][self.nametoprofile[name]].remove("javaArgs")
        json.dump(open(os.path.join(self.minecraftdir, "launcher_profiles.json"), "w"), self.accounts)

    def login(self, username, premium=False):
        """True login process that requests an access token."""
        logger.info(f"Logging in as {username}")
        if username == "" and not premium:
            messagebox.showinfo("Try again", "No login info was provided.")
            return
        if not premium:
            self.accesstoken = ""
            self.username = username
            self.cache["username"] = username
            self.cache["premium"] = premium
        else:
            if not messagebox.askyesno("Experimental features ahead", "This is an experimental feature that has NOT been fully developed.\nI am NOT responsible for ANY damage that this inflicts on your AP Launcher or Minecraft installation.\nAre you sure you want to continue?"):
                return
            try:
                if not "msIdExpiresAt" in self.cache["accessid"].keys():
                    self.cache["accessid"]["msIdExpiresAt"] = 0
                if self.cache["accessid"]["msIdExpiresAt"] is None:
                    self.cache["accessid"]["msIdExpiresAt"] = 0
                if int(self.cache["accessid"]["msIdExpiresAt"]) < int(time.time()):
                    status = "signing into your Microsoft Account"
                    redirect_uri = "https://login.live.com/oauth20_desktop.srf"
                    if self.cache["accessid"]["msRefreshId"] == "":
                        url = "https://login.live.com/oauth20_authorize.srf"
                        query_params = {
                            "client_id": MS_CLI_ID,
                            "response_type": "code",
                            "approval_prompt": "true",
                            "scope": "Xboxlive.signin",
                            "redirect_uri": redirect_uri,
                        }
                        destination_url = requests.Request("GET", url, params=query_params).prepare().url
                        list_because_i_hate_you = [] #stay mad
                        login_win = webview.create_window("Login to your Microsoft account", destination_url)
                        webview.start(threading.Thread(None, lambda: self.watch_webview(login_win, list_because_i_hate_you)).start)
                        code = [x.lstrip("code=") for x in list_because_i_hate_you[0].split("?")[1].split("&") if x.startswith("code=")][0]
                        params = {
                            "grant_type": "authorization_code",
                            "client_id": MS_CLI_ID,
                            "scope": "Xboxlive.signin",
                            "code": code,
                            "redirect_uri": redirect_uri,
                        }
                    else:
                        params = {
                            "grant_type": "refresh_token",
                            "client_id": MS_CLI_ID,
                            "scope": "Xboxlive.signin",
                            "refresh_token": self.cache["accessid"]["msRefreshId"],
                            "redirect_uri": redirect_uri,
                        }
                    base_url = "https://login.live.com/oauth20_token.srf"
                    resp = requests.post(base_url, data=params)
                    ms_access_token = resp.json()["access_token"]
                    ms_refresh_token = resp.json()["refresh_token"].lstrip("M.R3_BAY.")
                    ms_access_expiry = int(resp.json()["expires_in"])
                    self.cache["accessid"]["msId"] = ms_access_token
                    self.cache["accessid"]["msIdExpiresAt"] = int(time.time()) + ms_access_expiry
                    self.cache["accessid"]["msRefreshId"] = ms_refresh_token
                if self.accesstoken == "":
                    status = "signing into Xbox Live"
                    url = "https://user.auth.xboxlive.com/user/authenticate"
                    headers = {"x-xbl-contract-version": "1"}
                    data = {
                        "RelyingParty": "http://auth.xboxlive.com",
                        "TokenType": "JWT",
                        "Properties": {
                            "AuthMethod": "RPS",
                            "SiteName": "user.auth.xboxlive.com",
                            "RpsTicket": "d=" + self.cache["accessid"]["msId"]
                        },
                    }
                    resp = requests.post(url, json=data, headers=headers)
                    xbox_user_token = resp.json()["Token"]
                    xbox_user_hash = resp.json()["DisplayClaims"]["xui"][0]["uhs"]
                    url = "https://xsts.auth.xboxlive.com/xsts/authorize"
                    headers = {"x-xbl-contract-version": "1"}
                    data = {
                        "RelyingParty": "rp://api.minecraftservices.com/",
                        "TokenType": "JWT",
                        "Properties": {
                            "UserTokens": [xbox_user_token],
                            "SandboxId": "RETAIL",
                        },
                    }
                    resp = requests.post(url, json=data, headers=headers)
                    xbox_access_token = resp.json()["Token"]
                    url = "https://api.minecraftservices.com/authentication/login_with_xbox"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "identityToken" : f"XBL3.0 x={xbox_user_hash};{xbox_access_token}",
                        "ensureLegacyEnabled" : True
                    }
                    resp = requests.post(url, json=data, headers=headers)
                    xuid = resp.json()["username"]
                    mc_access_token = resp.json()["access_token"]
                    mc_access_expiry = int(resp.json()["expires_in"])
                    self.cache["accessid"]["id"] = mc_access_token
                    self.cache["accessid"]["expiresAt"] = int(time.time()) + mc_access_expiry
                    url = "https://api.minecraftservices.com/minecraft/profile"
                    headers = {"Authorization": f"Bearer {mc_access_token}"}
                    resp = requests.get(url, headers=headers)
                    if "error" in resp.json().keys():
                        messagebox.showerror("Invalid account", "This Microsoft account does not appear to own Minecraft.")
                        return
                    mc_uuid = resp.json()["id"]
                    self.username = resp.json()["name"]
                    account_json = json.load(open(os.path.join(self.minecraftdir, "launcher_accounts.json")))
                    accounts = [account for account in account_json["accounts"].keys() if account_json["accounts"][account]["minecraftProfile"]["name"] == self.username]
                    if len(accounts) == 0:
                        account_json["accounts"][str(uuid.uuid4().hex).replace("-", "")] = {
                            "minecraftProfile": {
                                "id": mc_uuid,
                                "name": self.username
                            }
                        }
                    for account in accounts:
                        account_json["accounts"][account]["minecraftProfile"]["id"] = mc_uuid
                    json.dump(account_json, open(os.path.join(self.minecraftdir, "launcher_accounts.json"), "w"))
            except:
                logger.error("Unable to login", exc_info=True)
                messagebox.showerror("Unable to login", f"There was a problem when {status}.")

    def watch_webview(self, window: webview.Window, l: list):
        """Blocks until webview leaves login page."""
        while not window.get_current_url().startswith("https://login.live.com/oauth20_desktop.srf"):
            pass
        l.clear()
        l.append(window.get_current_url())
        window.destroy()

    def start_game(self):
        """Starts the game"""
        logger.info("Starting the game...")
        if self.accesstoken == "" and self.username == "":
            messagebox.showinfo("Please Login", "You must login to play Minecraft.")
            return
        self.cache["selectedVersion"] = [self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["name"], self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastVersionId"]]
        if self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastVersionId"] == "latest-release":
            self.currentversion = self.get_latest_version("release")
        elif self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastVersionId"] == "latest-snapshot":
            self.currentversion = self.get_latest_version("snapshot")
        else:
            self.currentversion = self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastVersionId"]
        self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastUsed"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        thread = threading.Thread(None, lambda: self.sbloop())
        thread.start()

    def sbloop(self):
        """Launcher process"""
        self.playbutton.config(state="disabled", text="\nPlaying...\n")
        self.playcontext.entryconfigure(0, state="normal")
        cmdargs = [
        "launcher_process",
        "--username",
        self.username,
        "--version",
        self.currentversion,
        "--accessToken",
        str(self.accesstoken),
        "--accountType",
        self.accounttype,
        "--mcDir",
        self.profgamedir.get(),
        "--javaHome",
        self.profjavadir.get(),
        "--javaArgs",
        self.jvmargs.replace("-", "+")
        ]
        sb = subprocess.Popen(
        cmdargs, 
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True
        )
        logger.info("Process started successfully.")
        self.processtext.monitor(sb)
        code = sb.returncode
        if code > 0:
            messagebox.showerror("Game Crashed", "Unfortunately, the game has crashed.\nCode:" + str(code))
        self.playbutton.config(state="normal", text="\nPlay\n")
        self.playcontext.entryconfigure(0, state="disabled")

    def update_procscreen(self, text):
        """Updates the console screen"""
        self.processtext.config(state="normal")
        self.processtext.insert("end", text)
        self.processtext.config(state="disabled")
        self.processtext.see("end")
        self.processtext.update_idletasks()
        
    def toggle_premium_mode(self, ul, ue, cv):
        """Toggles between premium and cracked mode"""
        if cv.get() == 1:
            ul.grid_forget()
            ue.grid_forget()
        elif cv.get() == 0:
            ul.grid(column=0, row=0)
            ue.grid(column=1, row=0)
        
    def get_latest_version(self, type_):
        """Finds the 'latest' version and snapshot"""
        versions = [x[0] for x in os.walk(os.path.join(self.minecraftdir, "versions"))]
        if type_ == "release":
            filtered = [x.split(os.sep)[-1][:6] for x in versions if bool(re.match(r"1\.[0-9]+\.[1-9]+", x.split(os.sep)[-1])) or bool(re.match(r"1\.[0-9]+", x.split("\\")[-1]))]
            for x in range(len(filtered)):
                if bool(re.match(r"1\.[0-9]+", filtered[x])):
                    filtered[x] += ".0"
            ranked = [int(x.replace(".", "")) for x in filtered]
            if filtered[ranked.index(max(ranked))].endswith(".0"):
                return filtered[ranked.index(max(ranked))].rstrip(".0")
        elif type_ == "snapshot":
            filtered = [x.split(os.sep)[-1][:6] for x in versions if bool(re.match("[0-9][0-9]w[0-9][0-9]a", x.split(os.sep)[-1]))]
            ranked = [int(x.replace("w", "").replace("a", "")) for x in filtered]
            return filtered[ranked.index(max(ranked))]

    @staticmethod
    def update_java():
        """Downloads Java to home directory."""
        logger.info("A Java installation was not found, downloading now...")
        urlretrieve(OS_SPECIFICS["java_install_url"], f"java/java{OS_SPECIFICS['java_install_ext']}")
        if OS_SPECIFICS["java_install_ext"] == ".zip":
            f = ZipFile(open(f"java/java{OS_SPECIFICS['java_install_ext']}", "rb"))
            f.extractall("java")
        elif OS_SPECIFICS["java_install_ext"] == ".tar.gz":
            f = TarFile(open(f"java/java{OS_SPECIFICS['java_install_ext']}", "rb"))
            f.extractall("java")
        f.close()
        os.remove(f"java/java{OS_SPECIFICS['java_install_ext']}")

    def open_install_archive(self):
        """Opens version files to install them."""
        logger.info("Opening version file...")
        filepath = filedialog.askopenfilename(master=self.win, title="Open version file", filetypes=[("ZIP files", "*.zip")])
        if filepath == "":
            return
        with ZipFile(open(filepath, "rb")) as zf:
            folders = list(set([os.path.dirname(x).split("/")[0] for x in zf.namelist()]))
            try:
                folders.remove("indexes")
            except ValueError:
                pass
            try:
                folders.remove("natives")
            except ValueError:
                pass
            try:
                folders.remove("libraries")
            except ValueError:
                pass
            try:
                folders.remove("objects")
            except ValueError:
                pass
            folders.remove("")
            infofile = zf.open("manifest.json")
            info = json.load(infofile)
            for folder in folders:
                logger.info(f"Extracting version {folder}...")
                if os.path.isdir(os.path.join(self.minecraftdir, "versions", folder)):
                    if not messagebox.askyesno("Confirm", f"There is already a version by the name '{folder}'. Would you like to overwrite it?"):
                        zf.close()
                        return
                    else:
                        shutil.rmtree(os.path.join(self.minecraftdir, "versions", folder))
                        os.mkdir(os.path.join(self.minecraftdir, "versions", folder))
                for file_ in zf.namelist():
                    if file_.startswith(folder):
                        zf.extract(file_, os.path.join(self.minecraftdir, "versions"))
                info["profile"][list(info["profile"].keys())[0]]["created"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
                self.accounts["profiles"][list(info["profile"].keys())[0]] = info["profile"][list(info["profile"].keys())[0]]
            logger.info("Extracting assets...")
            for file_ in zf.namelist():
                if file_.startswith("indexes"):
                    zf.extract(file_, os.path.join(self.minecraftdir, "assets"))
            for file_ in zf.namelist():
                if file_.startswith("objects"):
                    zf.extract(file_, os.path.join(self.minecraftdir, "assets"))
            logger.info("Extracting required DLL files...")
            for file_ in zf.namelist():
                dllpath = os.path.join(self.minecraftdir, "bin", "natives")
                if not os.path.isdir(dllpath):
                    os.makedirs(dllpath, exist_ok=True)
                if file_.startswith("natives"):
                    zf.extract(file_, os.path.join(self.minecraftdir, "bin"))
            logger.info("Extracting libraries...")
            for file_ in zf.namelist():
                if file_.startswith("libraries"):
                    if not os.path.isdir(os.path.join(self.minecraftdir, *file_.split("/")[:-1])):
                        os.makedirs(os.path.join(self.minecraftdir, *file_.split("/")[:-1]), exist_ok=True)
                    zf.extract(file_, self.minecraftdir)
            messagebox.showinfo("Success", "The version was successfully imported. Restart AP Launcher to see changes.")
            zf.close()
            return

    def update_version(self, local=False):
        """Update process"""
        names = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}
        if not local:
            logger.info("Checking for updates...")
            request = requests.get("https://api.github.com/repos/SpacePython12/AP-Launcher/releases").json() 
            latest = [x for x in request if not x["prerelease"]][0]
            installer_archive = ""
            for vfile in latest["assets"]:
                if vfile["name"] == "APLauncher.zip":
                    if not os.path.exists("update"):
                        os.mkdir("update")
                    urlretrieve(vfile["browser_download_url"], os.path.join("update", vfile["name"]))
                    installer_archive = vfile["name"]
                    break
        else:
            installer_archive = "APLauncher.zip"
        if platform.system() == "Windows":
            include = ["windows/APLauncher.exe", "windows/launcher_process.exe"]
            install_command = ["update/windows.bat"]
        elif platform.system() == "Darwin":
            include = ["macos/APLauncher", "macos/launcher_process"]
            install_command = ["chmod +x update/macos.sh", "sh update/macos.sh"]
        elif platform.system() == "Linux":
            include = ["linux/APLauncher", "linux/launcher_process"]
            install_command = ["chmod +x update/linux.sh", "sh update/linux.sh"]
        with zipfile.ZipFile(os.path.join("update", installer_archive)) as i:
            i.extractall("update", include)
            for f in os.listdir(os.path.join("update", names[platform.system()])):
                os.rename(f, f.replace(OS_SPECIFICS["defaultext"], "") + "_old" + OS_SPECIFICS["defaultext"])
                shutil.move(os.path.join("update", names[platform.system()], f), f)
        

    def get_available_versions(self):
        """Tries to download version manifest, then adds versions found in .minecraft folder to a list."""
        available_versions = []
        for d in os.listdir(os.path.join(self.minecraftdir, "versions")):
            if os.path.isdir(os.path.join(self.minecraftdir, "versions", d)):
                available_versions.append(d)
        try:
            requests.get("https://launchermeta.mojang.com/mc/game/version_manifest.json", allow_redirects=False)
        except:
            pass
        else:
            urlretrieve("https://launchermeta.mojang.com/mc/game/version_manifest.json", os.path.join(self.minecraftdir, "versions", "version_manifest.json"))
            new_versions = json.load(open(os.path.join(self.minecraftdir, "versions", "version_manifest.json")))
            for version in new_versions["versions"]:
                available_versions.append(version["id"])
        self.availableversions = available_versions
        self.availableversion.set(self.availableversions[0])
        self.availableversionlist["values"] = self.availableversions
        self.availableversionlist.grid(column=0, row=9, sticky="w")
        
    def add_available_versions(self):
        """Downloads selected version, if it isn't local."""
        chosen = self.availableversion.get()
        if os.path.isfile(os.path.join(self.minecraftdir, "versions", "version_manifest.json")):
            new_versions = json.load(open(os.path.join(self.minecraftdir, "versions", "version_manifest.json")))
            if chosen in [new_versions["versions"][i]["id"] for i in range(len(new_versions["versions"]))]:
                url = [new_versions["versions"][i]["url"] for i in range(len(new_versions["versions"])) if new_versions["versions"][i]["id"] == chosen][0]
                os.mkdir(os.path.join(self.minecraftdir, "versions", chosen))
                urlretrieve(url, os.path.join(self.minecraftdir, "versions", chosen, f"{chosen}.json"))

if __name__ == "__main__":
    if not os.path.isdir("launcher_logs"):
        os.mkdir("launcher_logs")
    if not os.path.isdir("launcher_logs/gui"):
        os.mkdir("launcher_logs/gui")        
    if os.path.isfile("launcher_logs/gui/latest.log"):
        createtime = datetime.datetime.fromtimestamp(os.path.getctime("launcher_logs/gui/latest.log")).strftime("%Y-%m-%d")
        num = 1
        while os.path.isfile(f"launcher_logs/gui/{createtime}-{num}.log"):
            num += 1
        try:
            os.rename("launcher_logs/gui/latest.log", f"launcher_logs/gui/{createtime}-{num}.log")
        except:
            sys.exit()
    fmt = "[%(asctime)s] (Process %(processName)s thread %(threadName)s func %(funcName)s/%(levelname)s): %(message)s"
    logging.basicConfig(filename="launcher_logs/gui/latest.log", format=fmt, level=logging.INFO)
    logger = logging.getLogger()
    OS_SPECIFICS_MAP = {
        "Windows": {
            "name": "windows",
            "defaultext": ".exe",
            "java_install_url": "https://corretto.aws/downloads/latest/amazon-corretto-17-x64-windows-jdk.zip",
            "java_install_ext": ".zip",
            "java_executable": "java.exe",
            "filesystem_sep": "\\",
            "default_minecraft_dir": f"C:\\Users\\{getpass.getuser()}\\AppData\\Roaming\\.minecraft"
        },
        "Darwin": {
            "name": "osx",
            "defaultext": "",
            "java_install_url": "https://corretto.aws/downloads/latest/amazon-corretto-17-x64-macos-jdk.tar.gz",
            "java_install_ext": ".tar.gz",
            "java_executable": "java",
            "filesystem_sep": "/",
            "default_minecraft_dir": "/Library/Application Support/minecraft"
        },
        "Linux": {
            "name": "linux",
            "defaultext": "",
            "java_install_url": "https://corretto.aws/downloads/latest/amazon-corretto-17-x64-linux-jdk.tar.gz",
            "java_install_ext": ".tar.gz",
            "java_executable": "java",
            "filesystem_sep": "/",
            "default_minecraft_dir": f"/home/{getpass.getuser()}/.minecraft"
        }
    }
    OS_SPECIFICS = OS_SPECIFICS_MAP[platform.system()]
    MS_CLI_ID = "4e43efcb-1376-4e12-9232-def91c06c074"
    if not os.path.exists(os.path.join(os.getcwd(), "java")):
        os.mkdir(os.path.join(os.getcwd(), "java"))
        App.update_java()
    elif len(os.listdir(os.path.join(os.getcwd(), "java"))) == 0:
        App.update_java()
    if platform.system() == "Windows":
        OS_SPECIFICS["java_home"] = os.path.join(os.getcwd(), "java", [x[1] for x in os.walk("java")][0][0])
    elif platform.system() == "Darwin":
        OS_SPECIFICS["java_home"] = os.path.join(os.getcwd(), "java", [x[1] for x in os.walk("java")][0][0], "Contents", "Home")
    elif platform.system() == "Linux":
        OS_SPECIFICS["java_home"] = os.path.join(os.getcwd(), "java")
    try:
        main = App()
        if "--update" in sys.argv and len(os.listdir("update")) > 0:
            main.update_version(local=True)
    except BaseException as e:
        messagebox.showerror("Fatal error", "A fatal error has occurred during startup.")
        logger.error(e, exc_info=True)
        traceback.print_exc(file=open("launcher_logs/error.log", "w"))
        send_error_report(fatal=True)
        sys.exit()
    try:
        main.win.mainloop()
    except BaseException as e:
        if not type(e).__name__ == "SystemExit":
            messagebox.showerror("Fatal error", "A fatal error has occurred during runtime.")
            logger.error(e, exc_info=True)
            traceback.print_exc(file=open("launcher_logs/error.log", "w"))
            send_error_report(fatal=True)
            main.win.destroy()
            sys.exit()