#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        return 2

    src = Path(sys.argv[1]).expanduser()
    if not src.exists():
        return 3

    try:
        import gi

        gi.require_version("GnomeDesktop", "4.0")
        from gi.repository import Gio, GnomeDesktop
    except Exception:
        return 4

    try:
        gio_file = Gio.File.new_for_path(str(src))
        uri = gio_file.get_uri()
        info = gio_file.query_info(
            "standard::content-type,time::modified",
            Gio.FileQueryInfoFlags.NONE,
            None,
        )
        mime = info.get_content_type()
        modified = info.get_modification_date_time()
        mtime = modified.to_unix() if modified else int(src.stat().st_mtime)

        factory = GnomeDesktop.DesktopThumbnailFactory.new(
            GnomeDesktop.DesktopThumbnailSize.LARGE
        )

        hit = factory.lookup(uri, mtime)
        if hit:
            print(hit)
            return 0

        if not factory.can_thumbnail(uri, mime, mtime):
            return 5

        generated = factory.generate_thumbnail(uri, mime)
        if not generated:
            return 6

        factory.save_thumbnail(generated, uri, mtime)
        hit = factory.lookup(uri, mtime)
        if hit:
            print(hit)
            return 0
        return 7
    except Exception:
        return 8


if __name__ == "__main__":
    raise SystemExit(main())
