import os
import json
import logging
import urllib.parse
from typing import List, Dict, Set, Tuple
from .corpus import INDIAN_RECIPES, PANTRY_STAPLES
from .models import RecipeItem, ShoppingItem, RecipeMatchResponse

logger = logging.getLogger(__name__)

# Common synonyms mapping for Indian culinary ingredients
SYNONYMS_MAP = {
    "potato": "potatoes",
    "aloo": "potatoes",
    "alu": "potatoes",
    "tomato": "tomatoes",
    "tamatar": "tomatoes",
    "onion": "onions",
    "pyaz": "onions",
    "pyaaz": "onions",
    "capsicum": "capsicum",
    "shimla mirch": "capsicum",
    "bell pepper": "capsicum",
    "bell peppers": "capsicum",
    "curd": "dahi",
    "yogurt": "dahi",
    "dahi": "dahi",
    "cottage cheese": "paneer",
    "paneer": "paneer",
    "okra": "okra",
    "bhindi": "okra",
    "ladyfinger": "okra",
    "eggplant": "baingan",
    "brinjal": "baingan",
    "baingan": "baingan",
    "aubergine": "baingan",
    "green peas": "green peas",
    "peas": "green peas",
    "matar": "green peas",
    "cauliflower": "cauliflower",
    "gobi": "cauliflower",
    "gobhi": "cauliflower",
    "spinach": "palak",
    "palak": "palak",
    "bottle gourd": "lauki",
    "lauki": "lauki",
    "ghiya": "lauki",
    "doodhi": "lauki",
    "chilli": "green chillies",
    "chillies": "green chillies",
    "green chilli": "green chillies",
    "green chillies": "green chillies",
    "hari mirch": "green chillies",
    "coriander": "coriander",
    "cilantro": "coriander",
    "dhaniya": "coriander",
    "hara dhaniya": "coriander",
    "curry leaves": "curry leaves",
    "kadi patta": "curry leaves",
    "kadipatta": "curry leaves",
    "egg": "eggs",
    "eggs": "eggs",
    "anda": "eggs",
    "ande": "eggs",
    "methi": "methi",
    "fenugreek": "methi",
    "fenugreek leaves": "methi",
    "ginger": "ginger",
    "adrak": "ginger",
    "garlic": "garlic",
    "lahsun": "garlic",
    "cabbage": "cabbage",
    "patta gobi": "cabbage",
    "bandh gobi": "cabbage",
    "broccoli": "broccoli",
    "asparagus": "asparagus",
    "green leafy vegetables": "palak",
    "leafy greens": "palak",
    "greens": "palak",
    "herbs": "coriander",
    "lemon": "lemon",
    "lemons": "lemon",
    "lime": "lemon",
    "limes": "lemon",
    "nimbu": "lemon",
    "apple": "apples",
    "apples": "apples",
    "grape": "grapes",
    "grapes": "grapes",
    "green grapes": "grapes",
    "strawberry": "strawberries",
    "strawberries": "strawberries",
    "pineapple": "pineapple",
    "grapefruit": "grapefruit",
    "orange": "oranges",
    "oranges": "oranges",
}


def normalize_ingredient_name(name: str) -> str:
    """Normalizes an ingredient name to its canonical form."""
    cleaned = name.lower().strip()
    return SYNONYMS_MAP.get(cleaned, cleaned)


def is_pantry_staple(item_name: str) -> bool:
    """Checks if an ingredient is an assumed staple (salt, haldi, oil, etc.)."""
    norm = normalize_ingredient_name(item_name)
    return norm in PANTRY_STAPLES or any(staple in norm for staple in PANTRY_STAPLES)


