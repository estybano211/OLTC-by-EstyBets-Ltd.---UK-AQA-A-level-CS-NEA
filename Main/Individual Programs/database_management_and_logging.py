import sys
import os
import sqlite3
import pandas as pd
import json
import csv
from datetime import datetime
import logging
from queue import Queue
from threading import Thread, Event

# Database file paths.
BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
DB_PATH = os.path.join(BASE_DIR, "OLTC_database.db")


# LOGGING HANDLERS


class LogHandler(logging.Handler):
    """
    Base class for log handlers.

    Owns all queue, worker-thread, emit, processor and close logic.
    Subclasses supply the name of the table they write to through
    TABLE.

    The worker thread runs as a daemon so it never prevents the process
    from exiting. A stop_event is used to signal clean shutdown.
    """

    TABLE = ""

    def __init__(self):
        """
        Initialises the handler, starts the background worker thread.
        """
        super().__init__()

        self.queue = Queue()
        self.stop_event = Event()
        self.worker_thread = Thread(target=self.processor, daemon=True)
        self.worker_thread.start()

    def emit(self, record):
        """
        Formats the log record and places it on the queue.

        Args:
            record (logging.LogRecord): The log record to process.
        """
        try:
            log_entry = self.format(record)
            level = record.levelname
            timestamp = datetime.now().strftime("%d-%m-%Y | %H:%M:%S")
            self.queue.put((timestamp, level, log_entry))
        except Exception:
            self.handleError(record)

    def processor(self):
        """
        Worker thread: drains the queue and writes each entry to the
        database one at a time to avoid locking contention.

        Runs until stop_event is set. The 1-second get() timeout prevents
        the thread from hanging indefinitely when the queue is empty.
        """
        while not self.stop_event.is_set():
            try:
                timestamp, level, log_entry = self.queue.get(timeout=1)

                with sqlite3.connect(DB_PATH, timeout=5) as conn:
                    conn.execute(
                        f"""
                        INSERT INTO {self.TABLE}(timestamp, level, log_entry)
                        VALUES (?, ?, ?)
                        """,
                        (timestamp, level, log_entry),
                    )
                    conn.commit()

                self.queue.task_done()

            except Exception:
                pass

    def close(self):
        """
        Signals the worker thread to stop, waits for it to finish and then
        calls the parent close method.
        """
        self.stop_event.set()
        self.worker_thread.join()
        super().close()


class DatabaseLogHandler(LogHandler):
    """
    Writes log entries to the 'db_logs' table.
    """

    TABLE = "db_logs"


class AdminLogHandler(LogHandler):
    """
    Writes log entries to the 'admin_logs' table.
    """

    TABLE = "admin_logs"


# LOGGER SETUP


database_logger = logging.getLogger("oltc_db")
database_logger.setLevel(logging.DEBUG)

if not database_logger.handlers:
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(logging.DEBUG)
    db_handler.setFormatter(logging.Formatter("%(message)s"))
    database_logger.addHandler(db_handler)


admin_logger = logging.getLogger("oltc_admin")
admin_logger.setLevel(logging.DEBUG)

if not admin_logger.handlers:
    admin_handler = AdminLogHandler()
    admin_handler.setLevel(logging.DEBUG)
    admin_handler.setFormatter(logging.Formatter("%(message)s"))
    admin_logger.addHandler(admin_handler)


