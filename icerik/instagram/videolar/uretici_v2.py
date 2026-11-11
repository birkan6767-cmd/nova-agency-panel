import math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DUR = 13.5
N = int(DUR * FPS)
F = "/usr/share/fonts/opentype/inter/"
BLACK = F + "InterDisplay-Black.otf"; XB = F + "InterDisplay-ExtraBold.otf"; SB = F + "InterDisplay-SemiBold.otf"; MD = F + "InterDisplay-Medium.otf"
GOLD = (232, 190, 72); GOLD2 = (255, 214, 102); WHITE = (255, 255, 255); SOFT = (196, 206, 232); NAVY = (6, 16, 46)
fc = {}
def font(p, s):
    k = (p, int(s))
    if k not in fc: fc[k] = ImageFont.truetype(p, int(s))
    return fc[k]

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def ease_out_cubic(t): t = clamp(t); return 1 - (1 - t) ** 3
def ease_in_cubic(t): t = clamp(t); return t ** 3
def ease_out_back(t, s=1.7):
    t = clamp(t) - 1; return t * t * ((s + 1) * t + s) + 1
def prog(t, a, b): return clamp((t - a) / (b - a))

# arka plan
yy = np.linspace(0, 1, H)[:, None]
top = np.array([5, 12, 36]); bot = np.array([10, 30, 88])
bg = (top * (1 - yy) + bot * yy)[:, None, :].repeat(W, 1).reshape(H, W, 3).astype(np.uint8)
BG = Image.fromarray(bg)
glow = Image.new("L", (1400, 1400), 0); ImageDraw.Draw(glow).ellipse([300, 300, 1100, 1100], fill=255)
glow = glow.filter(ImageFilter.GaussianBlur(170))
glow_col = Image.new("RGB", glow.size, (210, 160, 40))

def fit_size(text, path, maxw, start):
    s = start
    while s > 40 and font(path, s).getbbox(text)[2] > maxw: s -= 4
    return s

def draw_text_scaled(base, text, path, size, x, y, color, scale=1.0, alpha=1.0, anchor_center_y=True):
    if alpha <= 0 or scale <= 0.01: return
    f = font(path, size * scale)
    bb = f.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    layer = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer); d.text((20 - bb[0], 20 - bb[1]), text, font=f, fill=color + (int(255 * alpha),))
    # gölge
    sh = layer.copy().split()[3].filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55))
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0)); shadow.putalpha(sh)
    # ölçek sol-orta merkezli
    ox = x - 20; oy = y - 20 + int((size - size * scale) * 0.5) if anchor_center_y else y - 20
    base.alpha_composite(shadow, (int(ox + 4), int(oy + 8)))
    base.alpha_composite(layer, (int(ox), int(oy)))

def bars(base, t, y0=1548, alpha=1.0):
    d = ImageDraw.Draw(base)
    n = 26; bw = 18; gap = (W - 180 - n * bw) / (n - 1)
    for i in range(n):
        h = 24 + 90 * abs(math.sin(t * 3.1 + i * 0.55) * math.sin(t * 1.7 + i * 0.27))
        x = 90 + i * (bw + gap)
        a = int(110 * alpha)
        d.rounded_rectangle([x, y0 - h / 2, x + bw, y0 + h / 2], radius=9, fill=GOLD + (a,))

def header(base, t):
    d = ImageDraw.Draw(base)
    d.text((90, 150), "NOVA MEDYA", font=font(XB, 40), fill=GOLD + (255,))
    w = font(XB, 40).getbbox("NOVA MEDYA")[2]
    d.line([(90 + w + 24, 175), (W - 90, 175)], fill=GOLD + (120,), width=3)

def mic(base, cx, cy, s, t, alpha):
    if alpha <= 0: return
    d = ImageDraw.Draw(base)
    for k in range(3):
        ph = (t * 0.9 + k / 3) % 1
        r = s * (0.9 + ph * 1.25)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD + (int(150 * (1 - ph) * alpha),), width=6)
    a = int(255 * alpha)
    d.rounded_rectangle([cx - s * 0.32, cy - s * 0.62, cx + s * 0.32, cy + s * 0.25], radius=int(s * 0.32), fill=GOLD + (a,))
    d.arc([cx - s * 0.5, cy - s * 0.45, cx + s * 0.5, cy + s * 0.45], 0, 180, fill=GOLD + (a,), width=int(s * 0.08))
    d.line([(cx, cy + s * 0.45), (cx, cy + s * 0.7)], fill=GOLD + (a,), width=int(s * 0.08))
    d.rounded_rectangle([cx - s * 0.28, cy + s * 0.66, cx + s * 0.28, cy + s * 0.76], radius=8, fill=GOLD + (a,))

