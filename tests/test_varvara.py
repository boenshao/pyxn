import time
from typing import TYPE_CHECKING

from pyxn.uxn import UXN
from pyxn.varvara import Dev, stat

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def write_c_string(uxn: UXN, addr: int, s: str):
    data = s.encode() + b"\x00"
    uxn.mem[addr : addr + len(data)] = data


def write_bytes(uxn: UXN, addr: int, data: bytes):
    uxn.mem[addr : addr + len(data)] = data


def test_system_device_wst_and_rst_ports():
    uxn = UXN()
    uxn.wst.top = 0x12
    uxn.rst.top = 0x34

    assert uxn.dev.get(Dev.SYSTEM_WST, short=False) == 0x12
    assert uxn.dev.get(Dev.SYSTEM_RST, short=False) == 0x34

    uxn.dev.set(Dev.SYSTEM_WST, 0x56, short=False)
    uxn.dev.set(Dev.SYSTEM_RST, 0x78, short=False)

    assert uxn.wst.top == 0x56
    assert uxn.rst.top == 0x78


def test_system_device_debug_port(capsys: pytest.CaptureFixture[str]):
    uxn = UXN()

    uxn.wst.load(bytes([0x12, 0x34, 0x56]))
    uxn.rst.load(bytes([0xAB, 0xCD]))

    uxn.dev.set(Dev.SYSTEM_DEBUG, 0x00, short=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""

    expected = f"WST{uxn.wst.debug()}\nRST{uxn.rst.debug()}\n"
    uxn.dev.set(Dev.SYSTEM_DEBUG, 0x01, short=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == expected


def test_system_device_expansion_ports():
    uxn = UXN()

    cmd_addr = 0x0200
    bank = 12
    base = bank * uxn.MEMSIZE + 0x0300
    initial = b"......[hello]....."
    write_bytes(uxn, base, initial)

    # cpyl copies from the first byte, so overlapping copies smear forward.
    write_bytes(
        uxn,
        cmd_addr,
        # cpyl - 0x01 length* src bank* src addr* dst bank* dst addr*
        bytes([0x01, 0x00, 0x07, 0x00, bank, 0x03, 0x06, 0x00, bank, 0x03, 0x03]),
    )
    uxn.dev.set(Dev.SYSTEM_EXPANSION, cmd_addr, short=True)
    assert bytes(uxn.mem[base : base + len(initial)]) == b"...[hello]lo]....."

    # cpyr copies from the last byte, so overlapping writes to a higher
    # destination address keep the later source bytes intact
    write_bytes(
        uxn,
        cmd_addr,
        # cpyl - 0x02 length* src bank* src addr* dst bank* dst addr*
        bytes([0x02, 0x00, 0x07, 0x00, bank, 0x03, 0x03, 0x00, bank, 0x03, 0x09]),
    )
    uxn.dev.set(Dev.SYSTEM_EXPANSION, cmd_addr, short=True)
    assert bytes(uxn.mem[base : base + len(initial)]) == b"...[hello[hello].."

    # cpyl again
    write_bytes(
        uxn,
        cmd_addr,
        # cpyl - 0x01 length* src bank* src addr* dst bank* dst addr*
        bytes([0x01, 0x00, 0x07, 0x00, bank, 0x03, 0x09, 0x00, bank, 0x03, 0x06]),
    )
    uxn.dev.set(Dev.SYSTEM_EXPANSION, cmd_addr, short=True)
    assert bytes(uxn.mem[base : base + len(initial)]) == b"...[he[hello]lo].."

    # fill 13 bytes at bank 1, 0x0303 with "-"
    write_bytes(
        uxn,
        cmd_addr,
        # fill - 0x00 length* bank* addr* value
        bytes([0x00, 0x00, 0x0D, 0x00, bank, 0x03, 0x03, ord("-")]),
    )
    uxn.dev.set(Dev.SYSTEM_EXPANSION, cmd_addr, short=True)
    assert bytes(uxn.mem[base : base + len(initial)]) == b"...-------------.."


def test_console_device_write_and_error_ports(capsys: pytest.CaptureFixture[str]):
    uxn = UXN()

    uxn.dev.set(Dev.CONSOLE_WRITE, ord("A"), short=False)
    uxn.dev.set(Dev.CONSOLE_ERROR, ord("B"), short=False)

    captured = capsys.readouterr()
    assert captured.out == "A"
    assert captured.err == "B"


def test_stat_formats(tmp_path: Path):
    small = tmp_path / "small.txt"
    small.write_bytes(b"hey")

    large = tmp_path / "large.bin"
    large.write_bytes(b"\x00" * 0x10000)

    folder = tmp_path / "folder"
    folder.mkdir()

    assert stat(small) == "0003"
    assert stat(large) == "????"
    assert stat(folder) == "----"
    assert stat(tmp_path / "missing") == "!!!!"


def test_file_device_read_and_write_ports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    uxn = UXN()

    name_addr = 0x0200
    write_addr = 0x0300
    read_addr = 0x0400

    write_c_string(uxn, name_addr, "hello.txt")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)

    # plain write
    write_bytes(uxn, write_addr, b"hello")
    uxn.dev.set(Dev.FILE_LENGTH, 5, short=True)
    uxn.dev.set(Dev.FILE_WRITE, write_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 5
    # reopen to reset the file handle and flush the buffer
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    assert (tmp_path / "hello.txt").read_bytes() == b"hello"

    # append
    uxn.dev.set(Dev.FILE_APPEND, 1, short=False)
    write_bytes(uxn, write_addr, b" world")
    uxn.dev.set(Dev.FILE_LENGTH, 6, short=True)
    uxn.dev.set(Dev.FILE_WRITE, write_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 6
    # reopen to reset the file handle and flush the buffer
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    assert (tmp_path / "hello.txt").read_bytes() == b"hello world"

    # reopen for reading
    write_c_string(uxn, name_addr, "hello.txt")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_LENGTH, 5, short=True)
    uxn.dev.set(Dev.FILE_READ, read_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 5
    assert bytes(uxn.mem[read_addr : read_addr + 5]) == b"hello"

    # consecutive reads continue from the previous cursor position
    uxn.dev.set(Dev.FILE_READ, read_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 5
    assert bytes(uxn.mem[read_addr : read_addr + 5]) == b" worl"

    # the read should not go out of bound
    uxn.dev.set(Dev.FILE_READ, read_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 1
    assert bytes(uxn.mem[read_addr : read_addr + 1]) == b"d"

    # reject paths outside cwd
    outside = tmp_path.parent / "outside.txt"
    outside.write_bytes(b"blocked")
    write_c_string(uxn, name_addr, str(outside))
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_LENGTH, 7, short=True)
    uxn.dev.set(Dev.FILE_READ, read_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 0


def test_file_device_stat_and_delete_ports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    uxn = UXN()

    name_addr = 0x0200
    buf_addr = 0x0300
    (tmp_path / "note.txt").write_bytes(b"hey")
    (tmp_path / "subdir").mkdir()

    # file stat returns file size, left padded with zeros as needed
    write_c_string(uxn, name_addr, "note.txt")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_LENGTH, 6, short=True)
    uxn.dev.set(Dev.FILE_STAT, buf_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 6
    assert bytes(uxn.mem[buf_addr : buf_addr + 6]) == b"000003"

    # directory stat is dashes
    write_c_string(uxn, name_addr, "subdir")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_LENGTH, 6, short=True)
    uxn.dev.set(Dev.FILE_STAT, buf_addr, short=True)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 6
    assert bytes(uxn.mem[buf_addr : buf_addr + 6]) == b"------"

    # directory read yields a list of stats
    write_c_string(uxn, name_addr, ".")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_LENGTH, 0x40, short=True)
    uxn.dev.set(Dev.FILE_READ, buf_addr, short=True)
    listing = bytes(
        uxn.mem[buf_addr : buf_addr + uxn.dev.get(Dev.FILE_SUCCESS, short=True)]
    )
    assert b"0003 note.txt\n" in listing
    assert b"---- subdir/\n" in listing

    # deleting reports success with 0x0001
    write_c_string(uxn, name_addr, "note.txt")
    uxn.dev.set(Dev.FILE_NAME, name_addr, short=True)
    uxn.dev.set(Dev.FILE_DELETE, 1, short=False)
    assert uxn.dev.get(Dev.FILE_SUCCESS, short=True) == 0x0001
    assert not (tmp_path / "note.txt").exists()


def test_datetime_device(monkeypatch: pytest.MonkeyPatch):
    # note that Python's struct_time is different from C's struct_time
    fake_now = time.struct_time((2026, 3, 21, 4, 5, 6, 5, 80, 1))
    monkeypatch.setattr("pyxn.varvara.t", lambda: fake_now)

    uxn = UXN()

    # day starts from 1, dotw begins on sunday
    assert uxn.dev.get(Dev.DATETIME_YEAR_H, short=True) == 2026
    assert uxn.dev.get(Dev.DATETIME_MONTH, short=False) == 2
    assert uxn.dev.get(Dev.DATETIME_DAY, short=False) == 21
    assert uxn.dev.get(Dev.DATETIME_HOUR, short=False) == 4
    assert uxn.dev.get(Dev.DATETIME_MINIUTE, short=False) == 5
    assert uxn.dev.get(Dev.DATETIME_SECOND, short=False) == 6
    assert uxn.dev.get(Dev.DATETIME_DOTW, short=False) == 6
    assert uxn.dev.get(Dev.DATETIME_DOTY_H, short=True) == 79
    assert uxn.dev.get(Dev.DATETIME_ISDST, short=False) == 1
