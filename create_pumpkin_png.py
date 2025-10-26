#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
import subprocess

def create_pumpkin_png():
    # Create a 512x512 image with white background
    size = 512
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Try to get the system emoji font
    try:
        # Use system command to find emoji font
        result = subprocess.run(['fc-list', ':family'], capture_output=True, text=True)
        if 'Apple Color Emoji' in result.stdout:
            font_path = '/System/Library/Fonts/Apple Color Emoji.ttc'
        else:
            font_path = '/System/Library/Fonts/Helvetica.ttc'
        
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, size//2)
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Draw pumpkin emoji
    emoji_text = "🎃"
    
    # Get text bounding box to center it
    try:
        bbox = draw.textbbox((0, 0), emoji_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        # Fallback if textbbox doesn't work
        text_width = size//2
        text_height = size//2
    
    # Center the emoji
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    # Draw the emoji
    draw.text((x, y), emoji_text, font=font, fill=(0, 0, 0, 255))
    
    return img

def create_all_sizes():
    """Create PNG files for all required sizes"""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    
    # Create iconset directory
    iconset_dir = "KinectMaster.app/Contents/Resources/pumpkin_icon.iconset"
    os.makedirs(iconset_dir, exist_ok=True)
    
    # Create base image
    base_img = create_pumpkin_png()
    
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
    
    print("Pumpkin PNG icon set created successfully!")

if __name__ == "__main__":
    create_all_sizes()
