# File: src/utils.py
import os
import glob
from typing import List

def get_image_files(directory: str, extensions: List[str] = None) -> List[str]:
    """
    Get all image files from a directory.
    
    Args:
        directory (str): Directory path
        extensions (list): List of file extensions to include
        
    Returns:
        list: List of image file paths
    """
    if extensions is None:
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    
    image_files = []
    for ext in extensions:
        pattern = os.path.join(directory, '**', ext)
        image_files.extend(glob.glob(pattern, recursive=True))
        pattern = os.path.join(directory, '**', ext.upper())
        image_files.extend(glob.glob(pattern, recursive=True))
    
    return sorted(list(set(image_files)))

def create_directory_structure():
    """Create the project directory structure."""
    directories = [
        'models',
        'test_images',
        'src',
        'results'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")