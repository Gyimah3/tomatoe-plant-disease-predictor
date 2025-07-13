from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from uuid import uuid4
import base64
import dotenv
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

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

# Add CORS middleware to allow all origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class LeafType(str, Enum):
    TOMATO = "tomato"
    NOT_TOMATO = "not_tomato"
    UNCLEAR = "unclear"

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DISEASED = "diseased"
    STRESSED = "stressed"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"  # For non-tomato leaves

class DiseaseType(str, Enum):
    EARLY_BLIGHT = "early_blight"
    LATE_BLIGHT = "late_blight"
    BACTERIAL_SPOT = "bacterial_spot"
    SEPTORIA_LEAF_SPOT = "septoria_leaf_spot"
    YELLOW_LEAF_CURL = "yellow_leaf_curl"
    MOSAIC_VIRUS = "mosaic_virus"
    NUTRIENT_DEFICIENCY = "nutrient_deficiency"
    PEST_DAMAGE = "pest_damage"
    OTHER = "other"

class TomatoLeafAnalysis(BaseModel):
    is_tomato_leaf: LeafType = Field(description="Whether the image shows a tomato leaf or not")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence level in the tomato leaf identification (0-1)")
    health_status: Optional[HealthStatus] = Field(default=None, description="Overall health status of the tomato leaf")
    diseases_detected: List[DiseaseType] = Field(default_factory=list, description="List of diseases or issues detected")
    symptoms_observed: List[str] = Field(default_factory=list, description="Specific symptoms visible on the leaf")
    severity_level: Optional[str] = Field(default=None, description="Severity level: mild, moderate, severe")
    treatment_recommendations: List[str] = Field(default_factory=list, description="Specific treatment recommendations")
    prevention_tips: List[str] = Field(default_factory=list, description="Prevention measures for future care")
    additional_notes: Optional[str] = Field(default=None, description="Extensive additional observations, analysis, or context")

@app.get("/")
def read_root():
    return {"message": "Plant Disease Predictor API", "status": "healthy"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "plant-disease-predictor"}

@app.post('/predict')
def predict_image(file: UploadFile = File(...)):
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    temp_dir = 'temp_uploads'
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = os.path.join(temp_dir, f"{uuid4()}_{file.filename}")
    try:
        with open(temp_filename, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        with open(temp_filename, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        prompt = (
            "Analyze this image for tomato leaf health. Please provide the following fields in JSON, using ONLY the allowed values for each field:\n"
            "- is_tomato_leaf: 'tomato', 'not_tomato', 'unclear'\n"
            "- confidence_score: float between 0 and 1\n"
            "- health_status: 'healthy', 'diseased', 'stressed', 'unclear', 'not_applicable'\n"
            "- diseases_detected: list of any of ['early_blight', 'late_blight', 'bacterial_spot', 'septoria_leaf_spot', 'yellow_leaf_curl', 'mosaic_virus', 'nutrient_deficiency', 'pest_damage', 'other']\n"
            "- symptoms_observed: list of strings\n"
            "- severity_level: 'mild', 'moderate', 'severe', or null\n"
            "- treatment_recommendations: list of strings\n"
            "- prevention_tips: list of strings\n"
            "- additional_notes: string or null\n"
            "If unsure, use 'unclear' or 'other' as appropriate. Do NOT use any other values for enum fields.\n"
            "IMPORTANT: If this is NOT a tomato leaf, set health_status to 'not_applicable' and leave treatment/prevention recommendations empty... make additional notes extensive!"
        )
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{encoded_image}"},
            ]
        )
        structured_llm = llm.with_structured_output(TomatoLeafAnalysis)
        result = structured_llm.invoke([message])
        return JSONResponse(content=result.dict())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename) 