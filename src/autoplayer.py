"""
Piano Autoplayer - Virtual Piano / Roblox
------------------------------------------
Lee partituras en formato Virtual Piano y las toca enviando teclas al juego.
Requisitos: Python 3.8+ en Windows. Sin librerias externas.
"""

import ctypes
import json
import os
import random
import re
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, filedialog, messagebox, simpledialog

# ---------------------------------------------------------------------------
# Envio de teclas: SendInput con scancodes fisicos (lo que Roblox si registra)
# ---------------------------------------------------------------------------

user32 = ctypes.WinDLL("user32", use_last_error=True)
winmm = ctypes.WinDLL("winmm")

INPUT_KEYBOARD = 1
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_KEYUP = 0x0002
ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    # pad al tamaño del MOUSEINPUT real: sin esto INPUT queda en 32 bytes
    # y en Windows 64-bit SendInput exige 40 -> rechaza el envío en silencio.
    _fields_ = [("ki", KEYBDINPUT), ("pad", ctypes.c_ubyte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _U)]


# Guarda de seguridad: si esto no da 40 en 64-bit, SendInput no funcionaría.
assert ctypes.sizeof(INPUT) in (28, 40), \
    f"Tamaño de INPUT inesperado: {ctypes.sizeof(INPUT)}"

# Callback opcional para reportar fallos de envío a la interfaz.
_send_error = {"cb": None}


def _send(items):
    if not items:
        return
    arr = (INPUT * len(items))(*items)
    n = user32.SendInput(len(items), ctypes.byref(arr), ctypes.sizeof(INPUT))
    if n != len(items) and _send_error["cb"]:
        err = ctypes.get_last_error()
        _send_error["cb"](err)


def _mk(scan, up):
    flags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if up else 0)
    return INPUT(INPUT_KEYBOARD, _U(ki=KEYBDINPUT(0, scan, flags, 0, 0)))


def press(scans):
    _send([_mk(s, False) for s in scans])


def release(scans):
    _send([_mk(s, True) for s in scans])


SC = {"1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07,
      "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B,
      "q": 0x10, "w": 0x11, "e": 0x12, "r": 0x13, "t": 0x14, "y": 0x15,
      "u": 0x16, "i": 0x17, "o": 0x18, "p": 0x19,
      "a": 0x1E, "s": 0x1F, "d": 0x20, "f": 0x21, "g": 0x22, "h": 0x23,
      "j": 0x24, "k": 0x25, "l": 0x26,
      "z": 0x2C, "x": 0x2D, "c": 0x2E, "v": 0x2F, "b": 0x30, "n": 0x31,
      "m": 0x32}
SC_SHIFT = 0x2A

SHIFT_SYMBOLS = {"!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
                 "^": "6", "&": "7", "*": "8", "(": "9", ")": "0"}


def resolve(ch):
    """(scancode, necesita_shift) o None si el caracter no sirve."""
    if ch in SHIFT_SYMBOLS:
        return SC[SHIFT_SYMBOLS[ch]], True
    if ch.isupper() and ch.lower() in SC:
        return SC[ch.lower()], True
    if ch in SC:
        return SC[ch], False
    return None


# ---------------------------------------------------------------------------
# Transposicion: mapa cromatico del teclado Virtual Piano
# ---------------------------------------------------------------------------

WHITES = "1234567890qwertyuiopasdfghjklzxcvbnm"
DIGIT_SHIFT = {v: k for k, v in SHIFT_SYMBOLS.items()}


def _build_chromatic():
    """Teclas VP ordenadas por altura real. Octava = 12 posiciones."""
    seq = []
    for i, w in enumerate(WHITES):
        seq.append(w)
        if i % 7 in (0, 1, 3, 4, 5) and i + 1 < len(WHITES):
            seq.append(DIGIT_SHIFT[w] if w.isdigit() else w.upper())
    return seq


CHROMATIC = _build_chromatic()
CHROM_IDX = {c: i for i, c in enumerate(CHROMATIC)}


def transpose(ch, semis):
    if semis == 0 or ch not in CHROM_IDX:
        return ch
    j = CHROM_IDX[ch] + semis
    return CHROMATIC[j] if 0 <= j < len(CHROMATIC) else None


# ---------------------------------------------------------------------------
# Parser de partitura
# ---------------------------------------------------------------------------

