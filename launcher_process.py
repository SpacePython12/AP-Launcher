import json
import os
import sys
import platform
from pathlib import Path
import subprocess
import threading
import uuid as uuidlib


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

try:
    username = sys.argv[sys.argv.index("-username")+1]
    version = sys.argv[sys.argv.index("-version")+1]
    accessToken = sys.argv[sys.argv.index("-accessToken")+1]
    accountType = sys.argv[sys.argv.index("-accountType")+1]
except ValueError:
    print("Invalid syntax.")
    quit()

try:
    mcDir = os.path.join(os.getenv('APPDATA'), '.minecraft')
except FileNotFoundError:
    print("Did not find a .minecraft folder.")
    quit()

try:
    nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
except FileNotFoundError:
    os.mkdir(os.path.join(mcDir, 'versions', version, 'natives'))
    nativesDir = os.path.join(mcDir, 'versions', version, 'natives')
try:
    accountJson = json.load(
        open(os.path.join(mcDir, "launcher_profiles.json"))
        )
except FileNotFoundError:
    print(f"Account not found.")
    quit()
try:
    clientJson = json.load(
        open(os.path.join(mcDir, 'versions', version, f'{version}.json'))
        )
except FileNotFoundError:
    print(f"{version}.json does not exist.")
    quit()
try:
    classPath = get_classpath(clientJson, mcDir)
except Exception as e:
    print(e)
    quit()
try:
    mainClass = clientJson['mainClass']
    versionType = clientJson['type']
    assetIndex = clientJson['assetIndex']['id']
except:
    print("Invalid JSON asset index file.")
    quit()
try:
    authDatabase = accountJson["authenticationDatabase"]
    for key in authDatabase:
        if authDatabase[key]["username"] == username:
            uuid = authDatabase[key]["uuid"]
            break
except:
    print("Invalid account.")
    quit()

debug(classPath)
debug(mainClass)
debug(versionType)
debug(assetIndex)

sb = subprocess.Popen([
    f'{os.getenv("JAVA_HOME")}/bin/javaw.exe',
    f'-Djava.library.path={nativesDir}',
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
], 
shell=True,
text=True,
stdout=subprocess.PIPE,
stderr=subprocess.STDOUT
)
line = sb.stdout.readline().rstrip()
while True:
    if sb.poll() is None and line != "":
        if line[0].startswith("\t"):
            print(line)
        else:
            try:
                title, text = line.split(": ", 1)
                title = title.replace("[", "")
                title = title.replace("]", "")
                text = text.replace("ERROR : ", "")
                time, rinfo = title.split(" ", 1)
                name, info = rinfo.split("/")
                print(f"[{time}] {info} from {name}: {text}")
            except ValueError:
                if not line.startswith("ERROR : "):
                    print(line)
        line = sb.stdout.readline().rstrip()
    else:
        break