def check(base, x, y, r, p):
    d = ImageDraw.Draw(base)
    d.ellipse([x - r, y - r, x + r, y + r], fill=GOLD + (255,))
    if p > 0:
        pts = [(x - r * 0.45, y + r * 0.02), (x - r * 0.1, y + r * 0.38), (x + r * 0.5, y - r * 0.35)]
        seg1 = clamp(p * 2); seg2 = clamp(p * 2 - 1)
        p1 = (pts[0][0] + (pts[1][0] - pts[0][0]) * seg1, pts[0][1] + (pts[1][1] - pts[0][1]) * seg1)
        d.line([pts[0], p1], fill=NAVY + (255,), width=int(r * 0.22))
        if seg2 > 0:
            p2 = (pts[1][0] + (pts[2][0] - pts[1][0]) * seg2, pts[1][1] + (pts[2][1] - pts[1][1]) * seg2)
            d.line([pts[1], p2], fill=NAVY + (255,), width=int(r * 0.22))

def scene_offset(t, start, end):
    # giriş: aşağıdan, çıkış: yukarı
    inn = 1 - ease_out_cubic(prog(t, start, start + 0.35))
    out = ease_in_cubic(prog(t, end - 0.3, end))
    return inn * 120 - out * 160, 1 - out

MAXW = W - 180
WORDS = ["YAYINCI", "OLMAK", "İSTER", "MİSİN?"]
WS = [fit_size(w, BLACK, MAXW, 300) for w in WORDS]
WS = [min(s, 222) for s in WS]

