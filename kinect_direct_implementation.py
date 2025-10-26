#!/usr/bin/env python3
"""
Kinect Direct Access Implementation
===================================

This script implements a complete Kinect interface using ctypes to directly
access the libfreenect C library, bypassing the problematic Python wrapper.
"""

import ctypes
import ctypes.util
import time
import numpy as np
import cv2
import threading
from typing import Optional, Tuple

class KinectDirectAccess:
    """Direct access to Kinect using libfreenect C library via ctypes"""
    
    def __init__(self):
        # Load the libfreenect library
        libfreenect_path = "./libfreenect/build/lib/libfreenect.0.dylib"
        self.libfreenect = ctypes.CDLL(libfreenect_path)
        
        # Define structures
        class FreenectContext(ctypes.Structure):
            pass
        
        class FreenectDevice(ctypes.Structure):
            pass
        
        class FreenectFrameMode(ctypes.Structure):
            _fields_ = [
                ("reserved", ctypes.c_uint),
                ("resolution", ctypes.c_int),
                ("format", ctypes.c_int),
                ("bytes", ctypes.c_int),
                ("width", ctypes.c_short),
                ("height", ctypes.c_short),
                ("data_bits_per_pixel", ctypes.c_uint8),
                ("padding_bits_per_pixel", ctypes.c_uint8),
                ("framerate", ctypes.c_uint8),
                ("is_valid", ctypes.c_uint8),
            ]
        
        # Store structures
        self.FreenectContext = FreenectContext
        self.FreenectDevice = FreenectDevice
        self.FreenectFrameMode = FreenectFrameMode
        
        # Function signatures
        self._setup_function_signatures()
        
        # Constants
        self.FREENECT_DEVICE_CAMERA = 0x02
        self.FREENECT_LOG_DEBUG = 3
        self.FREENECT_RESOLUTION_MEDIUM = 1
        self.FREENECT_DEPTH_MM = 2
        self.FREENECT_VIDEO_RGB = 0
        
        # Device state
        self.ctx = None
        self.dev = None
        self.running = False
        self.event_thread = None
        
        # Frame data
        self.latest_depth = None
        self.latest_video = None
        self.depth_lock = threading.Lock()
        self.video_lock = threading.Lock()
    
    def _setup_function_signatures(self):
        """Setup function signatures for libfreenect calls"""
        lib = self.libfreenect
        
        # Context management
        lib.freenect_init.argtypes = [ctypes.POINTER(ctypes.POINTER(self.FreenectContext)), ctypes.POINTER(ctypes.c_void_p)]
        lib.freenect_init.restype = ctypes.c_int
        
        lib.freenect_shutdown.argtypes = [ctypes.POINTER(self.FreenectContext)]
        lib.freenect_shutdown.restype = ctypes.c_int
        
        # Device management
        lib.freenect_num_devices.argtypes = [ctypes.POINTER(self.FreenectContext)]
        lib.freenect_num_devices.restype = ctypes.c_int
        
        lib.freenect_open_device.argtypes = [ctypes.POINTER(self.FreenectContext), ctypes.POINTER(ctypes.POINTER(self.FreenectDevice)), ctypes.c_int]
        lib.freenect_open_device.restype = ctypes.c_int
        
        lib.freenect_close_device.argtypes = [ctypes.POINTER(self.FreenectDevice)]
        lib.freenect_close_device.restype = ctypes.c_int
        
        # Configuration
        lib.freenect_select_subdevices.argtypes = [ctypes.POINTER(self.FreenectContext), ctypes.c_int]
        lib.freenect_select_subdevices.restype = None
        
        lib.freenect_set_log_level.argtypes = [ctypes.POINTER(self.FreenectContext), ctypes.c_int]
        lib.freenect_set_log_level.restype = None
        
        # Mode management
        lib.freenect_find_depth_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.freenect_find_depth_mode.restype = ctypes.POINTER(self.FreenectFrameMode)
        
        lib.freenect_find_video_mode.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.freenect_find_video_mode.restype = ctypes.POINTER(self.FreenectFrameMode)
        
        lib.freenect_set_depth_mode.argtypes = [ctypes.POINTER(self.FreenectDevice), ctypes.POINTER(self.FreenectFrameMode)]
        lib.freenect_set_depth_mode.restype = ctypes.c_int
        
        lib.freenect_set_video_mode.argtypes = [ctypes.POINTER(self.FreenectDevice), ctypes.POINTER(self.FreenectFrameMode)]
        lib.freenect_set_video_mode.restype = ctypes.c_int
        
        # Stream management
        lib.freenect_start_depth.argtypes = [ctypes.POINTER(self.FreenectDevice)]
        lib.freenect_start_depth.restype = ctypes.c_int
        
        lib.freenect_start_video.argtypes = [ctypes.POINTER(self.FreenectDevice)]
        lib.freenect_start_video.restype = ctypes.c_int
        
        lib.freenect_stop_depth.argtypes = [ctypes.POINTER(self.FreenectDevice)]
        lib.freenect_stop_depth.restype = ctypes.c_int
        
        lib.freenect_stop_video.argtypes = [ctypes.POINTER(self.FreenectDevice)]
        lib.freenect_stop_video.restype = ctypes.c_int
        
        # Event processing
        lib.freenect_process_events.argtypes = [ctypes.POINTER(self.FreenectContext)]
        lib.freenect_process_events.restype = ctypes.c_int
        
        # Frame access
        lib.freenect_sync_get_depth.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
        lib.freenect_sync_get_depth.restype = ctypes.c_int
        
        lib.freenect_sync_get_video.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint32), ctypes.c_int, ctypes.c_int]
        lib.freenect_sync_get_video.restype = ctypes.c_int
    
    def initialize(self) -> bool:
        """Initialize the Kinect device"""
        print("🔧 Initializing Kinect with direct C access...")
        
        # Initialize context
        ctx_ptr = ctypes.POINTER(self.FreenectContext)()
        ret = self.libfreenect.freenect_init(ctypes.byref(ctx_ptr), None)
        if ret < 0:
            print(f"❌ Failed to initialize freenect context: {ret}")
            return False
        self.ctx = ctx_ptr
        print("✅ Freenect context initialized")
        
        # Set log level and select camera
        self.libfreenect.freenect_set_log_level(self.ctx, self.FREENECT_LOG_DEBUG)
        self.libfreenect.freenect_select_subdevices(self.ctx, self.FREENECT_DEVICE_CAMERA)
        print("✅ Log level set and camera selected")
        
        # Check device count
        num_devices = self.libfreenect.freenect_num_devices(self.ctx)
        if num_devices < 0:
            print(f"❌ Failed to get device count: {num_devices}")
            self.cleanup()
            return False
        if num_devices == 0:
            print("❌ No Kinect devices found!")
            self.cleanup()
            return False
        print(f"✅ Found {num_devices} Kinect device(s)")
        
        # Open device
        dev_ptr = ctypes.POINTER(self.FreenectDevice)()
        ret = self.libfreenect.freenect_open_device(self.ctx, ctypes.byref(dev_ptr), 0)
        if ret < 0:
            print(f"❌ Failed to open device: {ret}")
            self.cleanup()
            return False
        self.dev = dev_ptr
        print("✅ Device opened successfully")
        
        # Set modes
        depth_mode = self.libfreenect.freenect_find_depth_mode(self.FREENECT_RESOLUTION_MEDIUM, self.FREENECT_DEPTH_MM)
        video_mode = self.libfreenect.freenect_find_video_mode(self.FREENECT_RESOLUTION_MEDIUM, self.FREENECT_VIDEO_RGB)
        
        ret = self.libfreenect.freenect_set_depth_mode(self.dev, depth_mode)
        if ret < 0:
            print(f"❌ Failed to set depth mode: {ret}")
            self.cleanup()
            return False
        print("✅ Depth mode set")
        
        ret = self.libfreenect.freenect_set_video_mode(self.dev, video_mode)
        if ret < 0:
            print(f"❌ Failed to set video mode: {ret}")
            self.cleanup()
            return False
        print("✅ Video mode set")
        
        # Start streams
        ret = self.libfreenect.freenect_start_depth(self.dev)
        if ret < 0:
            print(f"❌ Failed to start depth stream: {ret}")
            self.cleanup()
            return False
        print("✅ Depth stream started")
        
        ret = self.libfreenect.freenect_start_video(self.dev)
        if ret < 0:
            print(f"❌ Failed to start video stream: {ret}")
            self.cleanup()
            return False
        print("✅ Video stream started")
        
        return True
    
    def get_depth_frame(self) -> Optional[np.ndarray]:
        """Get the latest depth frame"""
        if not self.dev:
            return None
        
        # Use sync API to get depth frame
        depth_ptr = ctypes.c_void_p()
        timestamp = ctypes.c_uint32()
        
        ret = self.libfreenect.freenect_sync_get_depth(ctypes.byref(depth_ptr), ctypes.byref(timestamp), 0, 0)
        if ret < 0:
            return None
        
        # Convert to numpy array (assuming 16-bit depth data)
        depth_data = ctypes.cast(depth_ptr, ctypes.POINTER(ctypes.c_uint16))
        depth_array = np.ctypeslib.as_array(depth_data, shape=(480, 640))
        
        return depth_array
    
    def get_video_frame(self) -> Optional[np.ndarray]:
        """Get the latest video frame"""
        if not self.dev:
            return None
        
        # Use sync API to get video frame
        video_ptr = ctypes.c_void_p()
        timestamp = ctypes.c_uint32()
        
        ret = self.libfreenect.freenect_sync_get_video(ctypes.byref(video_ptr), ctypes.byref(timestamp), 0, 0)
        if ret < 0:
            return None
        
        # Convert to numpy array (assuming RGB data)
        video_data = ctypes.cast(video_ptr, ctypes.POINTER(ctypes.c_uint8))
        video_array = np.ctypeslib.as_array(video_data, shape=(480, 640, 3))
        
        return video_array
    
    def cleanup(self):
        """Clean up resources"""
        if self.dev:
            self.libfreenect.freenect_stop_depth(self.dev)
            self.libfreenect.freenect_stop_video(self.dev)
            self.libfreenect.freenect_close_device(self.dev)
            self.dev = None
        
        if self.ctx:
            self.libfreenect.freenect_shutdown(self.ctx)
            self.ctx = None
        
        print("✅ Cleanup complete")

