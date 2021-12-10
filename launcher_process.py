import json
import os
import sys
import platform
from pathlib import Path
import subprocess
import threading
import uuid as uuidlib
from urllib.request import urlretrieve
from urllib.error import HTTPError
import shutil
import datetime
import logging
import socket
import requests
import traceback

# If anyone edits this file, you do NOT, under ANY circumstances, remove this code.
LOG4J_CONFIG = """<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Appenders>
        <Console name="SysOut" target="SYSTEM_OUT">
            <LegacyXMLLayout />
        </Console>
        <RollingRandomAccessFile name="File" fileName="logs/latest.log" filePattern="logs/%d{yyyy-MM-dd}-%i.log.gz">
            <PatternLayout pattern="[%d{HH:mm:ss}] [%t/%level]: %msg{nolookups}%n" />
            <Policies>
                <TimeBasedTriggeringPolicy />
                <OnStartupTriggeringPolicy />
            </Policies>
        </RollingRandomAccessFile>
    </Appenders>
    <Loggers>
        <Root level="info">
            <filters>
                <MarkerFilter marker="NETWORK_PACKETS" onMatch="DENY" onMismatch="NEUTRAL" />
            </filters>
            <AppenderRef ref="SysOut"/>
            <AppenderRef ref="File"/>
        </Root>
    </Loggers>
</Configuration>"""

# Base program derived from https://stackoverflow.com/questions/14531917/launch-minecraft-from-command-line-username-and-password-as-prefix

def debug(str):
    """Debug output"""
    if os.getenv('DEBUG') != None:
        sys.stdout.write(str)

def get_natives_string(lib):
    """[Gets the natives_string to prepend to the jar if it exists. If there is nothing native specific, returns and empty string]"""
    arch = ""
    if platform.architecture()[0] == "64bit":
        arch = "64"
    elif platform.architecture()[0] == "32bit":
        arch = "32"
    else:
        raise Exception("Architecture not supported; why are you even running it here?")

    nativesFile=""
    if not "natives" in lib:
        return nativesFile

    if "windows" in lib["natives"] and platform.system() == 'Windows':
        nativesFile = lib["natives"]["windows"].replace("${arch}", arch)
    elif "osx" in lib["natives"] and platform.system() == 'Darwin':
        nativesFile = lib["natives"]["osx"].replace("${arch}", arch)
    elif "linux" in lib["natives"] and platform.system() == "Linux":
        nativesFile = lib["natives"]["linux"].replace("${arch}", arch)
    else:
        raise Exception("Platform not supported")

    return nativesFile

def should_use_library(lib):
    """[Parses "rule" subpropery of library object, testing to see if should be included]"""
    def rule_says_yes(rule):
        useLib = None

        if rule["action"] == "allow":
            useLib = False
        elif rule["action"] == "disallow":
            useLib = True

        if "os" in rule:
            for key, value in rule["os"].items():
                os = platform.system()
                if key == "name":
                    if value == "windows" and os != 'Windows':
                        return useLib
                    elif value == "osx" and os != 'Darwin':
                        return useLib
                    elif value == "linux" and os != 'Linux':
                        return useLib
                elif key == "arch":
                    if value == "x86" and platform.architecture()[0] != "32bit":
                        return useLib

        return not useLib

    if not "rules" in lib:
        return True

    shouldUseLibrary = False
    for i in lib["rules"]:
        if rule_says_yes(i):
            return True

    return shouldUseLibrary

def get_classpath(lib, mcDir, inheritor):
    """[Get string of all libraries to add to java classpath]"""
    cp = []

    for i in lib["libraries"]:
        if not should_use_library(i):
            continue

        libDomain, libName, libVersion = i["name"].split(":")
        jarPath = os.path.join(mcDir, "libraries", *
                               libDomain.split('.'), libName, libVersion)

        native = get_natives_string(i)
        jarFile = libName + "-" + libVersion + ".jar"
        if native != "":
            jarFile = libName + "-" + libVersion + "-" + native + ".jar"

        cp.append(os.path.join(jarPath, jarFile))

    cp.append(os.path.join(mcDir, "versions", lib["id"], f'{lib["id"]}.jar'))
    if not inheritor is None:
        cp.append(os.path.join(mcDir, "versions", lib["inheritsFrom"], f'{lib["inheritsFrom"]}.jar'))

    return os.pathsep.join(cp)

