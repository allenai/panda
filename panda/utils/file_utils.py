
import requests
import os
from pdfminer.high_level import extract_text
import shutil	# for copy_file


from .utils import replace_special_chars_with_ascii

# ======================================================================
#		READ FILE 
# ======================================================================

def read_file_contents(filename):
  """
  Reads the entire contents of a text file into a string.
  Args:
    filename: The path to the text file.
  Returns:
    str: The contents of the file as a string.
    None: If the file cannot be opened.
  """
  try:
    with open(filename, 'r', encoding="utf-8") as file:
#    with open(filename, 'r') as file:
      contents = file.read()
      return contents
  except FileNotFoundError:
    print(f"Error: File '{filename}' not found.")
    return None

"""
# Example usage:
file_path = "path/to/your/file.txt"  # Replace with the actual file path
file_contents = read_file_contents(file_path)

if file_contents:
  print(file_contents)
"""

# utility

def file_exists(path):
  return os.path.isfile(path)

def delete_file(filepath):
  if os.path.exists(filepath):
    os.remove(filepath)
    
# ======================================================================
# 		DOWNLOAD A FILE
# ======================================================================

def download_file(url=None, filepath=None):
    """
    Downloads a file from the given URL and saves it to the dir.
    Args:
        url (str): The URL of the file.
    Returns:
        str: The path to the downloaded file, or None if download fails.
    """
    try:
        # Download the file
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Save the file to the directory
        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath

    except Exception as e:
        print(f"Error downloading file from {url}: {e}")
        return None

### ======================================================================
###		CONVERT PDF TO TEXT
### ======================================================================

# o1's version

def convert_pdf_to_text(filestem, directory):
    # Construct the full paths to the PDF and the output text file
    pdf_path = os.path.join(directory, f"{filestem}.pdf")
    txt_path = os.path.join(directory, f"{filestem}.txt")
    
    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        print(f"PDF file '{pdf_path}' does not exist.")
        return
    
    try:
        # Extract text from the PDF file
        text = extract_text(pdf_path)
        clean_text = replace_special_chars_with_ascii(text)
        
        # Write the text to the output text file
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(clean_text)
        
        print(f"Successfully converted '{pdf_path}' to '{txt_path}'.")
    except Exception as e:
        print(f"An error occurred while converting the PDF: {e}")

# ======================================================================
#		WIPE A DIRECTORY (Courtesy Gemini)
# ======================================================================        

def clear_directory(directory_path):
    """Removes all files within a directory."""
    try:
        for filename in os.listdir(directory_path):  # Get all files and directories
            file_path = os.path.join(directory_path, filename) # Create the full file path
            if os.path.isfile(file_path):  # Check if it's a file
                os.remove(file_path)  # Remove the file
                print(f"Removed file: {file_path}")
            # If you also want to remove subdirectories, uncomment the next two lines:
            #elif os.path.isdir(file_path):
            #    shutil.rmtree(file_path)
            #    print(f"Removed directory: {file_path}")
        print(f"All files in '{directory_path}' removed.")
    except FileNotFoundError:
        print(f"Directory '{directory_path}' not found (so is already clear).")
    except Exception as e:
        print(f"Error removing files in '{directory_path}': {e}")

# ======================================================================
#	 COPY A FILE
# ======================================================================

def copy_file(source_path, destination_path):
    """
    Copies a file from source_path to destination_path.

    Args:
        source_path: The full path to the source file.
        destination_path: The full path to the destination file.
    """
    try:
        shutil.copy2(source_path, destination_path)  # copy2 preserves metadata
        print(f"File copied successfully from {source_path} to {destination_path}")
    except FileNotFoundError:
        print(f"Error: Source file not found at {source_path}")
    except PermissionError:
        print(f"Error: Permission denied. Check read/write permissions for source and destination.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
