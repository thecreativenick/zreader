# zreader

A Z-machine interpreter (Infocom-format interactive fiction, versions 3–8) with a browser
reader: styled text, undo, save/restore and transcripts.

## Status

Early scaffold. Done so far:

- Story-file header parser (version, memory map, file length scaling, checksum for `verify`).
- Z-character text decoder: the three alphabets, shifts, 10-bit ZSCII escapes and
  abbreviations (spec sections 3.2–3.5).
- Text encoder and dictionary-word encoding (6 z-chars for v3, 9 for v4+), checked against a
  hand-worked example from the spec and by round-trips.

## Planned milestones

1. Instruction decoder: all operand forms (long, short, variable, extended) and the
   store/branch/text suffixes.
2. Core opcodes, the call stack, local and global variables. Enough to run czech.
3. The object table (attributes, properties, tree operations) and the tokenizer / `read`.
4. Screen model: upper/lower windows, styles, colours; v5+ extensions. Run praxix.
5. Quetzal save/restore, multi-level undo, transcripts.
6. Localhost reader page over WebSocket. Glulx is a stretch goal.

## Success bar

The test stories czech and praxix (and later glulxercise) report every test passing, and a
Playwright script plays through a game's opening and save/restore with the expected transcript.

## Development

```bash
pip install -e .[dev]
pytest
```