class DatabaseManagement:
    """
    Manages all database creation, connection and data operations.

    Provides methods for creating and viewing the database, registering users, verifying
    passwords, fetching user records, modifying user data.

    Usage:
        dbm = DatabaseManagement(DB_PATH)
        dbm.create_database()
        record = dbm.fetch_user_record(username="user1")
    """

    def __init__(self, db_path):
        """
        Stores the database file path.

        Args:
            db_path (str): Absolute path to the SQLite database file.
                           All methods use this path when connecting.
        """
        self.db_path = db_path

    # SQL DATABASE SCHEMA

    # Defines all database tables and their structure.
    SCHEMA = {
        # Logs of all database access and modifications.
        "db_logs": """
        CREATE TABLE IF NOT EXISTS db_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            log_entry TEXT
        )  
        """,
        # Logs of administrative actions and system events.
        "admin_logs": """
        CREATE TABLE IF NOT EXISTS admin_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT NOT NULL,
            log_entry TEXT
        )
        """,
        # Player account information with balance tracking.
        "users": """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            registered INTEGER,
            balance REAL DEFAULT 10000 CHECK (balance >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
        """,
        # Player statistics.
        "user_poker_data": """
        CREATE TABLE IF NOT EXISTS user_poker_data(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rounds_played INTEGER DEFAULT 0,
            player_range TEXT,
            vpip REAL DEFAULT 0,
            pfr REAL DEFAULT 0,
            total_hands_played INTEGER DEFAULT 0,
            total_hands_raised INTEGER DEFAULT 0,
            total_bets INTEGER DEFAULT 0,
            fold_to_raise INTEGER DEFAULT 0,
            call_when_weak INTEGER DEFAULT 0,
            tournament_wins INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """,
        # Detailed action history for each poker round.
        "user_poker_actions": """
        CREATE TABLE IF NOT EXISTS user_poker_actions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            round_number INTEGER,
            street TEXT,
            action TEXT,
            bet_size REAL,
            pot_size REAL,
            resolved INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """,
    }

    def connect(self):
        """
        Opens and returns a connection to self.db_path with row factory
        and foreign key constraints are enabled.

        Returns:
            sqlite3.Connection: Configured connection object.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def check_database_exists(self):
        """
        Checks if the database file exists in the same directory as the
        program. Constructs the full database path and verifies file existence.

        Returns:
            bool: True if the database file exists, False otherwise.
        """
        return os.path.exists(self.db_path)

    def create_database(self):
        """
        Creates all tables defined in SCHEMA (if they do not already
        exist) and ensures the default Administrator account is present.
        """
        with self.connect() as conn:
            try:
                for name, statement in self.SCHEMA.items():
                    conn.execute(statement)
                    database_logger.info(f"Attempting to create Table: '{name}'.")

                conn.commit()
                database_logger.info(f"Attempting to create File: '{self.db_path}'.")

                self.admin_account()

            except sqlite3.Error as error:
                database_logger.exception(f"'create_database' error. {error}")

    def admin_account(self):
        """
        Inserts the default Administrator account if it does not already
        exist.
        """

        from check_systems import hash_function

        hashed_password = hash_function("Password1")

        with self.connect() as conn:
            try:
                database_logger.info("Attempting to create Administrator account.")
                cursor = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    ("Administrator",),
                )

                if cursor.fetchone() is None:
                    conn.execute(
                        """
                        INSERT INTO users (username, password_hash, registered, balance)
                        VALUES (?, ?, ?, ?)
                        """,
                        ("Administrator", hashed_password, 1, 0.0),
                    )
                    database_logger.info("Administrator account created.")

            except sqlite3.Error as error:
                database_logger.exception(f"'admin_account' error. {error}")

    # ADMIN LOGIN

    def admin_logged_in(self):
        """Logs that the administrator has successfully authenticated."""
        admin_logger.info("Administrator logged in.")

    def admin_accessed_system(self, system):
        """
        Logs that the administrator has accessed a named system.

        Args:
            system (str): The name of the accessed system.
        """
        admin_logger.info(f"Administrator accessed system: '{system}'.")

    # ADMIN PASSWORD MANAGEMENT

    def admin_password_check(self, password):
        """
        Verifies a plaintext password against the stored Administrator hash.

        Args:
            password (str): The plaintext password to verify.

        Returns:
            dict: {'found': bool, 'verified': bool}
        """
        with self.connect() as conn:
            try:
                database_logger.info("Attempting to fetch Administrator password_hash.")

                cursor = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    ("Administrator",),
                )
                row = cursor.fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'admin_password_check' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.debug("Administrator password_hash not found.")
            return {"found": False, "verified": False}

        from check_systems import verify_hash

        verified = verify_hash(row["password_hash"], password)

        database_logger.info(
            "Administrator password verification successful."
            if verified
            else "Administrator password verification failed."
        )

        return {"found": True, "verified": verified}

    def change_admin_password(self, new_password):
        """
        Replaces the Administrator password hash with a newly hashed value.

        Args:
            new_password (str): The new plaintext password to hash and store.
        """
        with self.connect() as conn:
            try:
                admin_logger.info("Request for Administrator password change.")
                database_logger.info("Attempting to change Administrator password.")

                from check_systems import hash_function

                password_hash = hash_function(new_password)

                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (password_hash, "Administrator"),
                )

                database_logger.info("Administrator password changed successfully.")
                admin_logger.info(
                    "Request for Administrator password change successful."
                )

            except sqlite3.Error as error:
                admin_logger.error("Request for Administrator password change failed.")
                database_logger.exception(f"'change_admin_password' error. {error}")

    # DATABASE VIEW AND EXPORT OPERATIONS

    def view_database(self, table):
        """
        Returns all rows from the requested table as a DataFrame.

        Args:
            table (str): The table name to read.

        Returns:
            pd.DataFrame: All rows or an empty DataFrame on error.
        """
        if not table:
            database_logger.error("No table provided for view_database().")
            return pd.DataFrame()

        with self.connect() as conn:
            try:
                admin_logger.info(f"Requesting to view Table: '{table}'.")
                database_logger.info(f"Attempting to read data from Table: '{table}'.")

                dataframe = pd.read_sql_query(f"SELECT * FROM {table}", conn)

                database_logger.info(f"Table: '{table}' data read successfully.")
                admin_logger.info("Request to view table successful.")

                return dataframe

            except sqlite3.Error as error:
                admin_logger.error("Request to view table failed.")
                database_logger.exception(f"'view_database' error. {error}")
                return pd.DataFrame()

    def export_table_to_csv(self, table, file_path):
        """
        Exports all rows from a table to a CSV file.

        Args:
            table (str): The table to export.
            file_path (str): Destination file path.

        Returns:
            bool: True on success, False on error.
        """
        try:
            with self.connect() as conn:
                database_logger.info(
                    f"Attempting to export Table: '{table}' to CSV at '{file_path}'."
                )

                rows = conn.execute(f"SELECT * FROM {table}").fetchall()

                if not rows:
                    database_logger.warning(f"Table: '{table}' is empty.")
                    return False

                headers = list(rows[0].keys())

                with open(file_path, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(headers)
                    writer.writerows(rows)

                database_logger.info(
                    f"Table: '{table}' exported to '{file_path}' successfully."
                )
                return True

        except Exception as error:
            database_logger.exception(f"'export_table_to_csv' error. {error}")
            return False

    # USER RECORD OPERATIONS

    def change_user_record(
        self,
        *,
        user_id,
        new_username=None,
        new_password=None,
        new_account_type=None,
        new_balance=None,
    ):
        """
        Updates one or more fields on a user record. Only non-None
        arguments are applied.

        Args:
            user_id (int): The user ID to modify.
            new_username (str, optional): New username.
            new_password (str, optional): New plaintext password
                                          (hashed before storage).
            new_account_type (int, optional): New registered status
                                              (0 or 1).
            new_balance (float, optional): New balance value.
        """
        if new_username is not None:
            self.change_user_username(user_id, new_username)
        if new_password is not None:
            self.change_user_password(user_id, new_password)
        if new_account_type is not None:
            self.change_user_account_type(user_id, new_account_type)
        if new_balance is not None:
            self.change_user_balance(user_id, new_balance)

    def change_user_username(self, user_id, new_username):
        """
        Changes a user's username.

        Args:
            user_id (int): Target user ID.
            new_username (str): The new username to assign.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(
                    f"Request for username change for User ID: {user_id}."
                )
                database_logger.info(
                    f"Attempting to change username for User ID: {user_id}."
                )

                conn.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (new_username, user_id),
                )

                database_logger.info(
                    f"User ID: {user_id} username changed successfully."
                )
                admin_logger.info("Request for username change successful.")

            except sqlite3.Error as error:
                admin_logger.error("Request for username change failed.")
                database_logger.exception(f"'change_user_username' error. {error}")

    def change_user_password(self, user_id, new_password):
        """
        Changes a user's password. Hashes the plaintext before storing.

        Args:
            user_id (int): Target user ID.
            new_password (str): New plaintext password.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(
                    f"Request for password change for User ID: {user_id}."
                )
                database_logger.info(
                    f"Attempting to change password for User ID: {user_id}."
                )

                from check_systems import hash_function

                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE user_id = ?",
                    (hash_function(new_password), user_id),
                )

                database_logger.info(
                    f"User ID: {user_id} password changed successfully."
                )
                admin_logger.info("Request for password change successful.")

            except sqlite3.Error as error:
                admin_logger.error("Request for password change failed.")
                database_logger.exception(f"'change_user_password' error. {error}")

    def change_user_account_type(self, user_id, registered):
        """
        Changes a user's registered status.

        Args:
            user_id (int): Target user ID.
            registered (int): New status (0 = guest, 1 = registered).
        """
        with self.connect() as conn:
            try:
                admin_logger.info(
                    f"Request for account type change for User ID: {user_id}."
                )
                database_logger.info(
                    f"Attempting to change account type for User ID: {user_id}."
                )

                conn.execute(
                    "UPDATE users SET registered = ? WHERE user_id = ?",
                    (registered, user_id),
                )

                database_logger.info(
                    f"User ID: {user_id} account type changed successfully."
                )
                admin_logger.info("Request for account type change successful.")

            except sqlite3.Error as error:
                admin_logger.error("Request for account type change failed.")
                database_logger.exception(f"'change_user_account_type' error. {error}")

    def change_user_balance(self, user_id, new_balance):
        """
        Sets a user's balance to the given value.

        Args:
            user_id (int): Target user ID.
            new_balance (float): New balance.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request for balance change for User ID: {user_id}.")
                database_logger.info(
                    f"Attempting to change balance for User ID: {user_id}."
                )

                conn.execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?",
                    (float(new_balance), user_id),
                )

                database_logger.info(
                    f"User ID: {user_id} balance changed successfully."
                )
                admin_logger.info("Request for balance change successful.")

            except sqlite3.Error as error:
                admin_logger.error("Request for balance change failed.")
                database_logger.exception(f"'change_user_balance' error. {error}")

    def delete_user_record(self, user_id):
        """
        Permanently deletes a user record and all associated poker data.

        Child rows in user_poker_actions and user_poker_data are removed
        before the parent row in users so that the foreign key constraints
        are satisfied.

        Args:
            user_id (int): The user ID to delete.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request for deletion of User ID: {user_id} record.")
                database_logger.info(
                    f"Attempting to delete record for User ID: {user_id}."
                )

                conn.execute(
                    "DELETE FROM user_poker_actions WHERE user_id = ?", (user_id,)
                )
                conn.execute(
                    "DELETE FROM user_poker_data WHERE user_id = ?", (user_id,)
                )
                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

                database_logger.info(f"User ID: {user_id} record deleted successfully.")
                admin_logger.info("Request for deletion of user record successful.")

            except sqlite3.Error as error:
                admin_logger.error("Request for deletion of user record failed.")
                database_logger.exception(f"'delete_user_record' error. {error}")

    # USER LOOKUP AND AUTHENTICATION

    def fetch_user_record(self, *, user_id=None, username=None):
        """
        Returns all columns from the users table for the specified user.

        Args:
            user_id (int, optional): User ID to search by.
            username (str, optional): Username to search by.

        Returns:
            dict: All user fields or None if not found.

        Raises:
            ValueError: If neither user_id nor username is provided.
        """
        if user_id is None and username is None:
            raise ValueError("Either user_id or username must be provided.")

        with self.connect() as conn:
            try:
                if user_id is not None:
                    database_logger.info(
                        f"Attempting to fetch full record for User ID: {user_id}."
                    )
                    row = conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", (user_id,)
                    ).fetchone()
                else:
                    database_logger.info(
                        f"Attempting to fetch full record for User: '{username}'."
                    )
                    row = conn.execute(
                        "SELECT * FROM users WHERE username = ?", (username,)
                    ).fetchone()

                return dict(row) if row else None

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_record' error. {error}")
                return None

    def fetch_user_presence(self, username):
        """
        Checks whether a username exists in the database.

        Args:
            username (str): The username to search for.

        Returns:
            dict: {'found': bool}
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to check presence of User: '{username}'."
                )

                row = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?", (username,)
                ).fetchone()

                found = row is not None
                database_logger.info(
                    f"User: '{username}' {'found' if found else 'not found'}."
                )

                return {"found": found}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_presence' error. {error}")
                return {"found": False}

    def register_user(self, username, password, registered):
        """
        Inserts a new user with a hashed password and £10,000 starting
        balance. Guest accounts may pass None for password.

        Args:
            username (str): Unique username (must not be 'Administrator').
            password (str or None): Plaintext password or None for guests.
            registered (int): 0 for guest, 1 for registered.

        Returns:
            str: The created username.

        Raises:
            ValueError: If the username is invalid or reserved.
            sqlite3.IntegrityError: If the username already exists.
            sqlite3.Error: For other database errors.
        """
        if not username or not isinstance(username, str):
            raise ValueError("'username' must be a non-empty string.")

        if username.strip().lower() == "administrator":
            raise ValueError("The username 'Administrator' cannot be used.")

        from check_systems import hash_function

        password_hash = hash_function(password) if password else None

        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to register account for User: '{username}'."
                )

                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, registered, balance)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, int(float(registered)), 10000.0),
                )

                database_logger.info(
                    f"User: '{username}' account registered successfully."
                )
                return username

            except sqlite3.IntegrityError:
                database_logger.warning(f"User: '{username}' account already exists.")
                raise

            except sqlite3.Error as error:
                database_logger.exception(f"'register_user' error. {error}")
                raise

    def verify_user_password(self, username, password):
        """
        Verifies a plaintext password against the stored hash.

        Args:
            username (str): The username to verify.
            password (str): The plaintext password to check.

        Returns:
            dict: {'found': bool, 'verified': bool}
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to fetch password_hash for User: '{username}'."
                )

                row = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    (username,),
                ).fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'verify_user_password' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.info(f"User: '{username}' password_hash not found.")
            return {"found": False, "verified": False}

        from check_systems import verify_hash

        verified = verify_hash(row["password_hash"], password)

        database_logger.info(
            f"User: '{username}' password verification successful."
            if verified
            else f"User: '{username}' password verification failed."
        )

        return {"found": True, "verified": verified}

    def record_user_login(self, username):
        """
        Records the current timestamp as the last login time for the given
        user. The timestamp is stored in ISO 8601 format (YYYY-MM-DD HH:MM:SS)
        so that SQLite's strftime functions can compare it correctly.

        Args:
            username (str): The username of the user who logged in.
        """
        with self.connect() as conn:
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                database_logger.info(
                    f"Attempting to record login for User: '{username}'."
                )

                conn.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (now_str, username),
                )

                database_logger.info(
                    f"User: '{username}' login recorded successfully at {now_str}."
                )

            except sqlite3.Error as error:
                database_logger.exception(f"'record_user_login' error. {error}")

    def check_expired_guest_account(self):
        """
        Deletes guest accounts (registered = 0) and all their associated
        poker data if they are older than 24 hours.
        """
        with self.connect() as conn:
            try:
                database_logger.info("Attempting to check for expired guest accounts.")

                expired = conn.execute(
                    """
                    SELECT user_id FROM users
                    WHERE registered = 0
                    AND (julianday('now') - julianday(created_at)) * 86400.0 > ?
                    """,
                    (24 * 3600,),
                ).fetchall()

                for row in expired:
                    user_id = row["user_id"]
                    conn.execute(
                        "DELETE FROM user_poker_actions WHERE user_id = ?", (user_id,)
                    )
                    conn.execute(
                        "DELETE FROM user_poker_data WHERE user_id = ?", (user_id,)
                    )
                    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                    database_logger.info(
                        f"User ID: {user_id} expired guest account removed."
                    )

                conn.commit()
                database_logger.info("Expired guest account check completed.")

            except sqlite3.Error as error:
                database_logger.exception(
                    f"'check_expired_guest_account' error. {error}"
                )

    def apply_daily_login_bonus(self):
        """
        Awards a £1,000 bonus to every registered user whose last_login
        was recorded more than 24 hours ago. Resets last_login to now
        after each award so the bonus is granted at most once every
        24 hours.

        Should be called once at program start-up.
        """
        with self.connect() as conn:
            try:
                database_logger.info("Attempting to apply daily login bonuses.")

                eligible = conn.execute(
                    """
                    SELECT user_id FROM users
                    WHERE registered = 1
                    AND last_login IS NOT NULL
                    AND (julianday('now') - julianday(last_login)) * 86400.0 > ?
                    """,
                    (24 * 3600,),
                ).fetchall()

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for row in eligible:
                    user_id = row["user_id"]
                    conn.execute(
                        """
                        UPDATE users
                        SET balance = balance + 1000,
                            last_login = ?
                        WHERE user_id = ?
                        """,
                        (now_str, user_id),
                    )
                    database_logger.info(
                        f"User ID: {user_id} awarded £1,000 daily login bonus."
                    )

                conn.commit()
                database_logger.info("Daily login bonus check completed.")

            except sqlite3.Error as error:
                database_logger.exception(f"'apply_daily_login_bonus' error. {error}")

    def fetch_user_id(self, username):
        """
        Retrieves the user ID for a given username.

        Args:
            username (str): The username to look up.

        Returns:
            dict: {'found': bool, 'user_id': int or None}
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to fetch user_id for User: '{username}'."
                )

                row = conn.execute(
                    "SELECT user_id FROM users WHERE username = ?", (username,)
                ).fetchone()

                if row:
                    database_logger.info(f"User: '{username}' user_id found.")
                    return {"found": True, "user_id": row["user_id"]}
                else:
                    database_logger.info(f"User: '{username}' user_id not found.")
                    return {"found": False, "user_id": None}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_id' error. {error}")
                return {"found": False, "user_id": None}

    def fetch_username(self, user_id):
        """
        Retrieves the username for a given user ID.

        Args:
            user_id (int): The user ID to look up.

        Returns:
            dict: {'found': bool, 'username': str or None}
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to fetch username for User ID: {user_id}."
                )

                row = conn.execute(
                    "SELECT username FROM users WHERE user_id = ?", (user_id,)
                ).fetchone()

                if row:
                    database_logger.info(f"User ID: {user_id} username found.")
                    return {"found": True, "username": row["username"]}
                else:
                    database_logger.info(f"User ID: {user_id} username not found.")
                    return {"found": False, "username": None}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_username' error. {error}")
                return {"found": False, "username": None}

    def fetch_user_balance(self, username):
        """
        Retrieves the account balance for a username.

        Args:
            username (str): The username to query.

        Returns:
            dict: {'found': bool, 'balance': float}
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to fetch balance for User: '{username}'."
                )

                row = conn.execute(
                    "SELECT balance FROM users WHERE username = ?", (username,)
                ).fetchone()

                if row:
                    database_logger.info(f"User: '{username}' balance found.")
                    return {"found": True, "balance": float(row["balance"])}
                else:
                    database_logger.info(f"User: '{username}' balance not found.")
                    return {"found": False, "balance": 0.0}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_balance' error. {error}")
                return {"found": False, "balance": 0.0}

    def modify_user_balance(self, username, new_balance):
        """
        Sets a user's balance to the specified value.

        Args:
            username (str): The username to update.
            new_balance (float): The new balance.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to modify balance for User: '{username}'."
                )

                conn.execute(
                    "UPDATE users SET balance = ? WHERE username = ?",
                    (float(new_balance), username),
                )

                database_logger.info(
                    f"User: '{username}' balance modified successfully."
                )

            except sqlite3.Error as error:
                database_logger.exception(f"'modify_user_balance' error. {error}")

    # POKER STATISTICS AND ACTION HISTORY

    def check_user_poker_data_exists(self, user_id):
        """
        Returns True if a poker data record exists for the given user ID.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to check poker data existence for User ID: {user_id}."
                )

                exists = conn.execute(
                    "SELECT 1 FROM user_poker_data WHERE user_id = ?", (user_id,)
                ).fetchone()

                database_logger.info(
                    f"User ID: {user_id} poker data "
                    f"{'found' if exists else 'not found'}."
                )

                return exists is not None

            except sqlite3.Error as error:
                database_logger.exception(
                    f"'check_user_poker_data_exists' error. {error}"
                )
                return False

    def initialise_user_poker_data(self, user_id):
        """
        Creates a poker data record for the user with default values and a
        base range chart. Does nothing if a record already exists.

        Args:
            user_id (int): The user ID to initialise.

        Returns:
            bool: True if successful or already initialised, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to initialise poker data for User ID: {user_id}."
                )

                exists = conn.execute(
                    "SELECT 1 FROM user_poker_data WHERE user_id = ?", (user_id,)
                ).fetchone()

                if exists:
                    database_logger.info(
                        f"User ID: {user_id} poker data already exists."
                    )
                    return True

                from poker_player_management import generate_range_chart

                conn.execute(
                    "INSERT INTO user_poker_data (user_id, player_range) VALUES (?, ?)",
                    (user_id, json.dumps(generate_range_chart())),
                )

                database_logger.info(
                    f"User ID: {user_id} poker data initialised successfully."
                )
                return True

            except sqlite3.Error as error:
                database_logger.exception(
                    f"'initialise_user_poker_data' error. {error}"
                )
                return False

    def load_user_poker_data(self, user_id):
        """
        Loads the necessary poker data record for a user, including derived
        statistics and a deserialised range chart.

        Args:
            user_id (int): The user ID to load.

        Returns:
            dict: All poker data fields plus avg_bet_size or None on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to load poker data for User ID: {user_id}."
                )

                row = conn.execute(
                    """
                    SELECT
                        upd.user_id,
                        upd.rounds_played,
                        upd.player_range,
                        upd.vpip,
                        upd.pfr,
                        upd.total_hands_played,
                        upd.total_hands_raised,
                        upd.total_bets,
                        upd.fold_to_raise,
                        upd.call_when_weak,
                        upd.tournament_wins,
                        upd.last_updated
                    FROM user_poker_data upd
                    WHERE upd.user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if not row:
                    database_logger.warning(
                        f"User ID: {user_id} not found in poker data."
                    )
                    return None

                record = dict(row)

                record["player_range"] = (
                    json.loads(record["player_range"])
                    if record.get("player_range")
                    else None
                )

                rounds = max(1, record["rounds_played"])
                record["avg_bet_size"] = record["total_bets"] / rounds

                total = record["fold_to_raise"] + record["call_when_weak"]
                if total > 0:
                    record["fold_to_raise"] = record["fold_to_raise"] / total
                    record["call_when_weak"] = record["call_when_weak"] / total
                else:
                    record["fold_to_raise"] = 0.5
                    record["call_when_weak"] = 0.5

                database_logger.info(
                    f"User ID: {user_id} poker data loaded successfully."
                )

                return record

            except (sqlite3.Error, json.JSONDecodeError) as error:
                database_logger.exception(f"'load_user_poker_data' error. {error}")
                return None

    def update_player_range(self, user_id, player_range):
        """
        Serialises and stores a player's range chart.

        Args:
            user_id (int): Target user ID.
            player_range (dict): The range chart to store.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to update player range for User ID: {user_id}."
                )

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET player_range = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (json.dumps(player_range), user_id),
                )

                database_logger.info(
                    f"User ID: {user_id} player range updated successfully."
                )
                return True

            except (sqlite3.Error, json.JSONDecodeError) as error:
                database_logger.exception(f"'update_player_range' error. {error}")
                return False

    def log_player_action(
        self,
        *,
        user_id,
        round_number,
        street,
        action,
        bet_size,
        pot_size,
    ):
        """
        Inserts a player action record into user_poker_actions.

        Args:
            user_id (int): The acting user's ID.
            round_number (int): The hand/round identifier.
            street (str): 'preflop', 'flop', 'turn' or 'river'.
            action (str): 'fold', 'call' or 'raise'.
            bet_size (float): Amount bet or raised.
            pot_size (float): Total pot at the time of the action.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to log action for User ID: {user_id}."
                )

                conn.execute(
                    """
                    INSERT INTO user_poker_actions
                        (user_id, round_number, street, action, bet_size, pot_size)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, round_number, street, action, bet_size, pot_size),
                )

                database_logger.info(f"User ID: {user_id} action logged successfully.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'log_player_action' error. {error}")
                return False

    def resolve_player_actions(self, user_id, round_number):
        """
        Marks all actions for a specific round as resolved.

        Args:
            user_id (int): Target user ID.
            round_number (int): The round to resolve.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to resolve actions for User ID: {user_id}."
                )

                conn.execute(
                    """
                    UPDATE user_poker_actions
                    SET resolved = 1
                    WHERE user_id = ? AND round_number = ?
                    """,
                    (user_id, round_number),
                )

                database_logger.info(
                    f"User ID: {user_id} actions resolved successfully."
                )
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'resolve_player_actions' error. {error}")
                return False

    def update_hand_statistics(
        self,
        *,
        user_id,
        action,
        bet_size,
        voluntarily_entered,
        preflop_raised,
        faced_raise,
    ):
        """
        Increments poker statistics after a hand and
        recalculates VPIP/PFR percentages.

        Args:
            user_id (int): The user ID to update.
            action (str): Final action taken ('fold', 'call', 'raise').
            bet_size (float): Amount bet during the hand.
            voluntarily_entered (bool): True if the player voluntarily
                                        put money in the pot.
            preflop_raised (bool): True if the player raised preflop.
            faced_raise (bool): True if the player faced a raise.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to update hand statistics for User ID: {user_id}."
                )

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET
                        rounds_played = rounds_played + 1,
                        total_hands_played = total_hands_played + ?,
                        total_hands_raised = total_hands_raised + ?,
                        total_bets = total_bets + ?,
                        fold_to_raise = fold_to_raise + ?,
                        call_when_weak = call_when_weak + ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (
                        int(voluntarily_entered),
                        int(preflop_raised),
                        bet_size,
                        int(faced_raise and action == "fold"),
                        int(faced_raise and action == "call"),
                        user_id,
                    ),
                )

                self.recalculate_frequencies(conn, user_id)

                database_logger.info(
                    f"User ID: {user_id} hand statistics updated successfully."
                )
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_hand_statistics' error. {error}")
                return False

    def recalculate_frequencies(self, conn, user_id):
        """
        Recalculates and stores VPIP and PFR percentages from the raw
        counters.

        Args:
            conn (sqlite3.Connection): Active connection to reuse.
            user_id (int): The user ID to recalculate for.
        """
        try:
            database_logger.info(
                f"Attempting to recalculate frequencies for User ID: {user_id}."
            )

            row = conn.execute(
                """
                SELECT rounds_played, total_hands_played, total_hands_raised
                FROM user_poker_data
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if not row or row["rounds_played"] == 0:
                return

            rounds = row["rounds_played"]
            vpip = (row["total_hands_played"] / rounds) * 100.0
            pfr = (row["total_hands_raised"] / rounds) * 100.0

            conn.execute(
                "UPDATE user_poker_data SET vpip = ?, pfr = ? WHERE user_id = ?",
                (vpip, pfr, user_id),
            )

            database_logger.info(
                f"User ID: {user_id} frequencies recalculated successfully."
            )

        except sqlite3.Error as error:
            database_logger.exception(f"'recalculate_frequencies' error. {error}")

    def fetch_total_rounds(self, user_id):
        """
        Returns the total of rounds played by a player.

        Args:
            user_id (int): The user ID to retrieve the total rounds played for.

        Returns:
            dict: Statistics dictionary or None if not found.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to fetch player total rounds for User ID: {user_id}."
                )

                rounds = conn.execute(
                    """
                    SELECT rounds_played
                    FROM user_poker_data
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if not rounds:
                    return None

                database_logger.info(
                    f"User ID: {user_id} player total rounds fetched successfully."
                )
                return rounds

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_total_rounds' error. {error}")
                return None

    def fetch_tournament_scores(self):
        """
        Retrieves the tournament wins for all users.

        Returns:
            list: List of dicts with 'user_id' and 'tournament_wins', or None on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    "Attempting to fetch tournament scores for all users."
                )

                row = conn.execute(
                    """
                    SELECT user_id, tournament_wins
                    FROM user_poker_data
                    """,
                ).fetchall()

                database_logger.info("Tournament scores fetched successfully.")
                return [
                    {"user_id": r["user_id"], "tournament_wins": r["tournament_wins"]}
                    for r in row
                ]

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_tournament_scores' error. {error}")
                return None

    def update_tournament_best(self, user_id, rounds_survived):
        """
        Updates tournament_wins  with the best number of
        consecutive rounds survived in a single tournament run.

        Args:
            user_id (int): The user ID to update.
            rounds_survived (int): Rounds survived in the completed tournament.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Attempting to update tournament best for User ID: {user_id}."
                )

                row = conn.execute(
                    "SELECT tournament_wins FROM user_poker_data WHERE user_id = ?",
                    (user_id,),
                ).fetchone()

                current_best = row["tournament_wins"] if row else 0

                if rounds_survived > current_best:
                    conn.execute(
                        """
                        UPDATE user_poker_data
                        SET tournament_wins = ?,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        (rounds_survived, user_id),
                    )
                    database_logger.info(
                        f"User ID: {user_id} tournament best updated to "
                        f"{rounds_survived} (was {current_best})."
                    )
                else:
                    database_logger.info(
                        f"User ID: {user_id} tournament best unchanged "
                        f"({rounds_survived} did not beat {current_best})."
                    )

                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_tournament_best' error. {error}")
                return False
