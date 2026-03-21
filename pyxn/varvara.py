import enum
import io
import pathlib
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .uxn import UXN


def stat(p: pathlib.Path) -> str:
    if p.is_dir():
        return "----"
    if p.is_file():
        if (size := p.stat().st_size) > 0xFFFF:
            # larger than 64KB
            return "????"
        return f"{size:04x}"
    return "!!!!"


class File:
    __slots__ = ("cwd", "name", "state", "buffer")

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
    SYSTEM_EXPANSION = 0x02
    SYSTEM_WST = 0x04
    SYSTEM_RST = 0x05
    SYSTEM_METADATA = 0x06
    SYSTEM_RED = 0x08
    SYSTEM_GREEN = 0x0A
    SYSTEM_BLUE = 0x0C
    SYSTEM_DEBUG = 0x0E
    SYSTEM_STATE = 0x0F

    CONSLOE_VECTOR = 0x10
    CONSOLE_READ = 0x12
    CONSOLE_TYPE = 0x17
    CONSOLE_WRITE = 0x18
    CONSOLE_ERROR = 0x19

    FILE_VECTOR = 0xA0
    FILE_SUCCESS = 0xA2
    FILE_STAT = 0xA4
    FILE_DELETE = 0xA6
    FILE_APPEND = 0xA7
    FILE_NAME = 0xA8
    FILE_LENGTH = 0xAA
    FILE_READ = 0xAC
    FILE_WRITE = 0xAE

    DATETIME_YEAR_H = 0xC0
    DATETIME_YEAR_L = 0xC1
    DATETIME_MONTH = 0xC2
    DATETIME_DAY = 0xC3
    DATETIME_HOUR = 0xC4
    DATETIME_MINIUTE = 0xC5
    DATETIME_SECOND = 0xC6
    DATETIME_DOTW = 0xC7
    DATETIME_DOTY_H = 0xC8
    DATETIME_DOTY_L = 0xC9
    DATETIME_ISDST = 0xCA


def t() -> time.struct_time:
    # Python's struct_time is different from C's struct_time
    # tm_year already has +1900
    # tm_mon is [1-12], not [0-11]
    # tm_wday starts on Monday, not Sunday
    # tm_yday is [1-366], not [0-365]
    return time.localtime()


class Varvara:
    __slots__ = ("uxn", "mem", "file", "vtable")

    def __init__(self, uxn: UXN, mem: memoryview):
        self.uxn = uxn
        self.mem = mem
        self.file = File()

        self.vtable = [None] * 0x100
        for dev in Dev:
            self.vtable[dev] = getattr(self, dev.name, None)

    def get(self, addr: int, *, short: bool) -> int:
        match addr:
            case Dev.SYSTEM_WST:
                self.mem[addr] = self.uxn.wst.top
            case Dev.SYSTEM_RST:
                self.mem[addr] = self.uxn.rst.top
            case Dev.DATETIME_YEAR_H | Dev.DATETIME_YEAR_L:
                y = t().tm_year
                self.mem[Dev.DATETIME_YEAR_H] = y >> 8
                self.mem[Dev.DATETIME_YEAR_L] = y & 0xFF
            case Dev.DATETIME_DAY:
                self.mem[addr] = t().tm_mday
            case Dev.DATETIME_MONTH:
                self.mem[addr] = t().tm_mon - 1
            case Dev.DATETIME_HOUR:
                self.mem[addr] = t().tm_hour
            case Dev.DATETIME_MINIUTE:
                self.mem[addr] = t().tm_min
            case Dev.DATETIME_SECOND:
                self.mem[addr] = t().tm_sec
            case Dev.DATETIME_DOTW:
                return (t().tm_wday + 1) % 7
            case Dev.DATETIME_DOTY_H | Dev.DATETIME_DOTY_L:
                d = t().tm_yday - 1
                self.mem[Dev.DATETIME_DOTY_H] = d >> 8
                self.mem[Dev.DATETIME_DOTY_L] = d & 0xFF
            case Dev.DATETIME_ISDST:
                self.mem[addr] = t().tm_isdst

        if short:
            return (self.mem[addr] << 8) | self.mem[addr + 1]
        return self.mem[addr]

    def set(self, addr: int, x: int, *, short: bool):
        if short:
            self.mem[addr] = (x >> 8) & 0xFF
            self.mem[addr + 1] = x & 0xFF
        else:
            self.mem[addr] = x

        if f := self.vtable[addr]:
            f(x)

    # ruff: disable[N802]
    def SYSTEM_EXPANSION(self, x: int):
        op = self.uxn.memget(x, short=False)
        exp = self.uxn.memget(x + 1, short=True)
        if op:
            # 0x01, 0x02
            sbank = self.uxn.memget(x + 3, short=True)
            saddr = self.uxn.memget(x + 5, short=True)
            dbank = self.uxn.memget(x + 7, short=True)
            daddr = self.uxn.memget(x + 9, short=True)
            src = sbank * self.uxn.MEMSIZE + saddr
            dst = dbank * self.uxn.MEMSIZE + daddr
            if op == 0x01:
                self.uxn.mem[dst : dst + exp] = self.uxn.mem[src : src + exp]
            else:
                for i in range(exp - 1, -1, -1):
                    self.uxn.mem[dst + i] = self.uxn.mem[src + i]
        else:
            # 0x00
            bank = self.uxn.memget(x + 3, short=True)
            addr = self.uxn.memget(x + 5, short=True)
            val = self.uxn.memget(x + 7, short=False)
            dst = bank * self.uxn.MEMSIZE + addr
            self.uxn.mem[dst : dst + exp] = val.to_bytes(1) * exp

    def SYSTEM_WST(self, x: int):
        self.uxn.wst.top = x

    def SYSTEM_RST(self, x: int):
        self.uxn.rst.top = x

    def SYSTEM_DEBUG(self, x: int):
        if x != 0:
            print(f"WST{self.uxn.wst.debug()}")
            print(f"RST{self.uxn.rst.debug()}")

    def CONSOLE_WRITE(self, x: int):
        sys.stdout.write(chr(x))

    def CONSOLE_ERROR(self, x: int):
        sys.stderr.write(chr(x))

    def FILE_NAME(self, x: int):
        self.file.setname(self.uxn.mem[x:])

    def FILE_READ(self, x: int):
        ed = min(x + self.get(Dev.FILE_LENGTH, short=True), self.uxn.MEMSIZE)
        sz = self.file.read(self.uxn.mem[x:ed])
        self.set(Dev.FILE_SUCCESS, sz, short=True)

    def FILE_WRITE(self, x: int):
        ed = min(x + self.get(Dev.FILE_LENGTH, short=True), self.uxn.MEMSIZE)
        sz = self.file.write(
            self.uxn.mem[x:ed],
            append=self.get(Dev.FILE_APPEND, short=True) != 0,
        )
        self.set(Dev.FILE_SUCCESS, sz, short=True)

    def FILE_STAT(self, x: int):
        ed = min(x + self.get(Dev.FILE_LENGTH, short=True), self.uxn.MEMSIZE)
        sz = self.file.stat(self.uxn.mem[x:ed])
        self.set(Dev.FILE_SUCCESS, sz, short=True)

    def FILE_DELETE(self, _: int):
        ok = self.file.delete()
        self.set(Dev.FILE_SUCCESS, ok, short=True)

    # ruff: enable[N802]
