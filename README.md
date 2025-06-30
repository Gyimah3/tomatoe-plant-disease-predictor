# 🌱 Plant Disease Predictor

A machine learning-powered web application for detecting plant diseases using deep learning and computer vision. Built with TensorFlow/Keras and FastAPI.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.18.0-orange.svg)](https://tensorflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Live Demo

**API Endpoint:** https://tomatoe-plant-disease-predictor.onrender.com

**API Documentation:** https://tomatoe-plant-disease-predictor.onrender.com/docs

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Deployment](#-deployment)
- [Model Information](#-model-information)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

- **🌿 Plant Disease Detection**: Identify healthy vs unhealthy tomato plants
- **🤖 Deep Learning Model**: Powered by TensorFlow/Keras CNN
- **🌐 RESTful API**: FastAPI-based web service
- **📱 Easy Integration**: Simple HTTP endpoints for predictions
- **🐳 Docker Support**: Containerized deployment
- **📊 Real-time Predictions**: Instant disease classification
- **🔧 Multiple Interfaces**: Command-line and web API

## 🏗️ Architecture

```
plant-disease-predictor/
├── models/
│   └── tomaotoe_model1.keras    # Trained CNN model
├── src/
│   ├── predictor.py             # Core prediction logic
│   ├── api.py                   # FastAPI application
│   └── utils.py                 # Utility functions
├── test_images/                 # Sample images for testing
├── main.py                      # Command-line interface
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose setup
└── README.md                    # This file
```

## 🛠️ Installation

### Prerequisites

- Python 3.10 or higher
- Docker (optional, for containerized deployment)

### Option 1: Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Gyimah3/tomatoe-plant-disease-predictor.git
   cd tomatoe-plant-disease-predictor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Option 2: Docker Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Gyimah3/tomatoe-plant-disease-predictor.git
   cd tomatoe-plant-disease-predictor
   ```

2. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

## 🚀 Usage

### Command Line Interface

#### Single Image Prediction
```bash
python main.py --model models/tomaotoe_model1.keras --image test_images/sample.jpg
```

#### Batch Prediction (Directory)
```bash
python main.py --model models/tomaotoe_model1.keras --directory test_images/
```

#### Save Results to File
```bash
python main.py --model models/tomaotoe_model1.keras --directory test_images/ --output results.txt
```

### Web API

#### Start the FastAPI Server
```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

#### Make Predictions via API

**Using curl:**
```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@path/to/your/image.jpg"
```

**Using Python requests:**
```python
import requests

url = "http://localhost:8000/predict"
files = {"file": open("path/to/image.jpg", "rb")}
response = requests.post(url, files=files)
result = response.json()
print(f"Prediction: {result['label']}")
print(f"Confidence: {result['confidence']:.2f}")
```

## 📚 API Documentation

### Endpoints

#### POST `/predict`

Predict plant disease from an uploaded image.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Form data with key `file` containing the image

**Response:**
```json
{
  "label": "tomatoe-healthy",
  "probability": 0.95,
  "confidence": 0.95,
  "image_path": "/path/to/image.jpg"
}
```

**Response Fields:**
- `label`: Classification result (`tomatoe-healthy` or `tomaote-not-healthy`)
- `probability`: Raw model probability (0.0 to 1.0)
- `confidence`: Confidence score (0.0 to 1.0)
- `image_path`: Path to the processed image

**Error Response:**
```json
{
  "error": "Error message description"
}
```

### Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation.

## 🐳 Deployment

### Docker Deployment

1. **Build the image**
   ```bash
   docker build -t plant-disease-predictor .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 plant-disease-predictor
   ```

3. **Using Docker Compose (Recommended)**
   ```bash
   docker-compose up --build
   ```

### Cloud Deployment

#### Render (Current)
- **URL**: https://tomatoe-plant-disease-predictor.onrender.com
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`

#### Heroku
```bash
# Create Procfile
echo "web: uvicorn src.api:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
```

#### AWS/GCP/Azure
Use the provided Dockerfile for container deployment on any cloud platform.

## 🤖 Model Information

### Model Details
- **Architecture**: Convolutional Neural Network (CNN)
- **Framework**: TensorFlow/Keras
- **Input Size**: 64x64 pixels
- **Classes**: 2 (Healthy vs Unhealthy tomato plants)
- **Training Data**: Tomato plant images
- **Model File**: `models/tomaotoe_model1.keras`

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff)

### Performance Notes
- Model runs on CPU (GPU acceleration not required)
- Typical inference time: < 1 second
- Memory usage: ~200MB

## 🧪 Testing

### Test with Sample Images
```bash
# Test single image
curl -X POST "http://localhost:8000/predict" \
  -F "file=@test_images/image.JPG"

# Test with Python
python -c "
import requests
response = requests.post('http://localhost:8000/predict', 
                        files={'file': open('test_images/image.JPG', 'rb')})
print(response.json())
"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
python -m pytest

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- TensorFlow team for the deep learning framework
- FastAPI team for the excellent web framework
- The open-source community for various tools and libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Gyimah3/tomatoe-plant-disease-predictor/issues)
- **Email**: [Your Email]
- **Documentation**: [API Docs](https://tomatoe-plant-disease-predictor.onrender.com/docs)

---

⭐ **Star this repository if you find it useful!**
