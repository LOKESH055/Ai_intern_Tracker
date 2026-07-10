# app/components/tracked_jobs_ui.py
import streamlit as st
from app.services.cloudant_client import (
    get_saved_jobs,
    update_job_status,
    delete_saved_job,
    get_search_history,
    save_job
)


STATUS_COLORS = {
    "saved":      "#4A90D9",
    "applied":    "#f39c12",
    "interview":  "#9b59b6",
    "offered":    "#2ecc71",
    "rejected":   "#e74c3c",
}

STATUS_ICONS = {
    "saved":      "🔖",
    "applied":    "📨",
    "interview":  "🎤",
    "offered":    "🎉",
    "rejected":   "❌",
}


def render_tracked_jobs_page():
    st.markdown("""
        <h2 style='color: #4A90D9;'>📊 Tracked Jobs</h2>
        <p style='color: #888;'>Save and track your internship applications in IBM Cloudant</p>
        <hr>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔖 Saved Jobs", "🕐 Search History"])

    with tab1:
        _render_saved_jobs()

    with tab2:
        _render_search_history()


def _render_saved_jobs():
    """Render saved/tracked jobs with status management."""

    # ── Save from current search ─────────────────────────────
    last_jobs = st.session_state.get("last_jobs", [])
    if last_jobs:
        st.markdown("### 💾 Save from Current Search")
        st.markdown(f"You have **{len(last_jobs)}** jobs from your last search.")

        cols = st.columns(2)
        with cols[0]:
            selected_indices = st.multiselect(
                "Select jobs to save",
                options=range(len(last_jobs)),
                format_func=lambda i: f"{last_jobs[i]['title']} @ {last_jobs[i]['company']}"
            )
        with cols[1]:
            notes = st.text_input("Notes (optional)", placeholder="e.g. Strong match for my skills")

        if st.button("💾 Save Selected Jobs", disabled=not selected_indices):
            for i in selected_indices:
                try:
                    save_job(last_jobs[i], notes)
                except Exception as e:
                    st.error(f"Failed to save {last_jobs[i]['title']}: {e}")
            st.success(f"✅ Saved {len(selected_indices)} job(s) to Cloudant!")
            st.rerun()

        st.markdown("---")

    # ── Tracked jobs list ────────────────────────────────────
    st.markdown("### 📋 All Tracked Applications")

    try:
        jobs = get_saved_jobs()
    except Exception as e:
        st.error(f"Failed to load tracked jobs: {e}")
        return

    if not jobs:
        st.info("No saved jobs yet. Search for internships in the Chat tab and save them here.")
        return

    # Status filter
    status_filter = st.selectbox(
        "Filter by status",
        ["All", "saved", "applied", "interview", "offered", "rejected"]
    )

    filtered = jobs if status_filter == "All" else [
        j for j in jobs if j.get("status") == status_filter
    ]

    # Stats row
    status_counts = {}
    for j in jobs:
        s = j.get("status", "saved")
        status_counts[s] = status_counts.get(s, 0) + 1

    stat_cols = st.columns(5)
    for i, (status, icon) in enumerate(STATUS_ICONS.items()):
        with stat_cols[i]:
            count = status_counts.get(status, 0)
            color = STATUS_COLORS[status]
            st.markdown(
                f"<div style='text-align:center;padding:8px;background:{color}22;"
                f"border-radius:8px;border:1px solid {color};'>"
                f"<b style='color:{color};font-size:18px;'>{count}</b><br>"
                f"<span style='font-size:11px;'>{icon} {status.title()}</span></div>",
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Job cards
    for job in filtered:
        _render_job_tracker_card(job)


def _render_job_tracker_card(job: dict):
    status = job.get("status", "saved")
    color = STATUS_COLORS.get(status, "#888")
    icon = STATUS_ICONS.get(status, "🔖")

    with st.expander(
        f"{icon} {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')} "
        f"— {status.title()}",
        expanded=False
    ):
        col1, col2 = st.columns([2, 1])

        with col1:
            location = "🌐 Remote" if job.get("is_remote") else f"📍 {job.get('location', '—')}"
            st.markdown(f"**{location}**")
            st.markdown(f"📅 Saved: {job.get('saved_at', '—')[:10]}")

            if job.get("applied_at"):
                st.markdown(f"📨 Applied: {job['applied_at'][:10]}")

            if job.get("salary_min"):
                st.markdown(f"💰 {job['salary_min']:,.0f}+")

            if job.get("apply_link"):
                st.markdown(f"[🔗 Apply Now]({job['apply_link']})")

            if job.get("notes"):
                st.markdown(f"📝 **Notes:** {job['notes']}")

        with col2:
            st.markdown("**Update Status:**")
            new_status = st.selectbox(
                "Status",
                ["saved", "applied", "interview", "offered", "rejected"],
                index=["saved", "applied", "interview", "offered", "rejected"].index(status),
                key=f"status_{job['_id']}"
            )
            new_notes = st.text_input(
                "Notes",
                value=job.get("notes", ""),
                key=f"notes_{job['_id']}"
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💾 Update", key=f"update_{job['_id']}"):
                    if update_job_status(job["_id"], new_status, new_notes):
                        st.success("Updated!")
                        st.rerun()
            with col_b:
                if st.button("🗑️ Delete", key=f"delete_{job['_id']}"):
                    if delete_saved_job(job["_id"]):
                        st.success("Deleted!")
                        st.rerun()

        # ── Auto-fill prep button ─────────────────────────────
        st.markdown("---")
        if st.button("🚀 Prep Application", key=f"prep_{job['_id']}",
                     use_container_width=True, type="primary"):
            st.session_state[f"show_autofill_{job['_id']}"] = True
            st.rerun()

        # Show autofill UI if button was clicked
        if st.session_state.get(f"show_autofill_{job['_id']}"):
            from app.components.autofill_ui import render_autofill_modal
            render_autofill_modal(job)


def _render_search_history():
    """Render past search history."""
    st.markdown("### 🕐 Recent Searches")

    try:
        history = get_search_history(limit=20)
    except Exception as e:
        st.error(f"Failed to load search history: {e}")
        return

    if not history:
        st.info("No search history yet. Start searching for internships in the Chat tab.")
        return

    for search in history:
        query = search.get("query", "Unknown")
        location = search.get("location", "")
        count = search.get("job_count", 0)
        date = search.get("searched_at", "")[:10]

        with st.expander(
            f"🔍 {query}" + (f" in {location}" if location else "") +
            f" — {count} results ({date})"
        ):
            saved_jobs = search.get("jobs", [])
            if saved_jobs:
                for job in saved_jobs[:5]:
                    st.markdown(
                        f"- **{job['title']}** at {job['company']} "
                        f"({'Remote' if job.get('is_remote') else job.get('location', '—')})"
                    )
                if len(saved_jobs) > 5:
                    st.markdown(f"*...and {len(saved_jobs) - 5} more*")