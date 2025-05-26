import sys

if not (sys.version_info.major == 3 and sys.version_info.minor > 6):
    raise Exception("Python version must be greater than 3.6")

from cli import *
# import interactive # TODO

if __name__ == '__main__':
    cli()
    #interactive()