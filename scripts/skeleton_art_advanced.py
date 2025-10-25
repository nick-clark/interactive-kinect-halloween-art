#!/usr/bin/env python3
"""
Advanced Skeleton Art Installation with Control Panel
Uses Kinect depth data to draw cartoon skeletons with real-time parameter adjustment
"""

import freenect
import cv2
import numpy as np
import time
import math

class AdvancedSkeletonArt:
    def __init__(self):
        # Default parameters - these will be adjustable via trackbars
        self.depth_min = 914      # mm - 3 feet
        self.depth_max = 5029     # mm - 16.5 feet  
        self.min_contour_area = 5000  # Minimum size for a person
        self.video_opacity = 0.3  # Video feed opacity (0.0 = transparent, 1.0 = opaque)
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        self.ghost_alpha = 0.7  # Ghost transparency
        self.show_depth_vis = True
        self.show_contours = True
        
        # Sprite/image overlay settings
        self.use_sprite = True  # Enable sprites by default
        self.sprite_alpha = 0.8
        self.sprite_scale = 1.0
        self.sprite_rotation = 0
        self.sprite_image = None
        self.sprite_path = ""
        
        # Create control panel window
        self.setup_control_panel()
        
        # Try to automatically load the default skeleton sprite
        self.load_sprite("sprites/skeleton.png")
        
    def setup_control_panel(self):
        """Create a control panel with trackbars for real-time adjustment"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 400, 300)
        
        # Create trackbars
        cv2.createTrackbar('Min Distance (mm)', 'Control Panel', self.depth_min, 2000, self.update_min_distance)
        cv2.createTrackbar('Max Distance (mm)', 'Control Panel', self.depth_max, 6000, self.update_max_distance)
        cv2.createTrackbar('Min Area', 'Control Panel', self.min_contour_area, 20000, self.update_min_area)
        cv2.createTrackbar('Video Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        cv2.createTrackbar('Ghost Alpha', 'Control Panel', int(self.ghost_alpha * 100), 100, self.update_ghost_alpha)
        cv2.createTrackbar('Use Sprite', 'Control Panel', 1, 1, self.toggle_sprite)
        cv2.createTrackbar('Sprite Alpha', 'Control Panel', int(self.sprite_alpha * 100), 100, self.update_sprite_alpha)
        cv2.createTrackbar('Sprite Scale', 'Control Panel', int(self.sprite_scale * 100), 200, self.update_sprite_scale)
        cv2.createTrackbar('Show Depth', 'Control Panel', 1, 1, self.toggle_depth)
        cv2.createTrackbar('Show Contours', 'Control Panel', 1, 1, self.toggle_contours)
        
    def update_min_distance(self, val):
        self.depth_min = val
        
    def update_max_distance(self, val):
        self.depth_max = val
        
    def update_min_area(self, val):
        self.min_contour_area = val
        
    def update_video_opacity(self, val):
        self.video_opacity = val / 100.0
        
    def update_ghost_alpha(self, val):
        self.ghost_alpha = val / 100.0
        
    def toggle_sprite(self, val):
        self.use_sprite = bool(val)
        
    def update_sprite_alpha(self, val):
        self.sprite_alpha = val / 100.0
        
    def update_sprite_scale(self, val):
        self.sprite_scale = val / 100.0
        
    def toggle_depth(self, val):
        self.show_depth_vis = bool(val)
        
    def toggle_contours(self, val):
        self.show_contours = bool(val)
    
    def load_sprite(self, sprite_path):
        """Load a sprite image for overlay"""
        try:
            self.sprite_image = cv2.imread(sprite_path, cv2.IMREAD_UNCHANGED)
            if self.sprite_image is not None:
                self.sprite_path = sprite_path
                print(f"Sprite loaded: {sprite_path}")
                return True
            else:
                print(f"Failed to load sprite: {sprite_path}")
                return False
        except Exception as e:
            print(f"Error loading sprite: {e}")
            return False
    
    def morph_sprite_to_contour(self, image, contour):
        """Morph a sprite to fit the person's contour - draw sprite ONLY on the person"""
        if self.sprite_image is None or contour is None:
            return image
        
        # Create a mask for the person's contour
        person_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.fillPoly(person_mask, [contour], 255)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Resize sprite to fit the person's size
        sprite_resized = cv2.resize(self.sprite_image, (w, h))
        
        # Convert RGBA to RGB if needed
        if sprite_resized.shape[2] == 4:
            sprite_rgb = sprite_resized[:, :, :3]
        else:
            sprite_rgb = sprite_resized
        
        # Create result image
        result = image.copy()
        
        # Extract the region of interest
        roi = result[y:y+h, x:x+w].copy()
        person_roi_mask = person_mask[y:y+h, x:x+w]
        
        # Create sprite with transparency
        sprite_with_alpha = cv2.addWeighted(
            roi,
            1 - self.sprite_alpha,
            sprite_rgb,
            self.sprite_alpha,
            0
        )
        
        # Apply sprite ONLY where the person is (person_mask == 255)
        # Where person_mask is 255 (person), use sprite; where 0 (background), keep original
        for c in range(3):
            roi[:, :, c] = np.where(
                person_roi_mask == 255,
                sprite_with_alpha[:, :, c],
                roi[:, :, c]
            )
        
        result[y:y+h, x:x+w] = roi
        
        return result
    
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
    
    def find_person_contour(self, depth):
        """Find the largest person-like contour in the depth image"""
        # Create a mask for objects within our adjustable depth range
        mask = (depth > self.depth_min) & (depth < self.depth_max)
        mask = mask.astype(np.uint8) * 255
        
        # Apply some morphological operations to clean up the mask
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, mask
            
        # Find the largest contour (likely a person)
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) < self.min_contour_area:
            return None, mask
            
        return largest_contour, mask
    
    def draw_ghost_shape(self, image, contour):
        """Draw a ghost shape based on the person's contour - just the outline"""
        if contour is None:
            return image
        
        # Draw ONLY the contour outline, not a filled shape
        cv2.drawContours(image, [contour], -1, self.ghost_color, 3)
        
        return image
    
    def create_depth_visualization(self, depth):
        """Create a depth visualization for debugging"""
        # Normalize depth for display
        depth_vis = depth.copy().astype(np.float32)
        depth_vis[depth_vis == 0] = np.nan
        depth_vis = np.clip(depth_vis, self.depth_min, self.depth_max)
        depth_vis = (depth_vis - self.depth_min) / (self.depth_max - self.depth_min)
        depth_vis = (1.0 - depth_vis) * 255.0  # Invert so closer = brighter
        depth_vis[np.isnan(depth_vis)] = 0
        return depth_vis.astype(np.uint8)
    
    def run(self):
        """Main loop for the advanced skeleton art installation"""
        print("🎨 Advanced Skeleton Art Installation")
        print("Use the Control Panel to adjust settings in real-time!")
        print("Press 'q' to quit, 's' to save a frame, 'l' to load a different sprite")
        if self.sprite_image is not None:
            print(f"✅ Default sprite loaded: {self.sprite_path}")
        else:
            print("⚠️  No default sprite found - using ghost shapes")
        
        while True:
            # Get depth and RGB data
            depth = self.get_depth_data()
            rgb = self.get_rgb_data()
            
            if depth is None or rgb is None:
                print("Waiting for Kinect...")
                time.sleep(0.1)
                continue
            
            # Create output image with video opacity
            if self.video_opacity > 0:
                output = rgb.copy()
                # Apply video opacity by blending with black
                output = cv2.addWeighted(output, self.video_opacity, 
                                       np.zeros_like(output), 1 - self.video_opacity, 0)
            else:
                # No video feed, just black background
                output = np.zeros_like(rgb)
            
            # Find person and draw ghost shape or sprite
            contour, mask = self.find_person_contour(depth)
            if contour is not None:
                if self.use_sprite and self.sprite_image is not None:
                    # Draw morphed sprite
                    output = self.morph_sprite_to_contour(output, contour)
                else:
                    # Draw ghost shape
                    output = self.draw_ghost_shape(output, contour)
                
                # Calculate distance for display
                M = cv2.moments(contour)
                if M["m00"] > 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    torso_depth_mm = depth[cy, cx] if 0 <= cy < depth.shape[0] and 0 <= cx < depth.shape[1] else 0
                    distance_feet = torso_depth_mm / 304.8
                    
                    # Add status info with distance in feet
                    cv2.putText(output, f"Ghost Detected! Distance: {distance_feet:.4f} feet", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # Convert range to feet with 4 decimal places
                    min_feet = self.depth_min / 304.8
                    max_feet = self.depth_max / 304.8
                    cv2.putText(output, f"Range: {min_feet:.4f} - {max_feet:.4f} feet", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(output, "Ghost detected but distance unclear", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                cv2.putText(output, "No ghost detected - adjust distance range", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Show contours if enabled
            if self.show_contours and contour is not None:
                cv2.drawContours(output, [contour], -1, (255, 0, 0), 2)
            
            # Display the result
            cv2.imshow("Skeleton Art Installation", output)
            
            # Show depth visualization if enabled
            if self.show_depth_vis:
                depth_vis = self.create_depth_visualization(depth)
                cv2.imshow("Depth Visualization", depth_vis)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save a frame
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"skeleton_art_{timestamp}.png", output)
                print(f"Saved skeleton_art_{timestamp}.png")
            elif key == ord('l'):
                # Load sprite dialog
                sprite_path = input("Enter path to sprite image: ")
                if sprite_path:
                    self.load_sprite(sprite_path)
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        import freenect
        print("✅ Freenect module loaded successfully")
    except ImportError as e:
        raise SystemExit("Missing 'freenect' Python module. Make sure libfreenect is installed.") from e
    
    try:
        # Create and run the advanced skeleton art installation
        print("🎨 Starting Advanced Skeleton Art Installation...")
        art = AdvancedSkeletonArt()
        art.run()
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🔄 Stopping Kinect...")
        freenect.sync_stop()
        print("✅ Kinect stopped successfully")