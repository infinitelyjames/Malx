import sys

VERSION="1.0.1"
HELP_MENU = """
Options:
    -h, --help      Show this help menu
    -v, --version   Show version
    -f, --file      File to launch
    -d, --directory Directory from which to launch files (only in the first level)
    -r, --recursive Recursively launch files from any depth within a folder
    -e, --extension Extension to filter by
    -l, --log       Log file to write to
    -t, --thread    Number of threads to use for launching the files (default 1)

ie.
    malx.py -d samples/ -e .txt
"""

class Tools:
    def countAllInstances(listSearch, items) -> int:
        count = 0
        for item in items:
            count += listSearch.count(item)
        return count

class Interface:
    def catchAsserts(func):
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except AssertionError as e:
                print(f"Invalid options specified: {e}")
                sys.exit(1)
        return wrapper
    @catchAsserts
    def main() -> None: 
        ARGS = sys.argv[1:]
        class ArgsParser(object):
            def __init__(self, ARGS): 
                self.ARGS = ARGS
                self.lowercaseOptions()
                self.checkNeedsHelp()
                self.validateArgs()
                self.checkVersionArg()
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
            def checkVersionArg(self):
                if "-v" in self.ARGS or "--version" in self.ARGS:
                    print(f"Malx version {VERSION}")
                    sys.exit(0)
        ArgsParser(ARGS)

if __name__ == "__main__":
    Interface.main()