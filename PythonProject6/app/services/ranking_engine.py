# app/services/ranking_engine.py
import json
import re
from app.services.watsonx_client import get_watsonx_client


RANKING_PROMPT_TEMPLATE = """You are an expert career advisor. Analyze these internship listings and rank them.

USER PROFILE:
{user_profile}

INTERNSHIP LISTINGS:
{job_listings}

Score each internship on these 7 dimensions (0-10 each):
1. company_reputation     - Brand value, size, industry standing
2. learning_opportunity   - Skill development, mentorship, exposure
3. career_growth          - Long-term impact on resume and career
4. stipend_value          - Compensation relative to role and location
5. remote_flexibility     - Remote/hybrid options (10=fully remote, 5=hybrid, 2=onsite)
6. application_difficulty - How accessible it is (10=easy to apply, 1=very competitive)
7. beginner_friendliness  - Suitable for students with limited experience

Return ONLY a valid JSON array. No explanation outside the JSON. Format:
[
  {{
    "rank": 1,
    "job_index": 3,
    "title": "exact job title",
    "company": "exact company name",
    "scores": {{
      "company_reputation": 8,
      "learning_opportunity": 9,
      "career_growth": 8,
      "stipend_value": 7,
      "remote_flexibility": 5,
      "application_difficulty": 6,
      "beginner_friendliness": 8
    }},
    "total_score": 51,
    "verdict": "2-3 sentence explanation of why this ranks here and what makes it stand out or fall short."
  }}
]

Rank ALL {num_jobs} internships. Total score = sum of all 7 dimension scores."""


def rank_internships(jobs: list[dict], user_profile: dict = None, top_n: int = None) -> list[dict]:
    """
    Use watsonx to score and rank a list of internships.

    Args:
        jobs:         List of job dicts from JSearch
        user_profile: Optional dict with user's skills, experience level, preferences
        top_n:        If set, return only top N results

    Returns:
        List of ranked job dicts with scores
    """
    if not jobs:
        return []

    client = get_watsonx_client()

    # Build job listings text for the prompt
    job_text = _format_jobs_for_ranking(jobs)

    # Build user profile text
    profile_text = _format_user_profile(user_profile)

    prompt = RANKING_PROMPT_TEMPLATE.format(
        user_profile=profile_text,
        job_listings=job_text,
        num_jobs=len(jobs)
    )

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        ranked = _parse_ranking_response(response, jobs)

        if top_n:
            ranked = ranked[:top_n]

        return ranked

    except Exception as e:
        raise Exception(f"Ranking failed: {str(e)}")


def _format_jobs_for_ranking(jobs: list[dict]) -> str:
    """Format jobs into a numbered list for the ranking prompt."""
    lines = []
    for i, job in enumerate(jobs, 1):
        salary = ""
        if job.get("salary_min") and job.get("salary_max"):
            salary = f"Salary: {job['salary_currency']} {job['salary_min']:,.0f}-{job['salary_max']:,.0f}/{job.get('salary_period','yr').lower()}"
        elif job.get("salary_min"):
            salary = f"Salary: {job['salary_currency']} {job['salary_min']:,.0f}+"

        skills = ", ".join(job.get("required_skills", [])[:5]) or "Not specified"
        location = "Remote" if job.get("is_remote") else job.get("location", "Unknown")

        lines.append(
            f"[{i}] {job['title']} at {job['company']}\n"
            f"    Location: {location}\n"
            f"    Posted: {job.get('posted_date', 'Recently')}\n"
            f"    {salary}\n"
            f"    Skills needed: {skills}\n"
            f"    Publisher: {job.get('publisher', 'Unknown')}\n"
        )
    return "\n".join(lines)


def _format_user_profile(profile: dict = None) -> str:
    """Format user profile for the ranking prompt."""
    if not profile:
        return (
            "Student seeking internship. "
            "Assume beginner to intermediate level. "
            "Prefers good learning opportunities and reasonable stipend."
        )
    return (
        f"Education: {profile.get('education', 'Student')}\n"
        f"Skills: {', '.join(profile.get('skills', []))}\n"
        f"Experience: {profile.get('experience', 'Limited')}\n"
        f"Preferences: {profile.get('preferences', 'Open to all')}\n"
        f"Location preference: {profile.get('location_pref', 'Any')}"
    )


def _parse_ranking_response(response: str, original_jobs: list[dict]) -> list[dict]:
    """
    Parse the JSON ranking response from watsonx.
    Falls back gracefully if JSON is malformed.
    """
    # Extract JSON array from response
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON array found in ranking response")

    json_str = json_match.group(0)

    # Clean common JSON issues
    json_str = re.sub(r',\s*}', '}', json_str)   # trailing commas in objects
    json_str = re.sub(r',\s*]', ']', json_str)   # trailing commas in arrays

    ranked_data = json.loads(json_str)

    # Merge ranking data with original job data
    enriched = []
    for item in ranked_data:
        job_index = item.get("job_index", 1) - 1  # convert to 0-based
        if 0 <= job_index < len(original_jobs):
            original = original_jobs[job_index]
        else:
            original = {}

        enriched.append({
            **original,
            "rank": item.get("rank", len(enriched) + 1),
            "scores": item.get("scores", {}),
            "total_score": item.get("total_score", 0),
            "verdict": item.get("verdict", ""),
            "title": item.get("title", original.get("title", "")),
            "company": item.get("company", original.get("company", "")),
        })

    # Sort by rank to ensure correct order
    enriched.sort(key=lambda x: x.get("rank", 999))
    return enriched