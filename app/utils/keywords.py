"""
Semantic-aware keyword extraction for stock video search.

Problem: Stock APIs match keywords, not meaning.
Solution: Add context words that push results toward the right semantic space.

Example:
  "garage" alone → random garage videos
  "garage startup technology" → tech startup origin videos
"""
from __future__ import annotations

import re
from typing import List, Tuple, Optional

# Words to skip
SKIP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "it", "its", "this", "that", "these", "those", "what", "which", "who",
    "all", "each", "every", "some", "any", "no", "not", "only", "just",
    "about", "really", "actually", "basically", "very", "much", "many",
    "thing", "things", "stuff", "way", "lot", "kind", "type",
    "year", "years", "time", "day", "today", "now", "around", "nearly",
    "make", "get", "take", "use", "show", "look", "become",
    "picture", "imagine", "think", "say", "started", "shapes",
}

# Visual keywords with scores
VISUAL_BOOST = {
    # Devices
    "smartphone": 10, "phone": 10, "laptop": 10, "computer": 10, "tablet": 10,
    "screen": 8, "monitor": 8, "camera": 9, "smartwatch": 10, "headphones": 9,
    
    # People & Actions  
    "person": 9, "people": 9, "man": 8, "woman": 8, "team": 9,
    "meeting": 10, "office": 10, "working": 9, "typing": 8, "shopping": 10,
    
    # Places
    "city": 10, "street": 8, "building": 8, "store": 9, "home": 8,
    "factory": 9, "warehouse": 8, "classroom": 9, "garage": 9, "workshop": 9,
    
    # Business
    "stock": 10, "chart": 10, "graph": 9, "market": 9, "trading": 9,
    "business": 8, "corporate": 8, "growth": 8,
    
    # Tech
    "technology": 8, "digital": 7, "software": 8, "code": 8, "cloud": 8,
    "app": 8, "mobile": 9, "data": 7, "server": 8,
    
    # Modifiers
    "modern": 7, "vintage": 8, "retro": 8, "futuristic": 8,
    "closeup": 7, "aerial": 8, "professional": 7,
}

# Semantic context enhancers
# Maps keywords to additional context words that improve semantic matching
SEMANTIC_CONTEXT = {
    # Tech/Startup context
    "garage": ["startup", "entrepreneur", "innovation"],
    "workshop": ["creative", "maker", "professional"],
    
    # Business context
    "stock": ["finance", "investment", "professional"],
    "chart": ["data", "analytics", "business"],
    "market": ["finance", "trading", "professional"],
    "growth": ["success", "business", "upward"],
    
    # Product context
    "smartphone": ["mobile", "technology", "modern"],
    "laptop": ["work", "professional", "modern"],
    "tablet": ["technology", "modern", "digital"],
    
    # People context
    "meeting": ["business", "professional", "corporate"],
    "office": ["business", "professional", "modern"],
    "team": ["collaboration", "business", "professional"],
    "shopping": ["retail", "consumer", "store"],
    "classroom": ["education", "learning", "students"],
    
    # Abstract concepts → concrete visuals
    "digital": ["technology", "computer", "screen"],
    "cloud": ["technology", "data", "server"],
    "global": ["world", "international", "connected"],
    "connected": ["network", "technology", "communication"],
    "ecosystem": ["technology", "connected", "digital"],
    "transformation": ["change", "evolution", "progress"],
}

# Theme detection patterns
THEME_PATTERNS = {
    "tech_startup": {
        "triggers": ["startup", "garage", "founded", "company", "innovation"],
        "context": ["technology", "entrepreneur", "silicon valley"],
    },
    "finance": {
        "triggers": ["stock", "market", "investment", "growth", "percent", "increase"],
        "context": ["business", "professional", "finance"],
    },
    "product": {
        "triggers": ["smartphone", "laptop", "tablet", "device", "hardware", "product"],
        "context": ["technology", "modern", "sleek"],
    },
    "corporate": {
        "triggers": ["business", "company", "corporate", "enterprise", "institution"],
        "context": ["professional", "office", "modern"],
    },
}


def detect_theme(text: str, tags: List[str]) -> Optional[str]:
    """Detect the semantic theme from text and tags."""
    combined = text.lower() + " " + " ".join(tags).lower()
    
    best_theme = None
    best_score = 0
    
    for theme, config in THEME_PATTERNS.items():
        score = sum(1 for trigger in config["triggers"] if trigger in combined)
        if score > best_score:
            best_score = score
            best_theme = theme
    
    return best_theme if best_score >= 1 else None


def get_semantic_context(keyword: str, theme: Optional[str] = None) -> List[str]:
    """Get additional context words for a keyword."""
    context = []
    
    # Add keyword-specific context
    if keyword in SEMANTIC_CONTEXT:
        context.extend(SEMANTIC_CONTEXT[keyword][:1])  # Just top 1
    
    # Add theme context
    if theme and theme in THEME_PATTERNS:
        context.extend(THEME_PATTERNS[theme]["context"][:1])  # Just top 1
    
    return context


def extract_keywords(text: str, tags: List[str] = None) -> List[str]:
    """
    Extract keywords with semantic context for better video matching.
    """
    scored: List[Tuple[str, int]] = []
    seen = set()
    
    # Detect overall theme
    theme = detect_theme(text, tags or [])
    
    # Process user tags (split multi-word)
    if tags:
        for tag in tags:
            words = tag.lower().strip().split()
            for word in words:
                word = word.strip()
                if word and len(word) >= 3 and word not in SKIP_WORDS and word not in seen:
                    base_score = 50 + VISUAL_BOOST.get(word, 0)
                    scored.append((word, base_score))
                    seen.add(word)
    
    # Add from narration (only visual keywords)
    if len(scored) < 4:
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        for word in text_clean.split():
            if len(word) >= 3 and word not in SKIP_WORDS and word not in seen:
                if word in VISUAL_BOOST:
                    scored.append((word, VISUAL_BOOST[word]))
                    seen.add(word)
    
    # Sort by score
    scored.sort(key=lambda x: -x[1])
    
    # Get top keywords
    keywords = [w for w, _ in scored[:3]]
    
    # Add semantic context for the top keyword
    if keywords:
        context = get_semantic_context(keywords[0], theme)
        for ctx in context:
            if ctx not in seen and len(keywords) < 4:
                keywords.append(ctx)
                seen.add(ctx)
    
    return keywords if keywords else ["technology", "business"]


def build_search_query(narration: str, tags: List[str] = None) -> str:
    """Build semantically-aware search query (max 3-4 words)."""
    keywords = extract_keywords(narration, tags)
    return " ".join(keywords[:4])


def get_fallback_queries(primary_query: str) -> List[str]:
    """Generate progressively broader fallback queries."""
    words = primary_query.split()
    fallbacks = []
    
    if len(words) >= 2:
        fallbacks.append(" ".join(words[:2]))
    if words:
        fallbacks.append(words[0])
    
    fallbacks.extend(["business professional", "technology modern"])
    return fallbacks[:4]
