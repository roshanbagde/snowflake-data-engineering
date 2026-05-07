"""
Database layer for ThinkSpark.
SQLite schema, seed data, and all CRUD operations.
"""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "thinkpark.db"

# ── Master data ────────────────────────────────────────────────────────────────

TOPICS = [
    ("🧠 Critical Thinking",          "Logic, reasoning, problem analysis, spotting flaws in arguments"),
    ("❤️ Emotional Intelligence",     "Empathy, self-regulation, recognising and understanding emotions"),
    ("💬 Communication",              "Speaking clearly, active listening, expressing ideas confidently"),
    ("🤝 Social Skills & Teamwork",   "Collaboration, conflict resolution, fairness, sense of belonging"),
    ("🏆 Leadership & Decisions",     "Responsibility, decision-making under pressure, owning mistakes"),
    ("🎨 Creativity & Problem Solving","Open-ended thinking, innovation, imagination, lateral thinking"),
    ("⚖️ Ethics & Values",            "Right vs. easy, honesty, fairness, moral dilemmas"),
    ("🪞 Self-Awareness",             "Strengths, weaknesses, personal values, identity, growth mindset"),
    ("💰 Financial Literacy",         "Needs vs. wants, saving, fairness of money (age-adjusted)"),
    ("🌍 Environment & Society",      "Impact of choices, community responsibility, global thinking"),
]

AGE_GROUPS = [
    ("Seedlings",   5,  7,  "Short scenarios, visual language, play-based thinking"),
    ("Explorers",   8,  10, "Story-based dilemmas, simple cause-effect reasoning"),
    ("Builders",    11, 13, "Real social situations, peer dynamics, basic ethics"),
    ("Challengers", 14, 16, "Complex dilemmas, leadership, debate-ready questions"),
    ("Leaders",     17, 18, "Real-world problems, career/life decisions, advanced ethics"),
]

QUESTION_TYPES = ["scenario", "dilemma", "reflection", "debate_starter", "creative", "what_if", "puzzle"]
LEVELS         = ["simple", "medium", "hard"]

CURRICULUM = {
    1: {"theme": "Know Yourself",       "topics": ["🪞 Self-Awareness", "❤️ Emotional Intelligence"]},
    2: {"theme": "Feel & Express",      "topics": ["❤️ Emotional Intelligence", "💬 Communication"]},
    3: {"theme": "Talk & Listen",       "topics": ["💬 Communication", "🤝 Social Skills & Teamwork"]},
    4: {"theme": "Work Together",       "topics": ["🤝 Social Skills & Teamwork", "🏆 Leadership & Decisions"]},
    5: {"theme": "Do the Right Thing",  "topics": ["⚖️ Ethics & Values", "🏆 Leadership & Decisions"]},
    6: {"theme": "Think Creatively",    "topics": ["🎨 Creativity & Problem Solving", "🧠 Critical Thinking"]},
    7: {"theme": "Think Deeply",        "topics": ["🧠 Critical Thinking", "🌍 Environment & Society"]},
    8: {"theme": "Lead & Impact",       "topics": ["🌍 Environment & Society", "💰 Financial Literacy"]},
}

