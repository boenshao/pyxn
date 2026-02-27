# ruff: noqa: N802

from pytest_cases import parametrize, parametrize_with_cases

from pyxn import UXN, Mask, Op

CASES = [
# asm                        |r| wst                                 | rst   | pc
"BRK #01                     |*|                                     |       |     ",
"#01 BRK                     |*| 01                                  |       |     ",
# INC
"#01 INC                     |*| 02                                  |       |     ",
"#01 INCk                    |*| 01 02                               |       |     ",
"#0001 INC2                  |*| 00 02                               |       |     ",
"#0001 INCk2                 |*| 00 01 00 02                         |       |     ",
# POP
"#12 #34 POP                 |*| 12                                  |       |     ",
"#12 #34 POPk                |*| 12 34                               |       |     ",
"#1234 #5678 POP2            |*| 12 34                               |       |     ",
"#1234 #5678 POPk2           |*| 12 34 56 78                         |       |     ",
# NIP
"#12 #34 NIP                 |*| 34                                  |       |     ",
"#12 #34 NIPk                |*| 12 34 34                            |       |     ",
"#1234 #5678 NIP2            |*| 56 78                               |       |     ",
"#1234 #5678 NIPk2           |*| 12 34 56 78 56 78                   |       |     ",
# SWP
"#12 #34 SWP                 |*| 34 12                               |       |     ",
"#12 #34 SWPk                |*| 12 34 34 12                         |       |     ",
"#1234 #5678 SWP2            |*| 56 78 12 34                         |       |     ",
"#1234 #5678 SWPk2           |*| 12 34 56 78 56 78 12 34             |       |     ",
# ROT
"#12 #34 #56 ROT             |*| 34 56 12                            |       |     ",
"#12 #34 #56 ROTk            |*| 12 34 56 34 56 12                   |       |     ",
"#1234 #5678 #9abc ROT2      |*| 56 78 9a bc 12 34                   |       |     ",
"#1234 #5678 #9abc ROTk2     |*| 12 34 56 78 9a bc 56 78 9a bc 12 34 |       |     ",
# DUP
"#12 DUP                     |*| 12 12                               |       |     ",
"#12 DUPk                    |*| 12 12 12                            |       |     ",
"#1234 DUP2                  |*| 12 34 12 34                         |       |     ",
"#1234 DUPk2                 |*| 12 34 12 34 12 34                   |       |     ",
# OVR
"#12 #34 OVR                 |*| 12 34 12                            |       |     ",
"#12 #34 OVRk                |*| 12 34 12 34 12                      |       |     ",
"#1234 #5678 OVR2            |*| 12 34 56 78 12 34                   |       |     ",
"#1234 #5678 OVRk2           |*| 12 34 56 78 12 34 56 78 12 34       |       |     ",
# EQU
"#12 #34 EQU                 |*| 00                                  |       |     ",
"#12 #12 EQUk                |*| 12 12 01                            |       |     ",
"#1234 #5678 EQU2            |*| 00                                  |       |     ",
"#1234 #1234 EQUk2           |*| 12 34 12 34 01                      |       |     ",
# NEQ
"#12 #34 NEQ                 |*| 01                                  |       |     ",
"#12 #12 NEQk                |*| 12 12 00                            |       |     ",
"#1234 #5678 NEQ2            |*| 01                                  |       |     ",
"#1234 #1234 NEQk2           |*| 12 34 12 34 00                      |       |     ",
# GTH
"#12 #12 GTH                 |*| 00                                  |       |     ",
"#34 #12 GTH                 |*| 01                                  |       |     ",
"#12 #34 GTHk                |*| 12 34 00                            |       |     ",
"#1234 #1234 GTH2            |*| 00                                  |       |     ",
"#5678 #1234 GTH2            |*| 01                                  |       |     ",
"#1234 #5678 GTHk2           |*| 12 34 56 78 00                      |       |     ",
# LTH
"#12 #12 LTH                 |*| 00                                  |       |     ",
"#34 #12 LTH                 |*| 00                                  |       |     ",
"#12 #34 LTHk                |*| 12 34 01                            |       |     ",
"#1234 #1234 LTH2            |*| 00                                  |       |     ",
"#5678 #1234 LTH2            |*| 00                                  |       |     ",
"#1234 #5678 LTHk2           |*| 12 34 56 78 01                      |       |     ",
# ADD
"#ff #01 ADD                 |*| 00                                  |       |     ",
"#12 #34 ADDk                |*| 12 34 46                            |       |     ",
"#ffff #0001 ADD2            |*| 00 00                               |       |     ",
"#1234 #5678 ADDk2           |*| 12 34 56 78 68 ac                   |       |     ",
# SUB
"#00 #01 SUB                 |*| ff                                  |       |     ",
"#34 #12 SUBk                |*| 34 12 22                            |       |     ",
"#0000 #0001 SUB2            |*| ff ff                               |       |     ",
"#5678 #1234 SUB2k           |*| 56 78 12 34 44 44                   |       |     ",
# MUL
"#02 #03 MUL                 |*| 06                                  |       |     ",
"#ff #03 MULk                |*| ff 03 fd                            |       |     ",
"#0002 #0003 MUL2            |*| 00 06                               |       |     ",
"#ffff #0003 MULk2           |*| ff ff 00 03 ff fd                   |       |     ",
# DIV
"#02 #10 DIV                 |*| 00                                  |       |     ",
"#10 #02 DIV                 |*| 08                                  |       |     ",
"#06 #04 DIVk                |*| 06 04 01                            |       |     ",
"#06 #00 DIVk                |*| 06 00 00                            |       |     ",
"#0002 #0100 DIV2            |*| 00 00                               |       |     ",
"#0100 #0002 DIV2            |*| 00 80                               |       |     ",
"#0100 #0003 DIVk2           |*| 01 00 00 03 00 55                   |       |     ",
"#0100 #0000 DIVk2           |*| 01 00 00 00 00 00                   |       |     ",
# AND
"#00 #ff AND                 |*| 00                                  |       |     ",
"#55 #ff ANDk                |*| 55 ff 55                            |       |     ",
"#0000 #ffff AND2            |*| 00 00                               |       |     ",
"#55aa #aaff AND2k           |*| 55 aa aa ff 00 aa                   |       |     ",
# ORA
"#00 #00 ORA                 |*| 00                                  |       |     ",
"#00 #ff ORAk                |*| 00 ff ff                            |       |     ",
"#0000 #0000 ORA2            |*| 00 00                               |       |     ",
"#ffff #0000 ORAk2           |*| ff ff 00 00 ff ff                   |       |     ",
# EOR
"#00 #ff EOR                 |*| ff                                  |       |     ",
"#ff #f0 EORk                |*| ff f0 0f                            |       |     ",
"#0000 #0000 EOR2            |*| 00 00                               |       |     ",
"#ffff #00ff EORk2           |*| ff ff 00 ff ff 00                   |       |     ",
# SFT right
"#04 #02 SFT                 |*| 01                                  |       |     ",
"#04 #02 SFTk                |*| 04 02 01                            |       |     ",
"#0040 #02 SFT2              |*| 00 10                               |       |     ",
"#0040 #02 SFT2k             |*| 00 40 02 00 10                      |       |     ",
# SFT left
"#04 #20 SFT                 |*| 10                                  |       |     ",
"#04 #20 SFTk                |*| 04 20 10                            |       |     ",
"#0040 #20 SFT2              |*| 01 00                               |       |     ",
"#0040 #20 SFT2k             |*| 00 40 20 01 00                      |       |     ",
# SFT right then left
"#04 #21 SFT                 |*| 08                                  |       |     ",
"#04 #12 SFT                 |*| 02                                  |       |     ",
"#04 #22 SFTk                |*| 04 22 04                            |       |     ",
"#0040 #21 SFT2              |*| 00 80                               |       |     ",
"#0040 #12 SFT2              |*| 00 20                               |       |     ",
"#0040 #22 SFT2              |*| 00 40                               |       |     ",
# JMP forward
"#12 #02 JMP #ff BRK         |*| 12                                  |       | 0108",
"#12 #02 JMPk #ff BRK        |*| 12 02                               |       | 0108",
"#12 #0108 JMP2 #ff BRK      |*| 12                                  |       | 0109",
"#12 #0108 JMPk2 #ff BRK     |*| 12 01 08                            |       | 0109",
# JMP backward
"#00 #fc JMP #ff             |*| 00                                  |       | 0102",
"#00 #fc JMPk #ff            |*| 00 fc                               |       | 0102",
"#00 #0101 JMP2 #ff          |*| 00                                  |       | 0102",
"#00 #0101 JMPk2 #ff         |*| 00 01 01                            |       | 0102",
# JCN forward
"#01 #03 JCN #ff BRK         |*|                                     |       | 0109",
"#01 #03 JCNk #ff BRK        |*| 01 03                               |       | 0109",
"#00 #03 JCN #ff BRK         |*| ff                                  |       | 0108",
"#00 #03 JCNk #ff BRK        |*| 00 03 ff                            |       | 0108",
"#01 #0108 JCN2 #ff BRK      |*|                                     |       | 0109",
"#01 #0108 JCNk2 #ff BRK     |*| 01 01 08                            |       | 0109",
"#00 #0108 JCN2 #ff BRK      |*| ff                                  |       | 0109",
"#00 #0108 JCNk2 #ff BRK     |*| 00 01 08 ff                         |       | 0109",
# JCN backward
"#00 #01 #fa JCN             |*| 00                                  |       | 0102",
"#00 #01 #fa JCNk            |*| 00 01 fa                            |       | 0102",
"#00 #00 #fa JCN BRK         |*| 00                                  |       | 0108",
"#00 #00 #fa JCNk BRK        |*| 00 00 fa                            |       | 0108",
"#00 #01 #0101 JCN2          |*| 00                                  |       | 0102",
"#00 #01 #0101 JCNk2         |*| 00 01 01 01                         |       | 0102",
"#00 #00 #0101 JCN2 BRK      |*| 00                                  |       | 0109",
"#00 #00 #0101 JCNk2 BRK     |*| 00 00 01 01                         |       | 0109",
# JSR forward
"#12 #02 JSR ff ff BRK       |*| 12                                  | 01 05 | 0108",
"#12 #02 JSRk ff ff BRK      |*| 12 02                               | 01 05 | 0108",
"#12 #0107 JSR2 ff BRK       |*| 12                                  | 01 06 | 0108",
"#12 #0107 JSRk2 ff BRK      |*| 12 01 07                            | 01 06 | 0108",
# JSR backward
"#00 #fc JSR                 |*| 00                                  | 01 05 | 0102",
"#00 #fc JSRk                |*| 00 fc                               | 01 05 | 0102",
"#00 #0101 JSR2              |*| 00                                  | 01 06 | 0102",
"#00 #0101 JSRk2             |*| 00 01 01                            | 01 06 | 0102",
# STH
"#12 #34 STH                 |*| 12                                  | 34    |     ",
"#1234 #5678 STH2            |*| 12 34                               | 56 78 |     ",
# JCI
"#01 JCI 00 03 #1234 BRK     | |                                     |       | 0109",
"#00 JCI 00 03 #1234 BRK     | | 12 34                               |       | 0109",
"#00 #01 JCI ff fa #1234     | | 00                                  |       | 0102",
"#00 JCI ff fa #1234 BRK     | | 12 34                               |       | 0109",
# JMI
"#12 JMI 00 03 #abcd BRK     | | 12                                  |       | 0109",
"#00 #12 JMI ff fa #abcd     | | 00 12                               |       | 0102",
# JSI
"#12 JSI 00 03 #abcd BRK     | | 12                                  | 01 05 | 0109",
"#00 #12 JSI ff fa #abcd     | | 00 12                               | 01 07 | 0102",
# STZ LDZ
"#34 LDZ                     |*| 00                                  |       |     ",
"#12 #34 STZ #34 LDZ         |*| 12                                  |       |     ",
"#12 LDZ2                    |*| 00 00                               |       |     ",
"#1234 #56 STZ2 #56 LDZ2     |*| 12 34                               |       |     ",
# STR LDR forward
"#03 LDR BRK ff ff 68        |*| 68                                  |       |     ",
"#31 LDR                     |*| 00                                  |       |     ",
"#12 #34 STR #31 LDR         |*| 12                                  |       |     ",
"#03 LDR2 BRK ff ff 12 34    |*| 12 34                               |       |     ",
"#53 LDR2                    |*| 00 00                               |       |     ",
"#1234 #56 STR2 #53 LDR2     |*| 12 34                               |       |     ",
# STR LDR backward
"#f5 LDR                     |*| 00                                  |       |     ",
"#12 #f8 STR #f5 LDR         |*| 12                                  |       |     ",
"#f5 LDR2                    |*| 00 00                               |       |     ",
"#1234 #f8 STR2 #f5 LDR2     |*| 12 34                               |       |     ",
# LDA STA
"#0108 LDA BRK ff ff ff 68   |*| 68                                  |       |     ",
"#1234 LDA                   |*| 00                                  |       |     ",
"#ab #1234 STA #1234 LDA     |*| ab                                  |       |     ",
"#0107 LDA2 BRK ff ff 12 34  |*| 12 34                               |       |     ",
"#1234 LDA2                  |*| 00 00                               |       |     ",
"#abcd #1234 STA2 #1234 LDA2 |*| ab cd                               |       |     ",
# DEI DEO
"#34 DEI                     |*| 00                                  |       |     ",
"#12 #34 DEO #34 DEI         |*| 12                                  |       |     ",
"#56 DEI2                    |*| 00 00                               |       |     ",
"#1234 #56 DEO2 #56 DEI2     |*| 12 34                               |       |     ",
]  # fmt: skip


