import enum


class ConsoleType(enum.IntEnum):
    NO_QUEUE = 0x00
    STDIN = 0x01
    ARGUMENT = 0x02
    ARGUMENT_SPACER = 0x03
    ARGUMENT_END = 0x04


class Dev(enum.IntEnum):
    SYSTEM_EXPANSION = 0x02
    SYSTEM_WST = 0x04
    SYSTEM_RST = 0x05
    SYSTEM_METADATA = 0x06
    SYSTEM_RED = 0x08
    SYSTEM_GREEN = 0x0A
    SYSTEM_BLUE = 0x0C
    SYSTEM_DEBUG = 0x0E
    SYSTEM_STATE = 0x0F

    CONSOLE_VECTOR = 0x10
    CONSOLE_READ = 0x12
    CONSOLE_TYPE = 0x17
    CONSOLE_WRITE = 0x18
    CONSOLE_ERROR = 0x19


class Varvara:
    def __init__(self):
        self.mem = bytearray(0x100)

    def set(self, addr: int, x: int, *, short: bool):
        if short:
            self.mem[addr] = (x >> 8) & 0xFF
            self.mem[addr + 1] = x & 0xFF
        else:
            self.mem[addr] = x

        match addr:
            case Dev.CONSOLE_WRITE:
                print(chr(self.mem[addr]), end="")
            case _:
                pass

    def get(self, addr: int, *, short: bool) -> int:
        if short:
            return (self.mem[addr] << 8) | self.mem[addr + 1]
        return self.mem[addr]
