import freenect
import cv2
import numpy as np
import time
import math
import random
import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import subprocess

class SimplePersonGhost:
    def __init__(self):
        # Default parameters - User's preferred settings
        self.depth_min = 217      # mm = 0.7120 feet
        self.depth_max = 3626     # mm = 11.8943 feet
        self.video_opacity = 0.3
        self.ghost_alpha = 0.7
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        
        # Motor control settings
        self.motor_enabled = False
        self.motor_tilt = 0  # -30 to +30 degrees
        
        # Ghost sprites - load all ghost images
        self.ghost_sprites = []
        self.load_ghost_sprites()
        
        # Track ghost assignments for each person
        self.person_ghost_map = {}  # Maps person ID to ghost sprite
        self.person_fade_data = {}  # Maps person ID to fade cycle data
        
        # Background capture
        self.background_image = None
        self.capture_background = False
        
        # Initialize Kinect
        self.initialize_kinect()
        
        # Create control panel
        self.setup_control_panel()

    def setup_control_panel(self):
        """Create a simple OpenCV control panel"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 500, 300)
        
        # Distance controls in feet (4 decimal places)
        min_feet = self.depth_min / 304.8
        max_feet = self.depth_max / 304.8
        cv2.createTrackbar('Min Dist', 'Control Panel', int(min_feet * 10000), 100000, self.update_min_distance_feet)
        cv2.createTrackbar('Max Dist', 'Control Panel', int(max_feet * 10000), 200000, self.update_max_distance_feet)
        
        # Video opacity
        cv2.createTrackbar('Video Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        
        # Background capture button
        cv2.createTrackbar('Capture BG', 'Control Panel', 0, 1, self.capture_background_callback)

    def initialize_kinect(self):
        """Initialize Kinect by running the command-line tool to reset USB interface"""
        print("🔧 Initializing Kinect...")
        
        try:
            # Run the freenect-camtest command to reset the Kinect
            camtest_path = "./libfreenect/build/bin/freenect-camtest"
            if os.path.exists(camtest_path):
                print("   Running Kinect reset...")
                # Run the command for 3 seconds then stop it
                process = subprocess.Popen([camtest_path], 
                                         stdout=subprocess.PIPE, 
                                         stderr=subprocess.PIPE)
                time.sleep(3)  # Let it run for 3 seconds
                process.terminate()  # Stop it
                process.wait()
                print("   ✅ Kinect reset complete!")
            else:
                print("   ⚠️  freenect-camtest not found, skipping reset")
                
        except Exception as e:
            print(f"   ⚠️  Kinect reset failed: {e}")
            print("   Continuing anyway...")
        
        # Give the system a moment to settle
        time.sleep(1)

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

    def update_min_distance_ui(self, val):
        """Update min distance from UI slider"""
        feet = float(val)
        self.depth_min = int(feet * 304.8)
        self.min_dist_label.config(text=f"{feet:.4f} ft")
        
    def update_max_distance_ui(self, val):
        """Update max distance from UI slider"""
        feet = float(val)
        self.depth_max = int(feet * 304.8)
        self.max_dist_label.config(text=f"{feet:.4f} ft")
        
    def update_video_opacity_ui(self, val):
        """Update video opacity from UI slider"""
        self.video_opacity = float(val)
        self.video_opacity_label.config(text=f"{self.video_opacity:.2f}")
        
    def capture_background_ui(self):
        """Capture background from UI button"""
        self.capture_background = True
        self.background_status.config(text="✅ Background captured!")
        messagebox.showinfo("Background Captured", "Background image captured! You can now step in front of the camera.")
        
    def update_ui_status(self):
        """Update the status text in the UI"""
        if hasattr(self, 'status_text'):
            # Get current values
            min_feet = self.depth_min / 304.8
            max_feet = self.depth_max / 304.8
            detection_range = max_feet - min_feet
            
            # Count tracked people
            people_count = len(self.person_ghost_map) if hasattr(self, 'person_ghost_map') else 0
            
            # Build status text
            status = f"""Current Settings:
• Min Distance: {min_feet:.4f} ft ({self.depth_min}mm)
• Max Distance: {max_feet:.4f} ft ({self.depth_max}mm)
• Detection Range: {detection_range:.4f} ft
• Live Video Opacity: {self.video_opacity:.2f}
• Background: {'Captured' if self.background_image is not None else 'Not captured'}
• People Tracked: {people_count}
• Ghost Sprites Loaded: {len(self.ghost_sprites)}

Instructions:
• Adjust distance sliders to set detection range
• Use video opacity to blend live feed with background
• Click 'Capture Background' to snap a static background
• Ghosts will appear on detected people with random fade cycles
• Press 'q' in video window to quit, 's' to save frame"""
            
            # Update status text
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(1.0, status)
            
            # Update background status
            if hasattr(self, 'background_status'):
                if self.background_image is not None:
                    self.background_status.config(text="✅ Background ready")
                else:
                    self.background_status.config(text="❌ No background captured")
        
        # Schedule next update
        if hasattr(self, 'root'):
            self.root.after(1000, self.update_ui_status)

    def update_min_distance_feet(self, val):
        # Convert from feet*10000 back to mm
        feet = val / 10000.0
        self.depth_min = int(feet * 304.8)
        print(f"Min distance set to {feet:.4f} feet ({self.depth_min}mm)")

    def update_max_distance_feet(self, val):
        # Convert from feet*10000 back to mm
        feet = val / 10000.0
        self.depth_max = int(feet * 304.8)
        print(f"Max distance set to {feet:.4f} feet ({self.depth_max}mm)")

    def update_video_opacity(self, val):
        self.video_opacity = val / 100.0

    def update_ghost_alpha(self, val):
        self.ghost_alpha = val / 100.0

    def toggle_motor(self, val):
        self.motor_enabled = bool(val)
        print(f"Motor {'enabled' if self.motor_enabled else 'disabled'}")

    def update_motor_tilt(self, val):
        # Convert from 0-60 range to -30 to +30 degrees
        self.motor_tilt = val - 30
        # Motor control disabled to prevent crashes
        print(f"Motor tilt set to {self.motor_tilt} degrees (motor control disabled)")


    def set_motor_tilt(self, angle):
        """Set the Kinect motor tilt angle"""
        try:
            # freenect.set_tilt_degs() needs device context as first argument
            # For now, let's disable motor control to avoid crashes
            print(f"Motor tilt would be set to {angle} degrees (motor control disabled)")
        except Exception as e:
            print(f"Error setting motor tilt: {e}")
            print("Make sure Kinect is connected and freenect is working")


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
            if depth is None:
                return None
            return depth
        except Exception as e:
            print(f"Depth error: {e}")
            return None

    def get_rgb_data(self):
        """Get RGB data from Kinect"""
        try:
            rgb, _ = freenect.sync_get_video()
            if rgb is None:
                return None
            return rgb
        except Exception as e:
            print(f"RGB error: {e}")
            return None

    def find_person_center(self, depth):
        """Find the center of the largest person-like object"""
        # Create mask for objects within depth range
        mask = (depth > self.depth_min) & (depth < self.depth_max)
        mask = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, None, mask
            
        # Find largest contour (person)
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) < 10000:  # Minimum person size
            return None, None, mask
        
        # Calculate center of mass
        M = cv2.moments(largest_contour)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # Get depth at center
            if 0 <= cy < depth.shape[0] and 0 <= cx < depth.shape[1]:
                center_depth = depth[cy, cx]
                return (cx, cy, center_depth), largest_contour, mask
        
        return None, None, mask

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
    
    def assign_ghost_to_person(self, person_id):
        """Assign a random ghost to a person if they don't have one yet"""
        if person_id not in self.person_ghost_map:
            if len(self.ghost_sprites) > 0:
                self.person_ghost_map[person_id] = random.choice(self.ghost_sprites)
                # Initialize fade data for this person
                # Random cycle time between 0.5 and 2.0 seconds
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
        # Sine goes from -1 to 1, so we adjust to 0 to 1
        sine_value = (np.sin(cycle_position * 2 * np.pi) + 1) / 2
        
        # Map to min/max opacity range
        opacity = fade_data['min_opacity'] + sine_value * (fade_data['max_opacity'] - fade_data['min_opacity'])
        
        return opacity
    
    def track_people(self, current_blobs):
        """Track people across frames and maintain ghost assignments"""
        # Simple tracking based on centroid distance
        # If a person's centroid is close to a previous person, keep the same ID
        
        if not hasattr(self, 'previous_blobs'):
            self.previous_blobs = []
            self.person_counter = 0
        
        # Match current blobs to previous blobs
        matched = [False] * len(current_blobs)
        for prev_id, prev_blob in enumerate(self.previous_blobs):
            px, py = prev_blob['center']
            min_dist = float('inf')
            best_match = None
            
            for i, blob_data in enumerate(current_blobs):
                if matched[i]:
                    continue
                # Extract coordinates from blob data
                if len(blob_data) == 5:
                    cx, cy, blob_depth, contour, _ = blob_data
                else:
                    cx, cy, blob_depth, contour = blob_data
                
                dist = np.sqrt((cx - px)**2 + (cy - py)**2)
                if dist < min_dist and dist < 100:  # Threshold for matching
                    min_dist = dist
                    best_match = i
            
            if best_match is not None:
                matched[best_match] = True
                # Reuse the previous person ID
                blob_data = current_blobs[best_match]
                if len(blob_data) == 5:
                    cx, cy, blob_depth, contour, _ = blob_data
                else:
                    cx, cy, blob_depth, contour = blob_data
                current_blobs[best_match] = (cx, cy, blob_depth, contour, prev_blob['id'])
        
        # Assign new IDs to unmatched blobs
        for i, is_matched in enumerate(matched):
            if not is_matched:
                blob_data = current_blobs[i]
                if len(blob_data) == 5:
                    cx, cy, blob_depth, contour, _ = blob_data
                else:
                    cx, cy, blob_depth, contour = blob_data
                self.person_counter += 1
                current_blobs[i] = (cx, cy, blob_depth, contour, self.person_counter)
        
        # Update previous blobs
        self.previous_blobs = [{'center': (cx, cy), 'id': pid} for cx, cy, _, _, pid in current_blobs]
        
        return current_blobs
    
    def find_all_person_blobs(self, depth):
        """Find all person-like blobs in the depth map using gradient"""
        # Normalize depth to 0-255 gradient (like kinect_viewer)
        depth_normalized = self.normalize_depth(depth)
        
        # Threshold to find bright areas (white = person/subject)
        # Subject is white in the normalized depth (bright = close), so threshold for bright pixels
        # Don't invert - we want to track the white/bright objects
        _, mask = cv2.threshold(depth_normalized, 200, 255, cv2.THRESH_BINARY)
        
        # Find contours on the mask (white areas = people)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        person_blobs = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Person-like size range - adjust as needed
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
        
        # Track people across frames
        person_blobs = self.track_people(person_blobs)
        
        return person_blobs
    
    def get_person_center(self, person_contour):
        """Get the center of the person contour"""
        if person_contour is None:
            return None
        M = cv2.moments(person_contour)
        if M["m00"] > 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy)
        return None

    def calculate_ghost_position(self, person_center, hand_objects):
        """Calculate ghost position - center of person if no hands, between hands if hands detected"""
        if len(hand_objects) >= 2:
            # Use center between two largest hands
            hand_objects.sort(key=lambda x: cv2.contourArea(x[3]), reverse=True)
            hand1 = hand_objects[0]
            hand2 = hand_objects[1]
            
            center_x = (hand1[0] + hand2[0]) // 2
            center_y = (hand1[1] + hand2[1]) // 2
            center_depth = (hand1[2] + hand2[2]) // 2
            
            # Calculate distance between hands
            distance = math.sqrt((hand1[0] - hand2[0])**2 + (hand1[1] - hand2[1])**2)
            
            return (center_x, center_y, center_depth), distance, "between_hands"
        elif person_center is not None:
            # Use person center
            return person_center, 0, "person_center"
        else:
            return None, 0, "none"

    def draw_ghost_at_position(self, image, position, distance, mode):
        """Draw ghost sprite at the calculated position"""
        if position is None or self.ghost_sprite is None:
            return image
        
        center_x, center_y, center_depth = position
        
        # Calculate ghost size
        if mode == "between_hands":
            # Scale based on distance between hands
            base_size = 100
            scale_factor = max(0.5, min(2.0, distance / 200))
            ghost_size = int(base_size * scale_factor)
        else:
            # Fixed size for person center
            ghost_size = 120
        
        # Resize ghost sprite
        ghost_resized = cv2.resize(self.ghost_sprite, (ghost_size, ghost_size))
        
        # Calculate position to center the ghost
        half_size = ghost_size // 2
        x1 = max(0, center_x - half_size)
        y1 = max(0, center_y - half_size)
        x2 = min(image.shape[1], center_x + half_size)
        y2 = min(image.shape[0], center_y + half_size)
        
        # Adjust ghost_resized if it goes out of bounds
        if x2 - x1 != ghost_size or y2 - y1 != ghost_size:
            ghost_resized = cv2.resize(ghost_resized, (x2 - x1, y2 - y1))
        
        # Create alpha channel if needed
        if ghost_resized.shape[2] == 4:
            alpha = ghost_resized[:, :, 3] / 255.0
            ghost_rgb = ghost_resized[:, :, :3]
        else:
            alpha = np.ones((ghost_resized.shape[0], ghost_resized.shape[1]))
            ghost_rgb = ghost_resized
        
        # Blend ghost with background
        roi = image[y1:y2, x1:x2]
        for c in range(3):
            roi[:, :, c] = (1 - alpha * self.ghost_alpha) * roi[:, :, c] + \
                          (alpha * self.ghost_alpha) * ghost_rgb[:, :, c]
        
        return image

    def draw_hand_markers(self, image, hand_objects):
        """Draw X markers on detected hands for debugging"""
        for i, (x, y, depth, contour) in enumerate(hand_objects):
            # Draw red X mark (bigger and more visible)
            size = 20
            cv2.line(image, (x - size, y - size), (x + size, y + size), (0, 0, 255), 4)
            cv2.line(image, (x - size, y + size), (x + size, y - size), (0, 0, 255), 4)
            
            # Draw circle around X
            cv2.circle(image, (x, y), size + 5, (0, 255, 0), 3)
            
            # Draw distance text
            distance_feet = depth / 304.8
            cv2.putText(image, f"H{i+1}: {distance_feet:.2f}ft", 
                       (x - 40, y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # Draw area info
            area = cv2.contourArea(contour)
            cv2.putText(image, f"Area: {int(area)}", 
                       (x - 40, y + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    def run(self):
        """Main loop"""
        print("👻 Simple Person Ghost Tracking")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame")
        print("Looking for Kinect...")
        
        while True:
            # Get data from Kinect
            depth = self.get_depth_data()
            rgb = self.get_rgb_data()
            
            if depth is None or rgb is None:
                print("Waiting for Kinect...", end='\r')
                # Show a test pattern while waiting for Kinect
                test_output = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(test_output, "Waiting for Kinect...", (50, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.putText(test_output, "Make sure Kinect is plugged in and powered", (50, 280), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.imshow("👻 Ghost Tracking - Main View", test_output)
                cv2.imshow("🔍 Depth Map & Detection", test_output)
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
                    # Extract blob data (now includes person ID)
                    if len(blob_data) == 5:
                        cx, cy, blob_depth, contour, person_id = blob_data
                    else:
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
                        # Height matches bounding box, width maintains sprite's aspect ratio
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
                    # Extract contour from blob data
                    if len(blob_data) == 5:
                        _, _, _, contour, _ = blob_data
                    else:
                        _, _, _, contour = blob_data
                    cv2.drawContours(debug_mask, [contour], -1, 0, 2)  # Draw in black for visibility
            cv2.imshow("🔍 Depth Map & Detection", debug_mask)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"simple_person_ghost_{timestamp}.png", output)
                print(f"Saved simple_person_ghost_{timestamp}.png")
            
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        tracker = SimplePersonGhost()
        tracker.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()
