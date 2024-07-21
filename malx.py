#!/usr/bin/python3

from xdrlib import ConversionError
from colorama import init, Fore, Back, Style
from git import Repo
from zipfile import ZipFile
import sys
import shutil
import psutil # pip install -r requirements.txt
import time
import subprocess
import os
import traceback
import threading
import matplotlib.pyplot as plt

init() # initialize colorama

"""
Issues:
- stuff needs to be thread-safe
"""

# CTRL+F "--WARN--" to find stuff that needs fixing

VERSION="1.0.1"
TIME_DELAY = 5 # time delay between spawning in each round of threads /seconds
CHECK_ACTIVE_DELAY = 0.5 # time delay between checking if the program is still active /seconds
CHECK_TIMEOUT = 30 # after this has finished, it is concluded that the malware is still active and not stopped by the antivirus
HELP_MENU = f"""
Options:
    -h, --help      Show this help menu
    -v, --version   Show version
    -f, --file      File to launch
    -d, --directory Directory from which to launch files (only in the first level)
    -r, --recursive Recursively launch files from any depth within a folder
    -e, --extension Extension to filter by (default: all)
    -t, --threads   Number of threads to use for launching the files every {TIME_DELAY} seconds (default 1)
    -l, --log       Save the output log (default: none)
    -o, --output    Output folder to write a html output document to, previous details will be overwritten, only applicable to directory and recursive modes (default: none)
    -z, --thezoo    Use this flag to launch malware from the thezoo (ie. `py malx.py --thezoo`)

ie.
    py malx.py -d samples/ -e .txt
"""

OUTPUT_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>Malx results</title>
    </head>
    <body>
        <h1>Malx results</h1>
        <p>The graph below shows the number of malware samples running over time after initial invocation. Any samples still remaining at {TIMEOUT} seconds may have not been terminated, and can continue running after this test concludes.
        </p>
        <img src="graph.png" alt="graph">
        <p>{PROACTIVE}% of samples had terminated within the first 5 seconds.
        <br>{ACTIVE}% of samples were still active after {TIMEOUT} seconds.
        <br>{SAMPLES} were tested, and the test time per sample lasted a total of {TIMEOUT} seconds.
        </p>
        <h2>Results</h2>
        <pre>{RESULTS}</pre>
        <h2>Output during execution</h2>
        <pre>{OUTPUT}</pre>
    </body>
