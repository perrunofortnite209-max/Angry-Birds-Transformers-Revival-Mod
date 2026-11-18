#!/usr/bin/env python3
"""Conservative reader/rebuilder for Exient XGS 2.9.x KPX v2 archives.

Only supports the 0x34-header v2 layout used by the pinned abgtool parser.
It preserves the original header, record order, name table, inter-entry gaps,
and trailing bytes. It refuses ambiguous/overlapping layouts.
"""
from __future__ import annotations
import argparse, hashlib, struct, sys, zlib
from dataclasses import dataclass
from pathlib import Path

HEADER = 0x34
RECORD = 32

class PakError(ValueError):
    pass

@dataclass
class Entry:
    record_index: int
    name: str
    size: int
    offset: int
    compressed: bool
    mtime: int
    packed_size: int

def u32(b: bytes, at: int) -> int:
    if at < 0 or at + 4 > len(b):
        raise PakError(f"read outside archive at 0x{at:x}")
    return struct.unpack_from("<I", b, at)[0]

def put32(b: bytearray, at: int, value: int) -> None:
    if not 0 <= value <= 0xffffffff:
        raise PakError(f"value outside u32 range: {value}")
    struct.pack_into("<I", b, at, value)

def cstr(b: bytes, at: int) -> str:
    if at < 0 or at >= len(b):
        raise PakError("name offset outside archive")
    end = b.find(b"\\0", at)
    if end < 0:
        raise PakError("unterminated name")
    return b[at:end].decode("utf-8")

def parse(blob: bytes):
    if len(blob) < HEADER or blob[:4] != b"\\x02KPX":
        raise PakError("not an Exient KPX v2 archive")
    compression = u32(blob, 0x10)
    if compression not in (0, 1, 2):
        raise PakError(f"unsupported archive compression scheme {compression}")
    names_size = u32(blob, 0x0c)
    data_start = None
    for i in range(4096):
        at = HEADER + RECORD * i + 12
        if at + 4 > len(blob):
            break
        off = u32(blob, at)
        if off:
            data_start = off
            break
    if data_start is None:
        raise PakError("no file payload offsets found")
    padded_names = (names_size + 3) & ~3
    names_start = data_start - padded_names
    if names_start < HEADER or (names_start - HEADER) % RECORD:
        raise PakError("record table does not end on a 32-byte boundary")
    record_count = (names_start - HEADER) // RECORD
    if names_start + names_size > len(blob):
        raise PakError("name table exceeds archive")
    raw_records = [blob[HEADER+i*RECORD:HEADER+(i+1)*RECORD] for i in range(record_count)]
    dirs, files = [], []
    for i, rec in enumerate(raw_records):
        name = cstr(blob, names_start + struct.unpack_from("<I", rec, 0)[0])
        size, offset, flag, mtime, csize = struct.unpack_from("<IIIII", rec, 8)
        if offset == 0:
            dirs.append((name, csize))
        else:
            files.append(Entry(i, name, size, offset, flag == 1, mtime, csize if flag == 1 else size))
    root_count = len(files) - sum(count for _, count in dirs)
    if root_count < 0:
        raise PakError("directory file counts exceed total files")
    ordered, cursor = [], 0
    for e in files[:root_count]:
        ordered.append(e)
    cursor = root_count
    for dirname, count in dirs:
        if cursor + count > len(files):
            raise PakError("directory table exceeds file table")
        for e in files[cursor:cursor+count]:
            e.name = dirname.rstrip("/") + "/" + e.name.lstrip("/")
            ordered.append(e)
        cursor += count
    if cursor != len(files):
        raise PakError("directory table does not cover all file records")
    ranges = []
    for e in ordered:
        end = e.offset + e.packed_size
        if e.offset < data_start or end > len(blob):
            raise PakError(f"payload bounds invalid for {e.name}")
        ranges.append((e.offset, end, e))
    ranges.sort(key=lambda x: x[0])
    previous = data_start
    for start, end, e in ranges:
        if start < previous:
            raise PakError(f"overlapping payload for {e.name}")
        previous = end
    return {
        "compression": compression, "data_start": data_start,
        "names_start": names_start, "names_size": names_size,
        "records": raw_records, "entries": ordered, "ranges": ranges,
    }

