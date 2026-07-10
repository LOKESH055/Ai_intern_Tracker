# app/services/jsearch_client.py
import requests
from app.utils.config import Config


JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com"

HEADERS = {
    "X-RapidAPI-Key": Config.RAPIDAPI_KEY,
    "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
}


def search_internships(query: str, location: str = "", num_pages: int = 1) -> list[dict]:
    """
    Search for internships using JSearch API.

    Args:
        query:     e.g. "Data Science internship"
        location:  e.g. "India", "Remote", "New York"
        num_pages: how many pages of results to fetch (10 results per page)

    Returns:
        List of cleaned internship dicts
    """
    # Build search query — always append "internship" if not already there
    if "internship" not in query.lower():
        query = f"{query} internship"

    # Add location to query if provided
    full_query = f"{query} {location}".strip()

    params = {
        "query": full_query,
        "page": "1",
        "num_pages": str(num_pages),
        "date_posted": "month",       # only last 30 days
        "employment_types": "INTERN",  # internships only
    }

    try:
        response = requests.get(
            # New - v2 endpoint
f"{JSEARCH_BASE_URL}/search-v2",
            headers=HEADERS,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        if data.get("status") != "OK":
            return []

        raw_jobs = data.get("data", {}).get("jobs", [])
        return [_clean_job(job) for job in raw_jobs]

    except requests.exceptions.Timeout:
        raise Exception("JSearch API timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            raise Exception("Invalid RapidAPI key. Check your RAPIDAPI_KEY in .env")
        elif e.response.status_code == 429:
            raise Exception("RapidAPI rate limit reached. Try again later.")
        raise Exception(f"JSearch API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to fetch internships: {str(e)}")


def _clean_job(job: dict) -> dict:
    """Extract only the fields we need from a raw JSearch result."""
    return {
        "id": job.get("job_id", ""),
        "title": job.get("job_title", "Unknown Title"),
        "company": job.get("employer_name", "Unknown Company"),
        "location": _format_location(job),
        "is_remote": job.get("job_is_remote", False),
        "description": job.get("job_description", "")[:800],  # cap at 800 chars
        "apply_link": job.get("job_apply_link", ""),
        "posted_date": _format_date(job.get("job_posted_at_datetime_utc", "")),
        "employment_type": job.get("job_employment_type", "INTERN"),
        "salary_min": job.get("job_min_salary"),
        "salary_max": job.get("job_max_salary"),
        "salary_currency": job.get("job_salary_currency", "USD"),
        "salary_period": job.get("job_salary_period", ""),
        "required_skills": job.get("job_required_skills") or [],
        "experience_required": job.get("job_required_experience", {}).get(
            "required_experience_in_months", None
        ),
        "publisher": job.get("job_publisher", ""),
    }


def _format_location(job: dict) -> str:
    """Build a readable location string."""
    if job.get("job_is_remote"):
        return "Remote"
    parts = [
        job.get("job_city", ""),
        job.get("job_state", ""),
        job.get("job_country", ""),
    ]
    return ", ".join(p for p in parts if p) or "Location not specified"


def _format_date(date_str: str) -> str:
    """Convert ISO date to readable format."""
    if not date_str:
        return "Recently posted"
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_ago = (now - dt).days
        if days_ago == 0:
            return "Today"
        elif days_ago == 1:
            return "Yesterday"
        elif days_ago < 7:
            return f"{days_ago} days ago"
        elif days_ago < 30:
            weeks = days_ago // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return "Recently posted"


def format_jobs_for_ai(jobs: list[dict]) -> str:
    if not jobs:
        return "No internships found for this search."

    lines = [f"REAL INTERNSHIP LISTINGS ({len(jobs)} found):\n"]

    for i, job in enumerate(jobs, 1):
        salary_str = ""
        if job["salary_min"] and job["salary_max"]:
            salary_str = (
                f"💰 Salary: {job['salary_currency']} "
                f"{job['salary_min']:,.0f}–{job['salary_max']:,.0f} "
                f"/{job['salary_period'].lower() if job['salary_period'] else 'year'}"
            )
        elif job["salary_min"]:
            salary_str = f"💰 Salary: {job['salary_currency']} {job['salary_min']:,.0f}+"

        skills_str = ""
        if job["required_skills"]:
            skills_str = f"🛠 Skills: {', '.join(job['required_skills'][:6])}"

        remote_str = "🌐 Remote" if job["is_remote"] else f"📍 {job['location']}"

        # Force the AI to include the apply link as a markdown hyperlink
        apply_str = f"[🔗 Apply Here]({job['apply_link']})" if job['apply_link'] else "No link available"

        lines.append(
            f"[{i}] **{job['title']}** at **{job['company']}**\n"
            f"    {remote_str}\n"
            f"    📅 Posted: {job['posted_date']}\n"
            + (f"    {salary_str}\n" if salary_str else "")
            + (f"    {skills_str}\n" if skills_str else "")
            + f"    Apply: {apply_str}\n"
        )

    return "\n".join(lines)