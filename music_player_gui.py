"""
╔══════════════════════════════════════════════════════════════════╗
║         AETHER PLAYER  ✦  Pixel Dreamscape Edition  v2          ║
║   Drop-in replacement for music_player_gui.py                   ║
║                                                                  ║
║  FILES EXPECTED NEXT TO THIS SCRIPT:                            ║
║    default_cover.png   — album art / cover image                 ║
║    temp_song.mp3       — auto-used on launch (or search new)     ║
║    scene_*.jpg / *.png — optional pixel-art scene backgrounds    ║
║    (all your uploaded pixel images are auto-detected)            ║
║                                                                  ║
║  DEPENDENCIES:                                                   ║
║    pip install pygame Pillow yt-dlp                              ║
║    FFmpeg in C:\ffmpeg\bin  (change FFMPEG_PATH below if needed) ║
╚══════════════════════════════════════════════════════════════════╝
"""

import pygame
import subprocess
import os
import sys
import time
import math
import random
import threading
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# ═══════════════════════════════════════════════════════════
#  USER CONFIG  — edit these two lines if needed
# ═══════════════════════════════════════════════════════════
FFMPEG_PATH = r"C:\ffmpeg\bin"
WINDOW_W, WINDOW_H = 520, 760          # matches original compact window feel
FPS = 60

# ═══════════════════════════════════════════════════════════
#  COLOUR PALETTE  (mirrors IMPROVEMENTS.md palette exactly)
# ═══════════════════════════════════════════════════════════
C = {
    "bg_dark":       (10,  14,  39),      # #0A0E27
    "bg_secondary":  (26,  31,  58),      # #1A1F3A
    "accent_primary":(255,107,157),       # #FF6B9D  warm pink
    "accent_sec":    (0,  217, 255),      # #00D9FF  cyan
    "accent_tert":   (255,217, 61),       # #FFD93D  warm yellow
    "text_primary":  (232,232,255),       # #E8E8FF
    "text_secondary":(160,160,192),       # #A0A0C0
    "border":        (45,  47,  79),      # #2D2F4F
    # glass variants (RGBA)
    "glass":         (26,  31,  58, 180),
    "glass_light":   (45,  50,  90, 140),
    "glass_dark":    (10,  14,  39, 210),
    "overlay":       ( 0,   0,   0, 150),
}

LOOP_LABELS  = ["∞", "×1", "×3", "×5", "×10"]
LOOP_COUNTS  = [-1,   1,   3,   5,   10]

# ═══════════════════════════════════════════════════════════
#  SCENE DEFINITIONS  (key → candidate filenames to search)
# ═══════════════════════════════════════════════════════════
SCENE_MAP = [
    ("galaxy",    ["scene_galaxy",   "download__16_"],             "✦ Galaxy Night",    (255,207,255), "star"),
    ("fantasy",   ["scene_fantasy",  "Dark_Fantasy_Pixel_Art"],    "⚔ Dark Fantasy",   (255,210, 80), "ember"),
    ("japan",     ["scene_japan",    "Pixel_japan"],               "⛩ Cherry Blossom", (255,180,200), "petal"),
    ("lotus",     ["scene_lotus",    "pixel"],                     "❀ Lotus Pond",     (100,220,160), "petal"),
    ("flowers",   ["scene_flowers",  "Would_be_a_cool_cross_stitch","download__10_"],  "✿ Water Lilies",(255,180,220),"petal"),
    ("koi",       ["scene_koi",      "download__13_"],             "鯉 Koi Garden",    (100,220,255), "petal"),
    ("mercedes",  ["scene_mercedes", "download__14_"],             "◈ Night Drive",    (100,180,255), "dust"),
    ("starry",    ["scene_starry",   "download__11_"],             "★ Starry Night",   (255,220,120), "star"),
]

DEMO_LYRICS = [
    "✦  drifting through the pixel sky  ✦",
    "where ancient stars remember",
    "a melody half-forgotten",
    "like rain on distant cobblestones",
    "the night breathes softly here",
    "beneath the painted heavens",
    "we found this moment, whole",
    "♫  let the song carry you  ♫",
    "pixels hold the feelings",
    "that words cannot contain",
]

# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════

def lerp(a, b, t):   return a + (b-a)*t
def clamp(v,lo,hi):  return max(lo, min(hi, v))
def fmt_time(s):
    s = max(0, int(s))
    return f"{s//60:02d}:{s%60:02d}"
def truncate(t, n=38):
    return t[:n]+"…" if len(t)>n else t

def pil_to_surf(img):
    img = img.convert("RGBA")
    return pygame.image.fromstring(img.tobytes(), img.size, "RGBA")

def load_bg(path, w=WINDOW_W, h=WINDOW_H):
    try:
        img = Image.open(path).convert("RGB").resize((w,h), Image.LANCZOS)
        img = ImageEnhance.Brightness(img).enhance(0.60)
        img = ImageEnhance.Color(img).enhance(1.15)
        return pil_to_surf(img)
    except Exception as e:
        print("load_bg:", e)
        return None

