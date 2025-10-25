# Kinect v1 (Xbox 360) — Python Starter Kit (Unix/Linux)

A minimal, no‑nonsense starter to get **RGB + depth** from the original **Kinect v1 (Xbox 360 sensor)** using **libfreenect** and Python.

> TL;DR: You will build `libfreenect` (for the Python bindings), set udev rules, then run the viewer script.

---

## 0) Hardware checklist
- **Kinect v1 (Xbox 360)** — model 1414/1473 (NOT Kinect v2).
- **Kinect power/USB adapter** (the sensor needs external power; plain USB is not enough).
- A Unix-like OS (Ubuntu/Debian/Fedora/macOS). Commands below assume Ubuntu/Debian.

## 1) System packages
```bash
sudo apt-get update
sudo apt-get install -y build-essential cmake git libusb-1.0-0-dev libgl1-mesa-dev freeglut3-dev pkg-config python3-dev
# Optional: OpenCV dependencies if you plan to build from source instead of using wheels
sudo apt-get install -y libopencv-core-dev libopencv-highgui-dev libopencv-imgproc-dev
```
If you use Python virtualenvs (recommended):
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install numpy opencv-python
```
> **Note:** The Python module `freenect` comes from **libfreenect** and is **not** provided by PyPI. You build libfreenect to get it.

## 2) Build libfreenect (with Python bindings)
```bash
git clone https://github.com/OpenKinect/libfreenect.git
cd libfreenect
mkdir build && cd build
cmake -DBUILD_EXAMPLES=ON -DBUILD_PYTHON3=ON ..
make -j$(nproc)
sudo make install
sudo ldconfig
```
This should install the Python module `freenect` into your environment. If not, you can build/install it directly:
```bash
# From libfreenect/wrappers/python
cd ../wrappers/python
python3 setup.py build
python3 setup.py install  # or: pip install .
```

## 3) Set udev rules (Linux only)
Copy the provided rule (below) so non-root users can access the device:
```bash
sudo cp udev/51-kinect.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```
Unplug/replug the Kinect after applying rules.

## 4) Run the demo
With the Kinect powered and USB connected:
```bash
# In this repo
python3 src/kinect_viewer.py
```
Controls:
- **q** — quit
- **s** — save a pair of RGB + depth frames into `captures/`

## 5) Simple “near-hand” gesture demo
```bash
python3 src/gesture_toggle.py
```
It detects a blob entering a configurable depth band and prints/toggles a state. It’s intentionally simple.

## 6) Troubleshooting (real talk)
- **Power**: If you don’t have the **external power/USB adapter**, depth won’t work. Get the adapter.
- **Conflicting kernel drivers**: If some generic webcam driver grabs the device, blacklist it or unload it so libfreenect gets raw access.
- **Permissions**: If you get “permission denied”, your udev rules didn’t apply. Re-check step 3 and replug the Kinect.
- **macOS**: Can work, but Linux is less pain. On macOS you still build `libfreenect` and use `freenect` Python module.
- **Which Kinect is this for?** This is **Kinect v1 (Xbox 360)**. If you own **Kinect v2**, you need **libfreenect2** and different code.

## 7) License
MIT — do what you want; no warranty.

---

### References
- OpenKinect/libfreenect: https://github.com/OpenKinect/libfreenect
