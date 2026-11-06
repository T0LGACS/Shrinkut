import sys
import os
import io
import re
import subprocess
import threading
import time
import tempfile
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk, ImageEnhance

try:
    import imageio_ffmpeg as _iio
    _FFMPEG = _iio.get_ffmpeg_exe()
except Exception:
    _FFMPEG = 'ffmpeg'

_probe = os.path.join(os.path.dirname(_FFMPEG), 'ffprobe.exe')
_FFPROBE = _probe if os.path.exists(_probe) else _FFMPEG.replace('ffmpeg', 'ffprobe')

def get_ffmpeg():
    return _FFMPEG

def get_ffprobe():
    return _FFPROBE

NOWINDOW = 0x08000000 if sys.platform == 'win32' else 0

def get_duration(path):
    try:
        r = subprocess.run(
            [get_ffprobe(), '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', path],
            capture_output=True, encoding='utf-8', errors='replace', timeout=15, creationflags=NOWINDOW
        )
        return float(r.stdout.strip())
    except Exception:
        try:
            r = subprocess.run([get_ffmpeg(), '-i', path],
                               capture_output=True, encoding='utf-8', errors='replace', timeout=15, creationflags=NOWINDOW)
            m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
            if m:
                return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
        except Exception:
            pass
        return None

def extract_frame(path, t, height=None):
    """Verilen saniyedeki kareyi PIL Image olarak döndürür."""
    cmd = [get_ffmpeg(), '-ss', str(t), '-i', path, '-frames:v', '1']
    if height:
        cmd += ['-vf', f'scale=-2:{height}']
    cmd += ['-f', 'image2pipe', '-vcodec', 'png', '-']
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=10, creationflags=NOWINDOW)
        return Image.open(io.BytesIO(r.stdout)).convert('RGB')
    except Exception:
        return None

# Donanım kodlayıcıları: (ad, ffmpeg kodlayıcısı, bitrate ayarları). b = hedef kbps
HW_ENCODERS = [
    ('NVIDIA', 'h264_nvenc', lambda b: ['-preset', 'p4', '-tune', 'hq', '-rc', 'vbr', '-multipass', 'qres',
                                         '-b:v', f'{b}k', '-maxrate', f'{b*2}k', '-bufsize', f'{b*2}k']),
    ('AMD', 'h264_amf', lambda b: ['-quality', 'balanced', '-rc', 'vbr_peak',
                                   '-b:v', f'{b}k', '-maxrate', f'{b*2}k', '-bufsize', f'{b*2}k']),
    ('Intel', 'h264_qsv', lambda b: ['-preset', 'faster', '-b:v', f'{b}k', '-maxrate', f'{b*2}k',
                                     '-bufsize', f'{b*2}k']),
]

def detect_encoder():
    """Bu bilgisayarda gerçekten çalışan ilk donanım kodlayıcısını döndürür, yoksa None."""
    for enc in HW_ENCODERS:
        try:
            r = subprocess.run([get_ffmpeg(), '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
                                '-i', 'testsrc=size=640x360:rate=30', '-t', '0.5',
                                '-c:v', enc[1], '-f', 'null', '-'],
                               capture_output=True, timeout=15, creationflags=NOWINDOW)
            if r.returncode == 0:
                return enc
        except Exception:
            pass
    return None

def fmt(secs, tenths=False):
    whole = int(secs)
    h, r = divmod(whole, 3600)
    m, s = divmod(r, 60)
    out = f'{h:d}:{m:02d}:{s:02d}' if h else f'{m:02d}:{s:02d}'
    return f'{out}.{int((secs - whole) * 10)}' if tenths else out

# ---------------------------------------------------------------- tema
BG = '#0f1115'
CARD = '#171a21'
CARD2 = '#1f232c'
BORDER = '#2a2f3a'
TEXT = '#e8eaf0'
MUTED = '#8a91a1'
ACCENT = '#7c5cff'
ACCENT_HOVER = '#6a4cf0'
GREEN = '#22c55e'
RED = '#ef4444'
RED_HOVER = '#dc2626'

