import freenect
import cv2
import numpy as np
import time
import mediapipe as mp
import math

class PersonHandGhost:
    def __init__(self):
        # Default parameters
        self.depth_min = 914      # mm - 3 feet
        self.depth_max = 5029     # mm - 16.5 feet
        self.video_opacity = 0.3
        self.ghost_alpha = 0.7
        self.ghost_color = (200, 200, 255)  # Light blue ghost
        
        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.mp_pose = mp.solutions.pose
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        
        # Ghost sprite
        self.ghost_sprite = None
        self.load_ghost_sprite("sprites/skeleton.png")
        
        # Create control panel
        self.setup_control_panel()

    def setup_control_panel(self):
        """Create a control panel with trackbars"""
        cv2.namedWindow('Control Panel', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Control Panel', 600, 400)
        
        cv2.createTrackbar('Min Dist', 'Control Panel', self.depth_min, 2000, self.update_min_distance)
        cv2.createTrackbar('Max Dist', 'Control Panel', self.depth_max, 6000, self.update_max_distance)
        cv2.createTrackbar('Opacity', 'Control Panel', int(self.video_opacity * 100), 100, self.update_video_opacity)
        cv2.createTrackbar('Ghost Alpha', 'Control Panel', int(self.ghost_alpha * 100), 100, self.update_ghost_alpha)

    def update_min_distance(self, val):
        self.depth_min = val

    def update_max_distance(self, val):
        self.depth_max = val

    def update_video_opacity(self, val):
        self.video_opacity = val / 100.0

    def update_ghost_alpha(self, val):
        self.ghost_alpha = val / 100.0

    def load_ghost_sprite(self, sprite_path):
        """Load ghost sprite image"""
        try:
            self.ghost_sprite = cv2.imread(sprite_path, cv2.IMREAD_UNCHANGED)
            if self.ghost_sprite is not None:
                print(f"Ghost sprite loaded: {sprite_path}")
            else:
                print(f"Failed to load ghost sprite: {sprite_path}")
        except Exception as e:
            print(f"Error loading ghost sprite: {e}")

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

    def find_person_in_depth(self, depth):
        """Find the largest person-like object in depth range"""
        # Create mask for objects within depth range
        mask = (depth > self.depth_min) & (depth < self.depth_max)
        mask = mask.astype(np.uint8) * 255
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, mask
            
        # Find largest contour (person)
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) < 10000:  # Minimum person size
            return None, mask
            
        return largest_contour, mask

    def get_hand_centers_3d(self, rgb, depth, person_contour):
        """Get 3D positions of hand centers using MediaPipe + depth"""
        # Convert BGR to RGB for MediaPipe
        rgb_mp = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        
        # Process with MediaPipe
        results = self.hands.process(rgb_mp)
        
        hand_centers_3d = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Get hand center (wrist landmark)
                wrist = hand_landmarks.landmark[0]  # Wrist is landmark 0
                
                # Convert to pixel coordinates
                h, w, _ = rgb.shape
                x = int(wrist.x * w)
                y = int(wrist.y * h)
                
                # Check if hand is within person contour
                if person_contour is not None:
                    # Create a small test point
                    test_point = np.array([[x, y]], dtype=np.int32)
                    inside = cv2.pointPolygonTest(person_contour, (x, y), False)
                    if inside <= 0:  # Not inside person
                        continue
                
                # Get depth at hand position
                if 0 <= y < depth.shape[0] and 0 <= x < depth.shape[1]:
                    hand_depth = depth[y, x]
                    if self.depth_min < hand_depth < self.depth_max:
                        hand_centers_3d.append((x, y, hand_depth))
        
        return hand_centers_3d

    def calculate_ghost_position(self, hand_centers_3d):
        """Calculate ghost position centered between hands"""
        if len(hand_centers_3d) < 2:
            return None, None
        
        # Get the two hands
        hand1 = hand_centers_3d[0]
        hand2 = hand_centers_3d[1]
        
        # Calculate center point between hands
        center_x = (hand1[0] + hand2[0]) // 2
        center_y = (hand1[1] + hand2[1]) // 2
        center_depth = (hand1[2] + hand2[2]) // 2
        
        # Calculate distance between hands
        distance = math.sqrt((hand1[0] - hand2[0])**2 + (hand1[1] - hand2[1])**2)
        
        return (center_x, center_y, center_depth), distance

    def draw_ghost_at_position(self, image, position, distance):
        """Draw ghost sprite centered at the calculated position"""
        if position is None or self.ghost_sprite is None:
            return image
        
        center_x, center_y, center_depth = position
        
        # Calculate ghost size based on distance between hands
        # Scale the ghost to be proportional to hand distance
        base_size = 100
        scale_factor = max(0.5, min(2.0, distance / 200))  # Scale between 0.5x and 2x
        ghost_size = int(base_size * scale_factor)
        
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

    def draw_hand_markers(self, image, hand_centers_3d):
        """Draw markers on detected hands"""
        for i, (x, y, depth) in enumerate(hand_centers_3d):
            # Draw hand marker
            cv2.circle(image, (x, y), 10, (0, 255, 0), -1)
            cv2.circle(image, (x, y), 15, (0, 0, 255), 2)
            
            # Draw distance text
            distance_feet = depth / 304.8
            cv2.putText(image, f"Hand {i+1}: {distance_feet:.2f}ft", 
                       (x - 50, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def run(self):
        """Main loop"""
        print("👻 Person Hand Ghost Tracking")
        print("Use the Control Panel to adjust settings!")
        print("Press 'q' to quit, 's' to save a frame")
        
        while True:
            # Get data from Kinect
            depth = self.get_depth_data()
            rgb = self.get_rgb_data()
            
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
            
            # Find person in depth
            person_contour, mask = self.find_person_in_depth(depth)
            
            if person_contour is not None:
                # Get hand centers using MediaPipe + depth
                hand_centers_3d = self.get_hand_centers_3d(rgb, depth, person_contour)
                
                if len(hand_centers_3d) >= 2:
                    # Calculate ghost position between hands
                    ghost_position, hand_distance = self.calculate_ghost_position(hand_centers_3d)
                    
                    if ghost_position is not None:
                        # Draw ghost at calculated position
                        output = self.draw_ghost_at_position(output, ghost_position, hand_distance)
                        
                        # Draw hand markers
                        self.draw_hand_markers(output, hand_centers_3d)
                        
                        # Display status
                        cv2.putText(output, f"Person + 2 Hands Detected!", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(output, f"Hand Distance: {hand_distance:.1f}px", 
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    else:
                        cv2.putText(output, "Person detected, need 2 hands", 
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                else:
                    cv2.putText(output, f"Person detected, {len(hand_centers_3d)} hands found", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            else:
                cv2.putText(output, "No person detected - adjust distance range", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display output
            cv2.imshow("Person Hand Ghost Tracking", output)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                timestamp = int(time.time() * 1000)
                cv2.imwrite(f"person_hand_ghost_{timestamp}.png", output)
                print(f"Saved person_hand_ghost_{timestamp}.png")
        
        cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        tracker = PersonHandGhost()
        tracker.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        freenect.sync_stop()