def test_direct_kinect():
    """Test the direct Kinect access implementation"""
    print("🎯 Testing Direct Kinect Access Implementation")
    print("==============================================")
    
    kinect = KinectDirectAccess()
    
    if not kinect.initialize():
        print("❌ Failed to initialize Kinect")
        return False
    
    print("\n🔄 Testing frame capture for 10 seconds...")
    start_time = time.time()
    frame_count = 0
    
    while time.time() - start_time < 10:
        depth = kinect.get_depth_frame()
        video = kinect.get_video_frame()
        
        if depth is not None and video is not None:
            frame_count += 1
            print(f"✅ Frame {frame_count}: Depth {depth.shape}, Video {video.shape}")
            
            # Display frames
            cv2.imshow('Depth', depth.astype(np.uint8))
            cv2.imshow('Video', video)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("❌ Failed to get frames")
        
        time.sleep(0.033)  # ~30fps
    
    cv2.destroyAllWindows()
    kinect.cleanup()
    
    print(f"\n🎯 Test complete! Captured {frame_count} frames")
    return frame_count > 0

if __name__ == "__main__":
    success = test_direct_kinect()
    if success:
        print("\n✅ Direct Kinect access successful!")
        print("   This approach bypasses the Python freenect wrapper issues.")
    else:
        print("\n❌ Direct Kinect access failed!")
        print("   There may be deeper USB or driver issues.")
