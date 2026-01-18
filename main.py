import os
import math
import random
import subprocess
import numpy as np
from PIL import Image, ImageDraw

# ================= CONFIG =================
WIDTH, HEIGHT = 1280, 720
CENTER = (WIDTH // 2, HEIGHT // 2)
RADIUS = 260
FLAG_SIZE = 48
FPS = 30
MAX_FRAMES = 2000
GAP_ANGLE = 40          # degrees
SPEED = 4
BG_COLOR = (18, 18, 18)

FRAMES_DIR = "frames"
FLAGS_DIR = "flags"
HIT_SOUND = "hit.wav"
OUTPUT_VIDEO = "final.mp4"
# =========================================

os.makedirs(FRAMES_DIR, exist_ok=True)

# ---------- Load Flags ----------
flags = []
flag_imgs = []

for file in os.listdir(FLAGS_DIR):
    if file.lower().endswith(".png"):
        img = Image.open(f"{FLAGS_DIR}/{file}").convert("RGBA")
        img = img.resize((FLAG_SIZE, FLAG_SIZE))
        flag_imgs.append((file.split(".")[0].upper(), img))

if len(flag_imgs) < 2:
    raise Exception("Need at least 2 flags")

# ---------- Initialize Physics ----------
for name, img in flag_imgs:
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, RADIUS - 60)
    x = CENTER[0] + r * math.cos(angle)
    y = CENTER[1] + r * math.sin(angle)
    vel = np.array([
        random.choice([-1, 1]) * random.uniform(2, SPEED),
        random.choice([-1, 1]) * random.uniform(2, SPEED)
    ], dtype=float)

    flags.append({
        "name": name,
        "img": img,
        "pos": np.array([x, y], dtype=float),
        "vel": vel,
        "alive": True
    })

# ---------- Helpers ----------
def in_exit_gap(angle):
    deg = math.degrees(angle)
    return -GAP_ANGLE / 2 < deg < GAP_ANGLE / 2

hit_events = []

# ---------- Simulation ----------
for frame in range(MAX_FRAMES):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # Arena
    draw.ellipse([
        CENTER[0] - RADIUS, CENTER[1] - RADIUS,
        CENTER[0] + RADIUS, CENTER[1] + RADIUS
    ], outline=(255, 255, 255), width=4)

    alive = [f for f in flags if f["alive"]]

    for f in alive:
        f["pos"] += f["vel"]

        dx = f["pos"][0] - CENTER[0]
        dy = f["pos"][1] - CENTER[1]
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)

        # EXIT
        if dist > RADIUS and in_exit_gap(angle):
            f["alive"] = False
            print(f"❌ {f['name']} eliminated")
            continue

        # WALL COLLISION
        if dist > RADIUS - FLAG_SIZE / 2:
            nx, ny = dx / dist, dy / dist
            f["vel"] -= 2 * np.dot(f["vel"], [nx, ny]) * np.array([nx, ny])
            hit_events.append(frame)

        # FLAG COLLISION
        for o in alive:
            if o is f or not o["alive"]:
                continue
            d = np.linalg.norm(f["pos"] - o["pos"])
            if d < FLAG_SIZE:
                f["vel"], o["vel"] = o["vel"], f["vel"]
                hit_events.append(frame)

        x, y = int(f["pos"][0]), int(f["pos"][1])
        canvas.paste(
            f["img"],
            (x - FLAG_SIZE // 2, y - FLAG_SIZE // 2),
            f["img"]
        )

    canvas.save(f"{FRAMES_DIR}/frame_{frame:04d}.png")

    if len([f for f in flags if f["alive"]]) <= 1:
        break

winner = [f["name"] for f in flags if f["alive"]]
print("🏆 WINNER:", winner[0] if winner else "None")

# ---------- FFmpeg Video ----------
print("🎞 Rendering video...")
subprocess.run([
    "ffmpeg", "-y",
    "-r", str(FPS),
    "-i", f"{FRAMES_DIR}/frame_%04d.png",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "video.mp4"
], check=True)

# ---------- Add Hit Sound ----------
print("🔊 Adding sound...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", "video.mp4",
    "-stream_loop", "-1",
    "-i", HIT_SOUND,
    "-filter_complex", "amix=inputs=2:dropout_transition=0",
    "-shortest",
    OUTPUT_VIDEO
], check=True)

print("✅ DONE →", OUTPUT_VIDEO)
