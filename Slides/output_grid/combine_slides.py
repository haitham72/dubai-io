from PIL import Image
import os
import glob

# Get all images from Slides directory
slides_dir = 'Slides'
image_files = sorted(glob.glob(os.path.join(slides_dir, '*.jpg')))

print(f"Found {len(image_files)} images")

# Load all images
images = []
for img_file in image_files:
    img = Image.open(img_file)
    images.append(img)

# Calculate dimensions for the grid
# Assuming all images have the same dimensions, use the first one as reference
sample_img = images[0]
original_width, original_height = sample_img.size

# Each slide at 50% size
slide_width = original_width // 2
slide_height = original_height // 2

# 2x2 grid, so output image is 2 slides wide and 2 slides tall
output_width = slide_width * 2
output_height = slide_height * 2

# Create 4 output images
for i in range(4):
    # Create a white canvas
    output_img = Image.new('RGB', (output_width, output_height), 'white')
    
    # Place 4 slides in 2x2 grid
    for j in range(4):
        slide_index = i * 4 + j
        
        if slide_index < len(images):
            # Resize slide to 50%
            slide = images[slide_index].resize((slide_width, slide_height), Image.Resampling.LANCZOS)
            
            # Calculate position in grid
            row = j // 2
            col = j % 2
            x = col * slide_width
            y = row * slide_height
            
            # Paste slide onto canvas
            output_img.paste(slide, (x, y))
    
    # Save output image
    output_path = f'output_grid_{i + 1}.jpg'
    output_img.save(output_path, 'JPEG', quality=95)
    print(f"Created {output_path}")

print("Done!")
