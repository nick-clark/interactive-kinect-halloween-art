#!/usr/bin/env python3

import cv2
import numpy as np
import time
import random
import os

class WorkingGhostTracker:
    def __init__(self):
        # Default parameters - User's preferred settings
        self.depth_min = 217      # mm = 0.7120 feet
        self.depth_max = 3626     # mm = 11.8943 feet
        self.video_opacity = 0.3
        self.ghost_alpha = 0.7
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        
        # Ghost sprites - load all ghost images
        self.ghost_sprites = []
        self.load_ghost_sprites()
        
        # Track ghost assignments for each person
        self.person_ghost_map = {}  # Maps person ID to ghost sprite
        self.person_fade_data = {}  # Maps person ID to fade cycle data
        
        # Background capture
        self.background_image = None
        self.capture_background = False
        
        # Create control panel
        self.setup_control_panel()

    def setup_control_panel(self):
        """Create a simple OpenCV control panel"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 500, 400)
        
        # Distance controls in feet (4 decimal places)
        min_feet = self.depth_min / 304.8
        max_feet = self.depth_max / 304.8
        cv2.createTrackbar('Min Dist', 'Control Panel', int(min_feet * 10000), 100000, self.update_min_distance_feet)
        cv2.createTrackbar('Max Dist', 'Control Panel', int(max_feet * 10000), 200000, self.update_max_distance_feet)
        
        # Video opacity
        cv2.createTrackbar('Video Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        
        # Background capture button
        cv2.createTrackbar('Capture BG', 'Control Panel', 0, 1, self.capture_background_callback)

    def update_min_distance_feet(self, val):
        """Update min distance from trackbar"""
        feet = val / 10000.0
        self.depth_min = int(feet * 304.8)
        print(f"Min distance set to {feet:.4f} feet ({self.depth_min}mm)")

    def update_max_distance_feet(self, val):
        """Update max distance from trackbar"""
        feet = val / 10000.0
        self.depth_max = int(feet * 304.8)
        print(f"Max distance set to {feet:.4f} feet ({self.depth_max}mm)")

    def update_video_opacity(self, val):
        """Update video opacity from trackbar"""
        self.video_opacity = val / 100.0
        print(f"Video opacity set to {self.video_opacity:.2f}")

    def capture_background_callback(self, val):
        """Callback for background capture button"""
        if val == 1:  # Button was pressed
            self.capture_background = True
            print("✅ Background capture triggered!")
            # Reset button to 0 after capturing
            cv2.setTrackbarPos('Capture BG', 'Control Panel', 0)

    def load_ghost_sprites(self):
        """Load all ghost sprite images from sprites folder"""
        sprite_folder = "sprites"
        
        if not os.path.exists(sprite_folder):
            print(f"Sprite folder '{sprite_folder}' not found!")
            return
        
        # Load all ghost images
        for filename in sorted(os.listdir(sprite_folder)):
            if filename.endswith('.png'):
                sprite_path = os.path.join(sprite_folder, filename)
                sprite = cv2.imread(sprite_path, cv2.IMREAD_UNCHANGED)
                if sprite is not None:
                    self.ghost_sprites.append(sprite)
                    print(f"Loaded ghost sprite: {filename}")
                else:
                    print(f"Failed to load: {filename}")
        
        if len(self.ghost_sprites) == 0:
            print("No ghost sprites loaded!")
        else:
            print(f"Total ghosts loaded: {len(self.ghost_sprites)}")

    def run(self):
        """Main loop - test version without Kinect"""
        print("👻 Ghost Tracking Test (No Kinect)")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame")
        
        frame_count = 0
        while True:
            # Create proper test frames instead of random noise
            rgb = np.zeros((480, 640, 3), dtype=np.uint8)
            rgb[:] = (50, 50, 50)  # Dark gray background
            
            # Create a proper depth map
            depth = np.ones((480, 640), dtype=np.uint16) * 2000  # Default depth
            
            # Add some test content to RGB
            cv2.putText(rgb, f"Test Frame {frame_count}", (50, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(rgb, "Simulated Kinect Feed", (50, 100), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Mirror RGB feed for easier interaction
            rgb_mirrored = cv2.flip(rgb, 1)
            
            # Capture background if button was pressed
            if self.capture_background:
                self.background_image = rgb_mirrored.copy()
                print("Background captured! You can now step in front of the camera.")
                self.capture_background = False
            
            # Create output with video opacity
            if self.background_image is not None:
                # Use captured background
                output = self.background_image.copy()
                if self.video_opacity > 0:
                    # Blend current frame with background based on opacity
                    output = cv2.addWeighted(self.background_image, 1 - self.video_opacity,
                                            rgb_mirrored, self.video_opacity, 0)
            elif self.video_opacity > 0:
                # Use live feed as background
                output = rgb_mirrored.copy()
                output = cv2.addWeighted(output, self.video_opacity,
                                       np.zeros_like(output), 1 - self.video_opacity, 0)
            else:
                output = np.zeros_like(rgb_mirrored)
            
            # Mirror depth feed to match RGB
            depth_mirrored = cv2.flip(depth, 1)
            
            # Simulate person detection with some test blobs
            if frame_count % 100 < 50:  # Show "detected" people every 50 frames
                # Add some test person shapes (rectangles to simulate bounding boxes)
                cv2.rectangle(output, (270, 200), (370, 400), (0, 255, 0), 2)
                cv2.putText(output, "Simulated Person 1", (270, 190), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if frame_count % 100 < 25:  # Sometimes show 2 people
                    cv2.rectangle(output, (150, 250), (250, 450), (0, 255, 0), 2)
                    cv2.putText(output, "Simulated Person 2", (150, 240), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Display output
            cv2.imshow("👻 Ghost Tracking - Main View", output)
            
            # Show debug depth mask
            debug_mask = self.normalize_depth(depth_mirrored)
            cv2.imshow("🔍 Depth Map & Detection", debug_mask)
            
            # Handle key presses
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"ghost_tracker_{timestamp}.png", output)
                print(f"Saved ghost_tracker_{timestamp}.png")
            
            frame_count += 1
        
        cv2.destroyAllWindows()

    def normalize_depth(self, depth_mm):
        """Normalize depth to 0-255 gradient"""
        d = depth_mm.copy().astype(np.float32)
        d[d <= 0] = np.nan
        near, far = float(self.depth_min), float(self.depth_max)
        d = np.clip(d, near, far)
        d = (d - near) / (far - near)  # 0..1
        d = (1.0 - d) * 255.0          # invert so near = bright
        d[np.isnan(d)] = 0
        return d.astype(np.uint8)

if __name__ == "__main__":
    try:
        tracker = WorkingGhostTracker()
        tracker.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
