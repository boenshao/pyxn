from pyxn import UXN, Dev, Op

if __name__ == "__main__":
    uxn = UXN()
    uxn.load(
        bytes(
            [
                Op.LIT, 0x48,  # H
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
                Op.LIT, 0x65,  # e
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
                Op.LIT, 0x6C,  # l
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
                Op.LIT, 0x6C,  # l
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
                Op.LIT, 0x6F,  # o
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
                Op.LIT, 0x21,  # !
                Op.LIT, Dev.CONSOLE_WRITE, Op.DEO,
            ]
        )
    )  # fmt: skip
    while uxn.step():
        pass