def B(*args: int) -> bytes:
    return bytes(args)


def assemble(asm: str, *, ret: bool = False) -> bytes:
    rom = b""
    for token in asm.split():
        match token[0], len(token):
            case _, 2:
                rom += B(int(token, 16))
            case "#", 3:
                rom += B(
                    Op.LIT | (Mask.RETURN if ret else 0),
                    int(token[1:], 16),
                )
            case "#", 5:
                rom += B(
                    Op.LIT | Mask.SHORT | (Mask.RETURN if ret else 0),
                    int(token[1:3], 16),
                    int(token[3:5], 16),
                )
            case _:
                op = Op[token[:3]]
                if "k" in token:
                    op |= Mask.KEEP
                if "2" in token:
                    op |= Mask.SHORT
                if ret and op not in (Op.BRK, Op.JCI, Op.JMI, Op.JSI):
                    op |= Mask.RETURN
                rom += B(op)
    return rom


def gen():
    for case in CASES:
        yield case.replace("*", "0")
        if case.split("|")[1].strip() == "*":
            yield case.replace("*", "1")


@parametrize(case=gen())
def case_stack(case: str) -> tuple[bytes, bytes, bytes, int | None]:
    asm, ret, wst, rst, pc = (s.strip() for s in case.split("|"))
    ret = ret == "1"
    rom = assemble(asm, ret=ret)
    wst = B(*(int(byte, 16) for byte in wst.split()))
    rst = B(*(int(byte, 16) for byte in rst.split()))
    pc = int(pc, 16) if pc else None
    return (rom, rst, wst, pc) if ret else (rom, wst, rst, pc)


@parametrize_with_cases("rom,wst,rst,pc", cases=case_stack)
def test_uxn(rom: bytes, wst: bytes, rst: bytes, pc: int | None) -> None:
    uxn = UXN()
    uxn.load(rom)

    while uxn.step():
        pass

    assert uxn.wst.top == len(wst)
    assert uxn.wst.arr[: uxn.wst.top] == wst
    assert uxn.rst.top == len(rst)
    assert uxn.rst.arr[: uxn.rst.top] == rst
    if pc is not None:
        assert uxn.pc == pc
