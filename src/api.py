from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import shutil
import os
from .predictor import get_predictor
from uuid import uuid4

app = FastAPI()

@app.post('/predict')
def predict_image(file: UploadFile = File(...)):
    # Save uploaded file to a temporary location
    temp_dir = 'temp_uploads'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, f"{uuid4()}_{file.filename}")
    with open(temp_filename, 'wb') as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        predictor = get_predictor()
        result = predictor.predict(temp_filename)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename) 