def move_libraries(mcdir, dest, libjson, cp, version):
    """Moves libraries to natives path"""
    index = 0
    if not os.path.isdir(dest):
        os.mkdir(dest)
    shutil.copyfile(f"{mcDir}/versions/{version}/{version}.jar", os.path.join(dest, f"{version}.jar"))
    for c in cp.split(";"):
        name = c.split("\\")[-1]
        logger.info(f"Checking if {name} is cached...")
        if os.path.isfile(os.path.join(dest, name)):
            logger.info(f"{name} is already cached, no action needed.")
        elif not os.path.isfile(os.path.join(dest, name)) and os.path.isfile(c):
            logger.info(f"{name} is not cached, however it is in the library path.")
            shutil.copyfile(os.path.join(mcDir, "libraries", c.replace("\\", "/")), os.path.join(dest, name))
        elif not os.path.isfile(c) and not os.path.isfile(os.path.join(dest, name)):
            logger.info(f"{name} is not cached and is not in libraries folder, trying to download...")
            os.makedirs(os.path.join(mcDir, "libraries", *c.replace(f"{mcDir}\\libraries\\", "").split("\\")[:-1]), exist_ok=True)
            url = "https://libraries.minecraft.net/" + c.replace(f"{mcDir}\\libraries\\", "").replace("\\", "/")
            try:
                urlretrieve(url, os.path.join(mcDir, "libraries", c.replace("\\", "/")))
            except:
                logger.error(f"Unable to download {name}, this could break the game.")
            else:
                shutil.copyfile(os.path.join(mcDir, "libraries", c.replace("\\", "/")), os.path.join(dest, name))
        index += 1

def download_asset(hash_, failedlist):
    try:
        urlretrieve(url=f"https://resources.download.minecraft.net/{hash_[:2]}/{hash_}", filename=os.path.join(assetsDir, f"objects/{hash_[:2]}/{hash_}"))
        logger.info(f"Trying to download resource with hash {hash_}")
    except:
        logger.warning(f"Resource with hash {hash_} could not be downloaded, presumably due to rate limits.")
        failedlist.append(hash_)

def download_assets(assetsdir, assetindex):
    failedlist = []
    try:
        urlretrieve("https://resources.download.minecraft.net")
    except:
        logger.warning("Cannot contact assets server.")
        return
    for hash_ in [assetindex["objects"][asset]["hash"] for asset in list(assetindex["objects"].keys())]:
        if not os.path.isdir(os.path.join(assetsDir, f"objects/{hash_[:2]}")):
            os.mkdir(os.path.join(assetsDir, f"objects/{hash_[:2]}"))
        if not os.path.isfile(os.path.join(assetsDir, f"objects/{hash_[:2]}/{hash_}")):
            thread = threading.Thread(None, lambda: download_asset(hash_, failedlist))
            thread.start()
    for hash_ in failedlist:
        if not os.path.isdir(os.path.join(assetsDir, f"objects/{hash_[:2]}")):
            os.mkdir(os.path.join(assetsDir, f"objects/{hash_[:2]}"))
        if not os.path.isfile(os.path.join(assetsDir, f"objects/{hash_[:2]}/{hash_}")):
            thread = threading.Thread(None, lambda: download_asset(hash_, failedlist))
            thread.start()

def move_natives(mcdir, nativesdir):
    src = os.path.join(mcdir, "bin", "natives")
    if not os.path.isdir(src):
        os.makedirs(src, exist_ok=True)
    files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
    for file_ in files:
        if not os.path.isfile(os.path.join(nativesdir, file_)):
            shutil.copyfile(os.path.join(mcdir, "bin", "natives", file_), os.path.join(nativesdir, file_))

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
fmt = "[%(asctime)s] (Process %(processName)s thread %(threadName)s func %(funcName)s/%(levelname)s): %(message)s"
logging.basicConfig(filename="launcher_logs/process/latest.log", format=fmt, level=logging.INFO)
logger = logging.getLogger()

try:
    username = sys.argv[sys.argv.index("-username")+1]
    version = sys.argv[sys.argv.index("-version")+1]
    accessToken = sys.argv[sys.argv.index("-accessToken")+1]
    accountType = sys.argv[sys.argv.index("-accountType")+1]
    mcDir = sys.argv[sys.argv.index("-mcDir")+1]
    javaHome = sys.argv[sys.argv.index("-javaHome")+1]
    javaArgs = sys.argv[sys.argv.index("-javaArgs")+1]
    sock = int(sys.argv[sys.argv.index("-launcherServerSocket")+1])
except ValueError:
    sys.stdout.write("Invalid syntax.")
    sys.exit()

launcherClient = socket.socket()
launcherClient.connect(("localhost", sock))

