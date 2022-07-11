import sys
import psutil # pip install -r requirements.txt
import time

VERSION="1.0.1"
TIME_DELAY = 5 # time delay between spawning in each round of threads /seconds
CHECK_ACTIVE_DELAY = 0.5 # time delay between checking if the program is still active /seconds
HELP_MENU = """
Options:
    -h, --help      Show this help menu
    -v, --version   Show version
    -f, --file      File to launch
    -d, --directory Directory from which to launch files (only in the first level)
    -r, --recursive Recursively launch files from any depth within a folder
    -e, --extension Extension to filter by (default: all)
    -t, --thread    Number of threads to use for launching the files (default 1)
    -l, --log       Log file to write to for extra details (default: none)
    -o, --output    Output file to write a condensed summary to (default: none)

ie.
    malx.py -d samples/ -e .txt
"""

# Logging mechanisms
def debug(): # debugging info to be sent straight to the log if provided
    pass 

def info(): # info to be sent to the analysis summary
    pass


class Tools:
    def countAllInstances(listSearch, items) -> int:
        count = 0
        for item in items:
            count += listSearch.count(item)
        return count

class ErrorIdentifier(object):
    def __init__(self, details = "This is an object assigned to a dict key if the key is invalid"):
        self.details = details

class Analysis:
    def isStillActive(pid) -> bool:
        try:
            psutil.Process(pid)
            return True
        except psutil.NoSuchProcess:
            return False
    def waitUntilInactive(pid):
        while Analysis.isStillActive(pid):
            time.sleep(0.5)

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
    @catchAsserts
    def main() -> None: 
        ARGS = sys.argv[1:]
        class ArgsParser(object):
            def __init__(self, ARGS): 
                self.ARGS = ARGS
                self.CONFIG = {}
                #print(self.ARGS)
                self.lowercaseOptions()
                self.checkNeedsHelp()
                self.validateArgs()
                self.checkVersionArg()
                self.launch()
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
                assert not(Tools.countAllInstances(self.ARGS, ["-f","--file","-d","--directory","-r","--recursive"]) == 0 and Tools.countAllInstances(self.ARGS,["-v","--version"]) == 0), "No operation specified"
            def checkVersionArg(self):
                if "-v" in self.ARGS or "--version" in self.ARGS:
                    print(f"Malx version {VERSION}")
                    sys.exit(0)
            def checkForErrorIdentifier(self, inputDict):
                for key in inputDict.keys():
                    if isinstance(inputDict[key], ErrorIdentifier):
                        raise AssertionError("Options were not in a supported format, or were not found")
            @Interface.catchIndexErrors
            def launch(self):
                self.CONFIG = {
                    "mode": "file" if "-f" in self.ARGS or "--file" in self.ARGS else "directory" if "-d" in self.ARGS or "--directory" in self.ARGS else "recursive" if "-r" in self.ARGS or "--recursive" in self.ARGS else ErrorIdentifier(),
                    "file": self.ARGS[self.ARGS.index("-f") + 1] if "-f" in self.ARGS or "--file" in self.ARGS else self.ARGS[self.ARGS.index("-d") + 1] if "-d" in self.ARGS or "--directory" in self.ARGS else self.ARGS[self.ARGS.index("-r") + 1] if "-r" in self.ARGS or "--recursive" in self.ARGS else ErrorIdentifier(),
                    "extension": self.ARGS[self.ARGS.index("-e") + 1] if "-e" in self.ARGS or "--extension" in self.ARGS else None,
                    "log": self.ARGS[self.ARGS.index("-l") + 1] if "-l" in self.ARGS or "--log" in self.ARGS else None,
                    "output": self.ARGS[self.ARGS.index("-o") + 1] if "-o" in self.ARGS or "--output" in self.ARGS else None,
                    "threads": self.ARGS[self.ARGS.index("-t") + 1] if "-t" in self.ARGS or "--thread" in self.ARGS else 1
                }
                #print(self.CONFIG)
                self.checkForErrorIdentifier(self.CONFIG)#
                self.startOperation()
            def startOperation(self):
                if self.CONFIG["mode"] == "file":
                    self.launchFile()
                elif self.CONFIG["mode"] == "directory":
                    self.launchDirectory()
                elif self.CONFIG["mode"] == "recursive":
                    self.launchRecursive()
            def analyseFile(self, file):
                pass
        ArgsParser(ARGS)

if __name__ == "__main__":
    Interface.main()