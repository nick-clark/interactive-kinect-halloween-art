#!/usr/bin/env python3

import freenect
import cv2
import numpy as np
import time
import random
import os

class GhostTrackerFixed:
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

    def get_depth_data(self):
        """Get depth data from Kinect"""
        try:
            depth, _ = freenect.sync_get_depth()
            return depth
        except:
            return None

    def get_rgb_data(self):
        """Get RGB data from Kinect"""
        try:
            rgb, _ = freenect.sync_get_video()
            return rgb
        except:
            return None

    def normalize_depth(self, depth_mm):
        """Normalize depth to 0-255 gradient like kinect_viewer"""
        d = depth_mm.copy().astype(np.float32)
        d[d <= 0] = np.nan
        near, far = float(self.depth_min), float(self.depth_max)
        d = np.clip(d, near, far)
        d = (d - near) / (far - near)  # 0..1
        d = (1.0 - d) * 255.0          # invert so near = bright
        d[np.isnan(d)] = 0
        return d.astype(np.uint8)

    def find_all_person_blobs(self, depth):
        """Find all person-like blobs in the depth map using gradient"""
        # Normalize depth to 0-255 gradient (like kinect_viewer)
        depth_normalized = self.normalize_depth(depth)
        
        # Threshold to find bright areas (white = person/subject)
        _, mask = cv2.threshold(depth_normalized, 200, 255, cv2.THRESH_BINARY)
        
        # Find contours on the mask (white areas = people)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        person_blobs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Person-like size range
            if area > 5000:  # Minimum person size
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    if 0 <= cy < depth.shape[0] and 0 <= cx < depth.shape[1]:
                        blob_depth = depth[cy, cx]
                        person_blobs.append((cx, cy, blob_depth, contour))
        
        # Sort by area (largest first)
        person_blobs.sort(key=lambda x: cv2.contourArea(x[3]), reverse=True)
        
        return person_blobs

    def assign_ghost_to_person(self, person_id):
        """Assign a random ghost to a person if they don't have one yet"""
        if person_id not in self.person_ghost_map:
            if len(self.ghost_sprites) > 0:
                self.person_ghost_map[person_id] = random.choice(self.ghost_sprites)
                # Initialize fade data for this person
                cycle_time = random.uniform(0.5, 2.0)
                self.person_fade_data[person_id] = {
                    'cycle_time': cycle_time,
                    'start_time': time.time(),
                    'min_opacity': 0.4,
                    'max_opacity': 0.8
                }
                print(f"Assigned ghost to person {person_id} with {cycle_time:.2f}s fade cycle")
        return self.person_ghost_map.get(person_id, None)

    def get_current_opacity(self, person_id):
        """Calculate current opacity for a person's ghost based on fade cycle"""
        if person_id not in self.person_fade_data:
            return self.ghost_alpha
        
        fade_data = self.person_fade_data[person_id]
        elapsed = time.time() - fade_data['start_time']
        
        # Calculate position in cycle (0 to 1)
        cycle_position = (elapsed % fade_data['cycle_time']) / fade_data['cycle_time']
        
        # Use sine wave for smooth fade in/out
        sine_value = (np.sin(cycle_position * 2 * np.pi) + 1) / 2
        
        # Map to min/max opacity range
        opacity = fade_data['min_opacity'] + sine_value * (fade_data['max_opacity'] - fade_data['min_opacity'])
        
        return opacity

    def run(self):
        """Main loop"""
        print("👻 Ghost Tracking with Real Kinect")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame")
        print("Looking for Kinect...")
        
        while True:
            # Get data from Kinect
            depth = self.get_depth_data()
            rgb = self.get_rgb_data()
            
            if depth is None or rgb is None:
                print("Waiting for Kinect...", end='\r')
                time.sleep(0.1)
                continue
            
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
            
            # Find all person blobs
            person_blobs = self.find_all_person_blobs(depth_mirrored)
            
            if person_blobs:
                # Draw ghost sprite on each detected blob
                for i, blob_data in enumerate(person_blobs):
                    cx, cy, blob_depth, contour = blob_data
                    person_id = i + 1
                    
                    # Draw bounding box around blob
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    # Get or assign ghost sprite for this person
                    ghost_sprite = self.assign_ghost_to_person(person_id)
                    
                    if ghost_sprite is not None:
                        # Get current opacity for this person's fade cycle
                        current_opacity = self.get_current_opacity(person_id)
                        
                        # Draw ghost sprite proportionally scaled to bounding box height
                        sprite_h, sprite_w = ghost_sprite.shape[:2]
                        aspect_ratio = sprite_w / sprite_h
                        
                        # Use bounding box height as sprite height
                        ghost_height = h
                        ghost_width = int(ghost_height * aspect_ratio)
                        
                        # Resize sprite maintaining aspect ratio
                        ghost_resized = cv2.resize(ghost_sprite, (ghost_width, ghost_height))
                        
                        # Center sprite in bounding box
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        # Calculate position to center the sprite
                        x1 = max(0, center_x - ghost_width // 2)
                        y1 = max(0, center_y - ghost_height // 2)
                        x2 = min(output.shape[1], center_x + ghost_width // 2)
                        y2 = min(output.shape[0], center_y + ghost_height // 2)
                        
                        # Adjust if needed
                        actual_w = x2 - x1
                        actual_h = y2 - y1
                        if actual_w != ghost_width or actual_h != ghost_height:
                            ghost_resized = cv2.resize(ghost_resized, (actual_w, actual_h))
                        
                        # Blend sprite with background using current opacity
                        if ghost_resized.shape[2] == 4:
                            alpha = ghost_resized[:, :, 3] / 255.0
                            ghost_rgb = ghost_resized[:, :, :3]
                        else:
                            alpha = np.ones((ghost_resized.shape[0], ghost_resized.shape[1]))
                            ghost_rgb = ghost_resized
                        
                        roi = output[y1:y2, x1:x2]
                        for c in range(3):
                            roi[:, :, c] = (1 - alpha * current_opacity) * roi[:, :, c] + \
                                          (alpha * current_opacity) * ghost_rgb[:, :, c]
                    
                    # Draw person number and distance
                    distance_feet = blob_depth / 304.8
                    cv2.putText(output, f"Person {person_id}: {distance_feet:.2f}ft", 
                               (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Display status
                cv2.putText(output, f"{len(person_blobs)} person(s) detected!", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # Show current distance range in feet
                min_feet = self.depth_min / 304.8
                max_feet = self.depth_max / 304.8
                cv2.putText(output, "No person detected - adjust distance range", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(output, f"Range: {min_feet:.4f} - {max_feet:.4f} feet", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display output
            cv2.imshow("👻 Ghost Tracking - Main View", output)
            
            # Show debug depth mask with gradient
            debug_mask = self.normalize_depth(depth_mirrored)
            if person_blobs:
                # Draw detected contours on gradient
                for blob_data in person_blobs:
                    _, _, _, contour = blob_data
                    cv2.drawContours(debug_mask, [contour], -1, 0, 2)  # Draw in black for visibility
            cv2.imshow("🔍 Depth Map & Detection", debug_mask)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"ghost_tracker_{timestamp}.png", output)
                print(f"Saved ghost_tracker_{timestamp}.png")
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        tracker = GhostTrackerFixed()
        tracker.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()