def unpack_entry(blob: bytes, meta, entry: Entry) -> bytes:
    raw = blob[entry.offset:entry.offset+entry.packed_size]
    if not entry.compressed:
        data = raw
    elif meta["compression"] == 1:
        data = zlib.decompress(raw)
    elif meta["compression"] == 2:
        try:
            import lz4.block
        except ImportError as exc:
            raise PakError("LZ4 archive needs python package lz4") from exc
        data = lz4.block.decompress(raw, uncompressed_size=entry.size)
    else:
        raise PakError(f"compressed entry in raw archive: {entry.name}")
    if len(data) != entry.size:
        raise PakError(f"{entry.name}: unpacked {len(data)} != expected {entry.size}")
    return data

def pack_entry(data: bytes, compression: int, compressed: bool) -> bytes:
    if not compressed:
        return data
    if compression == 1:
        return zlib.compress(data, 9)
    if compression == 2:
        try:
            import lz4.block
        except ImportError as exc:
            raise PakError("LZ4 archive needs python package lz4") from exc
        return lz4.block.compress(data, store_size=False)
    raise PakError("cannot compress an entry with archive compression=0")

def rebuild(blob: bytes, meta, replacement_name: str | None = None, replacement: bytes | None = None) -> bytes:
    entries = meta["entries"]
    targets = [e for e in entries if e.name == replacement_name] if replacement_name else []
    if replacement_name and len(targets) != 1:
        raise PakError(f"expected one entry named {replacement_name!r}; found {len(targets)}")
    target = targets[0] if targets else None
    packed = {}
    for e in entries:
        if e is target:
            packed[e.record_index] = pack_entry(replacement or b"", meta["compression"], e.compressed)
        else:
            packed[e.record_index] = blob[e.offset:e.offset+e.packed_size]
    out = bytearray(blob[:meta["data_start"]])
    cursor = meta["data_start"]
    updated_records = bytearray(out)
    for start, end, e in meta["ranges"]:
        gap = blob[cursor:start]
        out.extend(gap)
        cursor += len(gap)
        new_payload = packed[e.record_index]
        new_offset = len(out)
        out.extend(new_payload)
        rec_at = HEADER + e.record_index * RECORD
        put32(out, rec_at + 12, new_offset)
        if e is target:
            put32(out, rec_at + 8, len(replacement or b""))
            if e.compressed:
                put32(out, rec_at + 24, len(new_payload))
        cursor = end
    out.extend(blob[cursor:])
    return bytes(out)

def verify(blob: bytes, rebuilt: bytes, meta, target_name=None, replacement=None):
    newmeta = parse(rebuilt)
    if len(meta["entries"]) != len(newmeta["entries"]):
        raise PakError("entry count changed after rebuild")
    old_by_record = {e.record_index:e for e in meta["entries"]}
    new_by_record = {e.record_index:e for e in newmeta["entries"]}
    for idx, old in old_by_record.items():
        new = new_by_record[idx]
        if old.name != new.name:
            raise PakError(f"entry name changed at record {idx}")
        expected = replacement if old.name == target_name else unpack_entry(blob, meta, old)
        actual = unpack_entry(rebuilt, newmeta, new)
        if actual != expected:
            raise PakError(f"payload mismatch after rebuild: {old.name}")
    return True

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("roundtrip"); p.add_argument("pak"); p.add_argument("output")
    p = sub.add_parser("replace"); p.add_argument("pak"); p.add_argument("entry"); p.add_argument("replacement"); p.add_argument("output")
    p = sub.add_parser("list"); p.add_argument("pak")
    args = ap.parse_args()
    source = Path(args.pak).read_bytes()
    meta = parse(source)
    if args.cmd == "list":
        print(f"KPX v2 compression={meta['compression']} entries={len(meta['entries'])} data_start=0x{meta['data_start']:x}")
        for e in meta["entries"]:
            print(f"{e.size:>9} {e.packed_size:>9}  {e.name}")
        return
    target_name = None; replacement = None
    if args.cmd == "replace":
        target_name = args.entry
        replacement = Path(args.replacement).read_bytes()
    result = rebuild(source, meta, target_name, replacement)
    verify(source, result, meta, target_name, replacement)
    Path(args.output).write_bytes(result)
    if args.cmd == "roundtrip" and result != source:
        raise PakError("no-op rebuild was not byte-identical")
    print(f"OK: {args.cmd}; entries={len(meta['entries'])}; input={len(source)} output={len(result)} sha256={hashlib.sha256(result).hexdigest()}")

if __name__ == "__main__":
    try: main()
    except Exception as exc:
        print(f"xgs-kpx: {exc}", file=sys.stderr); raise SystemExit(2)
