# app/components/chat_ui.py
import streamlit as st
from app.services.watsonx_client import get_watsonx_client
from app.services.jsearch_client import search_internships, format_jobs_for_ai
from app.services.ranking_engine import rank_internships
from app.components.ranking_ui import render_ranking_table
from app.utils.intent_parser import parse_search_intent
from app.utils.config import Config
from app.components.monitor_ui import render_monitor_controls, render_notifications


RANK_TRIGGERS = [
    "rank", "ranking", "score", "compare", "best", "top 5", "top 10",
    "top 20", "which one", "recommend", "suggest", "sort", "order",
    "evaluate", "assess", "rate"
]


def initialize_chat_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "client_ready" not in st.session_state:
        st.session_state.client_ready = False
    if "watsonx_client" not in st.session_state:
        st.session_state.watsonx_client = None
    if "last_jobs" not in st.session_state:
        st.session_state.last_jobs = []
    if "last_ranked" not in st.session_state:
        st.session_state.last_ranked = []
    if "ranking_requested" not in st.session_state:
        st.session_state.ranking_requested = False
    if "last_search_query" not in st.session_state:
        st.session_state.last_search_query = ""
    if "last_search_location" not in st.session_state:
        st.session_state.last_search_location = ""


def load_client():
    if not st.session_state.client_ready:
        with st.spinner("🔌 Connecting to IBM watsonx.ai..."):
            try:
                st.session_state.watsonx_client = get_watsonx_client()
                st.session_state.client_ready = True
            except Exception as e:
                st.error(f"Failed to connect to watsonx: {e}")
                st.stop()


def render_chat():
    initialize_chat_state()
    load_client()

    # ── Header ──────────────────────────────────────────────
    st.markdown("""
        <h2 style='text-align: center; color: #4A90D9;'>
            🎯 Internship Discovery Assistant
        </h2>
        <p style='text-align: center; color: #888; font-size: 14px;'>
            Powered by IBM watsonx.ai · Real listings from LinkedIn & Indeed
        </p>
        <hr style='margin-bottom: 1.5rem;'>
    """, unsafe_allow_html=True)

    if not Config.RAPIDAPI_KEY:
        st.warning("⚠️ RapidAPI key not set. Add RAPIDAPI_KEY to your .env file.")

    # ── Suggested prompts ────────────────────────────────────
    if not st.session_state.messages:
        st.markdown("#### 👋 Try asking:")
        cols = st.columns(2)
        suggestions = [
            "Find Data Science internships",
            "Find Software Engineering internships in India",
            "Find remote Machine Learning internships",
            "Find Marketing internships",
        ]
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    _handle_user_input(suggestion)
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat history ─────────────────────────────────────────
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ── Ranking UI (shown below chat when active) ────────────
    if st.session_state.last_ranked:
        render_ranking_table(st.session_state.last_ranked)

    # ── Monitoring controls ──────────────────────────────────
    render_notifications()
    if st.session_state.get("last_search_query"):
        render_monitor_controls(
            query=st.session_state.get("last_search_query", ""),
            location=st.session_state.get("last_search_location", "")
        )

    # ── Chat input ───────────────────────────────────────────
    if prompt := st.chat_input("Ask about internships, resume tips, ranking, or career advice..."):
        _handle_user_input(prompt)
        st.rerun()


def _is_ranking_request(message: str) -> bool:
    msg = message.lower()
    return any(trigger in msg for trigger in RANK_TRIGGERS)


def _extract_top_n(message: str) -> int:
    msg = message.lower()
    if "top 5" in msg or "5 best" in msg:
        return 5
    elif "top 20" in msg or "20 best" in msg:
        return 20
    return 10  # default


def _handle_user_input(user_input: str):
    """Process user message — search, rank, or chat."""
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    intent = parse_search_intent(user_input)
    is_ranking = _is_ranking_request(user_input)
    job_context = ""
    status_placeholder = st.empty()

    # ── Step 1: Fetch jobs if search intent detected ─────────
    if intent["is_search"] and Config.RAPIDAPI_KEY:
        with st.spinner(
            f"🔍 Searching real listings for **{intent['query']}**"
            + (f" in **{intent['location']}**" if intent["location"] else "") + "..."
        ):
            try:
                jobs = search_internships(
                    query=intent["query"],
                    location=intent["location"],
                    num_pages=2
                )
                jobs = jobs[:intent["num_results"]]
                st.session_state.last_jobs = jobs
                st.session_state.last_ranked = []

                if jobs:
                    job_context = format_jobs_for_ai(jobs)
                    status_placeholder.success(f"✅ Found {len(jobs)} real internship listings!")

                    # Auto-save search to Cloudant
                    try:
                        from app.services.cloudant_client import save_job_search
                        save_job_search(intent["query"], intent["location"], jobs)
                    except Exception:
                        pass

                    # Store last search query for monitoring
                    st.session_state["last_search_query"] = intent["query"]
                    st.session_state["last_search_location"] = intent["location"]

                else:
                    job_context = "No internships found. Inform the user and suggest alternatives."
                    status_placeholder.warning("No listings found. Try a different search.")

            except Exception as e:
                job_context = f"Job search failed: {str(e)}"
                status_placeholder.error(f"⚠️ {str(e)}")

    # ── Step 2: Rank if ranking intent detected ──────────────
    if is_ranking and st.session_state.last_jobs:
        top_n = _extract_top_n(user_input)
        jobs_to_rank = st.session_state.last_jobs

        with st.spinner(f"🧠 Ranking {len(jobs_to_rank)} internships across 7 dimensions..."):
            try:
                ranked = rank_internships(
                    jobs=jobs_to_rank,
                    top_n=top_n
                )
                st.session_state.last_ranked = ranked
                rank_context = (
                    f"I have ranked {len(ranked)} internships. "
                    f"Top pick: {ranked[0]['company']} — {ranked[0]['title']} "
                    f"(score: {ranked[0]['total_score']}/70). "
                    f"Tell the user the ranking is displayed below and briefly summarize the top 3."
                )
                job_context = rank_context
                status_placeholder.success("✅ Ranking complete!")
            except Exception as e:
                status_placeholder.error(f"⚠️ Ranking failed: {str(e)}")

    elif is_ranking and not st.session_state.last_jobs:
        job_context = (
            "The user wants to rank internships but no jobs have been fetched yet. "
            "Ask them to search for internships first."
        )

    # ── Step 3: Get AI response ──────────────────────────────
    augmented = (
        f"{user_input}\n\n[CONTEXT: {job_context}]"
        if job_context else user_input
    )

    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking..."):
            history = st.session_state.messages[:-1]
            response = st.session_state.watsonx_client.chat(
                history + [{"role": "user", "content": augmented}]
            )
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
    status_placeholder.empty()