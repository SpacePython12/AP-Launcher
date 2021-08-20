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

class App:

    def __init__(self):
        self.win = Tk()
        self.win.title("AP Launcher")
        self.tabs = Notebook(self.win)
        self.tabs.pack()
        self.minecraftdir = os.path.join(os.getenv('APPDATA'), '.minecraft')
        self.accounts = self.get_accounts()
        self.mainframe = Frame(self.win)
        self.tabs.add(self.mainframe, text="Versions")
        self.background = ImageTk.PhotoImage(Image.open("assets/background.png"))
        self.background2 = Label(self.mainframe, image=self.background)
        self.background2.pack()
        self.buttonframe = Frame(self.mainframe)
        self.buttonframe.pack(side="left")
        self.accountlabel = Label(self.buttonframe, text="Account: ")
        self.accountlabel.pack(side="left")
        self.accountbutton = Button(self.buttonframe, text="Choose...", command=lambda: self.accountdialog())
        self.accountbutton.pack(side="left")
        self.versionvar = StringVar()
        selectedprofile = self.accounts["selectedProfile"]
        self.versionvar.set(self.accounts["profiles"][selectedprofile]["lastVersionId"])
        self.versions = self.get_versions()
        self.versionlabel = Label(self.buttonframe, text="Version: ")
        self.versionlabel.pack(side="left")
        self.versionlist = Combobox(self.buttonframe, textvariable=self.versionvar)
        self.versionlist.pack(side="left")
        self.versionlist["values"] = self.versions
        self.playbutton = Button(self.win, text="\nPlay\n", command=lambda: self.start_game())
        self.playbutton.pack(expand=True, fill="x")
        self.processframe = Frame(self.win)
        self.tabs.add(self.processframe, text="Game Output")
        self.processtext = ScrolledText(self.processframe, state="disabled")
        self.processtext.pack()
        self.accesstoken = None
        self.username = None
        self.accounttype = "microsoft"

    def get_versions(self):
        vdir = os.path.join(self.minecraftdir, 'versions')
        for root, folders, files in os.walk(vdir):
            versions = folders
            break
        return versions

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
        username_label = Label(login_frame, text="Username or email:")
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
        connect_box.config(command=lambda: self.toggle_premium_mode(password_label, password_entry, connect_var))
        type_box.config(command=lambda: self.toggle_account_type(type_var))

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
        self.versionvar.get(),
        "-accessToken",
        self.accesstoken,
        "-accountType",
        self.accounttype
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
        
    def toggle_premium_mode(self, pl, pe, cv):
        if cv.get() == 1:
            pl.grid(column=0, row=3)
            pe.grid(column=1, row=3)
        elif cv.get() == 0:
            pl.grid_forget()
            pe.grid_forget()
    
    def toggle_account_type(self, tv):
        if tv.get() == 1:
            self.accounttype = "mojang"
        elif tv.get() == 0:
            self.accounttype = "microsoft"



if __name__ == "__main__":
    main = App()
    main.win.mainloop()