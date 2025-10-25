import freenect
import cv2
import numpy as np
import time

class SimpleSkeletonArt:
    def __init__(self):
        # Default parameters
        self.depth_min = 914      # mm - 3 feet
        self.depth_max = 5029     # mm - 16.5 feet
        self.min_contour_area = 5000
        self.video_opacity = 0.3
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        self.ghost_alpha = 0.7
        
        # Sprite settings
        self.use_sprite = True
        self.sprite_alpha = 0.8
        self.sprite_image = None
        self.sprite_path = ""
        
        # Create control panel
        self.setup_control_panel()
        
        # Try to load default sprite
        self.load_sprite("sprites/skeleton.png")

    def setup_control_panel(self):
        """Create a control panel with trackbars"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 400, 300)
        
        cv2.createTrackbar('Min Distance (mm)', 'Control Panel', self.depth_min, 2000, self.update_min_distance)
        cv2.createTrackbar('Max Distance (mm)', 'Control Panel', self.depth_max, 6000, self.update_max_distance)
        cv2.createTrackbar('Min Area', 'Control Panel', self.min_contour_area, 20000, self.update_min_area)
        cv2.createTrackbar('Video Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        cv2.createTrackbar('Ghost Alpha', 'Control Panel', int(self.ghost_alpha * 100), 100, self.update_ghost_alpha)
        cv2.createTrackbar('Use Sprite', 'Control Panel', 1, 1, self.toggle_sprite)
        cv2.createTrackbar('Sprite Alpha', 'Control Panel', int(self.sprite_alpha * 100), 100, self.update_sprite_alpha)

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

    def load_sprite(self, sprite_path):
        """Load a sprite image"""
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

    def find_person_contour(self, depth):
        """Find the largest person-like contour"""
        # Create mask for objects within depth range
        # The person should be closer (smaller depth values) than the background
        mask = (depth > self.depth_min) & (depth < self.depth_max)
        mask = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, mask
            
        # Find largest contour (this should be the person)
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) < self.min_contour_area:
            return None, mask
            
        # Debug: show the mask to see what we're detecting
        cv2.imshow("Debug Mask", mask)
        
        # Debug: show the contour on a black image
        debug_img = np.zeros_like(mask)
        cv2.drawContours(debug_img, [largest_contour], -1, 255, 2)
        cv2.imshow("Debug Contour", debug_img)
            
        return largest_contour, mask

    def draw_ghost_shape(self, image, contour):
        """Draw ghost shape - just the outline around the person's actual shape"""
        if contour is None:
            return image
        
        # Draw ONLY the contour outline around the person's shape
        # This draws the blue line directly on the person's contour, not around a bounding box
        cv2.drawContours(image, [contour], -1, self.ghost_color, 3)
        return image

    def morph_sprite_to_contour(self, image, contour):
        """Morph sprite to fit person's contour"""
        if self.sprite_image is None or contour is None:
            return image
        
        # Create mask for person's contour
        person_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.fillPoly(person_mask, [contour], 255)
        
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        
        # Resize sprite to fit person's size
        sprite_resized = cv2.resize(self.sprite_image, (w, h))
        
        # Convert RGBA to RGB if needed
        if sprite_resized.shape[2] == 4:
            sprite_rgb = sprite_resized[:, :, :3]
        else:
            sprite_rgb = sprite_resized
        
        # Create result image
        result = image.copy()
        
        # Extract region of interest
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
        
        # Apply sprite ONLY where person is
        for c in range(3):
            roi[:, :, c] = np.where(
                person_roi_mask == 255,
                sprite_with_alpha[:, :, c],
                roi[:, :, c]
            )
        
        result[y:y+h, x:x+w] = roi
        return result

    def run(self):
        """Main loop"""
        print("🎨 Simple Skeleton Art Installation")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame, 'l' to load a different sprite")
        
        if self.sprite_image is not None:
            print(f"✅ Default sprite loaded: {self.sprite_path}")
        else:
            print("⚠️  No default sprite found - using ghost shapes")
        
        while True:
            try:
                # Get depth and RGB data using the same method as the working viewer
                depth, _ = freenect.sync_get_depth()
                rgb, _ = freenect.sync_get_video()
                
                if depth is None or rgb is None:
                    print("Waiting for Kinect...")
                    time.sleep(0.1)
                    continue
                
                # Create output with video opacity
                if self.video_opacity > 0:
                    output = rgb.copy()
                    output = cv2.addWeighted(output, self.video_opacity,
                                           np.zeros_like(output), 1 - self.video_opacity, 0)
                else:
                    output = np.zeros_like(rgb)
                
                # Find person and draw
                contour, mask = self.find_person_contour(depth)
                if contour is not None:
                    if self.use_sprite and self.sprite_image is not None:
                        output = self.morph_sprite_to_contour(output, contour)
                    else:
                        output = self.draw_ghost_shape(output, contour)
                    
                    # Calculate distance
                    M = cv2.moments(contour)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        torso_depth_mm = depth[cy, cx] if 0 <= cy < depth.shape[0] and 0 <= cx < depth.shape[1] else 0
                        distance_feet = torso_depth_mm / 304.8
                        
                        cv2.putText(output, f"Person Detected! Distance: {distance_feet:.4f} feet",
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        
                        min_feet = self.depth_min / 304.8
                        max_feet = self.depth_max / 304.8
                        cv2.putText(output, f"Range: {min_feet:.4f} - {max_feet:.4f} feet",
                                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(output, "No person detected - adjust distance range",
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Display output
                cv2.imshow("Skeleton Art Installation", output)
                
                # Handle key presses
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    timestamp = int(time.time() * 1000)
                    cv2.imwrite(f"skeleton_art_{timestamp}.png", output)
                    print(f"Saved skeleton_art_{timestamp}.png")
                elif key == ord('l'):
                    sprite_path = input("Enter path to sprite image: ")
                    if sprite_path:
                        self.load_sprite(sprite_path)
                        
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(0.1)
                continue
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        art = SimpleSkeletonArt()
        art.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()
