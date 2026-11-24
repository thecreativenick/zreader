"""Story-file header and Z-character text codec (Z-machine Standard 1.1, sections 3 and 11).

Covers versions 3-8. Versions 1 and 2 use different shift rules and are a
later milestone.
"""

from __future__ import annotations

from dataclasses import dataclass

A0 = "abcdefghijklmnopqrstuvwxyz"
A1 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# A2 positions 6 and 7 are special: 6 = 10-bit ZSCII escape, 7 = newline.
A2 = "^\n0123456789.,!?_#'\"/\\-:()"  # A2[0] is a placeholder for the escape slot


@dataclass
class Header:
    version: int
    high_memory: int
    initial_pc: int
    dictionary: int
    object_table: int
    globals: int
    static_memory: int
    abbreviations: int
    file_length: int
    checksum: int
    release: int
    serial: str


def word(mem: bytes | bytearray, addr: int) -> int:
    return (mem[addr] << 8) | mem[addr + 1]


def parse_header(mem: bytes | bytearray) -> Header:
    if len(mem) < 64:
        raise ValueError("story file shorter than the 64-byte header")
    version = mem[0]
    if not 1 <= version <= 8:
        raise ValueError(f"unknown Z-machine version {version}")
    scale = 2 if version <= 3 else 4 if version <= 5 else 8
    return Header(
        version=version,
        release=word(mem, 0x02),
        high_memory=word(mem, 0x04),
        initial_pc=word(mem, 0x06),
        dictionary=word(mem, 0x08),
        object_table=word(mem, 0x0A),
        globals=word(mem, 0x0C),
        static_memory=word(mem, 0x0E),
        serial=bytes(mem[0x12:0x18]).decode("ascii", "replace"),
        abbreviations=word(mem, 0x18),
        file_length=word(mem, 0x1A) * scale,
        checksum=word(mem, 0x1C),
    )


def compute_checksum(mem: bytes | bytearray, header: Header) -> int:
    """Sum of bytes from 0x40 to the stated file length, mod 0x10000 (the 'verify' opcode)."""
    return sum(mem[0x40 : header.file_length]) & 0xFFFF


# --------------------------------------------------------------------- decode
def read_zchars(mem: bytes | bytearray, addr: int) -> tuple[list[int], int]:
    """Read packed 5-bit Z-characters from addr until the end bit. Returns (zchars, next_addr)."""
    out = []
    while True:
        w = word(mem, addr)
        addr += 2
        out += [(w >> 10) & 31, (w >> 5) & 31, w & 31]
        if w & 0x8000:
            return out, addr


def decode_text(mem: bytes | bytearray, addr: int, abbrev_table: int | None = None,
                _in_abbrev: bool = False) -> tuple[str, int]:
    """Decode a Z-string at addr. Returns (text, address just past the string)."""
    zchars, end = read_zchars(mem, addr)
    out: list[str] = []
    alphabet = 0
    i = 0
    while i < len(zchars):
        z = zchars[i]
        if z == 0:
            out.append(" ")
        elif z in (1, 2, 3):
            if i + 1 >= len(zchars):
                break  # incomplete abbreviation at end of string: ignored
            if _in_abbrev or abbrev_table is None:
                raise ValueError("abbreviation used where it is not allowed")
            idx = 32 * (z - 1) + zchars[i + 1]
            target = word(mem, abbrev_table + 2 * idx) * 2
            out.append(decode_text(mem, target, abbrev_table, _in_abbrev=True)[0])
            i += 1
        elif z == 4:
            alphabet = 1
            i += 1
            continue
        elif z == 5:
            alphabet = 2
            i += 1
            continue
        elif alphabet == 2 and z == 6:
            if i + 2 >= len(zchars):
                break
            out.append(zscii_to_unicode((zchars[i + 1] << 5) | zchars[i + 2]))
            i += 2
        else:
            out.append((A0, A1, A2)[alphabet][z - 6])
        alphabet = 0
        i += 1
    return "".join(out), end


def zscii_to_unicode(code: int) -> str:
    if code == 13:
        return "\n"
    if 32 <= code <= 126:
        return chr(code)
    return "?"  # Unicode translation table (155-251) is a later milestone


# --------------------------------------------------------------------- encode
def encode_zchars(text: str) -> list[int]:
    out: list[int] = []
    for ch in text:
        if ch == " ":
            out.append(0)
        elif ch in A0:
            out.append(A0.index(ch) + 6)
        elif ch in A1:
            out += [4, A1.index(ch) + 6]
        elif ch in A2[1:]:
            out += [5, A2.index(ch) + 6]
        else:
            code = ord(ch)
            if not 32 <= code <= 126:
                raise ValueError(f"cannot encode {ch!r}")
            out += [5, 6, code >> 5, code & 31]
    return out


def pack_zchars(zchars: list[int], min_words: int = 1) -> bytes:
    zchars = list(zchars)
    while len(zchars) % 3 or len(zchars) < 3 * min_words:
        zchars.append(5)  # pad with shift characters
    words = []
    for i in range(0, len(zchars), 3):
        words.append((zchars[i] << 10) | (zchars[i + 1] << 5) | zchars[i + 2])
    words[-1] |= 0x8000
    return b"".join(w.to_bytes(2, "big") for w in words)


def encode_text(text: str) -> bytes:
    return pack_zchars(encode_zchars(text))


def encode_dictionary_word(text: str, version: int) -> bytes:
    """Dictionary form: lowercase, truncated/padded to 6 (v3) or 9 (v4+) Z-characters."""
    n = 6 if version <= 3 else 9
    zchars = encode_zchars(text.lower())[:n]
    zchars += [5] * (n - len(zchars))
    return pack_zchars(zchars)
