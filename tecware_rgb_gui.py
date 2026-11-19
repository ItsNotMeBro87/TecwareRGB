#!/usr/bin/env python3
"""GUI front-end for the `rgb_keyboard` CLI (github.com/dokutan/rgb_keyboard).
Built for the Tecware Phantom TKL (USB 0c45:652f, ANSI). Needs: python-pyside6, rgb_keyboard, lsusb."""
import json, os, re, shutil, subprocess, sys, time
from PySide6.QtGui import QColor
from PySide6.QtCore import Signal
from PySide6.QtWidgets import *

VIDPID = "0c45:652f"
CFG = os.path.expanduser("~/.config/tecware-rgb")
U = 44


def ks(s): return [(c, c.upper(), 1) for c in s]
def g(w): return (None, "", w)
def fk(a, b): return [(f"F{i}", f"F{i}", 1) for i in range(a, b)]


ROWS = [
    [("Esc", "Esc", 1), g(1)] + fk(1, 5) + [g(.5)] + fk(5, 9) + [g(.5)] + fk(9, 13) + [g(.5),
     ("PrtSc", "Prt", 1), ("ScrLk", "Scr", 1), ("Pause", "Pau", 1)],
    [("Tilde", "`", 1)] + ks("1234567890") + [("Minus", "-", 1), ("Equals", "=", 1), ("Backspace", "Bksp", 2), g(.5),
     ("Insert", "Ins", 1), ("Home", "Home", 1), ("PgUp", "PgUp", 1)],
    [("Tab", "Tab", 1.5)] + ks("qwertyuiop") + [("Bracket_l", "[", 1), ("Bracket_r", "]", 1), ("Backslash", "\\", 1.5), g(.5),
     ("Delete", "Del", 1), ("End", "End", 1), ("PgDn", "PgDn", 1)],
    [("Caps_Lock", "Caps", 1.75)] + ks("asdfghjkl") + [("Semicolon", ";", 1), ("Apostrophe", "'", 1), ("Return", "Enter", 2.25)],
    [("Shift_l", "Shift", 2.25)] + ks("zxcvbnm") + [("Comma", ",", 1), ("Period", ".", 1), ("Slash", "/", 1),
     ("Shift_r", "Shift", 2.75), g(1.5), ("Up", "Up", 1)],
    [("Ctrl_l", "Ctrl", 1.25), ("Super_l", "Win", 1.25), ("Alt_l", "Alt", 1.25), ("Space", "Space", 6.25),
     ("Alt_r", "Alt", 1.25), ("Fn", "Fn", 1.25), ("Menu", "Menu", 1.25), ("Ctrl_r", "Ctrl", 1.25), g(.5),
     ("Left", "Left", 1), ("Down", "Down", 1), ("Right", "Right", 1)],
]
MODES = ["off", "fixed", "sine", "rain", "waterfall", "vortex", "swirl", "breathing", "breathing-color",
         "reactive-ripple", "reactive-single", "reactive-horizontal", "reactive-color", "horizontal-wave",
         "vertical-wave", "diagonal-wave", "pulse", "hurricane", "ripple", "custom"]


class Key(QPushButton):
    left, right = Signal(str), Signal(str)

    def __init__(s, name, label, parent):
        super().__init__(label, parent)
        s.name = name

    def mousePressEvent(s, e):
        (s.left if e.button().name == "LeftButton" else s.right).emit(s.name)


