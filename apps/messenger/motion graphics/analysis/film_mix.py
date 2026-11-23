"""The Mirsal redesign film's sound: the Stable Audio track (audio/music.mp3), Will's nine lines (audio/vo/l01..l09)
at the times the picture uses (VO in app/src/scenes/film.ts), and a few very soft effects from audio/sfx/. The
music ducks about 6 dB under the voice. Writes out/film_mix.wav; mux and normalise with:

    uv run --no-project --with numpy python analysis/film_mix.py
    ffmpeg -i out/film.mp4 -i out/film_mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -af loudnorm=I=-14:TP=-1 -shortest out/film_sound.mp4
"""
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR, DUR = 48000, 60.03
N = int(DUR * SR) + SR
VO = [0.8, 4.4, 10.6, 17.2, 23.4, 34.4, 41.4, 51.4, 56.4]  # = VO in film.ts


def decode(path, ch=1):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", str(ch), "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).copy()
    return x.reshape(-1, ch) if ch > 1 else x


def add(buf, t, x, g):
    i = int(round(t * SR))
    if i < 0:
        x, i = x[-i:], 0
    n = min(len(x), len(buf) - i)
    if n > 0:
        buf[i:i + n] += x[:n] * g


# the music (stereo)
music = np.zeros((N, 2), dtype=np.float32)
m = decode(ROOT / "audio" / "music.mp3", 2)[:N]
music[:len(m)] = m

# the voice: each line's first sound lands on its time
vo = np.zeros(N, dtype=np.float32)
for i, t in enumerate(VO, 1):
    x = decode(ROOT / "audio" / "vo" / f"l{i:02d}.mp3")
    x /= np.abs(x).max() + 1e-9
    env = np.convolve(np.abs(x), np.ones(480) / 480, mode="same")
    on = int(np.argmax(env > 0.08 * env.max()))
    add(vo, t - on / SR, x, 0.9)

# soft effects
fx = np.zeros(N, dtype=np.float32)
_c = {}


def cue(t, name, db):
    if name not in _c:
        x = decode(sorted((ROOT / "audio" / "sfx").glob(f"{name}_*.mp3"))[0])
        _c[name] = x / (np.abs(x).max() + 1e-9)
    x = _c[name]
    idx = np.where(np.abs(x) > 0.5)[0]
    on = max(0, int(idx[0]) - int(0.008 * SR)) if len(idx) else 0
    add(fx, t - on / SR, x, 10 ** (db / 20))


for tc in (5.3, 10.4, 13.2, 16.25, 23.2, 30.5, 36.3, 41.9, 42.9, 43.9, 47.55, 49.55, 51.35):
    cue(tc, "mouse_click", -19)                          # every click the cursor makes
for i in range(10):
    cue(3.2 + i * 0.05, "pop2", -34)                     # the chat list reveals
for i in range(6):
    cue(5.6 + i * 0.28, "pop2", -30)                     # the messages reveal
cue(7.8, "sent", -20)                                    # Arif's new message
cue(10.5, "whoosh_soft", -24)                            # the tray opens
for i in range(4):
    cue(10.9 + i * 0.1, "pop2", -29)
cue(14.2, "chime2", -22)                                 # Ready
cue(16.95, "sent", -18); cue(18.4, "pop2", -24)          # the image in the chat, Arif's reply
for k in range(int((23.0 - 21.0) / 0.06)):
    cue(21.0 + k * 0.06, "key_click", -30)               # the close-up typing
cue(23.25, "sent", -18)
for i in range(4):
    cue(24.2 + i * 0.4, "pen_tick", -30)                 # thinking steps done
cue(25.7, "riser2", -26); cue(25.75, "sparkle", -24)     # the burst
for i in range(4):
    cue(25.75 + i * 0.12, "pop2", -27)
for i in range(3):
    cue(27.8 + i * 0.12, "pop2", -29)
for k in range(int((32.6 - 31.7) / 0.06)):
    cue(31.7 + k * 0.06, "key_click", -32)
cue(37.3, "pop2", -22); cue(37.9, "chime2", -24)         # the flight lands on Wednesday
cue(41.9, "whoosh_soft", -26); cue(42.9, "whoosh_soft", -26); cue(43.9, "whoosh_soft", -26)
for i in range(7):
    cue(46.5 + i * 0.06, "pop2", -33)                    # the inbox reveals
cue(49.75, "chime2", -26)
for t in (20.6, 31.4, 40.0, 44.6, 46.4, 50.9):
    cue(t, "whoosh_soft", -29)
cue(51.6, "pop2", -24)                                   # the Profile modal
riser = _c.setdefault("riser2", None)
x = decode(sorted((ROOT / "audio" / "sfx").glob("riser2_*.mp3"))[0]); x /= np.abs(x).max() + 1e-9
add(fx, 56.3 - len(x) / SR, x, 10 ** (-26 / 20))         # a glassy swell into the finale

# mix: the music ducks under the voice
env = np.convolve(np.abs(vo), np.ones(int(0.15 * SR)) / int(0.15 * SR), mode="same")
duck = 1 - 0.5 * np.clip(env / (env.max() + 1e-9) * 4, 0, 1)
mono = vo + fx
mix = music * (0.8 * duck)[:, None] + mono[:, None]
mix = mix[: int(DUR * SR)]
mix /= np.abs(mix).max() / 0.89
out = ROOT / "out" / "film_mix.wav"
out.parent.mkdir(exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", str(out)], input=mix.astype(np.float32).tobytes(), check=True)
print(f"wrote {out} ({len(mix) / SR:.2f} s)")