_SEED_QUESTIONS = [
    # ── Seedlings (5-7) ─────────────────────────────────────────────────────────
    {
        "topic": "❤️ Emotional Intelligence", "age_group": "Seedlings",
        "level": "simple", "type": "scenario",
        "question_text": "Your friend falls down and starts crying. What do you do?",
        "context": "You are playing outside in the park.",
        "hint": "Think about how your friend feels right now. What would make you feel better if you were hurt?",
        "sample_answer": "Go to them right away. Ask if they are okay. Help them up. Give them a hug or get a grown-up if they are really hurt.",
        "discussion_points": ["Why is it important to go to a friend who is hurt?", "How does it feel when someone helps you?", "What are different ways to show you care?"],
        "follow_up_questions": ["What if the friend says they are fine but is still crying?", "What if you do not know what to say — is it okay to just sit with them?"],
        "tags": "empathy,helping,friendship",
    },
    {
        "topic": "⚖️ Ethics & Values", "age_group": "Seedlings",
        "level": "simple", "type": "dilemma",
        "question_text": "You find a shiny eraser on the floor at school. It has no name on it and no one is watching. What do you do?",
        "context": "",
        "hint": "Think about how the person who lost it might feel. What would you want someone to do if YOU lost something?",
        "sample_answer": "Hand it to the teacher or put it in the lost-and-found. Taking it without trying to return it would not be fair.",
        "discussion_points": ["Why is honesty important even when no one is watching?", "How would you feel if someone kept something you lost?", "Does it matter if the thing is small or big?"],
        "follow_up_questions": ["What if it was money — would that change things?", "What does it mean to have a 'conscience'?"],
        "tags": "honesty,fairness,values",
    },
    {
        "topic": "🎨 Creativity & Problem Solving", "age_group": "Seedlings",
        "level": "simple", "type": "creative",
        "question_text": "If you could invent a new animal, what would it look like and what special power would it have?",
        "context": "",
        "hint": "Think about animals you know. What do they do well? What could be even better? What problem could your animal solve?",
        "sample_answer": "Any creative answer is perfect! The key is to explain WHY your animal's special power is useful or interesting.",
        "discussion_points": ["Where did your idea come from?", "What would this animal eat?", "Could an animal like this ever exist in real life? Why or why not?"],
        "follow_up_questions": ["What would you name it?", "Would it be your friend or a wild animal?"],
        "tags": "creativity,imagination,nature",
    },
    # ── Explorers (8-10) ─────────────────────────────────────────────────────────
    {
        "topic": "🧠 Critical Thinking", "age_group": "Explorers",
        "level": "medium", "type": "what_if",
        "question_text": "What if schools had no homework? Would that be better or worse for students? Why?",
        "context": "",
        "hint": "Think of reasons it could be both good AND bad. Try to see both sides before picking one.",
        "sample_answer": "No homework means more time to rest and play. But practice at home helps learning stick. The answer depends on how much homework and what kind.",
        "discussion_points": ["What is the actual purpose of homework?", "Could there be a middle ground?", "Who should decide — students, parents, or teachers?"],
        "follow_up_questions": ["What would you replace homework with?", "Are some subjects where homework matters more than others?"],
        "tags": "education,debate,reasoning",
    },
    {
        "topic": "🤝 Social Skills & Teamwork", "age_group": "Explorers",
        "level": "medium", "type": "scenario",
        "question_text": "Your group is working on a project. One person is not doing any work but will get the same grade. What do you do?",
        "context": "You have been working hard for two weeks. The deadline is next week.",
        "hint": "Think about talking to that person privately first. Why might they not be contributing? Are they struggling?",
        "sample_answer": "First, talk privately with the person. Maybe they are confused or struggling. Give them a specific small task. If it does not improve, speak to the teacher — not to get them in trouble but to get help.",
        "discussion_points": ["Is it fair to get the same grade for different amounts of work?", "Why might someone not contribute — fear, confusion, problems at home?", "What is the difference between tattling and asking for help?"],
        "follow_up_questions": ["What if the person says they just do not care?", "How would you feel if you were the one struggling?"],
        "tags": "teamwork,fairness,conflict,communication",
    },
    {
        "topic": "💰 Financial Literacy", "age_group": "Explorers",
        "level": "medium", "type": "dilemma",
        "question_text": "You saved ₹500 over many months. Your friend wants to borrow ₹300 and promises to pay back — but they have forgotten to return money before. What do you do?",
        "context": "",
        "hint": "Think about both your friendship and your savings. What matters most? Can you say no kindly?",
        "sample_answer": "It is completely okay to say no, or to offer only what you can afford to lose. A true friend will understand. You could offer to do something together that does not involve lending money.",
        "discussion_points": ["Is it wrong to say no when a friend asks for money?", "What is the difference between a gift and a loan?", "How does money affect friendships?"],
        "follow_up_questions": ["What would you say to your friend to explain your decision kindly?", "What if YOU needed that money urgently soon?"],
        "tags": "financial literacy,friendship,decisions,trust",
    },
    {
        "topic": "🌍 Environment & Society", "age_group": "Explorers",
        "level": "medium", "type": "what_if",
        "question_text": "What if every person on Earth spoke the same language? What would be the benefits — and what would be lost?",
        "context": "",
        "hint": "Think about how language connects to culture, identity, and understanding others.",
        "sample_answer": "Benefits: easier communication, less misunderstanding. Losses: cultural diversity, unique ways of seeing the world, traditions tied to language. Language is not just words — it carries a whole worldview.",
        "discussion_points": ["What does language have to do with identity?", "Which language would everyone speak, and who would decide?", "What makes cultural diversity valuable?"],
        "follow_up_questions": ["Would this create more equality or less?", "What is one thing you love about your own language or culture?"],
        "tags": "culture,language,global thinking,debate",
    },
    # ── Builders (11-13) ──────────────────────────────────────────────────────────
    {
        "topic": "🏆 Leadership & Decisions", "age_group": "Builders",
        "level": "medium", "type": "dilemma",
        "question_text": "You are the team captain. Your best friend wants to play in the final game, but another player is clearly better. You can only pick one. What do you do?",
        "context": "The result matters to the whole team.",
        "hint": "Think about what is fair to the whole team, and also what a good friend actually looks like.",
        "sample_answer": "A good leader puts the team first. Pick the better player for the game, but explain to your friend honestly and kindly. A real friend will understand — even if it hurts.",
        "discussion_points": ["What makes someone a good leader?", "Is fairness to one person the same as fairness to the whole team?", "How do you have a hard conversation without destroying a friendship?"],
        "follow_up_questions": ["What if your friend gets very angry with you?", "What if the 'better' player has a bad attitude toward the team?"],
        "tags": "leadership,fairness,friendship,decisions",
    },
    {
        "topic": "💬 Communication", "age_group": "Builders",
        "level": "medium", "type": "reflection",
        "question_text": "Think of a time you had an argument with someone. Looking back, what could you have done differently?",
        "context": "",
        "hint": "Think about what you said, how you said it, and whether you actually listened to the other person.",
        "sample_answer": "Everyone argues sometimes. The key is to recognize when you could have listened better, spoken more calmly, or tried to understand the other person's point of view before reacting.",
        "discussion_points": ["What is the difference between hearing and listening?", "How does the way you say something change the outcome?", "What makes an apology meaningful — or not?"],
        "follow_up_questions": ["Did the argument change your relationship? How?", "What would you tell a younger child about how to handle arguments?"],
        "tags": "communication,reflection,conflict,self-awareness",
    },
    {
        "topic": "🤝 Social Skills & Teamwork", "age_group": "Builders",
        "level": "hard", "type": "scenario",
        "question_text": "You notice a classmate being quietly left out by your friend group. Nobody has done anything obviously mean — they just do not include this person. What do you do?",
        "context": "You have been friends with the group for years.",
        "hint": "Think about the difference between doing something wrong and not doing something right. Both can cause harm.",
        "sample_answer": "Exclusion is unkind even without obvious meanness. You can include the person yourself without needing the whole group to agree. Small acts matter: sit with them, invite them to one thing, acknowledge them.",
        "discussion_points": ["What is the difference between exclusion and bullying?", "Why do groups sometimes quietly exclude people?", "What does it take to include someone when the group has unspoken rules?"],
        "follow_up_questions": ["What stops most people from doing something in this situation?", "Have you ever felt excluded? What did it feel like?"],
        "tags": "empathy,belonging,courage,social skills",
    },
    # ── Challengers (14-16) ────────────────────────────────────────────────────────
    {
        "topic": "⚖️ Ethics & Values", "age_group": "Challengers",
        "level": "hard", "type": "debate_starter",
        "question_text": "Is it ever okay to lie? Give examples of when lying might be the right thing to do — and when it is clearly wrong.",
        "context": "",
        "hint": "Think about who the lie protects and who it harms. Does intention change the ethics?",
        "sample_answer": "Most lying breaks trust and causes harm. But edge cases exist — lying to protect someone from danger, for example. The question is: who benefits, who is harmed, and what happens to trust long-term?",
        "discussion_points": ["What is the difference between a 'white lie' and a harmful lie?", "Does the intention behind a lie matter more than its outcome?", "Can honesty be unkind? Can lying be kind?"],
        "follow_up_questions": ["Do small lies add up over time into something bigger?", "Would a world with no lying be better or worse overall?"],
        "tags": "ethics,honesty,debate,moral reasoning",
    },
    {
        "topic": "🧠 Critical Thinking", "age_group": "Challengers",
        "level": "hard", "type": "scenario",
        "question_text": "You read two news articles about the same event that say completely opposite things. How do you figure out what actually happened?",
        "context": "",
        "hint": "Think about why each source might tell the story differently. What questions would you ask about each source?",
        "sample_answer": "Look at WHO wrote it and WHY. Find a third independent source. Look for facts both agree on. Check for evidence — data, witnesses, documents. Be comfortable saying 'I do not know yet' rather than picking a side too fast.",
        "discussion_points": ["Why would different sources describe the same event differently?", "What makes a source trustworthy?", "Is it possible for anyone to be completely unbiased?"],
        "follow_up_questions": ["What if you simply cannot find a reliable source?", "How does media bias shape what large groups of people believe?"],
        "tags": "media literacy,critical thinking,bias,reasoning",
    },
    {
        "topic": "🪞 Self-Awareness", "age_group": "Challengers",
        "level": "hard", "type": "reflection",
        "question_text": "What is one habit or reaction you have that you know is not helpful — and what is stopping you from changing it?",
        "context": "",
        "hint": "Be honest with yourself. This is about what actually happens when things get hard — not what you wish would happen.",
        "sample_answer": "Common patterns: avoiding problems, blaming others, shutting down under pressure. The 'what stops me' is usually fear, habit, or not knowing how. Recognising the pattern honestly is already the first step.",
        "discussion_points": ["What is the difference between knowing what to do and actually doing it?", "Why is self-awareness a sign of maturity, not weakness?", "How do you build a new habit when the old one is comfortable?"],
        "follow_up_questions": ["Who in your life could help you work on this?", "How would your life look different in one year if you made this change?"],
        "tags": "self-awareness,growth mindset,reflection,habits",
    },
    # ── Leaders (17-18) ────────────────────────────────────────────────────────────
    {
        "topic": "🌍 Environment & Society", "age_group": "Leaders",
        "level": "hard", "type": "debate_starter",
        "question_text": "Some argue that individual choices (recycling, less plastic) cannot fix the environment — only governments and corporations can. Do you agree?",
        "context": "",
        "hint": "Think about this from both angles. What can individuals realistically change? What can only large systems change?",
        "sample_answer": "Both matter but in different ways. Individual choices build culture and shape demand. But systemic problems require systemic solutions. It is not either/or: personal action signals values; advocacy changes the system.",
        "discussion_points": ["Can one person genuinely make a difference?", "What is the relationship between individual action and collective change?", "How do you stay motivated about big problems without feeling helpless?"],
        "follow_up_questions": ["If you had political power today, what would be the first environmental law you would pass?", "What is one personal action you believe makes a real difference?"],
        "tags": "environment,systems thinking,debate,responsibility",
    },
    {
        "topic": "🏆 Leadership & Decisions", "age_group": "Leaders",
        "level": "hard", "type": "dilemma",
        "question_text": "You are leading a team project. After two weeks of work, you realise the original plan will not succeed — but one week remains. Do you change course, or push through?",
        "context": "The team has worked hard and morale is high based on the old plan.",
        "hint": "Think about honesty versus sunk cost. What does a good leader do when they realise they were wrong?",
        "sample_answer": "A good leader admits the problem honestly, explains it clearly, and pivots fast. Continuing a doomed plan to save face wastes everyone's effort. Teams respect transparency and a clear new direction more than pretending.",
        "discussion_points": ["What is 'sunk cost fallacy' and why is it a trap?", "How do you admit you were wrong without losing the team's confidence?", "Is there a difference between giving up and changing strategy?"],
        "follow_up_questions": ["How would you announce the change to the team?", "What would you do differently from the start to avoid this situation?"],
        "tags": "leadership,decision-making,sunk cost,honesty,pivoting",
    },
]


