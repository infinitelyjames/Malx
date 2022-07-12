# Malx - Automatic malware executer
An automatic mass sample (malware) execution based on that used by the PC Security Channel (YouTube), designed to test an antivirus over a number of samples. This tool has been tested and designed to run on Windows.

## Setup
Dependencies needing to be installed can be found in `requirements.txt` and installed with `pip install -r requirements.txt`.
Then, simply run with `python malx.py --help` (or `py malx.py --help`) for the supported commands.

## Recommended usage

1. Create a folder called `samples/`.
2. Paste all your malicious exes into this folder.
3. Run `py malx.py -e .exe -d samples/` (Run exe files in the folder called samples). If you're not sure how many threads to specify, keep it as  default (1), and increase if the CPU can be utilised further.
4. Wait for the results.

## Disclaimer
Do not use this tool to run malware on your main machine. A virtual machine should be used.
Use at your own risk.

Some sources of error may occur if you select too many threads when running the program. If you find the vm constantly on 100% CPU usage, then the number of threads is too high.