#!/usr/bin/env python3
import time
import numpy as np
import cv2

try:
    import freenect
except ImportError as e:
    raise SystemExit("Missing 'freenect'. Build/install libfreenect with Python bindings.") from e

# Config
NEAR_MM = 600       # treat blobs nearer than this as "hand in"
FAR_MM  = 900       # ...and farther than this as "hand out"
MIN_BLOB_PIXELS = 500  # adjust based on your scene
COOLDOWN_SEC = 0.5

def get_depth_mm():
    d, _ = freenect.sync_get_depth(format=freenect.DEPTH_MM)
    if d is None:
        return None
    return d.astype(np.uint16)

def detect_near_blob(depth_mm):
    # Build mask in the band [NEAR_MM, FAR_MM]
    mask = (depth_mm > 0) & (depth_mm >= NEAR_MM) & (depth_mm <= FAR_MM)
    mask = mask.astype(np.uint8) * 255
    # Morphological cleanup
    mask = cv2.medianBlur(mask, 5)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return False, mask
    area = max(cv2.contourArea(c) for c in cnts)
    return (area >= MIN_BLOB_PIXELS), mask

def main():
    print("Near-hand gesture demo — put your hand ~0.6–0.9m from the sensor to toggle. 'q' to quit.")
    toggled = False
    last_toggle = 0.0
    while True:
        depth = get_depth_mm()
        if depth is None:
            print("Waiting for depth...")
            time.sleep(0.2)
            continue

        present, mask = detect_near_blob(depth)
        vis = np.dstack([mask]*3)
        cv2.putText(vis, f\"state: {'ON' if toggled else 'OFF'}\", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
        cv2.imshow("near-hand mask", vis)

        now = time.time()
        if present and (now - last_toggle) > COOLDOWN_SEC:
            toggled = not toggled
            last_toggle = now
            print(f\"Toggled -> {'ON' if toggled else 'OFF'} @ {time.strftime('%H:%M:%S')}\")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
