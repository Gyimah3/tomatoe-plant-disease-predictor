# Plant Disease Predictor

A Python application for predicting plant diseases using a trained Keras model with FastAPI endpoint.

## Setup

### Option 1: Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Place your trained .keras model in the `models/` directory

3. Place test images in the `test_images/` directory

### Option 2: Docker Setup

1. Build the Docker image:
```bash
docker build -t plant-disease-predictor .
```

2. Run with Docker:
```bash
docker run -p 8000:8000 -v $(pwd)/models:/app/models plant-disease-predictor
```

### Option 3: Docker Compose (Recommended)

1. Run with Docker Compose:
```bash
docker-compose up --build
```

2. Stop the service:
```bash
docker-compose down
```

## Usage

### Command Line Interface

#### Single Image Prediction
```bash
python main.py --model models/your_model.keras --image test_images/sample.jpg
```

#### Directory Prediction
```bash
python main.py --model models/your_model.keras --directory test_images/
```

#### With Output File
```bash
python main.py --model models/your_model.keras --directory test_images/ --output my_results.txt
```

## FastAPI Prediction API

To run the FastAPI server locally:

```bash
uvicorn src.api:app --reload
```

### Predict with an image

Send a POST request to `/predict` with an image file:

```bash
curl -X POST "http://127.0.0.1:8000/predict" -F "file=@path_to_your_image.jpg"
```

The response will be a JSON object with the prediction result.

### API Response Format

```json
{
  "label": "tomatoe-healthy",
  "probability": 0.95,
  "confidence": 0.95,
  "image_path": "/path/to/image.jpg"
}
```

## Example Usage in Code

```python
from src.predictor import PlantDiseasePredictor

# Initialize predictor
predictor = PlantDiseasePredictor('models/your_model.keras')

# Make prediction
result = predictor.predict('path/to/image.jpg')
print(f"Prediction: {result['label']}")
print(f"Confidence: {result['confidence']:.2f}")
```
