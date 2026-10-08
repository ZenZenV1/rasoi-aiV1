from pydantic import BaseModel, Field
from typing import List, Optional


class DetectedIngredient(BaseModel):
    id: str = Field(..., description="Unique identifier for the ingredient")
    name: str = Field(..., description="English common name (e.g. tomatoes, paneer)")
    hindi_name: str = Field(..., description="Hindi/Romanized name (e.g. टमाटर / Tamatar)")
    category: str = Field(..., description="Produce, Dairy, Protein, Condiments, etc.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")


class DetectionResponse(BaseModel):
    detected_ingredients: List[DetectedIngredient]
    detected_count: int
    is_mock: bool = False


class MatchRecipeRequest(BaseModel):
    confirmed_ingredients: List[str] = Field(..., min_length=1, description="List of user-confirmed ingredients")
    diet_preference: Optional[str] = Field(default="all", description="Filter: 'all', 'veg', 'non-veg'")


class RecipeItem(BaseModel):
    id: str
    title: str
    hindi_title: str
    match_percentage: int
    match_status: str  # "Ready to Cook" (100%), "Missing 1-2 Items", etc.
    available_ingredients: List[str]
    missing_ingredients: List[str]
    pantry_staples: List[str]
    prep_time_minutes: int
    difficulty: str
    servings: int
    instructions: List[str]
    tags: List[str]
    youtube_url: str = ""
    is_ai_generated: bool = False


class ShoppingItem(BaseModel):
    item: str
    hindi_name: str = ""
    category: str
    needed_for_recipes: List[str]


class RecipeMatchResponse(BaseModel):
    exact_matches: List[RecipeItem]
    partial_matches: List[RecipeItem]
    shopping_list: List[ShoppingItem]
    total_recipes_found: int
    confirmed_ingredients_count: int
