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

# Base program derived from https://stackoverflow.com/questions/14531917/launch-minecraft-from-command-line-username-and-password-as-prefix


def debug(str):
    """Debug output"""
    if os.getenv('DEBUG') != None:
        print(str)

def get_natives_string(lib):
    """[Gets the natives_string to prepend to the jar if it exists. If there is nothing native specific, returns and empty string]"""
    arch = ""
    if platform.architecture()[0] == "64bit":
        arch = "64"
    elif platform.architecture()[0] == "32bit":
        arch = "32"
    else:
        raise Exception("Architecture not supported")

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

def get_classpath(lib, mcDir):
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

    return os.pathsep.join(cp)

def move_libraries(mcdir, dest, libjson, cp, version):
    """Moves libraries to natives path"""
    index = 0
    shutil.copyfile(f"{mcDir}/versions/{version}/{version}.jar", os.path.join(dest, f"{version}.jar"))
    for c in cp.split(";"):
        name = c.split("\\")[-1]
        print(f"Looking for {name}...")
        if not os.path.isfile(os.path.join(dest, name)) and os.path.isfile(c):
            print(f"{name} is already cached, moving to natives folder")
            shutil.copyfile(os.path.join(mcDir, "libraries", c.replace("\\", "/")), os.path.join(dest, name))
        elif not os.path.isfile(c):
            print(f"{name} is not cached, trying to download")
            os.makedirs(os.path.join(mcDir, "libraries", *c.replace(f"{mcDir}\\libraries\\", "").split("\\")[:-1]), exist_ok=True)
            url = "https://libraries.minecraft.net/" + c.replace(f"{mcDir}\\libraries\\", "").replace("\\", "/")
            urlretrieve(url, os.path.join(mcDir, "libraries", c.replace("\\", "/")))
            shutil.copyfile(os.path.join(mcDir, "libraries", c.replace("\\", "/")), os.path.join(dest, name))
        print(f"{name} successfully moved to natives folder.")
        index += 1

def download_asset(hash_, failedlist):
    try:
        urlretrieve(url=f"https://resources.download.minecraft.net/{hash_[:2]}/{hash_}", filename=os.path.join(assetsDir, f"objects/{hash_[:2]}/{hash_}"))
    except HTTPError:
        failedlist.append(hash_)

def download_assets(assetsdir, assetindex):
    failedlist = []
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

try:
    username = sys.argv[sys.argv.index("-username")+1]
    version = sys.argv[sys.argv.index("-version")+1]
    accessToken = sys.argv[sys.argv.index("-accessToken")+1]
    accountType = sys.argv[sys.argv.index("-accountType")+1]
    mcDir = sys.argv[sys.argv.index("-mcDir")+1]
    javaHome = sys.argv[sys.argv.index("-javaHome")+1]
    javaArgs = sys.argv[sys.argv.index("-javaArgs")+1]
except ValueError:
    print("Invalid syntax.")
    sys.exit()

accountJson = json.load(
    open(os.path.join(mcDir, "launcher_accounts.json"))
    )
clientJson = json.load(
    open(os.path.join(mcDir, 'versions', version, f'{version}.json'))
    )
assetJson = json.load(
    open(os.path.join(mcDir, 'assets/indexes', f'{clientJson["assets"]}.json'))
    )
assetsDir = os.path.join(mcDir, 'assets')
download_assets(assetsDir, assetJson)

additionalArgs = []

try:
    inheritor = clientJson["inheritsFrom"]
except KeyError:
    inheritor = None
else:
    clientJson2 = json.load(
        open(os.path.join(mcDir, 'versions', inheritor, f'{inheritor}.json'))
        )
    additionalArgs.extend(clientJson2["arguments"]["game"])
    clientJson["libraries"] = clientJson2["libraries"] + clientJson["libraries"]

classPath = get_classpath(clientJson, mcDir)

try:
    nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
except FileNotFoundError:
    os.mkdir(os.path.join(mcDir, 'versions', version, 'natives'))
    nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
move_libraries(classPath, nativesDir, clientJson["libraries"], classPath, version)
if inheritor is None:
    mainClass = clientJson['mainClass']
    assetIndex = clientJson['assetIndex']['id']
else:
    mainClass = clientJson2['mainClass']
    assetIndex = clientJson2['assetIndex']['id']
versionType = clientJson['type']
authDatabase = accountJson["accounts"]
for key in authDatabase:
    if authDatabase[key]["minecraftProfile"]["name"] == username:
        uuid = authDatabase[key]["minecraftProfile"]["id"]
        break

debug(classPath)
debug(mainClass)
debug(versionType)
debug(assetIndex)

finalArgs = [
    javaHome,
    f'-Djava.library.path={nativesDir}',
    f'-Djava-args={javaArgs}',
    '-Dminecraft.launcher.brand=custom-launcher',
    '-Dminecraft.launcher.version=2.1',
    '-Dorg.lwjgl.util.DebugLoader=true',
    '-cp',
    classPath,
    'net.minecraft.client.main.Main',
    '--username',
    username,
    '--version',
    version,
    '--gameDir',
    mcDir,
    '--assetsDir',
    assetsDir,
    '--assetIndex',
    assetIndex,
    '--uuid',
    uuid,
    '--accessToken',
    accessToken,
    '--userType',
    accountType,
    '--versionType',
    'release'
]
finalArgs.extend(additionalArgs)

sb = subprocess.Popen(finalArgs, 
shell=True,
stdout=subprocess.PIPE,
stderr=subprocess.STDOUT,
stdin=subprocess.DEVNULL
)
isfirstpass = True
while sb.poll() is None:
    line = sb.stdout.readline().decode("unicode-escape").rstrip()
    if not line == "":
        print(line)