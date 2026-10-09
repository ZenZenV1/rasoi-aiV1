// Client-Side Offline Recipe Matcher for RasoiAI
// Runs 100% locally on the device with zero network latency.

const OFFLINE_SYNONYMS = {
  "bell pepper": "capsicum",
  "bell peppers": "capsicum",
  "green pepper": "capsicum",
  "shimla mirch": "capsicum",
  "tomato": "tomatoes",
  "tamatar": "tomatoes",
  "onion": "onions",
  "pyaz": "onions",
  "pyaaz": "onions",
  "potato": "potatoes",
  "aloo": "potatoes",
  "alu": "potatoes",
  "chilli": "green chillies",
  "chillies": "green chillies",
  "mirch": "green chillies",
  "curd": "dahi",
  "yogurt": "dahi",
  "adrak": "ginger",
  "dhaniya": "coriander",
  "cilantro": "coriander",
  "cabbage": "cabbage",
  "patta gobhi": "cabbage",
  "bandh gobi": "cabbage",
  "broccoli": "broccoli",
  "spinach": "palak",
  "greens": "palak",
  "leafy greens": "palak",
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
  "paneer": "paneer",
  "cottage cheese": "paneer",
  "egg": "eggs",
  "chicken": "chicken",
  "bread": "bread",
  "rice": "rice",
  "chawal": "rice"
};

function normalizeOfflineName(name) {
  const cleaned = (name || "").toLowerCase().trim();
  return OFFLINE_SYNONYMS[cleaned] || cleaned;
}

function isOfflinePantryStaple(name, staplesSet) {
  const norm = normalizeOfflineName(name);
  if (staplesSet.has(norm)) return true;
  for (const staple of staplesSet) {
    if (norm.includes(staple)) return true;
  }
  return false;
}

function matchRecipesOffline(confirmedItemsList, dietPreference = "all") {
  const data = window.RASOI_OFFLINE_DATA;
  if (!data || !data.recipes) {
    console.error("Offline dataset not loaded");
    return null;
  }

  const staplesSet = new Set(data.pantry_staples.map(s => s.toLowerCase()));
  const normalizedUserItems = new Set(confirmedItemsList.map(item => normalizeOfflineName(item)));

  const exactMatches = [];
  const partialMatches = [];
  const shoppingDict = {};

  const jainForbidden = new Set([
    "onions", "pyaz", "pyaaz", "garlic", "lahsun", "potatoes", "aloo", "alu",
    "ginger", "adrak", "radish", "mooli", "carrot", "gajar", "beetroot", "chukandar"
  ]);

  for (const r of data.recipes) {
    // Diet preference filtering
    if (dietPreference === "veg" && r.diet !== "veg") continue;
    if (dietPreference === "non-veg" && r.diet !== "non-veg" && r.diet !== "egg") continue;
    if (dietPreference === "jain") {
      if (r.diet !== "veg") continue;
      const allIngredients = (r.core_ingredients || []).concat(r.optional_ingredients || []);
      const hasForbidden = allIngredients.some(item => jainForbidden.has(normalizeOfflineName(item)));
      if (hasForbidden) continue;
    }

    const core = r.core_ingredients || [];
    const normCore = core.map(ing => normalizeOfflineName(ing));

    const matchedCore = normCore.filter(ing => normalizedUserItems.has(ing));
    const missingCore = normCore.filter(ing => !normalizedUserItems.has(ing) && !isOfflinePantryStaple(ing, staplesSet));

    const totalCore = normCore.length;
    const matchRatio = totalCore > 0 ? (matchedCore.length / totalCore) : 0;
    const matchPct = Math.round(matchRatio * 100);

    let status = `${matchPct}% Match`;
    if (matchPct === 100) {
      status = "Ready to Cook";
    } else if (missingCore.length === 1) {
      status = "Missing 1 Ingredient";
    } else if (missingCore.length === 2) {
      status = "Missing 2 Ingredients";
    }

    const ytQuery = `how to make ${r.title} recipe`;
    const youtubeUrl = r.youtube_url || `https://www.youtube.com/results?search_query=${encodeURIComponent(ytQuery)}`;

    const recipeItem = {
      id: r.id,
      title: r.title,
      hindi_title: r.hindi_title || "",
      match_percentage: matchPct,
      match_status: status,
      available_ingredients: matchedCore,
      missing_ingredients: missingCore,
      pantry_staples: ["Haldi", "Namak", "Jeera", "Oil/Ghee"],
      prep_time_minutes: r.prep_time_minutes,
      difficulty: r.difficulty,
      servings: r.servings,
      portion_capacity: `Serves ${r.servings} Persons`,
      instructions: r.instructions || [],
      tags: r.tags || [],
      youtube_url: youtubeUrl,
      is_ai_generated: false
    };

    if (matchPct === 100) {
      exactMatches.push(recipeItem);
    } else if (matchPct >= 50) {
      partialMatches.push(recipeItem);

      for (const missing of missingCore) {
        if (!shoppingDict[missing]) {
          let category = "Vegetables";
          if (["paneer", "dahi", "milk", "butter"].includes(missing)) category = "Dairy";
          else if (["eggs", "chicken"].includes(missing)) category = "Protein";
          else if (["bread", "pav"].includes(missing)) category = "Bakery";
          else if (["toor dal", "moong dal", "chana dal", "besan", "suji", "poha", "atta"].includes(missing)) category = "Grains & Pulses";

          shoppingDict[missing] = {
            item: missing.charAt(0).toUpperCase() + missing.slice(1),
            category: category,
            needed_for_recipes: [r.title]
          };
        } else {
          if (!shoppingDict[missing].needed_for_recipes.includes(r.title)) {
            shoppingDict[missing].needed_for_recipes.push(r.title);
          }
        }
      }
    }
  }

  exactMatches.sort((a, b) => b.match_percentage - a.match_percentage);
  partialMatches.sort((a, b) => b.match_percentage - a.match_percentage);

  return {
    exact_matches: exactMatches,
    partial_matches: partialMatches,
    shopping_list: Object.values(shoppingDict),
    total_recipes_found: exactMatches.length + partialMatches.length,
    confirmed_ingredients_count: confirmedItemsList.length,
    is_offline: true
  };
}
