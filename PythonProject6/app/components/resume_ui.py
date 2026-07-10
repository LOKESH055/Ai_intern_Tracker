# app/components/resume_ui.py
import streamlit as st
from app.services.cos_client import upload_resume, list_resumes, download_resume
from app.services.resume_analyzer import (
    extract_text_from_pdf,
    analyze_resume,
    build_job_context_from_listings
)


def render_resume_page():
    """Full resume analysis page."""
    st.markdown("""
        <h2 style='color: #4A90D9;'>📄 Resume Analysis</h2>
        <p style='color: #888;'>Upload your resume and get an ATS score, skill gap analysis,
        and improvement suggestions powered by IBM watsonx.ai</p>
        <hr>
    """, unsafe_allow_html=True)

    # ── Upload section ───────────────────────────────────────
    st.markdown("### 📤 Upload Resume")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload your resume (PDF only)",
            type=["pdf"],
            help="Your resume will be stored securely in IBM Cloud Object Storage"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_existing = st.checkbox("Use previously uploaded resume")

        existing_key = None
        if use_existing:
            try:
                resumes = list_resumes()
                if resumes:
                    existing_key = st.selectbox(
                        "Select resume",
                        resumes,
                        format_func=lambda x: x.split("/")[-1]
                    )
                else:
                    st.info("No previously uploaded resumes found.")
            except Exception as e:
                st.error(f"Could not load resumes: {e}")

    # ── Job context ──────────────────────────────────────────
    st.markdown("### 🎯 Target Role (optional)")

    last_jobs = st.session_state.get("last_jobs", [])
    if last_jobs:
        st.success(
            f"✅ {len(last_jobs)} internship listings loaded from your search. "
            "Analysis will be tailored to these roles."
        )
        use_job_context = st.checkbox("Analyze against my searched internships", value=True)
    else:
        use_job_context = False
        st.info(
            "💡 Tip: Search for internships in the Chat tab first, "
            "then come back here for a role-specific analysis."
        )

    manual_role = st.text_input(
        "Or describe the target role manually",
        placeholder="e.g. Data Science internship requiring Python, SQL, and ML skills"
    )

    # ── Analyze button ───────────────────────────────────────
    st.markdown("---")
    analyze_btn = st.button(
        "🔍 Analyze Resume",
        type="primary",
        use_container_width=True,
        disabled=(uploaded_file is None and existing_key is None)
    )

    if analyze_btn:
        _run_analysis(
            uploaded_file=uploaded_file,
            existing_key=existing_key,
            use_job_context=use_job_context,
            manual_role=manual_role,
            last_jobs=last_jobs
        )

    # ── Show previous analysis if available ──────────────────
    if "resume_analysis" in st.session_state and not analyze_btn:
        st.markdown("---")
        st.markdown("### 📊 Previous Analysis Results")
        _render_analysis_results(st.session_state["resume_analysis"])


def _run_analysis(
    uploaded_file,
    existing_key,
    use_job_context,
    manual_role,
    last_jobs
):
    """Handle the full analysis pipeline."""

    # Step 1: Get PDF bytes
    pdf_bytes = None

    if uploaded_file:
        with st.spinner("📤 Uploading to IBM Cloud Object Storage..."):
            try:
                pdf_bytes = uploaded_file.read()
                object_key = upload_resume(pdf_bytes, uploaded_file.name)
                st.success(f"✅ Uploaded: `{object_key}`")
            except Exception as e:
                st.error(f"Upload failed: {e}")
                return

    elif existing_key:
        with st.spinner("📥 Downloading from IBM Cloud Object Storage..."):
            try:
                pdf_bytes = download_resume(existing_key)
                st.success(f"✅ Loaded: `{existing_key}`")
            except Exception as e:
                st.error(f"Download failed: {e}")
                return

    if not pdf_bytes:
        st.error("No resume file available.")
        return

    # Step 2: Extract text
    with st.spinner("📖 Extracting text from PDF..."):
        try:
            resume_text = extract_text_from_pdf(pdf_bytes)
            word_count = len(resume_text.split())
            st.info(f"📝 Extracted {word_count} words from your resume")
        except Exception as e:
            st.error(f"Text extraction failed: {e}")
            return

    # Step 3: Build job context
    job_context = ""
    if use_job_context and last_jobs:
        job_context = build_job_context_from_listings(last_jobs)
    elif manual_role:
        job_context = manual_role

    # Step 4: Analyze with watsonx
    with st.spinner("🤖 Analyzing with IBM watsonx.ai — this takes 15-20 seconds..."):
        try:
            analysis = analyze_resume(resume_text, job_context)
            st.session_state["resume_analysis"] = analysis
            st.session_state["resume_text"] = resume_text
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return

    # Step 5: Display results
    st.markdown("---")
    _render_analysis_results(analysis)


