from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox, filedialog 
from PIL import ImageTk, Image
from urllib.request import urlretrieve
from urllib.error import *
from zipfile import ZipFile
import os
import json
import uuid
import requests
import subprocess
import threading
import re
import shutil
import datetime
import webview
import hashlib
import atexit
import webbrowser
import configparser

VERSION = "0.8"

class AboutPage(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.titlelabel = Label(self, text=f"Links:", anchor="w")
        self.titlelabel.grid(column=0, row=0, sticky="nsew")
        self.bugreportlabel = Label(self, text="     Found a bug? Report it here!", foreground="blue", cursor="hand2")
        self.bugreportlabel.grid(column=0, row=1, sticky="nsew")
        self.bugreportlabel.bind("<Button-1>", lambda e: self.open_link("https://github.com/SpacePython12/AP-Launcher/issues/new"))

    def open_link(self, url):
        webbrowser.open_new(url)

class LabeledEntry(Frame):

    def __init__(self, parent, label: str, defaultval: str, elength=20):
        super().__init__(parent)
        self.label = Label(self, text=label)
        self.entryvar = StringVar(self)
        self.entryvar.set(defaultval)
        self.entry = Entry(self, textvariable=self.entryvar, width=elength)

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

class App:

    def __init__(self):
        self.win = Tk()
        self.win.title(f"AP Launcher v{VERSION}")
        self.tabs = Notebook(self.win)
        self.tabs.grid()
        self.minecraftdir = os.path.join(os.getenv('APPDATA'), '.minecraft')
        self.win.protocol("WM_DESTROY_WINDOW", lambda: self.on_closing())
        self.win.protocol("WM_DELETE_WINDOW", lambda: self.on_closing())
        self.accounts = self.get_accounts()
        self.mainframe = Frame(self.win)
        self.tabs.add(self.mainframe, text="Versions", sticky="nsew")
        if not os.path.isdir("assets"):
            os.mkdir("assets")
        if not os.path.isdir("temp"):
            os.mkdir("temp")
        try:
            urlretrieve(url="https://raw.github.com/SpacePython12/AP-Launcher/main/assets/background.png", filename="assets/background.png")
            urlretrieve(url="https://raw.github.com/SpacePython12/AP-Launcher/main/assets/icon.ico", filename="assets/icon.ico")
        except HTTPError:
            pass
        except URLError:
            pass
        self.background = ImageTk.PhotoImage(Image.open("assets/background.png"))
        self.icon = ImageTk.PhotoImage(file="assets/icon.ico")
        self.win.iconphoto(True, self.icon)
        self.background2 = Label(self.mainframe, image=self.background)
        self.background2.grid(column=0, row=0, sticky="nsew")
        self.versionvar = StringVar()
        self.get_versions()
        try:
            self.cache = json.load(open("cache.json"))
        except FileNotFoundError:
            self.cache = {
                    "username": "",
                    "accessid": {
                        "id": None,
                        "expiresAt": None
                    },
                    "premium": True,
                    "selectedVersion": None
                }
        if type(self.cache["selectedVersion"]) is type(list()):
            self.versionvar.set(f'{self.cache["selectedVersion"][0]} ({self.cache["selectedVersion"][1]})')
        elif type(self.cache["selectedVersion"]) is type(None):
            try:
                self.versionvar.set(self.versions[0])
            except IndexError:
                pass
        self.accesstoken = self.cache["accessid"]["id"]
        self.username = self.cache["username"]
        self.accounttype = "microsoft"
        self.premium = self.cache["premium"]
        self.buttonframe = Frame(self.mainframe)
        self.buttonframe.grid(column=0, row=1)
        self.login_frame = Frame(self.buttonframe)
        self.login_frame.grid(column=0, row=0)
        self.connect_label = Label(self.login_frame, text=" Premium mode: ")
        self.connect_label.grid(column=2, row=0)
        self.connect_var = IntVar(self.login_frame)
        self.connect_var.set(self.premium)
        self.connect_box = Checkbutton(self.login_frame, variable=self.connect_var)
        self.connect_box.grid(column=3, row=0)
        self.username_var = StringVar(self.login_frame)
        self.username_var.set(str(self.username))
        self.username_label = Label(self.login_frame, text="Username:")
        self.username_label.grid(column=0, row=0)
        self.username_entry = Entry(self.login_frame, textvariable=self.username_var)
        self.username_entry.grid(column=1, row=0)
        self.login_button = Button(self.buttonframe, text="Login", command=lambda: self.login(self.username_var.get(), premium=bool(self.connect_var.get())))
        self.login_button.grid(column=2, row=0)
        self.toggle_premium_mode(self.username_label, self.username_entry, self.connect_var)
        self.connect_box.config(command=lambda: self.toggle_premium_mode(self.username_label, self.username_entry, self.connect_var))        
        self.versionlabel = Label(self.buttonframe, text="Version: ")
        self.versionlabel.grid(column=3, row=0)
        self.versionlist = Combobox(self.buttonframe, textvariable=self.versionvar, width=30)
        self.versionlist.grid(column=4, row=0)
        self.versionlist["values"] = self.versions
        self.playbutton = Button(self.win, text="\nPlay\n", command=lambda: self.start_game())
        self.playbutton.grid(column=0, row=2, sticky="nsew")
        self.playcontext = Menu(self.win, tearoff=0)
        self.playcontext.add_command(label="Kill Process", command=lambda: self.kill_process())
        self.playcontext.entryconfigure(0, state="disabled")
        self.playbutton.bind("<Button-3>", lambda x: self.do_popup(x))
        self.processframe = Frame(self.win)
        self.tabs.add(self.processframe, text="Game Output")
        self.processtext = ScrolledText(self.processframe, state="disabled", height=35, width=120)
        self.processtext.grid(column=0, row=2, sticky="nsew")
        self.profileframe = Frame(self.win)
        self.tabs.add(self.profileframe, text="Profiles")
        self.profileselect = Frame(self.profileframe)
        self.profileselect.grid(column=0, row=0, sticky="nsew")
        self.profilelabel = Label(self.profileselect, text="Profile: ")
        self.profilelabel.grid(column=0, row=0, sticky="nsew")
        self.profilelist = Combobox(self.profileselect, textvariable=self.versionvar)
        self.profilelist.grid(column=1, row=0, sticky="nsew")
        self.profilelist["values"] = self.versions
        try:
            self.profname = LabeledEntry(self.profileframe, "Name: ", self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["name"])
        except KeyError:
            self.profname = LabeledEntry(self.profileframe, "Name: ", "N/A")
        self.profname.grid(column=0, row=1, sticky="nsew")
        self.profgamedir = LabeledEntry(self.profileframe, "Game Directory: ", os.path.join(os.getenv('APPDATA'), '.minecraft'), elength=30)
        self.profgamedir.grid(column=0, row=2, sticky="nsew")
        if not os.path.isdir("java"):
            os.mkdir("java")
        if len([x[1] for x in os.walk("java")][0]) == 0:
            self.update_java()
        java_home = os.path.join(os.getcwd(), "java", [x[1] for x in os.walk("java")][0][0])
        self.profjavadir = LabeledEntry(self.profileframe, "Java Directory: ", f'{java_home}\\bin\\javaw.exe', elength=30)
        self.profjavadir.grid(column=0, row=3, sticky="nsew")
        self.profjavargs = LabeledEntry(self.profileframe, "JVM Arguments: ", "-Xmx2G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M", elength=50)
        self.profjavargs.grid(column=0, row=4, sticky="nsew")
        self.profsave = Button(self.profileframe, text="Save")
        self.profsave.grid(column=0, row=5, sticky="nsew")
        self.proftrans = Label(self.profileframe, text="OR")
        self.proftrans.grid(column=0, row=6, sticky="nsew")
        self.profadd = Button(self.profileframe, text="Import new version", command=lambda: self.open_install_archive())
        self.profadd.grid(column=0, row=7, sticky="nsew")
        self.update_profiles(self.versionvar.get())
        self.profilelist.bind("<<ComboboxSelected>>", lambda x: self.update_profiles(self.versionvar.get()))
        self.aboutpage = AboutPage(self.win)
        self.tabs.add(self.aboutpage, text="About")

    def kill_process(self):
        """Kills the running Minecraft process. I dont really know what to do about this function..."""
        try: 
            temp = open("temp.txt")
        except FileNotFoundError:
            messagebox.showerror("Error", "Unable to stop the process because the process id was not loaded.")
            return
        try:
            pid = int(temp.read())
        except:
            messagebox.showerror("Error", "Unable to stop the process because the process id was corrupted.")
            return
        try:
            os.system(f"taskkill /pid {pid} /f")
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
        json.dump(self.accounts, open(os.path.join(self.minecraftdir, "launcher_profiles.json"), "w"), indent=2)
        json.dump(self.cache, open("cache.json", "w"), indent=2)
        self.win.withdraw()
        if self.update_version():
            atexit.register(lambda: self.run_updater())
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
            self.profjavargs.set(self.accounts["profiles"][self.nametoprofile[name]]["javaArgs"])
        except:
            pass

    def save_profile(self, name):
        """Saves the selected profile."""
        self.accounts["profiles"][self.nametoprofile[name]] = {"name": self.profname.get(), "type": "custom", "lastVersionId": self.accounts["profiles"][self.nametoprofile[name]]["lastVersionId"], "gameDir": self.profgamedir.get(), "javaDir": self.profjavadir.get(), "javaArgs": self.profjavargs.get()}
        self.get_versions()
        self.versionlist["values"] = self.versions
        self.profilelist["values"] = self.versions
        json.dump(open(os.path.join(self.minecraftdir, "launcher_profiles.json"), "w"), self.accounts)

    def login(self, username, error=True, premium=False):
        """True login process that requests an access token. (Unfinished)"""
        if username == "":
            messagebox.showinfo("Try again", "No login info was provided.")
            return
        if not premium:
            self.accesstoken = ""
            self.username = username
            self.cache["username"] = username
            self.cache["premium"] = premium
        else:
            messagebox.showinfo("Not yet implemented", "Currently, AP Launcher does not support premium accounts.")
            return
            url = ""
            login_window = webview.create_window("Login to your Microsoft account", url)
            webview.start()

    def start_game(self):
        """Starts the game"""
        if self.accesstoken is None and self.username is None:
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
        self.playbutton.config(state="disabled", text="\nRunning...\n")
        self.playcontext.entryconfigure(0, state="normal")
        cmdargs = [
        "launcher_process",
        "-username",
        self.username,
        "-version",
        self.currentversion,
        "-accessToken",
        str(self.accesstoken),
        "-accountType",
        self.accounttype,
        "-mcDir",
        self.profgamedir.get(),
        "-javaHome",
        self.profjavadir.get(),
        "-javaArgs",
        self.profjavargs.get()
        ]
        sb = subprocess.Popen(
        cmdargs, 
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL
        )
        while sb.poll() is None:
            line = sb.stdout.readline().decode("ISO-8859-1").rstrip()
            if not line == "":
                self.update_procscreen(line)
        self.playbutton.config(state="normal", text="\nPlay\n")
        self.playcontext.entryconfigure(0, state="disabled")

    def update_procscreen(self, text):
        """Updates the console screen"""
        self.processtext.config(state="normal")
        self.processtext.insert("end", text+"\n")
        self.processtext.config(state="disabled")
        self.processtext.see("end")
        
    def toggle_premium_mode(self, ul, ue, cv):
        if cv.get() == 1:
            ul.grid_forget()
            ue.grid_forget()
        elif cv.get() == 0:
            ul.grid(column=0, row=0)
            ue.grid(column=1, row=0)
        
    def get_latest_version(self, type_):
        versions = [x[0] for x in os.walk(os.path.join(self.minecraftdir, "versions"))]
        if type_ == "release":
            filtered = [x.split("\\")[-1][:6] for x in versions if bool(re.match("1\.[0-9]+\.[1-9]+", x.split("\\")[-1])) or bool(re.match("1\.[0-9]+", x.split("\\")[-1]))]
            for x in range(len(filtered)):
                if bool(re.match("1\.[0-9]+", filtered[x])):
                    filtered[x] += ".0"
            ranked = [int(x.replace(".", "")) for x in filtered]
            if filtered[ranked.index(max(ranked))].endswith(".0"):
                return filtered[ranked.index(max(ranked))].rstrip(".0")
        elif type_ == "snapshot":
            filtered = [x.split("\\")[-1][:6] for x in versions if bool(re.match("[0-9][0-9]w[0-9][0-9]a", x.split("\\")[-1]))]
            ranked = [int(x.replace("w", "").replace("a", "")) for x in filtered]
            return filtered[ranked.index(max(ranked))]

    def update_java(self):
        urlretrieve("https://corretto.aws/downloads/latest/amazon-corretto-16-x64-windows-jdk.zip", "java/java.zip")
        with ZipFile(open("java/java.zip", "rb")) as zf:
            zf.extractall("java")
            zf.close()
        os.remove("java/java.zip")

    def open_install_archive(self):
        filepath = filedialog.askopenfilename(master=self.win, title="Open version file", filetypes=[("ZIP files", "*.zip")])
        if filepath == "":
            return
        with ZipFile(open(filepath, "rb")) as zf:
            folders = list(set([os.path.dirname(x).split("/")[0] for x in zf.namelist()]))
            folders.remove("indexes")
            folders.remove("natives")
            folders.remove("")
            infofile = zf.open("manifest.json")
            info = json.load(infofile)
            for folder in folders:
                if os.path.isdir(os.path.join(self.minecraftdir, "versions", folder)):
                    if not messagebox.askyesno("Confirm", "There is already a version by this name. Would you like to overwrite it?"):
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
            for file_ in zf.namelist():
                if file_.startswith("indexes"):
                    zf.extract(file_, os.path.join(self.minecraftdir, "assets"))
            for file_ in zf.namelist():
                if file_.startswith("natives"):
                    zf.extract(file_, os.path.join(self.minecraftdir, "bin"))
            messagebox.showinfo("Success", "The version was successfully imported. Restart AP Launcher to see changes.")
            zf.close()
            return

    def update_version(self):
        request = requests.get("https://api.github.com/repos/SpacePython12/AP-Launcher/releases").json()
        if os.path.isfile("APLauncher.exe") and os.path.isfile("launcher_process.exe"):
            hash1 = hashlib.sha1()
            for f in ["APLauncher.exe", "launcher_process.exe"]:
                with open(f, "rb") as f2:
                    data = f2.read()
                    hash1.update(data)
                    f2.close()
            durl = None
            for asset in request[0]["assets"]:
                if asset["name"] == "update.zip":
                    durl = asset["browser_download_url"]
                    break
            if durl is None:
                return False
            if not os.path.isdir("update"):
                os.mkdir("update")
            urlretrieve(url=durl, filename="update/update.zip")
            if os.path.isfile("update/APLauncher.exe"):
                os.remove("update/APLauncher.exe")
            if os.path.isfile("update/launcher_process.exe"):
                os.remove("update/launcher_process.exe")
            with ZipFile(open("update/update.zip", "rb")) as zf:
                zf.extractall("update")
                zf.close()
            os.remove("update/update.zip")
            hash2 = hashlib.sha1()
            for f in ["update/APLauncher.exe", "update/launcher_process.exe"]:
                with open(f, "rb") as f2:
                    data = f2.read()
                    hash2.update(data)
                    f2.close()
            return True
        else:
            return False

    def run_updater(self):
        if os.path.isfile("APLauncher.exe"):
            os.remove("APLauncher.exe")
        if os.path.isfile("launcher_process.exe"):
            os.remove("launcher_process.exe")
        shutil.move("update/APLauncher.exe", "APLauncher.exe")
        shutil.move("update/launcher_process.exe", "launcher_process.exe")

if __name__ == "__main__":
    main = App()
    main.win.mainloop()