# ── Connection ─────────────────────────────────────────────────────────────────

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Schema ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    conn = connect()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS topics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS age_groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            label       TEXT    UNIQUE NOT NULL,
            min_age     INTEGER NOT NULL,
            max_age     INTEGER NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS questions (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id            INTEGER NOT NULL REFERENCES topics(id),
            age_group_id        INTEGER NOT NULL REFERENCES age_groups(id),
            level               TEXT    NOT NULL CHECK(level IN ('simple','medium','hard')),
            question_type       TEXT    NOT NULL,
            question_text       TEXT    NOT NULL,
            context             TEXT    DEFAULT '',
            hint                TEXT    DEFAULT '',
            sample_answer       TEXT    DEFAULT '',
            discussion_points   TEXT    DEFAULT '[]',
            follow_up_questions TEXT    DEFAULT '[]',
            tags                TEXT    DEFAULT '',
            source              TEXT    DEFAULT 'manual',
            ai_provider         TEXT,
            ai_model            TEXT,
            is_active           INTEGER DEFAULT 1,
            is_favourite        INTEGER DEFAULT 0,
            created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name  TEXT    NOT NULL,
            session_date  DATE    NOT NULL,
            age_group_id  INTEGER REFERENCES age_groups(id),
            week_number   INTEGER,
            facilitator   TEXT    DEFAULT '',
            notes         TEXT    DEFAULT '',
            status        TEXT    DEFAULT 'planned',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS session_questions (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id         INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            question_id        INTEGER NOT NULL REFERENCES questions(id),
            order_index        INTEGER DEFAULT 0,
            was_used           INTEGER DEFAULT 0,
            facilitator_notes  TEXT    DEFAULT '',
            time_spent_minutes INTEGER
        );
    """)
    conn.commit()
    # Migrate existing DBs that pre-date the is_favourite column
    try:
        conn.execute("ALTER TABLE questions ADD COLUMN is_favourite INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    _seed(conn)
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    # Topics
    if c.execute("SELECT COUNT(*) FROM topics").fetchone()[0] == 0:
        c.executemany("INSERT INTO topics (name, description) VALUES (?,?)", TOPICS)

    # Age groups
    if c.execute("SELECT COUNT(*) FROM age_groups").fetchone()[0] == 0:
        c.executemany(
            "INSERT INTO age_groups (label, min_age, max_age, description) VALUES (?,?,?,?)",
            AGE_GROUPS,
        )

    # Seed questions
    if c.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
        topic_ids = {row[0]: row[1] for row in c.execute("SELECT name, id FROM topics")}
        ag_ids    = {row[0]: row[1] for row in c.execute("SELECT label, id FROM age_groups")}

        for q in _SEED_QUESTIONS:
            c.execute(
                """INSERT INTO questions
                   (topic_id, age_group_id, level, question_type, question_text, context,
                    hint, sample_answer, discussion_points, follow_up_questions, tags, source)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    topic_ids[q["topic"]],
                    ag_ids[q["age_group"]],
                    q["level"],
                    q["type"],
                    q["question_text"],
                    q.get("context", ""),
                    q.get("hint", ""),
                    q.get("sample_answer", ""),
                    json.dumps(q.get("discussion_points", [])),
                    json.dumps(q.get("follow_up_questions", [])),
                    q.get("tags", ""),
                    "seed",
                ),
            )

    conn.commit()


