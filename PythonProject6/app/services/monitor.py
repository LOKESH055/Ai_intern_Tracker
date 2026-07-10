# app/services/monitor.py
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.services.jsearch_client import search_internships
from app.services.cloudant_client import (
    save_job_search,
    get_search_history,
    get_saved_jobs
)
from app.utils.config import Config


# Global scheduler instance
_scheduler = None


# ── Email ────────────────────────────────────────────────────

def send_email_alert(new_jobs: list[dict], query: str):
    """Send email notification for new internship listings."""
    if not Config.SMTP_EMAIL or not Config.SMTP_PASSWORD:
        print("Email not configured — skipping notification")
        return

    if not new_jobs:
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎯 Hi {recipient_name}! {len(new_jobs)} New Internship(s) Found — {query}"
        msg["From"] = Config.SMTP_EMAIL
        # Use profile email if available
        try:
            from app.services.cloudant_client import get_user_profile
            profile = get_user_profile()
            recipient = profile.get("email", Config.SMTP_EMAIL)
            recipient_name = profile.get("name", "there")
        except Exception:
            recipient = Config.SMTP_EMAIL
            recipient_name = "there"

        msg["To"] = recipient

        # Plain text version
        text_lines = [
            f"New internships found for: {query}",
            f"Found at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]
        for i, job in enumerate(new_jobs, 1):
            text_lines.append(f"{i}. {job['title']} at {job['company']}")
            text_lines.append(f"   Location: {job['location']}")
            text_lines.append(f"   Apply: {job['apply_link']}")
            text_lines.append("")
        text_content = "\n".join(text_lines)

        # HTML version
        job_rows = ""
        for job in new_jobs:
            salary = ""
            if job.get("salary_min"):
                salary = (
                    f"{job.get('salary_currency','USD')} "
                    f"{job['salary_min']:,.0f}"
                    + (f"–{job['salary_max']:,.0f}" if job.get("salary_max") else "+")
                )

            job_rows += f"""
            <tr>
                <td style='padding:12px;border-bottom:1px solid #eee;'>
                    <b>{job['title']}</b><br>
                    <span style='color:#666;'>{job['company']}</span>
                </td>
                <td style='padding:12px;border-bottom:1px solid #eee;color:#666;'>
                    {'🌐 Remote' if job.get('is_remote') else job.get('location','—')}
                </td>
                <td style='padding:12px;border-bottom:1px solid #eee;color:#666;'>
                    {salary or '—'}
                </td>
                <td style='padding:12px;border-bottom:1px solid #eee;'>
                    <a href='{job.get("apply_link","#")}'
                       style='background:#4A90D9;color:white;padding:6px 14px;
                              border-radius:4px;text-decoration:none;'>
                        Apply
                    </a>
                </td>
            </tr>
            """

        html_content = f"""
        <html><body style='font-family:Arial,sans-serif;max-width:700px;margin:auto;'>
            <div style='background:#4A90D9;padding:24px;border-radius:8px 8px 0 0;'>
                <h2 style='color:white;margin:0;'>
                    🎯 {len(new_jobs)} New Internship(s) Found
                </h2>
                <p style='color:#ddd;margin:8px 0 0;'>Query: <b>{query}</b></p>
            </div>
            <div style='background:#f9f9f9;padding:20px;border-radius:0 0 8px 8px;'>
                <table width='100%' style='border-collapse:collapse;background:white;
                                           border-radius:8px;overflow:hidden;'>
                    <thead>
                        <tr style='background:#f0f0f0;'>
                            <th style='padding:12px;text-align:left;'>Role</th>
                            <th style='padding:12px;text-align:left;'>Location</th>
                            <th style='padding:12px;text-align:left;'>Salary</th>
                            <th style='padding:12px;text-align:left;'>Apply</th>
                        </tr>
                    </thead>
                    <tbody>{job_rows}</tbody>
                </table>
                <p style='color:#888;font-size:12px;margin-top:20px;'>
                    Sent by your Internship Discovery Assistant · IBM watsonx.ai
                </p>
            </div>
        </html></body>
        """

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, recipient, msg.as_string())

        print(f"✅ Email sent: {len(new_jobs)} new jobs for '{query}'")

    except Exception as e:
        print(f"❌ Email failed: {str(e)}")


# ── Job comparison ───────────────────────────────────────────

