#!/usr/bin/env python3
"""Encode/decode Exient XOX2 tokenised XML containers.

This tool targets the XOX2 layout documented by the reverse-engineered
abgtool implementation. It never edits PAK files in place.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree

# XOX2 token alphabet reconstructed from Exient's 2.9.x reader.
TOKENS_V2 = bytes.fromhex(
    "78 65 D3 E2 6E F3 DA C5 76 D2 59 C3 52 48 6B 58 FC E8 F2 72 "
    "62 63 61 D1 ED FB 4B EA 44 6A 42 49 43 4E E0 EF 3A 41 6C 46 "
    "E1 4C C2 CC 64 F8 66 CE F9 5A 56 77 D8 4F F0 DE CA 57 DD DF "
    "53 FA 4A E9 DC 51 E7 73 68 7A 71 D4 74 FD EE C8 F1 F4 F6 C9 "
    "C4 C6 D6 D9 CF E3 70 75 DB FE F5 C7 EB D5 79 CB 47 CD EC 50 "
    "C1 6F 69 E6 54 45 FF E5 6D 55 C0 67 4D E4 D0"
)


def xox2_alphabet() -> bytes:
    """Return the real digit alphabet (0x78 is placed at digit 39)."""
    result = bytearray(115)
    out = 0
    for i, value in enumerate(TOKENS_V2):
        if i == 0:
            continue
        if out == 39:
            result[out] = TOKENS_V2[0]
            out += 1
        result[out] = value
        out += 1
    if out != 115:
        raise AssertionError(f"bad alphabet length: {out}")
    return bytes(result)


ALPHABET = xox2_alphabet()
DIGIT = {value: index for index, value in enumerate(ALPHABET)}
if len(DIGIT) != 115:
    raise RuntimeError("XOX2 alphabet contains duplicate bytes")


class XOX2Error(ValueError):
    pass


def _token_bytes(index: int) -> bytes:
    if index < 0:
        raise XOX2Error("negative token index")
    digits = [0] if index == 0 else []
    while index:
        digits.append(index % 115)
        index //= 115
    digits.reverse()
    return bytes(ALPHABET[d] for d in digits)


def _scan_tag(source: str, start: int, intern) -> tuple[bytes, int, str | None, bool]:
    """Tokenise one ordinary XML start/end tag; return bytes, end, name, closing."""
    quote = None
    end = start + 1
    while end < len(source):
        ch = source[end]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ">":
            break
        end += 1
    if end >= len(source):
        raise XOX2Error(f"unterminated XML tag at character {start}")

    body = source[start + 1:end]
    closing = body.startswith("/")
    pos = 1 if closing else 0
    name_start = pos
    while pos < len(body) and not body[pos].isspace() and body[pos] not in "/>":
        pos += 1
    if pos == name_start:
        raise XOX2Error(f"missing element name at character {start}")
    name = body[name_start:pos]
    out = bytearray(b"</" if closing else b"<")
    out.extend(_token_bytes(intern(name)))
    if closing:
        out.extend(body[pos:].encode("utf-8"))
        out.extend(b">")
        return bytes(out), end + 1, name, True

    # Preserve whitespace, separators and quote style exactly. Names and
    # quoted values become table tokens; '/' and '>' remain structural.
    while pos < len(body):
        if body[pos].isspace():
            ws = pos
            while pos < len(body) and body[pos].isspace():
                pos += 1
            out.extend(body[ws:pos].encode("utf-8"))
            continue
        if body[pos] == "/":
            out.extend(b"/")
            pos += 1
            continue
        attr_start = pos
        while pos < len(body) and not body[pos].isspace() and body[pos] not in "=/":
            pos += 1
        if pos == attr_start:
            out.extend(body[pos].encode("utf-8"))
            pos += 1
            continue
        attr_name = body[attr_start:pos]
        out.extend(_token_bytes(intern(attr_name)))
        while pos < len(body) and body[pos].isspace():
            out.extend(body[pos].encode("utf-8"))
            pos += 1
        if pos < len(body) and body[pos] == "=":
            out.extend(b"=")
            pos += 1
            while pos < len(body) and body[pos].isspace():
                out.extend(body[pos].encode("utf-8"))
                pos += 1
            if pos >= len(body) or body[pos] not in "\"'":
                raise XOX2Error(f"unquoted attribute value for {attr_name!r}")
            q = body[pos]
            out.extend(q.encode("ascii"))
            pos += 1
            value_start = pos
            while pos < len(body) and body[pos] != q:
                pos += 1
            if pos >= len(body):
                raise XOX2Error(f"unterminated value for attribute {attr_name!r}")
            out.extend(_token_bytes(intern(body[value_start:pos])))
            out.extend(q.encode("ascii"))
            pos += 1
    out.extend(b">")
    return bytes(out), end + 1, name, False


def encode(xml: str) -> bytes:
    """Encode XML text as an XOX2 container."""
    if not isinstance(xml, str) or not xml:
        raise XOX2Error("input XML is empty")
    strings: list[str] = []
    indices: dict[str, int] = {}

    def intern(value: str) -> int:
        if value not in indices:
            indices[value] = len(strings)
            strings.append(value)
        return indices[value]

    document = bytearray()
    # The native reader expects the entire document inside a literal <x> wrapper.
    document.extend(b"<" + bytes([ALPHABET[39]]) + b">")
    pos = 0
    while pos < len(xml):
        if xml[pos] != "<":
            end = xml.find("<", pos)
            if end < 0:
                end = len(xml)
            document.extend(_token_bytes(intern(xml[pos:end])))
            pos = end
            continue

        # Comments, declarations, CDATA and processing instructions are stored
        # as a single token so their punctuation and alphabet characters survive.
        if xml.startswith("<!--", pos):
            end = xml.find("-->", pos + 4)
            if end < 0:
                raise XOX2Error("unterminated XML comment")
            end += 3
            document.extend(_token_bytes(intern(xml[pos:end])))
            pos = end
            continue
        if xml.startswith("<![CDATA[", pos):
            end = xml.find("]]>", pos + 9)
            if end < 0:
                raise XOX2Error("unterminated CDATA section")
            end += 3
            document.extend(_token_bytes(intern(xml[pos:end])))
            pos = end
            continue
        if xml.startswith("<?", pos):
            end = xml.find("?>", pos + 2)
            if end < 0:
                raise XOX2Error("unterminated processing instruction")
            end += 2
            document.extend(_token_bytes(intern(xml[pos:end])))
            pos = end
            continue
        if xml.startswith("<!", pos):
            # DOCTYPE may contain an internal subset; track quotes and brackets.
            end = pos + 2
            quote = None
            depth = 0
            while end < len(xml):
                ch = xml[end]
                if quote:
                    if ch == quote:
                        quote = None
                elif ch in "\"'":
                    quote = ch
                elif ch == "[":
                    depth += 1
                elif ch == "]":
                    depth = max(0, depth - 1)
                elif ch == ">" and depth == 0:
                    break
                end += 1
            if end >= len(xml):
                raise XOX2Error("unterminated declaration")
            end += 1
            document.extend(_token_bytes(intern(xml[pos:end])))
            pos = end
            continue

        encoded, pos, _name, _closing = _scan_tag(xml, pos, intern)
        document.extend(encoded)

    # Close the wrapper. The reader resolves this closing token from its stack.
    document.extend(b"</" + bytes([ALPHABET[39]]) + b">")
    document.append(0)

    table = bytearray()
    offsets = [0]
    for value in strings:
        raw = value.encode("utf-8")
        if b"\0" in raw:
            raise XOX2Error("XML strings cannot contain NUL bytes")
        table.extend(raw)
        table.append(0)
        offsets.append(len(table))

    if len(strings) > 0xFFFFFFFF or len(table) > 0xFFFFFFFF:
        raise XOX2Error("XOX2 table exceeds 32-bit format limits")
    header = bytearray(b"XOX2")
    header.extend(struct.pack("<I", len(strings)))
    for offset in offsets:
        header.extend(struct.pack("<I", offset))
    return bytes(header + table + document)


def decode(data: bytes) -> str:
    """Small independent decoder used for round-trip validation."""
    if len(data) < 12 or data[:4] != b"XOX2":
        raise XOX2Error("not an XOX2 file")
    count = struct.unpack_from("<I", data, 4)[0]
    table_at = 8 + 4 * (count + 1)
    if table_at > len(data):
        raise XOX2Error("truncated offset table")
    offsets = struct.unpack_from("<" + "I" * (count + 1), data, 8)
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        raise XOX2Error("invalid string offsets")
    if table_at + offsets[-1] > len(data):
        raise XOX2Error("string table extends beyond file")
    strings = []
    for i in range(count):
        raw = data[table_at + offsets[i]:table_at + offsets[i + 1]]
        if not raw.endswith(b"\0"):
            raise XOX2Error(f"string #{i} is not NUL-terminated")
        strings.append(raw[:-1].decode("utf-8"))
    document = data[table_at + offsets[-1]:]
    used = [False] * count
    stack: list[str] = []
    out: list[str] = []
    run: int | None = None
    closing = False
    first = True

    def flush() -> None:
        nonlocal run, first
        if run is None:
            return
        value = run
        run = None
        if first:
            first = False
            token = "XOX2ROOT"
        elif closing:
            if not stack:
                raise XOX2Error("closing tag without open element")
            token = stack[-1]
        else:
            if value >= count:
                raise XOX2Error(f"token #{value} exceeds table size {count}")
            used[value] = True
            token = strings[value]
        if out and out[-1] == "<":
            stack.append(token)
        out.append(token)

    for byte in document:
        if byte == 0:
            break
        digit = DIGIT.get(byte)
        if digit is not None:
            run = digit if run is None else run * 115 + digit
            continue
        flush()
        if byte == ord("/") and out and out[-1] == "<":
            closing = True
        elif byte == ord(">") and out and out[-1] == "/" and not closing:
            if stack:
                stack.pop()
        elif byte == ord(">") and closing:
            if stack:
                stack.pop()
            closing = False
        out.append(chr(byte))
    flush()
    if any(not value for value in used):
        missing = [i for i, value in enumerate(used) if not value]
        raise XOX2Error(f"unused strings in generated table: {missing[:8]}")
    decoded = "".join(out)
    if not decoded.startswith("<XOX2ROOT>") or not decoded.endswith("</XOX2ROOT>"):
        raise XOX2Error("missing native XOX2 wrapper")
    return decoded[len("<XOX2ROOT>"):-len("</XOX2ROOT>")]


def self_test() -> None:
    samples = [
        '<Root a="one" b="two"><Child enabled="true"/>text &amp; more</Root>',
        '<?xml version="1.0" encoding="UTF-8"?>\n<Settings><Button id="Rate" title="Calificar juego"/></Settings>',
        '<A><B value="áéíóú 日本語"/><B value="áéíóú 日本語"/></A>',
        '<!-- keep comment --><Root note="a > b"><![CDATA[raw <data> & text]]></Root>',
    ]
    for sample in samples:
        packed = encode(sample)
        decoded = decode(packed)
        if decoded != sample:
            raise AssertionError(f"round-trip mismatch:\n{sample!r}\n{decoded!r}")
        ElementTree.fromstring(decoded)
    print(f"OK: {len(samples)} XOX2 round-trip samples; alphabet={len(ALPHABET)} unique bytes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="plain XML input file")
    parser.add_argument("output", nargs="?", help="XOX2 output file")
    parser.add_argument("--self-test", action="store_true", help="run local round-trip tests")
    parser.add_argument("--decode", action="store_true", help="decode an XOX2 input instead of encoding")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.input or not args.output:
        parser.error("input and output paths are required")
    source = Path(args.input)
    target = Path(args.output)
    raw = source.read_bytes()
    if args.decode:
        result = decode(raw).encode("utf-8")
    else:
        text = raw.decode("utf-8-sig")
        result = encode(text)
        # Refuse to write unless our own decoder can read the result and the
        # decoded XML is well-formed. This is a codec check, not game validation.
        round_trip = decode(result)
        ElementTree.fromstring(round_trip)
        if round_trip != text:
            raise XOX2Error("round-trip text mismatch; output was not written")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result)
    print(f"{'Decoded' if args.decode else 'Encoded'} {source} -> {target} ({len(result)} bytes)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, XOX2Error, ElementTree.ParseError) as exc:
        print(f"xox2: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
