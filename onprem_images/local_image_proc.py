import os
import time
from datetime import datetime
from PIL import Image
import csv

# ================= CONFIG =================

# Paths
THIS_DIR = os.path.dirname(os.path.abspath(__file__))        # .../Final Project/onprem_images
PROJECT_ROOT = os.path.dirname(THIS_DIR)                     # .../Final Project

INPUT_DIR = os.path.join(PROJECT_ROOT, "images_to_upload")
OUTPUT_DIR = os.path.join(THIS_DIR, "output_local")
METRICS_DIR = os.path.join(THIS_DIR, "metrics")
METRICS_FILE = os.path.join(METRICS_DIR, "local_metrics.csv")

# ==========================================

def process_image(path_in, path_out):
    orig_size = os.path.getsize(path_in)
    start = time.perf_counter()

    img = Image.open(path_in)
    img = img.convert("RGB")
    img = img.resize((800, 600))
    img.save(path_out, format="JPEG", quality=80, optimize=True)

    end = time.perf_counter()
    new_size = os.path.getsize(path_out)
    proc_ms = (end - start) * 1000.0

    return orig_size, new_size, proc_ms

def main():
    print("=== On-Prem Image Processing ===")
    print("Project root:", PROJECT_ROOT)
    print("Input dir:", INPUT_DIR)
    print("Output dir:", OUTPUT_DIR)
    print("Metrics file:", METRICS_FILE)
    print()

    if not os.path.isdir(INPUT_DIR):
        raise FileNotFoundError(f"Input folder does not exist: {INPUT_DIR}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(METRICS_DIR, exist_ok=True)

    rows = []
    for filename in os.listdir(INPUT_DIR):
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        path_in = os.path.join(INPUT_DIR, filename)
        path_out = os.path.join(OUTPUT_DIR, filename)

        orig_size, new_size, proc_ms = process_image(path_in, path_out)
        ts = datetime.utcnow().isoformat()

        print(f"{filename}: {proc_ms:.2f} ms")

        rows.append([ts, filename, orig_size, new_size, f"{proc_ms:.2f}"])

    # Save metrics
    header = ["timestamp", "image_key", "orig_size", "new_size", "proc_ms"]
    file_exists = os.path.exists(METRICS_FILE)
    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerows(rows)

    print("\nOn-prem processing completed.")
    print(f"Processed images saved to: {OUTPUT_DIR}")
    print(f"Metrics saved to: {METRICS_FILE}")

if __name__ == "__main__":
    main()
