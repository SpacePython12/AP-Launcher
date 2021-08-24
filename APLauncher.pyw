from tkinter import *
from tkinter.ttk import *
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
from PIL import ImageTk, Image
import os
import json
import uuid
import requests
import subprocess
import threading

class LabeledEntry(Frame):

    def __init__(self, parent, label: str, defaultval: str, elength=20):
        super().__init__(parent)
        self.label = Label(self, text=label)
        self.entryvar = StringVar(self)
        self.entryvar.set(defaultval)
        self.entry = Entry(self, textvariable=self.entryvar, width=elength)

    def grid(self, column, row, sticky=""):
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
        self.accounts = self.get_accounts()
        self.mainframe = Frame(self.win)
        self.tabs.add(self.mainframe, text="Versions", sticky="nsew")
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
        self.versionvar.set(self.versions[0])
        self.versionlabel = Label(self.buttonframe, text="Version: ")
        self.versionlabel.grid(column=3, row=0)
        self.versionlist = Combobox(self.buttonframe, textvariable=self.versionvar)
        self.versionlist.grid(column=4, row=0)
        self.versionlist["values"] = self.versions
        self.playbutton = Button(self.win, text="\nPlay\n", command=lambda: self.start_game())
        self.playbutton.grid(column=0, row=2, sticky="nsew")
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
        self.profjavadir = LabeledEntry(self.profileframe, "Java Directory: ", f'{os.getenv("JAVA_HOME")}\\bin\\javaw.exe', elength=30)
        self.profjavadir.grid(column=0, row=3, sticky="nsew")
        self.profjavargs = LabeledEntry(self.profileframe, "JVM Arguments: ", "-Xmx2G -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:G1NewSizePercent=20 -XX:G1ReservePercent=20 -XX:MaxGCPauseMillis=50 -XX:G1HeapRegionSize=32M", elength=50)
        self.profjavargs.grid(column=0, row=4, sticky="nsew")
        self.profsave = Button(self.profileframe, text="Save")
        self.profsave.grid(column=0, row=5, sticky="nsew")
        self.update_profiles(self.versionvar.get())
        self.profilelist.bind("<<ComboboxSelected>>", lambda x: self.update_profiles(self.versionvar.get()))
        self.accesstoken = None
        self.username = None
        self.accounttype = "microsoft"

    def get_versions(self):
        profiles = list(self.accounts["profiles"].keys())
        versions = []
        occurences = {}
        for profile in profiles:
            name = self.accounts["profiles"][profile]["name"]
            if name == "":
                name = "<unnamed installation>"
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
        out = {}
        for version in self.versions:
            for profile in self.profiles:
                if version == f'{self.accounts["profiles"][profile]["name"]} ({self.accounts["profiles"][profile]["lastVersionId"]})':
                    out[version] = profile
        return out

    def get_accounts(self):
        return json.load(open(os.path.join(self.minecraftdir, "launcher_profiles.json")))

    def accountdialog(self):
        dwin = Toplevel(self.win)
        dwin.title("Accounts")
        login_frame = Frame(dwin)
        login_frame.pack(side="left")
        connect_label = Label(login_frame, text="Premium mode:")
        connect_label.grid(column=0, row=0)
        connect_var = IntVar(login_frame)
        connect_var.set(1)
        connect_box = Checkbutton(login_frame, variable=connect_var)
        connect_box.grid(column=1, row=0)
        type_label = Label(login_frame, text="Legacy (Mojang) account:")
        type_label.grid(column=0, row=1)
        type_var = IntVar(login_frame)
        type_var.set(0)
        type_box = Checkbutton(login_frame, variable=type_var)
        type_box.grid(column=1, row=1)
        username_var = StringVar(login_frame)
        username_label = Label(login_frame, text="Email:")
        username_label.grid(column=0, row=2)
        username_entry = Entry(login_frame, textvariable=username_var)
        username_entry.grid(column=1, row=2)
        password_var = StringVar(login_frame)
        password_label = Label(login_frame, text="Password:")
        password_label.grid(column=0, row=3)
        password_entry = Entry(login_frame, textvariable=password_var, show="•")
        password_entry.grid(column=1, row=3)
        login_button = Button(login_frame, text="Login", command=lambda: self.login(dwin, username_var.get(), password_var.get(), offline=bool(connect_var.get())))
        login_button.grid(column=0, row=4)
        connect_box.config(command=lambda: self.toggle_premium_mode(username_label, password_label, password_entry, connect_var))
        type_box.config(command=lambda: self.toggle_account_type(type_var))

    def update_profiles(self, name):
        self.profname.set(self.accounts["profiles"][self.nametoprofile[name]]["name"])
        self.profgamedir.set(self.accounts["profiles"][self.nametoprofile[name]]["gameDir"])
        self.profjavadir.set(self.accounts["profiles"][self.nametoprofile[name]]["javaDir"])
        self.profjavargs.set(self.accounts["profiles"][self.nametoprofile[name]]["javaArgs"])

    def save_profile(self, name):
        self.accounts["profiles"][self.nametoprofile[name]] = {"name": self.profname.get(), "type": "custom", "lastVersionId": self.accounts["profiles"][self.nametoprofile[name]]["lastVersionId"], "gameDir": self.profgamedir.get(), "javaDir": self.profjavadir.get(), "javaArgs": self.profjavargs.get()}
        self.get_versions()
        self.versionlist["values"] = self.versions
        self.profilelist["values"] = self.versions
        

    def login(self, win, username, password, error=True, offline=False):
        if username == "":
            messagebox.showinfo("Try again", "No login info was provided.")
            win.lift()
            return
        if not offline:
            self.accesstoken = str(uuid.uuid4())
            self.username = username
            win.withdraw()
        else:
            try:
                clienttoken = self.accounts["clientToken"]
            except:
                clienttoken = str(uuid.uuid4())
                self.accounts["clientToken"] = clienttoken
            payload = {
                "agent": {
                    "name": "Minecraft",
                    "version": 1
                },
                "username": username,
                "password": password,
                "clientToken": clienttoken
            }
            try:
                response = requests.post("https://authserver.mojang.com/authenticate", data=payload, allow_redirects=False, timeout=0.1)
            except:
                if error:
                    messagebox.showerror("Login Failed", "AP Launcher was unable to access the Minecraft login servers. Minecraft may be blocked.")
                self.accesstoken = str(uuid.uuid4())
                if "@" in username:
                    selecteduser = self.accounts["selectedUser"]
                    self.username = self.accounts["authenticationDatabase"][selecteduser]["username"]
                else:
                    self.username = username
                win.withdraw()
                return
            self.accesstoken = response["accessToken"]
            self.username = response["selectedProfile"]["name"]
            win.withdraw()

    def start_game(self):
        if self.accesstoken is None and self.username is None:
            messagebox.showinfo("Please Login", "You must login to play Minecraft.")
            return
        thread = threading.Thread(None, lambda: self.sbloop())
        thread.start()

    def sbloop(self):
        self.playbutton.config(state="disabled", text="\nRunning...\n")
        sb = subprocess.Popen([
        "launcher_process",
        "-username",
        self.username,
        "-version",
        self.accounts["profiles"][self.nametoprofile[self.versionvar.get()]]["lastVersionId"],
        "-accessToken",
        self.accesstoken,
        "-accountType",
        self.accounttype,
        "-mcDir",
        self.profgamedir.get(),
        "-javaHome",
        self.profjavadir.get(),
        "-javaArgs",
        self.profjavargs.get()
        ], 
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
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

    def update_procscreen(self, text):
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

if __name__ == "__main__":
    main = App()
    main.win.mainloop()