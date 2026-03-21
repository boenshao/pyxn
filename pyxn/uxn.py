import enum
import mmap
from typing import TextIO

from .varvara import ConsoleType, Dev, Varvara


class StackOverflowError(Exception):
    pass


class StackUnderflowError(Exception):
    pass


class InvalidInstructionError(Exception):
    pass


class Stack:
    __slots__ = ("mem", "size", "top", "ptr", "keep", "short")

    def __init__(self, mem: memoryview):
        self.mem = mem
        self.size = len(mem)
        self.top = 0
        self.ptr = 0
        self.keep = False
        self.short = False

    def load(self, arr: bytes, *, keep: bool = False, short: bool = False):
        self.mem[: len(arr)] = arr
        self.top = len(arr)
        self.ptr = self.top
        self.keep = keep
        self.short = short

    def modeset(self, *, keep: bool, short: bool):
        self.ptr = self.top
        self.keep = keep
        self.short = short

    def push(self, x: int, *, short: bool | None = None):
        if short is None:
            short = self.short
        if short:
            self.push2(x)
        else:
            self.push1(x)

    def pop(self, *, short: bool | None = None) -> int:
        if short is None:
            short = self.short
        if short:
            return self.pop2()
        return self.pop1()

    def push1(self, x: int):
        if self.top >= self.size:
            raise StackOverflowError
        self.mem[self.top] = x & 0xFF
        self.top += 1

    def pop1(self) -> int:
        if self.ptr == 0:
            raise StackUnderflowError
        self.ptr -= 1
        if not self.keep:
            self.top = self.ptr
        return self.mem[self.ptr]

    def push2(self, x: int):
        if self.top + 1 >= self.size:
            raise StackOverflowError
        self.mem[self.top] = (x >> 8) & 0xFF
        self.mem[self.top + 1] = x & 0xFF
        self.top += 2

    def pop2(self) -> int:
        if self.ptr < 2:
            raise StackUnderflowError
        self.ptr -= 2
        if not self.keep:
            self.top = self.ptr
        return (self.mem[self.ptr] << 8) | self.mem[self.ptr + 1]

    def debug(self) -> str:
        s = "|" if self.top - 8 == 0 else " "
        for i in range(self.top - 8, self.top):
            s += f"{self.mem[i]:02x}" if i >= 0 else "00"
            s += "|" if i == -1 else " "
        s += f"<{self.top:02x}"
        return s

    def __repr__(self) -> str:
        return str([hex(self.mem[i]) for i in range(self.top)])


class Mask(enum.IntEnum):
    KEEP = 0b10000000
    RETURN = 0b01000000
    SHORT = 0b00100000
    MODE = 0b11100000
    CODE = 0b00011111


class Op(enum.IntEnum):
    # Immediate
    JCI = 0x20
    JMI = 0x40
    JSI = 0x60
    LIT = 0x80

    # Stack I
    BRK = 0x00
    INC = 0x01
    POP = 0x02
    NIP = 0x03

    # Stack II
    SWP = 0x04
    ROT = 0x05
    DUP = 0x06
    OVR = 0x07

    # Logic
    EQU = 0x08
    NEQ = 0x09
    GTH = 0x0A
    LTH = 0x0B

    # Stash
    JMP = 0x0C
    JCN = 0x0D
    JSR = 0x0E
    STH = 0x0F

    # Memory I
    LDZ = 0x10
    STZ = 0x11
    LDR = 0x12
    STR = 0x13

    # Memory II
    LDA = 0x14
    STA = 0x15
    DEI = 0x16
    DEO = 0x17

    # Arithmetic
    ADD = 0x18
    SUB = 0x19
    MUL = 0x1A
    DIV = 0x1B

    # Bitwise
    AND = 0x1C
    ORA = 0x1D
    EOR = 0x1E
    SFT = 0x1F


IMM = (Op.JCI, Op.JMI, Op.JSI)


def signed(x: int) -> int:
    return x - 0x100 if x >= 0x80 else x


def signed2(x: int) -> int:
    return x - 0x10000 if x >= 0x8000 else x


