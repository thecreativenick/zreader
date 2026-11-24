import pytest

from zreader import compute_checksum, decode_text, encode_dictionary_word, encode_text, parse_header


def make_story(version=3, body=b""):
    mem = bytearray(64) + bytearray(body)
    mem[0] = version
    mem[0x02:0x04] = (88).to_bytes(2, "big")
    mem[0x12:0x18] = b"261124"
    scale = 2 if version <= 3 else 4 if version <= 5 else 8
    while len(mem) % scale:
        mem.append(0)
    mem[0x1A:0x1C] = (len(mem) // scale).to_bytes(2, "big")
    return mem


def test_header_fields():
    mem = make_story(5, b"\x01\x02\x03")
    mem[0x06:0x08] = (0x1234).to_bytes(2, "big")
    h = parse_header(mem)
    assert (h.version, h.release, h.serial, h.initial_pc) == (5, 88, "261124", 0x1234)
    assert h.file_length == len(mem)
    assert compute_checksum(mem, h) == 6


def test_rejects_bad_version():
    with pytest.raises(ValueError):
        parse_header(bytes(64))


def test_known_encoding_of_hello():
    # h=13 e=10 l=17 | l=17 o=20 pad=5 (with end bit) -- worked out by hand from the spec
    assert encode_text("hello") == bytes.fromhex("3551C685")


@pytest.mark.parametrize("text", [
    "hello", "West of House", "You can't go that way.", "Score: 10/350 (rank: Novice)",
    "line one\nline two", "a@b{c}~", "",
])
def test_roundtrip(text):
    data = encode_text(text)
    decoded, end = decode_text(data, 0)
    assert decoded == text
    assert end == len(data)


def test_abbreviations():
    # Memory layout: [abbrev table: 96 words][strings...]
    mem = bytearray(2 * 96)
    the_addr = len(mem)
    mem += encode_text("the ")
    while len(mem) % 2:
        mem.append(0)
    mem[2 * 0 : 2 * 0 + 2] = (the_addr // 2).to_bytes(2, "big")  # abbreviation 0 = "the "
    text_addr = len(mem)
    # z-chars: [1, 0] = abbreviation 0, then "cat"
    from zreader.story import encode_zchars, pack_zchars
    mem += pack_zchars([1, 0] + encode_zchars("cat"))
    assert decode_text(mem, text_addr, abbrev_table=0)[0] == "the cat"


def test_dictionary_words():
    assert len(encode_dictionary_word("lantern", 3)) == 4
    assert len(encode_dictionary_word("lantern", 5)) == 6
    # v3 truncates to 6 z-chars: "lanter"
    assert encode_dictionary_word("LANTERN", 3) == encode_dictionary_word("lanterx", 3)
