import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import re
import numpy as np
from scipy.ndimage import zoom
import shutil

def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Parent Folder")
    return folder_path

def process_images(parent_folder):
    pattern = re.compile(r'.*_1\.tif$')
    output_folder = os.path.join(parent_folder, "Band_1_folder")
    os.makedirs(output_folder, exist_ok=True)

    for root, _, files in os.walk(parent_folder):
        # Skip the output folder
        if root == output_folder:
            continue
        
        for file in files:
            if pattern.match(file):
                input_path = os.path.join(root, file)
                output_path = os.path.join(output_folder, file)
                
                try:
                    with Image.open(input_path) as img:
                        if img.mode != 'I;16':
                            print(f"Skipping {input_path}: Not in I;16 mode")
                            continue

                        # Calculate the new size while maintaining aspect ratio
                        width, height = img.size
                        if width > height:
                            new_width = 256
                            new_height = int(height * (256 / width))
                        else:
                            new_height = 256
                            new_width = int(width * (256 / height))

                        # Convert to numpy array
                        img_array = np.array(img)

                        # Resize using numpy
                        zoom_factors = (new_height / height, new_width / width)
                        resized_array = zoom(img_array, zoom_factors, order=3)

                        # Convert back to Image
                        resized_img = Image.fromarray(resized_array.astype(np.uint16), mode='I;16')

                        # Save as TIFF
                        resized_img.save(output_path, format='TIFF')
                        
                        # Copy original file's modification time to the new file
                        shutil.copystat(input_path, output_path)
                        
                    print(f"Processed and saved: {output_path}")
                except Exception as e:
                    print(f"Error processing {input_path}: {str(e)}")

def main():
    parent_folder = select_folder()
    if parent_folder:
        print(f"Selected folder: {parent_folder}")
        process_images(parent_folder)
        print("Processing complete!")
    else:
        print("No folder selected. Exiting.")

if __name__ == "__main__":
    main()