# ── Lookup helpers ─────────────────────────────────────────────────────────────

def get_topics(conn: sqlite3.Connection) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM topics ORDER BY id")]


def get_age_groups(conn: sqlite3.Connection) -> List[Dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM age_groups ORDER BY min_age")]


def topic_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM topics")}


def age_group_id_map(conn: sqlite3.Connection) -> Dict[str, int]:
    return {r["label"]: r["id"] for r in conn.execute("SELECT id, label FROM age_groups")}


# ── Question CRUD ──────────────────────────────────────────────────────────────

def get_questions(
    conn:            sqlite3.Connection,
    topic_id:        Optional[int] = None,
    age_group_id:    Optional[int] = None,
    level:           Optional[str] = None,
    q_type:          Optional[str] = None,
    search:          Optional[str] = None,
    active_only:     bool = True,
    favourites_only: bool = False,
    limit:           int  = 500,
) -> List[Dict]:
    clauses = []
    params: List[Any] = []

    if active_only:
        clauses.append("q.is_active = 1")
    if favourites_only:
        clauses.append("q.is_favourite = 1")
    if topic_id:
        clauses.append("q.topic_id = ?")
        params.append(topic_id)
    if age_group_id:
        clauses.append("q.age_group_id = ?")
        params.append(age_group_id)
    if level:
        clauses.append("q.level = ?")
        params.append(level)
    if q_type:
        clauses.append("q.question_type = ?")
        params.append(q_type)
    if search:
        clauses.append("(q.question_text LIKE ? OR q.tags LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT q.*, t.name AS topic_name, ag.label AS age_group_label
        FROM questions q
        JOIN topics t ON t.id = q.topic_id
        JOIN age_groups ag ON ag.id = q.age_group_id
        {where}
        ORDER BY q.created_at DESC
        LIMIT {limit}
    """
    rows = conn.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["discussion_points"]   = json.loads(d.get("discussion_points") or "[]")
        d["follow_up_questions"] = json.loads(d.get("follow_up_questions") or "[]")
        result.append(d)
    return result


def insert_question(conn: sqlite3.Connection, q: Dict, source: str = "manual",
                    ai_provider: Optional[str] = None, ai_model: Optional[str] = None) -> int:
    cur = conn.execute(
        """INSERT INTO questions
           (topic_id, age_group_id, level, question_type, question_text, context,
            hint, sample_answer, discussion_points, follow_up_questions, tags,
            source, ai_provider, ai_model)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            q["topic_id"], q["age_group_id"], q["level"], q["question_type"],
            q["question_text"], q.get("context", ""), q.get("hint", ""),
            q.get("sample_answer", ""),
            json.dumps(q.get("discussion_points", [])),
            json.dumps(q.get("follow_up_questions", [])),
            q.get("tags", ""), source, ai_provider, ai_model,
        ),
    )
    conn.commit()
    return cur.lastrowid


