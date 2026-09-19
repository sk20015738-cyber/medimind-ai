"""
MediMind AI - Database Manager (db.py)
Zero external dependencies, built using standard Python sqlite3.
Handles medications, schedules, intake logs, and user profile management.
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = DB_DIR / "medimind.db"


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with foreign keys enabled and row_factory set."""
    target_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    conn = sqlite3.connect(str(target_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str | Path] = None, force_reset: bool = False) -> None:
    """Initializes the database tables and populates default seed data if empty."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    if force_reset:
        cur.execute("DROP TABLE IF EXISTS intake_logs")
        cur.execute("DROP TABLE IF EXISTS schedules")
        cur.execute("DROP TABLE IF EXISTS medications")
        cur.execute("DROP TABLE IF EXISTS user_profile")

    # 1. Medications table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            dosage TEXT NOT NULL,
            frequency TEXT NOT NULL,
            meal_timing TEXT NOT NULL,
            category TEXT NOT NULL,
            instructions TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    # 2. Schedules table (foreign key to medications)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            time_slot TEXT NOT NULL,
            specific_time TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (medication_id) REFERENCES medications(id) ON DELETE CASCADE
        )
    """)

    # 3. Intake logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS intake_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medication_id INTEGER NOT NULL,
            scheduled_date TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            status TEXT NOT NULL,
            logged_at TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY (medication_id) REFERENCES medications(id) ON DELETE CASCADE
        )
    """)

    # 4. User profile table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 68,
            conditions TEXT DEFAULT '',
            senior_mode INTEGER DEFAULT 1,
            notification_enabled INTEGER DEFAULT 1
        )
    """)

    conn.commit()

    # Check if seed data is needed
    cur.execute("SELECT COUNT(*) FROM medications")
    med_count = cur.fetchone()[0]

    if med_count == 0:
        seed_default_data(conn)

    conn.close()


