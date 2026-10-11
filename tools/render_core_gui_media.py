#!/usr/bin/env python3
"""Capture bilingual Tk windows: core GUI, inspector, and virtual-company labs.

Requires python3-tk and a display::

    xvfb-run -a -s "-screen 0 1680x1050x24" python tools/render_core_gui_media.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
VC_SRC = REPO / "Demo" / "Virtual company" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _grab(window, path: Path) -> None:
    from PIL import ImageGrab

    window.update_idletasks()
    window.update()
    try:
        window.deiconify()
        window.lift()
    except Exception:
        pass
    window.update()
    time.sleep(0.4)
    window.update()
    x = window.winfo_rootx()
    y = window.winfo_rooty()
    width = max(window.winfo_width(), 1)
    height = max(window.winfo_height(), 1)
    image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)
    print(f"{path.relative_to(REPO)}  {image.size[0]}x{image.size[1]}  {path.stat().st_size / 1024:.0f} KB")


def _dump_texts(widget, found: list[str]) -> None:
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        _dump_texts(child, found)
    try:
        current = widget.cget("text")
    except Exception:
        return
    if isinstance(current, str) and current.strip():
        found.append(current)


def _capture_core(lang: str) -> None:
    import tkinter as tk

    from gui import NOWAGUI
    from gui_i18n import reset_language, set_language

    reset_language()
    set_language(lang)
    root = tk.Tk()
    gui = NOWAGUI(root, lang=lang)
    root.update_idletasks()
    root.update()
    out = REPO / "docs" / "media" / lang
    texts: list[str] = []
    _dump_texts(root, texts)
    print(f"--- core {lang} title={root.title()!r}")
    print(" | ".join(texts[:40]))
    _grab(root, out / "core-gui.png")
    gui.open_inspector()
    inspector = gui.inspector_window
    inspector.geometry("900x650+40+40")
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.2)
    inspector.update()
    print(
        f"inspector mapped={inspector.winfo_ismapped()} "
        f"size={inspector.winfo_width()}x{inspector.winfo_height()} "
        f"children={len(inspector.winfo_children())}"
    )
    _grab(inspector, out / "core-inspector.png")
    root.destroy()


def _capture_lab(name: str, factory, lang: str) -> None:
    out = REPO / "docs" / "media" / lang
    app = factory(lang)
    try:
        app.update_idletasks()
        app.update()
        texts: list[str] = []
        _dump_texts(app, texts)
        print(f"--- {name} {lang} title={app.title()!r}")
        print(" | ".join(texts[:24]))
        _grab(app, out / f"{name}.png")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def _labs(lang: str) -> None:
    import os
    import tkinter as tk

    # Linux Tk has no Windows system color. The labs still ask for it when
    # painting the idle language button. Substitute only in this capture process.
    _button_configure = tk.Button.configure

    def _configure(self, cnf=None, **kw):
        if kw.get("bg") == "SystemButtonFace":
            kw["bg"] = "#f0f0f0"
        return _button_configure(self, cnf, **kw)

    tk.Button.configure = _configure

    if str(VC_SRC) not in sys.path:
        sys.path.insert(0, str(VC_SRC))
    from nowa_sandbox.gui_app import DEMO_ROOT

    os.chdir(DEMO_ROOT)
    from nowa_body.gui_app import BodyLabApp
    from nowa_body.gui_configurator import RoleConfiguratorApp
    from nowa_sandbox.gui_app import SandboxLabApp
    _capture_lab("body-lab", lambda code: BodyLabApp(lang=code), lang)
    _capture_lab("role-configurator", lambda code: RoleConfiguratorApp(lang=code), lang)
    _capture_lab("sandbox-lab", lambda code: SandboxLabApp(lang=code), lang)


def main() -> int:
    only = set(sys.argv[1:])
    if not only or "core" in only:
        for lang in ("en", "ru"):
            _capture_core(lang)
    if not only or "labs" in only:
        for lang in ("en", "ru"):
            _labs(lang)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
