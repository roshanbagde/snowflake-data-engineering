"""
ThinkSpark — Critical Thinking Trainer for Kids
Streamlit app: Question Bank · AI Generator · Session Builder · Classroom View
"""

from __future__ import annotations
import json
from datetime import date, datetime

import streamlit as st
from dotenv import load_dotenv

from src.database import (
    init_db, connect, get_topics, get_age_groups,
    topic_id_map, age_group_id_map,
    get_questions, insert_question, update_question, deactivate_question, restore_question,
    toggle_favourite, count_questions, get_stats, QUESTION_TYPES, LEVELS, CURRICULUM,
    create_session, get_sessions, get_session, update_session, delete_session,
    add_question_to_session, remove_question_from_session,
    get_session_questions, mark_question_used, reorder_session_questions,
)
from src.llm_provider import PROVIDERS, default_api_key, get_ollama_models
from src.ai_generator import generate_questions

load_dotenv()

# ── Init ───────────────────────────────────────────────────────────────────────

init_db()

st.set_page_config(
    page_title="ThinkSpark",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background: #0a0e1a; }
[data-testid="stSidebar"]          { background: #0f1320; border-right: 1px solid #1e2540; }
.block-container { padding-top: 1.2rem !important; }

/* Fix all heading colors — Streamlit's dark theme renders them near-invisible */
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4 {
    color: #e8eeff !important;
}
/* Sidebar headings slightly softer */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #c8d4f0 !important;
}
/* Body text and labels */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #b8c8e8 !important;
}
/* Expander headers */
[data-testid="stExpander"] summary span {
    color: #c8d8f8 !important;
}
/* Metric labels */
[data-testid="stMetricLabel"] { color: #8899bb !important; }
[data-testid="stMetricValue"] { color: #e8eeff !important; }

.q-card {
    background: #121828;
    border: 1px solid #1e2a44;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.q-card-selected {
    background: #0e2040;
    border: 1px solid #3b6de8;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.badge {
    display: inline-block;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: .78rem;
    margin-right: 4px;
}
.badge-simple   { background:#0d2b1a; color:#00d26a; }
.badge-medium   { background:#2a1f00; color:#ffb300; }
.badge-hard     { background:#2a0d0d; color:#ff5252; }
.badge-type     { background:#1a1e40; color:#8899ff; }
.badge-source   { background:#1a2030; color:#6688aa; }

/* Classroom view */
.classroom-question {
    background: #0d1526;
    border: 2px solid #2a4080;
    border-radius: 18px;
    padding: 40px 50px;
    margin: 20px 0;
    font-size: 1.7rem;
    line-height: 1.6;
    color: #e8eeff;
}
.classroom-context {
    color: #7a90b0;
    font-size: 1.1rem;
    margin-bottom: 18px;
    font-style: italic;
}
.classroom-hint {
    background: #1a2c1a;
    border-left: 4px solid #00d26a;
    border-radius: 8px;
    padding: 14px 20px;
    color: #90e8a0;
    font-size: 1.1rem;
    margin-top: 18px;
}
.classroom-discussion {
    background: #1a1f3a;
    border-left: 4px solid #3b6de8;
    border-radius: 8px;
    padding: 14px 20px;
    color: #aabeff;
    font-size: 1rem;
    margin-top: 12px;
}
[data-testid="metric-container"] {
    background: #121828;
    border-radius: 10px;
    padding: 10px;
    border: 1px solid #1e2540;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────

_defaults = {
    "provider":          "Ollama (Local)",
    "api_key":           "",
    "gen_results":       [],      # AI generator staging area
    "gen_approved":      [],      # booleans per generated question
    "gen_saved":         [],      # booleans — True if already saved to DB
    "gen_meta":          {},      # topic/ag/level/type used during generation
    "classroom_mode":    False,
    "cls_session_id":    None,
    "cls_q_index":       0,
    "cls_show_hint":     False,
    "cls_show_disc":     False,
    "cls_questions":     [],
    "active_tab":        0,
    "f_favourites_only": True,    # Tab 1 defaults to showing favourites only
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💡 ThinkSpark")
    st.markdown("*Critical Thinking Trainer*")
    st.markdown("---")

    if st.session_state.classroom_mode:
        if st.button("🚪 Exit Classroom View", use_container_width=True):
            st.session_state.classroom_mode = False
            st.rerun()
    else:
        st.markdown("### 🤖 AI Provider")
        provider_names    = list(PROVIDERS.keys())
        selected_provider = st.selectbox(
            "Provider", provider_names,
            index=provider_names.index(st.session_state.provider),
            key="provider_select", label_visibility="collapsed",
        )
        if selected_provider != st.session_state.provider:
            st.session_state.provider = selected_provider
            st.session_state.api_key  = default_api_key(selected_provider)

        provider_cfg = PROVIDERS[selected_provider]
        is_ollama    = selected_provider == "Ollama (Local)"

        model_list     = get_ollama_models() if is_ollama else provider_cfg["models"]
        selected_model = st.selectbox(
            "Model", model_list,
            key=f"model_{selected_provider}", label_visibility="collapsed",
        )

        if not is_ollama:
            api_key_val = st.text_input(
                "API Key",
                value=default_api_key(selected_provider) or st.session_state.api_key,
                type="password",
                placeholder=provider_cfg["key_hint"],
                label_visibility="collapsed",
            )
            st.session_state.api_key = api_key_val
            if not api_key_val:
                st.warning(f"Enter a {selected_provider} API key.")
        else:
            st.session_state.api_key = ""
            st.success("No API key needed for Ollama.")

        st.markdown("---")

        # Sidebar stats
        conn  = connect()
        stats = get_stats(conn)
        conn.close()

        st.markdown("### 📊 Question Bank")
        sb_c1, sb_c2 = st.columns(2)
        sb_c1.metric("Total Questions", stats["total_questions"])
        sb_c2.metric("⭐ Favourites", stats["total_favourites"])
        st.metric("Sessions Created", stats["total_sessions"])

        if stats["by_level"]:
            lvl = stats["by_level"]
            cols = st.columns(3)
            cols[0].metric("Simple",  lvl.get("simple", 0))
            cols[1].metric("Medium",  lvl.get("medium", 0))
            cols[2].metric("Hard",    lvl.get("hard",   0))

        st.markdown("---")
        st.markdown("### 📅 8-Week Curriculum")
        today_week = st.number_input("Current week", min_value=1, max_value=8, value=1, key="curr_week")
        week_info  = CURRICULUM.get(today_week, {})
        if week_info:
            st.info(f"**Week {today_week}: {week_info['theme']}**\n\n"
                    + "  \n".join(week_info["topics"]))

        st.markdown("---")
        st.caption("ThinkSpark v1.0 · Port 8505")

# ══════════════════════════════════════════════════════════════════════════════
# CLASSROOM VIEW (full-screen, replaces tabs)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.classroom_mode:
    cls_qs = st.session_state.cls_questions
    if not cls_qs:
        st.error("No questions loaded for classroom view.")
        st.session_state.classroom_mode = False
        st.rerun()

    idx   = st.session_state.cls_q_index
    total = len(cls_qs)
    q     = cls_qs[idx]

    st.markdown(f"## 💡 ThinkSpark — Classroom")
    st.markdown(f"Question **{idx + 1}** of **{total}**  ·  "
                f"`{q.get('age_group_label','')}`  ·  "
                f"`{q.get('level','')}` · `{q.get('question_type','')}`")

    progress_pct = (idx + 1) / total
    st.progress(progress_pct)

    topic_name = q.get("topic_name", "")
    if topic_name:
        st.markdown(f"**Topic:** {topic_name}")

    # Question display
    ctx_html = ""
    if q.get("context"):
        ctx_html = f'<div class="classroom-context">{q["context"]}</div>'

    st.markdown(
        f'<div class="classroom-question">'
        f'{ctx_html}'
        f'{q["question_text"]}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Reveal controls
    ctrl_cols = st.columns([1, 1, 1, 2])

    with ctrl_cols[0]:
        if st.button("⬅️ Previous", use_container_width=True, disabled=idx == 0):
            st.session_state.cls_q_index  -= 1
            st.session_state.cls_show_hint = False
            st.session_state.cls_show_disc = False
            st.rerun()

    with ctrl_cols[1]:
        if st.button("➡️ Next", use_container_width=True, disabled=idx == total - 1):
            st.session_state.cls_q_index  += 1
            st.session_state.cls_show_hint = False
            st.session_state.cls_show_disc = False
            st.rerun()

    with ctrl_cols[2]:
        hint_label = "🔒 Hide Hint" if st.session_state.cls_show_hint else "💡 Show Hint"
        if st.button(hint_label, use_container_width=True, disabled=not q.get("hint")):
            st.session_state.cls_show_hint = not st.session_state.cls_show_hint
            st.rerun()

    with ctrl_cols[3]:
        disc_label = "📋 Hide Discussion" if st.session_state.cls_show_disc else "📋 Discussion Points"
        if st.button(disc_label, use_container_width=True, disabled=not q.get("discussion_points")):
            st.session_state.cls_show_disc = not st.session_state.cls_show_disc
            st.rerun()

    # Hint reveal
    if st.session_state.cls_show_hint and q.get("hint"):
        st.markdown(
            f'<div class="classroom-hint">💡 <strong>Hint:</strong> {q["hint"]}</div>',
            unsafe_allow_html=True,
        )

    # Discussion points reveal (facilitator view)
    if st.session_state.cls_show_disc and q.get("discussion_points"):
        pts_html = "".join(f"<li>{p}</li>" for p in q["discussion_points"])
        st.markdown(
            f'<div class="classroom-discussion">'
            f'<strong>📋 Discussion Points (facilitator):</strong><ul>{pts_html}</ul>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Follow-up questions
    if q.get("follow_up_questions"):
        with st.expander("🔗 Follow-up questions"):
            for fq in q["follow_up_questions"]:
                st.markdown(f"- {fq}")

    # Sample answer (hidden by default)
    if q.get("sample_answer"):
        with st.expander("📝 Sample answer (facilitator only)"):
            st.info(q["sample_answer"])

    # Mark as done
    sq_id = q.get("id")
    if sq_id and not q.get("was_used"):
        fac_note = st.text_input("Facilitator note (optional):", key=f"note_{idx}")
        if st.button("✅ Mark as done for this session", key=f"done_{idx}"):
            conn = connect()
            mark_question_used(conn, sq_id, fac_note)
            conn.close()
            st.session_state.cls_questions[idx]["was_used"] = 1
            st.success("Marked as done!")
    elif q.get("was_used"):
        st.success("✅ Already used in this session")

    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("# 💡 ThinkSpark")
st.markdown("*Critical thinking & character development trainer for kids aged 5–18*")

tab1, tab2, tab3, tab4 = st.tabs([
    "📚 Question Bank",
    "🤖 AI Generator",
    "📅 Sessions",
    "🎯 Classroom",
])

# ── Shared data ────────────────────────────────────────────────────────────────

conn      = connect()
topics    = get_topics(conn)
age_grps  = get_age_groups(conn)
tid_map   = topic_id_map(conn)
agid_map  = age_group_id_map(conn)
conn.close()

topic_names   = [t["name"]  for t in topics]
ag_labels     = [a["label"] for a in age_grps]
ag_by_label   = {a["label"]: a for a in age_grps}


def _save_generated_question(conn, q: dict, meta: dict) -> None:
    """Insert one AI-generated question into the DB using the generation metadata."""
    insert_question(
        conn,
        {
            "topic_id":            tid_map[meta["topic"]],
            "age_group_id":        agid_map[meta["ag"]],
            "level":               meta["level"],
            "question_type":       meta["q_type"],
            "question_text":       q["question_text"],
            "context":             q.get("context", ""),
            "hint":                q.get("hint", ""),
            "sample_answer":       q.get("sample_answer", ""),
            "discussion_points":   q.get("discussion_points", []),
            "follow_up_questions": q.get("follow_up_questions", []),
            "tags":                q.get("tags", ""),
        },
        source      = "ai_generated",
        ai_provider = meta.get("provider"),
        ai_model    = meta.get("model"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Question Bank
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("### 📚 Question Bank")

    # ── Favourites toggle (prominent, above other filters) ─────────────────────
    fav_row_l, fav_row_r = st.columns([3, 5])
    with fav_row_l:
        f_favs_only = st.toggle(
            "⭐ Favourites only",
            value=st.session_state.f_favourites_only,
            key="f_favourites_toggle",
            help="Show only questions you have marked as favourites",
        )
        st.session_state.f_favourites_only = f_favs_only

    # ── Other filters (hidden when favourites-only is on, to keep UI clean) ────
    if not f_favs_only:
        fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 1, 1, 2])
        with fc1:
            f_topic = st.selectbox("Topic", ["All topics"] + topic_names, key="f_topic")
        with fc2:
            f_ag    = st.selectbox("Age group", ["All ages"] + ag_labels, key="f_ag")
        with fc3:
            f_level = st.selectbox("Level", ["All"] + LEVELS, key="f_level")
        with fc4:
            f_type  = st.selectbox("Type", ["All"] + QUESTION_TYPES, key="f_type")
        with fc5:
            f_search = st.text_input("🔍 Search", placeholder="keyword or tag", key="f_search")
        show_inactive = st.checkbox("Show inactive questions", key="show_inactive")
    else:
        # Set defaults so variable names are defined below
        f_topic = "All topics"; f_ag = "All ages"; f_level = "All"
        f_type = "All"; f_search = ""; show_inactive = False

    conn = connect()
    questions = get_questions(
        conn,
        topic_id        = tid_map.get(f_topic) if f_topic != "All topics" else None,
        age_group_id    = agid_map.get(f_ag) if f_ag != "All ages" else None,
        level           = f_level  if f_level  != "All" else None,
        q_type          = f_type   if f_type   != "All" else None,
        search          = f_search or None,
        active_only     = not show_inactive,
        favourites_only = f_favs_only,
    )
    conn.close()

    if f_favs_only and not questions:
        st.info(
            "⭐ No favourites yet. Open any question below and click **⭐ Favourite** to mark it — "
            "it will appear here on your next visit."
        )
        st.toggle("⭐ Favourites only", value=False, key="f_favourites_toggle_empty",
                  help="Toggle off to browse all questions")
        if st.session_state.get("f_favourites_toggle_empty") == False:
            st.session_state.f_favourites_only = False
            st.rerun()
        st.stop()

    st.caption(f"Showing **{len(questions)}** {'favourite' if f_favs_only else ''} question(s)")

    # ── Add question manually ──────────────────────────────────────────────────
    with st.expander("➕ Add Question Manually"):
        with st.form("add_q_form"):
            a1, a2 = st.columns(2)
            with a1:
                a_topic = st.selectbox("Topic *", topic_names, key="a_topic")
                a_ag    = st.selectbox("Age Group *", ag_labels,   key="a_ag")
            with a2:
                a_level = st.selectbox("Level *", LEVELS, key="a_level")
                a_type  = st.selectbox("Question Type *", QUESTION_TYPES, key="a_type")

            a_qtext  = st.text_area("Question Text *", height=80, key="a_qtext")
            a_ctx    = st.text_area("Context (optional)", height=60, key="a_ctx",
                                    placeholder="Short scene-setting — leave blank if not needed")
            a_hint   = st.text_area("Hint (for students)", height=60, key="a_hint",
                                    placeholder="A nudge to help them think — not the answer")
            a_sample = st.text_area("Sample Answer (facilitator only)", height=80, key="a_sample")
            a_dp     = st.text_area("Discussion Points (one per line)", height=80, key="a_dp",
                                    placeholder="Follow-up prompts to deepen the conversation")
            a_fu     = st.text_area("Follow-up Questions (one per line)", height=60, key="a_fu")
            a_tags   = st.text_input("Tags (comma-separated)", key="a_tags")

            submitted = st.form_submit_button("💾 Save Question", type="primary")
            if submitted:
                if not a_qtext.strip():
                    st.error("Question text is required.")
                else:
                    conn = connect()
                    insert_question(conn, {
                        "topic_id":            tid_map[a_topic],
                        "age_group_id":        agid_map[a_ag],
                        "level":               a_level,
                        "question_type":       a_type,
                        "question_text":       a_qtext.strip(),
                        "context":             a_ctx.strip(),
                        "hint":                a_hint.strip(),
                        "sample_answer":       a_sample.strip(),
                        "discussion_points":   [l.strip() for l in a_dp.splitlines() if l.strip()],
                        "follow_up_questions": [l.strip() for l in a_fu.splitlines() if l.strip()],
                        "tags":                a_tags.strip(),
                    }, source="manual")
                    conn.close()
                    st.success("Question saved!")
                    st.rerun()

    st.divider()

    # ── Question cards ─────────────────────────────────────────────────────────
    if not questions:
        st.info("No questions match your filters.")
    else:
        for q in questions:
            level_cls = {"simple": "badge-simple", "medium": "badge-medium", "hard": "badge-hard"}.get(q["level"], "badge-type")
            inactive_tag = "" if q["is_active"] else '<span class="badge" style="background:#2a0a0a;color:#ff6666;">inactive</span>'
            fav_tag = '<span class="badge" style="background:#2a1f00;color:#ffcc00;">⭐ favourite</span>' if q.get("is_favourite") else ""
            header_html = (
                f'<span class="badge {level_cls}">{q["level"]}</span>'
                f'<span class="badge badge-type">{q["question_type"]}</span>'
                f'<span class="badge badge-source">{q["source"]}</span>'
                f'<span class="badge" style="background:#1a1a2e;color:#8899cc;">{q["age_group_label"]}</span>'
                f'{fav_tag}{inactive_tag}'
            )

            fav_prefix = "⭐ " if q.get("is_favourite") else ""
            with st.expander(f'{fav_prefix}**{q["question_text"][:100]}{"…" if len(q["question_text"])>100 else ""}**  ·  {q["topic_name"]}'):
                st.markdown(header_html, unsafe_allow_html=True)

                if q.get("context"):
                    st.markdown(f"**Context:** _{q['context']}_")
                st.markdown(f"**Question:** {q['question_text']}")

                if q.get("hint"):
                    st.markdown(f"**Hint:** {q['hint']}")

                if q.get("sample_answer"):
                    with st.expander("📝 Sample Answer"):
                        st.write(q["sample_answer"])

                if q.get("discussion_points"):
                    st.markdown("**Discussion Points:**")
                    for dp in q["discussion_points"]:
                        st.markdown(f"  - {dp}")

                if q.get("follow_up_questions"):
                    st.markdown("**Follow-up Questions:**")
                    for fq in q["follow_up_questions"]:
                        st.markdown(f"  - {fq}")

                if q.get("tags"):
                    st.caption(f"Tags: {q['tags']}")
                st.caption(f"Added: {q['created_at'][:10]}  ·  ID #{q['id']}")

                # Actions row: favourite | deactivate/restore | edit
                ec1, ec2, ec3 = st.columns(3)
                with ec1:
                    fav_label = "⭐ Unfavourite" if q.get("is_favourite") else "☆ Favourite"
                    if st.button(fav_label, key=f"fav_{q['id']}", use_container_width=True):
                        conn = connect()
                        toggle_favourite(conn, q["id"])
                        conn.close()
                        st.rerun()
                with ec2:
                    if q["is_active"]:
                        if st.button("🚫 Deactivate", key=f"deact_{q['id']}", use_container_width=True):
                            conn = connect()
                            deactivate_question(conn, q["id"])
                            conn.close()
                            st.rerun()
                    else:
                        if st.button("✅ Restore", key=f"rest_{q['id']}", use_container_width=True):
                            conn = connect()
                            restore_question(conn, q["id"])
                            conn.close()
                            st.rerun()
                with ec3:
                    if st.button("✏️ Edit", key=f"edit_{q['id']}", use_container_width=True):
                        st.session_state[f"editing_{q['id']}"] = True

                # Inline edit form
                if st.session_state.get(f"editing_{q['id']}"):
                    with st.form(f"edit_form_{q['id']}"):
                        st.markdown("**Edit Question**")
                        e_qtext  = st.text_area("Question Text", value=q["question_text"], height=80)
                        e_ctx    = st.text_area("Context",       value=q.get("context",""), height=60)
                        e_hint   = st.text_area("Hint",          value=q.get("hint",""),    height=60)
                        e_sample = st.text_area("Sample Answer", value=q.get("sample_answer",""), height=80)
                        e_dp     = st.text_area("Discussion Points (one per line)",
                                                value="\n".join(q.get("discussion_points",[])), height=80)
                        e_fu     = st.text_area("Follow-up Questions (one per line)",
                                                value="\n".join(q.get("follow_up_questions",[])), height=60)
                        e_tags   = st.text_input("Tags", value=q.get("tags",""))
                        e_level  = st.selectbox("Level", LEVELS, index=LEVELS.index(q["level"]))
                        save_edit = st.form_submit_button("💾 Save Changes")
                        if save_edit:
                            conn = connect()
                            update_question(conn, q["id"], {
                                "question_text":       e_qtext.strip(),
                                "context":             e_ctx.strip(),
                                "hint":                e_hint.strip(),
                                "sample_answer":       e_sample.strip(),
                                "discussion_points":   [l.strip() for l in e_dp.splitlines() if l.strip()],
                                "follow_up_questions": [l.strip() for l in e_fu.splitlines() if l.strip()],
                                "tags":                e_tags.strip(),
                                "level":               e_level,
                            })
                            conn.close()
                            st.session_state.pop(f"editing_{q['id']}", None)
                            st.success("Saved!")
                            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — AI Generator
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("### 🤖 AI Question Generator")
    st.markdown(
        "Generate a batch of questions, then **save only the ones you like** "
        "to your offline collection — one at a time or all at once."
    )

    if not is_ollama and not st.session_state.api_key:
        st.warning("⚠️ Enter an API key in the sidebar to use AI generation.")

    g1, g2, g3 = st.columns(3)
    with g1:
        gen_topic = st.selectbox("Topic Domain *", topic_names, key="gen_topic")
        gen_ag    = st.selectbox("Age Group *",    ag_labels,   key="gen_ag")
    with g2:
        gen_level = st.selectbox("Difficulty Level *", LEVELS, key="gen_level")
        gen_type  = st.selectbox("Question Type *", QUESTION_TYPES, key="gen_type")
    with g3:
        gen_count = st.slider("Number of questions", 3, 15, 5, key="gen_count")
        languages = ["English","Hindi","Marathi","Spanish","French","German","Portuguese","Japanese","Arabic"]
        gen_lang  = st.selectbox("Language", languages, key="gen_lang")

    gen_hint = st.text_input(
        "Optional theme / focus within this topic",
        placeholder="e.g. 'focus on friendship conflicts' or 'include school scenarios'",
        key="gen_hint",
    )

    TYPE_DESCS = {
        "scenario":      "A realistic situation — 'What would you do if…'",
        "dilemma":       "Two valid options with real trade-offs — no easy answer",
        "reflection":    "Inward-looking — child reflects on own feelings or behaviour",
        "debate_starter":"Provocative statement to spark group discussion",
        "creative":      "Open-ended imagination prompt — no wrong answer",
        "what_if":       "Hypothetical world-building to explore consequences",
    }
    st.caption(f"💡 **{gen_type}**: {TYPE_DESCS.get(gen_type,'')}")

    ag_info = ag_by_label.get(gen_ag, {})

    btn_disabled = not is_ollama and not st.session_state.api_key
    if st.button("⚡ Generate Questions", type="primary", disabled=btn_disabled, use_container_width=True):
        with st.spinner(f"Generating {gen_count} questions via {selected_provider} · {selected_model}…"):
            try:
                results = generate_questions(
                    provider   = selected_provider,
                    api_key    = st.session_state.api_key,
                    model      = selected_model,
                    topic      = gen_topic,
                    age_group  = gen_ag,
                    min_age    = ag_info.get("min_age", 5),
                    max_age    = ag_info.get("max_age", 18),
                    level      = gen_level,
                    q_type     = gen_type,
                    count      = gen_count,
                    language   = gen_lang,
                    topic_hint = gen_hint,
                )
                st.session_state.gen_results  = results
                st.session_state.gen_saved    = [False] * len(results)
                st.session_state.gen_meta     = {
                    "topic": gen_topic, "ag": gen_ag, "level": gen_level,
                    "q_type": gen_type, "provider": selected_provider, "model": selected_model,
                }
                st.success(f"Generated {len(results)} questions. Save the ones you like below.")
            except Exception as e:
                st.error(f"Generation failed: {e}")

    # ── Review and selectively save ────────────────────────────────────────────
    if st.session_state.gen_results:
        results = st.session_state.gen_results
        saved   = st.session_state.gen_saved
        meta    = st.session_state.gen_meta

        n_saved   = sum(saved)
        n_unsaved = len(results) - n_saved

        st.divider()

        # Summary bar
        sb1, sb2, sb3 = st.columns(3)
        sb1.metric("Generated", len(results))
        sb2.metric("Saved to DB", n_saved)
        sb3.metric("Not saved yet", n_unsaved)

        if n_unsaved > 0:
            if st.button(f"💾 Save all remaining {n_unsaved} to collection", use_container_width=True):
                conn = connect()
                for i, q in enumerate(results):
                    if not st.session_state.gen_saved[i]:
                        _save_generated_question(conn, q, meta)
                        st.session_state.gen_saved[i] = True
                conn.close()
                st.success(f"All {n_unsaved} saved!")
                st.rerun()

        if st.button("🗑️ Clear results", use_container_width=False):
            st.session_state.gen_results = []
            st.session_state.gen_saved   = []
            st.session_state.gen_meta    = {}
            st.rerun()

        st.divider()
        level_cls = {"simple":"badge-simple","medium":"badge-medium","hard":"badge-hard"}.get(
            meta.get("level",""), "badge-type"
        )

        for i, q in enumerate(results):
            is_saved = st.session_state.gen_saved[i]

            # Card border: green if saved, normal if not
            border_color = "#00c853" if is_saved else "#1e2a44"
            saved_banner = (
                '<span style="background:#0d2b1a;color:#00d26a;border-radius:20px;'
                'padding:2px 12px;font-size:.8rem;font-weight:bold;">✅ Saved to collection</span>'
                if is_saved else ""
            )

            q_preview = q["question_text"][:80] + ("…" if len(q["question_text"]) > 80 else "")

            with st.expander(f'{"✅" if is_saved else "📋"} Q{i+1}: {q_preview}'):
                # Badges + saved state
                st.markdown(
                    f'<span class="badge {level_cls}">{meta.get("level","")}</span>'
                    f'<span class="badge badge-type">{meta.get("q_type","")}</span>'
                    f'<span class="badge" style="background:#1a1a2e;color:#8899cc;">{meta.get("ag","")}</span>'
                    f'&nbsp;&nbsp;{saved_banner}',
                    unsafe_allow_html=True,
                )
                st.markdown("")

                # Full question content
                if q.get("context"):
                    st.markdown(f"*{q['context']}*")

                st.markdown(f"### {q['question_text']}")

                col_hint, col_ans = st.columns(2)
                with col_hint:
                    if q.get("hint"):
                        st.markdown(
                            f'<div style="background:#1a2c1a;border-left:3px solid #00d26a;'
                            f'border-radius:6px;padding:10px 14px;color:#90e8a0;font-size:.9rem;">'
                            f'💡 <strong>Hint:</strong> {q["hint"]}</div>',
                            unsafe_allow_html=True,
                        )
                with col_ans:
                    if q.get("sample_answer"):
                        with st.expander("📝 Sample answer"):
                            st.write(q["sample_answer"])

                if q.get("discussion_points"):
                    st.markdown("**Discussion points:**")
                    for dp in q["discussion_points"]:
                        st.markdown(f"&nbsp;&nbsp;• {dp}")

                if q.get("follow_up_questions"):
                    st.markdown("**Follow-up questions:**")
                    for fq in q["follow_up_questions"]:
                        st.markdown(f"&nbsp;&nbsp;→ {fq}")

                if q.get("tags"):
                    st.caption(f"Tags: {q['tags']}")

                st.markdown("---")

                # Edit before saving
                with st.expander("✏️ Edit before saving"):
                    new_qtext  = st.text_area("Question text:", value=q["question_text"],
                                               key=f"e_qt_{i}", height=80)
                    new_hint   = st.text_input("Hint:", value=q.get("hint",""), key=f"e_h_{i}")
                    new_sample = st.text_area("Sample answer:", value=q.get("sample_answer",""),
                                               key=f"e_sa_{i}", height=70)
                    new_tags   = st.text_input("Tags:", value=q.get("tags",""), key=f"e_tg_{i}")
                    if st.button("Apply edits", key=f"e_apply_{i}"):
                        st.session_state.gen_results[i].update({
                            "question_text": new_qtext,
                            "hint":          new_hint,
                            "sample_answer": new_sample,
                            "tags":          new_tags,
                        })
                        st.rerun()

                # ── Save / Unsave button ───────────────────────────────────────
                if not is_saved:
                    if st.button(
                        f"💾 Save this to my collection",
                        key=f"save_one_{i}",
                        type="primary",
                        use_container_width=True,
                    ):
                        conn = connect()
                        _save_generated_question(conn, st.session_state.gen_results[i], meta)
                        conn.close()
                        st.session_state.gen_saved[i] = True
                        st.success("Saved to your question bank! ✅")
                        st.rerun()
                else:
                    st.success("✅ Already in your collection — available in Question Bank offline.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Sessions
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("### 📅 Session Builder")

    sl, sr = st.columns([1, 1])

    # ── Create session ─────────────────────────────────────────────────────────
    with sl:
        st.markdown("#### Create New Session")
        with st.form("create_session_form"):
            s_name  = st.text_input("Session Name *", placeholder="e.g. Week 3 — Builders Group")
            s_date  = st.date_input("Session Date", value=date.today())
            s_ag    = st.selectbox("Age Group", ag_labels, key="s_ag")
            s_week  = st.number_input("Week Number (1–8)", min_value=1, max_value=8, value=1)
            s_facil = st.text_input("Facilitator Name", placeholder="Optional")
            s_notes = st.text_area("Pre-session Notes", height=60, placeholder="Optional")

            week_topics = CURRICULUM.get(int(s_week), {}).get("topics", [])
            if week_topics:
                st.caption(f"💡 Week {s_week} theme: **{CURRICULUM[int(s_week)]['theme']}** — "
                            + ", ".join(week_topics))

            create_btn = st.form_submit_button("➕ Create Session", type="primary")
            if create_btn:
                if not s_name.strip():
                    st.error("Session name is required.")
                else:
                    conn = connect()
                    sid = create_session(
                        conn,
                        name         = s_name.strip(),
                        session_date = str(s_date),
                        age_group_id = agid_map.get(s_ag),
                        week_number  = int(s_week),
                        facilitator  = s_facil.strip(),
                        notes        = s_notes.strip(),
                    )
                    conn.close()
                    st.success(f"Session created! ID #{sid}")
                    st.session_state["active_session_id"] = sid
                    st.rerun()

    # ── Existing sessions ──────────────────────────────────────────────────────
    with sr:
        st.markdown("#### Existing Sessions")
        conn     = connect()
        sessions = get_sessions(conn)
        conn.close()

        if not sessions:
            st.info("No sessions yet. Create one on the left.")
        else:
            for s in sessions[:15]:
                label = (f"📅 **{s['session_name']}** · {s['session_date']} · "
                         f"{s.get('age_group_label','')} · "
                         f"{s.get('q_count',0)} Q ({s.get('used_count',0)} used)")
                if st.button(label, key=f"sel_sess_{s['id']}", use_container_width=True):
                    st.session_state["active_session_id"] = s["id"]
                    st.rerun()

    # ── Session detail ──────────────────────────────────────────────────────────
    active_sid = st.session_state.get("active_session_id")
    if active_sid:
        st.divider()
        conn     = connect()
        sess     = get_session(conn, active_sid)
        sess_qs  = get_session_questions(conn, active_sid)
        conn.close()

        if not sess:
            st.warning("Session not found.")
        else:
            st.markdown(f"### 📋 {sess['session_name']}")
            si1, si2, si3, si4 = st.columns(4)
            si1.metric("Date",         sess["session_date"])
            si2.metric("Age Group",    sess.get("age_group_label","—"))
            si3.metric("Week",         sess.get("week_number","—"))
            si4.metric("Questions",    len(sess_qs))

            if sess.get("facilitator"):
                st.caption(f"Facilitator: {sess['facilitator']}")

            # Status
            status_options = ["planned","in_progress","completed"]
            cur_status = sess.get("status","planned")
            new_status = st.selectbox("Status", status_options,
                                       index=status_options.index(cur_status),
                                       key=f"status_{active_sid}")
            if new_status != cur_status:
                conn = connect()
                update_session(conn, active_sid, {"status": new_status})
                conn.close()

            # ── Questions in session ────────────────────────────────────────────
            st.markdown("#### Questions in this Session")
            if not sess_qs:
                st.info("No questions added yet. Search below and add questions.")
            else:
                for idx_s, sq in enumerate(sess_qs):
                    done_icon = "✅" if sq.get("was_used") else "⬜"
                    level_cls = {"simple":"badge-simple","medium":"badge-medium","hard":"badge-hard"}.get(sq["level"],"badge-type")
                    with st.expander(f"{done_icon} {idx_s+1}. {sq['question_text'][:80]}…"):
                        st.markdown(
                            f'<span class="badge {level_cls}">{sq["level"]}</span>'
                            f'<span class="badge badge-type">{sq["question_type"]}</span>'
                            f'<span class="badge" style="background:#1a1a2e;color:#8899cc;">{sq["age_group_label"]}</span>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(sq["question_text"])
                        if sq.get("hint"):
                            st.markdown(f"**Hint:** {sq['hint']}")
                        if sq.get("discussion_points"):
                            st.markdown("**Discussion Points:**")
                            for dp in sq["discussion_points"]:
                                st.markdown(f"  - {dp}")
                        if st.button("🗑️ Remove from session", key=f"rm_{active_sid}_{sq['question_id']}"):
                            conn = connect()
                            remove_question_from_session(conn, active_sid, sq["question_id"])
                            conn.close()
                            st.rerun()

            # ── Add questions to session ────────────────────────────────────────
            st.markdown("#### Add Questions from Bank")
            qa1, qa2, qa3 = st.columns(3)
            with qa1:
                add_topic = st.selectbox("Filter topic", ["All topics"] + topic_names, key="add_topic")
            with qa2:
                add_ag    = st.selectbox("Filter age group", ["All ages"] + ag_labels, key="add_ag")
            with qa3:
                add_level = st.selectbox("Filter level", ["All"] + LEVELS, key="add_level")

            conn = connect()
            bank_qs = get_questions(
                conn,
                topic_id     = tid_map.get(add_topic) if add_topic != "All topics" else None,
                age_group_id = agid_map.get(add_ag)   if add_ag != "All ages" else None,
                level        = add_level if add_level != "All" else None,
            )
            conn.close()

            already_in = {sq["question_id"] for sq in sess_qs}
            available  = [q for q in bank_qs if q["id"] not in already_in]

            st.caption(f"{len(available)} available question(s) from bank")
            for bq in available[:30]:
                bc1, bc2 = st.columns([9, 1])
                with bc1:
                    level_cls = {"simple":"badge-simple","medium":"badge-medium","hard":"badge-hard"}.get(bq["level"],"badge-type")
                    st.markdown(
                        f'<span class="badge {level_cls}">{bq["level"]}</span> '
                        f'{bq["question_text"][:100]}',
                        unsafe_allow_html=True,
                    )
                with bc2:
                    if st.button("➕", key=f"addq_{active_sid}_{bq['id']}", help="Add to session"):
                        conn = connect()
                        add_question_to_session(conn, active_sid, bq["id"])
                        conn.close()
                        st.rerun()

            # ── Export ─────────────────────────────────────────────────────────
            st.divider()
            ex1, ex2 = st.columns([1, 1])
            with ex1:
                # Export as Markdown
                if sess_qs:
                    md_lines = [
                        f"# {sess['session_name']}",
                        f"**Date:** {sess['session_date']}  |  **Age Group:** {sess.get('age_group_label','')}  |  **Week:** {sess.get('week_number','')}",
                        f"**Facilitator:** {sess.get('facilitator','—')}",
                        "",
                    ]
                    for i_ex, sq in enumerate(sess_qs, 1):
                        md_lines += [
                            f"## Q{i_ex}: {sq['question_text']}",
                            "",
                        ]
                        if sq.get("context"):
                            md_lines += [f"*{sq['context']}*", ""]
                        if sq.get("hint"):
                            md_lines += [f"**Hint:** {sq['hint']}", ""]
                        if sq.get("discussion_points"):
                            md_lines.append("**Discussion Points:**")
                            for dp in sq["discussion_points"]:
                                md_lines.append(f"- {dp}")
                            md_lines.append("")
                        if sq.get("sample_answer"):
                            md_lines += [f"**Sample Answer (facilitator):** {sq['sample_answer']}", ""]
                        md_lines.append("---")

                    md_content = "\n".join(md_lines)
                    fname = sess["session_name"].replace(" ", "_").replace("/","_")[:50] + ".md"
                    st.download_button(
                        "⬇️ Export Session as Markdown",
                        data=md_content.encode("utf-8"),
                        file_name=fname,
                        mime="text/markdown",
                        use_container_width=True,
                    )
            with ex2:
                if st.button("🗑️ Delete this Session", use_container_width=True):
                    conn = connect()
                    delete_session(conn, active_sid)
                    conn.close()
                    st.session_state.pop("active_session_id", None)
                    st.success("Session deleted.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Classroom Launcher
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("### 🎯 Classroom View")
    st.markdown(
        "Enter classroom mode to display questions one at a time — "
        "projector-ready, with hint and discussion controls."
    )

    cls_mode = st.radio(
        "Load questions from:",
        ["📅 A saved session", "🔀 Quick pick from bank"],
        horizontal=True,
        key="cls_mode",
    )

    cls_questions_to_load = []

    if cls_mode == "📅 A saved session":
        conn     = connect()
        sessions = get_sessions(conn)
        conn.close()

        if not sessions:
            st.info("No sessions yet. Build one in the Sessions tab first.")
        else:
            sess_opts = {f"{s['session_name']} ({s['session_date']})": s["id"] for s in sessions}
            chosen    = st.selectbox("Choose session", list(sess_opts.keys()), key="cls_sess_pick")
            chosen_id = sess_opts[chosen]

            conn = connect()
            sq   = get_session_questions(conn, chosen_id)
            conn.close()

            st.caption(f"{len(sq)} question(s) in this session")
            cls_questions_to_load = sq

    else:
        st.markdown("**Quick pick from question bank:**")
        qp1, qp2, qp3 = st.columns(3)
        with qp1:
            qp_ag  = st.selectbox("Age Group", ag_labels, key="qp_ag")
        with qp2:
            qp_topic = st.selectbox("Topic", ["Any"] + topic_names, key="qp_topic")
        with qp3:
            qp_level = st.selectbox("Level", ["Any"] + LEVELS, key="qp_level")

        qp_count = st.slider("How many questions?", 3, 20, 8, key="qp_count")

        conn = connect()
        qp_qs = get_questions(
            conn,
            topic_id     = tid_map.get(qp_topic) if qp_topic != "Any" else None,
            age_group_id = agid_map.get(qp_ag),
            level        = qp_level if qp_level != "Any" else None,
            limit        = qp_count,
        )
        conn.close()

        # Convert to session_questions format for consistency
        cls_questions_to_load = [{**q, "id": None, "was_used": 0} for q in qp_qs[:qp_count]]
        st.caption(f"{len(cls_questions_to_load)} question(s) ready")

    st.markdown("---")

    if cls_questions_to_load:
        st.markdown(f"**{len(cls_questions_to_load)} question(s) ready for classroom**")
        for i_p, q in enumerate(cls_questions_to_load[:5], 1):
            st.markdown(f"{i_p}. {q['question_text'][:80]}…" if len(q['question_text'])>80 else f"{i_p}. {q['question_text']}")
        if len(cls_questions_to_load) > 5:
            st.caption(f"…and {len(cls_questions_to_load)-5} more")

        if st.button("🚀 Enter Classroom View", type="primary", use_container_width=True):
            st.session_state.classroom_mode = True
            st.session_state.cls_questions  = cls_questions_to_load
            st.session_state.cls_q_index    = 0
            st.session_state.cls_show_hint  = False
            st.session_state.cls_show_disc  = False
            st.rerun()
    else:
        st.info("Select a session or configure quick-pick to see questions here.")
