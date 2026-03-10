#!/usr/bin/env python3
"""
TAKE ACTION FASTER
A YouTube Poop about StockAlarm — stockalarm.io

Alerts. Candles. Technical indicators. Panic.
"""

import os, subprocess, random, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- CONFIG ---
W, H   = 1280, 720
FPS    = 30
OUT    = os.path.expanduser("~/take_action_faster.mp4")
TMP    = "/tmp/ytp_sa"

for d in [f"{TMP}/frames", f"{TMP}/audio", f"{TMP}/clips"]:
    os.makedirs(d, exist_ok=True)

# Colors
BK   = (0,   0,   0)
BL   = (10,  93,  255)    # StockAlarm blue
DBL  = (5,   40,  120)    # dark blue
UG   = (0,   220, 80)     # market green
DR   = (200, 0,   0)      # market red
YL   = (255, 210, 0)      # gold
WH   = (255, 255, 255)
GY   = (110, 110, 110)
OR   = (255, 120, 0)
CY   = (0,   200, 255)
PU   = (160, 0,   255)

random.seed(13)
np.random.seed(13)


# ── Fonts ──────────────────────────────────────────────────────────────────────
def load_font(size):
    for fp in ["/System/Library/Fonts/Menlo.ttc",
               "/System/Library/Fonts/Monaco.ttf",
               "/System/Library/Fonts/Courier.ttc"]:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except: pass
    return ImageFont.load_default()

F = {sz: load_font(sz) for sz in [13, 18, 20, 24, 28, 36, 48, 60, 72, 96]}


# ── Drawing ────────────────────────────────────────────────────────────────────
def new_frame(bg=BK):
    img = Image.new("RGB", (W, H), bg)
    return img, ImageDraw.Draw(img)

def cx(draw, text, y, sz=36, color=WH, dx=0, font=None):
    f  = font or F[sz]
    bb = draw.textbbox((0, 0), text, font=f)
    x  = (W - (bb[2] - bb[0])) // 2 + dx
    draw.text((x, y), text, fill=color, font=f)

