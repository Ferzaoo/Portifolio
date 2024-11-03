from pdf2image import convert_from_path
import os
from PIL import Image
import sys

def convert_pdf_to_jpg(pdf_path):
    """
    Convert a PDF file to JPG images, one image per page.
    Returns the paths of created JPG files.
    """
    try:
        # Get PDF filename without extension
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        print(f"\nProcessing: {pdf_path}")

        # Convert PDF to images
        # Using 300 DPI for good quality
        images = convert_from_path(pdf_path, 300)

        output_paths = []

        # Save each page as a JPG file
        for i, image in enumerate(images):
            # Convert to RGB mode to ensure color information
            image = image.convert('RGB')

            # Create output filename
            output_file = f"{pdf_name}_page_{i+1}.jpg"

            # Save the image
            image.save(output_file, 'JPEG')
            output_paths.append(output_file)

            print(f"Created: {output_file}")

        return output_paths

    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
        return []

def main():
    # Check if poppler is installed
    try:
        # Get all PDF files in current directory
        current_dir = os.getcwd()
        pdf_files = [f for f in os.listdir(current_dir)
                    if f.lower().endswith('.pdf')]

        if not pdf_files:
            print("No PDF files found in the current directory!")
            return

        print(f"Found {len(pdf_files)} PDF files:")
        for file in pdf_files:
            print(f"- {file}")

        # Process each PDF file
        total_pages_converted = 0
        for pdf_file in pdf_files:
            converted_files = convert_pdf_to_jpg(pdf_file)
            total_pages_converted += len(converted_files)

        print(f"\nConversion complete!")
        print(f"Total PDF files processed: {len(pdf_files)}")
        print(f"Total pages converted to JPG: {total_pages_converted}")

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nIMPORTANT: This script requires:")
        print("1. pdf2image library - install with: pip install pdf2image")
        print("2. Poppler - installation instructions:")
        print("   - Windows: download from: https://github.com/oschwartz10612/poppler-windows/releases/")
        print("   - Mac: brew install poppler")
        print("   - Linux: sudo apt-get install poppler-utils")

if __name__ == "__main__":
    main()