def make_gradient(c1, c2, w=WINDOW_W, h=WINDOW_H):
    surf = pygame.Surface((w,h))
    for y in range(h):
        t = y/h
        r=int(lerp(c1[0],c2[0],t)); g=int(lerp(c1[1],c2[1],t)); b=int(lerp(c1[2],c2[2],t))
        pygame.draw.line(surf,(r,g,b),(0,y),(w,y))
    return surf

def glass_rect(surf, rect, fill_rgba, border_rgba=None, radius=10):
    x,y,w,h = rect
    s = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.rect(s, fill_rgba, (0,0,w,h), border_radius=radius)
    if border_rgba:
        pygame.draw.rect(s, border_rgba, (0,0,w,h), width=1, border_radius=radius)
    surf.blit(s,(x,y))

def draw_text_c(surf, text, font, cy, color, alpha=255, glow_col=None):
    t = font.render(text, True, color)
    if alpha < 255: t.set_alpha(alpha)
    rx = WINDOW_W//2 - t.get_width()//2
    if glow_col:
        g = font.render(text, True, glow_col)
        g.set_alpha(min(alpha, 60))
        for dx,dy in ((-2,0),(2,0),(0,-2),(0,2)):
            surf.blit(g,(rx+dx,cy+dy))
    surf.blit(t,(rx,cy))

def get_duration(path):
    try:   return pygame.mixer.Sound(path).get_length()
    except:return 0

def search_songs(query, n=5):
    cmd=["yt-dlp","--print","%(title)s ||| %(id)s",f"ytsearch{n}:{query}"]
    res=subprocess.run(cmd,capture_output=True,text=True)
    songs=[]
    if res.returncode==0:
        for line in res.stdout.strip().split('\n'):
            if "|||" in line:
                t,vid=line.split("|||",1)
                songs.append((t.strip(),vid.strip()))
    return songs

def download_song(video_id, on_status=None):
    try: pygame.mixer.music.unload()
    except: pass
    for f in os.listdir("."):
        if f.startswith("temp_song."):
            try: os.remove(f)
            except: pass
    cmd=["yt-dlp","-f","bestaudio","--extract-audio","--audio-format","mp3",
         "--ffmpeg-location",FFMPEG_PATH,"-o","temp_song.%(ext)s",
         f"https://www.youtube.com/watch?v={video_id}"]
    if on_status: on_status("Downloading…")
    subprocess.run(cmd,capture_output=True,text=True)
    return "temp_song.mp3" if os.path.exists("temp_song.mp3") else None

