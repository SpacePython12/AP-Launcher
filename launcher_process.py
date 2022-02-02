import os
import subprocess
import sys
import datetime
import logging
import platform
import requests
import time
import re
import json
import argparse
import shutil
import ruamel.std.zipfile as zipfile
import hashlib

if __name__ == "__main__":
    if not os.path.isdir("launcher_logs/process"):
        os.mkdir("launcher_logs/process")
    if os.path.isfile("launcher_logs/process/latest.log"):
        time = datetime.datetime.fromtimestamp(os.path.getctime("launcher_logs/process/latest.log")).strftime("%Y-%m-%d")
        num = 1
        while os.path.isfile(f"launcher_logs/process/{time}-{num}.log"):
            num += 1
        try:
            os.rename("launcher_logs/process/latest.log", f"launcher_logs/process/{time}-{num}.log")
        except:
            sys.exit()
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(logging.Formatter("[%(asctime)s] [Launcher Interface/%(levelname)s]: %(message)s"))
    logging.basicConfig(format="[%(asctime)s] (Process %(processName)s thread %(threadName)s func %(funcName)s/%(levelname)s): %(message)s", handlers=[logging.FileHandler("launcher_logs/process/latest.log"), stream], level=logging.INFO)
    logger = logging.getLogger()

def download(url, path):
    with requests.get(url, allow_redirects=False, stream=True) as res:
        with open(path, "wb") as resfile:
            for chunk in res.iter_content(8192):
                resfile.write(bytes(chunk))
            resfile.close()

def should_use_library(lib, features={}):
    def rule_says_yes(rule, features={}):
        uselib = None

        if rule["action"] == "allow":
            uselib = False
        elif rule["action"] == "disallow":
            uselib = True

        if "os" in rule.keys():
            for key, value in rule["os"].items():
                os = platform.system()
                if key == "name":
                    if value == "windows" and os != 'Windows':
                        return uselib
                    elif value == "osx" and os != 'Darwin':
                        return uselib
                    elif value == "linux" and os != 'Linux':
                        return uselib
                elif key == "arch":
                    if value == "x86" and platform.architecture()[0] != "32bit":
                        return uselib
        elif "features" in rule.keys():
            return False

        return not uselib

    if not "rules" in lib.keys():
        return True

    shoulduselibrary = False
    for i in lib["rules"]:
        if rule_says_yes(i):
            return True

    return shoulduselibrary

def get_classpath(version, mc_dir):
    cp = []
    #os = {"Windows": "windows", "Darwin": "osx", "Linux": "linux"}[platform.system()]
    os_verbose = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}[platform.system()]
    arch = {"32bit": "32", "64bit": "64"}[platform.architecture()[0]]
    logger.info("Managing libraries...")
    for lib in version["libraries"]:
        if "rules" in lib.keys():
            if not should_use_library(lib):
                continue
        lib_domain, lib_name, lib_version = lib["name"].split(":")
        jar_file = lib_name + "-" + lib_version + ".jar"
        base_url = "https://libraries.minecraft.net/"
        if "url" in lib.keys():
            base_url = lib["url"]
        if "natives" in lib.keys():
            if os_verbose in lib["natives"].keys():
                blob = lib["downloads"]["classifiers"][lib["natives"][os_verbose].replace("${arch}", arch)]
            else:
                blob = lib["downloads"]["artifact"]
        elif "downloads" in lib.keys():
            blob = lib["downloads"]["artifact"]
        else:
            path = f"/{lib_domain.replace('.', '/')}/{lib_name}/{lib_version}/{jar_file}"
            blob = {
                "path": path,
                "url": f"{base_url}{path.lstrip('/')}"
            }
        if not os.path.exists(os.path.join(mc_dir, "versions", version["id"], "natives")):
            os.mkdir(os.path.join(mc_dir, "versions", version["id"], "natives"))
        if not os.path.exists(os.path.join(mc_dir, "libraries", *blob["path"].split("/"))):
            os.makedirs(os.path.join(mc_dir, "libraries", *blob["path"].split("/")[:-1]), exist_ok=True)
        try:   
            if not os.path.exists(os.path.join(mc_dir, "libraries", *blob["path"].split("/"))):
                download(blob["url"], os.path.join(mc_dir, "libraries", *blob["path"].split("/")))
        except:
            logger.error(f"FAILURE downloading {jar_file}. The game may not function properly.")
        if lib_name == "log4j-core":
            try:
                zipfile.delete_from_zip_file(os.path.join(mc_dir, "libraries", *blob["path"].split("/")), file_names="JndiLookup.class")
            except:
                pass
        cp.append(os.path.join(mc_dir, "libraries", *blob["path"].split("/")))
        shutil.copyfile(os.path.join(mc_dir, "libraries", *blob["path"].split("/")), os.path.join(mc_dir, "versions", version["id"], "natives", jar_file))
    cp.append(os.path.join(mc_dir, "versions", version["id"], f'{version["id"]}.jar'))
    shutil.copyfile(os.path.join(mc_dir, "versions", version["id"], f'{version["id"]}.jar'), os.path.join(mc_dir, "versions", version["id"], "natives", f'{version["id"]}.jar'))
    return os.pathsep.join(cp)