def frame(i):
    t = i / FPS
    im = BG.copy().convert("RGBA")
    gx = int(W / 2 - 700 + 160 * math.sin(t * 0.6)); gy = int(700 - 700 + 220 * math.sin(t * 0.45 + 1))
    a = glow.point(lambda v: int(v * (0.33 + 0.1 * math.sin(t * 2))))
    im.paste(glow_col, (gx, gy), a)
    header(im, t)
    bars(im, t, alpha=0.9)
    # SAHNE 1: 0 - 3.4
    if t < 3.4:
        dy, al = scene_offset(t, -1, 3.4)
        y = 430 + dy
        for k, (w, s) in enumerate(zip(WORDS, WS)):
            p = prog(t, 0.05 + k * 0.2, 0.55 + k * 0.2)
            sc = ease_out_back(p) if p < 1 else 1.0
            col = GOLD2 if k == 0 else WHITE
            draw_text_scaled(im, w, BLACK, s, 90, y, col, scale=max(sc, 0.001), alpha=al * clamp(p * 3))
            y += s * 1.02
        p = ease_out_cubic(prog(t, 1.25, 1.7))
        if p > 0:
            txt = "Sesli odalarda yayın · Kamera şart değil"
            f = font(SB, 40); tw = f.getbbox(txt)[2]
            lay = Image.new("RGBA", (tw + 70, 90), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            d.rounded_rectangle([2, 2, tw + 64, 84], radius=41, fill=(255, 255, 255, 26), outline=GOLD + (220,), width=3)
            d.text((33, 43), txt, font=f, fill=WHITE + (255,), anchor="lm")
            lay.putalpha(lay.split()[3].point(lambda v: int(v * p * al)))
            im.alpha_composite(lay, (90, int(y + 20 + (1 - p) * 30)))
    # SAHNE 2: 3.4 - 6.6
    if 3.4 <= t < 6.6:
        dy, al = scene_offset(t, 3.4, 6.6)
        mic(im, W / 2, 600 + dy, 150, t, al * ease_out_cubic(prog(t, 3.4, 3.8)))
        p1 = prog(t, 3.6, 4.1); p2 = prog(t, 4.0, 4.5)
        s1 = fit_size("KAMERA YOK.", BLACK, MAXW, 200); s2 = fit_size("SADECE SESİN.", BLACK, MAXW, 200)
        draw_text_scaled(im, "KAMERA YOK.", BLACK, s1, 90, 1010 + dy, WHITE, scale=max(ease_out_back(p1), .001), alpha=al * clamp(p1 * 3))
        draw_text_scaled(im, "SADECE SESİN.", BLACK, s2, 90, 1010 + s1 * 1.05 + dy, GOLD2, scale=max(ease_out_back(p2), .001), alpha=al * clamp(p2 * 3))
    # SAHNE 3: 6.6 - 9.8
    if 6.6 <= t < 9.8:
        dy, al = scene_offset(t, 6.6, 9.8)
        p0 = ease_out_cubic(prog(t, 6.6, 7.0))
        draw_text_scaled(im, "Seni neler", BLACK, 130, 90, 420 + dy, WHITE, alpha=al * p0)
        draw_text_scaled(im, "bekliyor?", BLACK, 130, 90, 560 + dy, GOLD2, alpha=al * p0)
        items = ["Deneyim şart değil", "Eğitim ve yayın planı", "Ekip desteği hep yanında"]
        for k, it in enumerate(items):
            p = ease_out_cubic(prog(t, 7.0 + k * 0.35, 7.45 + k * 0.35))
            if p <= 0: continue
            x = 90 - (1 - p) * 200; yk = 820 + k * 170 + dy
            lay = Image.new("RGBA", (W, 160), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            d.rounded_rectangle([0, 0, MAXW, 140], radius=36, fill=(255, 255, 255, 22), outline=(255, 255, 255, 40), width=2)
            check(lay, 75, 70, 38, prog(t, 7.2 + k * 0.35, 7.6 + k * 0.35))
            d.text((140, 70), it, font=font(XB, 54), fill=WHITE + (255,), anchor="lm")
            lay.putalpha(lay.split()[3].point(lambda v: int(v * p * al)))
            im.alpha_composite(lay, (int(x), int(yk)))
    # SAHNE 4: 9.8 - 13.5
    if t >= 9.8:
        dy, al = scene_offset(t, 9.8, 99)
        p1 = prog(t, 9.85, 10.35); p2 = prog(t, 10.05, 10.55)
        s1 = fit_size("HEMEN", BLACK, MAXW, 260); s2 = fit_size("BAŞVUR", BLACK, MAXW, 260)
        draw_text_scaled(im, "HEMEN", BLACK, s1, 90, 420 + dy, WHITE, scale=max(ease_out_back(p1), .001), alpha=clamp(p1 * 3))
        draw_text_scaled(im, "BAŞVUR", BLACK, s2, 90, 420 + s1 * 1.02 + dy, GOLD2, scale=max(ease_out_back(p2), .001), alpha=clamp(p2 * 3))
        p3 = ease_out_cubic(prog(t, 10.6, 11.0))
        if p3 > 0:
            pulse = 1 + 0.035 * math.sin((t - 10.6) * 6)
            bw, bh = int(MAXW * pulse), int(150 * pulse)
            lay = Image.new("RGBA", (bw + 40, bh + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            d.rounded_rectangle([20, 20, 20 + bw, 20 + bh], radius=bh // 2, fill=GOLD2 + (255,))
            d.text((20 + bw / 2, 20 + bh / 2), "DM'den “YAYINCI” yaz", font=font(BLACK, 64 * pulse), fill=NAVY + (255,), anchor="mm")
            lay.putalpha(lay.split()[3].point(lambda v: int(v * p3)))
            by = 420 + s1 * 1.02 + s2 * 1.02 + 70 + (1 - p3) * 40
            im.alpha_composite(lay, (int(90 - 20 - (bw - MAXW) / 2), int(by - 20)))
            d2 = ImageDraw.Draw(im)
            d2.text((W / 2, by + 230), "Başvuru ücretsiz · 18 yaş ve üzeri", font=font(SB, 44), fill=WHITE + (int(255 * p3),), anchor="mm")
    # yasal not (hep)
    d = ImageDraw.Draw(im)
    d.text((90, 1640), "Kazanç garanti edilmez; sonuçlar kişisel performansa ve", font=font(MD, 30), fill=SOFT + (200,))
    d.text((90, 1680), "platform koşullarına göre değişir. Maaşlı iş ilanı değildir.", font=font(MD, 30), fill=SOFT + (200,))
    return im.convert("RGB")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for ts in [0.6, 2.2, 4.8, 8.6, 11.8]:
            frame(int(ts * FPS)).save(f"p_{ts}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                          "-movflags", "+faststart", "reel.mp4"], stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
    p.stdin.close(); p.wait(); print("ok", N)
