import pathlib
import sys

from .uxn import UXN

if __name__ == "__main__":
    uxn = UXN()
    uxn.load(pathlib.Path(sys.argv[1]).read_bytes())
    uxn.reset(args=sys.argv, stdin=sys.stdin)