def update_question(conn: sqlite3.Connection, qid: int, fields: Dict) -> None:
    fields["updated_at"] = datetime.now().isoformat()
    if "discussion_points" in fields and isinstance(fields["discussion_points"], list):
        fields["discussion_points"] = json.dumps(fields["discussion_points"])
    if "follow_up_questions" in fields and isinstance(fields["follow_up_questions"], list):
        fields["follow_up_questions"] = json.dumps(fields["follow_up_questions"])
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE questions SET {set_clause} WHERE id = ?", list(fields.values()) + [qid])
    conn.commit()


def find_duplicate_question(conn: sqlite3.Connection, question_text: str) -> Optional[Dict]:
    """Return an existing active question whose text matches (case-insensitive), or None."""
    r = conn.execute(
        "SELECT * FROM questions WHERE LOWER(TRIM(question_text)) = LOWER(TRIM(?)) LIMIT 1",
        (question_text,),
    ).fetchone()
    return dict(r) if r else None


def get_duplicate_groups(conn: sqlite3.Connection) -> List[List[Dict]]:
    """Return groups of active questions that share the same normalised text."""
    norm_texts = conn.execute("""
        SELECT LOWER(TRIM(question_text)) AS norm_text
        FROM questions
        WHERE is_active = 1
        GROUP BY LOWER(TRIM(question_text))
        HAVING COUNT(*) > 1
    """).fetchall()

    groups: List[List[Dict]] = []
    for row in norm_texts:
        qs = conn.execute("""
            SELECT q.*, t.name AS topic_name, ag.label AS age_group_label
            FROM questions q
            JOIN topics t  ON t.id  = q.topic_id
            JOIN age_groups ag ON ag.id = q.age_group_id
            WHERE LOWER(TRIM(q.question_text)) = ? AND q.is_active = 1
            ORDER BY q.created_at ASC
        """, (row["norm_text"],)).fetchall()
        groups.append([dict(q) for q in qs])
    return groups


