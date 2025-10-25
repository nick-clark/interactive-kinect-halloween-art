#!/usr/bin/env python3
import os
import time
import cv2
import numpy as np

try:
    import freenect
except ImportError as e:
    raise SystemExit("Missing 'freenect' Python module. Build/install libfreenect with Python bindings.\n"
                     "See README step 2.") from e

CAPTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)

def get_depth():
    depth, _ = freenect.sync_get_depth(format=freenect.DEPTH_MM)  # millimeters
    if depth is None:
        return None
    depth = depth.astype(np.uint16)  # keep mm
    return depth

def get_rgb():
    rgb, _ = freenect.sync_get_video(format=freenect.VIDEO_RGB)
    if rgb is None:
        return None
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

def normalize_depth_for_display(depth_mm):
    # Clip range for display (e.g., 500mm..4500mm), then normalize to 0..255
    d = depth_mm.copy().astype(np.float32)
    d[d <= 0] = np.nan
    near, far = 500.0, 4500.0
    d = np.clip(d, near, far)
    d = (d - near) / (far - near)  # 0..1
    d = (1.0 - d) * 255.0          # invert so near = bright
    d[np.isnan(d)] = 0
    return d.astype(np.uint8)

def save_pair(bgr, depth_mm):
    ts = int(time.time() * 1000)
    bgr_path = os.path.join(CAPTURE_DIR, f"rgb_{ts}.png")
    depth_raw_path = os.path.join(CAPTURE_DIR, f"depth_mm_{ts}.npy")
    depth_vis_path = os.path.join(CAPTURE_DIR, f"depth_vis_{ts}.png")

    cv2.imwrite(bgr_path, bgr)
    np.save(depth_raw_path, depth_mm)
    cv2.imwrite(depth_vis_path, normalize_depth_for_display(depth_mm))
    print(f"Saved:\n  {bgr_path}\n  {depth_raw_path}\n  {depth_vis_path}")

def main():
    print("Kinect Viewer — press 's' to save RGB+Depth, 'q' to quit")
    while True:
        depth = get_depth()
        rgb = get_rgb()
        if depth is None or rgb is None:
            print("Waiting for Kinect streams... (is it powered + USB connected?)")
            time.sleep(0.5)
            continue

        depth_vis = normalize_depth_for_display(depth)
        cv2.imshow("RGB", rgb)
        cv2.imshow("Depth (vis)", depth_vis)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            save_pair(rgb, depth)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
