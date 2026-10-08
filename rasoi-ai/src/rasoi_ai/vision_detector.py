import os
import json
import base64
import logging
from typing import List, Tuple
from pydantic import BaseModel, Field

from .models import DetectedIngredient

logger = logging.getLogger(__name__)


class VisionDetectionResult(BaseModel):
    items: List[DetectedIngredient] = Field(
        ..., description="List of recognized kitchen ingredients from the fridge photo"
    )


def get_mock_indian_fridge_detection() -> List[DetectedIngredient]:
    """Realistic Indian fridge inventory for demo fallback."""
    return [
        DetectedIngredient(
            id="ing_1",
            name="paneer",
            hindi_name="पनीर / Paneer",
            category="Dairy",
            confidence=0.96,
        ),
        DetectedIngredient(
            id="ing_2",
            name="capsicum",
            hindi_name="शिमला मिर्च / Shimla Mirch",
            category="Vegetables",
            confidence=0.92,
        ),
        DetectedIngredient(
            id="ing_3",
            name="tomatoes",
            hindi_name="टमाटर / Tamatar",
            category="Vegetables",
            confidence=0.95,
        ),
        DetectedIngredient(
            id="ing_4",
            name="onions",
            hindi_name="प्याज / Pyaz",
            category="Vegetables",
            confidence=0.91,
        ),
        DetectedIngredient(
            id="ing_5",
            name="green chillies",
            hindi_name="हरी मिर्च / Hari Mirch",
            category="Produce",
            confidence=0.89,
        ),
        DetectedIngredient(
            id="ing_6",
            name="dahi",
            hindi_name="दही / Curd",
            category="Dairy",
            confidence=0.87,
        ),
        DetectedIngredient(
            id="ing_7",
            name="ginger",
            hindi_name="अदरक / Adrak",
            category="Produce",
            confidence=0.84,
        ),
        DetectedIngredient(
            id="ing_8",
            name="coriander",
            hindi_name="हरा धनिया / Hara Dhaniya",
            category="Herbs",
            confidence=0.82,
        ),
    ]


import io
from PIL import Image

def optimize_image(image_bytes: bytes, max_dim: int = 1024) -> Tuple[bytes, str]:
    """Resizes high-resolution camera photos to 1024px to reduce upload latency by 90%."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((max_dim, max_dim))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"Could not resize image with PIL: {e}")
        return image_bytes, "image/jpeg"


def detect_fridge_ingredients(
    image_bytes: bytes, mime_type: str = "image/jpeg"
) -> Tuple[List[DetectedIngredient], bool]:
    """
    Analyzes a fridge photo using Gemini 3.5 Flash-Lite for fast, sub-10 second recognition.
    Extracts individual kitchen ingredients, vegetables, dairy, and produces.
    Returns (List[DetectedIngredient], is_mock).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    force_mock = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

    if force_mock or not api_key:
        logger.info("Using mock fridge vision detection.")
        return get_mock_indian_fridge_detection(), True

    try:
        from google import genai

        # Optimize image size for lightning-fast network transfer
        compressed_bytes, safe_mime = optimize_image(image_bytes)
        encoded_image = base64.b64encode(compressed_bytes).decode("utf-8")

        client = genai.Client(api_key=api_key)

        prompt = (
            "You are an expert AI for kitchens and cooking. "
            "Inspect this refrigerator photo carefully. "
            "Identify up to 15 primary distinct raw fresh food ingredients, vegetables, fruits, dairy, eggs, and herbs. "
            "For each detected item, return: "
            "1. name: lowercase standard English ingredient name (e.g., 'tomatoes', 'bell peppers', 'broccoli', 'cabbage', 'paneer', 'apples') "
            "2. hindi_name: Romanized Hindi name if applicable (e.g. 'Tamatar', 'Shimla Mirch', 'Gobi') "
            "3. category: 'Vegetables', 'Fruits', 'Dairy', 'Produce', 'Herbs', or 'Protein' "
            "4. confidence: float between 0.0 and 1.0 "
        )

        interaction = client.interactions.create(
            model="gemini-3.5-flash-lite",
            input=[
                {"type": "image", "data": encoded_image, "mime_type": safe_mime},
                {"type": "text", "text": prompt},
            ],
            response_format=[
                {
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": VisionDetectionResult.model_json_schema(),
                }
            ],
        )

        output_text = interaction.output_text
        if not output_text:
            raise ValueError("Empty response from Gemini vision model.")

        data = json.loads(output_text)
        result = VisionDetectionResult.model_validate(data)

        # Normalize names to lowercase
        for item in result.items:
            item.name = item.name.lower().strip()

        return result.items, False

    except Exception as e:
        logger.warning(f"Gemini vision call failed ({e}). Falling back to demo mock detection.")
        return get_mock_indian_fridge_detection(), True

