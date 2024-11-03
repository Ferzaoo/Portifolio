from PIL import Image
import os

def process_image(image_path):
    """
    Process a single image: change black pixels to blue, keep white pixels unchanged.
    """
    print(f"Processing image: {image_path}")
    # Open the image
    img = Image.open(image_path)
    # Convert to RGB mode if it isn't already
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Get the pixel data
    pixels = img.load()
    width, height = img.size

    # Define colors
    BLACK_THRESHOLD = 30  # RGB values below this are considered black
    WHITE_THRESHOLD = 225  # RGB values above this are considered white
    BLUE_COLOR = (0, 0, 255)  # RGB value for blue

    # Process each pixel
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y]

            # Check if pixel is black (all RGB values are very low)
            if r <= BLACK_THRESHOLD and g <= BLACK_THRESHOLD and b <= BLACK_THRESHOLD:
                pixels[x, y] = BLUE_COLOR

    # Create output filename
    output_path = 'modified_' + os.path.basename(image_path)

    # Save the modified image
    img.save(output_path)
    print(f"Saved modified image as: {output_path}")
    return output_path

# Get all JPG files in the current directory
current_dir = os.getcwd()
jpg_files = [f for f in os.listdir(current_dir)
             if f.lower().endswith(('.jpg', '.jpeg'))]

if jpg_files:
    print(f"Found {len(jpg_files)} JPG files:")
    for file in jpg_files:
        print(f"- {file}")

    print("\nProcessing images...")
    for file in jpg_files:
        try:
            process_image(file)
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")

    print("\nProcessing complete! Check the 'modified_' files in the current directory.")
else:
    print("No JPG files found in the current directory!")
