#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import math

def create_emoji_icon():
    # Create a 512x512 image with transparent background
    size = 512
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to use system font for emoji, fallback to default
    try:
        # Try different font paths for emoji support
        font_paths = [
            "/System/Library/Fonts/Apple Color Emoji.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Unicode MS.ttf"
        ]
        
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, size//2)
                    break
                except:
                    continue
        
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw pumpkin emoji
    emoji_text = "🎃"
    
    # Get text bounding box to center it
    bbox = draw.textbbox((0, 0), emoji_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the emoji
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Draw the emoji
    draw.text((x, y), emoji_text, font=font, fill=(255, 255, 255, 255))
    
    return img

def create_emoji_iconset():
    """Create iconset with multiple sizes for macOS"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "KinectMaster.app/Contents/Resources/emoji_icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Create base image
    base_img = create_emoji_icon()
    
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
    
    print("Emoji icon set created successfully!")

if __name__ == "__main__":
    create_emoji_iconset()