def find_new_jobs(current_jobs: list[dict], previous_jobs: list[dict]) -> list[dict]:
    """
    Compare current search results against previous ones.
    Returns only jobs that weren't in the previous search.
    """
    previous_ids = {job.get("id", "") for job in previous_jobs}
    previous_titles = {
        f"{job.get('title','')}_{job.get('company','')}".lower()
        for job in previous_jobs
    }

    new_jobs = []
    for job in current_jobs:
        job_id = job.get("id", "")
        title_key = f"{job.get('title','')}_{job.get('company','')}".lower()

        # Consider it new if neither ID nor title+company matches
        if job_id not in previous_ids and title_key not in previous_titles:
            new_jobs.append(job)

    return new_jobs


# ── Monitor job ──────────────────────────────────────────────

def run_monitor_check(query: str, location: str, notification_placeholder=None):
    """
    Run a single monitoring check for a query.
    Fetches new jobs, compares with history, sends email if new ones found.
    """
    print(f"[Monitor] Checking: '{query}' in '{location}' at {datetime.datetime.now()}")

    try:
        # Fetch current listings
        current_jobs = search_internships(query=query, location=location, num_pages=2)

        # Get last search results for comparison
        history = get_search_history(limit=5)
        previous_jobs = []
        for h in history:
            if h.get("query", "").lower() == query.lower():
                previous_jobs = h.get("jobs", [])
                break

        # Find new jobs
        new_jobs = find_new_jobs(current_jobs, previous_jobs)

        # Save this search to Cloudant
        save_job_search(query, location, current_jobs)

        # Notify if new jobs found
        if new_jobs:
            print(f"[Monitor] Found {len(new_jobs)} new jobs!")
            send_email_alert(new_jobs, query)

            # Update in-app notification state
            if "monitor_notifications" not in st.session_state:
                st.session_state["monitor_notifications"] = []
            st.session_state["monitor_notifications"].append({
                "query": query,
                "count": len(new_jobs),
                "jobs": new_jobs,
                "time": datetime.datetime.now().strftime("%H:%M"),
            })
        else:
            print(f"[Monitor] No new jobs found for '{query}'")

        return len(new_jobs)

    except Exception as e:
        print(f"[Monitor] Error checking '{query}': {str(e)}")
        return 0


# ── Scheduler ────────────────────────────────────────────────

def start_monitoring(query: str, location: str = "", interval_hours: int = 6):
    """Start background monitoring for a query."""
    global _scheduler

    # Initialize scheduler if needed
    if _scheduler is None:
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.start()

    job_id = f"monitor_{query.replace(' ', '_')}"

    # Remove existing job with same ID if any
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    # Add new monitoring job
    _scheduler.add_job(
        func=run_monitor_check,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[query, location],
        id=job_id,
        name=f"Monitor: {query}",
        next_run_time=datetime.datetime.now() + datetime.timedelta(hours=interval_hours)
    )

    print(f"[Monitor] Started monitoring '{query}' every {interval_hours}h")

    # Save monitoring state
    if "active_monitors" not in st.session_state:
        st.session_state["active_monitors"] = {}

    st.session_state["active_monitors"][job_id] = {
        "query": query,
        "location": location,
        "interval_hours": interval_hours,
        "started_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "next_run": (
            datetime.datetime.now() +
            datetime.timedelta(hours=interval_hours)
        ).strftime("%Y-%m-%d %H:%M"),
        "job_id": job_id,
    }

    return job_id


def stop_monitoring(job_id: str):
    """Stop a specific monitoring job."""
    global _scheduler
    if _scheduler and _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)

    if "active_monitors" in st.session_state:
        st.session_state["active_monitors"].pop(job_id, None)

    print(f"[Monitor] Stopped monitoring job: {job_id}")


def stop_all_monitoring():
    """Stop all monitoring jobs."""
    global _scheduler
    if _scheduler:
        _scheduler.remove_all_jobs()

    if "active_monitors" in st.session_state:
        st.session_state["active_monitors"] = {}

    print("[Monitor] All monitoring stopped")


def get_active_monitors() -> dict:
    """Get all active monitoring jobs."""
    return st.session_state.get("active_monitors", {})


def is_monitoring(query: str) -> bool:
    """Check if a query is being monitored."""
    job_id = f"monitor_{query.replace(' ', '_')}"
    monitors = get_active_monitors()
    return job_id in monitors