try:
    accountJson = json.load(
        open(os.path.join(mcDir, "launcher_accounts.json"))
        )
    clientJson = json.load(
        open(os.path.join(mcDir, 'versions', version, f'{version}.json'))
        )
    gameArgs = []
    jvmArgs = []
    try:
        inheritor = clientJson["inheritsFrom"]
    except KeyError:
        inheritor = None
    else:
        logger.info(f"Version is modified, inheriting from {inheritor}.")
        clientJson2 = clientJson
        clientJson = json.load(
            open(os.path.join(mcDir, 'versions', inheritor, f'{inheritor}.json'))
            )
        clientJson["libraries"] = clientJson2["libraries"] + clientJson["libraries"]
        clientJson["id"] = clientJson2["id"]
        clientJson["inheritsFrom"] = clientJson2["inheritsFrom"]
    assetJson = json.load(
        open(os.path.join(mcDir, 'assets/indexes', f'{clientJson["assets"]}.json'))
        )
    assetsDir = os.path.join(mcDir, 'assets')
    logger.info("Downloading assets...")
    download_assets(assetsDir, assetJson)

    classPath = get_classpath(clientJson, mcDir, inheritor)

    try:
        nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
    except FileNotFoundError:
        os.mkdir(os.path.join(mcDir, 'versions', version, 'natives'))
        nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
    logger.info("Moving libraries to natives folder...")
    move_libraries(mcDir, nativesDir, clientJson["libraries"], classPath, version)
    logger.info("Moving DLLs to natives folder...")
    move_natives(mcDir, nativesDir)
    assetIndex = clientJson['assetIndex']['id']
    if inheritor is None:
        mainClass = clientJson['mainClass']
    else:
        mainClass = clientJson2['mainClass']
        try:
            clientJson["arguments"]["jvm"] = clientJson2["arguments"]["jvm"] + clientJson["arguments"]["jvm"]
        except:
            pass
        try:
            clientJson["arguments"]["game"].extend(clientJson2["arguments"]["game"])
        except:
            pass

    versionType = clientJson['type']
    authDatabase = accountJson["accounts"]
    logger.info("Checking for UUID...")
    uuid = None
    try:
        uuid = requests.get(f"https://mc-heads.net/minecraft/profile/{username}").json()["id"]
    except:
        for key in authDatabase:
            if authDatabase[key]["minecraftProfile"]["name"] == username:
                uuid = authDatabase[key]["minecraftProfile"]["id"]
                break
    if uuid is None:
        logger.error("Invalid and/or corrupt profile detected.")
        sys.exit()
    
    logger.info("Debugging...")
    debug(classPath)
    debug(mainClass)
    debug(versionType)
    debug(assetIndex)

    argFilePath = "C://Temp/classpath.txt"

    with open(argFilePath, "w") as f:
        f.write(classPath)
        f.close()
    
    logConfigPath = os.path.join(os.getcwd(), "temp", "client-1.12.xml")
    with open(logConfigPath, "w") as logConfig:
        logConfig.write(LOG4J_CONFIG)
        logConfig.close()

    clientJson["arguments"]["jvm"].insert(0, f'-Dlog4j.configurationFile="{logConfigPath}"')
    clientJson["arguments"]["jvm"].append(mainClass)
    preJvmArgs = []
    for index in range(len(clientJson["arguments"]["jvm"])):
        if isinstance(clientJson["arguments"]["jvm"][index], dict):
            should_use = should_use_library(clientJson["arguments"]["jvm"][index])
            if should_use:
                if isinstance(clientJson["arguments"]["jvm"][index]["value"], list):
                    preJvmArgs.extend(clientJson["arguments"]["jvm"][index]["value"])
                elif isinstance(clientJson["arguments"]["jvm"][index]["value"], str):
                    preJvmArgs.append(clientJson["arguments"]["jvm"][index]["value"])
        else:
            preJvmArgs.append(clientJson["arguments"]["jvm"][index])
    preGameArgs = []
    for index in range(len(clientJson["arguments"]["game"])):
        if isinstance(clientJson["arguments"]["game"][index], dict):
            pass
        else:
            preGameArgs.append(clientJson["arguments"]["game"][index])
            
    
    launchVars = {
        "auth_player_name": username,
        "version_name": version,
        "game_directory": mcDir,
        "assets_root": assetsDir,
        "assets_index_name": assetIndex,
        "auth_uuid": uuid,
        "auth_access_token": accessToken,
        "user_type": "mojang",
        "version_type": clientJson["type"],
        "natives_directory": nativesDir,
        "launcher_name": "AP-Launcher",
        "launcher_version": json.load(open("cache.json"))["launcherVersion"],
        "library_directory": os.path.join(mcDir, "libraries"),
        "classpath_separator": os.pathsep,
        "classpath": f'@{argFilePath}'
    }

    argList = javaArgs.split() + preJvmArgs + preGameArgs
    argList.insert(0, javaHome)
    finalArgs = [arg.replace("$", "").format(**launchVars) for arg in argList]

    logger.info("Running the game...")
    sb = subprocess.Popen(finalArgs, 
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL
    )
    isfirstpass = True
    while sb.poll() is None:
        line = sb.stdout.readline().decode("ISO-8859-1")
        if not line == "":
            sys.stdout.write(str(line))
        launcherClient.send(b"\x00")
except BaseException as e:
    if not type(e).__name__ == "SystemExit":
        logger.error(e, exc_info=True)
        traceback.print_exc(file=open("launcher_logs/error.log", "w"))
        launcherClient.send(b"\xff")
    else:
        launcherClient.send(b"\x00")
    sys.exit()