def seed_default_data(conn: sqlite3.Connection) -> None:
    """Populates realistic seed data for testing & demonstrations."""
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()

    # Seed User Profile
    cur.execute("""
        INSERT INTO user_profile (name, age, conditions, senior_mode, notification_enabled)
        VALUES (?, ?, ?, ?, ?)
    """, ("김정숙", 68, "고혈압, 당뇨병", 1, 1))

    # Seed 3 realistic medications
    # 1. 혈압약: 노바스크정 5mg (암로디핀)
    cur.execute("""
        INSERT INTO medications (name, dosage, frequency, meal_timing, category, instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "노바스크정",
        "5mg",
        "1일 1회",
        "식후 30분",
        "혈압약",
        "자몽주스와 함께 드시지 마세요. 아침 기상 후 일정한 시간에 복용하세요.",
        now_iso
    ))
    med1_id = cur.lastrowid
    cur.execute("""
        INSERT INTO schedules (medication_id, time_slot, specific_time, is_active)
        VALUES (?, ?, ?, 1)
    """, (med1_id, "아침", "08:00"))

    # 2. 당뇨약: 메트포르민정 500mg
    cur.execute("""
        INSERT INTO medications (name, dosage, frequency, meal_timing, category, instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "메트포르민정",
        "500mg",
        "1일 2회",
        "식사 직후",
        "당뇨약",
        "위장장애(속쓰림, 메스꺼움) 예방을 위해 식사 도중이나 식사 직후 바로 복용하세요.",
        now_iso
    ))
    med2_id = cur.lastrowid
    cur.execute("""
        INSERT INTO schedules (medication_id, time_slot, specific_time, is_active)
        VALUES (?, ?, ?, 1), (?, ?, ?, 1)
    """, (med2_id, "아침", "08:30", med2_id, "저녁", "19:00"))

    # 3. 위장약: 파모티딘정 20mg
    cur.execute("""
        INSERT INTO medications (name, dosage, frequency, meal_timing, category, instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "파모티딘정",
        "20mg",
        "1일 1회",
        "식후 30분",
        "위장약",
        "야간 위산 분비 억제 및 속쓰림 완화를 위해 저녁 식후 복용 권장.",
        now_iso
    ))
    med3_id = cur.lastrowid
    cur.execute("""
        INSERT INTO schedules (medication_id, time_slot, specific_time, is_active)
        VALUES (?, ?, ?, 1)
    """, (med3_id, "저녁", "19:30"))

    # Seed intake logs for past 3 days and today
    today = datetime.now().date()
    for days_ago in range(3, -1, -1):
        log_date = (today - timedelta(days=days_ago)).isoformat()
        log_time_str = f"{log_date}T"

        # Med 1: 노바스크 08:00
        cur.execute("""
            INSERT INTO intake_logs (medication_id, scheduled_date, scheduled_time, status, logged_at, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (med1_id, log_date, "08:00", "taken", log_time_str + "08:05:12", "정상 복용 완료"))

        # Med 2: 메트포르민 아침 08:30
        cur.execute("""
            INSERT INTO intake_logs (medication_id, scheduled_date, scheduled_time, status, logged_at, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (med2_id, log_date, "08:30", "taken", log_time_str + "08:35:40", "식사 직후 복용"))

        # Past days: evening doses taken.
        if days_ago > 0:
            cur.execute("""
                INSERT INTO intake_logs (medication_id, scheduled_date, scheduled_time, status, logged_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (med2_id, log_date, "19:00", "taken", log_time_str + "19:08:00", "저녁 식사 직후"))

            cur.execute("""
                INSERT INTO intake_logs (medication_id, scheduled_date, scheduled_time, status, logged_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (med3_id, log_date, "19:30", "taken", log_time_str + "19:34:10", "저녁 식후 30분"))

    conn.commit()


# ==========================================
# CRUD Operations: Medications & Schedules
# ==========================================

def get_all_medications(db_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Fetches all medications along with their schedules."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM medications ORDER BY id ASC")
    med_rows = cur.fetchall()

    results = []
    for med in med_rows:
        med_dict = dict(med)
        cur.execute("SELECT * FROM schedules WHERE medication_id = ? ORDER BY specific_time ASC", (med["id"],))
        sched_rows = cur.fetchall()
        med_dict["schedules"] = [dict(s) for s in sched_rows]
        results.append(med_dict)

    conn.close()
    return results


def get_medication_by_id(med_id: int, db_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    """Fetches a single medication by ID with its schedules."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM medications WHERE id = ?", (med_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None

    med_dict = dict(row)
    cur.execute("SELECT * FROM schedules WHERE medication_id = ? ORDER BY specific_time ASC", (med_id,))
    sched_rows = cur.fetchall()
    med_dict["schedules"] = [dict(s) for s in sched_rows]
    conn.close()
    return med_dict


def add_medication(
    name: str,
    dosage: str,
    frequency: str,
    meal_timing: str,
    category: str,
    schedules: List[Dict[str, str]],
    instructions: str = "",
    db_path: Optional[str | Path] = None
) -> int:
    """Adds a new medication and its schedule entries."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    created_at = datetime.now().isoformat()

    cur.execute("""
        INSERT INTO medications (name, dosage, frequency, meal_timing, category, instructions, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, dosage, frequency, meal_timing, category, instructions, created_at))

    med_id = cur.lastrowid

    for sched in schedules:
        time_slot = sched.get("time_slot", "아침")
        specific_time = sched.get("specific_time", "08:00")
        is_active = sched.get("is_active", 1)
        cur.execute("""
            INSERT INTO schedules (medication_id, time_slot, specific_time, is_active)
            VALUES (?, ?, ?, ?)
        """, (med_id, time_slot, specific_time, is_active))

    conn.commit()
    conn.close()
    return med_id


def update_medication(
    med_id: int,
    name: Optional[str] = None,
    dosage: Optional[str] = None,
    frequency: Optional[str] = None,
    meal_timing: Optional[str] = None,
    category: Optional[str] = None,
    instructions: Optional[str] = None,
    schedules: Optional[List[Dict[str, str]]] = None,
    db_path: Optional[str | Path] = None
) -> bool:
    """Updates a medication and optionally replaces schedules."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM medications WHERE id = ?", (med_id,))
    if not cur.fetchone():
        conn.close()
        return False

    update_fields = []
    params = []
    if name is not None:
        update_fields.append("name = ?")
        params.append(name)
    if dosage is not None:
        update_fields.append("dosage = ?")
        params.append(dosage)
    if frequency is not None:
        update_fields.append("frequency = ?")
        params.append(frequency)
    if meal_timing is not None:
        update_fields.append("meal_timing = ?")
        params.append(meal_timing)
    if category is not None:
        update_fields.append("category = ?")
        params.append(category)
    if instructions is not None:
        update_fields.append("instructions = ?")
        params.append(instructions)

    if update_fields:
        params.append(med_id)
        cur.execute(f"UPDATE medications SET {', '.join(update_fields)} WHERE id = ?", params)

    if schedules is not None:
        cur.execute("DELETE FROM schedules WHERE medication_id = ?", (med_id,))
        for sched in schedules:
            time_slot = sched.get("time_slot", "아침")
            specific_time = sched.get("specific_time", "08:00")
            is_active = sched.get("is_active", 1)
            cur.execute("""
                INSERT INTO schedules (medication_id, time_slot, specific_time, is_active)
                VALUES (?, ?, ?, ?)
            """, (med_id, time_slot, specific_time, is_active))

    conn.commit()
    conn.close()
    return True


def delete_medication(med_id: int, db_path: Optional[str | Path] = None) -> bool:
    """Deletes a medication and cascades deletes to schedules and logs."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM medications WHERE id = ?", (med_id,))
    if not cur.fetchone():
        conn.close()
        return False

    cur.execute("DELETE FROM intake_logs WHERE medication_id = ?", (med_id,))
    cur.execute("DELETE FROM schedules WHERE medication_id = ?", (med_id,))
    cur.execute("DELETE FROM medications WHERE id = ?", (med_id,))

    conn.commit()
    conn.close()
    return True


# ==========================================
# CRUD Operations: Intake Logs
# ==========================================

def add_intake_log(
    medication_id: int,
    scheduled_date: str,
    scheduled_time: str,
    status: str,
    notes: str = "",
    logged_at: Optional[str] = None,
    db_path: Optional[str | Path] = None
) -> int:
    """Records an intake action ('taken', 'skipped', 'snoozed')."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    if not logged_at:
        logged_at = datetime.now().isoformat()

    # Check if a log already exists for this medication, date, and scheduled_time
    cur.execute("""
        SELECT id FROM intake_logs 
        WHERE medication_id = ? AND scheduled_date = ? AND scheduled_time = ?
    """, (medication_id, scheduled_date, scheduled_time))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE intake_logs 
            SET status = ?, logged_at = ?, notes = ?
            WHERE id = ?
        """, (status, logged_at, notes, existing["id"]))
        log_id = existing["id"]
    else:
        cur.execute("""
            INSERT INTO intake_logs (medication_id, scheduled_date, scheduled_time, status, logged_at, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (medication_id, scheduled_date, scheduled_time, status, logged_at, notes))
        log_id = cur.lastrowid

    conn.commit()
    conn.close()
    return log_id


def get_intake_logs(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    medication_id: Optional[int] = None,
    db_path: Optional[str | Path] = None
) -> List[Dict[str, Any]]:
    """Queries intake logs with optional date and medication filters."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = """
        SELECT l.*, m.name as medication_name, m.dosage, m.meal_timing, m.category
        FROM intake_logs l
        JOIN medications m ON l.medication_id = m.id
        WHERE 1=1
    """
    params: List[Any] = []

    if date:
        query += " AND l.scheduled_date = ?"
        params.append(date)
    if start_date:
        query += " AND l.scheduled_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND l.scheduled_date <= ?"
        params.append(end_date)
    if medication_id:
        query += " AND l.medication_id = ?"
        params.append(medication_id)

    query += " ORDER BY l.scheduled_date DESC, l.scheduled_time DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results


def get_adherence_stats(days: int = 7, db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Computes overall medication adherence rate, streak, and daily counts."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    today = datetime.now().date()
    start_date = (today - timedelta(days=days - 1)).isoformat()
    end_date = today.isoformat()

    # Query logs in date range
    cur.execute("""
        SELECT status, scheduled_date 
        FROM intake_logs 
        WHERE scheduled_date >= ? AND scheduled_date <= ?
    """, (start_date, end_date))
    logs = cur.fetchall()

    total_logs = len(logs)
    taken_count = sum(1 for l in logs if l["status"] == "taken")
    skipped_count = sum(1 for l in logs if l["status"] == "skipped")
    snoozed_count = sum(1 for l in logs if l["status"] == "snoozed")

    adherence_rate = round((taken_count / total_logs * 100), 1) if total_logs > 0 else 100.0

    # Calculate streak (consecutive days with at least one taken dose and no skipped dose)
    cur.execute("""
        SELECT scheduled_date, 
               SUM(CASE WHEN status = 'taken' THEN 1 ELSE 0 END) as taken_c,
               SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_c
        FROM intake_logs
        GROUP BY scheduled_date
        ORDER BY scheduled_date DESC
    """)
    daily_rows = cur.fetchall()

    daily_dict = {r["scheduled_date"]: (r["taken_c"], r["skipped_c"]) for r in daily_rows}

    streak = 0
    for i in range(30):
        d_str = (today - timedelta(days=i)).isoformat()
        if d_str in daily_dict:
            t, s = daily_dict[d_str]
            if t > 0 and s == 0:
                streak += 1
            elif t > 0 and s > 0:
                # If there's a skip, streak ends
                break
            else:
                break
        else:
            if i == 0:
                # Today not logged yet, continue to count yesterday
                continue
            break

    # Daily breakdown for charts
    daily_breakdown = []
    for i in range(days - 1, -1, -1):
        d_obj = today - timedelta(days=i)
        d_str = d_obj.isoformat()
        label = d_obj.strftime("%m/%d")
        t, s = daily_dict.get(d_str, (0, 0))
        daily_breakdown.append({
            "date": d_str,
            "label": label,
            "taken": t,
            "skipped": s
        })

    conn.close()

    return {
        "period_days": days,
        "adherence_rate": adherence_rate,
        "total_scheduled": total_logs,
        "taken_count": taken_count,
        "skipped_count": skipped_count,
        "snoozed_count": snoozed_count,
        "streak_days": streak,
        "daily_breakdown": daily_breakdown
    }


# ==========================================
# CRUD Operations: User Profile
# ==========================================

def get_user_profile(db_path: Optional[str | Path] = None) -> Dict[str, Any]:
    """Returns the primary user profile."""
    conn = get_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profile LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if row:
        return dict(row)
    return {
        "id": 1,
        "name": "김정숙",
        "age": 68,
        "conditions": "고혈압, 당뇨병",
        "senior_mode": 1,
        "notification_enabled": 1
    }


def update_user_profile(
    name: Optional[str] = None,
    age: Optional[int] = None,
    conditions: Optional[str] = None,
    senior_mode: Optional[int] = None,
    notification_enabled: Optional[int] = None,
    db_path: Optional[str | Path] = None
) -> Dict[str, Any]:
    """Updates user profile settings."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id FROM user_profile LIMIT 1")
    row = cur.fetchone()

    if not row:
        cur.execute("""
            INSERT INTO user_profile (name, age, conditions, senior_mode, notification_enabled)
            VALUES (?, ?, ?, ?, ?)
        """, (name or "김정숙", age or 68, conditions or "고혈압, 당뇨병", 
              senior_mode if senior_mode is not None else 1, 
              notification_enabled if notification_enabled is not None else 1))
    else:
        profile_id = row["id"]
        fields = []
        params = []
        if name is not None:
            fields.append("name = ?")
            params.append(name)
        if age is not None:
            fields.append("age = ?")
            params.append(age)
        if conditions is not None:
            fields.append("conditions = ?")
            params.append(conditions)
        if senior_mode is not None:
            fields.append("senior_mode = ?")
            params.append(senior_mode)
        if notification_enabled is not None:
            fields.append("notification_enabled = ?")
            params.append(notification_enabled)

        if fields:
            params.append(profile_id)
            cur.execute(f"UPDATE user_profile SET {', '.join(fields)} WHERE id = ?", params)

    conn.commit()
    conn.close()
    return get_user_profile(db_path)
