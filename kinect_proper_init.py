#!/usr/bin/env python3

import freenect
import cv2
import numpy as np
import time

def proper_kinect_init():
    """Initialize Kinect using the same sequence as freenect-camtest"""
    print("🔧 Initializing Kinect with proper sequence...")
    
    try:
        # Step 1: Initialize context (like C code)
        print("1. Initializing freenect context...")
        freenect.init()
        
        # Step 2: Set log level and select camera only (like C code)
        print("2. Setting log level and selecting camera...")
        # Note: Python freenect doesn't expose these functions directly
        # But we can try to set them if available
        
        # Step 3: Check device count (like C code)
        print("3. Checking device count...")
        device_count = freenect.num_devices(freenect.init())
        print(f"   Found {device_count} devices")
        
        if device_count == 0:
            print("❌ No devices found!")
            return None
        
        # Step 4: Open device (like C code)
        print("4. Opening device...")
        device = freenect.open_device(freenect.init(), 0)
        if device is None:
            print("❌ Could not open device!")
            return None
        
        print("✅ Device opened successfully!")
        
        # Step 5: Set modes BEFORE starting streams (like C code)
        print("5. Setting video and depth modes...")
        freenect.set_video_mode(device, freenect.RESOLUTION_MEDIUM, freenect.VIDEO_RGB)
        freenect.set_depth_mode(device, freenect.RESOLUTION_MEDIUM, freenect.DEPTH_MM)
        
        print("✅ Modes set successfully!")
        
        # Step 6: Start streams (like C code)
        print("6. Starting video and depth streams...")
        freenect.start_video(device)
        freenect.start_depth(device)
        
        print("✅ Streams started successfully!")
        
        # Step 7: Wait a moment for streams to stabilize
        print("7. Waiting for streams to stabilize...")
        time.sleep(2)
        
        return device
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return None

def test_sync_functions():
    """Test the sync functions after proper initialization"""
    print("\n🧪 Testing sync functions...")
    
    try:
        # Test depth
        print("Testing sync_get_depth...")
        depth, _ = freenect.sync_get_depth()
        if depth is not None:
            print(f"✅ Depth data received! Shape: {depth.shape}")
        else:
            print("❌ No depth data")
        
        # Test video
        print("Testing sync_get_video...")
        rgb, _ = freenect.sync_get_video()
        if rgb is not None:
            print(f"✅ Video data received! Shape: {rgb.shape}")
        else:
            print("❌ No video data")
            
        return depth is not None and rgb is not None
        
    except Exception as e:
        print(f"❌ Error testing sync functions: {e}")
        return False

def cleanup(device):
    """Clean up resources"""
    if device:
        try:
            print("🧹 Cleaning up...")
            freenect.stop_video(device)
            freenect.stop_depth(device)
            freenect.close_device(device)
            freenect.sync_stop()
            print("✅ Cleanup complete!")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

def main():
    print("🎃 Testing Proper Kinect Initialization")
    print("=" * 50)
    
    device = None
    try:
        # Initialize using proper sequence
        device = proper_kinect_init()
        
        if device:
            # Test sync functions
            success = test_sync_functions()
            
            if success:
                print("\n🎉 SUCCESS! Kinect is working properly!")
                print("The issue was improper initialization sequence.")
            else:
                print("\n❌ Sync functions still failing")
        else:
            print("\n❌ Device initialization failed")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        cleanup(device)

if __name__ == "__main__":
    main()