class UXN:
    __slots__ = ("mem", "dev", "wst", "rst", "pc", "vtable")

    BNKSZIE = 0x10  # 16
    MEMSIZE = 0x10000  # 65536, 64k
    DEVSIZE = 0x100  # 256
    STKSIZE = 0x100  # 256
    PCSTART = 0x100

    def __init__(self):
        mm = mmap.mmap(
            -1,
            self.DEVSIZE  # device memory
            + self.STKSIZE  # wst
            + self.STKSIZE  # rst
            + (self.MEMSIZE * self.BNKSZIE),  # main memory
            mmap.MAP_PRIVATE | mmap.MAP_ANONYMOUS,
        )
        buf = memoryview(mm)

        st, ed = 0, self.DEVSIZE
        self.dev = Varvara(self, buf[st:ed])
        st, ed = ed, ed + self.STKSIZE
        self.wst = Stack(buf[st:ed])
        st, ed = ed, ed + self.STKSIZE
        self.rst = Stack(buf[st:ed])
        st = ed
        self.mem = buf[st:]

        self.pc = self.PCSTART
        self.vtable = [None] * 0x100
        for op in Op:
            if op == Op.BRK:
                continue
            self.vtable[op.value if op != Op.LIT else 0x00] = getattr(self, op.name)

    def load(self, rom: bytes):
        self.mem[self.PCSTART : self.PCSTART + len(rom)] = rom

    def reset(self, args: list[str] | None = None, stdin: TextIO | None = None):
        args = args or []
        self.dev.set(Dev.CONSOLE_TYPE, len(args) > 2, short=False)
        self.eval(self.PCSTART)
        if self.dev.get(Dev.CONSLOE_VECTOR, short=True):
            self._console_parse_args(args)
        if stdin:
            self._console_read_stdin(stdin)

    def _console_input(self, c: int, t: ConsoleType):
        self.dev.set(Dev.CONSOLE_TYPE, t, short=False)
        self.dev.set(Dev.CONSOLE_READ, c, short=False)
        self.dev.uxn.eval(self.dev.get(Dev.CONSLOE_VECTOR, short=True))

    def _console_parse_args(self, args: list[str]):
        for i in range(2, len(args)):
            for c in args[i]:
                self._console_input(ord(c), ConsoleType.ARGUMENT)
            self._console_input(
                0x0A,  # newline
                (
                    ConsoleType.ARGUMENT_END
                    if i + 1 == len(args)
                    else ConsoleType.ARGUMENT_SPACER
                ),
            )

    def _console_read_stdin(self, stdin: TextIO):
        for line in stdin:
            for c in line:
                self._console_input(ord(c), ConsoleType.STDIN)
            self._console_input(0, ConsoleType.ARGUMENT_END)

    def memset(self, addr: int, x: int, *, short: bool):
        if short:
            self.mem[addr] = (x >> 8) & 0xFF
            self.mem[addr + 1] = x & 0xFF
        else:
            self.mem[addr] = x

    def memget(self, addr: int, *, short: bool) -> int:
        if short:
            return (self.mem[addr] << 8) | self.mem[addr + 1]
        return self.mem[addr]

    def eval(self, addr: int):
        self.pc = addr
        while self.step():
            ...
        if (ret := self.dev.mem[Dev.SYSTEM_STATE]) != 0:
            exit(ret & 0x7F)

    def step(self) -> bool:
        op = self.mem[self.pc]
        self.pc += 1

        if op == Op.BRK:
            return False

        imm = op in IMM
        if not imm and (op & Mask.RETURN):
            wst, rst = self.rst, self.wst
        else:
            wst, rst = self.wst, self.rst

        wst.modeset(
            keep=bool(not imm and (op & Mask.KEEP)),
            short=bool(not imm and (op & Mask.SHORT)),
        )

        if not imm:
            op &= Mask.CODE

        if f := self.vtable[op]:
            f(wst, rst)
        else:
            raise InvalidInstructionError(f"Invalid instruction: {op:#04x}")

        return True

    # ruff: disable[N802,ARG002]
    def LIT(self, wst: Stack, rst: Stack):
        # ( -- a )
        a = self.memget(self.pc, short=wst.short)
        wst.push(a)
        self.pc += 1 + wst.short

    def JCI(self, wst: Stack, rst: Stack):
        # ( cond8 -- )
        cond8 = wst.pop1()
        if cond8:
            addr16 = self.memget(self.pc, short=True)
            self.pc += 2 + signed2(addr16)
        else:
            self.pc += 2

    def JMI(self, wst: Stack, rst: Stack):
        # ( -- )
        addr16 = self.memget(self.pc, short=True)
        self.pc += 2 + signed2(addr16)

    def JSI(self, wst: Stack, rst: Stack):
        # ( -- )
        rst.push2(self.pc + 2)
        addr16 = self.memget(self.pc, short=True)
        self.pc += 2 + signed2(addr16)

    def INC(self, wst: Stack, rst: Stack):
        # ( a -- a+1 )
        a = wst.pop() + 1
        wst.push(a)

    def POP(self, wst: Stack, rst: Stack):
        # ( a -- )
        wst.pop()

    def NIP(self, wst: Stack, rst: Stack):
        # ( a b -- b )
        b, _ = wst.pop(), wst.pop()
        wst.push(b)

    def SWP(self, wst: Stack, rst: Stack):
        # ( a b -- b a )
        b, a = wst.pop(), wst.pop()
        wst.push(b)
        wst.push(a)

    def ROT(self, wst: Stack, rst: Stack):
        # ( a b c -- b c a )
        c, b, a = wst.pop(), wst.pop(), wst.pop()
        wst.push(b)
        wst.push(c)
        wst.push(a)

    def DUP(self, wst: Stack, rst: Stack):
        # ( a -- a a )
        a = wst.pop()
        wst.push(a)
        wst.push(a)

    def OVR(self, wst: Stack, rst: Stack):
        # ( a b -- a b a )
        b, a = wst.pop(), wst.pop()
        wst.push(a)
        wst.push(b)
        wst.push(a)

    def EQU(self, wst: Stack, rst: Stack):
        # ( a b -- bool8 )
        b, a = wst.pop(), wst.pop()
        wst.push1(a == b)

    def NEQ(self, wst: Stack, rst: Stack):
        # ( a b -- bool8 )
        b, a = wst.pop(), wst.pop()
        wst.push1(a != b)

    def GTH(self, wst: Stack, rst: Stack):
        # ( a b -- bool8 )
        b, a = wst.pop(), wst.pop()
        wst.push1(a > b)

    def LTH(self, wst: Stack, rst: Stack):
        # ( a b -- bool8 )
        b, a = wst.pop(), wst.pop()
        wst.push1(a < b)

    def JMP(self, wst: Stack, rst: Stack):
        # ( addr -- )
        if wst.short:
            self.pc = wst.pop()
        else:
            self.pc += signed(wst.pop())

    def JCN(self, wst: Stack, rst: Stack):
        # ( cond8 addr -- )
        addr = wst.pop()
        cond8 = wst.pop1()
        if cond8:
            if wst.short:
                self.pc = addr
            else:
                self.pc += signed(addr)

    def JSR(self, wst: Stack, rst: Stack):
        # ( addr -- | ret16 )
        ret16 = self.pc
        rst.push2(ret16)
        addr = wst.pop()
        if wst.short:
            self.pc = addr
        else:
            self.pc += signed(addr)

    def STH(self, wst: Stack, rst: Stack):
        # ( a -- | a )
        a = wst.pop()
        rst.push(a, short=wst.short)

    def LDZ(self, wst: Stack, rst: Stack):
        # ( addr8 -- val )
        addr8 = wst.pop1()
        val = self.memget(addr8, short=wst.short)
        wst.push(val)

    def STZ(self, wst: Stack, rst: Stack):
        # ( val addr8 -- )
        addr8 = wst.pop1()
        val = wst.pop()
        self.memset(addr8, val, short=wst.short)

    def LDR(self, wst: Stack, rst: Stack):
        # ( addr8 -- val )
        addr8 = wst.pop1()
        val = self.memget(self.pc + signed(addr8), short=wst.short)
        wst.push(val)

    def STR(self, wst: Stack, rst: Stack):
        # ( val addr8 -- )
        addr8 = wst.pop1()
        val = wst.pop()
        self.memset(self.pc + signed(addr8), val, short=wst.short)

    def LDA(self, wst: Stack, rst: Stack):
        # ( addr16 -- val )
        addr16 = wst.pop2()
        val = self.memget(addr16, short=wst.short)
        wst.push(val)

    def STA(self, wst: Stack, rst: Stack):
        # ( val addr16 -- )
        addr16 = wst.pop2()
        val = wst.pop()
        self.memset(addr16, val, short=wst.short)

    def DEI(self, wst: Stack, rst: Stack):
        # ( dev8 -- val )
        dev8 = wst.pop1()
        val = self.dev.get(dev8, short=wst.short)
        wst.push(val)

    def DEO(self, wst: Stack, rst: Stack):
        # ( val dev8 -- )
        dev8 = wst.pop1()
        val = wst.pop()
        self.dev.set(dev8, val, short=wst.short)

    def ADD(self, wst: Stack, rst: Stack):
        # ( a b -- a+b )
        b, a = wst.pop(), wst.pop()
        wst.push(a + b)

    def SUB(self, wst: Stack, rst: Stack):
        # ( a b -- a-b )
        b, a = wst.pop(), wst.pop()
        wst.push(a - b)

    def MUL(self, wst: Stack, rst: Stack):
        # ( a b -- a*b )
        b, a = wst.pop(), wst.pop()
        wst.push(a * b)

    def DIV(self, wst: Stack, rst: Stack):
        # ( a b -- a//b )
        b, a = wst.pop(), wst.pop()
        wst.push(b and a // b)

    def AND(self, wst: Stack, rst: Stack):
        # ( a b -- a&b )
        b, a = wst.pop(), wst.pop()
        wst.push(a & b)

    def ORA(self, wst: Stack, rst: Stack):
        # ( a b -- a|b )
        b, a = wst.pop(), wst.pop()
        wst.push(a | b)

    def EOR(self, wst: Stack, rst: Stack):
        # ( a b -- ~(a^b) )
        b, a = wst.pop(), wst.pop()
        wst.push(a ^ b)

    def SFT(self, wst: Stack, rst: Stack):
        # ( a shift8 -- c )
        shift8, a = wst.pop(short=False), wst.pop()
        ls, rs = (shift8 >> 4) & 0x0F, shift8 & 0x0F
        c = a >> rs
        c = c << ls
        wst.push(c)

    # ruff: enable[N802,ARG002]
