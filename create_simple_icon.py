#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw
import math

def create_simple_pumpkin():
    # Create a 256x256 image
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Pumpkin body (orange circle)
    pumpkin_bbox = [size*0.2, size*0.3, size*0.8, size*0.8]
    draw.ellipse(pumpkin_bbox, fill=(255, 140, 0, 255))
    
    # Pumpkin ridges
    for i in range(3):
        y_offset = i * size * 0.15
        ridge_bbox = [size*0.25 + y_offset*0.1, size*0.35 + y_offset, 
                     size*0.75 - y_offset*0.1, size*0.45 + y_offset]
        draw.ellipse(ridge_bbox, fill=(255, 127, 0, 255))
    
    # Stem
    stem_bbox = [size*0.45, size*0.2, size*0.55, size*0.3]
    draw.rectangle(stem_bbox, fill=(34, 139, 34, 255))
    
    # Eyes
    left_eye = [size*0.35, size*0.45, size*0.45, size*0.55]
    right_eye = [size*0.55, size*0.45, size*0.65, size*0.55]
    draw.ellipse(left_eye, fill=(0, 0, 0, 255))
    draw.ellipse(right_eye, fill=(0, 0, 0, 255))
    
    # Nose
    nose_points = [(size*0.5, size*0.6), (size*0.47, size*0.65), (size*0.53, size*0.65)]
    draw.polygon(nose_points, fill=(0, 0, 0, 255))
    
    # Mouth
    mouth_bbox = [size*0.35, size*0.7, size*0.65, size*0.75]
    draw.arc(mouth_bbox, 0, 180, fill=(0, 0, 0, 255), width=6)
    
    return img

# Create the icon
img = create_simple_pumpkin()
img.save("KinectMaster.app/Contents/Resources/icon.png")
print("Created simple pumpkin icon!")
