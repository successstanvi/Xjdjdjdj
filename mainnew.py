import os
import math
import random
import subprocess
import numpy as np
from PIL import Image, ImageDraw
import io
import time

# ================= CONFIG =================
WIDTH, HEIGHT = 1280, 720
CENTER = (WIDTH//2, HEIGHT//2)
RADIUS = 260
FLAG_SIZE = 48
FPS = 30
GAP_ANGLE = 40        # degrees
SPEED = 4
BG_COLOR = (18, 18, 18)

FLAGS_DIR = "flags"
HIT_SOUND = "hit.wav"
# YouTube stream key
YOUTUBE_STREAM_KEY = "rg6h-8puw-p4eb-a1au-2xyf"
YOUTUBE_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"
# =========================================

# Load flag images
flag_imgs = []
for file in os.listdir(FLAGS_DIR):
    if file.lower().endswith(".png"):
        img = Image.open(os.path.join(FLAGS_DIR, file)).convert("RGBA")
        img = img.resize((FLAG_SIZE, FLAG_SIZE))
        flag_imgs.append((file.split(".")[0].upper(), img))

if len(flag_imgs) < 2:
    raise Exception("Need at least 2 flags")

# FFmpeg command to stream to YouTube
ffmpeg_cmd = [
    "ffmpeg",
    "-y",
    "-f", "rawvideo",
    "-pix_fmt", "rgb24",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-r", str(FPS),
    "-i", "-",                   # input from pipe
    "-stream_loop", "-1",         # loop audio
    "-i", HIT_SOUND,             # audio file
    "-shortest",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-preset", "veryfast",
    "-g", "60",
    "-c:a", "aac",
    "-b:a", "128k",
    "-f", "flv",
    YOUTUBE_URL
]

# Start FFmpeg process
proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

def create_flags():
    flags = []
    for name, img in flag_imgs:
        angle = random.uniform(0, 2*math.pi)
        r = random.uniform(0, RADIUS-60)
        x = CENTER[0] + r*math.cos(angle)
        y = CENTER[1] + r*math.sin(angle)
        vel = np.array([
            random.choice([-1,1])*random.uniform(2,SPEED),
            random.choice([-1,1])*random.uniform(2,SPEED)
        ], dtype=float)
        flags.append({
            "name": name,
            "img": img,
            "pos": np.array([x,y], dtype=float),
            "vel": vel,
            "alive": True
        })
    return flags

def in_exit_gap(angle):
    deg = math.degrees(angle)
    return -GAP_ANGLE/2 < deg < GAP_ANGLE/2

def draw_frame(flags):
    canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    # Arena
    draw.ellipse([
        CENTER[0]-RADIUS, CENTER[1]-RADIUS,
        CENTER[0]+RADIUS, CENTER[1]+RADIUS
    ], outline=(255,255,255), width=4)
    # Draw flags
    for f in flags:
        if not f["alive"]:
            continue
        x, y = int(f["pos"][0]), int(f["pos"][1])
        canvas.paste(f["img"], (x-FLAG_SIZE//2, y-FLAG_SIZE//2), f["img"])
    return np.array(canvas)

# Endless live loop
while True:
    flags = create_flags()
    frame_count = 0
    while True:
        alive_flags = [f for f in flags if f["alive"]]
        if len(alive_flags) <= 1:
            # Winner pause 10s
            winner = alive_flags[0]["name"] if alive_flags else "None"
            print(f"🏆 WINNER: {winner}")
            for _ in range(FPS*10):
                canvas = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
                draw = ImageDraw.Draw(canvas)
                draw.text((WIDTH//2-100, HEIGHT//2-20), f"🏆 WINNER: {winner}", fill=(255,255,0))
                proc.stdin.write(np.array(canvas).tobytes())
            break

        # Physics update
        for f in alive_flags:
            f["pos"] += f["vel"]
            dx = f["pos"][0]-CENTER[0]
            dy = f["pos"][1]-CENTER[1]
            dist = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            # Exit check
            if dist > RADIUS and in_exit_gap(angle):
                f["alive"] = False
                continue
            # Wall bounce
            if dist > RADIUS-FLAG_SIZE/2:
                nx, ny = dx/dist, dy/dist
                f["vel"] -= 2*np.dot(f["vel"], [nx,ny])*np.array([nx,ny])
            # Collision with others
            for o in alive_flags:
                if o is f: continue
                d = np.linalg.norm(f["pos"] - o["pos"])
                if d < FLAG_SIZE:
                    f["vel"], o["vel"] = o["vel"], f["vel"]

        # Draw frame & send to ffmpeg
        frame = draw_frame(flags)
        proc.stdin.write(frame.tobytes())
        frame_count += 1
