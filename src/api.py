from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from .predictor import get_predictor
from uuid import uuid4
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import base64
import dotenv

import dotenv
dotenv.load_dotenv()
key = os.getenv("GOOGLE_API_KEY")
if key:
    os.environ["GOOGLE_API_KEY"] = key
else:
    print("WARNING: GOOGLE_API_KEY is not set!")

print("GOOGLE_API_KEY is:", os.environ.get("GOOGLE_API_KEY"))

app = FastAPI(
    title="Plant Disease Predictor API",
    description="A machine learning API for detecting plant diseases using deep learning",
    version="1.0.0"
)

# Add CORS middleware to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
def read_root():
    return {"message": "Plant Disease Predictor API", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "plant-disease-predictor"}

@app.post('/predict')
def predict_image(file: UploadFile = File(...)):
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save uploaded file to a temporary location
    temp_dir = 'temp_uploads'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, f"{uuid4()}_{file.filename}")
    
    try:
        with open(temp_filename, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 1. Local model prediction
        predictor = get_predictor()
        result = predictor.predict(temp_filename)

        # 2. Gemini (Google) image model for expert description
        with open(temp_filename, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
        )
        prompt = (
            "You are a tomato plant disease expert. "
            "Given the following image, if you detect a disease, provide a detailed description of the disease, its symptoms, and possible treatments. "
            "If the tomato appears healthy, say so."
        )
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/png;base64,{encoded_image}"},
            ]
        )
        gemini_result = llm.invoke([message])
        # Add Gemini's description to the result
        result["gemini_description"] = gemini_result.content
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)}, 
            status_code=500
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename) 