PREVIEW_W, PREVIEW_H = 820, 440
TL_W, TL_H = 820, 76
STRIP_Y, STRIP_H = 10, 56
THUMBS = 12
HANDLE_W = 12
MIN_GAP = 0.1

VIDEO_EXT = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.ts')
CANCELLED = 'İPTAL'

VERSION = '1.0.0'  # GitHub'daki otomatik derleme bunu sürüm etiketinden (v1.2.3) yazar
REPO = 'T0LGACS/Shrinkut'
EXE_NAME = 'Shrinkut.exe'


def parse_version(s):
    return tuple(int(x) for x in re.findall(r'\d+', s)[:3])


def latest_release():
    """GitHub'daki son sürümü (etiket, indirme adresi, bayt) olarak döndürür; .exe yoksa None."""
    req = urllib.request.Request(f'https://api.github.com/repos/{REPO}/releases/latest',
                                 headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Shrinkut'})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.load(r)
    for asset in data.get('assets', []):
        if asset['name'].lower() == EXE_NAME.lower():
            return data['tag_name'], asset['browser_download_url'], asset['size']
    return None


def ps_quote(s):
    return "'" + s.replace("'", "''") + "'"

ctk.set_appearance_mode('dark')

def resource(name):
    # .exe içinde dosyalar PyInstaller'ın geçici klasöründe (_MEIPASS) durur
    return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), name)


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.TkdndVersion = TkinterDnD._require(self)
        self.title('Shrinkut — Kes & Sıkıştır')
        self.iconbitmap(resource('icon.ico'))
        self.resizable(False, False)
        self._proc = None
        self._busy = False
        self._cancelled = False
        self.protocol('WM_DELETE_WINDOW', self._on_close)
        self._duration = 0.0
        self.start = 0.0
        self.end = 0.0
        self._drag = None
        self._frame_job = None
        self._frame_token = 0
        self._strip = None          # aydınlık kare şeridi
        self._strip_dark = None     # seçim dışı için karartılmış hali
        self._strip_photo = None
        self._photo = None
        self.var_input = tk.StringVar()
        self.var_outdir = tk.StringVar()
        self.var_mode = tk.StringVar(value='Kes (kayıpsız)')
        self.var_mb = tk.StringVar(value='490')
        self._encoder = None
        self._encoder_ready = threading.Event()
        self._build_ui()
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self._on_drop)
        threading.Thread(target=self._detect_encoder, daemon=True).start()
        if getattr(sys, 'frozen', False):  # sadece .exe kendini güncelleyebilir
            threading.Thread(target=self._check_update, daemon=True).start()

    # ------------------------------------------------------------------ güncelleme
    def _check_update(self):
        try:
            rel = latest_release()
        except Exception:
            return  # internet yok ya da GitHub'a ulaşılamadı: sessizce geç
        if rel and parse_version(rel[0]) > parse_version(VERSION):
            self.after(0, self._show_update, rel)

    def _show_update(self, rel):
        self._release = rel
        self.btn_update.configure(text=f'⬆  Güncelle ({rel[0]})')
        self.btn_update.grid()

    def _start_update(self):
        if self._busy:
            messagebox.showinfo('Güncelleme', 'Önce devam eden işlemi bitir ya da iptal et.')
            return
        self._busy = True
        self.btn_update.configure(state='disabled', text='⬇  İndiriliyor…')
        self.btn_run.configure(state='disabled')
        self.progress.configure(progress_color=GREEN)
        self._set_status(f'Yeni sürüm ({self._release[0]}) indiriliyor…')
        threading.Thread(target=self._download_update, daemon=True).start()

    def _download_update(self):
        _, url, size = self._release
        exe = sys.executable
        new = exe + '.new'
        try:
            with urllib.request.urlopen(url, timeout=30) as r, open(new, 'wb') as f:
                done = 0
                while chunk := r.read(1 << 16):
                    f.write(chunk)
                    done += len(chunk)
                    self.after(0, self._update_progress, min(int(done / size * 100), 99))
            with open(new, 'rb') as f:
                if os.path.getsize(new) != size or f.read(2) != b'MZ':
                    raise ValueError('İndirilen dosya eksik ya da bozuk.')
        except Exception as e:
            try:
                os.remove(new)
            except OSError:
                pass
            self.after(0, self._update_failed, str(e))
            return
        self.after(0, self._apply_update, exe, new)

    def _apply_update(self, exe, new):
        # Tek dosyalık .exe'de dosyayı tutan, bizi başlatan ana süreçtir (getppid); o kapanınca yerine geçir
        script = (f'Wait-Process -Id {os.getppid()} -ErrorAction SilentlyContinue; '
                  f'for ($i = 0; $i -lt 20; $i++) {{ try {{ Move-Item -LiteralPath {ps_quote(new)} '
                  f'-Destination {ps_quote(exe)} -Force -ErrorAction Stop; break }} '
                  f'catch {{ Start-Sleep -Milliseconds 500 }} }}; '
                  f'Start-Process -FilePath {ps_quote(exe)}')
        # bu değişken olmadan yeni .exe, eskisinin silinen geçici klasörünü kullanmaya çalışıp açılmaz
        env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
        subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', script],
                         creationflags=NOWINDOW, env=env)
        self._busy = False
        self.destroy()

    def _update_failed(self, err):
        self._busy = False
        self.btn_update.configure(state='normal', text=f'⬆  Güncelle ({self._release[0]})')
        self.btn_run.configure(state='normal')
        self.progress.configure(progress_color=CARD2)
        self.progress.set(0)
        self.lbl_pct.configure(text='')
        self.lbl_status.configure(text='Güncelleme indirilemedi.', text_color=RED)
        messagebox.showerror('Güncelleme', f'Güncelleme indirilemedi:\n{err}')

    def _on_drop(self, event):
        if self._busy:
            return
        files = self.tk.splitlist(event.data)  # boşluklu yollar {...} içinde gelir
        videos = [f for f in files if f.lower().endswith(VIDEO_EXT)]
        if videos:
            self.load(videos[0])
        else:
            messagebox.showwarning('Desteklenmeyen dosya', 'Lütfen bir video dosyası bırak.')

    def _on_close(self):
        if self._busy:
            proc = self._proc
            self._cancel()  # açık kalan FFmpeg arka planda çalışmaya devam etmesin
            if proc:
                proc.wait()
            try:
                os.remove(self._out_path)
            except OSError:
                pass
        self.destroy()

    def _detect_encoder(self):
        self._encoder = detect_encoder()
        self._encoder_ready.set()

    # ------------------------------------------------------------------ UI
    def _font(self, size=13, weight='normal'):
        return ctk.CTkFont(family='Segoe UI', size=size, weight=weight)

    def _card(self, row, pady=(0, 12)):
        f = ctk.CTkFrame(self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        f.grid(row=row, column=0, sticky='ew', padx=20, pady=pady)
        return f

    def _build_ui(self):
        # --- Üst başlık ---
        top = ctk.CTkFrame(self, fg_color='transparent')
        top.grid(row=0, column=0, sticky='ew', padx=20, pady=(18, 12))
        top.grid_columnconfigure(1, weight=1)
        logo = ctk.CTkImage(Image.open(resource('icon.ico')), size=(40, 40))
        ctk.CTkLabel(top, text='', image=logo).grid(row=0, column=0, rowspan=2, padx=(0, 12))
        ctk.CTkLabel(top, text='Shrinkut', font=self._font(22, 'bold'), text_color=TEXT
                     ).grid(row=0, column=1, sticky='w')
        self.lbl_file = ctk.CTkLabel(top, text='Kayıpsız kes, istediğin boyuta sıkıştır',
                                     font=self._font(12), text_color=MUTED)
        self.lbl_file.grid(row=1, column=1, sticky='w')
        self.btn_update = ctk.CTkButton(top, text='', command=self._start_update, height=40, corner_radius=10,
                                        fg_color=GREEN, hover_color='#16a34a', text_color='#06240f',
                                        font=self._font(13, 'bold'))
        self.btn_update.grid(row=0, column=2, rowspan=2, padx=(0, 10))
        self.btn_update.grid_remove()  # yeni sürüm bulunursa görünür
        ctk.CTkButton(top, text='📂  Video Seç', command=self._pick_input, width=140, height=40,
                      corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      font=self._font(14, 'bold')).grid(row=0, column=3, rowspan=2)

        # --- Önizleme ---
        prev = self._card(1)
        self.canvas = tk.Canvas(prev, width=PREVIEW_W, height=PREVIEW_H, bg='#0a0b0e',
                                highlightthickness=0, cursor='hand2')
        self.canvas.grid(row=0, column=0, padx=12, pady=(12, 8))
        self.canvas.bind('<Button-1>', lambda e: self._pick_input() if not self._duration else None)
        self._draw_placeholder()

        # --- Zaman çizelgesi ---
        self.tl = tk.Canvas(prev, width=TL_W, height=TL_H, bg=CARD, highlightthickness=0)
        self.tl.grid(row=1, column=0, padx=12)
        self.tl.bind('<ButtonPress-1>', self._tl_press)
        self.tl.bind('<B1-Motion>', self._tl_drag)
        self.tl.bind('<ButtonRelease-1>', lambda e: setattr(self, '_drag', None))
        self.tl.bind('<Motion>', self._tl_hover)

        info = ctk.CTkFrame(prev, fg_color='transparent')
        info.grid(row=2, column=0, sticky='ew', padx=14, pady=(6, 12))
        info.grid_columnconfigure(1, weight=1)
        self.lbl_start = ctk.CTkLabel(info, text='Başlangıç  00:00.0', font=self._font(13), text_color=MUTED)
        self.lbl_start.grid(row=0, column=0, sticky='w')
        self.lbl_len = ctk.CTkLabel(info, text='', font=self._font(13, 'bold'), text_color=TEXT)
        self.lbl_len.grid(row=0, column=1)
        self.lbl_end = ctk.CTkLabel(info, text='00:00.0  Bitiş', font=self._font(13), text_color=MUTED)
        self.lbl_end.grid(row=0, column=2, sticky='e')
        self._draw_timeline()

        # --- Ayarlar ---
        opts = self._card(2)
        opts.grid_columnconfigure(2, weight=1)
        ctk.CTkSegmentedButton(opts, values=['Kes (kayıpsız)', 'Sıkıştır'], variable=self.var_mode,
                               command=self._toggle_mode, height=36, font=self._font(13, 'bold'),
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               unselected_color=CARD2, fg_color=CARD2
                               ).grid(row=0, column=0, padx=14, pady=14)

        self.frm_mb = ctk.CTkFrame(opts, fg_color='transparent')
        self.frm_mb.grid(row=0, column=1, padx=(6, 0))
        ctk.CTkLabel(self.frm_mb, text='Hedef', font=self._font(13), text_color=MUTED).pack(side='left', padx=(0, 6))
        self.ent_mb = ctk.CTkEntry(self.frm_mb, textvariable=self.var_mb, width=64, height=32,
                                   justify='center', fg_color=CARD2, border_color=BORDER)
        self.ent_mb.pack(side='left')
        ctk.CTkLabel(self.frm_mb, text='MB', font=self._font(13), text_color=MUTED).pack(side='left', padx=(6, 10))
        for mb in ('10', '50', '490'):
            ctk.CTkButton(self.frm_mb, text=f'{mb}', width=44, height=28, corner_radius=8,
                          fg_color=CARD2, hover_color=BORDER, font=self._font(12),
                          command=lambda v=mb: self.var_mb.set(v)).pack(side='left', padx=2)

        self.btn_out = ctk.CTkButton(opts, text='📁  Çıktı: video ile aynı klasör', command=self._pick_outdir,
                                     height=32, corner_radius=8, fg_color=CARD2, hover_color=BORDER,
                                     font=self._font(12), text_color=MUTED, anchor='w')
        self.btn_out.grid(row=0, column=2, sticky='e', padx=14)

        # --- Başlat + ilerleme ---
        run = self._card(3, pady=(0, 20))
        run.grid_columnconfigure(1, weight=1)
        self.btn_run = ctk.CTkButton(run, text='▶  Başlat', command=self._run, width=150, height=44,
                                     corner_radius=10, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                     font=self._font(15, 'bold'))
        self.btn_run.grid(row=0, column=0, rowspan=2, padx=14, pady=14)
        self.lbl_status = ctk.CTkLabel(run, text='Bir video seçerek başla', font=self._font(13), text_color=MUTED)
        self.lbl_status.grid(row=0, column=1, sticky='sw', padx=(0, 10), pady=(12, 0))
        self.lbl_pct = ctk.CTkLabel(run, text='', font=self._font(20, 'bold'), text_color=GREEN)
        self.lbl_pct.grid(row=0, column=2, rowspan=2, padx=(0, 18))
        # boştayken progress_color=CARD2: 0'da görünen yeşil noktayı gizler
        self.progress = ctk.CTkProgressBar(run, height=10, corner_radius=5, fg_color=CARD2, progress_color=CARD2)
        self.progress.set(0)
        self.progress.grid(row=1, column=1, sticky='new', padx=(0, 10), pady=(6, 14))

        self._toggle_mode()

    def _toggle_mode(self, *_):
        state = 'normal' if self.var_mode.get() == 'Sıkıştır' else 'disabled'
        for w in self.frm_mb.winfo_children():
            w.configure(state=state)

    def _draw_placeholder(self):
        c = self.canvas
        c.delete('all')
        c.create_rectangle(24, 24, PREVIEW_W - 24, PREVIEW_H - 24, outline=BORDER, dash=(6, 4), width=2)
        c.create_text(PREVIEW_W // 2, PREVIEW_H // 2 - 18, text='🎞', fill=MUTED, font=('Segoe UI Emoji', 40))
        c.create_text(PREVIEW_W // 2, PREVIEW_H // 2 + 36, text='Videoyu buraya sürükle-bırak veya tıklayıp seç',
                      fill=MUTED, font=('Segoe UI', 13))

    # ------------------------------------------------------------------ dosya seç
    def _pick_input(self):
        path = filedialog.askopenfilename(
            filetypes=[('Video', '*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv'), ('Tümü', '*.*')]
        )
        if path:
            self.load(path)

    def load(self, path):
        self.var_input.set(path)
        self.lbl_file.configure(text=os.path.basename(path))
        self.lbl_status.configure(text='Video okunuyor…')
        threading.Thread(target=self._load_video, args=(path,), daemon=True).start()

    def _load_video(self, path):
        dur = get_duration(path)
        self.after(0, self._apply_duration, path, dur)

    def _apply_duration(self, path, dur):
        if not dur:
            self.lbl_status.configure(text='Video süresi okunamadı.')
            return
        self._duration = dur
        self.start, self.end = 0.0, dur
        self._strip = self._strip_dark = None
        self.lbl_status.configure(text=f'Toplam süre {fmt(dur)} — tutamaçları sürükleyerek kes')
        self._draw_timeline()
        self._request_frame(0)
        threading.Thread(target=self._load_strip, args=(path, dur), daemon=True).start()

    def _pick_outdir(self):
        d = filedialog.askdirectory()
        if d:
            self.var_outdir.set(d)
            self.btn_out.configure(text=f'📁  Çıktı: {self._short(d)}', text_color=TEXT)

    @staticmethod
    def _short(p, n=34):
        return p if len(p) <= n else '…' + p[-(n - 1):]

    # ------------------------------------------------------------------ kare şeridi
    def _load_strip(self, path, dur):
        w = TL_W // THUMBS
        strip = Image.new('RGB', (TL_W, STRIP_H), (10, 11, 14))
        with ThreadPoolExecutor(6) as pool:
            frames = pool.map(lambda i: extract_frame(path, dur * (i + 0.5) / THUMBS, height=STRIP_H),
                              range(THUMBS))
        for i, img in enumerate(frames):
            if img is None:
                continue
            # kareyi hücreye sığacak şekilde ortadan kırp
            x0 = max(0, (img.width - w) // 2)
            strip.paste(img.crop((x0, 0, x0 + w, STRIP_H)), (i * w, 0))
        self.after(0, self._apply_strip, path, strip)

    def _apply_strip(self, path, strip):
        if path != self.var_input.get():
            return
        self._strip = strip
        self._strip_dark = ImageEnhance.Brightness(strip).enhance(0.3)
        self._draw_timeline()

    # ------------------------------------------------------------------ zaman çizelgesi
    def _t2x(self, t):
        return HANDLE_W + (t / self._duration) * (TL_W - 2 * HANDLE_W) if self._duration else HANDLE_W

    def _x2t(self, x):
        frac = (x - HANDLE_W) / (TL_W - 2 * HANDLE_W)
        return max(0.0, min(1.0, frac)) * self._duration

    def _draw_timeline(self):
        c = self.tl
        c.delete('all')
        x1, x2 = self._t2x(self.start), self._t2x(self.end) if self._duration else TL_W - HANDLE_W
        y0, y1 = STRIP_Y, STRIP_Y + STRIP_H

        if self._strip is not None:
            img = self._strip_dark.copy()
            bx1, bx2 = int(x1), int(x2)
            img.paste(self._strip.crop((bx1, 0, bx2, STRIP_H)), (bx1, 0))
            self._strip_photo = ImageTk.PhotoImage(img)
            c.create_image(0, y0, anchor='nw', image=self._strip_photo)
        else:
            c.create_rectangle(0, y0, TL_W, y1, fill=CARD2, outline='')
            c.create_rectangle(x1, y0, x2, y1, fill='#262b36', outline='')

        # seçim çerçevesi + tutamaçlar
        c.create_rectangle(x1, y0 - 2, x2, y0 + 1, fill=ACCENT, outline='')
        c.create_rectangle(x1, y1 - 1, x2, y1 + 2, fill=ACCENT, outline='')
        for x, side in ((x1, -1), (x2, 1)):
            hx0, hx1 = (x - HANDLE_W, x) if side < 0 else (x, x + HANDLE_W)
            c.create_rectangle(hx0, y0 - 2, hx1, y1 + 2, fill=ACCENT, outline='')
            mid = (hx0 + hx1) / 2
            c.create_line(mid, y0 + 18, mid, y1 - 18, fill='white', width=2)

        dur = self.end - self.start
        self.lbl_start.configure(text=f'Başlangıç  {fmt(self.start, True)}')
        self.lbl_end.configure(text=f'{fmt(self.end, True)}  Bitiş')
        self.lbl_len.configure(text=f'Seçilen: {fmt(dur, True)}' if self._duration else '')

    def _tl_press(self, e):
        if not self._duration:
            return
        x1, x2 = self._t2x(self.start), self._t2x(self.end)
        # en yakın tutamacı tut
        self._drag = 'start' if abs(e.x - (x1 - HANDLE_W / 2)) <= abs(e.x - (x2 + HANDLE_W / 2)) else 'end'
        self._tl_drag(e)

    def _tl_drag(self, e):
        if not self._drag:
            return
        t = self._x2t(e.x)
        if self._drag == 'start':
            self.start = max(0.0, min(t, self.end - MIN_GAP))
            shown = self.start
        else:
            self.end = min(self._duration, max(t, self.start + MIN_GAP))
            shown = self.end
        self._draw_timeline()
        self._request_frame(shown, delay=120)

    def _tl_hover(self, e):
        if self._duration:
            x1, x2 = self._t2x(self.start), self._t2x(self.end)
            near = min(abs(e.x - x1), abs(e.x - x2)) < 24
            self.tl.configure(cursor='sb_h_double_arrow' if near else 'hand2')

    # ------------------------------------------------------------------ önizleme
    def _request_frame(self, t, delay=0):
        if self._frame_job:
            self.after_cancel(self._frame_job)
        self._frame_job = self.after(delay, self._start_frame, t)

    def _start_frame(self, t):
        self._frame_job = None
        self._frame_token += 1
        token, path = self._frame_token, self.var_input.get()
        threading.Thread(target=lambda: self.after(0, self._show_frame_img,
                         extract_frame(path, t, height=PREVIEW_H), t, token), daemon=True).start()

    def _show_frame_img(self, img, t, token):
        if img is None or token != self._frame_token:
            return  # eski istek, daha yenisi yolda
        img.thumbnail((PREVIEW_W, PREVIEW_H), Image.LANCZOS)
        bg = Image.new('RGB', (PREVIEW_W, PREVIEW_H), (10, 11, 14))
        bg.paste(img, ((PREVIEW_W - img.width) // 2, (PREVIEW_H - img.height) // 2))
        self._photo = ImageTk.PhotoImage(bg)
        c = self.canvas
        c.delete('all')
        c.create_image(0, 0, anchor='nw', image=self._photo)
        c.create_rectangle(14, 14, 110, 42, fill='#000000', outline='')
        c.create_text(62, 28, text=fmt(t, True), fill='white', font=('Segoe UI', 13, 'bold'))
        c.configure(cursor='arrow')

    # ------------------------------------------------------------------ işlem
    def _run(self):
        inp = self.var_input.get().strip()
        if not inp or not os.path.exists(inp) or not self._duration:
            messagebox.showerror('Hata', 'Önce bir video seç.')
            return
        outdir = self.var_outdir.get().strip() or os.path.dirname(inp)
        base = os.path.splitext(os.path.basename(inp))[0]

        if self.var_mode.get() == 'Sıkıştır':
            cmd = self._build_compress_cmd(inp, outdir, base)
        else:
            cmd = self._build_cut_cmd(inp, outdir, base)
        if cmd is None:
            return

        self._out_path = cmd[-1] if cmd != 'compress' else self._compress_params[1]
        self._busy, self._cancelled = True, False
        self.btn_run.configure(text='✖  İptal', fg_color=RED, hover_color=RED_HOVER, command=self._cancel)
        self.lbl_pct.configure(text='%0', text_color=GREEN)
        self._set_status('İşleniyor…')
        self.progress.configure(progress_color=GREEN)
        self.progress.set(0)
        threading.Thread(target=self._run_cmd, args=(cmd, self._clip_duration()), daemon=True).start()

    def _clip_duration(self):
        return self.end - self.start if self._duration > 0 else 0

    def _build_cut_cmd(self, inp, outdir, base):
        out = os.path.join(outdir, f'{base}_kesilmis.mp4')
        return [get_ffmpeg(), '-y',
                '-ss', str(self.start), '-i', inp,
                '-to', str(self.end - self.start),
                '-c', 'copy', out]

    def _build_compress_cmd(self, inp, outdir, base):
        try:
            target_mb = float(self.var_mb.get().replace(',', '.'))
            if target_mb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror('Hata', 'Hedef MB geçersiz.')
            return None
        out = os.path.join(outdir, f'{base}_kucultulmus.mp4')
        self._compress_params = (inp, out, target_mb, self.start, self.end)
        return 'compress'

    def _run_cmd(self, cmd, clip_dur):
        try:
            if cmd == 'compress':
                self._run_compress(clip_dur)
            else:
                self._run_with_progress(cmd, clip_dur)
        except FileNotFoundError:
            self._finish(False, 'FFmpeg bulunamadı.')
        except Exception as e:
            self._finish(False, str(e))

    def _ffmpeg(self, cmd, dur, lo=0, hi=100):
        """FFmpeg'i çalıştırır, ilerlemeyi lo..hi aralığında gösterir. Hata metnini döndürür."""
        # -progress çıktı adından önce olmalı, sonra yazılırsa FFmpeg yok sayar
        cmd = cmd[:-1] + ['-progress', 'pipe:2', '-nostats', cmd[-1]]
        if self._cancelled:
            return CANCELLED
        proc = self._proc = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            encoding='utf-8', errors='replace', creationflags=NOWINDOW
        )
        tail = []
        for line in proc.stderr:
            tail = (tail + [line])[-15:]
            m = re.search(r'out_time_us=(\d+)', line)
            if m and dur > 0:
                pct = lo + min(int(int(m.group(1)) / 1e6 / dur * (hi - lo)), hi - lo - 1)
                self.after(0, self._update_progress, pct)
        proc.wait()
        self._proc = None
        if self._cancelled:
            return CANCELLED
        return ''.join(tail) if proc.returncode != 0 else None

    def _cancel(self):
        self._cancelled = True
        proc = self._proc
        if proc and proc.poll() is None:
            proc.kill()

    def _run_with_progress(self, cmd, dur):
        err = self._ffmpeg(cmd, dur)
        self._finish(err is None, err or '')

    def _run_compress(self, clip_dur):
        inp, out, target_mb, start, end = self._compress_params
        dur = (end - start) if (end - start) > 0 else clip_dur
        base = [get_ffmpeg(), '-y', '-ss', str(start), '-i', inp, '-to', str(dur)]
        audio = ['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart']
        self._encoder_ready.wait()

        def encode(vkbps):
            if self._encoder:
                name, codec, opts = self._encoder
                self.after(0, self._set_status, f'{name} ekran kartıyla sıkıştırılıyor…')
                err = self._ffmpeg(base + ['-c:v', codec] + opts(vkbps) + audio + [out], dur)
                if err in (None, CANCELLED):
                    return err
                self._encoder = None  # GPU bu videoda başarısız oldu, bundan sonra işlemci
            self.after(0, self._set_status, 'İşlemciyle sıkıştırılıyor…')
            return self._x264_2pass(base, vkbps, audio, out, dur)

        vkbps = max(int(target_mb * 8192 / dur) - 128, 50)
        err = encode(vkbps)
        if err is None and os.path.getsize(out) / 1048576 > target_mb:
            # hedefi aştıysa aşma oranı kadar düşürüp bir kez daha dene (Discord limiti)
            over = os.path.getsize(out) / 1048576 / target_mb
            err = encode(max(int(vkbps / over * 0.97), 50))
        self._finish(err is None, err or '')

    def _x264_2pass(self, base, vkbps, audio, out, dur):
        null = 'NUL' if sys.platform == 'win32' else '/dev/null'
        log = os.path.join(tempfile.gettempdir(), f'shrinkut_2pass_{os.getpid()}')  # video klasörüne çöp bırakmasın
        video = ['-c:v', 'libx264', '-preset', 'faster', '-b:v', f'{vkbps}k', '-passlogfile', log]
        err = (self._ffmpeg(base + video + ['-pass', '1', '-an', '-f', 'null', null], dur, 0, 50)
               or self._ffmpeg(base + video + ['-pass', '2'] + audio + [out], dur, 50, 100))
        for ext in ('-0.log', '-0.log.mbtree'):
            try:
                os.remove(log + ext)
            except OSError:
                pass
        return err

    def _set_status(self, text):
        self._phase, self._t0 = text, time.time()
        self.lbl_status.configure(text=text, text_color=MUTED)

    def _update_progress(self, pct):
        self.progress.set(pct / 100)
        self.lbl_pct.configure(text=f'%{pct}')
        if pct >= 3:
            left = (time.time() - self._t0) / pct * (100 - pct)
            self.lbl_status.configure(text=f'{self._phase}   ·   kalan ~{fmt(left)}')

    def _finish(self, ok, err=''):
        self.after(0, self._finish_ui, ok, err)

    def _finish_ui(self, ok, err):
        self._busy = False
        self.btn_run.configure(text='▶  Başlat', fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._run)
        if err == CANCELLED:
            try:
                os.remove(self._out_path)  # yarım kalan dosya
            except OSError:
                pass
            self.progress.configure(progress_color=CARD2)
            self.progress.set(0)
            self.lbl_pct.configure(text='')
            self.lbl_status.configure(text='İptal edildi.', text_color=MUTED)
        elif ok:
            self.progress.set(1)
            self.lbl_pct.configure(text='%100')
            size = os.path.getsize(self._out_path) / 1024 / 1024
            self.lbl_status.configure(text=f'✔  Hazır: {os.path.basename(self._out_path)}  ({size:.1f} MB)',
                                      text_color=GREEN)
            subprocess.Popen(['explorer', '/select,', os.path.normpath(self._out_path)])
        else:
            self.progress.configure(progress_color='#ef4444')
            self.lbl_pct.configure(text='', text_color=GREEN)
            self.lbl_status.configure(text='Hata oluştu.', text_color='#ef4444')
            messagebox.showerror('FFmpeg Hatası', err[-800:] or 'Bilinmeyen hata.')


if __name__ == '__main__':
    app = App()
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app.load(sys.argv[1])  # .exe'nin üstüne video sürükleyip bırakınca açılır
    app.mainloop()