def delete_question(conn: sqlite3.Connection, qid: int) -> None:
    """Hard-delete a question row."""
    conn.execute("DELETE FROM questions WHERE id = ?", (qid,))
    conn.commit()


def deactivate_question(conn: sqlite3.Connection, qid: int) -> None:
    conn.execute("UPDATE questions SET is_active = 0 WHERE id = ?", (qid,))
    conn.commit()


def restore_question(conn: sqlite3.Connection, qid: int) -> None:
    conn.execute("UPDATE questions SET is_active = 1 WHERE id = ?", (qid,))
    conn.commit()


def toggle_favourite(conn: sqlite3.Connection, qid: int) -> None:
    conn.execute(
        "UPDATE questions SET is_favourite = CASE WHEN is_favourite=1 THEN 0 ELSE 1 END WHERE id = ?",
        (qid,),
    )
    conn.commit()


def count_questions(conn: sqlite3.Connection) -> Dict[str, int]:
    total   = conn.execute("SELECT COUNT(*) FROM questions WHERE is_active=1").fetchone()[0]
    by_type = {
        r["question_type"]: r["cnt"]
        for r in conn.execute(
            "SELECT question_type, COUNT(*) as cnt FROM questions WHERE is_active=1 GROUP BY question_type"
        )
    }
    return {"total": total, **by_type}


