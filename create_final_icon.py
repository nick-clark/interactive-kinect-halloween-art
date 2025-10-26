#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont

def create_simple_pumpkin():
    # Create a 512x512 image with transparent background
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw orange circle background
    circle_bbox = [size*0.1, size*0.1, size*0.9, size*0.9]
    draw.ellipse(circle_bbox, fill=(255, 140, 0, 255), outline=(255, 127, 0, 255), width=4)
    
    # Try to use system font
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', size//3)
    except:
        try:
            font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', size//3)
        except:
            font = ImageFont.load_default()
    
    # Draw pumpkin emoji
    emoji_text = "🎃"
    
    # Center the emoji
    x = size//2 - size//6
    y = size//2 - size//6
    
    # Draw the emoji
    draw.text((x, y), emoji_text, font=font, fill=(255, 255, 255, 255))
    
    return img

def create_icon_set():
    """Create iconset with multiple sizes"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "KinectMaster.app/Contents/Resources/final_icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Create base image
    base_img = create_simple_pumpkin()
    
    # Create different sizes
    for size in sizes:
        resized = base_img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Save as PNG
        filename = f"icon_{size}x{size}.png"
        if size >= 1024:
            filename = f"icon_{size}x{size}@2x.png"
        
        resized.save(os.path.join(iconset_dir, filename))
        print(f"Created {filename}")
    
    # Create retina variants
    retina_sizes = [(16, 32), (32, 64), (128, 256), (256, 512)]
    for base_size, retina_size in retina_sizes:
        retina_img = base_img.resize((retina_size, retina_size), Image.Resampling.LANCZOS)
        retina_img.save(os.path.join(iconset_dir, f"icon_{base_size}x{base_size}@2x.png"))
        print(f"Created icon_{base_size}x{base_size}@2x.png")
    
    print("Final pumpkin icon set created!")

if __name__ == "__main__":
    create_icon_set()
