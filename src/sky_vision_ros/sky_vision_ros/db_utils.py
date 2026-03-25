# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/db_utils.py
"""
db_utils.py
Multi-table SQLite schema creation, upsert operations, event insertion,
lifecycle state updates, and duplicate matching.
Used by: database_logger_node.

Tables:
  orchards            - registered orchards
  plants              - registered plants (trees)
  tracked_objects     - one stable row per unique detected object
  detection_events    - one row per detection observation
  size_measurements   - one row per size estimate (time series)
  action_poses        - saved inspect and pick approach poses
  task_events         - one row per task attempt and outcome
"""
import sqlite3
import os


def get_connection(db_path: str) -> sqlite3.Connection:
    path = os.path.expanduser(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)


def init_schema(db_path: str) -> None:
    """Creates all tables if they do not already exist."""
    with get_connection(db_path) as conn:
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS orchards (
            orchard_id   TEXT PRIMARY KEY,
            orchard_name TEXT,
            crop_type    TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS plants (
            plant_id     TEXT PRIMARY KEY,
            plant_name   TEXT,
            orchard_id   TEXT,
            row_id       TEXT,
            plant_index  INTEGER,
            x_m          REAL,
            y_m          REAL,
            z_m          REAL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS tracked_objects (
            object_id              TEXT PRIMARY KEY,
            object_name            TEXT,
            class_id               INTEGER,
            class_name             TEXT,
            orchard_id             TEXT,
            row_id                 TEXT,
            plant_id               TEXT,
            plant_name             TEXT,
            health_status          TEXT DEFAULT 'unknown',
            object_status          TEXT DEFAULT 'new',
            orchard_lps_x_m        REAL,
            orchard_lps_y_m        REAL,
            orchard_lps_z_m        REAL,
            plant_relative_x_m     REAL,
            plant_relative_y_m     REAL,
            plant_relative_z_m     REAL,
            latitude               REAL,
            longitude              REAL,
            altitude_m             REAL,
            preferred_access_mode  TEXT DEFAULT 'top',
            estimated_size_mm      REAL,
            first_seen_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
            picked_at              DATETIME,
            missed_at              DATETIME
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS detection_events (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id              TEXT,
            event_timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
            task_type              TEXT,
            view_mode              TEXT,
            bbox_x1_px             INTEGER,
            bbox_y1_px             INTEGER,
            bbox_x2_px             INTEGER,
            bbox_y2_px             INTEGER,
            image_width_px         INTEGER,
            image_height_px        INTEGER,
            confidence             REAL,
            health_status          TEXT,
            estimated_size_mm      REAL,
            distance_from_lens_m   REAL,
            latitude               REAL,
            longitude              REAL,
            altitude_m             REAL,
            orchard_lps_x_m        REAL,
            orchard_lps_y_m        REAL,
            orchard_lps_z_m        REAL,
            plant_relative_x_m     REAL,
            plant_relative_y_m     REAL,
            plant_relative_z_m     REAL
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS size_measurements (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id            TEXT,
            measurement_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            estimated_size_mm    REAL,
            size_method          TEXT,
            confidence           REAL,
            source_event_id      INTEGER
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS action_poses (
            object_id               TEXT PRIMARY KEY,
            inspect_top_x_m         REAL,
            inspect_top_y_m         REAL,
            inspect_top_z_m         REAL,
            inspect_top_yaw         REAL,
            inspect_side_x_m        REAL,
            inspect_side_y_m        REAL,
            inspect_side_z_m        REAL,
            inspect_side_yaw        REAL,
            pick_top_x_m            REAL,
            pick_top_y_m            REAL,
            pick_top_z_m            REAL,
            pick_top_yaw            REAL,
            pick_side_x_m           REAL,
            pick_side_y_m           REAL,
            pick_side_z_m           REAL,
            pick_side_yaw           REAL,
            updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS task_events (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id        TEXT,
            task_timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            task_type        TEXT,
            task_status      TEXT,
            outcome          TEXT,
            notes            TEXT
        )''')

        conn.commit()


def object_exists(db_path: str, object_id: str) -> bool:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM tracked_objects WHERE object_id=?", (object_id,))
        return c.fetchone() is not None


def find_duplicate_object_id(db_path: str, class_name: str,
                              orchard_id: str, lps_x: float,
                              lps_y: float, lps_z: float,
                              max_distance_m: float) -> str:
    """
    Searches for an existing tracked object of the same class within max_distance_m.
    Returns the matching object_id or empty string.
    """
    import math
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""SELECT object_id, orchard_lps_x_m, orchard_lps_y_m, orchard_lps_z_m
                     FROM tracked_objects
                     WHERE class_name=? AND orchard_id=?""",
                  (class_name, orchard_id))
        rows = c.fetchall()
    for row in rows:
        oid, ex, ey, ez = row
        dist = math.sqrt((lps_x-ex)**2 + (lps_y-ey)**2 + (lps_z-ez)**2)
        if dist <= max_distance_m:
            return oid
    return ''


def upsert_tracked_object(db_path: str, obj: dict) -> None:
    """Inserts or updates a tracked object row."""
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO tracked_objects (
            object_id, object_name, class_id, class_name,
            orchard_id, row_id, plant_id, plant_name,
            health_status, object_status,
            orchard_lps_x_m, orchard_lps_y_m, orchard_lps_z_m,
            plant_relative_x_m, plant_relative_y_m, plant_relative_z_m,
            latitude, longitude, altitude_m,
            preferred_access_mode, estimated_size_mm,
            first_seen_at, last_seen_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
        ON CONFLICT(object_id) DO UPDATE SET
            health_status         = excluded.health_status,
            object_status         = excluded.object_status,
            estimated_size_mm     = excluded.estimated_size_mm,
            last_seen_at          = CURRENT_TIMESTAMP
        """, (
            obj['object_id'], obj.get('object_name',''), obj.get('class_id',0),
            obj['class_name'],
            obj.get('orchard_id',''), obj.get('row_id',''),
            obj.get('plant_id',''), obj.get('plant_name',''),
            obj.get('health_status','unknown'), obj.get('object_status','new'),
            obj.get('orchard_lps_x_m',0.0), obj.get('orchard_lps_y_m',0.0),
            obj.get('orchard_lps_z_m',0.0),
            obj.get('plant_relative_x_m',0.0), obj.get('plant_relative_y_m',0.0),
            obj.get('plant_relative_z_m',0.0),
            obj.get('latitude',0.0), obj.get('longitude',0.0),
            obj.get('altitude_m',0.0),
            obj.get('preferred_access_mode','top'),
            obj.get('estimated_size_mm',0.0)
        ))
        conn.commit()


def insert_detection_event(db_path: str, ev: dict) -> int:
    """Inserts a detection event and returns its row id."""
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO detection_events (
            object_id, task_type, view_mode,
            bbox_x1_px, bbox_y1_px, bbox_x2_px, bbox_y2_px,
            image_width_px, image_height_px,
            confidence, health_status, estimated_size_mm,
            distance_from_lens_m,
            latitude, longitude, altitude_m,
            orchard_lps_x_m, orchard_lps_y_m, orchard_lps_z_m,
            plant_relative_x_m, plant_relative_y_m, plant_relative_z_m
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            ev.get('object_id',''), ev.get('task_type',''), ev.get('view_mode',''),
            ev.get('bbox_x1_px',0), ev.get('bbox_y1_px',0),
            ev.get('bbox_x2_px',0), ev.get('bbox_y2_px',0),
            ev.get('image_width_px',0), ev.get('image_height_px',0),
            ev.get('confidence',0.0), ev.get('health_status','unknown'),
            ev.get('estimated_size_mm',0.0), ev.get('distance_from_lens_m',0.0),
            ev.get('latitude',0.0), ev.get('longitude',0.0), ev.get('altitude_m',0.0),
            ev.get('orchard_lps_x_m',0.0), ev.get('orchard_lps_y_m',0.0),
            ev.get('orchard_lps_z_m',0.0),
            ev.get('plant_relative_x_m',0.0), ev.get('plant_relative_y_m',0.0),
            ev.get('plant_relative_z_m',0.0)
        ))
        conn.commit()
        return c.lastrowid


def insert_size_measurement(db_path: str, object_id: str,
                             size_mm: float, method: str,
                             confidence: float, source_event_id: int) -> None:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO size_measurements
            (object_id, estimated_size_mm, size_method, confidence, source_event_id)
            VALUES (?,?,?,?,?)""",
                  (object_id, size_mm, method, confidence, source_event_id))
        conn.commit()


def insert_task_event(db_path: str, object_id: str, task_type: str,
                      task_status: str, outcome: str, notes: str = '') -> None:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO task_events
            (object_id, task_type, task_status, outcome, notes)
            VALUES (?,?,?,?,?)""",
                  (object_id, task_type, task_status, outcome, notes))
        conn.commit()


def update_object_status(db_path: str, object_id: str, new_status: str) -> None:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("UPDATE tracked_objects SET object_status=?, last_seen_at=CURRENT_TIMESTAMP WHERE object_id=?",
                  (new_status, object_id))
        conn.commit()


def get_object_status(db_path: str, object_id: str) -> str:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT object_status FROM tracked_objects WHERE object_id=?", (object_id,))
        row = c.fetchone()
        return row[0] if row else ''


def upsert_action_poses(db_path: str, object_id: str, poses: dict) -> None:
    with get_connection(db_path) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO action_poses (
            object_id,
            inspect_top_x_m, inspect_top_y_m, inspect_top_z_m, inspect_top_yaw,
            inspect_side_x_m, inspect_side_y_m, inspect_side_z_m, inspect_side_yaw,
            pick_top_x_m, pick_top_y_m, pick_top_z_m, pick_top_yaw,
            pick_side_x_m, pick_side_y_m, pick_side_z_m, pick_side_yaw
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(object_id) DO UPDATE SET
            inspect_top_x_m  = excluded.inspect_top_x_m,
            inspect_top_y_m  = excluded.inspect_top_y_m,
            inspect_top_z_m  = excluded.inspect_top_z_m,
            inspect_top_yaw  = excluded.inspect_top_yaw,
            inspect_side_x_m = excluded.inspect_side_x_m,
            inspect_side_y_m = excluded.inspect_side_y_m,
            inspect_side_z_m = excluded.inspect_side_z_m,
            inspect_side_yaw = excluded.inspect_side_yaw,
            pick_top_x_m     = excluded.pick_top_x_m,
            pick_top_y_m     = excluded.pick_top_y_m,
            pick_top_z_m     = excluded.pick_top_z_m,
            pick_top_yaw     = excluded.pick_top_yaw,
            pick_side_x_m    = excluded.pick_side_x_m,
            pick_side_y_m    = excluded.pick_side_y_m,
            pick_side_z_m    = excluded.pick_side_z_m,
            pick_side_yaw    = excluded.pick_side_yaw,
            updated_at       = CURRENT_TIMESTAMP
        """, (
            object_id,
            poses.get('inspect_top_x',0.0), poses.get('inspect_top_y',0.0),
            poses.get('inspect_top_z',0.0), poses.get('inspect_top_yaw',0.0),
            poses.get('inspect_side_x',0.0), poses.get('inspect_side_y',0.0),
            poses.get('inspect_side_z',0.0), poses.get('inspect_side_yaw',0.0),
            poses.get('pick_top_x',0.0), poses.get('pick_top_y',0.0),
            poses.get('pick_top_z',0.0), poses.get('pick_top_yaw',0.0),
            poses.get('pick_side_x',0.0), poses.get('pick_side_y',0.0),
            poses.get('pick_side_z',0.0), poses.get('pick_side_yaw',0.0),
        ))
        conn.commit()
