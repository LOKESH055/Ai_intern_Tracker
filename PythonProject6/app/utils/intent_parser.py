# app/utils/intent_parser.py
import re


# Keywords that signal an internship search request
SEARCH_TRIGGERS = [
    "find", "search", "look for", "show me", "get me",
    "list", "fetch", "discover", "explore", "recommend"
]

INTERNSHIP_KEYWORDS = [
    "internship", "internships", "intern", "interns",
    "placement", "placements", "apprenticeship"
]

# Common roles to detect in the query
ROLE_KEYWORDS = [
    "data science", "machine learning", "software", "engineering",
    "web development", "frontend", "backend", "fullstack", "full stack",
    "marketing", "finance", "business", "design", "ui/ux", "devops",
    "cybersecurity", "cloud", "ai", "artificial intelligence", "nlp",
    "python", "java", "react", "android", "ios", "product management"
]

# Location keywords
LOCATION_KEYWORDS = [
    "india", "remote", "usa", "uk", "bangalore", "mumbai", "delhi",
    "hyderabad", "chennai", "pune", "new york", "london", "canada",
    "australia", "singapore", "germany", "europe", "asia"
]


def parse_search_intent(user_message: str) -> dict:
    """
    Analyze a user message and extract search intent.

    Returns:
        {
            "is_search": bool,
            "query": str,       # e.g. "Data Science internship"
            "location": str,    # e.g. "India" or ""
            "num_results": int  # 5, 10, or 20
        }
    """
    msg = user_message.lower().strip()

    # Check if this is a search request
    has_trigger = any(trigger in msg for trigger in SEARCH_TRIGGERS)
    has_internship = any(kw in msg for kw in INTERNSHIP_KEYWORDS)

    # Also trigger if they just mention a role + internship directly
    # e.g. "Data Science internships" without "find"
    is_search = (has_trigger or has_internship) and (
        has_trigger or any(role in msg for role in ROLE_KEYWORDS)
    )

    if not is_search:
        return {"is_search": False, "query": "", "location": "", "num_results": 10}

    # Extract role
    query = "internship"
    for role in ROLE_KEYWORDS:
        if role in msg:
            query = f"{role} internship"
            break

    # Extract location
    location = ""
    for loc in LOCATION_KEYWORDS:
        if loc in msg:
            location = loc.title()
            break

    # Extract number of results requested
    num_results = 10  # default
    if "top 5" in msg or "5 intern" in msg:
        num_results = 5
    elif "top 20" in msg or "20 intern" in msg:
        num_results = 20

    return {
        "is_search": True,
        "query": query,
        "location": location,
        "num_results": num_results
    }