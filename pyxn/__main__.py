import pathlib
import sys

from .uxn import UXN
from .varvara import Dev, ConsoleType


def console_input(uxn: UXN, c: int, type: ConsoleType):
    uxn.dev.set(Dev.CONSOLE_TYPE, type, short=False)
    uxn.dev.set(Dev.CONSOLE_READ, c, short=False)
    uxn.eval(uxn.dev.get(Dev.CONSOLE_VECTOR, short=True))


def main():
    uxn = UXN()
    uxn.load(pathlib.Path(sys.argv[1]).read_bytes())
    uxn.dev.set(Dev.CONSOLE_TYPE, len(sys.argv[1]) > 2, short=False)

    uxn.eval(UXN.PCSTART)
    if uxn.dev.get(Dev.CONSOLE_VECTOR, short=True):
        for i in range(2, len(sys.argv)):
            for c in sys.argv[i]:
                console_input(uxn, ord(c), ConsoleType.ARGUMENT)
            console_input(
                uxn,
                0x0A,  # newline
                (
                    ConsoleType.ARGUMENT_END
                    if i + 1 == len(sys.argv)
                    else ConsoleType.ARGUMENT_SPACER
                ),
            )

    for line in sys.stdin:
        for c in line:
            console_input(uxn, ord(c), ConsoleType.STDIN)
        console_input(uxn, 0, ConsoleType.ARGUMENT_END)


if __name__ == "__main__":
    main()
