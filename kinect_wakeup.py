#!/usr/bin/env python3

import freenect
import time
import sys

def wakeup_kinect():
    """Try to wake up the Kinect"""
    print("Attempting to wake up Kinect...")
    
    try:
        # Initialize freenect
        print("Initializing freenect...")
        freenect.init()
        
        # Try to get device count
        print("Getting device count...")
        device_count = freenect.num_devices(freenect.init())
        print(f"Found {device_count} devices")
        
        if device_count == 0:
            print("❌ No Kinect devices found")
            return False
        
        # Try to open device
        print("Opening device...")
        device = freenect.open_device(freenect.init(), 0)
        
        if device is None:
            print("❌ Could not open device")
            return False
        
        print("✅ Device opened successfully!")
        
        # Try to set video mode
        print("Setting video mode...")
        freenect.set_video_mode(device, freenect.RESOLUTION_MEDIUM, freenect.VIDEO_RGB)
        
        # Try to set depth mode
        print("Setting depth mode...")
        freenect.set_depth_mode(device, freenect.RESOLUTION_MEDIUM, freenect.DEPTH_MM)
        
        print("✅ Modes set successfully!")
        
        # Try to start video
        print("Starting video stream...")
        freenect.start_video(device)
        
        # Try to start depth
        print("Starting depth stream...")
        freenect.start_depth(device)
        
        print("✅ Streams started successfully!")
        
        # Wait a moment
        time.sleep(1)
        
        # Try to get a frame
        print("Attempting to get video frame...")
        video_frame = freenect.sync_get_video()
        if video_frame is not None:
            print("✅ Got video frame!")
        else:
            print("❌ No video frame")
        
        print("Attempting to get depth frame...")
        depth_frame = freenect.sync_get_depth()
        if depth_frame is not None:
            print("✅ Got depth frame!")
        else:
            print("❌ No depth frame")
        
        # Stop streams
        print("Stopping streams...")
        freenect.stop_video(device)
        freenect.stop_depth(device)
        freenect.close_device(device)
        
        print("✅ Kinect wakeup successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error during wakeup: {e}")
        return False
    finally:
        try:
            freenect.sync_stop()
        except:
            pass

if __name__ == "__main__":
    success = wakeup_kinect()
    sys.exit(0 if success else 1)
