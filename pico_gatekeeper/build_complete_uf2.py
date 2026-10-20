#!/usr/bin/env python3
"""
File: pico_gatekeeper/build_complete_uf2.py
Description: Builds a single all-in-one RP2350 UF2 firmware image
             (`arctic_trailcam_pico2_complete.uf2`) combining:
               1. Official Stable MicroPython for Raspberry Pi Pico 2 (0x10000000)
               2. Pre-formatted LittleFS v2 filesystem (0x10100000) pre-loaded with
                  `main.py` and `test_qmc5883l.py` (with zero OS metadata/junk files).
             Flashing this single .uf2 via `picotool load -v -x` in BOOTSEL mode
             installs BOTH MicroPython AND the complete Gatekeeper application in one step!
License: MIT
"""
import glob
import os
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(SCRIPT_DIR, "arctic_trailcam_pico2_complete.uf2")


def build_combined_pico2_uf2(base_uf2_path=None, out_path=DEFAULT_OUT):
    from littlefs import LittleFS

    if not base_uf2_path:
        candidates = sorted(glob.glob(os.path.expanduser("~/Downloads/RPI_PICO2*v1.25*.uf2")))
        if not candidates:
            candidates = sorted(glob.glob(os.path.expanduser("~/Downloads/RPI_PICO2*.uf2")))
        if not candidates:
            raise FileNotFoundError("No base RPI_PICO2*.uf2 found in ~/Downloads/")
        base_uf2_path = candidates[0]

    fs = LittleFS(
        block_size=4096,
        block_count=768,
        read_size=256,
        prog_size=256,
        cache_size=1024,
        lookahead_size=32,
        disk_version=0x00020000,
    )
    for fname in ("main.py", "test_qmc5883l.py"):
        src = os.path.join(SCRIPT_DIR, fname)
        with open(src, "rb") as fsrc:
            payload = fsrc.read()
        with fs.open("/" + fname, "wb") as fdst:
            fdst.write(payload)

    img = bytes(fs.context.buffer)
    active_sectors = []
    for s in range(768):
        sec = img[s * 4096 : (s + 1) * 4096]
        if s in (0, 1) or sec != b"\xff" * 4096:
            active_sectors.append(s)

    with open(base_uf2_path, "rb") as f:
        uf2_raw = f.read()

    errata_blocks = []
    arm_chunks = []
    for i in range(len(uf2_raw) // 512):
        blk = uf2_raw[i * 512 : (i + 1) * 512]
        m0, m1, flags, addr, psize, blkno, numblks, fam = struct.unpack("<IIIIIIII", blk[:32])
        if fam == 0xE48BFF57:
            errata_blocks.append(blk)
        elif fam == 0xE48BFF59:
            arm_chunks.append((addr, blk[32 : 32 + 256]))

    lfs_base = 0x10100000
    for s in active_sectors:
        sec_bytes = img[s * 4096 : (s + 1) * 4096]
        for p in range(16):
            addr = lfs_base + s * 4096 + p * 256
            arm_chunks.append((addr, sec_bytes[p * 256 : (p + 1) * 256]))

    total_arm = len(arm_chunks)
    out_blocks = list(errata_blocks)
    for idx, (addr, payload) in enumerate(arm_chunks):
        hdr = struct.pack(
            "<IIIIIIII",
            0x0A324655,
            0x9E5D5157,
            0x00002000,
            addr,
            256,
            idx,
            total_arm,
            0xE48BFF59,
        )
        pad = b"\x00" * (512 - 32 - 256 - 4)
        ftr = struct.pack("<I", 0x0AB16F30)
        out_blocks.append(hdr + payload + pad + ftr)

    with open(out_path, "wb") as f:
        f.write(b"".join(out_blocks))
    print(f"[+] Built {out_path} ({os.path.getsize(out_path)} bytes, {total_arm} RP2350 blocks, files={fs.listdir('/')})")
    return out_path


if __name__ == "__main__":
    build_combined_pico2_uf2()
