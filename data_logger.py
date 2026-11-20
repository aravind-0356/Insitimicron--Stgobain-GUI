# data_logger.py
"""
Data logging engine for the Pi HMI.
Handles:
  - SQLite database for storing test runs and sensor data points
  - CSV export to local storage or USB drive
  - Test metadata (start time, duration, sample ID)

Design Decisions:
  - SQLite is used because it's file-based (no server), crash-safe with WAL mode,
    and can handle thousands of inserts/second — far exceeding our 100Hz data rate.
  - We use a write-ahead log (WAL) journal mode for concurrent reads during active writes.
  - Batch inserts are used (every 100 points) to minimize disk I/O on the SD card.
  - CSV export reads from the DB, not from memory, so exports are safe even after a crash.
"""

import os
import csv
import time
import sqlite3
import threading
import shutil
import platform
from datetime import datetime

import pandas as pd

def log_kiosk_status(msg):
    """Appends to the persistent kiosk_status.log for offline diagnostics."""
    kiosk_data_dir = "/mnt/data"
    log_path = os.path.join(kiosk_data_dir, "kiosk_status.log") if platform.system() == "Linux" and os.path.isdir(kiosk_data_dir) else "kiosk_status.log"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


# =========================================================
# DATABASE SCHEMA
# =========================================================
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tests (
    test_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    test_mode        TEXT    NOT NULL DEFAULT 'TEST',
    started_at       TEXT    NOT NULL,
    ended_at         TEXT,
    duration_s       REAL,
    notes            TEXT    DEFAULT '',
    sample_name      TEXT    DEFAULT '',
    test_number      TEXT    DEFAULT '',
    business_type    TEXT    DEFAULT '',
    length_mm        REAL,
    width_mm         REAL,
    thickness_mm     REAL,
    constant_load_n  REAL,
    target_heat_rate REAL,
    calibration_file TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS data_points (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id     INTEGER NOT NULL,
    timestamp_s REAL    NOT NULL,
    temp_val    REAL    NOT NULL,
    raw_disp    REAL    NOT NULL,
    comp_disp   REAL    NOT NULL,
    FOREIGN KEY (test_id) REFERENCES tests(test_id)
);

CREATE INDEX IF NOT EXISTS idx_dp_test ON data_points(test_id);
"""


class DataLogger:
    """Thread-safe data logger backed by SQLite."""

    def __init__(self, db_path=None):
        """
        Args:
            db_path: Path to the SQLite database file.
        """
        if db_path is None:
            # On Raspberry Pi (Linux) kiosk, use the dedicated persistent data partition
            kiosk_data_dir = "/mnt/data"
            if platform.system() == "Linux" and os.path.isdir(kiosk_data_dir):
                db_path = os.path.join(kiosk_data_dir, "mtr_data.db")
            else:
                db_path = os.path.join(os.path.dirname(__file__), "mtr_data.db")
                
        self.db_path = db_path

        self._lock = threading.Lock()
        self._conn = None
        self._current_test_id = None
        self._start_time = 0.0

        # Batch buffer for insert performance
        self._batch_buffer = []
        self._batch_size = 100  # Flush every 100 data points

        self._backup_db()
        self._init_db()

    def _backup_db(self):
        """Creates a rolling backup of the database to protect against FTL corruption on power loss."""
        if not os.path.exists(self.db_path):
            return
            
        try:
            # Keep up to 3 rotating backups
            for i in range(2, 0, -1):
                src = f"{self.db_path}.bak{i}"
                dst = f"{self.db_path}.bak{i+1}"
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, f"{self.db_path}.bak1")
        except Exception as e:
            print(f"Failed to backup database: {e}")

    def _init_db(self):
        """Create the database and tables if they don't exist."""
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=FULL;")
        self._conn.executescript(_SCHEMA_SQL)
        
        # Safely migrate existing databases
        try:
            self._conn.execute("ALTER TABLE tests ADD COLUMN business_type TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        self._conn.commit()
        self._auto_recover_tests()

    def _auto_recover_tests(self):
        """Find tests with ended_at IS NULL (from a crash/power loss) and close them."""
        # Get all interrupted tests
        cursor = self._conn.cursor()
        cursor.execute("SELECT test_id FROM tests WHERE ended_at IS NULL")
        interrupted_tests = cursor.fetchall()
        
        if not interrupted_tests:
            return
            
        ended_at = datetime.now().isoformat()
        
        for (t_id,) in interrupted_tests:
            # Calculate duration based on the last data point if possible
            cursor.execute("SELECT MAX(timestamp_s) FROM data_points WHERE test_id=?", (t_id,))
            row = cursor.fetchone()
            duration_s = row[0] if row[0] is not None else 0.0
            
            # Close the test
            cursor.execute(
                "UPDATE tests SET ended_at=?, duration_s=?, name=name || '_RECOVERED' WHERE test_id=?",
                (ended_at, duration_s, t_id)
            )
            print(f"Auto-recovered interrupted test {t_id}")
            
        self._conn.commit()

    # =========================================================
    # TEST LIFECYCLE
    # =========================================================

    def start_test(self, name="", sample_params=None):
        """
        Begin a new test. Returns the test_id.
        Args:
            name: Human-readable test name (e.g., "Sample_A_Run_3")
            sample_params: dict with keys: sample_name, test_number,
                           length_mm, width_mm, thickness_mm, temperature_c
        """
        if not name:
            name = f"Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if sample_params is None:
            sample_params = {}

        started_at = datetime.now().isoformat()
        self._start_time = time.time()

        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO tests "
                "(name, test_mode, started_at, notes, sample_name, test_number, business_type, "
                " length_mm, width_mm, thickness_mm, constant_load_n, target_heat_rate, calibration_file) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name, 
                    sample_params.get("test_mode", "TEST"),
                    started_at,
                    sample_params.get("remarks", sample_params.get("notes", "")),
                    sample_params.get("sample_name", ""),
                    sample_params.get("test_number", ""),
                    sample_params.get("business_type", ""),
                    sample_params.get("length_mm"),
                    sample_params.get("width_mm"),
                    sample_params.get("thickness_mm"),
                    sample_params.get("constant_load_n"),
                    sample_params.get("target_heat_rate"),
                    sample_params.get("calibration_file", "")
                )
            )
            self._conn.commit()
            self._current_test_id = cur.lastrowid
            self._batch_buffer = []

        return self._current_test_id

    def stop_test(self):
        """End the current test. Flushes any buffered data and records duration."""
        if self._current_test_id is None:
            return

        # Flush remaining batch
        self._flush_batch()

        duration = time.time() - self._start_time
        ended_at = datetime.now().isoformat()

        with self._lock:
            self._conn.execute(
                "UPDATE tests SET ended_at=?, duration_s=? WHERE test_id=?",
                (ended_at, duration, self._current_test_id)
            )
            self._conn.commit()

        test_id = self._current_test_id
        self._current_test_id = None
        return test_id

    # =========================================================
    # DATA RECORDING
    # =========================================================

    def log_data_point(self, timestamp_s, temp_val, raw_disp, comp_disp):
        """
        Buffer a data point for the current test.
        Automatically flushes to disk when batch_size is reached.
        """
        if self._current_test_id is None:
            return

        with self._lock:
            self._batch_buffer.append((self._current_test_id, timestamp_s, temp_val, raw_disp, comp_disp))
            if len(self._batch_buffer) >= self._batch_size:
                self._flush_batch_unlocked()

    def _flush_batch(self):
        """Write the buffered batch to the database."""
        with self._lock:
            self._flush_batch_unlocked()
            
    def _flush_batch_unlocked(self):
        if not self._batch_buffer:
            return

        self._conn.executemany(
            "INSERT INTO data_points (test_id, timestamp_s, temp_val, raw_disp, comp_disp) VALUES (?, ?, ?, ?, ?)",
            self._batch_buffer
        )
        self._conn.commit()
        self._batch_buffer = []

    # =========================================================
    # DATA RETRIEVAL
    # =========================================================

    def get_all_tests(self):
        """
        Returns a list of all tests as dicts with all columns including sample params.
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT test_id, name, test_mode, started_at, ended_at, duration_s, notes, "
                "       sample_name, test_number, business_type, length_mm, width_mm, "
                "       thickness_mm, constant_load_n, target_heat_rate, calibration_file "
                "FROM tests ORDER BY test_id DESC"
            )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_test_data(self, test_id):
        """
        Returns all data points for a given test as (timestamps[], loads[], disps[]).
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT timestamp_s, temp_val, raw_disp, comp_disp FROM data_points "
                "WHERE test_id=? ORDER BY timestamp_s",
                (test_id,)
            )
            rows = cur.fetchall()

        if not rows:
            return [], [], [], []
        timestamps, temps, raw_disps, comp_disps = zip(*rows)
        return list(timestamps), list(temps), list(raw_disps), list(comp_disps)

    def get_test_data_as_dataframe(self, test_id):
        """Returns test data as a Pandas DataFrame for analysis."""
        with self._lock:
            df = pd.read_sql_query(
                "SELECT timestamp_s, temp_val, raw_disp, comp_disp FROM data_points "
                "WHERE test_id=? ORDER BY timestamp_s",
                self._conn,
                params=(test_id,)
            )
        return df

    # =========================================================
    # CSV EXPORT
    # =========================================================

    def export_test_to_csv(self, test_id, output_path, yield_callback=None):
        """
        Export a single test's data to a CSV file.
        Args:
            test_id: The test to export.
            output_path: Full path to the output CSV file.
            yield_callback: Optional function to call periodically (e.g. processEvents)
        Returns:
            Number of rows written, or -1 on error.
        """
        try:
            timestamps, temps, raw_disps, comp_disps = self.get_test_data(test_id)
            if not timestamps:
                return 0

            # Get test metadata for the header (including sample params and remarks)
            with self._lock:
                cur = self._conn.execute(
                    "SELECT name, started_at, duration_s, "
                    "       sample_name, test_number, business_type, length_mm, "
                    "       width_mm, thickness_mm, constant_load_n, target_heat_rate, calibration_file, test_mode, notes "
                    "FROM tests WHERE test_id=?",
                    (test_id,)
                )
                test_info = cur.fetchone()

            dir_name = os.path.dirname(output_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Metadata header with sample parameters
                if test_info:
                    writer.writerow([f"# Test: {test_info[0]}"])
                    writer.writerow([f"# Mode: {test_info[12]}"])
                    writer.writerow([f"# Duration: {test_info[2]:.2f}s" if test_info[2] else "# Duration: N/A"])
                    if test_info[3]:  # sample_name
                        writer.writerow([f"# Sample Name: {test_info[3]}"])
                    if test_info[4]:  # test_number
                        writer.writerow([f"# Test Number: {test_info[4]}"])
                    if test_info[5]:  # business_type
                        writer.writerow([f"# Business Type: {test_info[5]}"])
                    if test_info[6] is not None:  # length_mm
                        writer.writerow([f"# Span Length (mm): {test_info[6]}"])
                    if test_info[7] is not None:  # width_mm
                        writer.writerow([f"# Width (mm): {test_info[7]}"])
                    if test_info[8] is not None:  # thickness_mm
                        writer.writerow([f"# Height (mm): {test_info[8]}"])
                    if test_info[9] is not None:  # constant_load_n
                        writer.writerow([f"# Constant Load (N): {test_info[9]}"])
                    if test_info[10] is not None:  # target_heat_rate
                        writer.writerow([f"# Target Heat Rate (C/min): {test_info[10]}"])
                    if test_info[11]:  # calibration_file
                        writer.writerow([f"# Calibration File: {test_info[11]}"])
                    if len(test_info) > 13 and test_info[13]:  # notes / remarks
                        writer.writerow([f"# Remarks: {test_info[13]}"])
                    writer.writerow([])

                # Column headers
                writer.writerow(["Time(s)", "Temperature(C)", "Raw_Displacement(mm)", "Comp_Displacement(mm)"])

                # Data rows
                for idx, (t, temp, raw, comp) in enumerate(zip(timestamps, temps, raw_disps, comp_disps)):
                    writer.writerow([f"{t:.4f}", f"{temp:.2f}", f"{raw:.6f}", f"{comp:.6f}"])
                    if yield_callback and idx % 1000 == 0:
                        yield_callback()
                
                # Critical: Force OS to flush buffers to the physical USB drive
                f.flush()
                os.fsync(f.fileno())

            return len(timestamps)
        except Exception as e:
            print(f"CSV Export Error: {e}")
            raise e

    def export_test_to_usb(self, test_id, usb_mount_path):
        """
        Export a test to a USB drive.
        Args:
            test_id: The test to export.
            usb_mount_path: Mount path of the USB drive (e.g., /media/usb0 on Pi,
                            or D:/ on Windows).
        Returns:
            The full path of the exported CSV, or None on error.
        """
        # Get test name and mode for filename and folder routing
        with self._lock:
            cur = self._conn.execute(
                "SELECT name, test_mode FROM tests WHERE test_id=?", (test_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        test_name = row[0].replace(" ", "_").replace("/", "-")
        test_mode = row[1] if len(row) > 1 and row[1] else "TEST"
        subfolder = "calibrations" if test_mode == "CALIBRATION" else "tests"
        target_dir = os.path.join(usb_mount_path, subfolder)
        os.makedirs(target_dir, exist_ok=True)

        filename = f"{test_name}.csv"
        output_path = os.path.join(target_dir, filename)

        rows = self.export_test_to_csv(test_id, output_path)
        if rows >= 0:
            return output_path
        return None

    # =========================================================
    # CLEANUP
    # =========================================================

    def delete_test(self, test_id):
        """Delete a test and all its data points from the database."""
        with self._lock:
            self._conn.execute("DELETE FROM data_points WHERE test_id=?", (test_id,))
            self._conn.execute("DELETE FROM tests WHERE test_id=?", (test_id,))
            self._conn.commit()

    def close(self):
        """Flush any pending data and close the database connection."""
        self._flush_batch()
        if self._conn:
            self._conn.close()
            self._conn = None
