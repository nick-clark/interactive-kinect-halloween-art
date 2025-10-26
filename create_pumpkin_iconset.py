#!/usr/bin/env python3
import os
from PIL import Image

def create_icon_set_from_png():
    """Create iconset with multiple sizes from the provided pumpkin.png"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "KinectMaster.app/Contents/Resources/pumpkin_iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Load the original pumpkin image
    try:
        original_img = Image.open("pumpkin.png")
        print(f"Loaded pumpkin.png: {original_img.size}")
    except Exception as e:
        print(f"Error loading pumpkin.png: {e}")
        return
    
    # Create different sizes
    for size in sizes:
        resized = original_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as PNG
        filename = f"icon_{size}x{size}.png"
        if size >= 1024:
            filename = f"icon_{size}x{size}@2x.png"
        
        resized.save(os.path.join(iconset_dir, filename))
        print(f"Created {filename}")
    
    # Create retina variants
    retina_sizes = [(16, 32), (32, 64), (128, 256), (256, 512)]
    for base_size, retina_size in retina_sizes:
        retina_img = original_img.resize((retina_size, retina_size), Image.Resampling.LANCZOS)
        retina_img.save(os.path.join(iconset_dir, f"icon_{base_size}x{base_size}@2x.png"))
        print(f"Created icon_{base_size}x{base_size}@2x.png")
    
    print("Pumpkin icon set created successfully!")

if __name__ == "__main__":
    create_icon_set_from_png()
