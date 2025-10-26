#!/usr/bin/env python3
"""
Simple Kinect Test Script
This script tests basic Kinect functionality and can be launched from KinectMaster
"""

import freenect
import cv2
import numpy as np
import time
import sys

def get_depth_data():
    """Get depth data from Kinect"""
    try:
        depth, _ = freenect.sync_get_depth()
        if depth is None:
            return None
        return depth
    except Exception as e:
        print(f"Depth error: {e}")
        return None

def get_rgb_data():
    """Get RGB data from Kinect"""
    try:
        rgb, _ = freenect.sync_get_video()
        if rgb is None:
            return None
        return rgb
    except Exception as e:
        print(f"RGB error: {e}")
        return None

def normalize_depth(depth_mm):
    """Normalize depth to 0-255 gradient"""
    d = depth_mm.copy().astype(np.float32)
    d[d <= 0] = np.nan
    near, far = 200, 4000  # mm
    d = np.clip(d, near, far)
    d = (d - near) / (far - near)  # 0..1
    d = (1.0 - d) * 255.0          # invert so near = bright
    d[np.isnan(d)] = 0
    return d.astype(np.uint8)

def main():
    print("🔍 Kinect Test Script Starting...")
    print("This script tests basic Kinect functionality")
    print("Press 'q' to quit, 's' to save a frame")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Get data from Kinect
            depth = get_depth_data()
            rgb = get_rgb_data()
            
            if depth is None or rgb is None:
                print("Waiting for Kinect...", end='\r')
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Mirror feeds for easier interaction
            rgb_mirrored = cv2.flip(rgb, 1)
            depth_mirrored = cv2.flip(depth, 1)
            
            # Normalize depth for display
            depth_normalized = normalize_depth(depth_mirrored)
            
            # Add frame counter and FPS
            elapsed_time = time.time() - start_time
            fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            
            cv2.putText(rgb_mirrored, f"Frames: {frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(rgb_mirrored, f"FPS: {fps:.1f}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display feeds
            cv2.imshow("RGB Feed", rgb_mirrored)
            cv2.imshow("Depth Feed", depth_normalized)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"kinect_test_rgb_{timestamp}.png", rgb_mirrored)
                cv2.imwrite(f"kinect_test_depth_{timestamp}.png", depth_normalized)
                print(f"Saved test images: kinect_test_rgb_{timestamp}.png, kinect_test_depth_{timestamp}.png")
    
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up...")
        cv2.destroyAllWindows()
        try:
            freenect.sync_stop()
        except:
            pass
        print("✅ Test complete")

if __name__ == "__main__":
    main()