class Win(QWidget):
    def __init__(s):
        super().__init__()
        s.setWindowTitle("Tecware Phantom RGB")
        os.makedirs(CFG, exist_ok=True)
        s.exe = shutil.which("rgb_keyboard")
        s.colors, s.keys, s.sel = {}, {}, set()
        s.cur, s.fxcolor = "ff0000", "ff0000"
        v = QVBoxLayout(s)
        top = QHBoxLayout()
        s.target = QComboBox(); s.target.addItems(["1", "2", "3"])
        top.addWidget(QLabel("Write to profile:")); top.addWidget(s.target)
        top.addWidget(QLabel("   Switch active profile:"))
        for p in "123":
            b = QPushButton(p); b.clicked.connect(lambda _=0, p=p: s.activate(p)); top.addWidget(b)
        s.keep = QCheckBox("keep typing while applying (-I)"); top.addWidget(s.keep); top.addStretch()
        v.addLayout(top)
        tabs = QTabWidget(); v.addWidget(tabs)
        tabs.addTab(s.perkey_tab(), "Per-key colours"); tabs.addTab(s.fx_tab(), "Effects / settings"); s.target.currentTextChanged.connect(s.load_profile)
        s.log = QPlainTextEdit(); s.log.setReadOnly(True); s.log.setMaximumHeight(120); v.addWidget(s.log)
        if not s.exe:
            s.log.appendPlainText("rgb_keyboard not found in PATH - install it first.")

    # ---- running the CLI ----
    def run(s, args, confirm=None):
        if not s.exe:
            return None
        if confirm and QMessageBox.question(s, "Confirm", confirm) != QMessageBox.StandardButton.Yes:
            return None
        cmd = [s.exe]
        try:  # device number changes after a replug, so look it up each time
            m = re.search(r"Bus (\d+) Device (\d+)", subprocess.run(["lsusb", "-d", VIDPID], capture_output=True, text=True).stdout)
            if m: cmd += ["-B", str(int(m[1])), "-D", str(int(m[2]))]
            if s.keep.isChecked(): cmd.append("-I")
            r = subprocess.run(cmd + args, capture_output=True, text=True, timeout=20)
        except Exception as e:
            s.log.appendPlainText(f"ERROR: {e}"); return None
        out = (r.stdout + r.stderr).strip()
        s.log.appendPlainText("$ rgb_keyboard " + " ".join(cmd[1:] + args) + (f"\n{out}" if out else "") +
                              ("" if r.returncode == 0 else f"\n[exit code {r.returncode}]"))
        return out

    def warn(s):
        return f"This overwrites the stored settings of profile {s.target.currentText()} on the keyboard. Continue?"

    # ---- per-key tab ----
    def perkey_tab(s):
        w = QWidget(); v = QVBoxLayout(w)
        board = QWidget(); board.setFixedSize(int(18.5 * U) + 8, int(6.5 * U) + 8)
        for r, row in enumerate(ROWS):
            x, y = 4, int((r + (.5 if r else 0)) * U) + 4
            for name, label, wd in row:
                if name:
                    k = Key(name, label, board); k.setGeometry(x, y, int(wd * U) - 3, U - 3)
                    k.left.connect(s.toggle); k.right.connect(s.pick); s.keys[name] = k; s.style(name)
                x += int(wd * U)
        v.addWidget(board)
        v.addWidget(QLabel("Click keys to select them (cyan outline), click again to deselect. Choose a brush colour, then press Paint selected. Right-click a key to copy its colour into the brush."))
        h = QHBoxLayout()
        s.brush = QPushButton("Brush colour"); s.brush.clicked.connect(s.choose_brush); s.set_btn(s.brush, s.cur); h.addWidget(s.brush)
        for text, fn in [("Paint selected", s.paint_sel), ("Turn selected off", s.off_sel), ("Select all", s.sel_all), ("Deselect all", s.desel)]:
            b = QPushButton(text); b.clicked.connect(fn); h.addWidget(b)
        h.addStretch(); v.addLayout(h)
        h = QHBoxLayout()
        for text, fn in [("Fill all", s.fill), ("Clear all", s.clear), ("Save layout…", s.save), ("Load layout…", s.load),
                         ("Import from keyboard (-r, experimental)", s.import_kb)]:
            b = QPushButton(text); b.clicked.connect(fn); h.addWidget(b)
        h.addStretch(); v.addLayout(h)
        h = QHBoxLayout()
        a = QPushButton("Apply to keyboard"); a.clicked.connect(s.apply_keys); h.addWidget(a)
        s.act = QCheckBox("switch to this profile after applying"); s.act.setChecked(True); h.addWidget(s.act)
        s.force = QCheckBox("force reload (flip profile)"); s.force.setChecked(True); h.addWidget(s.force)
        s.delay = QSpinBox(); s.delay.setRange(0, 3000); s.delay.setValue(600); s.delay.setSuffix(" ms delay"); h.addWidget(s.delay)
        b = QPushButton("Backup keyboard settings (-r)"); b.clicked.connect(s.backup); h.addWidget(b)
        h.addStretch(); v.addLayout(h)
        return w

    def set_btn(s, b, c):
        q = QColor("#" + c)
        b.setStyleSheet(f"background:#{c};color:{'black' if q.lightness() > 128 else 'white'};")

    def style(s, n):
        c = s.colors.get(n, "000000"); q = QColor("#" + c)
        bd = "3px solid #00e5ff" if n in s.sel else "1px solid #666"
        s.keys[n].setStyleSheet(f"background:#{c};color:{'black' if q.lightness() > 128 else 'white'};"
                                f"border:{bd};border-radius:4px;")

    def toggle(s, n): s.sel ^= {n}; s.style(n)

    def paint_sel(s):
        for n in s.sel: s.colors[n] = s.cur
        s.desel()

    def off_sel(s):
        for n in s.sel: s.colors[n] = "000000"
        s.desel()

    def sel_all(s):
        s.sel = set(s.keys)
        for n in s.keys: s.style(n)

    def desel(s):
        s.sel = set()
        for n in s.keys: s.style(n)

    def activate(s, p):
        s.target.setCurrentText(p)
        s.run(["-a", p])

    def reload(s, p):  # workaround for stale colours: briefly flip to another profile, then back
        d = s.delay.value() / 1000
        if s.force.isChecked():
            time.sleep(d); s.run(["-a", str(int(p) % 3 + 1)])
        time.sleep(d); s.run(["-a", p])

    def load_profile(s, p):
        try:
            s.colors = {k: v for k, v in json.load(open(f"{CFG}/profile{p}.json")).items() if k in s.keys}
        except Exception:
            s.colors = {}
            s.log.appendPlainText(f"No layout saved by this GUI for profile {p}; stored colours can't be read back, so the board is blank.")
        s.desel()

    def import_kb(s):
        out = s.run(["-r"]) or ""
        found = {m[1]: m[2].lower() for m in re.finditer(r"([A-Za-z_0-9]+)\s*[=:]\s*#?([0-9a-fA-F]{6})\b", out) if m[1] in s.keys}
        if found: s.colors = found; s.desel()
        s.log.appendPlainText(f"Imported {len(found)} key colours." if found else "No per-key colours found in the -r output.")

    def paint(s, n): s.colors[n] = s.cur; s.style(n)

    def pick(s, n): s.cur = s.colors.get(n, "000000"); s.set_btn(s.brush, s.cur)

    def choose_brush(s):
        c = QColorDialog.getColor(QColor("#" + s.cur), s)
        if c.isValid(): s.cur = c.name()[1:]; s.set_btn(s.brush, s.cur)

    def fill(s):
        for n in s.keys: s.paint(n)

    def clear(s):
        s.colors = {}
        for n in s.keys: s.style(n)

    def save(s):
        f, _ = QFileDialog.getSaveFileName(s, "Save layout", CFG + "/layout.json", "JSON (*.json)")
        if f: json.dump(s.colors, open(f, "w"), indent=1)

    def load(s):
        f, _ = QFileDialog.getOpenFileName(s, "Load layout", CFG, "JSON (*.json)")
        if f:
            s.colors = {k: v for k, v in json.load(open(f)).items() if k in s.keys}
            for n in s.keys: s.style(n)

    def apply_keys(s):
        p = s.target.currentText()
        pat = "".join(f"{n}={s.colors.get(n, '000000')};" for n in s.keys)
        if s.run(["-p", p, "-l", "custom", "-K", pat], s.warn()) is not None:
            json.dump(s.colors, open(f"{CFG}/profile{p}.json", "w"))
            if s.act.isChecked(): s.reload(p)

    def backup(s):
        out = s.run(["-r"])
        if out:
            f = f"{CFG}/backup-{time.strftime('%Y%m%d-%H%M%S')}.txt"
            open(f, "w").write(out); s.log.appendPlainText("Saved to " + f)

    # ---- effects tab ----
    def fx_tab(s):
        w = QWidget(); f = QFormLayout(w)
        s.mode = QComboBox(); s.mode.addItems(MODES); s.mode.setCurrentText("fixed"); f.addRow("LED mode", s.mode)
        h = QHBoxLayout(); s.fxb = QPushButton("Colour"); s.set_btn(s.fxb, s.fxcolor); s.fxb.clicked.connect(s.choose_fx)
        s.multi = QCheckBox("rainbow (multi)"); h.addWidget(s.fxb); h.addWidget(s.multi); f.addRow("Colour", h)
        s.bri = QSpinBox(); s.bri.setRange(0, 9); s.bri.setValue(5); s.bri.setToolTip("Your keyboard seems to top out at 5")
        f.addRow("Brightness", s.bri)
        s.spd = QSpinBox(); s.spd.setRange(0, 3); s.spd.setValue(2); f.addRow("Speed", s.spd)
        s.dir = QComboBox(); s.dir.addItems(["(unchanged)", "left", "right", "up", "down", "inwards", "outwards"]); f.addRow("Direction", s.dir)
        s.var = QComboBox(); s.var.addItems(["(unchanged)", "red", "yellow", "green", "blue"]); f.addRow("Reactive variant", s.var)
        s.rate = QComboBox(); s.rate.addItems(["(unchanged)", "125", "250", "500", "1000"]); f.addRow("USB report rate (Hz)", s.rate)
        a = QPushButton("Apply to keyboard"); a.clicked.connect(s.apply_fx); f.addRow(a)
        return w

    def choose_fx(s):
        c = QColorDialog.getColor(QColor("#" + s.fxcolor), s)
        if c.isValid(): s.fxcolor = c.name()[1:]; s.set_btn(s.fxb, s.fxcolor)

    def apply_fx(s):
        p = s.target.currentText()
        a = ["-p", p, "-l", s.mode.currentText(), "-c", "multi" if s.multi.isChecked() else s.fxcolor,
             "-b", str(s.bri.value()), "-s", str(s.spd.value())]
        for flag, box in (("-d", s.dir), ("-v", s.var), ("-R", s.rate)):
            if box.currentIndex() > 0: a += [flag, box.currentText()]
        if s.run(a, s.warn()) is not None:
            try: os.remove(f"{CFG}/profile{p}.json")
            except OSError: pass
            s.reload(p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Win(); w.show()
    sys.exit(app.exec())