def match_recipes_from_corpus(
    confirmed_ingredients: List[str], diet_preference: str = "all"
) -> RecipeMatchResponse:
    """
    Matches user's confirmed ingredients against the Indian Recipe Dataset.
    Calculates exact (100%) and partial matches, and generates missing items shopping list.
    """
    normalized_user_items = {
        normalize_ingredient_name(item) for item in confirmed_ingredients
    }

    exact_matches: List[RecipeItem] = []
    partial_matches: List[RecipeItem] = []
    shopping_dict: Dict[str, Dict[str, any]] = {}

    for r in INDIAN_RECIPES:
        # Check diet filter
        if diet_preference == "veg" and r.get("diet") != "veg":
            continue
        if diet_preference == "non-veg" and r.get("diet") not in ("non-veg", "egg"):
            continue
        if diet_preference == "jain":
            if r.get("diet") != "veg":
                continue
            jain_forbidden = {
                "onions", "pyaz", "pyaaz", "garlic", "lahsun", "potatoes", "aloo", "alu",
                "ginger", "adrak", "radish", "mooli", "carrot", "gajar", "beetroot", "chukandar"
            }
            core_and_optional = r["core_ingredients"] + r.get("optional_ingredients", [])
            if any(normalize_ingredient_name(item) in jain_forbidden for item in core_and_optional):
                continue

        core = r["core_ingredients"]
        norm_core = [normalize_ingredient_name(ing) for ing in core]

        matched_core = [ing for ing in norm_core if ing in normalized_user_items]
        missing_core = [
            ing
            for ing in norm_core
            if ing not in normalized_user_items and not is_pantry_staple(ing)
        ]

        # Calculate match ratio based on core ingredients
        total_core = len(norm_core)
        match_ratio = (
            len(matched_core) / total_core if total_core > 0 else 0.0
        )
        match_pct = int(round(match_ratio * 100))

        if match_pct == 100:
            status = "Ready to Cook"
        elif len(missing_core) == 1:
            status = "Missing 1 Ingredient"
        elif len(missing_core) == 2:
            status = "Missing 2 Ingredients"
        else:
            status = f"{match_pct}% Match"

        # Generate direct YouTube search/video link
        yt_query = f"how to make {r['title']} recipe"
        youtube_url = r.get("youtube_url") or f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(yt_query)}"

        recipe_item = RecipeItem(
            id=r["id"],
            title=r["title"],
            hindi_title=r.get("hindi_title", ""),
            match_percentage=match_pct,
            match_status=status,
            available_ingredients=matched_core,
            missing_ingredients=missing_core,
            pantry_staples=["Haldi", "Namak", "Jeera", "Oil/Ghee"],
            prep_time_minutes=r["prep_time_minutes"],
            difficulty=r["difficulty"],
            servings=r["servings"],
            instructions=r["instructions"],
            tags=r.get("tags", []),
            youtube_url=youtube_url,
            is_ai_generated=False,
        )

        if match_pct == 100:
            exact_matches.append(recipe_item)
        elif match_pct >= 50:
            partial_matches.append(recipe_item)
            # Add missing ingredients to the aggregated shopping list
            for missing_ing in missing_core:
                if missing_ing not in shopping_dict:
                    category = "Vegetables"
                    if missing_ing in ("paneer", "dahi", "milk", "butter"):
                        category = "Dairy"
                    elif missing_ing in ("eggs", "chicken"):
                        category = "Protein"
                    elif missing_ing in ("bread", "pav"):
                        category = "Bakery"
                    elif missing_ing in ("toor dal", "moong dal", "chana dal", "besan", "suji", "poha", "atta"):
                        category = "Grains & Pulses"

                    shopping_dict[missing_ing] = {
                        "item": missing_ing.title(),
                        "category": category,
                        "needed_for": [r["title"]],
                    }
                else:
                    if r["title"] not in shopping_dict[missing_ing]["needed_for"]:
                        shopping_dict[missing_ing]["needed_for"].append(r["title"])

    # Sort matches by percentage descending
    exact_matches.sort(key=lambda x: x.match_percentage, reverse=True)
    partial_matches.sort(key=lambda x: x.match_percentage, reverse=True)

    # Convert shopping dictionary to list
    shopping_list = [
        ShoppingItem(
            item=val["item"],
            hindi_name="",
            category=val["category"],
            needed_for_recipes=val["needed_for"],
        )
        for val in shopping_dict.values()
    ]

    total_count = len(exact_matches) + len(partial_matches)

    return RecipeMatchResponse(
        exact_matches=exact_matches,
        partial_matches=partial_matches,
        shopping_list=shopping_list,
        total_recipes_found=total_count,
        confirmed_ingredients_count=len(confirmed_ingredients),
    )
