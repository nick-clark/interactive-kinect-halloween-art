import freenect
import cv2
import numpy as np
import time
import math

class HandTrackingArt:
    def __init__(self):
        # Default parameters - these will be adjustable via trackbars
        self.depth_min = 914      # mm - 3 feet
        self.depth_max = 5029     # mm - 16.5 feet
        self.min_hand_area = 1000  # Minimum size for a hand
        self.video_opacity = 0.3  # Video feed opacity (0.0 = transparent, 1.0 = opaque)
        self.show_depth_vis = True
        self.show_contours = True
        
        # Hand tracking settings
        self.hand_marker_size = 20
        self.hand_marker_color = (0, 0, 255)  # Red for "x" marks
        
        # Create control panel window
        self.setup_control_panel()

    def setup_control_panel(self):
        """Create a control panel with trackbars for real-time adjustment"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 800, 500)  # Made much wider and taller

        # Create trackbars with very short labels to fit in OpenCV's fixed label width
        cv2.createTrackbar('Min Dist', 'Control Panel', self.depth_min, 2000, self.update_min_distance)
        cv2.createTrackbar('Max Dist', 'Control Panel', self.depth_max, 6000, self.update_max_distance)
        cv2.createTrackbar('Hand Area', 'Control Panel', self.min_hand_area, 10000, self.update_min_hand_area)
        cv2.createTrackbar('Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        cv2.createTrackbar('Marker', 'Control Panel', self.hand_marker_size, 50, self.update_marker_size)
        cv2.createTrackbar('Depth', 'Control Panel', 1, 1, self.toggle_depth)
        cv2.createTrackbar('Contours', 'Control Panel', 1, 1, self.toggle_contours)

    def update_min_distance(self, val):
        self.depth_min = val

    def update_max_distance(self, val):
        self.depth_max = val

    def update_min_hand_area(self, val):
        self.min_hand_area = val

    def update_video_opacity(self, val):
        self.video_opacity = val / 100.0

    def update_marker_size(self, val):
        self.hand_marker_size = val

    def toggle_depth(self, val):
        self.show_depth_vis = bool(val)

    def toggle_contours(self, val):
        self.show_contours = bool(val)

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

    def find_hands(self, depth):
        """Find hand-like objects in the depth image"""
        # Create a mask for objects within our depth range
        mask = (depth > self.depth_min) & (depth < self.depth_max)
        mask = mask.astype(np.uint8) * 255

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return [], mask

        # Filter contours by size (hands should be smaller than full body)
        hand_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_hand_area < area < 50000:  # Hands are smaller than full body
                hand_contours.append(contour)

        return hand_contours, mask

    def draw_hand_markers(self, image, hand_contours):
        """Draw red 'x' marks over detected hands"""
        for contour in hand_contours:
            # Get the center of the hand
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Draw red "x" mark
                size = self.hand_marker_size
                cv2.line(image, (cx - size, cy - size), (cx + size, cy + size), self.hand_marker_color, 3)
                cv2.line(image, (cx - size, cy + size), (cx + size, cy - size), self.hand_marker_color, 3)
                
                # Draw a small circle at the center
                cv2.circle(image, (cx, cy), 5, self.hand_marker_color, -1)

    def calculate_hand_distances(self, hand_contours, depth):
        """Calculate distances to each detected hand"""
        distances = []
        for contour in hand_contours:
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                # Get depth at hand center
                if 0 <= cy < depth.shape[0] and 0 <= cx < depth.shape[1]:
                    hand_depth_mm = depth[cy, cx]
                    distance_feet = hand_depth_mm / 304.8  # Convert mm to feet
                    distances.append((cx, cy, distance_feet))
        
        return distances

    def create_depth_visualization(self, depth):
        """Create a depth visualization for debugging"""
        # Normalize depth for display
        depth_vis = depth.copy().astype(np.float32)
        depth_vis[depth_vis <= 0] = np.nan
        depth_vis = np.clip(depth_vis, self.depth_min, self.depth_max)
        depth_vis = (depth_vis - self.depth_min) / (self.depth_max - self.depth_min)
        depth_vis = (1.0 - depth_vis) * 255.0  # Invert so closer = brighter
        depth_vis[np.isnan(depth_vis)] = 0
        return depth_vis.astype(np.uint8)

    def run(self):
        """Main loop for the hand tracking art installation"""
        print("🤚 Hand Tracking Art Installation")
        print("Use the Control Panel to adjust settings in real-time!")
        print("Press 'q' to quit, 's' to save a frame")

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

            # Find hands and draw markers
            hand_contours, mask = self.find_hands(depth)
            if hand_contours:
                # Draw red "x" marks over hands
                self.draw_hand_markers(output, hand_contours)
                
                # Calculate and display distances
                distances = self.calculate_hand_distances(hand_contours, depth)
                
                # Display hand count and distances
                cv2.putText(output, f"Hands Detected: {len(hand_contours)}",
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display individual hand distances
                for i, (cx, cy, distance_feet) in enumerate(distances):
                    cv2.putText(output, f"Hand {i+1}: {distance_feet:.4f} ft",
                              (10, 60 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Convert range to feet with 4 decimal places
                min_feet = self.depth_min / 304.8
                max_feet = self.depth_max / 304.8
                cv2.putText(output, f"Range: {min_feet:.4f} - {max_feet:.4f} feet",
                          (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            else:
                cv2.putText(output, "No hands detected - adjust distance range",
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            # Show contours if enabled
            if self.show_contours and hand_contours:
                cv2.drawContours(output, hand_contours, -1, (255, 0, 0), 2)

            # Display the output
            cv2.imshow("Hand Tracking Art Installation", output)

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
                cv2.imwrite(f"hand_tracking_{timestamp}.png", output)
                print(f"Saved hand_tracking_{timestamp}.png")

        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        art = HandTrackingArt()
        art.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()
