import os
import uuid
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .models import (
    DetectionResponse,
    MatchRecipeRequest,
    RecipeMatchResponse,
    DetectedIngredient,
)
from .vision_detector import detect_fridge_ingredients, get_mock_indian_fridge_detection
from .matcher import match_recipes_from_corpus
from .corpus import POPULAR_INGREDIENTS, PANTRY_STAPLES

load_dotenv()

app = FastAPI(
    title="RasoiAI API",
    description="Multimodal Indian Fridge-to-Recipe & Shopping List Generator",
    version="1.0.0",
)

# Crucial for React & Flutter integration: Allow all origins and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
STATIC_HTML_PATH = STATIC_DIR / "index.html"

# Mount /static directory for icons, manifest, and assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.json")
def get_manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def get_sw():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/", response_class=HTMLResponse)
def root():
    """Serves the main RasoiAI Interactive Experience."""
    if STATIC_HTML_PATH.exists():
        return STATIC_HTML_PATH.read_text(encoding="utf-8")
    return "<h1>RasoiAI Frontend HTML not found</h1>"


@app.get("/api/info")
def info():
    """Returns backend status and diagnostic information."""
    return {
        "status": "online",
        "service": "RasoiAI Backend",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
        "demo_mode": os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes"),
        "docs_url": "/docs",
        "interactive_ui": "/",
    }


@app.post("/api/detect-ingredients", response_model=DetectionResponse)
async def detect_ingredients(file: UploadFile = File(...)):
    """
    Step 1: Uploads a fridge photo, runs Gemini 3.8 Flash Vision to detect
    raw ingredients, vegetables, dairy, and produces in the Indian kitchen.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be a valid image (JPEG, PNG, WEBP).",
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    detected_items, is_mock = detect_fridge_ingredients(
        contents, mime_type=file.content_type
    )

    return DetectionResponse(
        detected_ingredients=detected_items,
        detected_count=len(detected_items),
        is_mock=is_mock,
    )


@app.post("/api/mock-detect", response_model=DetectionResponse)
def mock_detect():
    """
    Instant mock endpoint for frontend devs (React/Flutter) to test the confirmation grid
    without uploading images.
    """
    mock_items = get_mock_indian_fridge_detection()
    return DetectionResponse(
        detected_ingredients=mock_items,
        detected_count=len(mock_items),
        is_mock=True,
    )


@app.post("/api/match-recipes", response_model=RecipeMatchResponse)
def match_recipes(payload: MatchRecipeRequest):
    """
    Step 2: Receives confirmed ingredients from the user's confirmation grid,
    matches against the Indian recipe corpus, and generates:
    1. Exact ready-to-cook recipes (100% matched)
    2. Partial recipes (Missing 1-2 items)
    3. Missing items shopping list (excluding Masala Dabba pantry staples)
    """
    if not payload.confirmed_ingredients:
        raise HTTPException(
            status_code=400, detail="Please provide at least one confirmed ingredient."
        )

    return match_recipes_from_corpus(
        confirmed_ingredients=payload.confirmed_ingredients,
        diet_preference=payload.diet_preference or "all",
    )


@app.get("/api/popular-ingredients")
def get_popular_ingredients():
    """Returns top everyday ingredients for quick-add pill tags on the frontend."""
    return {"popular_ingredients": POPULAR_INGREDIENTS}


@app.get("/api/pantry-staples")
def get_pantry_staples():
    """Returns assumed household basics (Masala Dabba) that are never put on shopping lists."""
    return {"pantry_staples": sorted(list(PANTRY_STAPLES))}


@app.get("/test", response_class=HTMLResponse)
def serve_testbed():
    """Serves the interactive 3-step testbed UI for frontend and backend verification."""
    if STATIC_HTML_PATH.exists():
        return STATIC_HTML_PATH.read_text(encoding="utf-8")
    return "<h1>Testbed HTML not found</h1>"
