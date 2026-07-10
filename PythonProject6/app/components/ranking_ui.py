# app/components/ranking_ui.py
import streamlit as st


DIMENSION_LABELS = {
    "company_reputation":    ("🏢", "Company Reputation"),
    "learning_opportunity":  ("📚", "Learning Opportunity"),
    "career_growth":         ("📈", "Career Growth"),
    "stipend_value":         ("💰", "Stipend Value"),
    "remote_flexibility":    ("🌐", "Remote Flexibility"),
    "application_difficulty":("🎯", "Ease of Apply"),
    "beginner_friendliness": ("🌱", "Beginner Friendly"),
}

SCORE_COLORS = {
    range(0, 4):  "#e74c3c",   # red    — poor
    range(4, 6):  "#f39c12",   # orange — average
    range(6, 8):  "#3498db",   # blue   — good
    range(8, 11): "#2ecc71",   # green  — excellent
}


def get_score_color(score: int) -> str:
    for r, color in SCORE_COLORS.items():
        if score in r:
            return color
    return "#888"


def render_ranking_table(ranked_jobs: list[dict], top_n: int = None):
    """Render the full ranking UI with scores and verdicts."""
    if not ranked_jobs:
        st.warning("No ranked results to display.")
        return

    jobs_to_show = ranked_jobs[:top_n] if top_n else ranked_jobs

    st.markdown("---")
    st.markdown(f"### 🏆 Ranked Internships ({len(jobs_to_show)} shown)")

    # ── Summary table ────────────────────────────────────────
    st.markdown("#### Quick Comparison")

    table_rows = []
    for job in jobs_to_show:
        scores = job.get("scores", {})
        total = job.get("total_score", sum(scores.values()))
        max_possible = len(DIMENSION_LABELS) * 10

        table_rows.append({
            "Rank": f"#{job['rank']}",
            "Role": job.get("title", "Unknown"),
            "Company": job.get("company", "Unknown"),
            "Location": "🌐 Remote" if job.get("is_remote") else job.get("location", "—"),
            "Score": f"{total}/{max_possible}",
            "Apply": f"[Link]({job.get('apply_link', '#')})" if job.get("apply_link") else "—",
        })

    # Display as markdown table
    headers = list(table_rows[0].keys())
    header_row = " | ".join(headers)
    separator = " | ".join(["---"] * len(headers))
    rows = "\n".join(
        " | ".join(str(row[h]) for h in headers)
        for row in table_rows
    )
    st.markdown(f"{header_row}\n{separator}\n{rows}")

    st.markdown("---")

    # ── Detailed cards ───────────────────────────────────────
    st.markdown("#### Detailed Breakdown")

    for job in jobs_to_show:
        _render_job_card(job)


def _render_job_card(job: dict):
    """Render a single job card with scores and verdict."""
    scores = job.get("scores", {})
    total = job.get("total_score", sum(scores.values()))
    max_possible = len(DIMENSION_LABELS) * 10
    rank = job.get("rank", "?")

    # Medal emoji for top 3
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

    with st.expander(
        f"{medal} {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}  "
        f"— Score: {total}/{max_possible}",
        expanded=(rank <= 3)  # auto-expand top 3
    ):
        col1, col2 = st.columns([3, 2])

        with col1:
            # Job details
            location = "🌐 Remote" if job.get("is_remote") else f"📍 {job.get('location', 'Unknown')}"
            st.markdown(f"**{location}**")
            st.markdown(f"📅 Posted: {job.get('posted_date', 'Recently')}")

            if job.get("salary_min"):
                st.markdown(
                    f"💰 {job.get('salary_currency','USD')} "
                    f"{job['salary_min']:,.0f}"
                    + (f"–{job['salary_max']:,.0f}" if job.get('salary_max') else "+")
                    + f" /{job.get('salary_period','yr').lower()}"
                )

            if job.get("apply_link"):
                st.markdown(f"[🔗 Apply Now]({job['apply_link']})")

            # Verdict
            st.markdown("**Why this rank:**")
            st.info(job.get("verdict", "No explanation provided."))

        with col2:
            # Score bars
            st.markdown("**Dimension Scores:**")
            for key, (emoji, label) in DIMENSION_LABELS.items():
                score = scores.get(key, 0)
                color = get_score_color(score)
                bar_pct = int((score / 10) * 100)

                st.markdown(
                    f"{emoji} {label}: **{score}/10**",
                )
                st.markdown(
                    f"""<div style='background:#eee;border-radius:4px;height:8px;margin-bottom:6px;'>
                        <div style='width:{bar_pct}%;background:{color};height:8px;border-radius:4px;'></div>
                    </div>""",
                    unsafe_allow_html=True
                )