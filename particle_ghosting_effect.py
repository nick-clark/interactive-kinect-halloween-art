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

class Particle:
    def __init__(self, x, y, screen_width, screen_height):
        self.x = x
        self.y = y
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Random initial velocity
        self.vx = random.uniform(-3.0, 3.0)
        self.vy = random.uniform(-3.0, 3.0)
        
        # Store initial speed for decay reference
        self.initial_speed = math.sqrt(self.vx**2 + self.vy**2)
        self.current_speed = self.initial_speed
        
        # Collision state
        self.was_hit = False
        self.hit_frames_ago = 0
        
        # Visual properties
        self.size = 3
        self.color = (0, 0, 255)  # Red dots (BGR format)
    
    def update(self, person_contours, speed_decay=0.98, min_speed=0.1, bounce_multiplier=1.5):
        """Update particle position and handle collisions"""
        # Check for collisions with person contours
        self.check_collisions(person_contours, bounce_multiplier)
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Handle screen boundaries (bounce off edges)
        if self.x <= 0 or self.x >= self.screen_width:
            self.vx = -self.vx
            self.x = max(0, min(self.screen_width, self.x))
        
        if self.y <= 0 or self.y >= self.screen_height:
            self.vy = -self.vy
            self.y = max(0, min(self.screen_height, self.y))
        
        # Apply speed decay if not recently hit
        if not self.was_hit:
            self.vx *= speed_decay
            self.vy *= speed_decay
            
            # Don't let speed go below minimum
            current_speed = math.sqrt(self.vx**2 + self.vy**2)
            if current_speed < min_speed and current_speed > 0:
                # Normalize and set to minimum speed
                if current_speed > 0:
                    self.vx = (self.vx / current_speed) * min_speed
                    self.vy = (self.vy / current_speed) * min_speed
        
        # Update hit state
        if self.was_hit:
            self.hit_frames_ago += 1
            if self.hit_frames_ago > 5:  # Reset hit state after 5 frames
                self.was_hit = False
                self.hit_frames_ago = 0
    
    def check_collisions(self, person_contours, bounce_multiplier):
        """Check if particle collides with any person contour"""
        for contour in person_contours:
            # Check if particle is inside the contour
            if cv2.pointPolygonTest(contour, (self.x, self.y), False) >= 0:
                # Calculate bounce direction (away from contour center)
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Calculate direction away from center
                    dx = self.x - cx
                    dy = self.y - cy
                    distance = math.sqrt(dx**2 + dy**2)
                    
                    if distance > 0:
                        # Normalize direction
                        dx /= distance
                        dy /= distance
                        
                        # Calculate bounce velocity proportional to current speed
                        current_speed = math.sqrt(self.vx**2 + self.vy**2)
                        bounce_speed = current_speed * bounce_multiplier
                        
                        # Set new velocity
                        self.vx = dx * bounce_speed
                        self.vy = dy * bounce_speed
                        
                        # Mark as hit
                        self.was_hit = True
                        self.hit_frames_ago = 0
                        break

