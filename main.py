# File: main.py
import os
import sys
import argparse
from pathlib import Path
from loguru import logger
# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from predictor import PlantDiseasePredictor
from utils import get_image_files, create_directory_structure

def main():
    parser = argparse.ArgumentParser(description='Plant Disease Prediction')
    parser.add_argument('--model', '-m', type=str, required=True,
                        help='Path to the .keras model file')
    parser.add_argument('--image', '-i', type=str,
                        help='Path to a single image file')
    parser.add_argument('--directory', '-d', type=str,
                        help='Path to directory containing images')
    parser.add_argument('--output', '-o', type=str, default='results.txt',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    # Initialize predictor
    try:
        predictor = PlantDiseasePredictor(args.model)
    except Exception as e:
        print(f"Failed to initialize predictor: {e}")
        return
    
    results = []
    
    if args.image:
        # Single image prediction
        print(f"Predicting single image: {args.image}")
        try:
            result = predictor.predict(args.image)
            results.append(result)
            logger.info(f"prediction rsults{results}")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Prediction failed: {e}")
    
    elif args.directory:
        # Directory prediction
        print(f"Predicting images in directory: {args.directory}")
        image_files = get_image_files(args.directory)
        print(f"Found {len(image_files)} images")
        
        if image_files:
            results = predictor.predict_batch(image_files)
            
            # Print results
            for result in results:
                print(f"Image: {os.path.basename(result['image_path'])}")
                print(f"  Label: {result['label']}")
                print(f"  Probability: {result['probability']:.4f}")
                print(f"  Confidence: {result['confidence']:.4f}")
                print()
        else:
            print("No image files found in the directory")
    
    else:
        print("Please provide either --image or --directory argument")
        return
    
    # Save results to file
    if results:
        with open(args.output, 'w') as f:
            f.write("Plant Disease Prediction Results\n")
            f.write("=" * 40 + "\n\n")
            
            for result in results:
                f.write(f"Image: {result['image_path']}\n")
                f.write(f"Label: {result['label']}\n")
                f.write(f"Probability: {result['probability']:.4f}\n")
                f.write(f"Confidence: {result['confidence']:.4f}\n")
                if 'error' in result:
                    f.write(f"Error: {result['error']}\n")
                f.write("-" * 30 + "\n")
        
        print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()