TOKEN_RE = re.compile(r"\[[^\]]*\]|[^\s-]|-")


def parse_sheet(text):
    """
    [abc] = acorde | espacio = separa beats | abcd pegado = subdivide un beat
    salto de linea = pausa | '|' se ignora
    '-' alarga la nota/grupo anterior un beat; '-' solo = pausa de un beat.
    Devuelve [("note", [chars], dur) | ("rest", None, dur)]
    """
    events = []
    lines = text.splitlines()
    for li, line in enumerate(lines):
        line = line.replace("|", " ").strip()
        if not line:
            events.append(("rest", None, 1.0))
            continue
        for group in line.split():
            toks = TOKEN_RE.findall(group)
            # separo guiones colgados del final para alargar el grupo previo
            trailing = 0
            while toks and toks[-1] == "-":
                trailing += 1
                toks.pop()
            playable = [t for t in toks if t != "-"]
            leading_dashes = len(toks) - len(playable) - 0  # guiones sueltos internos

            if not playable:
                # grupo hecho solo de guiones -> pausa
                events.append(("rest", None, float(len(toks) + trailing)))
                continue

            dur = 1.0 / len(playable)
            for i, tok in enumerate(playable):
                if tok.startswith("["):
                    chars = [c for c in tok[1:-1] if resolve(c)]
                else:
                    chars = [tok] if resolve(tok) else []
                if not chars:
                    continue
                d = dur
                if i == len(playable) - 1:
                    d += trailing        # los guiones del final alargan la última
                events.append(("note", chars, d))
        if li < len(lines) - 1:
            events.append(("rest", None, 0.0))   # marca de fin de linea
    return events


