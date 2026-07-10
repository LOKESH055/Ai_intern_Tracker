# app/services/cloudant_client.py
from ibmcloudant.cloudant_v1 import CloudantV1, Document
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from app.utils.config import Config
import datetime
import uuid


# Database names
DB_PROFILES = "user-profiles"
DB_SEARCHES = "job-searches"
DB_APPLICATIONS = "job-applications"

ALL_DATABASES = [DB_PROFILES, DB_SEARCHES, DB_APPLICATIONS]


def get_cloudant_client() -> CloudantV1:
    authenticator = IAMAuthenticator(Config.CLOUDANT_APIKEY)
    client = CloudantV1(authenticator=authenticator)
    client.set_service_url(Config.CLOUDANT_URL)
    return client


def initialize_databases():
    """Create all required databases if they don't exist."""
    client = get_cloudant_client()
    existing = [db["key"] for db in client.get_all_dbs().get_result()]

    for db_name in ALL_DATABASES:
        if db_name not in existing:
            client.put_database(db=db_name).get_result()
            print(f"Created database: {db_name}")
        else:
            print(f"Database already exists: {db_name}")


# ── User Profile Operations ──────────────────────────────────

def save_user_profile(profile: dict) -> str:
    """Save or update user profile. Returns document ID."""
    client = get_cloudant_client()
    profile_id = profile.get("_id", "default_user")

    # Check if profile exists
    try:
        existing = client.get_document(
            db=DB_PROFILES,
            doc_id=profile_id
        ).get_result()
        # Update existing — preserve _rev for Cloudant MVCC
        profile["_id"] = profile_id
        profile["_rev"] = existing["_rev"]
    except Exception:
        # New profile
        profile["_id"] = profile_id

    profile["updated_at"] = _now()
    doc = Document.from_dict(profile)
    response = client.post_document(db=DB_PROFILES, document=doc).get_result()
    return response["id"]


def get_user_profile(profile_id: str = "default_user") -> dict:
    """Retrieve user profile. Returns empty dict if not found."""
    client = get_cloudant_client()
    try:
        return client.get_document(
            db=DB_PROFILES,
            doc_id=profile_id
        ).get_result()
    except Exception:
        return {}


# ── Job Search History Operations ────────────────────────────

def save_job_search(query: str, location: str, jobs: list[dict]) -> str:
    """Save a job search and its results."""
    client = get_cloudant_client()
    doc_id = f"search_{uuid.uuid4().hex[:8]}"

    # Store only essential job fields to save space
    slim_jobs = [
        {
            "id": j.get("id", ""),
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "is_remote": j.get("is_remote", False),
            "apply_link": j.get("apply_link", ""),
            "posted_date": j.get("posted_date", ""),
            "salary_min": j.get("salary_min"),
            "salary_max": j.get("salary_max"),
        }
        for j in jobs
    ]

    document = {
        "_id": doc_id,
        "type": "job_search",
        "query": query,
        "location": location,
        "job_count": len(jobs),
        "jobs": slim_jobs,
        "searched_at": _now(),
    }

    doc = Document.from_dict(document)
    response = client.post_document(db=DB_SEARCHES, document=doc).get_result()
    return response["id"]


def get_search_history(limit: int = 10) -> list[dict]:
    """Get recent job searches — sorted by date, newest first."""
    client = get_cloudant_client()
    try:
        response = client.post_all_docs(
            db=DB_SEARCHES,
            include_docs=True,
            limit=50  # fetch more, filter and sort manually
        ).get_result()

        # Filter only job_search type docs (not monitors)
        searches = [
            row["doc"] for row in response.get("rows", [])
            if "doc" in row
            and row["doc"].get("type") == "job_search"
        ]

        # Sort by searched_at descending (newest first)
        searches.sort(
            key=lambda x: x.get("searched_at", ""),
            reverse=True
        )

        return searches[:limit]
    except Exception:
        return []


def save_job(job: dict, notes: str = "") -> str:
    """Save an internship to the applications tracker."""
    client = get_cloudant_client()
    doc_id = f"job_{job.get('id', uuid.uuid4().hex[:8])}"

    # Check if already saved
    try:
        existing = client.get_document(
            db=DB_APPLICATIONS,
            doc_id=doc_id
        ).get_result()
        rev = existing["_rev"]
    except Exception:
        rev = None

    document = {
        "_id": doc_id,
        "type": "saved_job",
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "is_remote": job.get("is_remote", False),
        "apply_link": job.get("apply_link", ""),
        "posted_date": job.get("posted_date", ""),
        "salary_min": job.get("salary_min"),
        "salary_max": job.get("salary_max"),
        "status": "saved",   # saved → applied → interview → offered → rejected
        "notes": notes,
        "saved_at": _now(),
        "applied_at": None,
    }

    if rev:
        document["_rev"] = rev

    doc = Document.from_dict(document)
    response = client.post_document(db=DB_APPLICATIONS, document=doc).get_result()
    return response["id"]


def get_saved_jobs() -> list[dict]:
    """Get all saved/tracked jobs."""
    client = get_cloudant_client()
    try:
        response = client.post_all_docs(
            db=DB_APPLICATIONS,
            include_docs=True,
            descending=True
        ).get_result()
        return [row["doc"] for row in response.get("rows", []) if "doc" in row]
    except Exception:
        return []


def update_job_status(doc_id: str, status: str, notes: str = "") -> bool:
    """Update application status for a tracked job."""
    client = get_cloudant_client()
    try:
        existing = client.get_document(
            db=DB_APPLICATIONS,
            doc_id=doc_id
        ).get_result()

        existing["status"] = status
        existing["notes"] = notes
        if status == "applied":
            existing["applied_at"] = _now()

        doc = Document.from_dict(existing)
        client.post_document(db=DB_APPLICATIONS, document=doc).get_result()
        return True
    except Exception:
        return False


def delete_saved_job(doc_id: str) -> bool:
    """Delete a saved job."""
    client = get_cloudant_client()
    try:
        existing = client.get_document(
            db=DB_APPLICATIONS,
            doc_id=doc_id
        ).get_result()
        client.delete_document(
            db=DB_APPLICATIONS,
            doc_id=doc_id,
            rev=existing["_rev"]
        ).get_result()
        return True
    except Exception:
        return False


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"