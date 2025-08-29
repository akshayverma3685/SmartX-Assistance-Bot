#!/usr/bin/env python3
"""
logs/manager.py

Utility to inspect local bot log files:
- list available logs
- show last N lines (tail)
- paginate logs by lines
- export slice to file (CSV or plain)
- follow mode (tail -f)

Designed to work with LOG_DIR from core.logger (config.LOG_DIR).
"""

import argparse
import os
import sys
import asyncio
from typing import List, Optional

import config
from pathlib import Path
from collections import deque

LOG_DIR = Path(getattr(config, "LOG_DIR", "logs"))

AVAILABLE_FILES = ["bot.log", "errors.log", "payments.log", "usage.log"]

def resolve_path(fname: str) -> Path:
    path = LOG_DIR / fname
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    return path

def list_logs():
    files = []
    for f in AVAILABLE_FILES:
        p = LOG_DIR / f
        if p.exists():
            files.append({"name": f, "path": str(p), "size": p.stat().st_size})
    return files

def tail_file(path: Path, lines: int = 100) -> List[str]:
    """
    Return last `lines` lines efficiently using deque.
    """
    dq = deque(maxlen=lines)
    with open(path, "rb") as fh:
        for raw in fh:
            try:
                dq.append(raw.decode("utf-8", errors="replace").rstrip("\n"))
            except Exception:
                dq.append(raw.decode("latin-1", errors="replace").rstrip("\n"))
    return list(dq)

def paginate_file(path: Path, page: int =1, per_page: int =100) -> List[str]:
    """
    Return page (1-based) of file lines.
    """
    start = (page - 1) * per_page
    end = start + per_page
    out = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if i >= start and i < end:
                out.append(line.rstrip("\n"))
            if i >= end:
                break
    return out

def export_slice(path: Path, out_path: Path, start_line: int = 0, num_lines: Optional[int] = None):
    with open(path, "r", encoding="utf-8", errors="replace") as fh, open(out_path, "w", encoding="utf-8") as out:
        for i, line in enumerate(fh):
            if i < start_line:
                continue
            if num_lines is not None and i >= start_line + num_lines:
                break
            out.write(line)

async def follow(path: Path, poll_interval: float = 0.8):
    """
    Async tail -f implementation. Prints new lines as they are appended.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        # go to end
        fh.seek(0, os.SEEK_END)
        try:
            while True:
                line = fh.readline()
                if line:
                    print(line.rstrip("\n"))
                else:
                    await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            return

def build_parser():
    p = argparse.ArgumentParser(prog="logs/manager.py", description="Manage bot log files")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("list", help="List known log files")

    show = sub.add_parser("tail", help="Show last N lines")
    show.add_argument("file", choices=AVAILABLE_FILES)
    show.add_argument("--lines", type=int, default=200)

    pag = sub.add_parser("page", help="Paginate file by lines")
    pag.add_argument("file", choices=AVAILABLE_FILES)
    pag.add_argument("--page", type=int, default=1)
    pag.add_argument("--per-page", type=int, default=200)

    exp = sub.add_parser("export", help="Export slice of file")
    exp.add_argument("file", choices=AVAILABLE_FILES)
    exp.add_argument("--start", type=int, default=0)
    exp.add_argument("--lines", type=int, default=None)
    exp.add_argument("--out", required=True)

    fol = sub.add_parser("follow", help="Follow (tail -f)")
    fol.add_argument("file", choices=AVAILABLE_FILES)
    fol.add_argument("--interval", type=float, default=0.8)

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    if args.cmd == "list":
        for info in list_logs():
            print(f"{info['name']}\t{info['size']} bytes\t{info['path']}")
        return

    try:
        path = resolve_path(args.file)
    except Exception as e:
        print("Error:", e)
        return

    if args.cmd == "tail":
        lines = tail_file(path, args.lines)
        for l in lines:
            print(l)
        return

    if args.cmd == "page":
        rows = paginate_file(path, page=args.page, per_page=args.per_page)
        for r in rows:
            print(r)
        return

    if args.cmd == "export":
        outp = Path(args.out)
        export_slice(path, outp, start_line=args.start, num_lines=args.lines)
        print("Exported to", outp)
        return

    if args.cmd == "follow":
        try:
            asyncio.run(follow(path, poll_interval=args.interval))
        except KeyboardInterrupt:
            print("Stopped.")
        return

if __name__ == "__main__":
    main()
