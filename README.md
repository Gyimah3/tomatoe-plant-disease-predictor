## FastAPI Prediction API

To run the FastAPI server:

```bash
uvicorn src.api:app --reload
```

### Predict with an image

Send a POST request to `/predict` with an image file:

```bash
curl -X POST "http://127.0.0.1:8000/predict" -F "file=@path_to_your_image.jpg"
```

The response will be a JSON object with the prediction result. 