import enum
from typing import TextIO

from .varvara import ConsoleType, Dev, Varvara


class StackOverflowError(Exception):
    pass


class StackUnderflowError(Exception):
    pass


class InvalidInstructionError(Exception):
    pass


class Stack:
    def __init__(self, maxsize: int):
        self.size = maxsize
        self.arr = bytearray(self.size)
        self.top = 0
        self.ptr = 0
        self.keep = False
        self.short = False

    def load(self, arr: bytes, *, keep: bool = False, short: bool = False):
        self.arr[: len(arr)] = arr
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
        self.arr[self.top] = x & 0xFF
        self.top += 1

    def pop1(self) -> int:
        if self.ptr == 0:
            raise StackUnderflowError
        self.ptr -= 1
        if not self.keep:
            self.top = self.ptr
        return self.arr[self.ptr]

    def push2(self, x: int):
        if self.top + 1 >= self.size:
            raise StackOverflowError
        self.arr[self.top] = (x >> 8) & 0xFF
        self.arr[self.top + 1] = x & 0xFF
        self.top += 2

    def pop2(self) -> int:
        if self.ptr < 2:
            raise StackUnderflowError
        self.ptr -= 2
        if not self.keep:
            self.top = self.ptr
        return (self.arr[self.ptr] << 8) | self.arr[self.ptr + 1]

    def debug(self) -> str:
        s = "|" if self.top - 8 == 0 else " "
        for i in range(self.top - 8, self.top):
            s += f"{self.arr[i]:02x}" if i >= 0 else "00"
            s += "|" if i == -1 else " "
        s += f"<{self.top:02x}"
        return s

    def __repr__(self) -> str:
        return str([hex(self.arr[i]) for i in range(self.top)])


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


def signed(x: int) -> int:
    return x - 0x100 if x >= 0x80 else x


def signed2(x: int) -> int:
    return x - 0x10000 if x >= 0x8000 else x


