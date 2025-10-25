#!/usr/bin/env python3

import freenect
import cv2
import numpy as np
import time

def test_async_kinect():
    """Test Kinect using async API"""
    print("Testing Kinect with async API...")
    
    try:
        # Initialize freenect
        freenect.init()
        
        # Get device
        device = freenect.open_device(freenect.init(), 0)
        if device is None:
            print("❌ Could not open Kinect device")
            return False
        
        print("✅ Kinect device opened successfully!")
        
        # Set video and depth modes
        freenect.set_video_mode(device, freenect.RESOLUTION_MEDIUM, freenect.VIDEO_RGB)
        freenect.set_depth_mode(device, freenect.RESOLUTION_MEDIUM, freenect.DEPTH_MM)
        
        print("✅ Video and depth modes set")
        
        # Start video and depth streams
        freenect.start_video(device)
        freenect.start_depth(device)
        
        print("✅ Video and depth streams started")
        
        # Test getting frames
        for i in range(10):
            # Get video frame
            video_frame = freenect.sync_get_video()
            if video_frame is not None:
                print(f"✅ Got video frame {i}")
            else:
                print(f"❌ No video frame {i}")
            
            # Get depth frame
            depth_frame = freenect.sync_get_depth()
            if depth_frame is not None:
                print(f"✅ Got depth frame {i}")
            else:
                print(f"❌ No depth frame {i}")
            
            time.sleep(0.1)
        
        # Stop streams
        freenect.stop_video(device)
        freenect.stop_depth(device)
        freenect.close_device(device)
        
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        freenect.sync_stop()

if __name__ == "__main__":
    test_async_kinect()

