import enum
import io
import pathlib
import sys
import typing

if typing.TYPE_CHECKING:
    from .uxn import UXN


def stat(p: pathlib.Path) -> str:
    if p.is_dir():
        return "----"
    if p.is_file():
        if (size := p.stat().st_size) > 0xFFFF:
            # larger than 64KB
            return "????"
        return f"{size:x}".rjust(4, "0").lower()
    return "!!!!"


class File:
    class State(enum.IntEnum):
        IDLE = 0
        FILE_READ = 1
        FILE_WRITE = 2
        DIR_READ = 3
        DIR_WRITE = 4

    def __init__(self):
        self.cwd = pathlib.Path.cwd().absolute()
        self.name = ""
        self.state = self.State.IDLE
        self.buffer = None

    def setname(self, mem: memoryview):
        name = mem.tobytes()
        name = name[: name.find(0)]
        name = name.decode("utf-8")
        if self.name == name:
            return
        self.name = name
        self.state = self.State.IDLE
        if self.buffer:
            self.buffer.close()
            self.buffer = None

    def check(self) -> pathlib.Path | None:
        p = pathlib.Path(self.name).absolute()
        if not p.is_relative_to(self.cwd):
            # only allow access to files under the current working directory
            return None
        return p

    def read(self, mem: memoryview) -> int:
        if (p := self.check()) is None:
            return 0
        try:
            if p.is_file() and self.state != self.State.FILE_READ:
                self.buffer = p.open("rb")
                self.state = self.State.FILE_READ
            elif p.is_dir() and self.state != self.State.DIR_READ:
                self.buffer = io.BytesIO(
                    "".join(f"{stat(f)} {f.name}\n" for f in p.iterdir()).encode()
                )
                self.state = self.State.DIR_READ
            if not self.buffer:
                return 0
            return self.buffer.readinto(mem)
        except Exception:
            return 0

    def write(self, mem: memoryview, *, append: bool) -> int:
        if (p := self.check()) is None:
            return 0
        try:
            if self.name.endswith("/") and self.state != self.State.DIR_WRITE:
                p.mkdir(parents=True, exist_ok=True)
                self.state = self.State.DIR_WRITE
                return 1
            if self.state != self.State.FILE_WRITE:
                p.parent.mkdir(parents=True, exist_ok=True)
                self.buffer = p.open("ab" if append else "wb")
                self.state = self.State.FILE_WRITE
            if not self.buffer:
                return 0
            return self.buffer.write(mem)
        except Exception:
            return 0

    def stat(self, mem: memoryview) -> int:
        if (p := self.check()) is None:
            return 0
        sz = len(mem)
        st = stat(p)[-sz:]
        st = st.rjust(sz, "0" if st[0].isalnum() else st[0])
        mem[:] = st.encode()
        return sz

    def delete(self) -> int:
        if (p := self.check()) is None:
            return 0
        if not p.exists():
            return 0
        try:
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                p.rmdir()
        except Exception:
            return 0
        return 1


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

    FIL_VECTOR = 0xA0
    FIL_SUCCESS = 0xA2
    FIL_STAT = 0xA4
    FIL_DELETE = 0xA6
    FIL_APPEND = 0xA7
    FIL_NAME = 0xA8
    FIL_LENGTH = 0xAA
    FIL_READ = 0xAC
    FIL_WRITE = 0xAE


class Varvara:
    def __init__(self, uxn: UXN):
        self.uxn = uxn
        self.arr = bytearray(0x100)
        self.mem = memoryview(self.arr)
        self.file = File()

    def set(self, addr: int, x: int, *, short: bool):
        if short:
            self.mem[addr] = (x >> 8) & 0xFF
            self.mem[addr + 1] = x & 0xFF
        else:
            self.mem[addr] = x

        match addr:
            case Dev.CSL_WRITE:
                sys.stdout.write(chr(self.mem[addr]))
            case Dev.FIL_NAME:
                st = self.get(Dev.FIL_NAME, short=True)
                self.file.setname(self.uxn.mem[st:])
            case Dev.FIL_READ:
                st = self.get(Dev.FIL_READ, short=True)
                ed = st + self.get(Dev.FIL_LENGTH, short=True)
                sz = self.file.read(self.uxn.mem[st:ed])
                self.set(Dev.FIL_SUCCESS, sz, short=True)
            case Dev.FIL_WRITE:
                st = self.get(Dev.FIL_WRITE, short=True)
                ed = st + self.get(Dev.FIL_LENGTH, short=True)
                sz = self.file.write(
                    self.uxn.mem[st:ed],
                    append=self.get(Dev.FIL_APPEND, short=True) != 0,
                )
                self.set(Dev.FIL_SUCCESS, sz, short=True)
            case Dev.FIL_STAT:
                st = self.get(Dev.FIL_STAT, short=True)
                ed = st + self.get(Dev.FIL_LENGTH, short=True)
                sz = self.file.stat(self.uxn.mem[st:ed])
                self.set(Dev.FIL_SUCCESS, sz, short=True)
            case Dev.FIL_DELETE:
                ok = self.file.delete()
                self.set(Dev.FIL_SUCCESS, 1 if ok else 0, short=True)
            case _:
                pass

    def get(self, addr: int, *, short: bool) -> int:
        if short:
            return (self.mem[addr] << 8) | self.mem[addr + 1]
        return self.mem[addr]
