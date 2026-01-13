
"""
Installation:
pip install playwright
pip install opencv-python
ipython
%run panda/panda_agent/animate.py

USAGE:
make_video(html_and_video_directory='superpanda_results5', video_name="output_video.mp4")

%run animate.py
process_html_files(input_directory, output_directory)
create_video_from_images(output_directory, 'output_video.mp4')
"""

from playwright.sync_api import sync_playwright
import os
import cv2
import re

def make_video(html_and_video_directory, video_name="output_video.mp4"):
    print("Converting HTML to images...")
    process_html_files(html_and_video_directory, html_and_video_directory)
    print("Creating video...")    
    create_video_from_images(html_and_video_directory, os.path.join(html_and_video_directory,video_name))

def html_to_image(html_file_path, output_image_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
#        with open(html_file_path, 'r', encoding='utf-8') as f:
        with open(html_file_path, 'r', encoding='Windows-1252') as f:            
            html_content = f.read()
        page.set_content(html_content)
        page.screenshot(path=output_image_path)
        browser.close()

def process_html_files(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
#   html_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.html')])
    html_files = [html for html in os.listdir(input_dir) if html.endswith(".html")]
#   html_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
    html_files.sort(
        key=lambda x: int(re.search(r'(\d+)$', os.path.splitext(x)[0]).group(1))
    )
    for i, html_file in enumerate(html_files):
        html_file_path = os.path.join(input_dir, html_file)
        output_image_path = os.path.join(output_dir, f'{i + 1}.png')
        html_to_image(html_file_path, output_image_path)

# ----------

# Specify the directory containing the images
# Specify the output video file name and format
# video_name = 'output_video.mp4'

# create_video_from_images(output_directory, 'output_video.mp4')
def create_video_from_images(image_folder, video_name):

    # Get list of images in the directory
    images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
    # Sort images numerically (ensure your images are named numerically like 1.png, 2.png, etc.)
    images.sort(key=lambda x: int(os.path.splitext(x)[0]))
    print("images =", images)
#    input("press <return>...")

    # Check if images are found
    if not images:
        print("No images found in the directory.")
        exit()

    # Read the first image to get the video frame dimensions
    first_frame = cv2.imread(os.path.join(image_folder, images[0]))
    height, width, layers = first_frame.shape

    # Define the codec and create a VideoWriter object
    video = cv2.VideoWriter(
        video_name,
        cv2.VideoWriter_fourcc(*'mp4v'),
        1,  # Frames per second
#       3,  # Frames per second        
#       6,  # Frames per second        
        (width, height)
    )

    # Loop through images and write them to the video
    for image in images:
        img_path = os.path.join(image_folder, image)
        frame = cv2.imread(img_path)
        video.write(frame)

    # Release the VideoWriter
    video.release()
    cv2.destroyAllWindows()