</html>
"""

class Threads:
	def newThread(function, args=()):
		new_thread = threading.Thread(target=function, args=args) # error handle threads so they output into log file
		new_thread.start()
		return new_thread

class Tools:
    def countAllInstances(listSearch, items) -> int:
        count = 0
        for item in items:
            count += listSearch.count(item)
        return count

class ErrorIdentifier(object):
    def __init__(self, details = "This is an object assigned to a dict key if the key is invalid"):
        self.details = details

class TimeoutError(Exception):
    pass

class Analysis:
    def isStillActive(pid) -> bool:
        try:
            psutil.Process(pid)
            return True
        except psutil.NoSuchProcess:
            return False
    def waitUntilInactive(pid, time_delay = CHECK_ACTIVE_DELAY, timeout = CHECK_TIMEOUT) -> int:
        iterations = 0
        while Analysis.isStillActive(pid):
            time.sleep(time_delay)
            iterations += 1
            if iterations * time_delay >= timeout:
                raise TimeoutError("Timeout reached")
        return (iterations*time_delay) - (CHECK_ACTIVE_DELAY/2) # time taken to be inactive, average betweeen error intervals

class Interface:
    def catchAsserts(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except AssertionError as e:
                print(f"Invalid options: {e}")
                sys.exit(1)
        return wrapper
    def catchIndexErrors(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except IndexError:
                print(f"Invalid options: The option you provideed is missing a corresponding value")
                sys.exit(1)
        return wrapper
    def catchErrors(ErrorIdentifier, msg, auto_exit=True):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    func(*args, **kwargs)
                except ErrorIdentifier as e:
                    print(msg)
                    print(traceback.format_exc())
                    if auto_exit:
                        sys.exit(1)
            return wrapper
        return decorator
    @catchAsserts
    def main(CHECK_ACTIVE_DELAY=CHECK_ACTIVE_DELAY) -> None: 
        ARGS = sys.argv[1:]
        class ArgsParser(object):
            def __init__(self, ARGS, CHECK_ACTIVE_DELAY=CHECK_ACTIVE_DELAY, CHECK_TIMEOUT=CHECK_TIMEOUT, TIME_DELAY=TIME_DELAY, OUTPUT_HTML_TEMPLATE=OUTPUT_HTML_TEMPLATE): 
                self.ARGS = ARGS
                self.CONFIG = {}
                self.CHECK_ACTIVE_DELAY = CHECK_ACTIVE_DELAY
                self.CHECK_TIMEOUT = CHECK_TIMEOUT
                self.THREAD_DELAY = TIME_DELAY
                self.OUTPUT_HTML_TEMPLATE = OUTPUT_HTML_TEMPLATE
                self.result = ""
                self.resultdata = []
                self.debuglog = ""
                self.lowercaseOptions()
                self.checkNeedsHelp()
                self.validateArgs()
                self.checkVersionArg()
                self.launch()
            # Logging mechanisms
            def debug(self, text) -> None: # debugging info to be sent straight to the log if provided
                # --WARN-- This is a temporary solution, needs to be thread-safe
                print(text)
                self.debuglog += text + "\n"
            def info(self, text) -> None: # info to be sent to the analysis summary
                # --WARN-- This is a temporary solution, needs to be thread-safe
                self.result += text + "\n"
            def showresult(self):
                print(self.result)
                if self.CONFIG["log"]:
                    with open(self.CONFIG["log"], "w") as log:
                        log.write(f"Warning: Some characters may not load in notepad. Read the contents of this file in terminal.\nExecuted: \n{self.debuglog} \n\nResult:\n{self.result}")
                    print(f"Log file saved to {self.CONFIG['log']}")
            def lowercaseOptions(self): 
                for i in range(len(self.ARGS)):
                    if self.ARGS[i][0] == "-":
                        self.ARGS[i] = self.ARGS[i].lower()
            def checkNeedsHelp(self):
                if len(self.ARGS) == 0 or "-h" in self.ARGS or "--help" in self.ARGS:
                    print(HELP_MENU)
                    sys.exit(0)
            def validateArgs(self): # check for invalid arguments and assert before proceeding
                assert Tools.countAllInstances(self.ARGS, ["-f","--file","-d","--directory","-r","--recursive"]) <= 1, "Only one file/directory/recursive flag can be used at one time"
                assert not(Tools.countAllInstances(self.ARGS, ["-f","--file","-d","--directory","-r","--recursive"]) == 0 and Tools.countAllInstances(self.ARGS,["-v","--version","-z","--thezoo"]) == 0), "No operation specified"
            def checkVersionArg(self):
                if "-v" in self.ARGS or "--version" in self.ARGS:
                    print(f"Malx v{VERSION} by Infinity#1056 (Discord)")
                    sys.exit(0)
            def checkForErrorIdentifier(self, inputDict):
                for key in inputDict.keys():
                    if isinstance(inputDict[key], ErrorIdentifier):
                        raise AssertionError("Options were not in a supported format, or were not found")
            @Interface.catchIndexErrors
            @Interface.catchErrors(ValueError, "Invalid options: An option you provided is of the wrong type")
            def launch(self):
                self.CONFIG = {
                    "mode": "file" if "-f" in self.ARGS or "--file" in self.ARGS else "directory" if "-d" in self.ARGS or "--directory" in self.ARGS else "recursive" if "-r" in self.ARGS or "--recursive" in self.ARGS else "thezoo" if "-z" in self.ARGS or "--thezoo" in self.ARGS else ErrorIdentifier(),
                    "location": self.ARGS[self.ARGS.index("-f") + 1] if "-f" in self.ARGS else self.ARGS[self.ARGS.index("--file") + 1] if "--file" in self.ARGS else self.ARGS[self.ARGS.index("-d") + 1] if "-d" in self.ARGS else self.ARGS[self.ARGS.index("--directory") + 1] if "--directory" in self.ARGS else self.ARGS[self.ARGS.index("-r") + 1] if "-r" in self.ARGS else self.ARGS[self.ARGS.index("--recursive") + 1] if "--recursive" in self.ARGS else ErrorIdentifier(),
                    "extension": self.ARGS[self.ARGS.index("-e") + 1] if "-e" in self.ARGS else self.ARGS[self.ARGS.index("--extension") + 1] if "--extension" in self.ARGS else None,
                    "log": self.ARGS[self.ARGS.index("-l") + 1] if "-l" in self.ARGS else self.ARGS[self.ARGS.index("--log") + 1] if "--log" in self.ARGS else None,
                    "output": self.ARGS[self.ARGS.index("-o") + 1] if "-o" in self.ARGS else self.ARGS[self.ARGS.index("--output") + 1] if "--output" in self.ARGS else None,
                    "threads": int(self.ARGS[self.ARGS.index("-t") + 1]) if "-t" in self.ARGS else int(self.ARGS[self.ARGS.index("--threads") + 1]) if "--threads" in self.ARGS else 1
                }
                if self.CONFIG["output"]:
                    if not (self.CONFIG["output"].endswith("/") or self.CONFIG["output"].endswith("\\")):
                        self.CONFIG["output"] += "/"
                if not self.CONFIG["mode"] == "thezoo":
                    self.checkForErrorIdentifier(self.CONFIG)#
                else:
                    self.CONFIG["location"] = "thezoo/" # override folder location to thezoo (unspecified in command line args)
                self.startOperation()
            def startOperation(self):
                # output useful info
                print(f"{Back.GREEN}Launch settings{Back.RESET}")
                for key in self.CONFIG.keys():
                    print(f"{Fore.GREEN}{key.capitalize()}: {self.CONFIG[key]}{Fore.RESET}")
                print(f"\n{Back.GREEN}Output{Back.RESET}")
                # start it
                if self.CONFIG["mode"] == "file":
                    self.launchFile()
                elif self.CONFIG["mode"] == "directory":
                    self.launchDirectory()
                elif self.CONFIG["mode"] == "recursive":
                    self.launchRecursive()
                elif self.CONFIG["mode"] == "thezoo":
                    self.launchTheZoo()
                print(f"\n{Back.GREEN}Result{Back.RESET}")
                self.showresult()
                if self.CONFIG["mode"] == "directory" or self.CONFIG["mode"] == "recursive" or self.CONFIG["mode"] == "thezoo":
                    self.writeOutputContents() # only applicable to the modes above
            def analyseFile(self, file):
                details = {
                    "filename": file,
                    "timeTaken": 0, # time taken in seconds to be terminated
                    "terminated": False # was the program terminated by the antivirus 
                }
                try:
                    process = subprocess.Popen(file)
                    details["timeTaken"] = Analysis.waitUntilInactive(process.pid)
                    details["terminated"] = True
                except TimeoutError:
                    details["timeTaken"] = self.CHECK_TIMEOUT
                return details
            def launchFile(self, customFileName=None):
                filename = customFileName if customFileName else self.CONFIG["location"]
                self.debug(f"{Fore.RED}File: {filename}{Fore.RESET}")
                try:
                    details = self.analyseFile(filename)
                except:
                    # Failed to be executed, likely due to the antivirus preventing this by changing permissions. However, below can accidentally occur due to an internal error, so check traceback.
                    self.info(f"{Fore.RED}File: {filename}{Fore.RESET} could not be executed (see significance below error traceback)")
                    self.info(f"{Fore.RED}Error: {traceback.format_exc()}{Fore.RESET}. \nThis error signifies that this file could not be executed, so was detected by the antivirus before executing, unless an internal error has occurred,")
                    details = {
                        "filename": filename,
                        "timeTaken": 0, # time taken in seconds to be terminated
                        "terminated": True # was the program terminated by the antivirus 
                    }
                self.resultdata.append(details)
                self.info(f"""Executing file "{filename}"
{"Time taken: "+str(details["timeTaken"])+" seconds (terminated)" if details["terminated"] else "Timed out: "+str(details["timeTaken"])+" seconds"}
Time tolerance: ±{self.CHECK_ACTIVE_DELAY/2} seconds\n""")
            def scanFileList(self, scan_files):
                threads = []
                THREAD_CONFLICT_DELAY = 0.05 # delay in seconds to prevent threading conflicts, particularly with output logging
                thread_count = 0
                print(f"Estimated time: { THREAD_CONFLICT_DELAY*len(scan_files) + int(len(scan_files)/self.CONFIG['threads'])*5 + self.CHECK_TIMEOUT }s")
                for file in scan_files:
                    threads.append(Threads.newThread(lambda: self.launchFile(file)))
                    thread_count += 1
                    time.sleep(self.THREAD_DELAY if thread_count % self.CONFIG["threads"] == 0 else THREAD_CONFLICT_DELAY) # where THREAD_DELAY is the delay between bulk spawning threads
                # wait for thread completion
                print(f"{Fore.GREEN}Waiting for results...{Fore.RESET}")
                for thread in threads:
                    thread.join()
            def launchDirectory(self): #NB self.CONFIG["location"] is the directory
                print("Indexing directory...")
                total_files = os.listdir(self.CONFIG["location"])
                scan_files = []
                for filename in total_files:
                    if os.path.isfile(self.CONFIG["location"]+filename):
                        if self.CONFIG["extension"] is None or self.CONFIG["extension"] in filename:
                            scan_files.append(self.CONFIG["location"]+filename)
                print(f"{len(scan_files)} file(s) found")
                self.scanFileList(scan_files)
            def searchDirectory(self, directory):
                total_files = []
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if self.CONFIG["extension"] is None or self.CONFIG["extension"] in file:
                            total_files.append(os.path.join(root, file))
                return total_files
            def launchRecursive(self):
                print("Indexing directories...")
                scan_files = self.searchDirectory(self.CONFIG["location"])
                print("{} file(s) found".format(len(scan_files)))
                self.scanFileList(scan_files)
            def generateGraphXScale(self, step=1):
                x_scale = []
                for i in range(0, self.CHECK_TIMEOUT//step):
                    x_scale.append(i*step)
                return x_scale
            def generateGraphYScale(self, x_scale):
                y_scale = [0]*len(x_scale)
                for i in x_scale:
                    y_scale
                    for result in self.resultdata:
                        if result["timeTaken"] >= i:
                            y_scale[i] += 1
                return y_scale
            def calculateProactive(self, timeout=5): # returns % of samples blocked within the first x seconds
                samples_blocked = 0
                for result in self.resultdata:
                    if result["timeTaken"] <= timeout:
                        samples_blocked += 1
                return round((samples_blocked/len(self.resultdata))*100,1)
            def calculateStillActive(self, y_scale):
                still_active = y_scale[len(y_scale)-1]
                return round((still_active/len(self.resultdata))*100,1)
            def writeOutputContents(self):
                if self.CONFIG["output"] is not None:
                    if not os.path.exists(self.CONFIG["output"]):
                        os.makedirs(self.CONFIG["output"])
                    # get graph data & generate output graph
                    x_scale = self.generateGraphXScale()
                    y_scale = self.generateGraphYScale(x_scale)
                    plt.plot(x_scale, y_scale)
                    plt.title("Malware remaining active")
                    plt.ylabel("Samples active")
                    plt.xlabel("Time (s)")
                    plt.savefig(self.CONFIG["output"]+"/graph.png", dpi=100)
                    # get extra data
                    proactive = self.calculateProactive() # percentage proactively blocked
                    # generate output html file
                    output_html = self.OUTPUT_HTML_TEMPLATE
                    output_html = output_html.replace("{PROACTIVE}", str(proactive)
                    ).replace("{SAMPLES}", str(len(self.resultdata))
                    ).replace("{TIMEOUT}",str(self.CHECK_TIMEOUT)
                    ).replace("{ACTIVE}",str(self.calculateStillActive(y_scale))
                    ).replace("{RESULTS}",self.result
                    ).replace("{OUTPUT}",self.debuglog.replace(Fore.RED,"").replace(Fore.RESET,""))
                    with open(self.CONFIG["output"]+"/index.html", "w") as f:
                        f.write(output_html)
                    print(f"\n{Fore.GREEN}Written output details to {self.CONFIG['output']}, and a complete document can be found at {self.CONFIG['output']}/index.html {Fore.RESET}")
            def extractTheZoo(self, outputFolder="downloads/"): # extract password-protected archives into an output folder
                if not os.path.exists(outputFolder):
                    os.makedirs(outputFolder)
                for count, malwareFolder in enumerate(os.listdir("theZoo/malware/Binaries")):
                    if os.path.isdir("theZoo/malware/Binaries/"+malwareFolder):
                        try:
                            # get password
                            for filename in os.listdir("theZoo/malware/Binaries/"+malwareFolder):
                                if filename.endswith(".pass"):
                                    password = open("theZoo/malware/Binaries/"+malwareFolder+"/"+filename, "r").read()
                                    break
                            # extract zip file with password
                            for filename in os.listdir("theZoo/malware/Binaries/"+malwareFolder):
                                if filename.endswith(".zip"):
                                    with ZipFile("theZoo/malware/Binaries/"+malwareFolder+"/"+filename) as zf:
                                        zf.extractall(pwd=password.encode(), path=outputFolder)
                                    self.debug(f"{count+1}/{len(os.listdir('theZoo/malware/Binaries'))}: Extracted {filename}, with password {password}")
                        except:
                            print(f"{Fore.RED}Failed to extract {malwareFolder}: \n{traceback.format_exc()} {Fore.RESET}")
            def formatZooMalware(self, outputFolder="downloads/"): # check for missing extensions
                for filename in os.listdir(outputFolder):
                    if not "." in filename and os.path.isfile(outputFolder+filename):
                        try:
                            os.rename(outputFolder+filename, outputFolder+filename+".exe")
                        except:
                            print(f"{Fore.RED}Failed to rename {filename} to {filename}.exe: \n{traceback.format_exc()}{Fore.RESET}")
            def cleanUpZoo(self):
                # remove downloads and zoo directory
                if os.path.exists("downloads/"):
                    shutil.rmtree("downloads/")
                if os.path.exists("theZoo/"):
                    shutil.rmtree("theZoo/")
            def launchTheZoo(self) -> None:
                # download the zoo if not found
                if os.path.exists("theZoo/") and os.path.exists("downloads/"):
                    self.debug(f"{Fore.GREEN}Found theZoo directory, continuining with analysis (delete theZoo/ folder to re-download)...{Fore.RESET}")
                else:
                    self.debug(f"{Fore.GREEN}Downloading theZoo... {Fore.RESET}\n{Back.RED}{Fore.WHITE}WARNING: This process may set off the antivirus initially. Turn off the antivirus and hit ENTER{Fore.RESET}{Back.RESET}")
                    input()
                    # setup for clean installation
                    self.debug(f"{Fore.GREEN}Cleaning up previous downloads..{Fore.RESET}")
                    try:
                        self.cleanUpZoo()
                    except:
                        print(f"{Fore.RED}Failed to clean up previous downloads: \n{traceback.format_exc()} \nDelete /theZoo and downloads/ folders, then hit ENTER to continue{Fore.RESET}")
                        input()
                    # clone the repository
                    self.debug(f"{Fore.GREEN}Cloning repository...{Fore.RESET}")
                    os.makedirs("theZoo/")
                    Repo.clone_from("https://github.com/ytisf/theZoo","theZoo/") # test repository: "https://github.com/safety-jim/test"
                    # extract all password-protected archives
                    self.debug(f"{Fore.GREEN}Extracting malware...{Fore.RESET}")
                    self.extractTheZoo()
                    # format
                    self.debug(f"{Fore.GREEN}Formatting malware...{Fore.RESET}")
                    self.formatZooMalware()
                    # conclude
                    self.debug(f"{Fore.GREEN}Setup complete.{Fore.RESET}")
                self.debug(f"{Fore.GREEN}Starting analysis...{Fore.RESET}")
                self.CONFIG["location"] = "downloads/" # location of files changed to downloads now
                self.debug(f"{Fore.RED}Make sure the antivirus is enabled. \nHit ENTER to continue.{Fore.RESET}")
                input()
                self.debug(f"{Back.RED}WARNING: By continuing you ACCEPT that we take no responsibility for the irrepairable damage this may cause to your device. This should not be run on a main computer, instead, a Virtual Machine. If you do not know what you are doing, and how to correctly configure the Virtual Machine, DO NOT PROCEED. {Back.RESET} \n\n{Fore.RED}Type yes to continue {Fore.RESET}")
                result = input("yes/no: ")
                if result.lower() == "yes":
                    result = input("Are you sure? yes/no: ")
                    if result.lower() == "yes":
                        self.launchRecursive()
                    else:
                        self.debug(f"{Fore.RED}Aborted{Fore.RESET}")
                        sys.exit(0)
                else:
                    self.debug(f"{Fore.RED}Aborted{Fore.RESET}")
                    sys.exit(0)
        ArgsParser(ARGS)

if __name__ == "__main__":
    Interface.main()