# ── Session CRUD ───────────────────────────────────────────────────────────────

def create_session(
    conn:         sqlite3.Connection,
    name:         str,
    session_date: str,
    age_group_id: Optional[int],
    week_number:  Optional[int],
    facilitator:  str = "",
    notes:        str = "",
) -> int:
    cur = conn.execute(
        """INSERT INTO sessions (session_name, session_date, age_group_id, week_number, facilitator, notes)
           VALUES (?,?,?,?,?,?)""",
        (name, session_date, age_group_id, week_number, facilitator, notes),
    )
    conn.commit()
    return cur.lastrowid


def get_sessions(conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """SELECT s.*, ag.label AS age_group_label,
                  (SELECT COUNT(*) FROM session_questions sq WHERE sq.session_id = s.id) AS q_count,
                  (SELECT COUNT(*) FROM session_questions sq WHERE sq.session_id = s.id AND sq.was_used=1) AS used_count
           FROM sessions s
           LEFT JOIN age_groups ag ON ag.id = s.age_group_id
           ORDER BY s.session_date DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_session(conn: sqlite3.Connection, session_id: int) -> Optional[Dict]:
    r = conn.execute(
        """SELECT s.*, ag.label AS age_group_label
           FROM sessions s LEFT JOIN age_groups ag ON ag.id = s.age_group_id
           WHERE s.id = ?""",
        (session_id,),
    ).fetchone()
    return dict(r) if r else None


def update_session(conn: sqlite3.Connection, session_id: int, fields: Dict) -> None:
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", list(fields.values()) + [session_id])
    conn.commit()


def delete_session(conn: sqlite3.Connection, session_id: int) -> None:
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()


def add_question_to_session(conn: sqlite3.Connection, session_id: int, question_id: int) -> None:
    existing = conn.execute(
        "SELECT id FROM session_questions WHERE session_id=? AND question_id=?",
        (session_id, question_id),
    ).fetchone()
    if existing:
        return
    max_order = conn.execute(
        "SELECT COALESCE(MAX(order_index),0) FROM session_questions WHERE session_id=?",
        (session_id,),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO session_questions (session_id, question_id, order_index) VALUES (?,?,?)",
        (session_id, question_id, max_order + 1),
    )
    conn.commit()


def remove_question_from_session(conn: sqlite3.Connection, session_id: int, question_id: int) -> None:
    conn.execute(
        "DELETE FROM session_questions WHERE session_id=? AND question_id=?",
        (session_id, question_id),
    )
    conn.commit()


def get_session_questions(conn: sqlite3.Connection, session_id: int) -> List[Dict]:
    rows = conn.execute(
        """SELECT sq.*, q.question_text, q.context, q.hint, q.sample_answer,
                  q.discussion_points, q.follow_up_questions, q.level, q.question_type,
                  t.name AS topic_name, ag.label AS age_group_label
           FROM session_questions sq
           JOIN questions q  ON q.id  = sq.question_id
           JOIN topics t     ON t.id  = q.topic_id
           JOIN age_groups ag ON ag.id = q.age_group_id
           WHERE sq.session_id = ?
           ORDER BY sq.order_index""",
        (session_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["discussion_points"]   = json.loads(d.get("discussion_points") or "[]")
        d["follow_up_questions"] = json.loads(d.get("follow_up_questions") or "[]")
        result.append(d)
    return result


def mark_question_used(conn: sqlite3.Connection, sq_id: int, notes: str = "") -> None:
    conn.execute(
        "UPDATE session_questions SET was_used=1, facilitator_notes=? WHERE id=?",
        (notes, sq_id),
    )
    conn.commit()


def reorder_session_questions(conn: sqlite3.Connection, session_id: int, ordered_ids: List[int]) -> None:
    for i, qid in enumerate(ordered_ids):
        conn.execute(
            "UPDATE session_questions SET order_index=? WHERE session_id=? AND question_id=?",
            (i, session_id, qid),
        )
    conn.commit()


# ── Stats ──────────────────────────────────────────────────────────────────────

def get_stats(conn: sqlite3.Connection) -> Dict:
    total_q    = conn.execute("SELECT COUNT(*) FROM questions WHERE is_active=1").fetchone()[0]
    total_favs = conn.execute("SELECT COUNT(*) FROM questions WHERE is_active=1 AND is_favourite=1").fetchone()[0]
    total_s    = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    by_topic = [
        dict(r) for r in conn.execute(
            """SELECT t.name, COUNT(q.id) AS cnt
               FROM topics t LEFT JOIN questions q ON q.topic_id=t.id AND q.is_active=1
               GROUP BY t.id ORDER BY cnt DESC"""
        )
    ]
    by_age = [
        dict(r) for r in conn.execute(
            """SELECT ag.label, COUNT(q.id) AS cnt
               FROM age_groups ag LEFT JOIN questions q ON q.age_group_id=ag.id AND q.is_active=1
               GROUP BY ag.id ORDER BY ag.min_age"""
        )
    ]
    by_level = dict(conn.execute(
        "SELECT level, COUNT(*) FROM questions WHERE is_active=1 GROUP BY level"
    ).fetchall())
    return {
        "total_questions":   total_q,
        "total_favourites":  total_favs,
        "total_sessions":    total_s,
        "by_topic":          by_topic,
        "by_age":            by_age,
        "by_level":          by_level,
    }