def _render_analysis_results(analysis: dict):
    """Render the full analysis results UI."""

    ats_score = analysis.get("ats_score", 0)
    match_pct = analysis.get("match_percentage", 0)

    # ── Score cards ──────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        color = _score_color(ats_score)
        st.markdown(f"""
            <div style='background:{color}22;border:2px solid {color};
                        border-radius:12px;padding:20px;text-align:center;'>
                <h1 style='color:{color};margin:0;'>{ats_score}</h1>
                <p style='margin:0;font-weight:bold;'>ATS Score</p>
                <p style='margin:0;font-size:12px;color:#888;'>out of 100</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        color2 = _score_color(match_pct)
        st.markdown(f"""
            <div style='background:{color2}22;border:2px solid {color2};
                        border-radius:12px;padding:20px;text-align:center;'>
                <h1 style='color:{color2};margin:0;'>{match_pct}%</h1>
                <p style='margin:0;font-weight:bold;'>Role Match</p>
                <p style='margin:0;font-size:12px;color:#888;'>vs target role</p>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        level = analysis.get("experience_level", "beginner").title()
        st.markdown(f"""
            <div style='background:#4A90D922;border:2px solid #4A90D9;
                        border-radius:12px;padding:20px;text-align:center;'>
                <h1 style='color:#4A90D9;margin:0;'>🎓</h1>
                <p style='margin:0;font-weight:bold;'>{level}</p>
                <p style='margin:0;font-size:12px;color:#888;'>experience level</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Summary ──────────────────────────────────────────────
    st.markdown("### 💬 Overall Assessment")
    st.info(analysis.get("summary", "No summary available."))

    # ── Two column layout for gaps and strengths ─────────────
    col_left, col_right = st.columns(2)

    with col_left:
        # Strengths
        strengths = analysis.get("strengths", [])
        if strengths:
            st.markdown("### ✅ Strengths")
            for s in strengths:
                st.markdown(f"- {s}")

        # Missing skills
        missing_skills = analysis.get("missing_skills", [])
        if missing_skills:
            st.markdown("### ❌ Missing Skills")
            for skill in missing_skills:
                st.markdown(
                    f"<span style='background:#e74c3c22;padding:2px 8px;"
                    f"border-radius:4px;color:#e74c3c;'>⚠ {skill}</span>",
                    unsafe_allow_html=True
                )
                st.markdown("")

    with col_right:
        # Missing keywords
        keywords = analysis.get("missing_keywords", [])
        if keywords:
            st.markdown("### 🔑 Missing ATS Keywords")
            keyword_html = " ".join(
                f"<span style='background:#f39c1222;padding:3px 10px;"
                f"border-radius:12px;margin:2px;display:inline-block;"
                f"color:#f39c12;border:1px solid #f39c12;'>{kw}</span>"
                for kw in keywords
            )
            st.markdown(keyword_html, unsafe_allow_html=True)

        # Best matching roles
        top_roles = analysis.get("top_matching_roles", [])
        if top_roles:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🎯 Best Suited Roles")
            for role in top_roles:
                st.markdown(f"✦ {role}")

    st.markdown("---")

    # ── Suggestions ──────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(
        ["💡 Improvement Tips", "🛠 Project Ideas", "📐 Formatting"]
    )

    with tab1:
        suggestions = analysis.get("improvement_suggestions", [])
        if suggestions:
            for i, tip in enumerate(suggestions, 1):
                st.markdown(f"**{i}.** {tip}")
        else:
            st.info("No improvement suggestions generated.")

    with tab2:
        projects = analysis.get("project_suggestions", [])
        if projects:
            for i, proj in enumerate(projects, 1):
                st.markdown(f"**{i}.** {proj}")
        else:
            st.info("No project suggestions generated.")

    with tab3:
        formatting = analysis.get("formatting_suggestions", [])
        if formatting:
            for i, fmt in enumerate(formatting, 1):
                st.markdown(f"**{i}.** {fmt}")
        else:
            st.info("No formatting suggestions generated.")

    # ── Export ───────────────────────────────────────────────
    st.markdown("---")
    import json
    st.download_button(
        label="⬇️ Download Full Analysis (JSON)",
        data=json.dumps(analysis, indent=2),
        file_name="resume_analysis.json",
        mime="application/json"
    )


def _score_color(score: int) -> str:
    if score >= 75:
        return "#2ecc71"   # green
    elif score >= 50:
        return "#f39c12"   # orange
    else:
        return "#e74c3c"   # red