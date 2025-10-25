#!/usr/bin/env python3

import freenect
import cv2
import numpy as np
import time

def test_kinect():
    """Test if Kinect is working"""
    print("🔍 Testing Kinect connection...")
    
    try:
        # Try to get depth data
        depth, _ = freenect.sync_get_depth()
        if depth is not None:
            print("✅ Depth data received!")
            print(f"   Depth shape: {depth.shape}")
            print(f"   Depth range: {depth.min()} - {depth.max()}")
        else:
            print("❌ No depth data")
            
        # Try to get RGB data
        rgb, _ = freenect.sync_get_video()
        if rgb is not None:
            print("✅ RGB data received!")
            print(f"   RGB shape: {rgb.shape}")
        else:
            print("❌ No RGB data")
            
        # Show a frame
        if depth is not None and rgb is not None:
            print("📸 Showing Kinect feed for 5 seconds...")
            start_time = time.time()
            
            while time.time() - start_time < 5:
                depth, _ = freenect.sync_get_depth()
                rgb, _ = freenect.sync_get_video()
                
                if depth is not None and rgb is not None:
                    # Mirror for easier interaction
                    rgb_mirrored = cv2.flip(rgb, 1)
                    depth_mirrored = cv2.flip(depth, 1)
                    
                    # Normalize depth for display
                    depth_normalized = depth_mirrored.copy().astype(np.float32)
                    depth_normalized[depth_normalized <= 0] = np.nan
                    depth_normalized = np.clip(depth_normalized, 500, 4000)
                    depth_normalized = (depth_normalized - 500) / (4000 - 500)
                    depth_normalized = (1.0 - depth_normalized) * 255.0
                    depth_normalized[np.isnan(depth_normalized)] = 0
                    depth_display = depth_normalized.astype(np.uint8)
                    
                    # Add text overlay
                    cv2.putText(rgb_mirrored, "Kinect RGB Feed", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(depth_display, "Kinect Depth Feed", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    
                    cv2.imshow("RGB Feed", rgb_mirrored)
                    cv2.imshow("Depth Feed", depth_display)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                        
            cv2.destroyAllWindows()
            print("✅ Kinect test completed!")
            
    except Exception as e:
        print(f"❌ Error testing Kinect: {e}")
        print("Make sure Kinect is connected and powered on")
    
    finally:
        freenect.sync_stop()

if __name__ == "__main__":
    test_kinect()
