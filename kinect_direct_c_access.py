#!/usr/bin/env python3
"""
Kinect Device Access via C Library
==================================

This script uses ctypes to directly access the libfreenect C library,
bypassing the Python freenect wrapper that's having USB access issues.
"""

import ctypes
import ctypes.util
import time
import numpy as np
import cv2

# Load the libfreenect library
libfreenect_path = "./libfreenect/build/lib/libfreenect.0.dylib"
libfreenect = ctypes.CDLL(libfreenect_path)

# Define the C structures and functions we need
class FreenectContext(ctypes.Structure):
    pass

class FreenectDevice(ctypes.Structure):
    pass

# Function signatures
libfreenect.freenect_init.argtypes = [ctypes.POINTER(ctypes.POINTER(FreenectContext)), ctypes.POINTER(ctypes.c_void_p)]
libfreenect.freenect_init.restype = ctypes.c_int

libfreenect.freenect_num_devices.argtypes = [ctypes.POINTER(FreenectContext)]
libfreenect.freenect_num_devices.restype = ctypes.c_int

libfreenect.freenect_open_device.argtypes = [ctypes.POINTER(FreenectContext), ctypes.POINTER(ctypes.POINTER(FreenectDevice)), ctypes.c_int]
libfreenect.freenect_open_device.restype = ctypes.c_int

libfreenect.freenect_close_device.argtypes = [ctypes.POINTER(FreenectDevice)]
libfreenect.freenect_close_device.restype = ctypes.c_int

libfreenect.freenect_shutdown.argtypes = [ctypes.POINTER(FreenectContext)]
libfreenect.freenect_shutdown.restype = ctypes.c_int

libfreenect.freenect_select_subdevices.argtypes = [ctypes.POINTER(FreenectContext), ctypes.c_int]
libfreenect.freenect_select_subdevices.restype = None

libfreenect.freenect_set_log_level.argtypes = [ctypes.POINTER(FreenectContext), ctypes.c_int]
libfreenect.freenect_set_log_level.restype = None

# Constants
FREENECT_DEVICE_CAMERA = 0x02
FREENECT_LOG_DEBUG = 3

def test_direct_c_access():
    """Test direct access to libfreenect C library"""
    print("🔧 Testing Direct C Library Access")
    print("==================================")
    
    # Initialize context
    ctx_ptr = ctypes.POINTER(FreenectContext)()
    ret = libfreenect.freenect_init(ctypes.byref(ctx_ptr), None)
    if ret < 0:
        print(f"❌ Failed to initialize freenect context: {ret}")
        return False
    print("✅ Freenect context initialized")

    # Set log level and select camera
    libfreenect.freenect_set_log_level(ctx_ptr, FREENECT_LOG_DEBUG)
    libfreenect.freenect_select_subdevices(ctx_ptr, FREENECT_DEVICE_CAMERA)
    print("✅ Log level set and camera selected")

    # Check device count
    num_devices = libfreenect.freenect_num_devices(ctx_ptr)
    if num_devices < 0:
        print(f"❌ Failed to get device count: {num_devices}")
        libfreenect.freenect_shutdown(ctx_ptr)
        return False
    if num_devices == 0:
        print("❌ No Kinect devices found!")
        libfreenect.freenect_shutdown(ctx_ptr)
        return False
    print(f"✅ Found {num_devices} Kinect device(s)")

    # Try to open device
    dev_ptr = ctypes.POINTER(FreenectDevice)()
    ret = libfreenect.freenect_open_device(ctx_ptr, ctypes.byref(dev_ptr), 0)
    if ret < 0:
        print(f"❌ Failed to open device: {ret}")
        libfreenect.freenect_shutdown(ctx_ptr)
        return False
    print("✅ Device opened successfully!")

    # Keep device open for a few seconds
    print("🔄 Keeping device open for 5 seconds...")
    time.sleep(5)

    # Close device
    libfreenect.freenect_close_device(dev_ptr)
    libfreenect.freenect_shutdown(ctx_ptr)
    print("✅ Device closed and context shutdown")

    return True

if __name__ == "__main__":
    success = test_direct_c_access()
    if success:
        print("\n🎯 Direct C access successful!")
        print("   The C library can access the device.")
        print("   The issue is likely in the Python freenect wrapper.")
    else:
        print("\n❌ Direct C access failed!")
        print("   The issue is deeper - possibly USB permissions or kernel drivers.")
