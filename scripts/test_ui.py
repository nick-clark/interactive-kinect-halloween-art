#!/usr/bin/env python3

import cv2
import numpy as np
import time

def test_ui():
    """Test the UI without Kinect"""
    print("Testing UI without Kinect...")
    
    # Create control panel
    cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Control Panel', 500, 300)
    
    # Create some test trackbars
    cv2.createTrackbar('Test Slider', 'Control Panel', 50, 100, lambda x: print(f"Slider: {x}"))
    cv2.createTrackbar('Capture BG', 'Control Panel', 0, 1, lambda x: print(f"Capture: {x}"))
    
    # Create test video windows
    cv2.namedWindow('👻 Ghost Tracking - Main View', cv2.WINDOW_NORMAL)
    cv2.namedWindow('🔍 Depth Map & Detection', cv2.WINDOW_NORMAL)
    
    print("UI windows created. You should see:")
    print("1. Control Panel window with sliders")
    print("2. Ghost Tracking window")
    print("3. Depth Map window")
    print("Press 'q' to quit")
    
    frame_count = 0
    while True:
        # Create test frames
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        test_frame[:] = (50, 50, 50)  # Dark gray background
        
        # Add some test content
        cv2.putText(test_frame, f"Test Frame {frame_count}", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(test_frame, "This is a test without Kinect", (50, 280), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show frames
        cv2.imshow('👻 Ghost Tracking - Main View', test_frame)
        cv2.imshow('🔍 Depth Map & Detection', test_frame)
        
        frame_count += 1
        
        # Handle key presses
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break
    
    cv2.destroyAllWindows()
    print("Test completed!")

if __name__ == "__main__":
    test_ui()

