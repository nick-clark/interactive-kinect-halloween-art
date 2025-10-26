#!/bin/bash

# Kinect v1 Reset Script
# This script systematically unstucks the Kinect v1 device
# Run this when you get USB connection errors or "Invalid index" errors

echo "🔧 Kinect v1 Reset Script"
echo "========================="
echo ""

# Step 1: Kill all Python processes (deepest way possible)
echo "1️⃣ Killing all Python processes (deepest way possible)..."
sudo pkill -9 -f python
pkill -9 -f python
killall -9 Python
killall -9 python3
sleep 2

# Step 1.5: AGGRESSIVE PHYSICAL RESET INSTRUCTIONS
echo "1.5️⃣ AGGRESSIVE PHYSICAL RESET (Most Effective!)"
echo "================================================"
echo "⚠️  IMPORTANT: If you're getting kernel driver errors, try this first:"
echo "   1. Unplug the Kinect USB cable completely"
echo "   2. Wait 30 seconds for USB interface to fully reset"
echo "   3. Plug it back in to a DIFFERENT USB port"
echo "   4. Wait 10 seconds for system to recognize it"
echo "   5. Then run this script again"
echo ""
echo "Press ENTER to continue with software reset, or Ctrl+C to do physical reset first..."
read -r
echo ""

# Step 2: Check for processes using Kinect
echo "2️⃣ Checking for processes using Kinect..."
lsof | grep -i kinect
echo ""

# Step 3: Check USB device status
echo "3️⃣ Checking USB device status..."
system_profiler SPUSBDataType | grep -A 10 -B 5 -i kinect
echo ""

# Step 4: Check power management settings
echo "4️⃣ Checking power management settings..."
pmset -g
echo ""

# Step 5: Reset Kinect using freenect-camtest
echo "5️⃣ Resetting Kinect using freenect-camtest..."
echo "This will run for 3 seconds to reset the device..."
(./libfreenect/build/bin/freenect-camtest &) && sleep 3 && pkill -f freenect-camtest
echo ""

# Step 6: Wait for system to stabilize
echo "6️⃣ Waiting for system to stabilize..."
sleep 2

# Step 7: Final status check
echo "7️⃣ Final status check..."
system_profiler SPUSBDataType | grep -A 5 -B 2 -i kinect
echo ""

echo "✅ Kinect reset complete!"
echo "You can now run your Python scripts."
echo ""
echo "If you still have issues:"
echo "- Try unplugging and replugging the Kinect"
echo "- Try a different USB port"
echo "- Restart your computer if problems persist"
