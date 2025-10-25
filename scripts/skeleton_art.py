#!/usr/bin/env python3
"""
Interactive Skeleton Art Installation
Uses Kinect depth data to draw cartoon skeletons that follow people's movements
"""

import freenect
import cv2
import numpy as np
import time
import math

class SkeletonArt:
    def __init__(self):
        self.depth_threshold = 2000  # mm - only track objects closer than 2m
        self.min_contour_area = 5000  # Minimum size for a person
        self.skeleton_color = (0, 255, 255)  # Yellow skeleton
        self.skeleton_thickness = 3
        
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
        # Create a mask for objects within our depth range
        mask = (depth > 0) & (depth < self.depth_threshold)
        mask = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
            
        # Find the largest contour (likely a person)
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) < self.min_contour_area:
            return None
            
        return largest_contour
    
    def find_skeleton_points(self, contour):
        """Find key points for skeleton drawing"""
        # Get contour moments
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return None
            
        # Center of mass (torso)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        
        # Find top and bottom of contour
        top_point = tuple(contour[contour[:, :, 1].argmin()][0])
        bottom_point = tuple(contour[contour[:, :, 1].argmax()][0])
        
        # Find left and right extremes
        left_point = tuple(contour[contour[:, :, 0].argmin()][0])
        right_point = tuple(contour[contour[:, :, 0].argmax()][0])
        
        # Estimate head position (top 20% of body)
        head_y = top_point[1] + (cy - top_point[1]) * 0.2
        head_x = cx
        
        # Estimate shoulder level
        shoulder_y = top_point[1] + (cy - top_point[1]) * 0.4
        
        # Estimate hip level
        hip_y = cy + (bottom_point[1] - cy) * 0.3
        
        return {
            'head': (head_x, int(head_y)),
            'neck': (cx, int(shoulder_y)),
            'torso_center': (cx, cy),
            'hip': (cx, int(hip_y)),
            'left_shoulder': (left_point[0], int(shoulder_y)),
            'right_shoulder': (right_point[0], int(shoulder_y)),
            'left_hip': (left_point[0], int(hip_y)),
            'right_hip': (right_point[0], int(hip_y)),
            'left_hand': left_point,
            'right_hand': right_point,
            'left_foot': (left_point[0], bottom_point[1]),
            'right_foot': (right_point[0], bottom_point[1])
        }
    
    def draw_cartoon_skeleton(self, image, points):
        """Draw a cartoon skeleton on the image"""
        if not points:
            return image
            
        # Draw head (circle)
        cv2.circle(image, points['head'], 15, self.skeleton_color, self.skeleton_thickness)
        
        # Draw spine
        cv2.line(image, points['head'], points['neck'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['neck'], points['torso_center'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['torso_center'], points['hip'], self.skeleton_color, self.skeleton_thickness)
        
        # Draw shoulders
        cv2.line(image, points['left_shoulder'], points['right_shoulder'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['neck'], points['left_shoulder'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['neck'], points['right_shoulder'], self.skeleton_color, self.skeleton_thickness)
        
        # Draw arms
        cv2.line(image, points['left_shoulder'], points['left_hand'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['right_shoulder'], points['right_hand'], self.skeleton_color, self.skeleton_thickness)
        
        # Draw hips
        cv2.line(image, points['left_hip'], points['right_hip'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['hip'], points['left_hip'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['hip'], points['right_hip'], self.skeleton_color, self.skeleton_thickness)
        
        # Draw legs
        cv2.line(image, points['left_hip'], points['left_foot'], self.skeleton_color, self.skeleton_thickness)
        cv2.line(image, points['right_hip'], points['right_foot'], self.skeleton_color, self.skeleton_thickness)
        
        return image
    
    def run(self):
        """Main loop for the skeleton art installation"""
        print("🎨 Skeleton Art Installation")
        print("Press 'q' to quit, 's' to save a frame")
        
        while True:
            # Get depth and RGB data
            depth = self.get_depth_data()
            rgb = self.get_rgb_data()
            
            if depth is None or rgb is None:
                print("Waiting for Kinect...")
                time.sleep(0.1)
                continue
            
            # Create output image
            output = rgb.copy()
            
            # Find person and draw skeleton
            contour = self.find_person_contour(depth)
            if contour is not None:
                points = self.find_skeleton_points(contour)
                if points:
                    output = self.draw_cartoon_skeleton(output, points)
                    
                    # Add some visual flair
                    cv2.putText(output, "DANCE!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Display the result
            cv2.imshow("Skeleton Art Installation", output)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save a frame
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"skeleton_art_{timestamp}.png", output)
                print(f"Saved skeleton_art_{timestamp}.png")
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        import freenect
    except ImportError as e:
        raise SystemExit("Missing 'freenect' Python module. Make sure libfreenect is installed.") from e
    
    # Create and run the skeleton art installation
    art = SkeletonArt()
    art.run()
