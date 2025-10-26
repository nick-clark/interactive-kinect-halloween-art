#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw
import math

def create_pumpkin_icon():
    # Create a 512x512 image with transparent background
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Pumpkin body (orange ellipse)
    pumpkin_bbox = [size*0.15, size*0.4, size*0.85, size*0.9]
    draw.ellipse(pumpkin_bbox, fill=(255, 140, 0, 255), outline=(255, 127, 0, 255), width=4)
    
    # Pumpkin ridges (darker orange)
    ridge_color = (255, 127, 0, 255)
    for i in range(3):
        x_offset = i * size * 0.25
        ridge_points = []
        for angle in range(0, 360, 10):
            rad = math.radians(angle)
            x = size * 0.5 + (size * 0.35 + x_offset * 0.1) * math.cos(rad)
            y = size * 0.65 + (size * 0.25) * math.sin(rad)
            ridge_points.append((x, y))
        if ridge_points:
            draw.polygon(ridge_points, fill=ridge_color)
    
    # Pumpkin stem (green rectangle)
    stem_bbox = [size*0.47, size*0.27, size*0.53, size*0.4]
    draw.rectangle(stem_bbox, fill=(34, 139, 34, 255))
    
    # Stem top (darker green)
    stem_top_bbox = [size*0.45, size*0.27, size*0.55, size*0.32]
    draw.ellipse(stem_top_bbox, fill=(50, 205, 50, 255))
    
    # Eyes (black ellipses)
    left_eye_bbox = [size*0.35, size*0.5, size*0.45, size*0.6]
    right_eye_bbox = [size*0.55, size*0.5, size*0.65, size*0.6]
    draw.ellipse(left_eye_bbox, fill=(0, 0, 0, 255))
    draw.ellipse(right_eye_bbox, fill=(0, 0, 0, 255))
    
    # Nose (black triangle)
    nose_points = [(size*0.5, size*0.62), (size*0.47, size*0.66), (size*0.53, size*0.66)]
    draw.polygon(nose_points, fill=(0, 0, 0, 255))
    
    # Mouth (black arc)
    mouth_bbox = [size*0.35, size*0.74, size*0.65, size*0.84]
    draw.arc(mouth_bbox, 0, 180, fill=(0, 0, 0, 255), width=8)
    
    # Teeth (black rectangles)
    tooth1_bbox = [size*0.47, size*0.74, size*0.49, size*0.79]
    tooth2_bbox = [size*0.51, size*0.74, size*0.53, size*0.79]
    draw.rectangle(tooth1_bbox, fill=(0, 0, 0, 255))
    draw.rectangle(tooth2_bbox, fill=(0, 0, 0, 255))
    
    return img

def create_icon_set():
    """Create iconset with multiple sizes for macOS"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "KinectMaster.app/Contents/Resources/icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Create base image
    base_img = create_pumpkin_icon()
    
    # Create different sizes
    for size in sizes:
        resized = base_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as PNG
        filename = f"icon_{size}x{size}.png"
        if size >= 1024:
            filename = f"icon_{size}x{size}@2x.png"
        
        resized.save(os.path.join(iconset_dir, filename))
        print(f"Created {filename}")
    
    # Create icon_16x16@2x.png for retina
    retina_32 = base_img.resize((32, 32), Image.Resampling.LANCZOS)
    retina_32.save(os.path.join(iconset_dir, "icon_16x16@2x.png"))
    
    # Create icon_32x32@2x.png for retina
    retina_64 = base_img.resize((64, 64), Image.Resampling.LANCZOS)
    retina_64.save(os.path.join(iconset_dir, "icon_32x32@2x.png"))
    
    # Create icon_128x128@2x.png for retina
    retina_256 = base_img.resize((256, 256), Image.Resampling.LANCZOS)
    retina_256.save(os.path.join(iconset_dir, "icon_128x128@2x.png"))
    
    # Create icon_256x256@2x.png for retina
    retina_512 = base_img.resize((512, 512), Image.Resampling.LANCZOS)
    retina_512.save(os.path.join(iconset_dir, "icon_256x256@2x.png"))
    
    print("Icon set created successfully!")

if __name__ == "__main__":
    create_icon_set()