def download_assets(assets, assets_dir):
    index = 1
    total = len([assets["objects"][asset]["hash"] for asset in list(assets["objects"].keys())])
    for hash in [assets["objects"][asset]["hash"] for asset in list(assets["objects"].keys())]:
        if not os.path.exists(os.path.join(assets_dir, "objects", hash[:2])):
            os.mkdir(os.path.join(assets_dir, "objects", hash[:2]))
        if not os.path.exists(os.path.join(assets_dir, "objects", hash[:2], hash)):
            download(f"https://resources.download.minecraft.net/{hash[:2]}/{hash}", os.path.join(assets_dir, "objects", hash[:2], hash))
            time.sleep(0.1)
        index += 1

def update_files(version, mc_dir, assets):
    try:
        if hashlib.sha1(open(os.path.join(mc_dir, "assets", "indexes", f'{version["assets"]}.json')).read()).hexdigest() != version["assetIndex"]["client"]["sha1"]:
            logger.info("Downloading asset index...")
            download(version["assetIndex"]["url"], os.path.join(mc_dir, "assets", "indexes", f'{version["assets"]}.json'))
    except:
        logger.warning("Unable to download asset index.")
    logger.info("Updating assets...")
    download_assets(assets, os.path.join(argv["mcDir"], "assets"))
    try:
        if hashlib.sha1(open(os.path.join(mc_dir, "versions", version["id"], f'{version["id"]}.jar'), "rb").read()).hexdigest() != version["downloads"]["client"]["sha1"]:
            logger.info("Updating main jar...")
            download(version["downloads"]["client"]["url"], os.path.join(mc_dir, "versions", version["id"], f'{version["id"]}.jar'))
    except:
        if os.path.exists(os.path.join(mc_dir, "versions", version["id"], f'{version["id"]}.jar')):
            logger.warning("Unable to update main jar. However, it already exists, hope it's good.")
        else:
            logger.error("Unable to download main jar. The game cannot run.")
            sys.exit()

def get_info_files(argv):
    accounts = json.load(open(os.path.join(argv["mcDir"], "launcher_accounts.json")))
    logger.info("\tRead launcher_accounts.json.")
    version = json.load(open(os.path.join(argv["mcDir"], "versions", argv["version"], f'{argv["version"]}.json')))
    if "inheritsFrom" in version.keys():
        parentversion = json.load(open(os.path.join(argv["mcDir"], "versions", version["inheritsFrom"], f'{version["inheritsFrom"]}.json')))
        version["assets"] = parentversion["assets"]
        version["libraries"] = version["libraries"] + parentversion["libraries"]
        if "arguments" in version.keys():
            if "game" in version["arguments"].keys():
                version["arguments"]["game"] = parentversion["arguments"]["game"] + version["arguments"]["game"]
            if "jvm" in version["arguments"].keys():
                version["arguments"]["jvm"] = version["arguments"]["jvm"] + parentversion["arguments"]["jvm"]
        elif "minecraftArguments" in version.keys():
            version["minecraftArguments"] = parentversion["minecraftArguments"] + " " + version["minecraftArguments"]
        if "arguments" in parentversion.keys():
            version["arguments"] = {}
            if "game" in parentversion["arguments"].keys():
                version["arguments"]["game"] = parentversion["arguments"]["game"]
            if "jvm" in parentversion["arguments"].keys():
                version["arguments"]["jvm"] = parentversion["arguments"]["jvm"]
        elif "minecraftArguments" in parentversion.keys():
            version["minecraftArguments"] = parentversion["minecraftArguments"]
    logger.info("\tRead " + f'{argv["version"]}.json' + ".")
    assets = json.load(open(os.path.join(argv["mcDir"], "assets", "indexes", f'{version["assets"]}.json')))
    logger.info("\tRead " + f'{version["assets"]}.json' + ".")
    account = [accounts["accounts"][localid] for localid in accounts["accounts"].keys() if accounts["accounts"][localid]["minecraftProfile"]["name"] == argv["username"]][0]
    return version, account, assets

