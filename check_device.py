#!/usr/bin/env python3

import freenect
import sys

def check_kinect():
    print("🔍 Checking Kinect device...")
    
    try:
        # Try to get depth data
        print("Testing depth access...")
        depth, _ = freenect.sync_get_depth()
        if depth is not None:
            print("✅ Depth data received!")
            print(f"   Shape: {depth.shape}")
            print(f"   Range: {depth.min()} - {depth.max()}")
        else:
            print("❌ No depth data")
            
        # Try to get RGB data
        print("Testing RGB access...")
        rgb, _ = freenect.sync_get_video()
        if rgb is not None:
            print("✅ RGB data received!")
            print(f"   Shape: {rgb.shape}")
        else:
            print("❌ No RGB data")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("This usually means:")
        print("1. Kinect is not connected")
        print("2. Kinect is not powered on")
        print("3. USB permission issues")
        print("4. Another process is using the Kinect")
        
    finally:
        try:
            freenect.sync_stop()
        except:
            pass

if __name__ == "__main__":
    check_kinect()
