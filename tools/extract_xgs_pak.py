#!/usr/bin/env python3
"""Read-only inventory/extractor for Exient XGS v2 KPX/zlib PAK archives."""
import argparse, io, os, struct, sys, zipfile, zlib
from pathlib import PurePosixPath

def parse_pak(blob, label, out_dir):
    if len(blob) < 20:
        raise ValueError(f"{label}: truncated header")
    version, magic = blob[0], blob[1:4]
    if version != 2 or magic != b"KPX":
        raise ValueError(f"{label}: unsupported header {version!r}/{magic!r}")
    folders, files, table_size, compression = struct.unpack_from("<IIII", blob, 4)
    if compression not in (0, 1, 2):
        raise ValueError(f"{label}: unknown compression {compression}")
    folder_base = 20
    file_base = folder_base + folders * 32
    strings_base = file_base + files * 32
    if strings_base > len(blob):
        raise ValueError(f"{label}: metadata tables exceed archive")
    def cstr(offset):
        pos = strings_base + offset
        if pos < strings_base or pos >= len(blob):
            raise ValueError(f"{label}: string offset out of range: {offset}")
        end = blob.find(b"\0", pos)
        if end < 0:
            raise ValueError(f"{label}: unterminated string at {offset}")
        return blob[pos:end].decode("utf-8", "replace")
    folder_rows = []
    for i in range(folders):
        row = struct.unpack_from("<QQQII", blob, folder_base + i * 32)
        folder_rows.append(row)
    file_rows = []
    for i in range(files):
        row = struct.unpack_from("<QIIIIQ", blob, file_base + i * 32)
        file_rows.append(row)
    # KPX folder rows: u64 name, u64 filesPos, u64 foldersPos, u32 fileCount, u32 folderCount.
    paths = {}
    visiting = set()
    def walk(folder_idx, prefix=""):
        if folder_idx in visiting or folder_idx < 0 or folder_idx >= folders:
            raise ValueError(f"{label}: invalid/cyclic folder index {folder_idx}")
        visiting.add(folder_idx)
        row = folder_rows[folder_idx]
        name = cstr(row[0])
        here = "/".join(x for x in (prefix, name) if x)
        fpos, dpos, fcount, dcount = row[1], row[2], row[3], row[4]
        if fpos + fcount > files or dpos + dcount > folders:
            raise ValueError(f"{label}: folder {folder_idx} index range outside tables")
        for fi in range(fpos, fpos + fcount):
            paths[fi] = "/".join(x for x in (here, cstr(file_rows[fi][0])) if x)
        for di in range(dpos, dpos + dcount):
            walk(di, here)
        visiting.remove(folder_idx)
    if folders:
        try:
            walk(0)
        except Exception:
            paths = {}
    os.makedirs(out_dir, exist_ok=True)
    lines = [f"PAK {label}: version={version} magic=KPX folders={folders} files={files} content_table_bytes={table_size} compression={compression}"]
    text_ext = {".xml", ".atlas", ".txt", ".json", ".manifest", ".ini", ".csv"}
    for i, row in enumerate(file_rows):
        name_off, unpacked, offset, compressed, timestamp, packed = row
        name = paths.get(i) or cstr(name_off)
        if offset > len(blob) or packed > len(blob) - offset:
            raise ValueError(f"{label}: payload bounds invalid for entry {i} ({name})")
        raw = blob[offset:offset + packed]
        if compressed:
            if compression == 1:
                data = zlib.decompress(raw)
            elif compression == 2:
                raise ValueError(f"{label}: LZ4 entry found; LZ4 decoder not implemented")
            else:
                raise ValueError(f"{label}: compressed entry but archive compression is raw")
        else:
            data = raw
        if len(data) != unpacked:
            raise ValueError(f"{label}: size mismatch for {name}: got {len(data)}, expected {unpacked}")
        safe = PurePosixPath(name)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError(f"{label}: unsafe entry path {name!r}")
        dest = os.path.join(out_dir, *safe.parts)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        sig = data[:12].hex(" ")
        lines.append(f"  [{i:03d}] {name} | packed={packed} unpacked={unpacked} compressed={bool(compressed)} signature={sig}")
        if safe.suffix.lower() in text_ext:
            sample = data[:16000].decode("utf-8", "replace").replace("\r", "")
            lines.append("    --- text preview ---")
            lines.extend("    " + line[:400] for line in sample.splitlines()[:80])
            lines.append("    --- end preview ---")
    return lines

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apk")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    all_lines = []
    wanted = ("assets/data/ui/ui_bundles.pak", "assets/data/uisplash.pak", "assets/data/uienv.pak")
    with zipfile.ZipFile(args.apk) as z:
        names = set(z.namelist())
        for name in wanted:
            if name not in names:
                all_lines.append(f"NOT FOUND: {name}")
                continue
            target = os.path.join(args.out, os.path.basename(name)[:-4])
            all_lines.extend(parse_pak(z.read(name), name, target))
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("\n".join(all_lines) + "\n")
    print("\n".join(line for line in all_lines if line.startswith("PAK ") or line.startswith("NOT FOUND:")))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PAK extraction failed: {exc}", file=sys.stderr)
        sys.exit(1)