def get_args(version, argv, account, cp):
    args = [argv["javaHome"]]
    args.extend(argv["javaArgs"])
    if "arguments" in version.keys():
        if "jvm" in version["arguments"].keys():
            for jvmarg in version["arguments"]["jvm"]:
                if isinstance(jvmarg, str):
                    args.append(jvmarg)
                elif isinstance(jvmarg, dict):
                    if should_use_library(jvmarg):
                        if isinstance(jvmarg["value"], list):
                            args.extend(jvmarg["value"])
                        elif isinstance(jvmarg["value"], str):
                            args.append(jvmarg["value"])
            args.append(version["mainClass"])
        else:
            args.extend(["-Djava.library.path=${natives_directory}", "-Dminecraft.launcher.brand=${launcher_name}", "-Dminecraft.launcher.version=${launcher_version}", "-cp", "${classpath}", version["mainClass"]])
        if "game" in version["arguments"].keys():
            for gamearg in version["arguments"]["game"]:
                if isinstance(gamearg, str):
                    args.append(gamearg)
                elif isinstance(gamearg, dict):
                    if should_use_library(gamearg):
                        if isinstance(gamearg["value"], list):
                            args.extend(gamearg["value"])
                        elif isinstance(gamearg["value"], str):
                            args.append(gamearg["value"])
        elif "minecraftArguments" in version.keys():
            args.extend(version["minecraftArguments"].split(" "))
    elif "minecraftArguments" in version.keys():
        args.extend(["-Djava.library.path=${natives_directory}", "-Dminecraft.launcher.brand=${launcher_name}", "-Dminecraft.launcher.version=${launcher_version}", "-cp", "${classpath}", version["mainClass"]])
        args.extend(version["minecraftArguments"].split(" "))
    argfile_path = os.path.realpath(os.path.join(os.getenv("temp"), "classpath.txt"))
    with open(argfile_path, "w") as cpf:
        cpf.write(cp)
    blacklisted_launchvars = [
        "--clientId",
        "${clientid}",
        "--xuid",
        "${auth_xuid}",
        "--userProperties",
        "${user_properties}"
    ]
    launchvars = {
        "auth_player_name": argv["username"],
        "version_name": argv["version"],
        "game_directory": argv["mcDir"],
        "assets_root": os.path.join(argv["mcDir"], "assets"),
        "assets_index_name": version["assets"],
        "auth_uuid": account["minecraftProfile"]["id"],
        "auth_access_token": argv["accessToken"],
        "user_type": argv["accountType"],
        "version_type": version["type"],
        "natives_directory": os.path.join(argv["mcDir"], "versions", argv["version"], "natives"),
        "launcher_name": "AP-Launcher",
        "launcher_version": json.load(open("cache.json"))["launcherVersion"],
        "library_directory": os.path.join(argv["mcDir"], "libraries"),
        "classpath_separator": os.pathsep,
        "classpath": f"@{argfile_path}"
    }
    args = [arg.replace("$", "").format(**launchvars) for arg in args if arg not in blacklisted_launchvars]
    return args

def run_game(args):
    with open("output.txt", "w") as f:
        f.write(" ".join(args))
    with subprocess.Popen(
        args,
        shell=True,
        stdout=sys.stdout,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    ) as sb:
        sb.wait()
        sys.exit(sb.returncode)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--username", action="store")
    argparser.add_argument("--version", action="store")
    argparser.add_argument("--accessToken", action="store")
    argparser.add_argument("--accountType", action="store")
    argparser.add_argument("--mcDir", action="store")
    argparser.add_argument("--javaHome", action="store")
    argparser.add_argument("--javaArgs", action="store", nargs="*")
    argv = vars(argparser.parse_args())
    argv["javaArgs"] = [arg.replace("+", "-") for arg in argv["javaArgs"]]
    try:
        logger.info("Reading base files...")
        version, account, assets = get_info_files(argv)
        logger.info("Downloading files...")
        update_files(version, argv["mcDir"], assets)
        cp = get_classpath(version, argv["mcDir"])
        launchargs = get_args(version, argv, account, cp)
        logger.info("Running the game...")
        run_game(launchargs)
    except Exception as e:
        logger.error(e, exc_info=True)
        sys.exit()