# ═══════════════════════════════════════════════════════════
#  PARTICLE
# ═══════════════════════════════════════════════════════════
class Particle:
    def __init__(self, ptype, accent):
        self.ptype  = ptype
        self.accent = accent
        self._spawn()

    def _spawn(self):
        pt = self.ptype
        if pt == "star":
            self.x=random.uniform(0,WINDOW_W); self.y=random.uniform(0,WINDOW_H)
            self.vx=random.uniform(-0.08,0.08); self.vy=random.uniform(-0.25,-0.04)
            self.r=random.choice([1,1,1,2]); self.alpha=random.randint(60,200)
            self.col=random.choice([(255,255,255),(180,200,255),(255,215,100),(100,220,255)])
        elif pt == "petal":
            self.x=random.uniform(0,WINDOW_W); self.y=random.uniform(-20,WINDOW_H)
            self.vx=random.uniform(-0.5,0.5); self.vy=random.uniform(0.2,0.7)
            self.r=random.randint(2,5); self.alpha=random.randint(120,200)
            self.col=self.accent
            self.rot=random.uniform(0,360); self.drot=random.uniform(-1.5,1.5)
        elif pt == "ember":
            self.x=random.uniform(0,WINDOW_W); self.y=random.uniform(0,WINDOW_H)
            self.vx=random.uniform(-0.2,0.2); self.vy=random.uniform(-0.5,-0.1)
            self.r=1; self.alpha=random.randint(60,160)
            self.col=random.choice([(255,200,80),(255,160,40),(255,240,150)])
        else:  # dust
            self.x=random.uniform(0,WINDOW_W); self.y=random.uniform(0,WINDOW_H)
            self.vx=random.uniform(-0.05,0.05); self.vy=random.uniform(-0.15,0.15)
            self.r=1; self.alpha=random.randint(30,100); self.col=self.accent

    def update(self):
        self.x+=self.vx; self.y+=self.vy
        if self.ptype=="star":
            self.alpha+=random.randint(-3,3)
            self.alpha=clamp(self.alpha,40,210)
        if hasattr(self,'drot'): self.rot+=self.drot
        # wrap
        if self.y<-20: self.y=WINDOW_H+5; self.x=random.uniform(0,WINDOW_W)
        if self.y>WINDOW_H+20: self.y=-5; self.x=random.uniform(0,WINDOW_W)
        if self.x<-10: self.x=WINDOW_W+5
        if self.x>WINDOW_W+10: self.x=-5

    def draw(self, surf):
        a=clamp(int(self.alpha),0,255)
        col=self.col+(a,)
        sz=self.r*2+6
        s=pygame.Surface((sz,sz),pygame.SRCALPHA)
        cx=sz//2
        if self.ptype=="petal":
            pygame.draw.ellipse(s,col,(2,2,self.r*2,max(self.r,2)))
        elif self.ptype=="star" and self.r>=2:
            pygame.draw.circle(s,col,(cx,cx),self.r)
            g=self.col+(a//5,)
            pygame.draw.circle(s,g,(cx,cx),self.r+3)
        else:
            pygame.draw.circle(s,col,(cx,cx),self.r)
        surf.blit(s,(int(self.x)-cx,int(self.y)-cx))

# ═══════════════════════════════════════════════════════════
#  LYRICS ENGINE
# ═══════════════════════════════════════════════════════════
class Lyrics:
    def __init__(self):
        self.lines=[]; self.idx=0; self.alpha=0.0
        self.fade_in=True; self.timer=0; self.interval=4.5

    def set(self, lines, interval=4.5):
        self.lines=lines; self.idx=0; self.alpha=0.0
        self.fade_in=True; self.timer=0; self.interval=interval

    def update(self, dt):
        if not self.lines: return
        self.timer+=dt
        speed=280
        if self.fade_in:
            self.alpha=clamp(self.alpha+speed*dt,0,210)
        else:
            self.alpha=clamp(self.alpha-speed*dt,0,210)
            if self.alpha<=0:
                self.idx=(self.idx+1)%len(self.lines)
                self.fade_in=True
        if self.timer>=self.interval:
            self.timer=0; self.fade_in=False

    def line(self):
        if not self.lines: return ""
        return self.lines[self.idx%len(self.lines)]

# ═══════════════════════════════════════════════════════════
#  WAVEFORM
# ═══════════════════════════════════════════════════════════
class Waveform:
    def __init__(self, n=28):
        self.n=n
        self.h=[random.uniform(0.05,0.2) for _ in range(n)]
        self.tgt=[random.uniform(0.05,0.2) for _ in range(n)]
        self.playing=False

    def update(self, dt):
        for i in range(self.n):
            if self.playing:
                if random.random()<0.10:
                    self.tgt[i]=random.uniform(0.05,0.90)
            else:
                self.tgt[i]=random.uniform(0.02,0.07)
            self.h[i]=lerp(self.h[i],self.tgt[i],7*dt)

    def draw(self, surf, cx, cy, width, height, accent):
        bw=max(2, width//(self.n*2))
        gap=bw
        x=cx-width//2
        for i,hv in enumerate(self.h):
            bh=max(1,int(hv*height))
            bx=x+i*(bw+gap)
            by=cy-bh
            a=clamp(int(100+120*hv),0,220)
            col=accent+(a,)
            s=pygame.Surface((bw,bh+1),pygame.SRCALPHA)
            s.fill(col)
            surf.blit(s,(bx,by))

# ═══════════════════════════════════════════════════════════
#  COVER ART DISPLAY
# ═══════════════════════════════════════════════════════════
class CoverArt:
    """Loads default_cover.png, shows it with a pixel-border glow."""
    def __init__(self, script_dir):
        self.surf = None
        path = os.path.join(script_dir, "default_cover.png")
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA").resize((180,180), Image.LANCZOS)
                self.surf = pil_to_surf(img)
            except Exception as e:
                print("CoverArt:", e)
        self.angle = 0.0     # slow spin when playing
        self.scale = 1.0
        self.tgt_scale = 1.0

    def update(self, dt, playing):
        if playing:
            self.angle = (self.angle + 4*dt) % 360
            self.tgt_scale = 1.0
        else:
            self.tgt_scale = 0.95
        self.scale = lerp(self.scale, self.tgt_scale, 5*dt)

    def draw(self, surf, cx, cy, accent, playing):
        size = int(180 * self.scale)
        if size < 1: return
        bx = cx - size//2 - 4
        by = cy - size//2 - 4
        # Outer glow border (pixel-art sharp corners)
        pulse = 0.6 + 0.4*math.sin(time.time()*1.8)
        border_a = int(pulse * 200)
        glass_rect(surf, (bx-2, by-2, size+12, size+12),
                   C["bg_secondary"]+(200,), accent+(border_a,), radius=3)
        if self.surf:
            s = pygame.transform.scale(self.surf, (size, size))
            surf.blit(s, (bx+2, by+2))
        else:
            # Fallback: musical notes
            glass_rect(surf, (bx+2,by+2,size,size), C["bg_secondary"]+(255,), radius=2)
            placeholder = pygame.font.SysFont("Courier New", 48).render("♫", True, accent)
            surf.blit(placeholder, (cx-placeholder.get_width()//2, cy-placeholder.get_height()//2))

# ═══════════════════════════════════════════════════════════
#  SEARCH OVERLAY  (in-window, no Tkinter dialogs)
# ═══════════════════════════════════════════════════════════
class SearchOverlay:
    def __init__(self):
        self.active=False; self.mode="input"
        self.query=""; self.results=[]; self.sel=0
        self.cursor=True; self.cursor_t=0; self.status=""
        self.callback=None

    def open(self, cb):
        self.active=True; self.mode="input"; self.query=""
        self.results=[]; self.sel=0; self.status=""; self.callback=cb

    def close(self): self.active=False

    def handle(self, ev):
        if not self.active: return False
        if self.mode=="input" and ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.close()
            elif ev.key==pygame.K_RETURN and self.query.strip(): self._search()
            elif ev.key==pygame.K_BACKSPACE: self.query=self.query[:-1]
            elif ev.unicode and ord(ev.unicode)>=32: self.query+=ev.unicode
        elif self.mode=="results" and ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: self.mode="input"
            elif ev.key in(pygame.K_UP,pygame.K_w): self.sel=max(0,self.sel-1)
            elif ev.key in(pygame.K_DOWN,pygame.K_s): self.sel=min(len(self.results)-1,self.sel+1)
            elif ev.key==pygame.K_RETURN: self._confirm()
        elif self.mode=="results" and ev.type==pygame.MOUSEBUTTONDOWN:
            mx,my=ev.pos
            sy=WINDOW_H//2-120
            for i in range(len(self.results)):
                ry=sy+i*42
                if WINDOW_W//2-220<=mx<=WINDOW_W//2+220 and ry<=my<=ry+38:
                    self.sel=i; self._confirm(); return True
        return True

    def _search(self):
        self.mode="loading"; self.status=f'Searching "{self.query}"…'
        def run():
            r=search_songs(self.query,5)
            self.results=r; self.mode="results" if r else "input"
            if not r: self.status="No results found."
        threading.Thread(target=run,daemon=True).start()

    def _confirm(self):
        if self.results and 0<=self.sel<len(self.results):
            t,v=self.results[self.sel]
            self.close()
            if self.callback: self.callback(t,v)

    def update(self, dt):
        self.cursor_t+=dt
        if self.cursor_t>0.5: self.cursor=not self.cursor; self.cursor_t=0

    def draw(self, surf, fb, fm, fs):
        if not self.active: return
        dim=pygame.Surface((WINDOW_W,WINDOW_H),pygame.SRCALPHA); dim.fill((0,0,0,190)); surf.blit(dim,(0,0))
        bw,bh=460,380; bx=WINDOW_W//2-bw//2; by=WINDOW_H//2-bh//2
        glass_rect(surf,(bx,by,bw,bh),C["glass_dark"],C["border"]+(200,),radius=12)
        draw_text_c(surf,"⊞  SEARCH & LOAD",fb,by+18,C["accent_sec"])
        if self.mode=="input":
            draw_text_c(surf,"Type song name → Enter",fs,by+52,C["text_secondary"])
            ibx=bx+30; iby=by+78; ibw=bw-60; ibh=46
            glass_rect(surf,(ibx,iby,ibw,ibh),(255,255,255,18),C["accent_sec"]+(140,),radius=6)
            q=self.query+("|" if self.cursor else " ")
            t=fm.render(q,True,C["text_primary"]); surf.blit(t,(ibx+14,iby+12))
            if self.status:
                st=fs.render(self.status,True,C["accent_tert"])
                surf.blit(st,(WINDOW_W//2-st.get_width()//2,by+142))
            hint=fs.render("Esc to close",True,C["text_secondary"])
            surf.blit(hint,(WINDOW_W//2-hint.get_width()//2,by+bh-30))
        elif self.mode=="loading":
            draw_text_c(surf,self.status,fm,WINDOW_H//2-14,C["accent_sec"])
        elif self.mode=="results":
            draw_text_c(surf,f'Results: "{truncate(self.query,28)}"',fs,by+52,C["text_secondary"])
            sy=by+76
            for i,(title,_) in enumerate(self.results):
                ry=sy+i*42
                sel=i==self.sel
                bg=(80,120,220,130) if sel else (30,38,80,90)
                glass_rect(surf,(bx+18,ry,bw-36,36),bg,radius=5)
                tc=C["text_primary"] if sel else C["text_secondary"]
                t=fs.render(f"{i+1}.  {truncate(title,48)}",True,tc); surf.blit(t,(bx+30,ry+9))
            draw_text_c(surf,"↑↓  navigate    Enter / click  select    Esc  back",fs,by+bh-30,C["text_secondary"])

# ═══════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════
class AetherPlayer:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100,size=-16,channels=2,buffer=2048)
        pygame.mixer.music.set_volume(0.8)
        pygame.display.set_caption("Aether Player  ✦  Pixel Dreamscape")
        self.screen = pygame.display.set_mode((WINDOW_W,WINDOW_H))
        self.clock  = pygame.time.Clock()
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        self._init_fonts()
        self._init_scenes()
        self._init_particles()

        self.cover  = CoverArt(self.script_dir)
        self.lyrics = Lyrics()
        self.wave   = Waveform(24)
        self.search = SearchOverlay()

        # ── playback state (mirrors original globals) ──
        self.current_file  = None
        self.song_title    = "No Song Loaded"
        self.song_duration = 0
        self.current_pos   = 0.0
        self.playback_start= None
        self.paused        = False
        self.is_dragging   = False
        self.vol           = 0.8

        # loop
        self.loop_idx   = 0
        self.loop_count = 0

        # status
        self.status_text  = "Search for a song to begin"
        self.status_alpha = 200
        self.status_timer = 0

        # scene transition
        self.prev_bg   = None
        self.trans_t   = 1.0

        # animation
        self.breath_t  = 0.0
        self.hover_btn = None

        # dragging flags
        self.prog_drag = False
        self.vol_drag  = False

        # scene panel
        self.scene_open  = False
        self.scene_panel_y = WINDOW_H + 20

        # try to auto-load temp_song.mp3 if it exists
        tmp = os.path.join(self.script_dir, "temp_song.mp3")
        if os.path.exists(tmp):
            self.current_file  = tmp
            self.song_title    = "temp_song  (search to change)"
            self.song_duration = get_duration(tmp)
            self.status_text   = "Ready — press ▶ to play"
            self.status_alpha  = 220

        self._build_ui()

    # ── INIT HELPERS ───────────────────────────────────────

    def _init_fonts(self):
        fc = "Courier New"
        try: pygame.font.SysFont(fc,12)
        except: fc = pygame.font.get_default_font()
        self.f_header = pygame.font.SysFont(fc, 17, bold=True)
        self.f_title  = pygame.font.SysFont(fc, 15, bold=True)
        self.f_big    = pygame.font.SysFont(fc, 16, bold=True)
        self.f_med    = pygame.font.SysFont(fc, 14)
        self.f_sm     = pygame.font.SysFont(fc, 12)
        self.f_xs     = pygame.font.SysFont(fc, 10)
        self.f_lyric  = pygame.font.SysFont(fc, 15, italic=True)

    def _init_scenes(self):
        ext = [".jpg",".jpeg",".png",".webp"]
        self.scenes = []   # list of (key, label, accent_rgb, surf)
        for key, cands, label, accent, ptype in SCENE_MAP:
            surf = None
            for cand in cands:
                for e in ext:
                    p=os.path.join(self.script_dir, cand+e)
                    if os.path.exists(p):
                        surf=load_bg(p); break
                if surf: break
            if surf:
                self.scenes.append((key, label, accent, ptype, surf))
        # auto-detect any other images
        known = {c for _,cands,*_ in SCENE_MAP for c in cands}
        for f in os.listdir(self.script_dir):
            nm,ex=os.path.splitext(f.lower())
            if ex in ext and nm not in known and nm not in [s[0] for s in self.scenes]:
                p=os.path.join(self.script_dir,f)
                surf=load_bg(p)
                if surf:
                    self.scenes.append((nm,f"⊞ {nm.title()}",(180,180,255),"star",surf))
        # fallback gradient
        if not self.scenes:
            self.scenes=[("void","✦ Void Night",(180,160,255),"star",
                          make_gradient((10,14,39),(20,30,70)))]
        self.scene_idx    = 0
        self.bg           = self.scenes[0][4]
        self.cur_ptype    = self.scenes[0][3]
        self.cur_accent   = self.scenes[0][2]
        self.prev_bg      = None

    def _init_particles(self):
        self.particles = [Particle(self.cur_ptype, self.cur_accent) for _ in range(70)]

    def _build_ui(self):
        W,H=WINDOW_W,WINDOW_H
        cx=W//2
        # cover art centre
        self.cover_cy = 200
        # progress bar
        self.prog_x  = 30;  self.prog_w = W-60
        self.prog_y  = H-190; self.prog_h = 5
        # buttons row  (⏮  ▶/⏸  ⏹  ⏭)
        by = H-150
        self.btns = {
            "loop":   pygame.Rect(cx-195, by, 38,38),
            "prev":   pygame.Rect(cx-110, by, 40,40),
            "play":   pygame.Rect(cx- 24, by, 48,48),
            "stop":   pygame.Rect(cx+ 78, by, 40,40),
            "next":   pygame.Rect(cx+120, by, 40,40),
            "search": pygame.Rect(cx+162, by, 38,38),
        }
        # volume
        self.vol_x=30; self.vol_y=H-90; self.vol_w=120
        # scene button
        self.scene_btn=pygame.Rect(W-52,10,42,26)

    # ── SCENE SWITCH ───────────────────────────────────────

    def switch_scene(self, idx):
        if idx==self.scene_idx: return
        self.prev_bg   = self.bg
        self.scene_idx = idx % len(self.scenes)
        _,_,acc,pt,surf = self.scenes[self.scene_idx]
        self.bg        = surf
        self.cur_accent= acc
        self.cur_ptype = pt
        self.trans_t   = 0.0
        for p in self.particles:
            p.ptype=pt; p.accent=acc; p._spawn()
        self.scene_open=False

    # ── PLAYBACK ───────────────────────────────────────────

    def _pos(self):
        if self.playback_start and pygame.mixer.music.get_busy() and not self.paused:
            return self.current_pos+(time.time()-self.playback_start)
        return self.current_pos

    def play(self, start=None):
        if not self.current_file: return
        if start is None: start=self.current_pos
        try:
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play(start=start)
            self.current_pos=start; self.playback_start=time.time()
            self.paused=False; self.wave.playing=True
            self._status("Playing")
        except Exception as e:
            self._status(f"Error: {e}")

    def pause(self):
        if pygame.mixer.music.get_busy() and not self.paused:
            pygame.mixer.music.pause()
            self.current_pos=self._pos(); self.playback_start=None
            self.paused=True; self.wave.playing=False; self._status("Paused")

    def resume(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.playback_start=time.time()
            self.paused=False; self.wave.playing=True; self._status("Playing")

    def stop(self):
        pygame.mixer.music.stop()
        try: pygame.mixer.music.unload()
        except: pass
        self.current_pos=0; self.playback_start=None
        self.paused=False; self.wave.playing=False; self._status("Stopped")

    def toggle(self):
        if not self.current_file: self.search.open(self._on_chosen); return
        if pygame.mixer.music.get_busy() and not self.paused: self.pause()
        elif self.paused: self.resume()
        else: self.play(0)

    def skip_fwd(self):  self.play(min(self._pos()+10, self.song_duration-0.5))
    def skip_back(self): self.play(max(self._pos()-10, 0))

    def _status(self, msg, dur=3.0):
        self.status_text=msg; self.status_alpha=230; self.status_timer=dur

    def _on_chosen(self, title, video_id):
        def run():
            self._status("Downloading…", 60)
            path=download_song(video_id, self._status)
            if path:
                self.current_file=path; self.song_title=title
                self.song_duration=get_duration(path)
                self.current_pos=0; self.loop_count=0
                self.lyrics.set(DEMO_LYRICS, 5.0)
                self.play(0)
        threading.Thread(target=run,daemon=True).start()

    # ── EVENTS ─────────────────────────────────────────────

    def handle_events(self):
        mx,my=pygame.mouse.get_pos()
        self.hover_btn=None
        for n,r in self.btns.items():
            if r.collidepoint(mx,my): self.hover_btn=n; break

        for ev in pygame.event.get():
            if ev.type==pygame.QUIT: return False
            if self.search.handle(ev): continue
            if ev.type==pygame.KEYDOWN: self._key(ev)
            if ev.type==pygame.MOUSEBUTTONDOWN: self._click(ev)
            if ev.type==pygame.MOUSEBUTTONUP:
                self.prog_drag=False; self.vol_drag=False
            if ev.type==pygame.MOUSEMOTION: self._drag(ev)
        return True

    def _key(self,ev):
        k=ev.key
        if k==pygame.K_SPACE:   self.toggle()
        elif k==pygame.K_RIGHT: self.skip_fwd()
        elif k==pygame.K_LEFT:  self.skip_back()
        elif k==pygame.K_l:     self.loop_idx=(self.loop_idx+1)%len(LOOP_LABELS)
        elif k==pygame.K_s:     self.search.open(self._on_chosen)
        elif k==pygame.K_TAB:   self.switch_scene((self.scene_idx+1)%len(self.scenes))
        elif k==pygame.K_ESCAPE:self.scene_open=False

    def _click(self,ev):
        mx,my=ev.pos
        # buttons
        if self.btns["play"].collidepoint(mx,my):   self.toggle()
        elif self.btns["prev"].collidepoint(mx,my): self.skip_back()
        elif self.btns["next"].collidepoint(mx,my): self.skip_fwd()
        elif self.btns["stop"].collidepoint(mx,my): self.stop()
        elif self.btns["loop"].collidepoint(mx,my):
            self.loop_idx=(self.loop_idx+1)%len(LOOP_LABELS)
        elif self.btns["search"].collidepoint(mx,my):
            self.search.open(self._on_chosen)
        elif self.scene_btn.collidepoint(mx,my):
            self.scene_open=not self.scene_open
        # scene panel
        elif self.scene_open:
            py=int(self.scene_panel_y)
            for i,(_,lbl,*_) in enumerate(self.scenes):
                ry=py+8+i*36
                if WINDOW_W-210<=mx<=WINDOW_W-10 and ry<=my<=ry+30:
                    self.switch_scene(i); break
        # progress
        px,py2=self.prog_x,self.prog_y
        if px<=mx<=px+self.prog_w and py2-8<=my<=py2+12:
            if self.song_duration>0:
                r=clamp((mx-px)/self.prog_w,0,1)
                self.current_pos=r*self.song_duration; self.play(self.current_pos)
            self.prog_drag=True
        # volume
        vx,vy=self.vol_x,self.vol_y
        if vx<=mx<=vx+self.vol_w and vy-8<=my<=vy+12:
            self.vol=clamp((mx-vx)/self.vol_w,0,1)
            pygame.mixer.music.set_volume(self.vol); self.vol_drag=True

    def _drag(self,ev):
        mx,my=ev.pos
        if self.prog_drag and self.song_duration>0:
            r=clamp((mx-self.prog_x)/self.prog_w,0,1)
            self.current_pos=r*self.song_duration; self.play(self.current_pos)
        if self.vol_drag:
            self.vol=clamp((mx-self.vol_x)/self.vol_w,0,1)
            pygame.mixer.music.set_volume(self.vol)

    # ── UPDATE ─────────────────────────────────────────────

    def update(self, dt):
        self.breath_t+=dt
        if self.trans_t<1.0: self.trans_t=min(1.0,self.trans_t+dt*1.4)
        for p in self.particles: p.update()
        self.lyrics.update(dt)
        self.wave.update(dt)
        playing=pygame.mixer.music.get_busy() and not self.paused
        self.cover.update(dt, playing)
        if self.status_timer>0: self.status_timer-=dt
        else: self.status_alpha=max(0,self.status_alpha-100*dt)
        # song end
        pos=self._pos()
        if (self.current_file and not self.paused
                and not pygame.mixer.music.get_busy() and pos>1):
            self._handle_end()
        # scene panel slide
        ty = WINDOW_H-20-len(self.scenes)*36-16 if self.scene_open else WINDOW_H+20
        self.scene_panel_y=lerp(self.scene_panel_y,ty,8*dt)

    def _handle_end(self):
        lc=LOOP_COUNTS[self.loop_idx]
        if lc==-1: self.play(0)
        elif lc==1: self.stop(); self.current_pos=0
        else:
            self.loop_count+=1
            if self.loop_count<lc: self.play(0)
            else: self.loop_count=0; self.stop()

    # ── DRAW ───────────────────────────────────────────────

    def draw(self):
        # background + transition
        if self.trans_t<1.0 and self.prev_bg:
            self.screen.blit(self.prev_bg,(0,0))
            tmp=self.bg.copy(); tmp.set_alpha(int(self.trans_t*255))
            self.screen.blit(tmp,(0,0))
        else:
            self.screen.blit(self.bg,(0,0))

        # vignette
        vig=pygame.Surface((WINDOW_W,WINDOW_H),pygame.SRCALPHA)
        for i in range(80):
            a=int((i/80)**1.8 * 160)
            m=i*3
            if WINDOW_W-m*2>0 and WINDOW_H-m*2>0:
                pygame.draw.rect(vig,(0,0,0,a),(m,m,WINDOW_W-m*2,WINDOW_H-m*2),width=4)
        self.screen.blit(vig,(0,0))

        # particles
        ps=pygame.Surface((WINDOW_W,WINDOW_H),pygame.SRCALPHA)
        for p in self.particles: p.draw(ps)
        self.screen.blit(ps,(0,0))

        acc=self.cur_accent

        # ── header ──
        glass_rect(self.screen,(WINDOW_W//2-200,8,400,36),
                   C["glass"],C["border"]+(120,),radius=6)
        draw_text_c(self.screen,"⊞  AETHER PLAYER  ⊞",self.f_header,14,
                    C["accent_primary"],glow_col=C["accent_primary"])

        # ── cover art ──
        self.cover.draw(self.screen, WINDOW_W//2, self.cover_cy, acc,
                        pygame.mixer.music.get_busy() and not self.paused)

        # ── song title ──
        pulse=0.7+0.3*math.sin(self.breath_t*1.5)
        glow=tuple(int(c*pulse) for c in acc)
        draw_text_c(self.screen, truncate(self.song_title,38),
                    self.f_title, self.cover_cy+102, C["text_primary"],
                    glow_col=glow)

        # ── status ──
        if self.status_alpha>5:
            draw_text_c(self.screen,self.status_text,self.f_xs,
                        self.cover_cy+122,C["text_secondary"],int(self.status_alpha))

        # ── lyrics ──
        if self.lyrics.lines:
            draw_text_c(self.screen,self.lyrics.line(),self.f_lyric,
                        WINDOW_H//2-10,C["text_primary"],int(self.lyrics.alpha),glow_col=acc)

        # ── waveform ──
        self.wave.draw(self.screen,WINDOW_W//2,self.prog_y-30,
                       WINDOW_W-80,36,acc)

        # ── control panel ──
        panel_y=self.prog_y-18
        glass_rect(self.screen,(20,panel_y,WINDOW_W-40,WINDOW_H-panel_y-10),
                   C["glass_dark"],C["border"]+(100,),radius=12)

        # progress bar
        px,py,pw,ph=self.prog_x,self.prog_y,self.prog_w,self.prog_h
        glass_rect(self.screen,(px,py,pw,ph),C["bg_secondary"]+(200,),radius=3)
        pos=self._pos()
        rat=clamp(pos/self.song_duration,0,1) if self.song_duration>0 else 0
        fw=int(pw*rat)
        if fw>0:
            glass_rect(self.screen,(px,py,fw,ph),acc+(210,),radius=3)
            bead=pygame.Surface((12,12),pygame.SRCALPHA)
            pygame.draw.circle(bead,acc+(230,),(6,6),5)
            pygame.draw.circle(bead,(255,255,255,200),(6,6),3)
            self.screen.blit(bead,(px+fw-6,py-4))
        t_el=self.f_xs.render(fmt_time(pos),True,C["text_secondary"])
        t_tot=self.f_xs.render(fmt_time(self.song_duration),True,C["text_secondary"])
        self.screen.blit(t_el,(px,py+8))
        self.screen.blit(t_tot,(px+pw-t_tot.get_width(),py+8))

        # buttons
        playing=pygame.mixer.music.get_busy() and not self.paused
        btn_data={
            "loop":  (LOOP_LABELS[self.loop_idx], False),
            "prev":  ("⏮", False),
            "play":  ("⏸" if playing else "▶", True),
            "stop":  ("⏹", False),
            "next":  ("⏭", False),
            "search":("⊳", False),
        }
        for name,rect in self.btns.items():
            lbl,is_main=btn_data[name]
            hov=(self.hover_btn==name)
            if is_main:
                pulse2=0.82+0.18*math.sin(self.breath_t*2.2)
                bg=tuple(int(c*pulse2) for c in C["accent_primary"])+(210,)
                br=C["accent_sec"]+(160,)
                tc=C["bg_dark"]
                f=self.f_big
            else:
                bg=C["bg_secondary"]+(200,) if not hov else (60,70,130,220)
                br=acc+(120,)
                tc=acc if not hov else C["text_primary"]
                f=self.f_sm
            glass_rect(self.screen,(rect.x,rect.y,rect.w,rect.h),bg,br,radius=4)
            t=f.render(lbl,True,tc)
            self.screen.blit(t,(rect.centerx-t.get_width()//2,
                                rect.centery-t.get_height()//2))

        # volume bar
        vx,vy,vw=self.vol_x,self.vol_y,self.vol_w
        glass_rect(self.screen,(vx,vy,vw,5),C["bg_secondary"]+(180,),radius=3)
        fv=int(vw*self.vol)
        if fv>0:
            glass_rect(self.screen,(vx,vy,fv,5),C["accent_tert"]+(200,),radius=3)
        vol_lbl=self.f_xs.render(f"♪  {int(self.vol*100)}%",True,C["text_secondary"])
        self.screen.blit(vol_lbl,(vx+vw+12,vy-3))

        # loop counter
        if LOOP_COUNTS[self.loop_idx]>1:
            lc_lbl=self.f_xs.render(
                f"loop {self.loop_count+1}/{LOOP_COUNTS[self.loop_idx]}",
                True,C["text_secondary"])
            self.screen.blit(lc_lbl,(WINDOW_W-lc_lbl.get_width()-30,vy-3))

        # ── scene switcher button ──
        sbr=self.scene_btn
        hov=sbr.collidepoint(pygame.mouse.get_pos())
        glass_rect(self.screen,(sbr.x,sbr.y,sbr.w,sbr.h),
                   (60,80,160,190) if hov else (30,40,100,150),
                   acc+(120,),radius=5)
        sl=self.f_xs.render("⊞",True,C["text_primary"] if hov else acc)
        self.screen.blit(sl,(sbr.centerx-sl.get_width()//2,
                             sbr.centery-sl.get_height()//2))

        # ── scene panel ──
        spy=int(self.scene_panel_y)
        if spy<WINDOW_H:
            pw2=200; ph2=len(self.scenes)*36+14
            px2=WINDOW_W-pw2-10
            glass_rect(self.screen,(px2,spy,pw2,ph2),C["glass_dark"],
                       C["border"]+(180,),radius=9)
            for i,(key,lbl,sc_acc,*_) in enumerate(self.scenes):
                ry=spy+7+i*36
                sel=(i==self.scene_idx)
                rb=sc_acc+(120,) if sel else (40,50,100,70)
                glass_rect(self.screen,(px2+6,ry,pw2-12,30),rb,radius=4)
                tc=C["text_primary"] if sel else C["text_secondary"]
                t=self.f_xs.render(lbl,True,tc)
                self.screen.blit(t,(px2+14,ry+8))

        # search overlay
        self.search.draw(self.screen,self.f_big,self.f_med,self.f_sm)

        pygame.display.flip()

    # ── MAIN LOOP ──────────────────────────────────────────

    def run(self):
        last=time.time()
        running=True
        while running:
            now=time.time(); dt=min(now-last,0.05); last=now
            running=self.handle_events()
            self.update(dt)
            self.draw()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()

# ═══════════════════════════════════════════════════════════
if __name__=="__main__":
    AetherPlayer().run()