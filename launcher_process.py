import json
import os
import sys
import platform
from pathlib import Path
import subprocess
import threading
import uuid as uuidlib
from urllib.request import urlretrieve
import shutil
import logging
import datetime

# Base program derived from https://stackoverflow.com/questions/14531917/launch-minecraft-from-command-line-username-and-password-as-prefix

"""
Debug output
"""
def debug(str):
    if os.getenv('DEBUG') != None:
        print(str)

"""
[Gets the natives_string toprepend to the jar if it exists. If there is nothing native specific, returns and empty string]
"""
def get_natives_string(lib):
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


"""
[Parses "rule" subpropery of library object, testing to see if should be included]
"""
def should_use_library(lib):
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

"""
[Get string of all libraries to add to java classpath]
"""
def get_classpath(lib, mcDir):
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

def move_libraries(cp, dest, libjson):
    """Moves libraries to natives path"""
    index = 0
    for p in cp.split(";"):
        name = p.split("\\")[-1]
        try:
            shutil.copyfile(p, os.path.join(dest, name))
        except FileNotFoundError:
            name2 = libjson[index]["name"].replace(":", "/").split("/")
            urlretrieve(f"https://libraries.minecraft.net/{name2[0].replace('.', '/')}/{name2[1]}/{name2[2]}/{name2[1]}-{name2[2]}.jar", p)
            shutil.copyfile(p, os.path.join(dest, name))
        except FileExistsError:
            os.remove(os.path.join(dest, name))
            shutil.copyfile(p, os.path.join(dest, name))
        index += 1

if not os.path.isdir("launcher_logs"):
    os.mkdir("launcher_logs")

num = 1
date = datetime.datetime.today().strftime("%Y-%m-%d")
while os.path.isfile(os.path.join("launcher_logs", f"{date}-{num}.log")):
    num += 1
fp = os.path.join("launcher_logs", f"{date}-{num}")

logging.basicConfig(format="[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s", level=logging.INFO)
handler = logging.FileHandler(fp, "a")
logging.getLogger('').addHandler(handler)
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
    quit()

accountJson = json.load(
    open(os.path.join(mcDir, "launcher_accounts.json"))
    )
clientJson = json.load(
    open(os.path.join(mcDir, 'versions', version, f'{version}.json'))
    )

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
    move_libraries(classPath, nativesDir, clientJson["libraries"])
except FileNotFoundError:
    os.mkdir(os.path.join(mcDir, 'versions', version, 'natives'))
    nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
    move_libraries(classPath, nativesDir, clientJson["libraries"])
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
    os.path.join(mcDir, 'assets'),
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
text=True,
stdout=subprocess.PIPE,
stderr=subprocess.STDOUT,
stdin=subprocess.DEVNULL
)
line = sb.stdout.readline().rstrip()
isfirstpass = True
while True:
    if sb.poll() is None and line != "":
        print(line)
        line = sb.stdout.readline().rstrip()
    else:
        break