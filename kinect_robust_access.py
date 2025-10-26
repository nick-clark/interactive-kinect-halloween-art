#!/usr/bin/env python3
"""
Kinect Robust Access Script
===========================

This script uses our C device manager to prepare the Kinect device,
then attempts to use the Python freenect library.
"""

import subprocess
import time
import freenect
import cv2
import numpy as np

def run_device_manager():
    """Run the C device manager to prepare the Kinect"""
    print("🔧 Running device manager to prepare Kinect...")
    
    try:
        result = subprocess.run(['./kinect_device_manager'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Device manager completed successfully")
            print("   Device should now be ready for Python access")
            return True
        else:
            print(f"❌ Device manager failed with return code {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Device manager timed out")
        return False
    except Exception as e:
        print(f"❌ Error running device manager: {e}")
        return False

def test_python_freenect():
    """Test Python freenect access after device preparation"""
    print("\n🐍 Testing Python freenect access...")
    
    try:
        # Try to get depth and video frames
        depth, _ = freenect.sync_get_depth()
        rgb, _ = freenect.sync_get_video()
        
        if depth is not None and rgb is not None:
            print("✅ Successfully got frames from Python freenect!")
            print(f"   Depth shape: {depth.shape}")
            print(f"   RGB shape: {rgb.shape}")
            return True
        else:
            print("❌ Failed to get frames from Python freenect")
            return False
            
    except Exception as e:
        print(f"❌ Python freenect error: {e}")
        return False

def display_frames():
    """Display frames from Python freenect"""
    print("\n🖼️  Displaying frames for 10 seconds...")
    
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 10:
        try:
            depth, _ = freenect.sync_get_depth()
            rgb, _ = freenect.sync_get_video()
            
            if depth is not None and rgb is not None:
                frame_count += 1
                
                # Convert depth to displayable format
                depth_display = cv2.convertScaleAbs(depth, alpha=0.05)
                
                # Display frames
                cv2.imshow('Depth', depth_display)
                cv2.imshow('RGB', rgb)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("❌ Failed to get frames")
                
        except Exception as e:
            print(f"❌ Error getting frames: {e}")
            break
        
        time.sleep(0.033)  # ~30fps
    
    cv2.destroyAllWindows()
    print(f"✅ Displayed {frame_count} frames")

def main():
    """Main function"""
    print("🎯 Kinect Robust Access Test")
    print("============================")
    
    # Step 1: Run device manager
    if not run_device_manager():
        print("❌ Device preparation failed")
        return False
    
    # Step 2: Wait a moment for device to settle
    print("\n⏳ Waiting 2 seconds for device to settle...")
    time.sleep(2)
    
    # Step 3: Test Python freenect
    if not test_python_freenect():
        print("❌ Python freenect access failed")
        return False
    
    # Step 4: Display frames
    display_frames()
    
    print("\n🎯 Test completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Robust access approach successful!")
        print("   The C device manager + Python freenect combination works!")
    else:
        print("\n❌ Robust access approach failed!")
        print("   The issue persists even with device preparation.")
