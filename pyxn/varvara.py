import enum


class Dev(enum.IntEnum):
    CONSOLE = 0x10
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
