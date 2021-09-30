from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
from PIL import ImageTk, Image
from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import json
import uuid
import requests
import subprocess
import threading
import re

class SettingsPage(Frame):

    def __init__(self, parent):
        super().__init__(parent)
        self.label = Label(self, text="Settings page coming soon!")

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
        self.win.title("AP Launcher")
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
        urlretrieve("https://raw.github.com/SpacePython12/AP-Launcher/main/assets/background.png", "assets/background.png")
        self.background = ImageTk.PhotoImage(Image.open("assets/background.png"))
        self.background2 = Label(self.mainframe, image=self.background)
        self.background2.grid(column=0, row=0, sticky="nsew")
        self.buttonframe = Frame(self.mainframe)
        self.buttonframe.grid(column=0, row=1)
        self.accountlabel = Label(self.buttonframe, text="Account: ")
        self.accountlabel.grid(column=1, row=0)
        self.accountbutton = Button(self.buttonframe, text="Choose...", command=lambda: self.accountdialog())
        self.accountbutton.grid(column=2, row=0)
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
                    "premium": True
                }
        try:
            self.versionvar.set(f'{self.cache["selectedVersion"][0]} ({self.cache["selectedVersion"][1]})')
        except KeyError:
            self.versionvar.set(self.versions[0])
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
        self.tabs.add(self.profileframe, text="Edit Profiles")
        self.profileselect = Frame(self.profileframe)
        self.profileselect.grid(column=0, row=0, sticky="nsew")
        self.profilelabel = Label(self.profileselect, text="Profile: ")
        self.profilelabel.grid(column=0, row=0, sticky="nsew")
        self.profilelist = Combobox(self.profileselect, textvariable=self.versionvar)
        self.profilelist.grid(column=1, row=0, sticky="nsew")
        self.profilelist["values"] = self.versions
        self.profname = LabeledEntry(self.profileframe, "Name: ", self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["name"])
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
        self.update_profiles(self.versionvar.get())
        self.profilelist.bind("<<ComboboxSelected>>", lambda x: self.update_profiles(self.versionvar.get()))
        self.accesstoken = self.cache["accessid"]["id"]
        self.username = self.cache["username"]
        self.accounttype = "microsoft"
        self.premium = self.cache["premium"]
        if not self.username == "":
            if self.premium:
                type_ = "Premium"
            else:
                type_ = "Non-Premium"
            self.accountbutton.config(text=f"{self.username} ({type_})")

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
        self.accounts["selectedProfile"] = self.versionvar.get()
        json.dump(self.accounts, open(os.path.join(self.minecraftdir, "launcher_profiles.json"), "w"), indent=2)
        json.dump(self.cache, open("cache.json", "w"), indent=2)
        self.win.withdraw()
        quit()

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

    def accountdialog(self):
        """Login dialog"""
        dwin = Toplevel(self.win)
        dwin.title("Accounts")
        login_frame = Frame(dwin)
        login_frame.pack(side="left")
        connect_label = Label(login_frame, text="Premium mode: ")
        connect_label.grid(column=0, row=0)
        connect_var = IntVar(login_frame)
        connect_var.set(self.premium)
        connect_box = Checkbutton(login_frame, variable=connect_var)
        connect_box.grid(column=1, row=0)
        type_label = Label(login_frame, text="Legacy (Mojang) account:")
        type_label.grid(column=0, row=1)
        type_var = IntVar(login_frame)
        type_var.set(0)
        type_box = Checkbutton(login_frame, variable=type_var)
        type_box.grid(column=1, row=1)
        username_var = StringVar(login_frame)
        username_var.set(str(self.username))
        username_label = Label(login_frame, text="Email:")
        username_label.grid(column=0, row=2)
        username_entry = Entry(login_frame, textvariable=username_var)
        username_entry.grid(column=1, row=2)
        password_var = StringVar(login_frame)
        password_label = Label(login_frame, text="Password:")
        password_label.grid(column=0, row=3)
        password_entry = Entry(login_frame, textvariable=password_var, show="•")
        password_entry.grid(column=1, row=3)
        login_button = Button(login_frame, text="Login", command=lambda: self.login(dwin, username_var.get(), password_var.get(), premium=bool(connect_var.get())))
        login_button.grid(column=0, row=4)
        self.toggle_premium_mode(username_label, password_label, password_entry, connect_var)
        connect_box.config(command=lambda: self.toggle_premium_mode(username_label, password_label, password_entry, connect_var))
        type_box.config(command=lambda: self.toggle_account_type(type_var))

    def update_profiles(self, name):
        """Updates special game arguments"""
        self.profname.set(self.accounts["profiles"][self.nametoprofile[name]]["name"])
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
        

    def login(self, win, username, password, error=True, premium=False):
        """True login process that requests an access token. (Unfinished)"""
        if not username == "":
            if premium:
                type_ = "Premium"
            else:
                type_ = "Non-Premium"
            self.accountbutton.config(text=f"{username} ({type_})")
        if username == "":
            messagebox.showinfo("Try again", "No login info was provided.")
            win.lift()
            return
        if not premium:
            self.accesstoken = ""
            self.username = username
            self.cache["username"] = username
            self.cache["premium"] = premium
            win.withdraw()
        else:
            messagebox.showinfo("Not yet implemented", "Currently, AP Launcher does not support premium accounts.")
            win.lift()
            return
            try:
                clienttoken = self.accounts["clientToken"]
            except:
                clienttoken = str(uuid.uuid4())
                self.accounts["clientToken"] = clienttoken
            win.withdraw()

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
        text=True,
        stdout=subprocess.PIPE
        )
        line = sb.stdout.readline().rstrip()
        while True:
            if sb.poll() is None:
                if line.startswith("\t"):
                    self.update_procscreen(line)
                else:
                    try:
                        title, text = line.split(": ", 1)
                        title = title.replace("[", "")
                        title = title.replace("]", "")
                        text = text.replace("ERROR : ", "")
                        time, rinfo = title.split(" ", 1)
                        name, info = rinfo.split("/")
                        self.update_procscreen(f"[{time}] {info} from {name}: {text}")
                    except ValueError:
                        if not line.startswith("ERROR : "):
                            self.update_procscreen(line)
                line = sb.stdout.readline().rstrip()
            else:
                break
        print("Process finished")
        self.playbutton.config(state="normal", text="\nPlay\n")
        self.playcontext.entryconfigure(0, state="disabled")

    def update_procscreen(self, text):
        """Updates the console screen"""
        self.processtext.config(state="normal")
        self.processtext.insert("end", text+"\n")
        self.processtext.config(state="disabled")
        
    def toggle_premium_mode(self, ul, pl, pe, cv):
        if cv.get() == 1:
            pl.grid(column=0, row=3)
            ul.config(text="Email:")
            pe.grid(column=1, row=3)
        elif cv.get() == 0:
            pl.grid_forget()
            ul.config(text="Username:")
            pe.grid_forget()
    
    def toggle_account_type(self, tv):
        if tv.get() == 1:
            self.accounttype = "mojang"
        elif tv.get() == 0:
            self.accounttype = "microsoft"
        
    def get_latest_version(self, type_):
        versions = [x[0] for x in os.walk(os.path.join(self.minecraftdir, "versions"))]
        if type_ == "release":
            filtered = [x.split("\\")[-1][:6] for x in versions if bool(re.match("1\.[1-9][1-9]\.[1-9]", x.split("\\")[-1]))]
            ranked = [int(x.replace(".", "")) for x in filtered]
            return filtered[ranked.index(max(ranked))] 
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

if __name__ == "__main__":
    main = App()
    main.win.mainloop()