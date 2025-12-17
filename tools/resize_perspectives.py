#!/usr/bin/env python3
from PIL import Image
import glob
import os

TARGET_WIDTH = 645
TARGET_HEIGHT = 408
BASE_DIR = "/Users/jay/ekyc/lama"

def trim_and_resize(img_path, target_w, target_h):
    img = Image.open(img_path).convert("RGBA")

    # 투명 배경 trim (실제 콘텐츠 영역만 crop)
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # 목표 크기로 리사이즈 (비율 무시, 강제 fit)
    resized = img.resize((target_w, target_h), Image.LANCZOS)

    return resized

if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(BASE_DIR, "t*.png")))

    for f in files:
        name = os.path.basename(f)
        if name == "t1.png":
            print(f"Skip: {name} (base)")
            continue

        result = trim_and_resize(f, TARGET_WIDTH, TARGET_HEIGHT)
        result.save(f)
        print(f"Trimmed & Resized: {name} -> {TARGET_WIDTH}x{TARGET_HEIGHT}")