class ParticleGhostingEffect:
    def __init__(self):
        # Default parameters - User's preferred settings
        self.depth_min = 217      # mm = 0.7120 feet
        self.depth_max = 3626     # mm = 11.8943 feet
        self.video_opacity = 0
        self.ghost_alpha = 0.7
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        
        # Video ghosting effect settings (optimized for performance)
        self.ghost_trail_length = 5  # Reduced from 10 to 5 for better performance
        self.ghost_trails = []  # List to store previous silhouettes
        self.silhouette_alpha = 0.4  # Increased alpha since we have fewer layers
        self.silhouette_color = (255, 255, 255)  # White silhouettes
        
        # Performance optimization settings
        self.frame_skip = 2  # Process every 2nd frame for silhouette detection
        self.frame_counter = 0
        self.last_silhouette = None
        
        # Particle system settings
        self.particle_count = 100
        self.particles = []
        self.min_speed = 0.5
        self.max_speed = 3.0
        self.speed_decay = 0.98
        self.min_speed_threshold = 0.1
        self.bounce_multiplier = 1.5
        
        # Background capture
        self.background_image = None
        self.capture_background = False
        self.debug_mode = False  # Default to off
        
        # Time exposure settings (3-second capture with noise reduction)
        self.time_exposure_duration = 10.0  # 3 seconds
        self.time_exposure_start_time = None
        self.time_exposure_frames_list = []
        
        # Initialize Kinect
        self.initialize_kinect()
        
        # Initialize particles
        self.initialize_particles()
        
        # Create control panel
        self.setup_control_panel()

    def setup_control_panel(self):
        """Create a simple OpenCV control panel"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 500, 350)
        
        # Distance controls in feet (4 decimal places)
        min_feet = self.depth_min / 304.8
        max_feet = self.depth_max / 304.8
        cv2.createTrackbar('Min Dist', 'Control Panel', int(min_feet * 10000), 100000, self.update_min_distance_feet)
        cv2.createTrackbar('Max Dist', 'Control Panel', int(max_feet * 10000), 200000, self.update_max_distance_feet)
        
        # Video opacity
        cv2.createTrackbar('Video Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        
        # Particle controls
        cv2.createTrackbar('Particle Count', 'Control Panel', self.particle_count, 500, self.update_particle_count)
        cv2.createTrackbar('Min Speed', 'Control Panel', int(self.min_speed * 10), 50, self.update_min_speed)
        cv2.createTrackbar('Max Speed', 'Control Panel', int(self.max_speed * 10), 50, self.update_max_speed)
        
        # Debug mode will be handled by mouse callback checkbox
        
        # Set up mouse callback for button
        cv2.setMouseCallback('Control Panel', self.mouse_callback)
        
        # Create the static control panel with button
        self.create_static_control_panel()

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
        
        # Give the system a moment to stabilize
        time.sleep(0.5)
        
        # Give the system a moment to settle
        time.sleep(1)
    
    def initialize_particles(self):
        """Initialize particle system"""
        print(f"🎆 Initializing {self.particle_count} particles...")
        self.particles = []
        
        # Create particles with random positions and velocities
        for i in range(self.particle_count):
            # Random position within screen bounds (assuming 640x480 for now)
            x = random.randint(0, 640)
            y = random.randint(0, 480)
            
            # Create particle with random velocity within speed range
            particle = Particle(x, y, 640, 480)
            
            # Set random velocity within speed range
            speed = random.uniform(self.min_speed, self.max_speed)
            angle = random.uniform(0, 2 * math.pi)
            particle.vx = speed * math.cos(angle)
            particle.vy = speed * math.sin(angle)
            particle.initial_speed = speed
            
            self.particles.append(particle)
        
        print(f"✅ {len(self.particles)} particles initialized!")
    
    def update_particles(self, person_contours):
        """Update all particles with collision detection"""
        for particle in self.particles:
            particle.update(person_contours, self.speed_decay, self.min_speed_threshold, self.bounce_multiplier)
    
    def render_particles(self, output_frame):
        """Render all particles as animated SVG-style bats"""
        for particle in self.particles:
            self.draw_svg_bat(output_frame, particle)
    
    def draw_svg_bat(self, frame, particle):
        """Draw an animated SVG-style bat based on the reference design"""
        x, y = int(particle.x), int(particle.y)
        
        # Calculate wing flap based on speed and time
        current_speed = math.sqrt(particle.vx**2 + particle.vy**2)
        wing_flap = math.sin(time.time() * 8 + current_speed * 3) * 0.3
        
        # Calculate body rotation based on movement direction
        if particle.vx != 0 or particle.vy != 0:
            body_angle = math.atan2(particle.vy, particle.vx)
        else:
            body_angle = 0
        
        # Bat size based on speed
        base_size = 8
        size_multiplier = 1 + (current_speed / 5.0)  # Scale with speed
        size = int(base_size * size_multiplier)
        
        # Draw bat body (ellipse)
        body_color = (50, 50, 50)  # Dark gray
        cv2.ellipse(frame, (x, y), (size//3, size//2), 
                   int(math.degrees(body_angle)), 0, 360, body_color, -1)
        
        # Draw wings with detailed structure
        self.draw_bat_wings(frame, x, y, size, wing_flap, body_angle, particle)
        
        # Draw glowing eyes
        eye_color = (0, 255, 255)  # Cyan glow
        eye_size = max(1, size // 8)
        cv2.circle(frame, (x - size//6, y - size//8), eye_size, eye_color, -1)
        cv2.circle(frame, (x + size//6, y - size//8), eye_size, eye_color, -1)
    
    def draw_bat_wings(self, frame, x, y, size, wing_flap, body_angle, particle):
        """Draw detailed bat wings with bone structure like the reference"""
        # Wing parameters
        wing_span = size * 2
        wing_height = size
        
        # Calculate wing positions with flapping
        left_wing_angle = body_angle - math.pi/2 + wing_flap
        right_wing_angle = body_angle + math.pi/2 - wing_flap
        
        # Draw left wing
        self.draw_detailed_wing(frame, x, y, wing_span, wing_height, 
                              left_wing_angle, particle, "left")
        
        # Draw right wing  
        self.draw_detailed_wing(frame, x, y, wing_span, wing_height,
                              right_wing_angle, particle, "right")
    
    def draw_detailed_wing(self, frame, x, y, span, height, angle, particle, side):
        """Draw a detailed wing with bone structure and scalloped edges"""
        # Wing color
        wing_color = (30, 30, 30)  # Dark gray
        bone_color = (100, 100, 100)  # Light gray for bones
        
        # Calculate wing points
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        
        # Wing base (connected to body)
        base_x = x + int(span//4 * cos_a)
        base_y = y + int(span//4 * sin_a)
        
        # Wing tip
        tip_x = x + int(span * cos_a)
        tip_y = y + int(span * sin_a)
        
        # Wing top edge (curved)
        top_x = x + int(span//2 * cos_a)
        top_y = y + int(span//2 * sin_a) - height//2
        
        # Create wing outline with scalloped edges
        wing_points = self.create_scalloped_wing_outline(base_x, base_y, tip_x, tip_y, top_x, top_y, side)
        
        # Draw wing fill
        if len(wing_points) > 2:
            cv2.fillPoly(frame, [np.array(wing_points, dtype=np.int32)], wing_color)
        
        # Draw bone structure (detailed lines like reference)
        self.draw_wing_bones(frame, base_x, base_y, tip_x, tip_y, top_x, top_y, bone_color)
    
    def create_scalloped_wing_outline(self, base_x, base_y, tip_x, tip_y, top_x, top_y, side):
        """Create wing outline with scalloped edges like the reference"""
        points = []
        
        # Start from base
        points.append([base_x, base_y])
        
        # Create scalloped edge along the wing
        num_scallops = 4
        for i in range(num_scallops + 1):
            t = i / num_scallops
            
            # Interpolate along wing edge
            edge_x = int(base_x + (tip_x - base_x) * t)
            edge_y = int(base_y + (tip_y - base_y) * t)
            
            # Add scallop (sharp points)
            if i < num_scallops:
                # Create sharp point
                scallop_x = edge_x + (5 if side == "right" else -5)
                scallop_y = edge_y + 3
                points.append([scallop_x, scallop_y])
            
            points.append([edge_x, edge_y])
        
        # Add top edge
        points.append([top_x, top_y])
        
        return points
    
    def draw_wing_bones(self, frame, base_x, base_y, tip_x, tip_y, top_x, top_y, bone_color):
        """Draw wing bone structure like the reference"""
        # Main bone (from base to tip)
        cv2.line(frame, (base_x, base_y), (tip_x, tip_y), bone_color, 1)
        
        # Secondary bones (from base to various points)
        for i in range(3):
            t = (i + 1) / 4
            bone_x = int(base_x + (tip_x - base_x) * t)
            bone_y = int(base_y + (tip_y - base_y) * t)
            
            # Draw bone line
            cv2.line(frame, (base_x, base_y), (bone_x, bone_y), bone_color, 1)
            
            # Add small branches
            branch_x = bone_x + (5 if i % 2 == 0 else -5)
            branch_y = bone_y + 2
            cv2.line(frame, (bone_x, bone_y), (branch_x, branch_y), bone_color, 1)

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
    
    def update_particle_count(self, val):
        """Update particle count from trackbar"""
        if val != self.particle_count:
            self.particle_count = val
            print(f"Particle count set to {self.particle_count}")
            # Reinitialize particles with new count
            self.initialize_particles()
    
    def update_min_speed(self, val):
        """Update minimum speed from trackbar"""
        self.min_speed = val / 10.0
        print(f"Min speed set to {self.min_speed:.1f}")
    
    def update_max_speed(self, val):
        """Update maximum speed from trackbar"""
        self.max_speed = val / 10.0
        print(f"Max speed set to {self.max_speed:.1f}")
    
    def average_frames(self, frames_list):
        """Average multiple frames to create a higher quality background image"""
        if not frames_list:
            return None
        
        # Convert frames to float for averaging
        float_frames = [frame.astype(np.float32) for frame in frames_list]
        
        # Calculate the average
        averaged = np.mean(float_frames, axis=0)
        
        # Convert back to uint8
        result = np.clip(averaged, 0, 255).astype(np.uint8)
        
        print(f"⏱️ Averaged {len(frames_list)} frames for improved quality")
        return result
    
    def average_frames_with_noise_reduction(self, frames_list):
        """Average multiple frames with noise reduction for high-quality background"""
        if not frames_list:
            return None
        
        print(f"⏱️ Processing {len(frames_list)} frames with noise reduction...")
        
        # Convert frames to float for processing
        float_frames = [frame.astype(np.float32) for frame in frames_list]
        
        # Calculate the average
        averaged = np.mean(float_frames, axis=0)
        
        # Convert back to uint8 for OpenCV processing
        averaged_uint8 = np.clip(averaged, 0, 255).astype(np.uint8)
        
        # Apply noise reduction using bilateral filter
        # This preserves edges while reducing noise
        noise_reduced = cv2.bilateralFilter(averaged_uint8, 9, 75, 75)
        
        # Additional Gaussian blur for extra smoothness (optional)
        # noise_reduced = cv2.GaussianBlur(noise_reduced, (3, 3), 0)
        
        print(f"⏱️ Applied noise reduction to {len(frames_list)} frames")
        return noise_reduced


    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse clicks on the control panel"""
        if event == cv2.EVENT_LBUTTONDOWN:
            print(f"Mouse click detected at ({x}, {y})")
            
            # Check if click is on the Capture BG button
            # Button area: x=50 to x=200, y=250 to y=300
            if 50 <= x <= 200 and 250 <= y <= 300:
                self.capture_background = True
                print("✅ Background capture triggered!")
            
            # Check if click is on the Debug checkbox
            # Checkbox area: x=50 to x=80, y=200 to y=230
            elif 50 <= x <= 80 and 200 <= y <= 230:
                self.debug_mode = not self.debug_mode
                print(f"🔧 Debug mode {'enabled' if self.debug_mode else 'disabled'}")
                # Redraw the control panel to update checkbox state
                self.create_static_control_panel()
            
            else:
                print(f"Click outside interactive areas")
    
    def create_static_control_panel(self):
        """Create the static control panel with button and checkbox"""
        # Create a black background
        panel = np.zeros((350, 500, 3), dtype=np.uint8)
        
        # Draw debug checkbox
        checkbox_x, checkbox_y = 50, 200
        checkbox_size = 30
        
        # Checkbox border
        cv2.rectangle(panel, (checkbox_x, checkbox_y), 
                     (checkbox_x + checkbox_size, checkbox_y + checkbox_size), 
                     (255, 255, 255), 2)
        
        # Checkbox fill if checked
        if self.debug_mode:
            cv2.rectangle(panel, (checkbox_x + 3, checkbox_y + 3), 
                         (checkbox_x + checkbox_size - 3, checkbox_y + checkbox_size - 3), 
                         (0, 255, 0), -1)
        
        # Checkbox label
        cv2.putText(panel, 'Debugging On', (checkbox_x + 40, checkbox_y + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Draw Capture BG button
        button_color = (0, 255, 0)  # Green button
        cv2.rectangle(panel, (50, 250), (200, 300), button_color, -1)
        cv2.rectangle(panel, (50, 250), (200, 300), (255, 255, 255), 2)  # White border
        
        # Add button text
        cv2.putText(panel, 'Capture BG', (60, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        # Add instructions
        cv2.putText(panel, 'Click checkbox to toggle debug mode', (10, 320), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(panel, 'Click "Capture BG" for high-quality background (3-second capture)', (10, 340), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Show the static panel once
        cv2.imshow('Control Panel', panel)
        cv2.waitKey(1)  # Ensure the window is displayed

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


    def create_silhouette_from_depth(self, depth_map, person_mask):
        """Create a silhouette from the depth map for the detected person"""
        # Create a silhouette by using the person mask
        silhouette = np.zeros_like(depth_map, dtype=np.uint8)
        silhouette[person_mask] = 255
        
        # Convert to 3-channel for blending
        silhouette_3ch = cv2.cvtColor(silhouette, cv2.COLOR_GRAY2BGR)
        
        return silhouette_3ch

    def get_depth_data(self):
        """Get depth data from Kinect"""
        try:
            depth, _ = freenect.sync_get_depth()
            if depth is None:
                return None
            return depth
        except Exception as e:
            # Don't print every error to avoid spam
            return None

    def get_rgb_data(self):
        """Get RGB data from Kinect"""
        try:
            rgb, _ = freenect.sync_get_video()
            if rgb is None:
                return None
            return rgb
        except Exception as e:
            # Don't print every error to avoid spam
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
    
    def add_silhouette_to_trail(self, silhouette):
        """Add a silhouette to the ghost trail"""
        self.ghost_trails.append(silhouette.copy())
        
        # Keep only the last N frames
        if len(self.ghost_trails) > self.ghost_trail_length:
            self.ghost_trails.pop(0)
    
    
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
        print("🦇 Bat Particle Effect")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame")
        print("Looking for Kinect...")
        
        try:
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
                    cv2.imshow("👻 Video Ghosting Effect - Main View", test_output)
                    cv2.imshow("🔍 Depth Map & Detection", test_output)
                    time.sleep(0.1)
                    continue
                
                # Mirror RGB feed for easier interaction
                rgb_mirrored = cv2.flip(rgb, 1)
                
                # Capture background if button was pressed
                if self.capture_background:
                    # Start time exposure capture (3 seconds)
                    self.time_exposure_start_time = time.time()
                    self.time_exposure_frames_list = []
                    print(f"⏱️ Starting 3-second time exposure capture...")
                    self.capture_background = False  # Reset flag, will be handled in time exposure logic
                
                # Handle time exposure capture (3-second duration)
                if self.time_exposure_start_time is not None:
                    elapsed_time = time.time() - self.time_exposure_start_time
                    if elapsed_time < self.time_exposure_duration:
                        # Still capturing - add frame to list
                        self.time_exposure_frames_list.append(rgb_mirrored.copy())
                        remaining_time = self.time_exposure_duration - elapsed_time
                        print(f"⏱️ Time exposure: {elapsed_time:.1f}s / {self.time_exposure_duration:.1f}s (frames: {len(self.time_exposure_frames_list)})")
                        
                        # Progress will be shown on the final output layer later
                    else:
                        # Time exposure complete - process frames
                        print("⏱️ Processing time exposure frames with noise reduction...")
                        self.background_image = self.average_frames_with_noise_reduction(self.time_exposure_frames_list)
                        print(f"✅ 3-second time exposure background captured! ({len(self.time_exposure_frames_list)} frames)")
                        print("You can now step in front of the camera.")
                        # Mark as completed
                        self.time_exposure_start_time = None
                        self.time_exposure_frames_list = []
                
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
                
                # Performance optimization: only process silhouettes every few frames
                self.frame_counter += 1
                should_process_silhouette = (self.frame_counter % self.frame_skip == 0)
                
                # Find all person blobs
                person_blobs = self.find_all_person_blobs(depth_mirrored)
                
                # Update particles with collision detection
                person_contours = [blob_data[3] for blob_data in person_blobs] if person_blobs else []
                self.update_particles(person_contours)
                
                if person_blobs and should_process_silhouette:
                    # Create combined silhouette from all detected people
                    combined_silhouette = np.zeros_like(depth_mirrored, dtype=np.uint8)
                    
                    for i, blob_data in enumerate(person_blobs):
                        # Extract blob data
                        if len(blob_data) == 5:
                            cx, cy, blob_depth, contour, person_id = blob_data
                        else:
                            cx, cy, blob_depth, contour = blob_data
                            person_id = i + 1
                        
                        # Draw bounding box around blob (debug mode only)
                        x, y, w, h = cv2.boundingRect(contour)
                        if self.debug_mode:
                            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        
                        # Create mask for this person
                        person_mask = np.zeros_like(depth_mirrored, dtype=np.uint8)
                        cv2.fillPoly(person_mask, [contour], 255)
                        
                        # Add to combined silhouette
                        combined_silhouette = cv2.bitwise_or(combined_silhouette, person_mask)
                        
                        # Draw person number and distance (debug mode only)
                        if self.debug_mode:
                            distance_feet = blob_depth / 304.8
                            cv2.putText(output, f"Person {person_id}: {distance_feet:.2f}ft", 
                                       (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    
                    # Add current silhouette to trail
                    if np.any(combined_silhouette):
                        self.add_silhouette_to_trail(combined_silhouette)
                        self.last_silhouette = combined_silhouette.copy()
                elif person_blobs and not should_process_silhouette:
                    # Use last silhouette for skipped frames
                    if self.last_silhouette is not None:
                        self.add_silhouette_to_trail(self.last_silhouette)
                
                # Start with background if available, otherwise use current frame
                if self.background_image is not None:
                    output = self.background_image.copy()
                else:
                    output = rgb_mirrored.copy()
                
                # Draw all silhouettes in the trail with decreasing opacity (optimized)
                for i, trail_silhouette in enumerate(self.ghost_trails):
                    if np.any(trail_silhouette):
                        # Calculate opacity (newer silhouettes are more opaque)
                        opacity = self.silhouette_alpha * (i + 1) / len(self.ghost_trails)
                        
                        # Create mask for silhouette (white areas only)
                        mask = trail_silhouette > 0
                        
                        # Apply silhouette with transparency using vectorized operations
                        silhouette_color_array = np.array(self.silhouette_color, dtype=np.uint8)
                        output[mask] = (1 - opacity) * output[mask] + opacity * silhouette_color_array
                
                # Display status (debug mode only)
                if self.debug_mode:
                    cv2.putText(output, f"{len(person_blobs)} person(s) detected!", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    # Show current distance range in feet (debug mode only)
                    if self.debug_mode:
                        min_feet = self.depth_min / 304.8
                        max_feet = self.depth_max / 304.8
                        cv2.putText(output, "No person detected - adjust distance range", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        cv2.putText(output, f"Range: {min_feet:.4f} - {max_feet:.4f} feet", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Add time exposure countdown text to top layer (always visible)
                if self.time_exposure_start_time is not None:
                    elapsed_time = time.time() - self.time_exposure_start_time
                    remaining_time = self.time_exposure_duration - elapsed_time
                    if remaining_time > 0:
                        cv2.putText(output, f"Capturing background... {remaining_time:.1f}s remaining", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Render particles on top of everything
                self.render_particles(output)
                
                # Display output
                cv2.imshow("🦇 Bat Particle Effect - Main View", output)
                
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
                    cv2.imwrite(f"video_ghosting_effect_{timestamp}.png", output)
                    print(f"Saved video_ghosting_effect_{timestamp}.png")
            
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("🧹 Cleaning up...")
            cv2.destroyAllWindows()
            # Safe cleanup of freenect
            try:
                freenect.sync_stop()
            except:
                pass  # Ignore cleanup errors
            print("✅ Cleanup complete")

if __name__ == "__main__":
    try:
        effect = ParticleGhostingEffect()
        effect.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()