def scanlines(img, alpha=55):
    ov = Image.new("RGBA", img.size, (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for y in range(0, H, 3):
        d.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

def chromashift(img, n=4):
    r, g, b = img.split()
    r = Image.fromarray(np.roll(np.array(r),  n, axis=1))
    b = Image.fromarray(np.roll(np.array(b), -n, axis=1))
    return Image.merge("RGB", [r, g, b])

def glitch(img, intensity=5):
    arr = np.array(img)
    for _ in range(random.randint(1, intensity)):
        y = random.randint(0, H - 1)
        arr[y] = np.roll(arr[y], random.randint(-50, 50), axis=0)
    return Image.fromarray(arr)

def draw_ticker(draw, tick_offset, items, y=H - 36, bg=DBL, fg=WH, sz=18):
    """Scrolling bottom ticker tape."""
    draw.rectangle([0, y, W, H], fill=bg)
    x = -tick_offset % (W * 3)
    for sym, price, pct in items * 6:
        color = UG if pct >= 0 else DR
        label = f"  {sym} {price:.2f} ({'+' if pct>=0 else ''}{pct:.1f}%)  |"
        draw.text((x, y + 6), label, fill=fg, font=F[18])
        bb = draw.textbbox((0, 0), label, font=F[18])
        x += bb[2] - bb[0]


# ── Audio ──────────────────────────────────────────────────────────────────────
SR = 44100

def write_wav(samples, path):
    samples = np.clip(samples, -1, 1)
    ints = (samples * 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(ints.tobytes())

def beep(freq=440, dur=0.08, vol=0.45, decay=8):
    t = np.linspace(0, dur, int(SR * dur))
    return vol * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)

def silence(dur=0.1):
    return np.zeros(int(SR * dur))

def alert_chime(pitch=1.0):
    """Upward notification ding."""
    freqs = [523, 659, 784, 1047]
    parts = []
    for f in freqs:
        parts.append(beep(f * pitch, 0.07, 0.35, 6))
        parts.append(silence(0.03))
    return np.concatenate(parts)

def tts(text, name, voice="Samantha", rate=160):
    aiff = f"{TMP}/audio/{name}.aiff"
    wav  = f"{TMP}/audio/{name}.wav"
    subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", aiff, text],
                   check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-i", aiff, wav],
                   check=True, capture_output=True)
    return wav

def pad_audio(wav_in, dur, wav_out):
    subprocess.run(["ffmpeg", "-y", "-i", wav_in,
                    "-af", f"apad=whole_dur={dur}", "-t", str(dur), wav_out],
                   check=True, capture_output=True)
    return wav_out

def mix_audio(paths, out):
    cmd = ["ffmpeg", "-y"]
    for p in paths: cmd += ["-i", p]
    n = len(paths)
    subprocess.run(cmd + ["-filter_complex",
                          f"amix=inputs={n}:duration=longest", out],
                   check=True, capture_output=True)
    return out

def fx(wav_in, af, wav_out):
    subprocess.run(["ffmpeg", "-y", "-i", wav_in, "-af", af, wav_out],
                   check=True, capture_output=True)
    return wav_out

def frames_to_clip(frames, audio, name, vf="null", af="anull"):
    fd = f"{TMP}/frames/{name}"
    os.makedirs(fd, exist_ok=True)
    for i, f in enumerate(frames):
        f.save(f"{fd}/{i:06d}.png")
    dur = len(frames) / FPS
    out = f"{TMP}/clips/{name}.mp4"
    cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", f"{fd}/%06d.png"]
    if audio and os.path.exists(audio):
        padded = pad_audio(audio, dur, f"{TMP}/audio/{name}_pad.wav")
        cmd += ["-i", padded, "-vf", vf, "-af", af, "-t", str(dur),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    else:
        cmd += ["-vf", vf, "-t", str(dur), "-c:v", "libx264",
                "-pix_fmt", "yuv420p", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out

def concat_clips(clips, out):
    cmd = ["ffmpeg", "-y"]
    for c in clips: cmd += ["-i", c]
    n  = len(clips)
    fc = "".join(f"[{i}:v][{i}:a]" for i in range(n))
    fc += f"concat=n={n}:v=1:a=1[vout][aout]"
    cmd += ["-filter_complex", fc, "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "44100", "-ac", "1", out]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


# ── Fake market data ───────────────────────────────────────────────────────────
TICKER_ITEMS = [
    ("AAPL",  221.73,  1.4), ("TSLA",  248.50,  5.2), ("NVDA",  875.20,  3.8),
    ("SPY",   512.40,  0.6), ("AMZN",  185.90, -0.9), ("MSFT",  415.30,  1.1),
    ("GME",    23.10, 18.7), ("BBBY",   0.003,-94.2), ("BTC",  67420.0,  2.3),
    ("ETH",   3512.0,  1.7), ("MEME",  420.69, 69.0), ("YOLO", 1337.00, 13.3),
]

def draw_candle(draw, x, open_, close, high, low, width=14):
    color = UG if close >= open_ else DR
    top   = min(open_, close)
    bot   = max(open_, close)
    draw.line([(x + width//2, high), (x + width//2, low)], fill=color, width=2)
    draw.rectangle([x, top, x + width, bot], fill=color)


# ══════════════════════════════════════════════════════════════════════════════
#  SCENES
# ══════════════════════════════════════════════════════════════════════════════

def scene_title():
    """2.5s – StockAlarm title card."""
    n = int(2.5 * FPS)
    frames = []
    for fn in range(n):
        p = fn / n
        img, d = new_frame(DBL)

        # Animated price line in background
        for i in range(W // 4):
            py = H // 2 + int(30 * math.sin(i * 0.3 + fn * 0.15))
            d.point((i * 4, py), fill=(BL[0], BL[1], BL[2]))

        fade = min(1.0, p / 0.35)
        bl_ = tuple(int(c * fade) for c in BL)
        wh_ = tuple(int(c * fade) for c in WH)
        gy_ = tuple(int(c * fade) for c in GY)

        cx(d, "STOCKALARM.IO", H//2 - 80, color=wh_, font=F[96])
        cx(d, "take action faster", H//2 + 30, color=bl_, font=F[36])
        cx(d, "a youtube poop",     H//2 + 85, color=gy_, font=F[20])

        draw_ticker(d, fn * 4, TICKER_ITEMS)
        img = scanlines(img)
        frames.append(img)

    chimes = np.concatenate([alert_chime(0.8), silence(0.3), alert_chime(1.0)])
    w = f"{TMP}/audio/title.wav"
    write_wav(chimes, w)
    return frames_to_clip(frames, w, "title")


def scene_market_open():
    """4s – 9:29:59 → bell → CHAOS."""
    n = 4 * FPS
    frames = []
    for fn in range(n):
        p = fn / n
        img, d = new_frame()

        if p < 0.45:
            # Countdown
            secs_left = 1 - p / 0.45
            cx(d, "MARKET OPENS IN", H//2 - 80, color=GY,  font=F[28])
            cx(d, f"{secs_left:.2f}s", H//2 - 20, color=WH, font=F[96])
            cx(d, "9:29:59", H//2 + 80, color=YL, font=F[36])

        elif p < 0.55:
            # THE BELL
            cx(d, "🔔", H//2 - 60, color=YL, font=F[96])
            cx(d, "MARKETS OPEN", H//2 + 40, color=UG, font=F[72])

        else:
            # Chaos
            chaos = (p - 0.55) / 0.45
            for _ in range(int(chaos * 30) + 5):
                sym, price, pct = random.choice(TICKER_ITEMS)
                sz  = random.choice([20, 28, 36, 48])
                col = UG if pct > 0 else DR
                x_  = random.randint(0, W - 200)
                y_  = random.randint(0, H - 60)
                d.text((x_, y_), f"{sym} {'+' if pct>0 else ''}{pct:.1f}%",
                       fill=col, font=F[sz])
            cx(d, "TAKE ACTION FASTER", H//2 - 30, color=WH, font=F[60])

        draw_ticker(d, fn * 6, TICKER_ITEMS)
        img = scanlines(img)
        if p > 0.55:
            img = glitch(img, int((p - 0.55) * 10) + 1)
        frames.append(img)

    # Bell sound synthesized
    t = np.linspace(0, 0.8, SR)
    bell = (0.6 * np.sin(2*np.pi*1047*t) + 0.3 * np.sin(2*np.pi*2093*t)) * np.exp(-t * 3)
    chaos_noise = np.zeros(SR * 4)
    chaos_noise[int(SR*1.8):int(SR*1.8)+len(bell)] = bell
    w = f"{TMP}/audio/bell.wav"
    write_wav(chaos_noise, w)

    vw = tts("Market open! Prices are moving! Take action faster!",
             "open_voice", voice="Fred", rate=185)
    mw = mix_audio([w, vw], f"{TMP}/audio/open.wav")
    return frames_to_clip(frames, mw, "open")


def scene_alert_storm():
    """5s – Notifications raining down."""
    n = 5 * FPS
    alerts = [
        ("AAPL",  "hit your price target $220.00 ↑",   UG),
        ("TSLA",  "up 8.2% — RSI crossed 70",           UG),
        ("NVDA",  "Golden Cross detected!",             YL),
        ("SPY",   "dropped below 200 SMA ↓",            DR),
        ("BTC",   "Death Cross — MACD bearish",         DR),
        ("GME",   "up 18% — earnings surprise",         UG),
        ("BBBY",  "down 94% — going to zero",           DR),
        ("ETH",   "hit limit: $3,500",                  UG),
        ("AMZN",  "EMA(20) crossed EMA(50) ↑",          UG),
        ("MEME",  "420% gain in 24h",                   UG),
    ]
    # Active notifications on screen
    active = []  # (x, y, text, color, age)
    frames = []

    for fn in range(n):
        p = fn / n
        img, d = new_frame((5, 8, 20))

        # Add new alert every ~0.4s
        if fn % 12 == 0:
            sym, msg, col = random.choice(alerts)
            active.append([40, -60, sym, msg, col, 0])

        # Draw active notifications
        for alert in active[:]:
            ax, ay, sym, msg, col, age = alert
            ay += 3
            alert[1] = ay
            alert[5] += 1

            if ay > H + 80 or age > FPS * 3:
                active.remove(alert)
                continue

            # Notification card
            card_w = 600
            d.rounded_rectangle([ax, ay, ax + card_w, ay + 60],
                                  radius=8, fill=(15, 25, 50), outline=col, width=2)
            d.text((ax + 12, ay + 8),  sym, fill=col,  font=F[24])
            d.text((ax + 90, ay + 10), msg, fill=WH,   font=F[18])
            d.text((ax + 12, ay + 38), "StockAlarm", fill=BL, font=F[13])
            # App icon placeholder
            d.rounded_rectangle([ax + card_w - 50, ay + 8, ax + card_w - 8, ay + 52],
                                  radius=6, fill=BL)
            d.text((ax + card_w - 44, ay + 18), "SA", fill=WH, font=F[18])

        # Stats sidebar
        d.text((W - 250, 20), "ALERTS FIRED", fill=GY, font=F[13])
        count = int(p * 847)
        d.text((W - 250, 38), f"{count:,}", fill=YL, font=F[48])
        d.text((W - 250, 100), f"ASSETS TRACKED", fill=GY, font=F[13])
        d.text((W - 250, 118), "65,000+", fill=BL, font=F[28])

        draw_ticker(d, fn * 5, TICKER_ITEMS)
        img = scanlines(img)
        frames.append(img)

    # Rapid notification chimes
    chime_audio = []
    for i in range(15):
        chime_audio.append(silence(random.uniform(0.1, 0.4)))
        chime_audio.append(alert_chime(random.uniform(0.8, 1.3)))
    w = f"{TMP}/audio/alert_chimes.wav"
    write_wav(np.concatenate(chime_audio), w)

    vw = tts(
        "Apple hit your price target. "
        "Tesla up eight percent. "
        "Golden cross detected on Nvidia. "
        "Step away from your computer. We've got your back.",
        "alert_voice", voice="Samantha", rate=165
    )
    mw = mix_audio([w, vw], f"{TMP}/audio/alerts.wav")
    return frames_to_clip(frames, mw, "alerts")


def scene_candlestick_war():
    """5s – Candles battling. Green vs red."""
    n = 5 * FPS
    frames = []

    # Generate random walk price data
    np.random.seed(99)
    prices = [500.0]
    for _ in range(120):
        prices.append(prices[-1] * (1 + np.random.normal(0, 0.008)))

    for fn in range(n):
        p = fn / n
        img, d = new_frame((8, 8, 15))

        d.text((20, 12), "SPY  1D  |  Chart by StockAlarm", fill=GY, font=F[18])

        # Visible candles
        visible = min(fn // 2 + 1, len(prices) - 1)
        price_min = min(prices[:visible+1]) * 0.998
        price_max = max(prices[:visible+1]) * 1.002
        price_range = price_max - price_min or 1

        chart_y0 = 60
        chart_h  = H - 120
        cw = max(8, (W - 40) // max(1, visible))

        for i in range(visible):
            o = prices[i]
            c_ = prices[i + 1]
            hi = max(o, c_) * (1 + abs(np.random.normal(0, 0.002)))
            lo = min(o, c_) * (1 - abs(np.random.normal(0, 0.002)))

            def price_to_y(pr):
                return chart_y0 + int(chart_h * (1 - (pr - price_min) / price_range))

            x = 20 + i * cw
            draw_candle(d, x,
                        price_to_y(o), price_to_y(c_),
                        price_to_y(hi), price_to_y(lo),
                        width=max(4, cw - 3))

        # Current price label
        if visible > 0:
            cur = prices[visible]
            cy_ = chart_y0 + int(chart_h * (1 - (cur - price_min) / price_range))
            chg = (cur - prices[0]) / prices[0] * 100
            col = UG if chg >= 0 else DR
            d.line([(0, cy_), (W, cy_)], fill=(col[0]//3, col[1]//3, col[2]//3), width=1)
            d.text((W - 180, cy_ - 20), f"${cur:.2f}", fill=col, font=F[28])
            d.text((W - 180, cy_ + 6),  f"{'+' if chg>=0 else ''}{chg:.2f}%", fill=col, font=F[18])

        # YTP effect: buy/sell shout at chaos moments
        if p > 0.6 and fn % 10 < 5:
            last_chg = prices[visible] - prices[max(0, visible-1)]
            shout = "BUY BUY BUY" if last_chg > 0 else "SELL SELL SELL"
            scol  = UG if last_chg > 0 else DR
            cx(d, shout, H//2 - 30, color=scol, font=F[72])

        draw_ticker(d, fn * 5, TICKER_ITEMS)
        img = scanlines(img)
        if p > 0.7 and random.random() < 0.15:
            img = chromashift(img, 5)
        frames.append(img)

    vw = tts(
        "Green candle. Red candle. Green. Red. Green green green. "
        "RED. "
        "Set an alert. Step away from the computer.",
        "candle_voice", voice="Daniel", rate=155
    )
    return frames_to_clip(frames, vw, "candles")


def scene_indicators():
    """4s – Technical indicator overload / YTP stutter."""
    n = 4 * FPS
    indicators = [
        ("RSI",    73.4,  "OVERBOUGHT",   DR),
        ("MACD",   "+2.1 CROSS", "BULLISH",    UG),
        ("SMA 50", "ABOVE",      "GOLDEN CROSS", YL),
        ("EMA 20", "BELOW",      "SELL SIGNAL",  DR),
        ("RSI",    28.1,  "OVERSOLD",     UG),
        ("VWAP",   "ABOVE",      "BULLISH",      UG),
        ("BB",     "UPPER BAND", "BREAKOUT?",    YL),
    ]
    phases = [
        (0.0,  0.15, 0), (0.15, 0.22, 1), (0.22, 0.29, 2),
        (0.29, 0.36, 1), (0.36, 0.43, 2), (0.43, 0.50, 3),  # stutter
        (0.50, 0.60, 4), (0.60, 0.70, 5), (0.70, 0.80, 6),
        (0.80, 1.00, 99),  # ALL AT ONCE
    ]
    frames = []

    for fn in range(n):
        p = fn / n
        idx = 0
        for (ps, pe, i) in phases:
            if ps <= p < pe:
                idx = i
                break

        img, d = new_frame()

        if idx == 99:
            # ALL indicators screaming at once
            for i_, (name, val, signal, col) in enumerate(indicators):
                row = i_ % 4
                col_ = i_ // 4
                x_ = 40 + col_ * 640
                y_ = 40 + row * 160
                d.rectangle([x_, y_, x_+580, y_+140], fill=(15,15,30), outline=col, width=2)
                d.text((x_+10, y_+10), str(name), fill=col, font=F[28])
                d.text((x_+10, y_+50), str(val),  fill=WH, font=F[36])
                d.text((x_+10, y_+100), str(signal), fill=col, font=F[20])
        else:
            ind = indicators[idx % len(indicators)]
            name, val, signal, col = ind
            d.text((60, 40), "TECHNICAL ANALYSIS", fill=GY, font=F[24])
            d.line([(60, 76), (W-60, 76)], fill=GY, width=1)

            jitter = int(max(0, p - 0.3) * 20)
            dy = random.randint(-jitter, jitter)
            cx(d, str(name), H//2 - 100 + dy, color=col, font=F[96])
            cx(d, str(val),  H//2 + 10 + dy,  color=WH, font=F[60])
            cx(d, str(signal), H//2 + 90 + dy, color=col, font=F[36])

        draw_ticker(d, fn * 4, TICKER_ITEMS)
        img = scanlines(img)
        if p > 0.5:
            img = chromashift(img, int(p * 6))
        frames.append(img)

    vw = tts(
        "R S I. Overbought! "
        "Overbought! Overbought! "
        "MACD bullish cross! "
        "Golden- golden- golden cross! Death cross! "
        "BOTH AT THE SAME TIME. "
        "Set an alert. Step away from your computer.",
        "indicators_voice", voice="Fred", rate=175
    )
    fw = fx(vw, "vibrato=f=5:d=0.4", f"{TMP}/audio/indicators_fx.wav")
    return frames_to_clip(frames, fw, "indicators")


def scene_not_financial_advice():
    """4s – The disclaimer. YTP stutter."""
    n = 4 * FPS
    DISC = "THIS IS NOT FINANCIAL ADVICE"
    phases = [
        (0.00, 0.20, DISC,             WH,  F[48]),
        (0.20, 0.27, "THIS IS NOT-",   YL,  F[60]),
        (0.27, 0.34, DISC,             WH,  F[48]),
        (0.34, 0.41, "THIS IS NOT-",   YL,  F[60]),
        (0.41, 0.48, "NOT FINANCIAL-", OR,  F[48]),
        (0.48, 0.58, DISC,             DR,  F[60]),
        (0.58, 0.68, "THIS IS-",       DR,  F[72]),
        (0.68, 0.78, "NOT-",           DR,  F[96]),
        (0.78, 0.88, "FINANCIAL-",     PU,  F[72]),
        (0.88, 1.00, "ADVICE",         DR,  F[96]),
    ]
    sub_texts = [
        "past performance does not guarantee future results",
        "always do your own research",
        "we are not responsible for your losses",
        "or your gains",
        "stocks can go to zero",
        "or to the moon",
        "consult a financial advisor",
        "or don't",
    ]
    frames = []

    for fn in range(n):
        p = fn / n
        text, color, fnt = DISC, WH, F[48]
        for (ps, pe, t, c, f_) in phases:
            if ps <= p < pe:
                text, color, fnt = t, c, f_
                break

        chaos = max(0.0, (p - 0.4) * 1.7)
        bg = (int(chaos * 20), 0, 0)
        img, d = new_frame(bg)

        jitter = int(chaos * 10)
        cx(d, text, H//2 - 60 + random.randint(-jitter, jitter),
           color=color, font=fnt)

        # Scrolling sub-disclaimers
        sub_idx = int(p * len(sub_texts) * 2) % len(sub_texts)
        cx(d, sub_texts[sub_idx], H//2 + 80, color=GY, font=F[20])

        # Fine print spam
        if p > 0.3:
            for _ in range(int(p * 12)):
                d.text((random.randint(0, W - 300), random.randint(H//2+120, H-40)),
                       "not financial advice", fill=(40, 40, 40), font=F[13])

        draw_ticker(d, fn * 4, TICKER_ITEMS)
        img = scanlines(img)
        if p > 0.5:
            img = chromashift(img, int(p * 6))
        if p > 0.7:
            img = glitch(img, int(p * 8))
        frames.append(img)

    vw = tts(
        "This is not financial advice. "
        "This is not- this is not financial advice. "
        "Not financial- not financial advice. "
        "Not. "
        "Financial. "
        "Advice. "
        "Please do your own research.",
        "nfa_voice", voice="Samantha", rate=180
    )
    fw = fx(vw, "vibrato=f=8:d=0.5,aecho=0.7:0.4:50:0.3",
            f"{TMP}/audio/nfa_fx.wav")
    return frames_to_clip(frames, fw, "nfa")


def scene_step_away():
    """3.5s – You cannot step away."""
    n = int(3.5 * FPS)
    frames = []
    for fn in range(n):
        p = fn / n
        img, d = new_frame(DBL)

        fade = min(1.0, p / 0.2)
        cx(d, "STEP AWAY FROM YOUR COMPUTER",
           H//2 - 120, color=tuple(int(c*fade) for c in WH), font=F[36])
        cx(d, "we've got your back.",
           H//2 - 70, color=tuple(int(c*fade) for c in BL), font=F[28])

        # But the screen keeps pulling them back
        if p > 0.35:
            pull = (p - 0.35) / 0.65
            cx(d, "but what if TSLA moves",
               H//2 + 10, color=tuple(int(c*pull) for c in YL), font=F[28])
        if p > 0.5:
            pull2 = (p - 0.5) / 0.5
            cx(d, "what if it gaps up",
               H//2 + 60, color=tuple(int(c*pull2) for c in OR), font=F[24])
        if p > 0.65:
            pull3 = (p - 0.65) / 0.35
            cx(d, "just one more chart",
               H//2 + 110, color=tuple(int(c*pull3) for c in DR), font=F[36])
        if p > 0.8:
            cx(d, "WE'VE GOT YOUR BACK",
               H//2 + 160, color=tuple(int(c*((p-0.8)/0.2)) for c in UG), font=F[48])

        draw_ticker(d, fn * 5, TICKER_ITEMS)
        img = scanlines(img)
        frames.append(img)

    vw = tts(
        "Step away from your computer. We've got your back. "
        "But what if Tesla moves? "
        "We've. Got. Your. Back. "
        "Just one more chart. "
        "WE HAVE GOT YOUR BACK.",
        "stepaway_voice", voice="Samantha", rate=150
    )
    return frames_to_clip(frames, vw, "stepaway")


def scene_meltdown():
    """4s – Full YTP chaos, StockAlarm edition."""
    n = 4 * FPS
    words = ["BUY", "SELL", "ALERT", "STOCKS", "UP", "DOWN", "MOON",
             "ZERO", "TAKE", "ACTION", "FASTER", "RSI", "MACD", "YOLO",
             "HOLD", "DIAMOND", "HANDS", "WHY", "CRASH", "RALLY"]
    frames = []

    for fn in range(n):
        p = fn / n
        arr = np.random.randint(0, int(p * 25) + 1, (H, W, 3), dtype=np.uint8)
        img = Image.fromarray(arr)
        d   = ImageDraw.Draw(img)

        for _ in range(int(p * 30) + 8):
            w_  = random.choice(words)
            sz_ = random.choice([24, 36, 48, 72, 96])
            x_  = random.randint(0, max(1, W - sz_ * len(w_)))
            y_  = random.randint(0, max(1, H - sz_))
            c_  = random.choice([UG, DR, YL, WH, BL, OR, PU])
            d.text((x_, y_), w_, fill=c_, font=F[sz_])

        if fn % 6 < 3:
            cx(d, "TAKE ACTION", H//2 - 55, color=WH, font=F[96])
        else:
            cx(d, "FASTER", H//2 - 55, color=UG if fn % 12 < 6 else DR, font=F[96])

        draw_ticker(d, fn * 12, TICKER_ITEMS)
        img = glitch(img, int(p * 15) + 3)
        img = chromashift(img, int(p * 12) + 2)
        frames.append(img)

    t     = np.linspace(0, 4.0, SR * 4)
    audio = np.zeros_like(t)
    for freq in [196, 294, 392, 784]:
        audio += 0.1 * np.sin(2 * np.pi * freq * t * (1 + 0.1 * np.sin(t * 6)))
    audio = np.tanh(audio * (1 + t * 2))
    for _ in range(20):
        s = random.randint(0, SR * 4 - SR // 8)
        audio[s:s + SR // 8] += random.uniform(0.2, 0.6) * (np.random.random(SR // 8) * 2 - 1)
    cw = f"{TMP}/audio/meltdown_chaos.wav"
    write_wav(audio * 0.8, cw)

    vw = tts(
        "Take action! Take action! Take action faster! "
        "Buy! Sell! Alert! Alert! ALERT! "
        "TAKE. ACTION. FASTER.",
        "meltdown_v", voice="Fred", rate=230
    )
    fv = fx(vw, "vibrato=f=10:d=0.8,aecho=0.9:0.5:30:0.4",
            f"{TMP}/audio/meltdown_vfx.wav")
    mw = mix_audio([cw, fv], f"{TMP}/audio/meltdown.wav")
    return frames_to_clip(frames, mw, "meltdown")


def scene_rating():
    """3s – 4.8 stars. 7000+ ratings."""
    n = 3 * FPS
    frames = []
    star_msgs = [
        ("5 ★★★★★", '"Saved my portfolio."',         UG),
        ("5 ★★★★★", '"I YOLO\'d and it worked."',    YL),
        ("5 ★★★★★", '"Best app. Thank you."',         UG),
        ("1 ★☆☆☆☆", '"TSLA went down anyway."',      DR),
        ("5 ★★★★★", '"Worth every penny."',           UG),
        ("5 ★★★★★", '"Step away. It works."',         BL),
        ("3 ★★★☆☆", '"Still watching charts tho."',  GY),
    ]
    for fn in range(n):
        p = fn / n
        img, d = new_frame(DBL)

        cx(d, "4.8 / 5", H//2 - 120, color=YL, font=F[96])
        cx(d, "★★★★★", H//2 - 30,  color=YL, font=F[60])
        cx(d, "7,000+ ratings",     H//2 + 50, color=WH, font=F[28])
        cx(d, "highest rated stock alerts platform",
           H//2 + 95, color=GY, font=F[20])

        # Rotating review
        rev_idx = int(p * len(star_msgs) * 2) % len(star_msgs)
        rating_, review_, rcol = star_msgs[rev_idx]
        cx(d, rating_, H//2 + 140, color=rcol,  font=F[24])
        cx(d, review_, H//2 + 172, color=WH,    font=F[20])

        draw_ticker(d, fn * 4, TICKER_ITEMS)
        img = scanlines(img)
        frames.append(img)

    vw = tts(
        "Four point eight stars. Seven thousand reviews. "
        "The highest rated stock alerts platform. "
        "stockalarm dot io.",
        "rating_voice", voice="Samantha", rate=145
    )
    return frames_to_clip(frames, vw, "rating")


def scene_credits():
    """3s – End card."""
    n = 3 * FPS
    lines = [
        ("stockalarm.io",                          BL,  F[72]),
        ("take action faster",                     WH,  F[36]),
        ("",                                       GY,  F[20]),
        ("past performance is not indicative",     GY,  F[18]),
        ("of future results",                       GY,  F[18]),
        ("",                                       GY,  F[20]),
        ("no stocks were harmed in this video",    GY,  F[13]),
    ]
    frames = []
    for fn in range(n):
        p = fn / n
        img, d = new_frame()
        fade = min(1.0, p / 0.3)
        y = H//2 - 150
        for text, color, fnt in lines:
            if text:
                col = tuple(int(c * fade) for c in color)
                cx(d, text, y, color=col, font=fnt)
            y += 38
        draw_ticker(d, fn * 3, TICKER_ITEMS)
        img = scanlines(img)
        frames.append(img)

    chimes = np.concatenate([silence(0.5)] +
                             [alert_chime(1.0 + i * 0.1) for i in range(3)])
    w = f"{TMP}/audio/credits.wav"
    write_wav(chimes, w)
    vw = tts("stockalarm dot io. Take action faster. "
             "Past performance is not indicative of future results.",
             "credits_voice", voice="Samantha", rate=135)
    mw = mix_audio([w, vw], f"{TMP}/audio/credits_mix.wav")
    return frames_to_clip(frames, mw, "credits")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("TAKE ACTION FASTER  –  generating scenes...\n")
    steps = [
        ("title card",           scene_title),
        ("market open",          scene_market_open),
        ("alert storm",          scene_alert_storm),
        ("candlestick war",      scene_candlestick_war),
        ("indicator overload",   scene_indicators),
        ("not financial advice", scene_not_financial_advice),
        ("step away",            scene_step_away),
        ("MELTDOWN",             scene_meltdown),
        ("ratings",              scene_rating),
        ("credits",              scene_credits),
    ]
    clips = []
    for i, (label, fn) in enumerate(steps, 1):
        print(f"  [{i:02d}/{len(steps)}] {label}...")
        clips.append(fn())

    print("\nConcatenating all scenes...")
    final = concat_clips(clips, OUT)

    dur = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", OUT], capture_output=True, text=True
    ).stdout.strip()

    print(f"\n✓ Done!  →  {OUT}")
    print(f"  Duration : {float(dur):.1f}s")
    print(f"  Size     : {os.path.getsize(OUT)/1024/1024:.1f} MB")
