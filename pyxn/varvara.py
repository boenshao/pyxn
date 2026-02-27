import enum
import sys
import typing

if typing.TYPE_CHECKING:
    from .uxn import UXN


class ConsoleType(enum.IntEnum):
    NO_QUEUE = 0x00
    STDIN = 0x01
    ARGUMENT = 0x02
    ARGUMENT_SPACER = 0x03
    ARGUMENT_END = 0x04


class Dev(enum.IntEnum):
    SYS_EXPANSION = 0x02
    SYS_WST = 0x04
    SYS_RST = 0x05
    SYS_METADATA = 0x06
    SYS_RED = 0x08
    SYS_GREEN = 0x0A
    SYS_BLUE = 0x0C
    SYS_DEBUG = 0x0E
    SYS_STATE = 0x0F

    CSL_VECTOR = 0x10
    CSL_READ = 0x12
    CSL_TYPE = 0x17
    CSL_WRITE = 0x18
    CSL_ERROR = 0x19


class Varvara:
    def __init__(self, uxn: UXN):
        self.uxn = uxn
        self.mem = bytearray(0x100)

    def set(self, addr: int, x: int, *, short: bool):
        if short:
            self.mem[addr] = (x >> 8) & 0xFF
            self.mem[addr + 1] = x & 0xFF
        else:
            self.mem[addr] = x

        match addr:
            case Dev.CSL_WRITE:
                sys.stdout.write(chr(self.mem[addr]))
            case _:
                pass

    def get(self, addr: int, *, short: bool) -> int:
        if short:
            return (self.mem[addr] << 8) | self.mem[addr + 1]
        return self.mem[addr]
