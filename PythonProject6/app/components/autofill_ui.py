# app/components/autofill_ui.py
import streamlit as st
from app.services.autofill_engine import generate_cover_letter, generate_autofill_data
from app.services.cloudant_client import get_user_profile, save_job


def render_autofill_modal(job: dict):
    """
    Render auto-fill prep UI for a specific job.
    Called from tracked jobs page or chat.
    """
    st.markdown(f"""
        <div style='background:#4A90D922;border:1px solid #4A90D9;
                    border-radius:8px;padding:16px;margin-bottom:16px;'>
            <h4 style='margin:0;color:#4A90D9;'>🚀 Application Prep</h4>
            <p style='margin:4px 0 0;color:#666;'>
                {job.get('title')} at {job.get('company')}
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Load profile
    profile = st.session_state.get("user_profile") or get_user_profile()

    if not profile or not profile.get("name"):
        st.warning(
            "⚠️ Your profile is incomplete. "
            "Go to **👤 Profile** tab and fill in your details first "
            "for personalized cover letters and auto-fill."
        )
        if st.button("Go to Profile →"):
            st.session_state["nav_page"] = "👤 Profile"
            st.rerun()
        return

    tab1, tab2 = st.tabs(["📝 Cover Letter", "📋 Auto-fill Form Data"])

    # ── Cover Letter ─────────────────────────────────────────
    with tab1:
        st.markdown(f"**Generating for:** {profile.get('name')} → {job.get('company')}")

        if st.button("✨ Generate Cover Letter", type="primary", key=f"cl_{job.get('id','')}"):
            with st.spinner("🤖 Writing personalized cover letter..."):
                try:
                    cover_letter = generate_cover_letter(job, profile)
                    st.session_state[f"cover_letter_{job.get('id','')}"] = cover_letter
                except Exception as e:
                    st.error(f"Failed: {e}")

        # Show generated cover letter
        cover_letter = st.session_state.get(f"cover_letter_{job.get('id','')}")
        if cover_letter:
            st.markdown("---")
            edited = st.text_area(
                "Your Cover Letter (edit if needed)",
                value=cover_letter,
                height=300,
                key=f"cl_edit_{job.get('id','')}"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ Download Cover Letter",
                    data=edited,
                    file_name=f"cover_letter_{job.get('company','').replace(' ','_')}.txt",
                    mime="text/plain",
                    key=f"dl_cl_{job.get('id','')}"
                )
            with col2:
                if st.button("📋 Copy to Clipboard", key=f"copy_{job.get('id','')}"):
                    st.code(edited)
                    st.info("Select all text above and copy (Ctrl+A, Ctrl+C)")

    # ── Auto-fill Form Data ──────────────────────────────────
    with tab2:
        st.markdown("Pre-filled data ready to paste into application forms:")

        if st.button("⚡ Generate Form Data", type="primary", key=f"af_{job.get('id','')}"):
            with st.spinner("🤖 Preparing application form data..."):
                try:
                    autofill = generate_autofill_data(job, profile)
                    st.session_state[f"autofill_{job.get('id','')}"] = autofill
                except Exception as e:
                    st.error(f"Failed: {e}")

        autofill = st.session_state.get(f"autofill_{job.get('id','')}")
        if autofill:
            st.markdown("---")

            # Display as editable fields
            col1, col2 = st.columns(2)
            fields = list(autofill.items())
            mid = len(fields) // 2

            with col1:
                for key, value in fields[:mid]:
                    label = key.replace("_", " ").title()
                    autofill[key] = st.text_input(
                        label, value=str(value),
                        key=f"af_field_{job.get('id','')}_{key}"
                    )

            with col2:
                for key, value in fields[mid:]:
                    label = key.replace("_", " ").title()
                    if len(str(value)) > 60:
                        autofill[key] = st.text_area(
                            label, value=str(value),
                            key=f"af_area_{job.get('id','')}_{key}",
                            height=80
                        )
                    else:
                        autofill[key] = st.text_input(
                            label, value=str(value),
                            key=f"af_field2_{job.get('id','')}_{key}"
                        )

            st.markdown("---")
            import json
            st.download_button(
                "⬇️ Download Form Data (JSON)",
                data=json.dumps(autofill, indent=2),
                file_name=f"application_{job.get('company','').replace(' ','_')}.json",
                mime="application/json",
                key=f"dl_af_{job.get('id','')}"
            )

    # ── Final Apply Button ───────────────────────────────────
    st.markdown("---")
    st.markdown("### ✅ Ready to Apply?")
    col1, col2 = st.columns(2)

    with col1:
        if job.get("apply_link"):
            st.link_button(
                "🚀 Open Application Page",
                url=job["apply_link"],
                use_container_width=True
            )

    with col2:
        if st.button("📨 Mark as Applied", use_container_width=True,
                     key=f"applied_{job.get('id','')}"):
            try:
                from app.services.cloudant_client import save_job, update_job_status
                doc_id = f"job_{job.get('id', '')}"
                update_job_status(doc_id, "applied")
                st.success("✅ Marked as applied in Tracked Jobs!")
            except Exception as e:
                st.error(f"Could not update status: {e}")