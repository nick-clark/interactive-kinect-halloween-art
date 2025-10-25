#!/usr/bin/env python3

import freenect
import cv2
import numpy as np
import time

class AsyncKinectViewer:
    def __init__(self):
        self.device = None
        self.running = False
        
    def init_kinect(self):
        """Initialize Kinect using async API"""
        try:
            print("Initializing Kinect...")
            freenect.init()
            
            # Open device
            self.device = freenect.open_device(freenect.init(), 0)
            if self.device is None:
                print("❌ Could not open Kinect device")
                return False
            
            print("✅ Kinect device opened!")
            
            # Set video and depth modes
            freenect.set_video_mode(self.device, freenect.RESOLUTION_MEDIUM, freenect.VIDEO_RGB)
            freenect.set_depth_mode(self.device, freenect.RESOLUTION_MEDIUM, freenect.DEPTH_MM)
            
            print("✅ Modes set successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error initializing Kinect: {e}")
            return False
    
    def start_streams(self):
        """Start video and depth streams"""
        try:
            print("Starting streams...")
            freenect.start_video(self.device)
            freenect.start_depth(self.device)
            self.running = True
            print("✅ Streams started!")
            return True
        except Exception as e:
            print(f"❌ Error starting streams: {e}")
            return False
    
    def get_frames(self):
        """Get video and depth frames"""
        try:
            # Get video frame
            video_frame = freenect.sync_get_video()
            depth_frame = freenect.sync_get_depth()
            
            return video_frame, depth_frame
        except Exception as e:
            print(f"❌ Error getting frames: {e}")
            return None, None
    
    def stop_streams(self):
        """Stop video and depth streams"""
        try:
            if self.device and self.running:
                freenect.stop_video(self.device)
                freenect.stop_depth(self.device)
                freenect.close_device(self.device)
                self.running = False
                print("✅ Streams stopped!")
        except Exception as e:
            print(f"❌ Error stopping streams: {e}")
    
    def run(self):
        """Main loop"""
        if not self.init_kinect():
            return
        
        if not self.start_streams():
            return
        
        print("👻 Async Kinect Viewer")
        print("Press 'q' to quit, 's' to save a frame")
        
        try:
            while True:
                # Get frames
                video, depth = self.get_frames()
                
                if video is not None and depth is not None:
                    # Display video
                    cv2.imshow("RGB Video", video)
                    
                    # Display depth (normalized)
                    depth_normalized = self.normalize_depth(depth)
                    cv2.imshow("Depth Map", depth_normalized)
                    
                    # Handle key presses
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('s'):
                        timestamp = int(time.time() * 1000)
                        cv2.imwrite(f"kinect_rgb_{timestamp}.png", video)
                        cv2.imwrite(f"kinect_depth_{timestamp}.png", depth_normalized)
                        print(f"Saved frames: kinect_rgb_{timestamp}.png, kinect_depth_{timestamp}.png")
                else:
                    print("Waiting for frames...", end='\r')
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.stop_streams()
            cv2.destroyAllWindows()
    
    def normalize_depth(self, depth_mm):
        """Normalize depth to 0-255 for display"""
        d = depth_mm.copy().astype(np.float32)
        d[d <= 0] = np.nan
        near, far = 500.0, 4500.0
        d = np.clip(d, near, far)
        d = (d - near) / (far - near)  # 0..1
        d = (1.0 - d) * 255.0          # invert so near = bright
        d[np.isnan(d)] = 0
        return d.astype(np.uint8)

if __name__ == "__main__":
    viewer = AsyncKinectViewer()
    viewer.run()