class UXN:
    BNKSZIE = 0x10  # 16
    MEMSIZE = 0x10000  # 65536, 64k
    DEVSIZE = 0x100  # 256
    STKSIZE = 0x100  # 256
    PCSTART = 0x100

    def __init__(self):
        self.dev = Varvara(self)
        self.arr = bytearray(self.MEMSIZE * self.BNKSZIE)
        self.mem = memoryview(self.arr)
        self.wst = Stack(self.STKSIZE)
        self.rst = Stack(self.STKSIZE)
        self.pc = self.PCSTART

    def load(self, rom: bytes):
        self.mem[self.PCSTART : self.PCSTART + len(rom)] = rom

    def reset(self, args: list[str] | None = None, stdin: TextIO | None = None):
        args = args or []
        self.dev.set(Dev.CSL_TYPE, len(args) > 2, short=False)
        self.eval(self.PCSTART)
        if self.dev.get(Dev.CSL_VECTOR, short=True):
            self._console_parse_args(args)
        if stdin:
            self._console_read_stdin(stdin)

    def _console_input(self, c: int, t: ConsoleType):
        self.dev.set(Dev.CSL_TYPE, t, short=False)
        self.dev.set(Dev.CSL_READ, c, short=False)
        self.dev.uxn.eval(self.dev.get(Dev.CSL_VECTOR, short=True))

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

    def step(self) -> bool:
        op = self.mem[self.pc]
        self.pc += 1

        if op == Op.BRK:
            return False

        imm = op in (Op.JCI, Op.JMI, Op.JSI)
        if not imm and (op & Mask.RETURN):
            wst = self.rst
            rst = self.wst
        else:
            wst = self.wst
            rst = self.rst

        wst.modeset(
            keep=bool(not imm and (op & Mask.KEEP)),
            short=bool(not imm and (op & Mask.SHORT)),
        )

        if imm:
            match op:
                case Op.JCI:
                    # ( cond8 -- )
                    cond8 = wst.pop1()
                    if cond8:
                        addr16 = self.memget(self.pc, short=True)
                        self.pc += 2 + signed2(addr16)
                    else:
                        self.pc += 2
                case Op.JMI:
                    # ( -- )
                    addr16 = self.memget(self.pc, short=True)
                    self.pc += 2 + signed2(addr16)
                case Op.JSI:
                    # ( -- )
                    rst.push2(self.pc + 2)
                    addr16 = self.memget(self.pc, short=True)
                    self.pc += 2 + signed2(addr16)
            return True

        match op & Mask.CODE:
            case 0x00:  # LIT
                # ( -- a )
                a = self.memget(self.pc, short=wst.short)
                wst.push(a)
                self.pc += 2 if wst.short else 1
            case Op.INC:
                # ( a -- a+1 )
                a = wst.pop() + 1
                wst.push(a)
            case Op.POP:
                # ( a -- )
                wst.pop()
            case Op.NIP:
                # ( a b -- b )
                b, _ = wst.pop(), wst.pop()
                wst.push(b)
            case Op.SWP:
                # ( a b -- b a )
                b, a = wst.pop(), wst.pop()
                wst.push(b)
                wst.push(a)
            case Op.ROT:
                # ( a b c -- b c a )
                c, b, a = wst.pop(), wst.pop(), wst.pop()
                wst.push(b)
                wst.push(c)
                wst.push(a)
            case Op.DUP:
                # ( a -- a a )
                a = wst.pop()
                wst.push(a)
                wst.push(a)
            case Op.OVR:
                # ( a b -- a b a )
                b, a = wst.pop(), wst.pop()
                wst.push(a)
                wst.push(b)
                wst.push(a)
            case Op.EQU:
                # ( a b -- bool8 )
                b, a = wst.pop(), wst.pop()
                wst.push1(a == b)
            case Op.NEQ:
                # ( a b -- bool8 )
                b, a = wst.pop(), wst.pop()
                wst.push1(a != b)
            case Op.GTH:
                # ( a b -- bool8 )
                b, a = wst.pop(), wst.pop()
                wst.push1(a > b)
            case Op.LTH:
                # ( a b -- bool8 )
                b, a = wst.pop(), wst.pop()
                wst.push1(a < b)
            case Op.JMP:
                # ( addr -- )
                if wst.short:
                    self.pc = wst.pop()
                else:
                    self.pc += signed(wst.pop())
            case Op.JCN:
                # ( cond8 addr -- )
                addr = wst.pop()
                cond8 = wst.pop1()
                if cond8:
                    if wst.short:
                        self.pc = addr
                    else:
                        self.pc += signed(addr)
            case Op.JSR:
                # ( addr -- | ret16 )
                ret16 = self.pc
                rst.push2(ret16)
                addr = wst.pop()
                if wst.short:
                    self.pc = addr
                else:
                    self.pc += signed(addr)
            case Op.STH:
                # ( a -- | a )
                a = wst.pop()
                rst.push(a, short=wst.short)
            case Op.LDZ:
                # ( addr8 -- val )
                addr8 = wst.pop1()
                val = self.memget(addr8, short=wst.short)
                wst.push(val)
            case Op.STZ:
                # ( val addr8 -- )
                addr8 = wst.pop1()
                val = wst.pop()
                self.memset(addr8, val, short=wst.short)
            case Op.LDR:
                # ( addr8 -- val )
                addr8 = wst.pop1()
                val = self.memget(self.pc + signed(addr8), short=wst.short)
                wst.push(val)
            case Op.STR:
                # ( val addr8 -- )
                addr8 = wst.pop1()
                val = wst.pop()
                self.memset(self.pc + signed(addr8), val, short=wst.short)
            case Op.LDA:
                # ( addr16 -- val )
                addr16 = wst.pop2()
                val = self.memget(addr16, short=wst.short)
                wst.push(val)
            case Op.STA:
                # ( val addr16 -- )
                addr16 = wst.pop2()
                val = wst.pop()
                self.memset(addr16, val, short=wst.short)
            case Op.DEI:
                # ( dev8 -- val )
                dev8 = wst.pop1()
                val = self.dev.get(dev8, short=wst.short)
                wst.push(val)
            case Op.DEO:
                # ( val dev8 -- )
                dev8 = wst.pop1()
                val = wst.pop()
                self.dev.set(dev8, val, short=wst.short)
            case Op.ADD:
                # ( a b -- a+b )
                b, a = wst.pop(), wst.pop()
                wst.push(a + b)
            case Op.SUB:
                # ( a b -- a-b )
                b, a = wst.pop(), wst.pop()
                wst.push(a - b)
            case Op.MUL:
                # ( a b -- a*b )
                b, a = wst.pop(), wst.pop()
                wst.push(a * b)
            case Op.DIV:
                # ( a b -- a//b )
                b, a = wst.pop(), wst.pop()
                wst.push(a // b if b else 0)
            case Op.AND:
                # ( a b -- a&b )
                b, a = wst.pop(), wst.pop()
                wst.push(a & b)
            case Op.ORA:
                # ( a b -- a|b )
                b, a = wst.pop(), wst.pop()
                wst.push(a | b)
            case Op.EOR:
                # ( a b -- ~(a^b) )
                b, a = wst.pop(), wst.pop()
                wst.push(a ^ b)
            case Op.SFT:
                # ( a shift8 -- c )
                shift8, a = wst.pop(short=False), wst.pop()
                ls, rs = (shift8 >> 4) & 0x0F, shift8 & 0x0F
                c = a >> rs
                c = c << ls
                wst.push(c)
            case _:
                raise InvalidInstructionError(hex(op))

        return True

    def eval(self, addr: int):
        self.pc = addr
        while self.step():
            ...
        if (ret := self.dev.mem[Dev.SYS_STATE]) != 0:
            exit(ret & 0x7F)
