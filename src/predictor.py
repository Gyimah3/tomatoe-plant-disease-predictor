# Project Structure:
# plant-disease-predictor/
# ├── models/
# │   └── your_model.keras
# ├── test_images/
# │   └── sample_images/
# ├── src/
# │   ├── __init__.py
# │   ├── predictor.py
# │   └── utils.py
# ├── main.py
# ├── requirements.txt
# └── README.md

# File: src/predictor.py
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from tensorflow.keras.models import load_model
import os
from typing import Dict, Tuple, Optional

class PlantDiseasePredictor:
    def __init__(self, model_path: str, image_height: int = 64, image_width: int = 64):
        """
        Initialize the predictor with a trained model.
        
        Args:
            model_path (str): Path to the .keras model file
            image_height (int): Target height for image preprocessing
            image_width (int): Target width for image preprocessing
        """
        self.model_path = model_path
        self.image_height = image_height
        self.image_width = image_width
        self.model = None
        self.label_map = {
            'tomatoe-healthy': 0, 
            'tomaote-not-healthy': 1
        }
        self.load_model()
    
    def load_model(self) -> None:
        """Load the Keras model from file."""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            self.model = load_model(self.model_path)
            print(f"Model loaded successfully from: {self.model_path}")
            print(f"Model input shape: {self.model.input_shape}")
            
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            raise
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for model prediction.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            np.ndarray: Preprocessed image array
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Load and resize image
            image = load_img(image_path, target_size=(self.image_height, self.image_width))
            
            # Convert to array and normalize
            image_arr = img_to_array(image)
            image_arr /= 255.0  # Normalize to [0,1]
            
            # Add batch dimension
            image_arr = image_arr[np.newaxis, :]
            
            return image_arr
            
        except Exception as e:
            print(f"Error preprocessing image: {str(e)}")
            raise
    
    def predict(self, image_path: str) -> Dict[str, any]:
        """
        Make prediction on a single image.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            Dict: Prediction results with label and probability
        """
        try:
            if self.model is None:
                raise ValueError("Model not loaded. Please check model path.")
            
            # Preprocess image
            image_arr = self.preprocess_image(image_path)
            
            # Make prediction
            proba = self.model.predict(image_arr, verbose=0)
            
            # Convert probability to label (assuming binary classification)
            label = (proba > 0.5).squeeze().astype(int)
            
            # Create inverse mapping
            inverse_map = {v: k for k, v in self.label_map.items()}
            
            result = {
                "label": inverse_map.get(int(label), "unknown"),
                "probability": float(proba.squeeze()),
                "confidence": float(max(proba.squeeze(), 1 - proba.squeeze())),
                "image_path": image_path
            }
            
            return result
            
        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            raise
    
    def predict_batch(self, image_paths: list) -> list:
        """
        Make predictions on multiple images.
        
        Args:
            image_paths (list): List of image file paths
            
        Returns:
            list: List of prediction results
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.predict(image_path)
                results.append(result)
            except Exception as e:
                results.append({
                    "label": "error",
                    "probability": 0.0,
                    "confidence": 0.0,
                    "image_path": image_path,
                    "error": str(e)
                })
        return results

# Singleton predictor for FastAPI
_predictor_instance = None
def get_predictor(model_path='models/tomaotoe_model1.keras'):
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = PlantDiseasePredictor(model_path)
    return _predictor_instance

# File: requirements.txt
# tensorflow>=2.8.0
# numpy>=1.21.0
# Pillow>=8.3.0
# argparse

# File: README.md
# # Plant Disease Predictor
# 
# A Python application for predicting plant diseases using a trained Keras model.
# 
# ## Setup
# 
# 1. Install dependencies:
# ```bash
# pip install -r requirements.txt
# ```
# 
# 2. Place your trained .keras model in the `models/` directory
# 
# 3. Place test images in the `test_images/` directory
# 
# ## Usage
# 
# ### Single Image Prediction
# ```bash
# python main.py --model models/your_model.keras --image test_images/sample.jpg
# ```


# 
# ### Directory Prediction
# ```bash
# python main.py --model models/your_model.keras --directory test_images/
# ```
# 
# ### With Output File
# ```bash
# python main.py --model models/your_model.keras --directory test_images/ --output my_results.txt
# ```
# 
# ## Example Usage in Code
# 
# ```python
# from src.predictor import PlantDiseasePredictor
# 
# # Initialize predictor
# predictor = PlantDiseasePredictor('models/your_model.keras')
# 
# # Single prediction
# result = predictor.predict('test_images/sample.jpg')
# print(result)
# 
# # Batch prediction
# results = predictor.predict_batch(['image1.jpg', 'image2.jpg'])
# ```