# ---------------------------------------------------------------------------
# Motor de reproduccion
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, cfg, on_status, on_progress):
        self.cfg = cfg                      # dict vivo: se lee en cada nota
        self.on_status = on_status
        self.on_progress = on_progress
        self.stop_flag = threading.Event()
        self.pause_flag = threading.Event()
        self.thread = None
        self.held = set()

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, events):
        if self.running:
            return
        self.stop_flag.clear()
        self.pause_flag.clear()
        self.thread = threading.Thread(target=self._run, args=(events,), daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_flag.set()

    def toggle_pause(self):
        if self.pause_flag.is_set():
            self.pause_flag.clear()
            self.on_status("Reproduciendo...")
        else:
            self.pause_flag.set()
            self._panic()
            self.on_status("Pausado — F7 para seguir")

    def _panic(self):
        if self.held:
            release(list(self.held))
            self.held.clear()
        release([SC_SHIFT])

    def _hit(self, chars, hold, semis):
        plain, shifted = [], []
        for c in chars:
            c = transpose(c, semis)
            if not c:
                continue
            sc, sh = resolve(c)
            (shifted if sh else plain).append(sc)
        if not plain and not shifted:
            return
        if plain:
            press(plain)
            self.held.update(plain)
        if shifted:
            press([SC_SHIFT])
            press(shifted)
            self.held.update(shifted)
        time.sleep(hold)
        if shifted:
            release(shifted)
            release([SC_SHIFT])
        if plain:
            release(plain)
        self.held.clear()

    def _run(self, events):
        winmm.timeBeginPeriod(1)   # sin esto Windows redondea los sleep a ~15ms
        try:
            for i in range(int(self.cfg["countdown"]), 0, -1):
                if self.stop_flag.is_set():
                    self.on_status("Cancelado")
                    return
                self.on_status(f"Cambia a Roblox... {i}")
                time.sleep(1)

            self.on_status("Reproduciendo...")
            clock = time.perf_counter()
            total = max(1, len(events))

            for idx, (kind, chars, dur) in enumerate(events):
                if self.stop_flag.is_set():
                    break
                while self.pause_flag.is_set() and not self.stop_flag.is_set():
                    time.sleep(0.05)
                    clock = time.perf_counter()

                beat = 60.0 / max(20.0, self.cfg["bpm"])     # tempo en vivo
                jitter = self.cfg["humanize"] / 1000.0

                if kind == "rest":
                    clock += beat * (self.cfg["line_gap"] if dur == 0.0 else dur)
                else:
                    hold = min(self.cfg["hold"] / 1000.0, beat * 0.85)
                    self._hit(chars, hold, int(self.cfg["semitones"]))
                    clock += beat * dur
                    if jitter:
                        clock += random.uniform(-jitter, jitter)

                self.on_progress(idx + 1, total)

                left = clock - time.perf_counter()
                while left > 0 and not self.stop_flag.is_set():
                    time.sleep(min(left, 0.005))
                    left = clock - time.perf_counter()

            self._panic()
            self.on_status("Detenido" if self.stop_flag.is_set() else "Listo")
            if self.stop_flag.is_set():
                self.on_progress(0, total)
        finally:
            self._panic()
            winmm.timeEndPeriod(1)


# ---------------------------------------------------------------------------
# Hotkeys globales
# ---------------------------------------------------------------------------

VK = {0x74: "start", 0x75: "stop", 0x76: "pause",
      0x77: "bpm_up", 0x78: "bpm_down"}   # F5 F6 F7 F8 F9


def hotkey_loop(app):
    prev = {k: False for k in VK}
    while True:
        for vk, action in VK.items():
            down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            if down and not prev[vk]:
                app.root.after(0, getattr(app, action))
            prev[vk] = down
        time.sleep(0.03)


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------

BG, PANEL, FG, DIM, ACC = "#1e1e24", "#2a2a33", "#e8e8ec", "#8a8a96", "#7c5cff"

DEMO = """u u u [uf] [uf] [ufx] [0ufx]
6 [80] 3 [80] 3 $ % 6 [80] 3
[6u] u [80u] u [3u] u [80u] u"""

_BASE_DIR = os.path.dirname(
    sys.executable if getattr(sys, "frozen", False) else __file__)
CFG_PATH = os.path.join(_BASE_DIR, "autoplayer_config.json")
SONGS_PATH = os.path.join(_BASE_DIR, "autoplayer_songs.json")


class App:
    def __init__(self, root):
        self.root = root
        root.title("Piano Autoplayer")
        root.configure(bg=BG)
        root.geometry("760x740")
        root.minsize(640, 620)

        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG)
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 9))
        s.configure("Dim.TLabel", foreground=DIM)
        s.configure("H.TLabel", font=("Segoe UI", 15, "bold"), foreground="#a99bff")
        s.configure("TButton", font=("Segoe UI", 9), padding=6,
                    background=PANEL, foreground=FG, borderwidth=0)
        s.map("TButton", background=[("active", "#3a3a46")])
        s.configure("Go.TButton", font=("Segoe UI", 9, "bold"), background=ACC)
        s.map("Go.TButton", background=[("active", "#9179ff")])
        s.configure("TScale", background=BG, troughcolor="#3a3a46")
        s.configure("TEntry", fieldbackground=PANEL, foreground=FG, borderwidth=0)
        s.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                    foreground=FG, borderwidth=0, arrowcolor=FG)
        s.map("TCombobox", fieldbackground=[("readonly", PANEL)],
              foreground=[("readonly", FG)])
        s.configure("Horizontal.TProgressbar", background=ACC,
                    troughcolor=PANEL, borderwidth=0)

        m = ttk.Frame(root, padding=16)
        m.pack(fill="both", expand=True)

        head = ttk.Frame(m)
        head.pack(fill="x")
        ttk.Label(head, text="Piano Autoplayer", style="H.TLabel").pack(side="left")
        ttk.Label(head, text="F5 tocar · F6 detener · F7 pausa · F8/F9 tempo ±",
                  style="Dim.TLabel").pack(side="right", pady=(6, 0))

        # --- barra de la partitura ---
        bar = ttk.Frame(m)
        bar.pack(fill="x", pady=(12, 6))
        ttk.Button(bar, text="Pegar", command=self.paste).pack(side="left")
        ttk.Button(bar, text="Limpiar", command=self.clear).pack(side="left", padx=6)
        ttk.Button(bar, text="Abrir .txt", command=self.load).pack(side="left")
        self.counter = ttk.Label(bar, text="0 notas", style="Dim.TLabel")
        self.counter.pack(side="right")

        # --- biblioteca de canciones ---
        lib = ttk.Frame(m)
        lib.pack(fill="x", pady=(0, 6))
        ttk.Label(lib, text="Biblioteca:", style="Dim.TLabel").pack(side="left")
        self.song_var = tk.StringVar()
        self.song_box = ttk.Combobox(lib, textvariable=self.song_var,
                                     state="readonly", width=26)
        self.song_box.pack(side="left", padx=6)
        self.song_box.bind("<<ComboboxSelected>>", self.load_song)
        ttk.Button(lib, text="Guardar canción",
                   command=self.save_song).pack(side="left")
        ttk.Button(lib, text="Borrar",
                   command=self.delete_song).pack(side="left", padx=6)

        wrap = ttk.Frame(m)
        wrap.pack(fill="both", expand=True)
        self.text = tk.Text(wrap, height=11, bg=PANEL, fg=FG, insertbackground=ACC,
                            font=("Consolas", 11), relief="flat", padx=12, pady=12,
                            wrap="word", undo=True, selectbackground="#4a4470")
        self.text.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.config(yscrollcommand=sb.set)
        self.text.insert("1.0", DEMO)
        self.text.bind("<<Modified>>", self.on_edit)

        # --- panel de ajustes ---
        ttk.Label(m, text="AJUSTES", style="Dim.TLabel").pack(anchor="w", pady=(16, 6))
        grid = ttk.Frame(m)
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        self.vars = {}
        self.outs = {}
        specs = [
            ("bpm",       "Tempo (BPM)",      20,  600, 180, 0),
            ("hold",      "Pulsación (ms)",   10,  400,  40, 0),
            ("line_gap",  "Pausa por línea",   0,    8, 1.0, 1),
            ("humanize",  "Humanizar (ms)",    0,   50,  10, 0),
            ("semitones", "Transponer",      -12,   12,   0, 0),
            ("countdown", "Cuenta atrás (s)",  0,   15,   5, 0),
        ]
        for r, (key, label, lo, hi, default, dec) in enumerate(specs):
            var = tk.DoubleVar(value=default)
            self.vars[key] = (var, dec)
            ttk.Label(grid, text=label).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Scale(grid, from_=lo, to=hi, variable=var,
                      orient="horizontal").grid(row=r, column=1, sticky="ew", padx=10)
            if key == "bpm":
                cell = ttk.Frame(grid)
                cell.grid(row=r, column=2)
                ttk.Button(cell, text="−", width=2,
                           command=self.bpm_down).pack(side="left")
                out = ttk.Label(cell, text=str(default), width=5, anchor="center",
                                background=PANEL, padding=3)
                out.pack(side="left", padx=3)
                ttk.Button(cell, text="+", width=2,
                           command=self.bpm_up).pack(side="left")
            else:
                out = ttk.Label(grid, text=str(default), width=6, anchor="center",
                                background=PANEL, padding=3)
                out.grid(row=r, column=2)
            self.outs[key] = out
            var.trace_add("write", lambda *_a, v=var, o=out, d=dec:
                          o.config(text=f"{v.get():.{d}f}" if d else f"{int(round(v.get()))}"))

        ttk.Label(m, text="Transponer mueve la melodía en semitonos si queda fuera "
                          "del rango del piano. Humanizar desincroniza levemente cada "
                          "nota.", style="Dim.TLabel", wraplength=700,
                  justify="left").pack(anchor="w", pady=(8, 0))

        # --- acciones ---
        act = ttk.Frame(m)
        act.pack(fill="x", pady=(14, 0))
        ttk.Button(act, text="▶  Tocar", style="Go.TButton",
                   command=self.start).pack(side="left")
        ttk.Button(act, text="Detener", command=self.stop).pack(side="left", padx=6)
        ttk.Button(act, text="Pausa", command=self.pause).pack(side="left")
        ttk.Button(act, text="Guardar ajustes",
                   command=self.save_cfg).pack(side="right")

        self.bar = ttk.Progressbar(m, maximum=100)
        self.bar.pack(fill="x", pady=(12, 6))
        self.status = ttk.Label(m, text="Listo", style="Dim.TLabel")
        self.status.pack(anchor="w")

        self.cfg = {}
        self.sync_cfg()
        self.load_cfg()
        self.refresh_songs()
        self.on_edit()
        self.player = Player(self.cfg, self.set_status, self.set_progress)
        _send_error["cb"] = lambda err: self.set_status(
            f"Windows rechazó el envío (error {err}). "
            "Probá ejecutar como administrador.")
        threading.Thread(target=hotkey_loop, args=(self,), daemon=True).start()
        root.bind("<Up>", lambda e: self.bpm_up())
        root.bind("<Down>", lambda e: self.bpm_down())
        root.protocol("WM_DELETE_WINDOW", self.close)

    # -- config viva ---------------------------------------------------------
    def sync_cfg(self):
        for k, (v, _) in self.vars.items():
            self.cfg[k] = v.get()
            v.trace_add("write", lambda *_a, key=k: self.cfg.__setitem__(
                key, self.vars[key][0].get()))

    def save_cfg(self):
        try:
            with open(CFG_PATH, "w") as f:
                json.dump({k: v.get() for k, (v, _) in self.vars.items()}, f)
            self.set_status("Ajustes guardados")
        except Exception as e:
            self.set_status(f"No se pudo guardar: {e}")

    def load_cfg(self):
        try:
            with open(CFG_PATH) as f:
                for k, val in json.load(f).items():
                    if k in self.vars:
                        self.vars[k][0].set(val)
        except Exception:
            pass

    # -- biblioteca de canciones --------------------------------------------
    def _read_songs(self):
        try:
            with open(SONGS_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_songs(self, songs):
        with open(SONGS_PATH, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=2)

    def refresh_songs(self, select=None):
        names = sorted(self._read_songs().keys())
        self.song_box["values"] = names
        if select and select in names:
            self.song_var.set(select)
        elif not names:
            self.song_var.set("")

    def save_song(self):
        content = self.text.get("1.0", "end").strip()
        if not content:
            self.set_status("No hay nada para guardar")
            return
        name = simpledialog.askstring("Guardar canción",
                                      "Nombre de la canción:", parent=self.root)
        if not name:
            return
        name = name.strip()
        songs = self._read_songs()
        if name in songs and not messagebox.askyesno(
                "Sobrescribir", f"«{name}» ya existe. ¿Reemplazar?"):
            return
        songs[name] = content
        self._write_songs(songs)
        self.refresh_songs(select=name)
        self.set_status(f"Guardada: {name}")

    def load_song(self, _=None):
        name = self.song_var.get()
        if not name:
            return
        content = self._read_songs().get(name)
        if content is None:
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.on_edit()
        self.set_status(f"Cargada: {name}")

    def delete_song(self):
        name = self.song_var.get()
        if not name:
            return
        if not messagebox.askyesno("Borrar", f"¿Borrar «{name}» de la biblioteca?"):
            return
        songs = self._read_songs()
        songs.pop(name, None)
        self._write_songs(songs)
        self.refresh_songs()
        self.set_status(f"Borrada: {name}")

    # -- partitura -----------------------------------------------------------
    def on_edit(self, _=None):
        self.text.edit_modified(False)
        try:
            self.events = parse_sheet(self.text.get("1.0", "end"))
            n = sum(1 for e in self.events if e[0] == "note")
            self.counter.config(text=f"{n} notas")
        except Exception:
            self.events = []

    def paste(self):
        try:
            data = self.root.clipboard_get()
        except tk.TclError:
            return
        self.text.delete("1.0", "end")
        self.text.insert("1.0", data)
        self.on_edit()

    def clear(self):
        self.text.delete("1.0", "end")
        self.on_edit()

    def load(self):
        p = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if p:
            with open(p, encoding="utf-8", errors="ignore") as f:
                self.text.delete("1.0", "end")
                self.text.insert("1.0", f.read())
            self.on_edit()

    # -- control -------------------------------------------------------------
    def set_status(self, msg):
        self.root.after(0, lambda: self.status.config(text=msg))

    def set_progress(self, i, total):
        def upd():
            self.bar.config(value=i / total * 100)
            if i:
                self.status.config(text=f"Reproduciendo… evento {i} de {total}")
        self.root.after(0, upd)

    def start(self):
        if self.player.running:
            return
        self.on_edit()
        if not any(e[0] == "note" for e in self.events):
            messagebox.showwarning("Vacío", "No encontré notas válidas en la partitura.")
            return
        self.player.start(list(self.events))

    def bump_bpm(self, delta):
        var = self.vars["bpm"][0]
        new = max(20, min(600, int(round(var.get())) + delta))
        var.set(new)
        self.set_status(f"Tempo: {new} BPM")

    def bpm_up(self):
        self.bump_bpm(5)

    def bpm_down(self):
        self.bump_bpm(-5)

    def stop(self):
        self.player.stop()

    def pause(self):
        if self.player.running:
            self.player.toggle_pause()

    def close(self):
        self.player.stop()
        time.sleep(0.15)
        self.root.destroy()


if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()
