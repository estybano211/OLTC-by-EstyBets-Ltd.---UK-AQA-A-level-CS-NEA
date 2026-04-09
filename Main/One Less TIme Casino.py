# This is the complete source code for the One Less Time Casino application:
# 1. database_management_and_logging.py
# 2. gui_helpers.py
# 3. search_sort_algorithms.py
# 4. encryption_software.py
# 5. check_systems.py
# 6. system_interfaces.py
# 7. deck_management.py
# 8. whitejoe.py
# 9. poker_player_management.py
# 10. harrogate_hold_em.py

import sys
import os
from datetime import datetime
from time import time, sleep
from queue import Queue, Empty
from threading import Thread, Event
import logging
import sqlite3
import pandas as pd
import csv
import json
from tkinter import (
    BOTH,
    BOTTOM,
    BooleanVar,
    Button,
    Canvas,
    Checkbutton,
    END,
    Entry,
    Frame,
    filedialog,
    font,
    HORIZONTAL,
    IntVar,
    Label,
    messagebox,
    Scale,
    Scrollbar,
    scrolledtext,
    simpledialog,
    Spinbox,
    StringVar,
    Tk,
    Toplevel,
    WORD,
    X,
)
from tkinter.ttk import Combobox, Treeview
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import hashlib
import hmac
import binascii
from treys import Card as TreysCard, Deck as TreysDeck, Evaluator
import random
from itertools import combinations

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# database_management_and_logging.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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
                    AND strftime('%s', 'now') - strftime('%s', created_at) > ?
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
                    AND strftime('%s', 'now') - strftime('%s', last_login) > ?
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


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# gui_helpers.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def fetch_text_styles(root):
    """
    Creates and returns a dictionary of named tkinter Font objects.

    Args:
        root: The root Tk window used to bind the font objects.

    Returns:
        dict: A dictionary mapping style names (e.g. 'heading', 'text') to
              tkinter Font instances.
    """
    text_styles = {
        "title": font.Font(
            root=root, family="Times New Roman", size=45, weight="bold", underline=True
        ),
        "heading": font.Font(
            root=root,
            family="Bodoni 72 Smallcaps",
            size=36,
            weight="bold",
            underline=True,
        ),
        "subheading": font.Font(
            root=root, family="Bodoni 72 Smallcaps", size=30, weight="bold"
        ),
        "rules": font.Font(root=root, family="Helvetica", size=20, weight="bold"),
        "text": font.Font(root=root, family="Verdana", size=26),
        "button": font.Font(root=root, family="Tahoma", size=22, weight="bold"),
        "label": font.Font(root=root, family="Didot", size=20),
        "emphasis": font.Font(
            root=root, family="Georgia", size=16, weight="bold", slant="italic"
        ),
    }
    return text_styles


# Colour scheme.
CS = {
    # Windows.
    "pwd_prompt": "#BB8C64",
    "admin": "#BB756D",
    "casino": "#1F6053",
    "rules": "#000000",
    # Labels, entrys and buttons.
    "label_bg": "#D7CBB4",
    "label_text": "#000000",
    "entry_bg": "#FDFEFE",
    "entry_text": "#000000",
    "button_bg": "#F1C40F",
    "button_text": "#000000",
    # Frames backgrounds.
    "top_left": "#D79393",
    "bottom_left": "#E59866",
    "top_right": "#2E7D73",
    "middle_right": "#BCC88B",
    "bottom_right": "#5B2A3C",
    # Widgets.
    "widget_bg": "#A50B5E",
    "widget_text": "#000000",
    # Text.
    "text_bg": "#1A1A1A",
    "text_fg": "#FFFFFF",
    "casino_text": "#E59866",
    # Log panel.
    "log_bg": "#000000",
    "log_fg": "#FFFFFF",
    # Log entry.
    "start_bg": "#243B7A",
    "start_fg": "#FFFFFF",
    "win_bg": "#244D3A",
    "win_fg": "#A8E6C1",
    "loss_bg": "#AE1E1E",
    "loss_fg": "#F2A3A3",
    "tie_bg": "#5C4A10",
    "tie_fg": "#F0d898",
    "thinking_bg": "#3C2A4A",
    "thinking_fg": "#D4B8E8",
    "tournament_bg": "#4A1E38",
    "tournament_fg": "#F4BDD9",
    # Misc.
    "correct": "#13DF00",
    "error": "#FF0000",
    "table_even": "#0C0C0C",
    "table_odd": "#364DE2",
    "separator": "#888888",
    "round_label_bg": "#1A5276",
    "round_label_fg": "#FFFFFF",
}

# Default delay for message logging in seconds.
DELAY = 1.5


# GUI WIDGET PRESET FUNCTIONS


def create_window(root, title, bg_color, is_main_frame=False):
    """
    Creates and configures a standardised Tkinter window.

    Args:
        root (Tk or Toplevel): The Tkinter root window to configure.
        title (str): The title to display in the window title bar.
        bg_color (str): Hex colour string for the window background.
        is_main_frame (bool): If True, creates and returns a packed main
                              Frame alongside the styles dict. If False,
                              returns only the styles dict. Defaults to
                              False.

    Returns:
        tuple[Frame, dict] or dict: When is_main_frame is True, returns
        (main_frame, styles). When False, returns only styles.
    """
    root.configure(bg=bg_color)
    root.title(title)
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+0+0")
    root.focus_force()

    styles = fetch_text_styles(root)

    if is_main_frame:
        main_frame = Frame(root, bg=bg_color)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        return main_frame, styles
    else:
        return styles


def preset_label(
    parent, text="", bg=None, fg=None, font=None, relief="raised", bd=2, **kwargs
):
    """
    Create a Label with default styling from CS and raised relief border.

    Args:
        parent (Widget): Parent widget
        text (str): Label text
        bg (str): Override background colour (default: CS["label_bg"])
        fg (str): Override foreground colour (default: CS["label_text"])
        font (Font): Override font (default: fetched from styles)
        relief (str): Border relief style (default: "raised")
        bd (int): Border width (default: 2)
        **kwargs: Additional Label parameters (font, padx, pady, etc.)

    Returns:
        Label widget with styling applied
    """
    bg = bg or CS["label_bg"]
    fg = fg or CS["label_text"]
    style = fetch_text_styles(parent)
    font = font or style["label"]
    return Label(
        parent, text=text, bg=bg, fg=fg, font=font, relief=relief, bd=bd, **kwargs
    )


def preset_button(
    parent, text="", bg=None, fg=None, font=None, relief="raised", bd=2, **kwargs
):
    """
    Create a Button with default styling from CS and raised relief border.

    Args:
        parent (Widget): Parent widget
        text (str): Button text
        bg (str): Override background colour (default: CS["button_bg"])
        fg (str): Override foreground colour (default: CS["button_text"])
        font (Font): Override font (default: fetched from styles)
        relief (str): Border relief style (default: "raised")
        bd (int): Border width (default: 2)
        **kwargs: Additional Button parameters (command, font, width, etc.)

    Returns:
        Button widget with styling applied
    """
    bg = bg or CS["button_bg"]
    fg = fg or CS["button_text"]
    style = fetch_text_styles(parent)
    font = font or style["button"]
    return Button(
        parent, text=text, bg=bg, fg=fg, font=font, relief=relief, bd=bd, **kwargs
    )


def preset_entry(parent, bg=None, fg=None, font=None, **kwargs):
    """
    Create an Entry with default styling from CS.

    Args:
        parent (Widget): Parent widget
        bg (str): Override background colour (default: CS["entry_bg"])
        fg (str): Override foreground colour (default: CS["entry_text"])
        font (Font): Override font (default: fetched from styles)
        **kwargs: Additional Entry parameters (show, width, font, etc.)

    Returns:
        Entry widget with styling applied
    """
    bg = bg or CS["entry_bg"]
    fg = fg or CS["entry_text"]
    style = fetch_text_styles(parent)
    font = font or style["text"]
    return Entry(parent, bg=bg, fg=fg, font=font, **kwargs)


def clear_current_section(self):
    """
    Destroys the currently active section frame if one exists and resets the
    reference to None.

    Args:
        self (object): The parent interface object that holds a 'current_section_frame'
                       attribute.
    """
    if getattr(self, "current_section_frame", None) is not None:
        self.current_section_frame.destroy()
        self.current_section_frame = None


def set_view(self, view_builder):
    """
    Clears the current section frame and builds a new one using the provided
    view builder function. The new frame is packed into the main frame and
    passed to the view builder.

    If the view_builder needs a parameter, lambda can be used to wrap it, e.g.:
    set_view(self, lambda f: self.function(f, param1, param2))
    this allows the view builder to receive the new frame as an argument while also
    passing additional parameters.

    Args:
        self (object): The parent interface object that holds 'main_frame' and
                       'current_section_frame' attributes.
        view_builder (callable): A function that accepts a Frame as its sole
                                 argument and populates it with widgets.
    """
    clear_current_section(self)

    background = getattr(self, "window_bg", None)
    self.current_section_frame = Frame(
        self.main_frame, bg=background if background else self.main_frame.cget("bg")
    )
    self.current_section_frame.pack(expand=True, fill="both")

    view_builder(self.current_section_frame)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# search_sort_algorithms.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def linear_search(array, key, value):
    """
    Performs a linear search through a list of dictionaries.
    Checks every element from a starting index 0 until the target is found.
    Time complexity: O(n).

    Args:
        array (list): A list of dictionaries to search.
        key (str): The dictionary key to inspect.
        value (any): The value to search for.

    Returns:
        int: Index of the first matching element or -1 if not found.
    """
    for index in range(len(array)):
        if array[index].get(key) == value:
            return index
    return -1


def bubble_sort(array, key, reverse):
    """
    Sorts a list of dictionaries by a given key using bubble sort.
    Compares adjacent pairs and swaps if out of order.
    Time complexity: O(n^2).

    Args:
        array (list): List of dictionaries to sort.
        key (str): The dictionary key to sort by.
        reverse (bool): True for descending, False for ascending.

    Returns:
        list: A new sorted list.
    """
    array = array.copy()
    array_length = len(array)
    for pass_num in range(array_length - 1):
        swapped = False
        for index in range(
            array_length - 1 - pass_num
        ):  # Last 'pass_num' elements are already sorted.
            value_a = array[index].get(key)
            value_b = array[index + 1].get(key)
            if (reverse and value_a < value_b) or (
                not reverse and value_a > value_b
            ):  # Compare based on sort order.
                array[index], array[index + 1] = array[index + 1], array[index]
                swapped = True
        if not swapped:  # No swaps means the array is already sorted.
            break
    return array


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# encryption_software.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class EncryptionSoftware:
    """
    GUI tool for hybrid RSA/AES file encryption and decryption. Used by
    administrators to secure database files or other data.
    """

    def __init__(self):
        """
        Initialises the root window, applies GUI styles, logs the system access
        event through DatabaseManagement, sets the AES key placeholder to None and
        starts the main interface.
        """
        self.window_bg = CS["admin"]
        self.enc_soft_root = Tk()
        self.main_frame, self.styles = create_window(
            self.enc_soft_root,
            "One Less Time Casino - Encryption Software",
            self.window_bg,
            is_main_frame=True,
        )
        self.enc_soft_root.protocol(
            "WM_DELETE_WINDOW", lambda: (self.enc_soft_root.quit(), sys.exit(0))
        )

        self.dbm = DatabaseManagement(DB_PATH)
        self.dbm.admin_accessed_system("Encryption Software")

        self.aes_key = None

        self.current_section_frame = None

        set_view(self, self.create_main_menu)

        self.enc_soft_root.mainloop()

    def create_main_menu(self, frame):
        """
        Builds the main menu interface with buttons for all available
        operations: generating an RSA keypair, generating and encrypting an AES
        key, loading an encrypted AES key, encrypting a file, decrypting a
        file and exiting.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Encryption Software",
            font=self.styles["heading"],
        ).pack(pady=10)

        buttons = [
            ("Generate RSA Keypair", self.generate_rsa_keys),
            ("Generate & Encrypt AES Key", self.generate_encrypted_aes_key),
            ("Load Encrypted AES Key", self.load_rsa_aes_key),
            ("Encrypt File", self.encrypt_file),
            ("Decrypt File", self.decrypt_file),
            ("Exit", self.enc_soft_root.destroy),
        ]

        for text, command in buttons:
            preset_button(
                frame,
                text=text,
                width=40,
                command=command,
            ).pack(pady=5)

    def generate_rsa_keys(self):
        """
        Generates a 2048-bit RSA keypair and saves both the private and public
        keys as PEM files to a user-selected directory. Filenames include a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file paths or an error message if generation or saving fails.
        """
        save_dir = filedialog.askdirectory(title="Select folder to save RSA keys")
        if not save_dir:
            return

        try:
            key = RSA.generate(2048)

            private_key = key.export_key()

            public_key = key.publickey().export_key()

            timestamp = datetime.now().strftime("%d-%B-%Y")

            private_path = os.path.join(save_dir, f"private_key_{timestamp}.pem")

            public_path = os.path.join(save_dir, f"public_key_{timestamp}.pem")

            with open(private_path, "wb") as file:
                file.write(private_key)

            with open(public_path, "wb") as file:
                file.write(public_key)

            messagebox.showinfo(
                "Success",
                f"RSA keys generated and saved:\n{private_path}\n{public_path}",
            )

        except Exception as error:
            messagebox.showerror("Error", f"Failed to generate RSA keys: {error}")

    def generate_encrypted_aes_key(self):
        """
        Generates a random 256-bit AES key, encrypts it using a user-selected
        RSA public key through PKCS1-OAEP and saves the encrypted result as a
        binary file to a user-selected directory. The filename includes a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file path or an error message on failure.
        """
        rsa_pub_file = filedialog.askopenfilename(
            title="Select RSA Public Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )

        if not rsa_pub_file:
            return

        save_dir = filedialog.askdirectory(
            title="Select folder to save encrypted AES key"
        )
        if not save_dir:
            return

        try:
            aes_key = get_random_bytes(32)

            with open(rsa_pub_file, "rb") as file:
                public_key = RSA.import_key(file.read())

            cipher_rsa = PKCS1_OAEP.new(public_key)

            encrypted_aes = cipher_rsa.encrypt(aes_key)

            timestamp = datetime.now().strftime("%d-%B-%Y")

            save_path = os.path.join(save_dir, f"aes_key_{timestamp}.bin")

            with open(save_path, "wb") as file:
                file.write(encrypted_aes)

            messagebox.showinfo("Success", f"Encrypted AES key saved to:\n{save_path}")

        except Exception as error:
            messagebox.showerror(
                "Error", f"Failed to generate/encrypt AES key: {error}"
            )

    def load_rsa_aes_key(self):
        """
        Prompts the user to select an RSA private key file and an encrypted AES
        key file and then decrypts the AES key using PKCS1-OAEP and stores it in
        memory as self.aes_key. The loaded key is used for subsequent encrypt
        and decrypt operations. Displays a success message on completion or an
        error message if decryption fails.
        """
        rsa_private_file = filedialog.askopenfilename(
            title="Select RSA Private Key",
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")],
        )

        if not rsa_private_file:
            return

        encrypted_aes_file = filedialog.askopenfilename(
            title="Select Encrypted AES Key",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")],
        )
        if not encrypted_aes_file:
            return

        try:
            with open(rsa_private_file, "rb") as file:
                private_key = RSA.import_key(file.read())

            with open(encrypted_aes_file, "rb") as file:
                encrypted_aes = file.read()

            cipher_rsa = PKCS1_OAEP.new(private_key)

            self.aes_key = cipher_rsa.decrypt(encrypted_aes)

            messagebox.showinfo("Success", "AES key loaded successfully.")

        except Exception as error:
            messagebox.showerror("Error", f"Failed to load AES key: {error}")

    def encrypt_file(self):
        """
        Encrypts a user-selected file using the currently loaded AES key in EAX
        mode. The encrypted output is saved to the same location with a .enc
        extension appended. The file contains the nonce, authentication tag and
        ciphertext concatenated in that order. Displays a warning if no AES key
        is loaded, a success message with the output path on completion or an
        error message on failure.
        """
        if not self.aes_key:
            messagebox.showwarning("Warning", "Please load an AES key first.")
            return

        file_path = filedialog.askopenfilename(
            title="Select database to encrypt",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as file:
                data = file.read()

            cipher = AES.new(self.aes_key, AES.MODE_EAX)

            ciphertext, tag = cipher.encrypt_and_digest(data)

            save_path = file_path + ".enc"

            with open(save_path, "wb") as file:
                file.write(cipher.nonce)
                file.write(tag)
                file.write(ciphertext)

            messagebox.showinfo(
                "Success", f"Database encrypted and saved to:\n{save_path}"
            )

        except Exception as error:
            messagebox.showerror("Error", f"Encryption failed: {error}")

    def decrypt_file(self):
        """
        Decrypts a user-selected .enc file using the currently loaded AES key
        in EAX mode. Reads the nonce, authentication tag and ciphertext from
        the file, verifies the authentication tag and writes the decrypted
        plaintext to disk. The output path is the input path with the .enc
        extension removed or with .dec appended if the file does not end in
        .enc. Displays a warning if no AES key is loaded, a success message
        with the output path on completion or an error message if decryption
        or tag verification fails.
        """
        if not self.aes_key:
            messagebox.showwarning("Warning", "Please load an AES key first.")
            return

        file_path = filedialog.askopenfilename(
            title="Select encrypted database",
            filetypes=[("Encrypted files", "*.enc"), ("All files", "*.*")],
        )

        if not file_path:
            return

        try:
            with open(file_path, "rb") as file:
                nonce = file.read(16)
                tag = file.read(16)
                ciphertext = file.read()

            cipher = AES.new(self.aes_key, AES.MODE_EAX, nonce=nonce)

            data = cipher.decrypt_and_verify(ciphertext, tag)

            save_path = (
                file_path[:-4] if file_path.endswith(".enc") else file_path + ".dec"
            )

            with open(save_path, "wb") as file:
                file.write(data)

            messagebox.showinfo(
                "Success", f"Database decrypted and saved to:\n{save_path}"
            )

        except Exception as error:
            messagebox.showerror("Error", f"Decryption failed: {error}")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# check_systems.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


PBKDF2_ITERATIONS = 200_000  # Iterations for password hashing (Password-Based Key Derivation Function 2).
SALT_BYTES = 16  # Number of random bytes for salt.


def hash_function(string):
    """
    Hashes a plaintext string using PBKDF2-HMAC-SHA256 with a randomly generated
    salt.

    Args:
        string (str): The plaintext string to hash.

    Returns:
        str: A '$'-delimited string in the format 'salt_hex$hash_hex', where
             both components are hexadecimal representations of their respective
             byte sequences.

    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(string, str):
        raise TypeError("Input must be a string.")

    # Generate a random salt.
    salt = os.urandom(SALT_BYTES)

    # Derive the hash using PBKDF2-HMAC-SHA256.
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    # Return the salt and hash joined by a '$' character.
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(derived_key).decode()}"


def verify_hash(stored_string, input_string):
    """
    Verifies a plaintext string against a stored PBKDF2-HMAC-SHA256 hash.

    Args:
        stored_string (str): The previously stored hash string in the format
                             'salt_hex$hash_hex' as produced by hash_function().
        input_string (str): The plaintext string to verify.

    Returns:
        bool: True if the input string matches the stored hash, False otherwise
              (including if the stored string is malformed).
    """
    try:
        salt_hex, hash_hex = stored_string.split("$")
    except ValueError:
        # The stored hash isn't in the expected format.
        return False

    salt = binascii.unhexlify(salt_hex)
    stored_hash = binascii.unhexlify(hash_hex)

    # Derive a hash using the same salt and parameters.
    input_hash = hashlib.pbkdf2_hmac(
        "sha256", input_string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    return hmac.compare_digest(input_hash, stored_hash)


PASSWORD_CRITERIA = [
    # (description_string, rule_function) pair
    (
        "At least 8 characters",
        lambda pwd: len(pwd) >= 8,
    ),
    (
        "At least one uppercase letter (A–Z)",
        lambda pwd: any(char.isupper() for char in pwd),
    ),
    (
        "At least one lowercase letter (a–z)",
        lambda pwd: any(char.islower() for char in pwd),
    ),
    (
        "At least one digit (0–9)",
        lambda pwd: any(char.isdigit() for char in pwd),
    ),
    (
        "At least one special character (!@#$%^&* etc.)",
        lambda pwd: any(not char.isalnum() for char in pwd),
    ),
]


def validate_password(password):
    """
    Checks a plaintext password against every rule in PASSWORD_CRITERIA.

    Args:
        password (str): The password to validate.

    Returns:
        tuple[bool, list[str]]:
            - passed (bool): True only when every rule is satisfied.
            - failures (list[str]): Descriptions of rules that were not met.
              Empty when passed is True.
    """
    failures = [
        description for description, rule in PASSWORD_CRITERIA if not rule(password)
    ]
    return (len(failures) == 0), failures


def passwords_confirmation(frame, root):
    """
    Opens a modal Toplevel dialog prompting the user to enter and confirm a
    new password. The dialog cannot be closed through the window manager's
    close button; the user must submit or cancel explicitly.

    A requirements checklist is displayed beneath the first entry field
    and updates on every keystroke. Each rule is drawn from PASSWORD_CRITERIA
    so the displayed criteria always match the enforced criteria. The Submit
    button is kept disabled until all rules pass and both fields match.

    Args:
        frame: The parent widget used to position the Toplevel window.
        root: The root Tk window, used for font settings and blocking through
              wait_window().

    Returns:
        dict: A dictionary with two keys:
              - 'confirmed' (bool): True if the user submitted a password that
                satisfies PASSWORD_CRITERIA and whose confirmation field matches.
              - 'password' (str or None): The confirmed password string, or
                None if the dialog was cancelled or validation failed.
    """
    styles = fetch_text_styles(root)

    # Default return state.
    password = {"confirmed": False, "password": None}

    password_window = Toplevel(frame)
    create_window(password_window, "Set New Password", CS["pwd_prompt"])
    password_window.protocol("WM_DELETE_WINDOW", lambda: None)

    preset_label(
        password_window,
        text="Enter password:",
    ).pack(pady=(10, 2))

    password_entry_1 = preset_entry(password_window, show="*", width=30)
    password_entry_1.pack(pady=(0, 4))

    rule_labels = []
    for description, _ in PASSWORD_CRITERIA:
        label = preset_label(
            password_window,
            text=f"Needs: {description}",
            fg=CS["error"],
            font=styles["emphasis"],
            justify="center",
        )
        label.pack(pady=1)
        rule_labels.append(label)

    preset_label(
        password_window,
        text="Confirm password:",
    ).pack(pady=(4, 2))

    password_entry_2 = preset_entry(password_window, show="*", width=30)
    password_entry_2.pack(pady=(0, 6))

    button_frame = Frame(password_window)
    button_frame.pack(pady=10)

    submit_button = preset_button(
        button_frame,
        text="Submit",
        state="disabled",
    )
    submit_button.pack(side="left", padx=5)

    def refresh_checklist(*_):
        """
        Called on every keystroke in either entry field.

        Re-evaluates PASSWORD_CRITERIA against the current first-field value,
        updates each rule label's text and colour, and enables or disables
        the Submit button depending on whether all rules pass and both fields
        are identical.
        """
        candidate = password_entry_1.get()
        _, failures = validate_password(candidate)
        failure_set = set(failures)

        for label, (description, _) in zip(rule_labels, PASSWORD_CRITERIA):
            if description in failure_set:
                label.config(text=f"Needs: {description}", fg=CS["error"])
            else:
                label.config(text=f"Requirement fulfilled.", fg=CS["correct"])

        all_rules_pass = len(failures) == 0
        passwords_match = candidate == password_entry_2.get() and bool(candidate)

        submit_button.config(
            state="normal" if (all_rules_pass and passwords_match) else "disabled"
        )

    password_entry_1.bind("<KeyRelease>", refresh_checklist)
    password_entry_2.bind("<KeyRelease>", refresh_checklist)

    def validate_passwords():
        """
        Final check on Submit then updates the shared password dict
        and closes the dialog.
        """
        password_1 = password_entry_1.get().strip()
        password_2 = password_entry_2.get().strip()

        passed, failures = validate_password(password_1)

        if not password_1:
            messagebox.showerror(
                "Error",
                "Password cannot be empty.",
                parent=password_window,
            )
            return

        if not passed:
            messagebox.showerror(
                "Password Requirements Not Met",
                "Your password does not meet the following requirements:\n\n"
                + "\n".join(f"• {f}" for f in failures),
                parent=password_window,
            )
            return

        if password_1 != password_2:
            messagebox.showerror(
                "Error",
                "Passwords do not match. Please try again.",
                parent=password_window,
            )
            return

        password["confirmed"] = True
        password["password"] = password_1
        password_window.destroy()

    submit_button.config(command=validate_passwords)

    def cancel_password():
        password_window.destroy()

    preset_button(button_frame, text="Cancel", command=cancel_password).pack(
        side="left", padx=5
    )

    root.wait_window(password_window)

    return password


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# system_interfaces.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class BaseInterface:
    """
    Base class for all top-level Tkinter interface windows.
    Handles common setup tasks.
      - Creates and configures the Tk root window.
      - Stores self.window_bg, self.styles, self.main_frame.
      - Instantiates self.dbm (DatabaseManagement).
      - Checks for and creates the database if absent.
      - Initialises self.current_section_frame to None.
      - Binds WM_DELETE_WINDOW to a safe quit handler.
      - Navigates to the first view through startup().
      - Starts the Tk mainloop.

    Subclasses must define:
      WINDOW_TITLE  (str) — the window title bar text.
      WINDOW_BG_KEY (str) — a key from the CS colour scheme dict.
      startup() — returns the view method to show on startup.

    Subclasses may override on_close() to customise the window-close
    behaviour (default: quit the mainloop and exit the process).
    """

    WINDOW_TITLE = ""
    WINDOW_BG_KEY = ""

    def startup(self):
        """
        Returns the view method that should be shown immediately after
        the window opens.

        Returns:
            callable: A bound method that accepts a Frame argument or None if not overridden.
        """
        return None

    def __init__(self):
        """
        Builds the window, sets up shared state, navigates to the first
        view and starts the mainloop.
        """
        self.window_bg = CS[self.WINDOW_BG_KEY]

        self.interface_root = Tk()

        window_title = self.WINDOW_TITLE

        self.main_frame, self.styles = create_window(
            self.interface_root,
            window_title,
            self.window_bg,
            is_main_frame=True,
        )

        self.interface_root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.dbm = DatabaseManagement(DB_PATH)

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.dbm.check_expired_guest_account()
        self.dbm.apply_daily_login_bonus()

        self.current_section_frame = None

        set_view(self, self.startup())

        self.interface_root.mainloop()

    def on_close(self):
        """
        Default window-close handler: stops the mainloop and exits the
        process.
        """
        self.interface_root.quit()
        sys.exit(0)


class AdminInterface(BaseInterface):
    """
    Administrator login screen and top-level navigation interface.
    Gives access to the Admin Console and the Casino Interface.

    Starts at the password check screen. On successful authentication,
    the administrator may open the console or access the casino.
    """

    WINDOW_TITLE = "One Less Time Casino - Administrator Interface"
    WINDOW_BG_KEY = "admin"

    def startup(self):
        return self.administrative_check

    def administrative_check(self, frame):
        """
        Renders a password entry form for authentication.
        On a correct password, navigates to the main admin interface.
        On an incorrect password, displays an error and clears the entry field.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter Administrator Password:").pack(pady=5)

        password_entry = preset_entry(frame, show="*")
        password_entry.pack(pady=5)

        def submit():
            """
            Reads the password entry field and verifies it against the stored
            administrator password hash. Navigates to the interface on success
            or shows an error dialog on failure.
            """
            password = password_entry.get()
            result = self.dbm.admin_password_check(password)

            if result.get("found") and result.get("verified"):
                set_view(self, self.interface_menu)
            else:
                messagebox.showerror(
                    "Error", "Incorrect password", parent=self.interface_root
                )
                password_entry.delete(0, "end")

        preset_button(frame, text="Submit", command=submit).pack(pady=10)

    def interface_menu(self, frame):
        """
        Renders the main administrator navigation menu with options to access
        the Admin Console, the Casino Interface or exit the application.
        Also logs the administrator login event to the database.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Welcome Administrator", font=self.styles["heading"]
        ).pack(pady=20)

        self.dbm.admin_logged_in()

        buttons = [
            ("Access Admin Console", self.admin_console),
            ("Access Casino", self.access_casino),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=3)

    def admin_console(self):
        """
        Opens the Admin Console window by instantiating the AdminConsole class.
        """

        AdminConsole()

    def access_casino(self):
        """
        Opens the Casino Interface in administrator mode by instantiating
        CasinoInterface with administrator=True.
        """

        self.interface_root.destroy()

        CasinoInterface(True)


class AdminConsole(BaseInterface):
    """
    Administrator console providing access to password management,
    encryption software, database management and user management.
    Sensitive operations are protected behind a master password.
    """

    WINDOW_TITLE = "One Less Time Casino - Administrative Console"
    WINDOW_BG_KEY = "admin"
    MASTER_PASSWORD = "Master_Password"

    def startup(self):
        return self.show_console_menu

    def show_console_menu(self, frame):
        """
        Renders the main admin console menu with navigation buttons for all
        available administrative operations.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Administrative Console",
            font=self.styles["heading"],
        ).pack(pady=(0, 20))

        buttons = [
            (
                "Change Administrative Password",
                lambda: set_view(self, self.change_admin_password),
            ),
            ("Access Encryption Software", self.encryption_software_access),
            (
                "Database Management",
                lambda: set_view(self, self.show_database_management),
            ),
            ("User Management", lambda: set_view(self, self.show_user_management)),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def change_admin_password(self, frame):
        """
        Renders the admin password change flow. Requires master password
        verification before prompting for the current admin password and then
        uses passwords_confirmation to set a new one. Displays appropriate
        error or success dialogs at each stage and returns to the main menu
        on completion or cancellation.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning(
                "Warning", f"'{DB_PATH}' does not exist.", parent=self.interface_root
            )
            return
        if messagebox.askyesno(
            "Confirm password change",
            "Are you sure you want to change the administrative password to the system?",
            parent=self.interface_root,
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    preset_label(
                        frame,
                        text="Enter Old Administrator Password:",
                        font=self.styles["heading"],
                    ).pack(pady=20)

                    password_entry = preset_entry(frame, show="*")
                    password_entry.pack(pady=5)

                    def submit():
                        """
                        Verifies the current admin password and then launches the
                        password confirmation dialog to capture and store the
                        new password. Returns to the main menu on success.
                        """
                        old_password = password_entry.get()
                        result = self.dbm.admin_password_check(old_password)

                        if not (result.get("found") and result.get("verified")):
                            messagebox.showerror(
                                "Error",
                                "Incorrect password",
                                parent=self.interface_root,
                            )
                            password_entry.delete(0, "end")
                            return

                        password_state = passwords_confirmation(
                            frame, self.interface_root
                        )
                        if not password_state["confirmed"]:
                            return

                        new_password = password_state["password"]
                        self.dbm.change_admin_password(new_password)

                        messagebox.showinfo(
                            "Success",
                            "Administrator password updated successfully!",
                            parent=self.interface_root,
                        )

                        set_view(self, self.show_console_menu)

                    preset_button(
                        frame,
                        text="Next",
                        width=25,
                        command=submit,
                    ).pack(pady=10)

                    preset_button(
                        frame,
                        text="Back",
                        width=25,
                        command=lambda: set_view(self, self.show_console_menu),
                    ).pack(pady=10)

                else:
                    messagebox.showerror(
                        "Error",
                        "Incorrect password. Operation cancelled.",
                        parent=self.interface_root,
                    )
                    set_view(self, self.show_console_menu)

            except Exception as error:
                messagebox.showerror(
                    "Error", f"An error occurred: {error}", parent=self.interface_root
                )
        else:
            messagebox.showinfo(
                "Cancelled", "Password change cancelled.", parent=self.interface_root
            )
            set_view(self, self.show_console_menu)

    def encryption_software_access(self):
        """
        Opens the Encryption Software window by instantiating
        EncryptionSoftware.
        """

        EncryptionSoftware()

    def show_database_management(self, frame):
        """
        Renders the database management submenu with options to create or
        delete the database, view table contents or return to the main menu.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Database Management", font=self.styles["heading"]
        ).pack(pady=10)

        buttons = [
            ("Create Database", self.create_database),
            ("Delete Database", self.delete_database),
            ("View Database", lambda: set_view(self, self.show_view_database)),
            ("Export Table to CSV", lambda: set_view(self, self.table_to_csv)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def create_database(self):
        """
        Prompts for confirmation and master password verification before
        creating the database.
        """
        if messagebox.askyesno(
            "Confirm Creation",
            f"Are you sure you want to create '{DB_PATH}'?\n Note: Nothing will change if the database is already present.",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    self.dbm.create_database()
                    messagebox.showinfo(
                        "Success",
                        f"'{DB_PATH}' created successfully.",
                        parent=self.interface_root,
                    )

                else:
                    messagebox.showerror(
                        "Error",
                        "Incorrect password. Operation cancelled.",
                        parent=self.interface_root,
                    )

            except Exception as error:
                messagebox.showerror("Error", f"Failed to create '{DB_PATH}': {error}")

    def delete_database(self):
        """
        Checks the database exists and then prompts for confirmation and master
        password verification before permanently deleting the database file.
        Displays a success or error message on completion.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{DB_PATH}' does not exist.")
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete '{DB_PATH}'?"
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.interface_root,
                )

                if password == self.MASTER_PASSWORD:
                    os.remove(DB_PATH)
                    messagebox.showinfo(
                        "Success",
                        f"'{DB_PATH}' deleted successfully.",
                        parent=self.interface_root,
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror("Error", f"Failed to delete '{DB_PATH}': {error}")

    def show_view_database(self, frame):
        """
        Renders a dropdown allowing the administrator to select a database
        table to view. On selection and confirmation, queries the table and
        navigates to the display view. Shows a warning if the database does
        not exist or the table is empty.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{DB_PATH}' does not exist.")
            return

        preset_label(
            frame, text="Select Table to View", font=self.styles["heading"]
        ).pack(pady=10)

        tables = [
            "db_logs",
            "admin_logs",
            "users",
            "user_poker_data",
            "user_poker_actions",
        ]

        dropdown = Combobox(
            frame, values=tables, state="readonly", font=self.styles["text"]
        )
        dropdown.pack(pady=10)

        def view_table():
            """
            Reads the selected table name from the dropdown, queries it through
            the database manager and navigates to the table display view.
            Shows an error if no table is selected or the result is empty.
            """
            selected_table = dropdown.get().strip()
            if not selected_table:
                messagebox.showerror("Error", "Please select a table first.")
                return

            dataframe = self.dbm.view_database(selected_table)

            if dataframe.empty:
                messagebox.showinfo(
                    "Info",
                    f"No data found in '{selected_table}'.",
                    parent=self.interface_root,
                )
                return

            set_view(self, lambda f: self.display_table(f, dataframe, selected_table))

        preset_button(
            frame,
            text="View Table",
            width=25,
            command=view_table,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_database_management),
        ).pack(pady=5)

    def display_table(self, frame, dataframe, table):
        """
        Renders the contents of a database table in a scrollable Treeview
        widget with alternating row colours. Column widths are automatically
        sized based on the widest value in each column.

        Args:
            frame (Frame): The parent frame to build the view into.
            dataframe (pd.DataFrame): The table data to display.
            table (str): The name of the table, shown in the heading.
        """
        preset_label(frame, text=f"'{table}' Table", font=self.styles["heading"]).pack(
            pady=10
        )

        # Frame to hold Treeview.
        inner_frame = Frame(frame)
        inner_frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree_scroll_y = Scrollbar(inner_frame, orient="vertical")
        tree_scroll_y.pack(side="right", fill="y")

        tree_scroll_x = Scrollbar(inner_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")

        tree = Treeview(
            inner_frame,
            columns=list(dataframe.columns),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )
        tree.pack(expand=True, fill="both")

        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)

        for column in dataframe.columns:
            tree.heading(column, text=column)
            max_width = (
                max(dataframe[column].astype(str).map(len).max(), len(column)) * 10
            )
            tree.column(column, width=max_width, anchor="w")

        # Insert rows with alternating tags for styling, '_' is used to prevent
        # issues with special characters in the data interfering with tag assignment.
        for count, (_, row) in enumerate(dataframe.iterrows()):
            tag = "evenrow" if count % 2 == 0 else "oddrow"
            tree.insert("", "end", values=list(row), tags=(tag,))
        tree.tag_configure("evenrow", background=CS["table_even"])
        tree.tag_configure("oddrow", background=CS["table_odd"])

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_view_database),
        ).pack(pady=5)

    def table_to_csv(self, frame):
        """
        Renders a dropdown allowing the administrator to select a database
        table to export. On selection and confirmation, prompts for a save
        location and exports the table to a CSV file. Shows a warning if
        the database does not exist.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{DB_PATH}' does not exist.")
            return

        preset_label(
            frame, text="Select Table to Export", font=self.styles["heading"]
        ).pack(pady=10)

        tables = [
            "db_logs",
            "admin_logs",
            "users",
            "user_poker_data",
            "user_poker_actions",
        ]

        dropdown = Combobox(
            frame, values=tables, state="readonly", font=self.styles["text"]
        )
        dropdown.pack(pady=10)

        def export_table():
            """
            Reads the selected table name from the dropdown, prompts for a
            save location and exports the table to CSV. Shows an error if no
            table is selected or no save location is provided.
            """
            selected_table = dropdown.get().strip()
            if not selected_table:
                messagebox.showerror("Error", "Please select a table first.")
                return

            save_path = filedialog.asksaveasfilename(
                title="Save CSV",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )

            if not save_path:
                messagebox.showerror("Returning to Menu", "No save location provided.")
                return

            try:
                self.dbm.export_table_to_csv(selected_table, save_path)
                messagebox.showinfo(
                    "Success",
                    f"'{selected_table}' exported to:\n{save_path}",
                    parent=self.interface_root,
                )
            except Exception as error:
                messagebox.showerror(
                    "Error",
                    f"Failed to export '{selected_table}': {error}",
                    parent=self.interface_root,
                )

        preset_button(
            frame,
            text="Export to CSV",
            width=25,
            command=export_table,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_database_management),
        ).pack(pady=5)

    def show_user_management(self, frame):
        """
        Renders the user management submenu with options to fetch, add, edit,
        or delete user records. Shows a warning if the database does not exist.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{DB_PATH}' does not exist.")
            return

        preset_label(frame, text="User Management", font=self.styles["heading"]).pack(
            pady=10
        )

        buttons = [
            ("Return User Information", lambda: set_view(self, self.fetch_user_record)),
            ("Add User", lambda: set_view(self, self.add_user)),
            ("Edit User", lambda: set_view(self, self.edit_user)),
            ("Delete User", lambda: set_view(self, self.delete_user)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            preset_button(frame, text=text, width=30, command=command).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Renders a search form allowing lookup by user ID, username or both.
        When both are provided, verifies that they refer to the same user
        before proceeding. Navigates to the record display view on a
        successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter User ID", font=self.styles["heading"]).pack(
            pady=10
        )

        user_id_entry = preset_entry(frame)
        user_id_entry.pack(pady=5)

        preset_label(frame, text="Enter Username", font=self.styles["heading"]).pack(
            pady=10
        )
        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def lookup_user():
            """
            Resolves the entered user ID and/or username to a full user record.
            Validates cross-referencing when both are provided and then navigates
            to the record display view. Shows appropriate errors for mismatches,
            non-numeric IDs or missing users.
            """
            if user_id_entry.get().strip() and username_entry.get().strip():
                user_id = user_id_entry.get().strip()
                username = username_entry.get().strip()
                if user_id.isdigit():
                    check_w_user_id = self.dbm.fetch_username(int(user_id))
                    check_w_username = self.dbm.fetch_user_id(username)
                    if check_w_user_id["username"] != username or check_w_username[
                        "user_id"
                    ] != int(user_id):
                        messagebox.showerror(
                            "Error", "User ID and Username do not match."
                        )
                        return
                    record = self.dbm.fetch_user_record(user_id=int(user_id))
                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            elif user_id_entry.get().strip():
                user_id = user_id_entry.get().strip()
                if user_id.isdigit():
                    record = self.dbm.fetch_user_record(user_id=int(user_id))
                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()
                record = self.dbm.fetch_user_record(username=username)
                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        preset_button(
            frame,
            text="Search",
            width=25,
            command=lookup_user,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def display_user_record(self, frame, record):
        """
        Renders a read-only view of a user's full record, including username,
        password hash, account type, balance, creation timestamp and
        termination status with details if applicable.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary as returned by
                           fetch_user_record().
        """
        preset_label(
            frame,
            text=f"User Information: {record.get('username')}",
            font=self.styles["heading"],
        ).pack(pady=10)

        for key, value in [
            ("Username", record["username"]),
            ("Password", record["password_hash"]),
            ("Account Type", "Registered" if record["registered"] else "Guest"),
            ("Balance", record["balance"]),
            ("Creation Time", record["created_at"]),
        ]:
            preset_label(frame, text=f"{key}: {value}", anchor="w").pack(
                fill="x", padx=20, pady=2
            )

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=10)

    def add_user(self, frame):
        """
        Renders a username input form for creating a new user. Validates that
        the username is non-empty and not already taken before proceeding to
        account type selection.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter Username", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Reads the entered username, validates it is non-empty and unique,
            then navigates to the account type selection view.
            """
            username = username_entry.get().strip()

            if not username:
                messagebox.showinfo("Cancelled", "No username provided.")
                set_view(self, self.show_user_management)
                return

            if self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username already exists.")
                return

            set_view(self, lambda f: self.choose_account_type(f, username))

        preset_button(frame, text="Next", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def choose_account_type(self, frame, username):
        """
        Presents a choice between creating a registered account (with password)
        or a temporary guest account (without password). Navigates to password
        creation for registered accounts or creates the guest account
        immediately and returns to user management.

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username for the account being created.
        """
        preset_label(frame, text="Account Type", font=self.styles["heading"]).pack(
            pady=10
        )

        def register():
            """Navigates to the password creation view for a registered account."""
            set_view(self, lambda f: self.create_password(f, username))

        def guest():
            """
            Creates a temporary guest account with no password and navigates
            back to the user management menu.
            """
            self.dbm.register_user(username, None, False)

            messagebox.showinfo(
                "Success", f"Temporary guest account '{username}' created successfully!"
            )

            set_view(self, self.show_user_management)

        preset_button(
            frame,
            text="Register Account",
            width=25,
            command=register,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Temporary Guest Account",
            width=25,
            command=guest,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog in a loop until a valid
        confirmed password is provided and then creates the registered user
        account and returns to the user management menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        while True:
            password_state = passwords_confirmation(frame, self.interface_root)
            if password_state["confirmed"]:
                self.dbm.register_user(username, password_state["password"], True)

                messagebox.showinfo(
                    "Success", f"Account for '{username}' created successfully!"
                )

                set_view(self, self.show_user_management)
                break

    def edit_user(self, frame):
        """
        Renders a search form for locating a user to edit, accepting a user ID,
        username or both. Cross-validates when both are provided. Navigates to
        the edit form on a successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(frame, text="Enter User ID:", font=self.styles["heading"]).pack(
            pady=10
        )

        user_id_entry = preset_entry(frame)
        user_id_entry.pack(pady=5)

        preset_label(frame, text="Enter Username:", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Resolves the entered user ID and/or username to a full user record,
            cross-validating when both are provided and then navigates to the edit
            form. Shows appropriate errors for mismatches, non-numeric IDs or
            missing users.
            """
            if user_id_entry.get().strip() and username_entry.get().strip():
                user_id = user_id_entry.get().strip()
                username = username_entry.get().strip()
                if user_id.isdigit():
                    check_w_user_id = self.dbm.fetch_username(int(user_id))
                    check_w_username = self.dbm.fetch_user_id(username)
                    if check_w_user_id["username"] != username or check_w_username[
                        "user_id"
                    ] != int(user_id):
                        messagebox.showerror(
                            "Error", "User ID and Username do not match."
                        )
                        return

                    record = self.dbm.fetch_user_record(user_id=int(user_id))

                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return

                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            elif user_id_entry.get().strip():
                user_id = user_id_entry.get().strip()
                if user_id.isdigit():
                    record = self.dbm.fetch_user_record(user_id=int(user_id))

                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()

                record = self.dbm.fetch_user_record(username=username)

                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        preset_button(frame, text="Next", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def show_edit_form(self, frame, record):
        """
        Renders an editable form pre-populated with the current user record.
        Allows changing username, password, account type, balance and
        termination status. Calls change_user_record with only the fields
        that have been filled in.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The current user record dictionary.
        """
        preset_label(
            frame,
            text=f"Edit User:\n{record['user_id']} | {record['username']}",
            font=self.styles["heading"],
        ).pack(pady=10)

        preset_label(frame, text="New Username:").pack()
        username_entry = preset_entry(frame)
        username_entry.pack()

        preset_label(frame, text="New Password:").pack()
        password_entry = preset_entry(frame, show="*")
        password_entry.pack()

        preset_label(frame, text="New Account Type:").pack()
        type_box = Combobox(frame, values=["Registered", "Temporary"], state="readonly")
        type_box.set("Registered" if record.get("registered") else "Temporary")
        type_box.pack()

        preset_label(frame, text="New Balance:").pack()
        balance_entry = preset_entry(frame)
        balance_entry.insert(0, str(record.get("balance", 0)))
        balance_entry.pack()

        def save():
            """
            Collects all non-empty field values from the form, validates the
            balance as a float then calls change_user_record to
            apply the changes.
            """
            kwargs = {"user_id": record["user_id"]}

            if username_entry.get().strip():
                kwargs["new_username"] = username_entry.get().strip()

            if password_entry.get().strip():
                kwargs["new_password"] = password_entry.get().strip()

            kwargs["new_account_type"] = type_box.get() == "Registered"

            try:
                kwargs["new_balance"] = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance.")
                return

            self.dbm.change_user_record(**kwargs)

            messagebox.showinfo("Success", "User updated successfully.")
            set_view(self, self.show_user_management)

        preset_button(
            frame,
            text="Save Changes",
            width=25,
            command=save,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def delete_user(self, frame):
        """
        Renders a username input form for deleting a user account. Prevents
        deletion of the Administrator account. Prompts for confirmation before
        permanently removing the record.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame, text="Enter Username to Delete", font=self.styles["heading"]
        ).pack(pady=10)

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Validates the entered username exists and is not the Administrator
            account, confirms deletion with the user and then resolves the
            username to a user ID and calls delete_user_record.
            """
            username = username_entry.get().strip()
            if not username or not self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username does not exist.")
                return

            if username == "Administrator":
                messagebox.showerror(
                    "Error", "Cannot delete the Administrator account."
                )
                return

            if messagebox.askyesno("Confirm Delete", f"Delete user '{username}'?"):
                result = self.dbm.fetch_user_id(username)
                if result["found"]:
                    self.dbm.delete_user_record(result["user_id"])

                messagebox.showinfo("Success", f"User '{username}' deleted.")
                set_view(self, self.show_user_management)

        preset_button(frame, text="Delete", width=25, command=next).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)


DEFAULT_SETTINGS = {
    # Harrogate Hold 'Em.
    "bot_count": 3,
    "bot_balance": 1000,
    "small_blind": 50,
    "big_blind": 100,
    "bot_difficulty": 50,
    # Tournament.
    "tournament_mode": False,
    "tournament_rounds": 5,
}

# Minimum rounds played before a user may enable Tournament Mode.
TOURNAMENT_MIN_ROUNDS = 25

# Tournament balance constants.
TOURNAMENT_USER_START_BALANCE = 50_000
TOURNAMENT_BOT_START_BALANCE = 50_000

# Fixed number of bots in every tournament.
TOURNAMENT_BOT_COUNT = 5

# Blind escalation: blinds increase by 50% every 3 rounds up to these caps.
TOURNAMENT_SMALL_BLIND_CAP = 2_000
TOURNAMENT_BIG_BLIND_CAP = 4_000


class CasinoInterface(BaseInterface):
    """
    Main casino interface for users and administrators. Handles login,
    account management, game selection and mode-specific settings for
    tournaments.
    """

    WINDOW_BG_KEY = "casino"

    def __init__(self, administrator=False, user_data=None):
        """
        Stores constructor arguments as instance state and then calls
        super().__init__() which builds the window, checks the database,
        and starts the mainloop.

        Args:
            administrator (bool): If True, launches in administrator mode,
                                  bypassing login.
            user_data (dict, optional): Pre-populated user session dict with
                                        keys 'user_id', 'username',
                                        'administrator'. Defaults to an
                                        unsigned-in state if None.
        """
        self._administrator = administrator
        self._user_data_init = user_data

        # Default game settings for HHE, set before mainloop starts.
        self.settings = dict(DEFAULT_SETTINGS)

        super().__init__()

    # Uses a property to dynamically generate the window title based on administrator
    # status, since this is not known until after the constructor arguments are processed.
    @property
    def WINDOW_TITLE(self):
        """
        Dynamic window title based on administrator mode.
        """
        return (
            "One Less Time Casino — Administrator Access"
            if self._administrator
            else "One Less Time Casino"
        )

    def setup_user_data(self):
        """
        Initialises self.user_data from the constructor arguments.
        """
        if self._user_data_init is not None:
            self.user_data = self._user_data_init
        else:
            self.user_data = {
                "user_id": None,
                "username": None,
                "administrator": False,
            }

        if self._administrator:
            result = self.dbm.fetch_user_id("Administrator")
            self.user_data["user_id"] = result["user_id"] if result["found"] else None
            self.user_data["username"] = "Administrator"
            self.user_data["administrator"] = True

    def startup(self):
        # User data must be ready before any view is rendered.
        self.setup_user_data()
        return self.casino_menu

    # Helpers.

    def user_linked(self):
        """
        Returns True if a user account is currently linked to this session.

        Returns:
            bool: True if a user is linked, False otherwise.
        """
        return bool(self.user_data.get("username"))

    def require_linked(self, action_label="this"):
        """
        Shows a warning dialog if no account is linked.

        Args:
            action_label (str): Short name for what was attempted, used in
                                the message (e.g. "the Game Menu").

        Returns:
            bool: True if the account is linked and the caller may proceed,
                  False if the user should be blocked.
        """
        if self.user_linked():
            return True
        messagebox.showwarning(
            "Account Required",
            f"You must be signed in to access {action_label}.\n\n"
            "Please register or log in first.",
        )
        return False

    def fetch_rounds_played(self):
        """
        Retrieves the number of poker rounds the current user has played
        from the database. Returns with TOURNAMENT_MIN_ROUNDS for
        administrators or 0 if the data cannot be fetched.

        Returns:
            int: Rounds played or 0 on failure / admin session.
        """
        if self.user_data.get("administrator"):
            # Administrators are never blocked by the rounds threshold.
            return TOURNAMENT_MIN_ROUNDS

        user_id = self.user_data.get("user_id")
        if not user_id:
            return 0

        try:
            rounds_played = self.dbm.fetch_total_rounds(user_id)
            return int(rounds_played["rounds_played"]) if rounds_played else 0
        except Exception:
            return 0

    def casino_menu(self, frame):
        """
        Displays the main casino menu. Displays a sign-in prompt if no user
        is logged in or a personalised welcome message if one is.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Welcome to\nOne Less Time Casino",
            font=self.styles["heading"],
        ).pack(pady=15)

        linked = self.user_linked()

        if not linked:
            preset_label(
                frame,
                text="Please sign in.\nIf you do not have an account please either register or create a guest account.",
                font=self.styles["emphasis"],
            ).pack(pady=10)

            preset_button(
                frame,
                text="Sign Up",
                width=30,
                command=self.user_register,
            ).pack(pady=5)

            preset_button(
                frame,
                text="Login",
                width=30,
                command=self.user_login_setup,
            ).pack(pady=5)
        else:
            preset_label(
                frame,
                text=f"Welcome, {self.user_data['username']}",
                font=self.styles["subheading"],
            ).pack(pady=10)

            preset_button(
                frame,
                text="Account Information",
                width=30,
                command=lambda: set_view(self, self.fetch_user_record),
            ).pack(pady=5)

            preset_button(
                frame,
                text="Game Menu",
                width=30,
                command=lambda: set_view(self, self.show_game_menu),
            ).pack(pady=5)

        preset_button(
            frame,
            text="Exit Casino",
            width=30,
            command=self.casino_exit,
        ).pack(pady=5)

    def show_game_menu(self, frame):
        """
        Displays the game selection menu. Requires an account to be linked;
        redirects to the main menu with a warning if not.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("the Game Menu"):
            set_view(self, self.casino_menu)
            return

        preset_label(
            frame,
            text="Game Menu",
            font=self.styles["heading"],
        ).pack(pady=20)

        buttons = [
            ("WhiteJoe", self.whitejoe_rules),
            ("Harrogate Hold 'Em", self.hhe_rules),
            ("Leaderboard", lambda: set_view(self, self.show_leaderboard)),
            ("Game Settings", lambda: set_view(self, self.game_settings)),
            ("Return to Main Menu", lambda: set_view(self, self.casino_menu)),
        ]

        for text, command in buttons:
            preset_button(
                frame,
                text=text,
                width=30,
                command=command,
            ).pack(pady=5)

    def user_register(self):
        """
        Initiates the registration flow. If the administrator is already
        signed in, prompts for confirmation before proceeding.
        """
        if self.user_data["administrator"]:
            if not messagebox.askyesno(
                "Administrator",
                "You are already signed in as an administrator.  "
                "Register a new account?",
            ):
                return

        set_view(self, lambda f: self.username_input(f, registered=True))

    def user_login_setup(self):
        """
        Initiates the login flow. If the administrator is signed in, prompts
        for confirmation and clears the administrator flag if they choose to
        sign in as a different user.
        """
        if self.user_data["administrator"]:
            if messagebox.askyesno(
                "Administrator",
                "You are already signed in as an administrator.  "
                "Sign in with another account?",
            ):
                self.user_data["administrator"] = False
            else:
                return
        set_view(self, lambda f: self.username_input(f, registered=False))

    def username_input(self, frame, registered):
        """
        Displays a username input form used for both registration and login.

        Args:
            frame (Frame): The parent frame to build the view into.
            registered (bool): If True, validates uniqueness for registration.
        """
        preset_label(
            frame,
            text="Enter Username",
            font=self.styles["heading"],
        ).pack(pady=10)

        username_entry = preset_entry(frame)
        username_entry.pack(pady=5)

        def proceed():
            """Validates the username and routes to the next step."""
            username = username_entry.get().strip()
            if not username:
                messagebox.showinfo("Cancelled", "No username provided.")
                set_view(self, self.casino_menu)
                return

            if username.lower() == "administrator":
                messagebox.showerror(
                    "Error",
                    "The username 'Administrator' is reserved and may not be used.",
                )
                return

            if registered and self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username already exists.")
                return

            set_view(
                self,
                (
                    (lambda f: self.set_account_type(f, username))
                    if registered
                    else (lambda f: self.user_login(f, username))
                ),
            )

        preset_button(
            frame,
            text="Next",
            width=25,
            command=proceed,
        ).pack(pady=10)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=5)

    def set_account_type(self, frame, username):
        """
        Presents a choice between a registered account (with password) or a
        temporary guest account (without password).

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username for the account being created.
        """
        preset_label(frame, text="Account Type", font=self.styles["heading"]).pack(
            pady=10
        )

        def register():
            set_view(self, lambda f: self.create_password(f, username))

        def temporary():
            self.dbm.register_user(username, None, False)
            result = self.dbm.fetch_user_id(username)
            self.user_data["user_id"] = result["user_id"] if result["found"] else None
            self.user_data["username"] = username
            messagebox.showinfo("Success", f"Temporary account '{username}' created.")
            set_view(self, self.casino_menu)

        for text, command in (
            ("Register Account", register),
            ("Temporary Guest Account", temporary),
            ("Back", lambda: set_view(self, self.casino_menu)),
        ):
            preset_button(
                frame,
                text=text,
                width=25,
                command=command,
            ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog, creates the registered user
        account on success and returns to the main casino menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        password_info = passwords_confirmation(frame, self.interface_root)
        if password_info["confirmed"]:
            self.dbm.register_user(username, password_info["password"], True)
            result = self.dbm.fetch_user_id(username)
            self.user_data["user_id"] = result["user_id"] if result["found"] else None
            self.user_data["username"] = username
            messagebox.showinfo(
                "Success", f"Account '{username}' created successfully."
            )
        else:
            messagebox.showinfo("Cancelled", "Password not set.  Returning to menu.")
        set_view(self, self.casino_menu)

    def user_login(self, frame, username):
        """
        Displays a password entry form for logging in as the given username.

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username attempting to log in.
        """
        if not self.dbm.fetch_user_presence(username).get("found"):
            messagebox.showerror("Error", f"Username '{username}' does not exist.")
            set_view(self, lambda f: self.username_input(f, registered=False))
            return

        preset_label(
            frame,
            text=f"Login for '{username}'",
            font=self.styles["heading"],
        ).pack(pady=10)

        preset_label(frame, text="Enter Password:", font=self.styles["text"]).pack(
            pady=5
        )

        password_entry = preset_entry(frame, show="*", font=self.styles["text"])
        password_entry.pack(pady=5)

        def submit_password():
            """Verifies the password and navigates accordingly."""
            password = password_entry.get().strip()
            result = self.dbm.verify_user_password(username, password)

            if result.get("found") and result.get("verified"):
                self.dbm.record_user_login(username)
                user_id = self.dbm.fetch_user_id(username)
                self.user_data["user_id"] = (
                    user_id["user_id"] if user_id["found"] else None
                )
                self.user_data["username"] = username
                self.user_data["administrator"] = False
                messagebox.showinfo("Success", f"Welcome back, {username}.")

                set_view(self, self.casino_menu)

            elif result.get("found") and not result.get("verified"):
                messagebox.showerror("Error", "Incorrect password.")
                password_entry.delete(0, "end")
                set_view(self, lambda f: self.username_input(f, registered=False))

            else:
                messagebox.showerror("Error", "Username not found or login failed.")
                set_view(self, lambda f: self.username_input(f, registered=False))

        preset_button(
            frame,
            text="Login",
            width=25,
            command=submit_password,
        ).pack(pady=5)

        preset_button(
            frame,
            text="Cancel",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Retrieves and displays the full record for the currently signed-in
        user. Redirects with a warning if no user is linked.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("Account Information"):
            set_view(self, self.casino_menu)
            return

        record = self.dbm.fetch_user_record(username=self.user_data["username"])
        if not record:
            messagebox.showinfo("Not Found", "User record not found.")
            return

        set_view(self, lambda f: self.display_user_record(f, record))

    def display_user_record(self, frame, record):
        """
        Displays a read-only view of the current user's account information.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary.
        """
        preset_label(
            frame,
            text=f"User Information: {record.get('username')}",
            font=self.styles["heading"],
        ).pack(pady=10)

        for label, value in [
            ("Username", record["username"]),
            ("Account Type", "Registered" if record["registered"] else "Guest"),
            ("Balance", record["balance"]),
            ("Created", record["created_at"]),
        ]:
            preset_label(
                frame,
                text=f"{label}: {value}",
                anchor="w",
            ).pack(fill="x", padx=20, pady=2)

        preset_button(
            frame,
            text="Back",
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=10)

    def casino_exit(self):
        """
        Prompts for confirmation before exiting the casino. Displays a
        thank-you and responsible gambling message on confirmation.
        """
        if messagebox.askyesno("Exit Casino", "Do you wish to exit the casino?"):
            messagebox.showinfo(
                "Thank You for Visiting",
                "Thank you for visiting One Less Time Casino.  "
                "And remember, when the fun stops, stop.",
            )
            self.interface_root.destroy()
            sys.exit(0)

    def game_settings(self, frame):
        """
        Displays the Harrogate Hold 'Em settings panel.
        Requires an account to be linked; redirects if not.
        """
        if not self.require_linked("Game Settings"):
            set_view(self, self.casino_menu)
            return

        canvas = Canvas(frame, bg=self.window_bg, highlightthickness=0)
        scrollbar = Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.window_bg)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        preset_label(
            scrollable_frame, text="Game Settings", font=self.styles["heading"]
        ).pack(pady=(10, 4))

        # Live variables.
        v_bot_count = IntVar(value=self.settings["bot_count"])
        v_small_blind = StringVar(value=str(self.settings["small_blind"]))
        v_big_blind = StringVar(value=str(self.settings["big_blind"]))
        v_bot_diff = IntVar(value=self.settings["bot_difficulty"])
        v_tournament = BooleanVar(value=self.settings["tournament_mode"])
        v_total_rounds = IntVar(value=self.settings["tournament_rounds"])

        def section(parent, title):
            preset_label(
                parent, text=title, font=self.styles["subheading"], anchor="w"
            ).pack(fill="x", padx=30, pady=(15, 5))

        def settings_grid(parent):
            container = Frame(parent, bg=self.window_bg)
            container.pack(fill="x", padx=30, pady=5)
            return container

        def grid_row(parent, row, label_text, widget):
            preset_label(
                parent,
                text=label_text,
                bg=self.window_bg,
                fg=CS["casino_text"],
                font=self.styles["text"],
                relief="flat",
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=4)
            widget.grid(row=row, column=1, sticky="w", padx=10, pady=4)

        section(scrollable_frame, "Table Settings (Non-Tournament)")

        grid = settings_grid(scrollable_frame)

        grid_row(
            grid,
            0,
            "Number of bots (1–9):",
            Spinbox(
                grid,
                from_=1,
                to=9,
                textvariable=v_bot_count,
                width=6,
                font=self.styles["text"],
            ),
        )
        grid_row(
            grid,
            1,
            "Small blind (£):",
            preset_entry(grid, textvariable=v_small_blind, width=10),
        )
        grid_row(
            grid,
            2,
            "Big blind (£):",
            preset_entry(grid, textvariable=v_big_blind, width=10),
        )

        section(scrollable_frame, "Bot Difficulty (Non-Tournament)")

        difficulty_frame = Frame(scrollable_frame, bg=self.window_bg)
        difficulty_frame.pack(fill="x", padx=30)

        difficulty_label = preset_label(
            difficulty_frame,
            text=f"Current: {v_bot_diff.get()}",
            font=self.styles["emphasis"],
            anchor="w",
        )
        difficulty_label.pack(anchor="w")

        Scale(
            difficulty_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=v_bot_diff,
            length=350,
            command=lambda v: difficulty_label.config(text=f"Current: {int(float(v))}"),
        ).pack(anchor="w", pady=5)

        section(scrollable_frame, "Tournament Mode")

        preset_label(
            scrollable_frame,
            text=(
                "Play multiple rounds against bots.\n"
                f"In tournament mode: {TOURNAMENT_BOT_COUNT} bots, each starting with "
                f"£{TOURNAMENT_BOT_START_BALANCE:,} and you start with "
                f"£{TOURNAMENT_USER_START_BALANCE:,}.\n"
                "Bot difficulties are evenly distributed from 50 to 100.\n"
                "Blinds escalate progressively each round.\n"
                "Win condition: win the betting round (pot).\n"
                "Unlocks after 25 rounds played."
            ),
            font=self.styles["emphasis"],
            bg=self.window_bg,
            fg=CS["casino_text"],
            relief="flat",
            anchor="w",
            justify="left",
            wraplength=650,
        ).pack(fill="x", padx=30, pady=(0, 10))

        rounds_played = self.fetch_rounds_played()
        rounds_needed = max(0, TOURNAMENT_MIN_ROUNDS - rounds_played)

        if rounds_needed > 0:
            preset_label(
                scrollable_frame,
                text=(
                    f"Locked — play {rounds_needed} more round"
                    f"{'s' if rounds_needed != 1 else ''} to unlock."
                ),
                font=self.styles["emphasis"],
                anchor="w",
            ).pack(fill="x", padx=30, pady=2)
            self.settings["tournament_mode"] = False
            v_tournament.set(False)
        else:
            toggle_frame = Frame(scrollable_frame, bg=self.window_bg)
            toggle_frame.pack(fill="x", padx=30)

            preset_label(toggle_frame, text="Enable Tournament Mode:", anchor="w").pack(
                side="left"
            )
            Checkbutton(
                toggle_frame,
                variable=v_tournament,
                bg=self.window_bg,
                activebackground=self.window_bg,
                highlightthickness=0,
                bd=0,
            ).pack(side="left", padx=10)

            t_grid = settings_grid(scrollable_frame)
            grid_row(
                t_grid,
                0,
                "Number of rounds:",
                Spinbox(
                    t_grid,
                    from_=1,
                    to=50,
                    textvariable=v_total_rounds,
                    width=6,
                    font=self.styles["text"],
                ),
            )

        def save_settings():
            """Validates and saves Standard and Tournament settings."""

            def parse_positive_int(raw, label, fallback):
                """
                Parses raw as a positive integer.
                Returns (value, error_string_or_None).
                """
                try:
                    value = int(raw)
                except (ValueError, TypeError):
                    return fallback, f"{label} must be a whole number."
                if value <= 0:
                    return fallback, f"{label} must be greater than 0."
                return value, None

            errors = []

            # Bot count — 1 to 9 inclusive.
            bot_count_raw = v_bot_count.get()
            try:
                bot_count = int(bot_count_raw)
                if not (1 <= bot_count <= 9):
                    raise ValueError
            except (ValueError, TypeError):
                errors.append("Bot count must be a whole number between 1 and 9.")
                bot_count = self.settings["bot_count"]

            # Small blind — positive integer.
            small_blind, err = parse_positive_int(
                v_small_blind.get(), "Small blind", self.settings["small_blind"]
            )
            if err:
                errors.append(err)

            # Big blind — positive integer and must be >= small blind.
            big_blind, err = parse_positive_int(
                v_big_blind.get(), "Big blind", self.settings["big_blind"]
            )
            if err:
                errors.append(err)
            elif big_blind < small_blind:
                errors.append(
                    f"Big blind (£{big_blind}) must be >= small blind (£{small_blind})."
                )
                big_blind = self.settings["big_blind"]

            # Bot difficulty — clamped 0–100
            try:
                difference = max(0, min(100, int(v_bot_diff.get())))
            except (ValueError, TypeError):
                difference = self.settings["bot_difficulty"]

            # Tournament rounds — integer >= 1.
            total_rounds_raw = v_total_rounds.get()
            try:
                total_rounds = int(total_rounds_raw)
                if total_rounds < 1:
                    raise ValueError
            except (ValueError, TypeError):
                errors.append("Tournament rounds must be a whole number of at least 1.")
                total_rounds = self.settings["tournament_rounds"]

            # Tournament toggle — locked out if the player hasn't played enough rounds.
            tournament_on = (
                False
                if self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS
                else bool(v_tournament.get())
            )

            if errors:
                messagebox.showerror(
                    "Settings Error", "\n".join(f"• {e}" for e in errors)
                )
                return

            self.settings.update(
                {
                    "bot_count": bot_count,
                    "small_blind": small_blind,
                    "big_blind": big_blind,
                    "bot_difficulty": difference,
                    "tournament_mode": tournament_on,
                    "tournament_rounds": total_rounds,
                }
            )

            messagebox.showinfo("Settings Saved", "Settings updated successfully.")

        def reset_defaults():
            """Resets all settings to DEFAULT_SETTINGS after confirmation."""
            if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
                self.settings = dict(DEFAULT_SETTINGS)
                set_view(self, self.game_settings)

        button_frame = Frame(scrollable_frame, bg=self.window_bg)
        button_frame.pack(fill="x", pady=20)

        for text, command in (
            ("Save Settings", save_settings),
            ("Reset to Defaults", reset_defaults),
            ("Back to Game Menu", lambda: set_view(self, self.show_game_menu)),
        ):
            preset_button(button_frame, text=text, command=command).pack(
                side="left", padx=10
            )

    def show_leaderboard(self, frame):
        """
        Displays a leaderboard showing the top tournament winners
        across all players in the database.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        preset_label(
            frame,
            text="Leaderboard",
            font=self.styles["heading"],
        ).pack(pady=(15, 5))

        try:
            player_data = self.dbm.fetch_tournament_scores()
        except Exception as e:
            print(f"Error fetching tournament scores: {e}")
            player_data = None

        if player_data is not None:
            preset_label(
                frame,
                text="Top Tournament Winners",
                font=self.styles["subheading"],
            ).pack(pady=(12, 2))
            Frame(frame, height=1, bg=CS["separator"]).pack(fill="x", padx=40)

            candidates = [
                p for p in player_data if p.get("tournament_wins", 0)
            ]  # Filter out players with no score.
            ranked = bubble_sort(candidates, key="tournament_wins", reverse=True)

            for index, entry in enumerate(ranked, 1):
                try:
                    result = self.dbm.fetch_username(entry["user_id"])
                    username = (
                        result["username"]
                        if result["found"]
                        else f"User {entry['user_id']}"
                    )
                except Exception:
                    username = f"User {entry['user_id']}"

                score = int(entry["tournament_wins"])
                preset_label(
                    frame,
                    text=f"  {index}.  {username:<20} with {score} wins.",
                    anchor="w",
                ).pack(fill="x", padx=60, pady=1)

            if not ranked:
                preset_label(
                    frame,
                    text="No tournament wins recorded yet.",
                ).pack(pady=4)

        preset_button(
            frame,
            text="Back to Game Menu",
            width=25,
            command=lambda: set_view(self, self.show_game_menu),
        ).pack(pady=14)

    def whitejoe_rules(self):
        """
        Launches the WhiteJoe rules window. Requires a linked account.
        On the user agreeing to the rules, starts the game.
        """
        if not self.require_linked("WhiteJoe"):
            return

        ShowGameRules(self.interface_root).show_whitejoe_rules(
            lambda: self.start_whitejoe()
        )

    def start_whitejoe(self):
        """
        Launches the WhiteJoe game, passing the current user data.
        """

        self.interface_root.destroy()

        WhiteJoe(self.user_data)

    def hhe_rules(self):
        """
        Launches the Harrogate Hold 'Em rules window. Requires a linked
        account. On the user agreeing to the rules, starts the game.
        """
        if not self.require_linked("Harrogate Hold 'Em"):
            return

        ShowGameRules(self.interface_root).show_hhe_rules(lambda: self.start_hhe())

    def start_hhe(self):
        """
        Builds a bot list from self.settings and launches Harrogate Hold 'Em.
        """
        settings = dict(self.settings)

        if (
            settings.get("tournament_mode")
            and self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS
        ):
            settings["tournament_mode"] = False

        tournament_mode = settings.get("tournament_mode", False)

        if tournament_mode:
            # Fixed tournament parameters — override anything the user saved.
            bot_count = TOURNAMENT_BOT_COUNT
            settings["bot_count"] = bot_count
            settings["bot_balance"] = TOURNAMENT_BOT_START_BALANCE

            # Evenly distribute difficulties from 50 to 100 inclusive.
            if bot_count == 1:
                difficulties = [75]
            else:
                step = (100 - 50) / (bot_count - 1)
                difficulties = [round(50 + step * i) for i in range(bot_count)]

            bot_list = list(DEFAULT_BOT_LIST)
            random.shuffle(bot_list)
            bots = [
                [bot_list[index % len(bot_list)], difficulties[index]]
                for index in range(bot_count)
            ]
        else:
            bot_count = settings["bot_count"]
            difficulty = settings["bot_difficulty"]
            bot_list = list(DEFAULT_BOT_LIST)
            random.shuffle(bot_list)
            bots = [
                [bot_list[index % len(bot_list)], difficulty]
                for index in range(bot_count)
            ]

        self.interface_root.destroy()
        HarrogateHoldEm(self.user_data, settings, bots)


# GAME RULES DISPLAY


class ShowGameRules:

    WJ_RULES = """
        The aim of the game is to beat the dealer by getting higher than the dealer’s hand value.\n
        To beat the dealer you must either:\n
        \t1. Draw a hand value that is higher than the dealer’s hand value.\n
        \t2. The dealer draws a hand value that goes over 21.\n
        \t3. Draw a hand value of 21 on your first two cards, when the dealer does not.\n
        To lose the game:\n
        \t1. Your hand value exceeds 21.\n
        \t2. The dealers hand has a greater value than yours at the end of the round.\n
        You will be offered to place a bet with the amount of money you have, The screen will show how much you have in your possession.\n
        The dealer will then deal out your cards with 2 cards facing upwards for you and 1 card facing up and another hidden for dealer.\n\n
        To play your hand, first you add the card values together and get a hand total anywhere from 4 to 21.\n
        If you’re dealt a ten-value card and an Ace as your first two cards that means you got a Blackjack.\n
        Those get paid 3 to 2 (or 1.5 times your wager) immediately, without playing through the round, as long as the dealer doesn’t also have a Blackjack.\n
        If the dealer also has a Blackjack, you wouldn’t win anything but you also wouldn’t lose your original wager.\n
        You have 5 action to do in total which will decide how you play (The number is the prompt you have to enter in order for the action to take place):\n
        \t1. Hit ~ If you would like more cards to improve your hand total, the dealer will deal you more cards, one at a time, until you either “bust” (go over 21) or you choose to stand.\n
        \tThere is no limit on the number of cards you can take (other than going over a total of 21 obviously).\n
        \t2. Stand ~ If your first two cards are acceptable, you can stand and the dealer will move on to the next player.(Multiplayer not available yet).\n
        \t3. Double Down ~ If you have a hand total that is advantageous to you but you need to take an additional card you can double your initial wager and the dealer will deal you only 1 additional card.\n
        \t4. Surrender ~ If you don’t like your initial hand, you have the option of giving it up in exchange for half your original bet back.\n
        The dealer can only draw up to 16 and stand.
        Once again you are reminded to read the T&C's before playing.
        """

    HHE_RULES = """
        The aim of the game is to use your hole cards in combination with the community cards to make the best possible five-card poker hand.
        \t*Each player is dealt two cards face down (the 'hole cards')
        \t*Over several betting rounds, five more cards are (eventually) dealt face up in the middle of the table.
        \t*These face-up cards are called the 'community cards'. Each player is free to use the community cards in combination with their hole cards to build a five-card poker hand.
        The community cards are revealed in 3 stages, 3 community cards are revealed in the 1st stage and 1 community card in the others:
        \t*1st stage is called the 'Flop'.
        \t*2nd stage is called the 'Turn'.
        \t*3rd stage is called the 'River'.
        Your goal is to construct your five-card poker hands using the best available five cards out of the seven total cards (your two hole cards and the five community cards).
        You can do that by using both your hole cards in combination with three community cards, one hole card in combination with four community cards or no hole cards.
        If the cards on the table lead to a better combination, you can also play all five community cards and forget about yours.
        In a game of Texas hold'em you can do whatever works to make the best five-card hand.
        If the betting causes all but one player to fold, the lone remaining player wins the pot without having to show any cards.
        For that reason, players don't always have to hold the best hand to win the pot. It's always possible a player can 'bluff' and get others to fold better hands.
        The following are key aspects:
        Given that this is a virtual experience there is no physical button yet it's principles will remain the same.
        At the beginning of the game, one player will be chosen to have the marker.
        The marker determines which player at the table is the acting dealer, after the round the marker will rotate to the next player, a list will be published at the beginning of the game to state the order of the marker.
        The first two players immediately below the marker are the 'small blind' and a 'big blind' respectively.
        The player below of the dealer marker in the small blind receives the first card and then the dealer pitches cards around the table in a clockwise motion from player to player until each has received two starting cards
        The blinds are forced bets that begin the wagering, the blinds ensure there will be some level of 'action' on every hand
        In tournaments, the blinds are raised at regular intervals. You will be given the choice to join a simple 'cash game' or high stakes tournament consisting of multiple tables, each of increasing difficulty.
        The small blind is generally half the amount of the big blind, although this stipulation varies from table to table and can also be dependent on the game being played.
        The moments:
        *Preflop:
        \tThe first round of betting takes place right after each player has been dealt two hole cards. The first player to act is the player below the big blind. The first player has three options:
        \t*Call: match the amount of the big blind
        \t*Raise: increase the bet within the specific limits of the game
        \t*Fold: throw the hand away. If the player chooses to fold, they are out of the game and no longer eligible to win the current hand
        \tThe amount a player can raise to depends on the game that is being played. This setting can be changed depending on what you choose to play.
        \tAfter the first player acts, the play proceeds down the list with each player also having the same three options — to call, to raise or fold.
        \tOnce the last bet is called and the action is 'closed', the preflop round is over and play moves on to the flop.
        *The Flop:
        \tAfter the first preflop betting round has been completed, the first three community cards are dealt and a second betting round follows involving only the players who have not folded already.
        \tIn this betting round (and subsequent ones), the action starts with the first active player to the left of the button.
        \tAlong with the options to bet, call, fold or raise, a player now has the option to 'check' if no betting action has occurred beforehand. A check simply means to pass the action to the next player in the hand.
        \tAgain betting continues until the last bet or raise has been called (which closes the action). It also can happen that every player simply chooses not to bet and checks around the 'table', which also ends the betting round.
        *The Turn:
        \tThe fourth community card, called the turn, is dealt face-up following all betting action on the flop.
        \tOnce this has been completed, another round of betting occurs, similar to that on the previous round of play. Again players have the option to check, bet, call, fold or raise.
        *The River:
        \tThe fifth community card, called the river, is dealt face-up following all betting action on the turn.
        \tOnce this has been completed, another round of betting occurs, similar to what took play on the previous round of play. Once more the remaining players have the option to options to check, bet, call, fold or raise.
        \tAfter all betting action has been completed, the remaining players in the hand with hole cards now expose their holdings to determine a winner. This is called the showdown.
        *The Showdown:
        \tThe remaining players show their hole cards and with the assistance of the dealer, a winning hand is determined.
        \tThe player with the best combination of five cards wins the pot according to the official poker hand rankings.
        \tA link to the official poker hand rankings will be attached to this document and in the game before you start. 
        \thttps://en.wikipedia.org/wiki/List_of_poker_hands
        Unique to this game is the opportunity to change difficulty (difficulty is regarding the opponents) and create custom characters however their actions are independent to single rounds and any money they lose or earn is not carried forward.
        Once again you are reminded to read the T&C's before playing.
        """

    def __init__(self, root):
        """
        Initialises the ShowGameRules instance with the root window
        reference for font settings and Toplevel parenting.

        Args:
            root: The root Tk window used to bind fonts and parent the
                  rules Toplevel.
        """
        self.interface_root = root
        self.styles = fetch_text_styles(root)

    def show_whitejoe_rules(self, callback):
        """
        Opens the rules window for WhiteJoe and calls the provided callback
        once the user confirms they have read and understood the rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("WhiteJoe Rules", self.WJ_RULES, callback)

    def show_hhe_rules(self, callback):
        """
        Opens the rules window for Harrogate Hold 'em and calls the provided
        callback once the user confirms they have read and understood the
        rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("Harrogate Hold 'em Rules", self.HHE_RULES, callback)

    def show_rules_window(self, title, rules_text, callback):
        """
        Creates and displays a modal rules window with a scrollable read-only
        text area and a Continue button.
        The window cannot be closed through the window manager's close button.
        Calls the callback and destroys the window when the user clicks Continue.

        Args:
            title (str): The window title and heading label text.
            rules_text (str): The full rules text to display.
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        bg = CS["rules"]
        window = Toplevel(self.interface_root)
        create_window(window, title, bg)

        heading = preset_label(window, text=title, font=self.styles["title"])
        heading.pack(pady=10)

        text_area = scrolledtext.ScrolledText(
            window,
            wrap=WORD,
            font=self.styles["rules"],
            background=bg,
        )
        text_area.pack(expand=True, fill=BOTH, padx=10)
        text_area.insert(END, rules_text)
        text_area.configure(state="disabled")
        text_area.yview_moveto(0)

        bottom_frame = Frame(window, bg=bg)
        bottom_frame.pack(side=BOTTOM, fill=X, pady=10)

        continue_button = preset_button(
            bottom_frame,
            text="Continue",
            command=lambda: (window.destroy(), callback()),
        )
        continue_button.pack(pady=10)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# deck_management.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CasinoDeckManager:
    """
    Central manager for deck handling, card format conversion and game logic
    for both poker and blackjack. Wraps the treys library to provide a unified
    interface for drawing cards, evaluating hands and converting between
    string and integer card representations.
    """

    def __init__(self, shuffle=True, game_mode="poker"):
        """
        Initialises the deck manager with a fresh treys deck, a treys
        Evaluator instance and the specified game mode. Optionally shuffles
        the deck on creation.

        Args:
            shuffle (bool): If True, shuffles the deck immediately after
                            creation. Defaults to True.
            game_mode (str): The game mode to use for hand evaluation.
                             Must be 'poker' or 'blackjack'. Defaults to
                             'poker'.
        """
        self.deck = TreysDeck()
        self.evaluator = Evaluator()
        self.game_mode = game_mode.lower()

        if shuffle:
            self.deck.shuffle()

    def str_deck(self):
        """
        Returns the current deck contents as a list of string representations.

        Returns:
            list[str]: All remaining cards in the deck as strings
                       (e.g. ['As', 'Kh', 'Td']).
        """
        return [self.treys_to_str(c) for c in self.deck.cards]

    def shuffle(self):
        """Shuffles the current deck."""
        self.deck.shuffle()

    def draw(self, n=1):
        """
        Draws n cards from the deck. If the deck has fewer than n cards
        remaining, resets and reshuffles the deck before drawing. Returns a
        single card integer when n=1 or a list of card integers when n>1.

        Args:
            n (int): The number of cards to draw. Defaults to 1.

        Returns:
            int or list[int]: A single treys card integer if n=1 or a list
                              of treys card integers if n>1.
        """
        if self.remaining() < n:
            self.deck = TreysDeck()
            self.deck.shuffle()
        cards = self.deck.draw(n) if n != 1 else self.deck.draw(n)[0]
        return cards

    def str_draw(self, n=1):
        """
        Draws n cards from the deck and returns them as string
        representations. Resets and reshuffles the deck first if fewer than
        n cards remain.

        Args:
            n (int): The number of cards to draw. Defaults to 1.

        Returns:
            list[str]: The drawn cards as strings (e.g. ['As', 'Kh']).
        """
        if self.remaining() < n:
            self.deck = TreysDeck()
            self.deck.shuffle()
        cards = self.deck.draw(n)
        return [self.treys_to_str(c) for c in cards]

    def pretty_draw(self, n=1):
        """
        Draws n cards from the deck and returns them as pretty-printed strings
        using Unicode suit symbols. Resets and reshuffles the deck first if
        fewer than n cards remain.

        Args:
            n (int): The number of cards to draw. Defaults to 1.

        Returns:
            list[str]: The drawn cards as pretty strings (e.g. ['A♠', 'K♥']).
        """
        if self.remaining() < n:
            self.deck = TreysDeck()
            self.deck.shuffle()
        cards = self.deck.draw(n)
        return [self.treys_to_pretty(c) for c in cards]

    def remove_card(self, card):
        """
        Removes a specific card from the deck if it is present. Used to
        exclude known cards (e.g. hole cards and community cards) before
        running simulations.

        Args:
            card (int): The treys card integer to remove.
        """
        if card in self.deck.cards:
            self.deck.cards.remove(card)

    def remaining(self):
        """
        Returns the number of cards currently remaining in the deck.

        Returns:
            int: The number of remaining cards.
        """
        return len(self.deck.cards)

    def copy(self):
        """
        Creates an independent copy of this deck manager instance.
        The copied deck shares the same Evaluator (which is stateless) but
        has its own independent card list. Used to ensure
        simulations do not interfere with each other.

        Returns:
            CasinoDeckManager: A new deck manager instance with a copied
                               deck state and the same game mode.
        """
        new_dm = CasinoDeckManager(shuffle=False, game_mode=self.game_mode)

        # Copy deck state.
        new_dm.deck.cards = self.deck.cards.copy()

        new_dm.evaluator = self.evaluator

        return new_dm

    def str_to_treys(self, card):
        """
        Converts a card string to a treys integer representation.

        Args:
            card (str): A card string in the format 'Rs' where R is the
                            rank and s is the suit (e.g. 'As', 'Td', '2h').

        Returns:
            int: The treys integer representation of the card.
        """
        return TreysCard.new(card)

    def treys_to_str(self, card):
        """
        Converts a treys card integer to a standard string representation.
        Args:
            card (int): A treys card integer.
        Returns:
            str: The card as a string (e.g. 'As', 'Td', '2h').
        """
        return TreysCard.int_to_str(card)

    def treys_to_pretty(self, card):
        """
        Converts a treys card integer to a pretty-printed string using Unicode
        suit symbols.
        Args:
            card (int): A treys card integer.
        Returns:
            str: The card as a pretty string (e.g. 'A♠', 'T♦', '2♥').
        """
        return TreysCard.int_to_pretty_str(card)

    def treys_to_str_pretty(self, cards):
        """
        Converts a list of treys card integers into a pair of parallel lists:
        one containing standard string representations and one containing
        pretty-printed representations.

        Args:
            cards (list[int]): A list of treys card integers.

        Returns:
            list[list[str]]: A list of two lists. The first contains standard
                             string representations (e.g. 'As'), the second
                             contains pretty strings (e.g. 'A♠').
        """
        str_pretty = [[], []]
        for card in cards:
            str_pretty[0].append(self.treys_to_str(card))
            str_pretty[1].append(self.treys_to_pretty(card))
        return str_pretty

    def str_cards(self, cards):
        """
        Converts a list of treys card integers to standard string
        representations.

        Args:
            cards (list[int]): A list of treys card integers.

        Returns:
            list[str]: The cards as standard strings (e.g. ['As', 'Kh']).
        """
        return [self.treys_to_str(card) for card in cards]

    def pretty_cards(self, cards):
        """
        Converts a list of treys card integers to a single space-separated
        string of pretty-printed card representations.

        Args:
            cards (list[int]): A list of treys card integers.

        Returns:
            str: A space-separated string of pretty cards
                 (e.g. 'A♠ K♥ T♦').
        """
        return " ".join(self.treys_to_pretty(c) for c in cards)

    def blackjack_hand_value(self, treys_hand):
        """
        Calculates the optimal blackjack hand value for a given list of treys
        card integers. Aces are counted as 11 unless doing so would bust the
        hand, in which case they are reduced to 1 one at a time.

        Args:
            treys_hand (list[int]): A list of treys card integers representing
                                    the hand.

        Returns:
            int: The optimal hand value, between 2 and 21 (or higher if
                 busted).
        """
        total = 0
        aces = 0

        for card in treys_hand:
            rank_int = TreysCard.get_rank_int(card)

            # Ace.
            if rank_int == 12:
                total += 11
                aces += 1
            # T, J, Q, K.
            elif rank_int >= 8:
                total += 10
            # 2–9.
            else:
                total += rank_int + 2

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    def evaluate_hand(self, hand, board=None):
        """
        Evaluates a hand according to the current game mode.

        For blackjack: converts the hand to treys integers and returns the
        numerical hand value through blackjack_hand_value().

        For poker: evaluates the hand against the provided board using the
        treys Evaluator, returning a tuple of the raw score and the hand
        name string (e.g. 'Flush', 'Two Pair').

        Args:
            hand (list[str]): The player's hole cards as string
                              representations (e.g. ['As', 'Kh']).
            board (list[str], optional): The community cards as string
                                         representations. Required for poker
                                         mode.

        Returns:
            int: The blackjack hand value (blackjack mode).
            tuple[int, str]: A (score, hand_name) tuple (poker mode).

        Raises:
            ValueError: If game mode is poker and no board is provided.
            ValueError: If the game mode is not 'poker' or 'blackjack'.
        """
        treys_hand = [TreysCard.new(c) for c in hand]

        if self.game_mode == "blackjack":
            return self.blackjack_hand_value(treys_hand)

        if self.game_mode == "poker":
            if not board:
                raise ValueError("Poker evaluation requires a board")

            treys_board = [TreysCard.new(c) for c in board]
            score = self.evaluator.evaluate(treys_hand, treys_board)

            rank_class = self.evaluator.get_rank_class(score)
            hand_name = self.evaluator.class_to_string(rank_class)
            return score, hand_name

        raise ValueError("Invalid game mode")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# whitejoe.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class WhiteJoe:
    """
    Handles all game flow, betting logic, card dealing, dealer resolution
    and logging for WhiteJoe. Runs its own tkinter mainloop and returns to
    the menu on exit.
    """

    def __init__(self, user_data):
        """
        Initialises the WhiteJoe game window, sets up external resources and
        initialises game state variables.

        Args:
            user_data (dict): Dictionary containing at minimum 'username'
                              (str) and 'administrator' (bool) keys and
                              optionally 'user_id'.
        """
        self.window_bg = CS["casino"]
        self.wj_root = Tk()
        self.main_frame, self.styles = create_window(
            self.wj_root,
            "One Less Time Casino - WhiteJoe",
            self.window_bg,
            is_main_frame=True,
        )
        self.wj_root.protocol(
            "WM_DELETE_WINDOW", lambda: (self.wj_root.quit(), sys.exit(0))
        )

        self.user_data = user_data

        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        self.dbm = DatabaseManagement(DB_PATH)

        self.action_buttons = []

        # Game state.
        self.player_hand = []
        self.dealer_hand = []
        self.dealer = "Dealer"
        self.current_bet = 0
        self.round_active = False

        self.start_balance = 0

        if not self.user_data.get("administrator"):
            balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
            if not balance_data["found"]:
                self.return_to_menu(
                    is_error=True, error=Exception("User not found in database.")
                )
                return
            self.start_balance = balance_data["balance"]

            set_view(self, self.whitejoe_screen)
        else:
            set_view(self, self.admin_modify_bet)

        self.wj_root.mainloop()

    def admin_modify_bet(self, frame):
        """
        Opens a modal Toplevel dialog that allows the administrator to set
        a custom starting balance.

        Args:
            frame (Frame or Tk): The parent widget used to anchor the
                                 Toplevel dialog.
        """
        screen_built = getattr(self, "balance_label", None) is not None

        balance_window = Toplevel(frame)
        create_window(
            balance_window,
            "Set Starting Balance",
            self.window_bg,
        )
        balance_window.grab_set()
        balance_window.protocol("WM_DELETE_WINDOW", lambda: None)
        balance_window.focus_force()

        preset_label(
            balance_window,
            text="Enter starting balance (£):",
        ).pack(pady=8)

        balance_entry = preset_entry(
            balance_window,
            width=20,
        )
        balance_entry.pack(pady=5)

        def submit_balance():
            """
            Validates the balance entry and closes the dialog.
            """
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()
                self.start_balance = balance
                self.dbm.modify_user_balance(self.user_data["username"], balance)
                balance_window.destroy()
                if screen_built:
                    self.balance_label.config(text=f"Balance: £{balance}")
                else:
                    set_view(self, self.whitejoe_screen)
            except Exception:
                messagebox.showerror("Error", "Please enter a valid positive integer.")

        preset_button(
            balance_window,
            text="Submit",
            relief="flat",
            command=submit_balance,
        ).pack(pady=10)

    def whitejoe_screen(self, frame):
        """
        Builds the main game layout using a three-panel grid. The left panel
        contains the scrollable game log, the top-right panel shows user
        information and balance and the bottom-right panel contains the bet
        controls and action buttons.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Left panel
        left_frame = Frame(frame, bd=2, relief="sunken", bg=CS["top_left"])
        left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)

        # Canvas + Scrollbar
        self.log_canvas = Canvas(left_frame, bg=CS["top_left"], highlightthickness=0)
        scrollbar = Scrollbar(
            left_frame, orient="vertical", command=self.log_canvas.yview
        )
        self.log_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_canvas.pack(side="left", fill="both", expand=True)

        # Inner frame
        self.log_frame = Frame(self.log_canvas, bg=CS["top_left"])
        self.log_window = self.log_canvas.create_window(
            (0, 0), window=self.log_frame, anchor="nw"
        )

        self.log_canvas.bind(
            "<Configure>",
            lambda e: self.log_canvas.itemconfig(self.log_window, width=e.width),
        )
        self.log_frame.bind(
            "<Configure>",
            lambda e: self.log_canvas.configure(
                scrollregion=self.log_canvas.bbox("all")
            ),
        )

        # Top-right panel
        top_right_frame = Frame(frame, bd=2, relief="sunken", bg=CS["top_right"])
        top_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        preset_button(
            top_right_frame,
            text="Return to Menu",
            command=self.return_to_menu,
        ).pack(pady=5)

        labels = []
        for text in (
            f"Username: {self.user_data['username']}",
            f"Balance: £{self.start_balance}",
            "Current Bet: £0",
        ):
            label = preset_label(
                top_right_frame,
                text=text,
                anchor="w",
            )
            label.pack(anchor="w", pady=5, padx=5)
            labels.append(label)

        self.balance_label = labels[1]
        self.current_bet_label = labels[2]

        # Bottom-right panel
        bottom_right_frame = Frame(frame, bd=2, relief="sunken", bg=CS["bottom_right"])
        bottom_right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        def check_bet_input(amount=0):
            """
            Updates the current bet by the given amount, clamping the result
            between 0 and the player's current balance. Updates bet_var,
            the current-bet label and the Start Round button state.
            """
            try:
                current_value = int(self.bet_var.get())
                new_value = max(0, current_value + amount)
                balance = self.return_balance()
                if balance is not None:
                    new_value = min(new_value, int(balance))
            except (ValueError, TypeError):
                new_value = 0

            self.bet_var.set(str(new_value))
            self.current_bet = new_value
            self.current_bet_label.config(text=f"Current Bet: £{new_value}")
            state = (
                "normal" if (new_value > 0 and not self.round_active) else "disabled"
            )
            self.start_button.config(state=state)

        # Increment rows
        for inc in (1, 10, 100, 1000):
            row = Frame(
                bottom_right_frame,
                bg=CS["text_bg"],
                bd=2,
                relief="ridge",
                padx=6,
                pady=3,
            )
            row.pack(fill="x", pady=3)

            preset_button(
                row,
                text="+",
                width=3,
                command=lambda v=inc: check_bet_input(amount=v),
            ).pack(side="left", padx=4)

            preset_label(
                row,
                text=str(inc),
                width=8,
                anchor="center",
            ).pack(side="left", expand=True)

            preset_button(
                row,
                text="-",
                width=3,
                command=lambda v=-inc: check_bet_input(amount=v),
            ).pack(side="right", padx=4)

        # Action buttons
        for text, command in (
            ("Hit", self.hit),
            ("Stand", self.stand),
            ("Double Down", self.double_down),
            ("Surrender", self.surrender),
        ):
            button = preset_button(
                bottom_right_frame,
                text=text,
                width=18,
                command=command,
                state="disabled",
            )
            button.pack(pady=6)
            self.action_buttons.append(button)

        self.start_button = preset_button(
            bottom_right_frame,
            text="Start Round",
            width=18,
            command=self.start_round,
        )
        self.start_button.pack(pady=10)

        self.bet_var = StringVar(value="0")
        self.bet_var.trace_add("write", lambda *_: check_bet_input())

        self.update_button_states()

    def update_button_states(self):
        """
        Enables or disables the Start Round and action buttons based on the
        current round state and bet value. The Start button is disabled during
        an active round or when the bet is zero. Action buttons are only
        enabled during an active round.
        """
        try:
            bet = int(self.bet_var.get())
        except ValueError:
            bet = 0

        # Start button
        if self.round_active or bet <= 0:
            self.start_button.config(state="disabled")
        else:
            self.start_button.config(state="normal")

        # Action buttons
        state = "normal" if self.round_active else "disabled"
        for button in self.action_buttons:
            button.config(state=state)

    def log_message(
        self, text, round_start=False, is_win=False, is_loss=False, is_push=False
    ):
        """
        Adds a message to the log queue and starts processing if the queue
        is not already active.

        Args:
            text (str): The message text to display.
            round_start (bool): If True, styles the entry as a round start
                                message. Defaults to False.
            is_win (bool): If True, styles the entry as a win. Defaults to
                           False.
            is_loss (bool): If True, styles the entry as a loss. Defaults to
                            False.
            is_push (bool): If True, styles the entry as a push (tie).
                            Defaults to False.
        """
        self.log_queue.append((text, round_start, is_win, is_loss, is_push))
        if not self.log_active:
            self.process_log_queue()

    def process_log_queue(self):
        """
        Processes the next entry in the log queue, renders it and schedules
        itself to run again after log_delay_ms milliseconds. Stops when the
        queue is empty.
        """
        if not self.log_queue:
            self.log_active = False
            return

        self.log_active = True
        text, round_start, is_win, is_loss, is_push = self.log_queue.pop(0)

        self.render_log(text, round_start, is_win, is_loss, is_push)

        self.wj_root.after(self.log_delay_ms, self.process_log_queue)

    def render_log(self, text, round_start, is_win, is_loss, is_push):
        """
        Creates and packs a colour-coded Label into the log frame for the
        given message and then scrolls the log canvas to the bottom.

        Args:
            text (str): The message text to display.
            round_start (bool): Applies round-start background colour.
            is_win (bool): Applies win background colour.
            is_loss (bool): Applies loss background colour.
            is_push (bool): Applies push background colour.
        """
        label = preset_label(
            self.log_frame,
            text=text,
            bg=(
                CS["start_bg"]
                if round_start
                else (
                    CS["win_bg"]
                    if is_win
                    else (
                        CS["loss_bg"]
                        if is_loss
                        else (CS["tie_bg"] if is_push else CS["log_bg"])
                    )
                )
            ),
            fg=(
                CS["start_fg"]
                if round_start
                else (
                    CS["win_fg"]
                    if is_win
                    else (
                        CS["loss_fg"]
                        if is_loss
                        else (CS["tie_fg"] if is_push else CS["log_fg"])
                    )
                )
            ),
            bd=2,
            relief="groove",
            padx=6,
            pady=4,
            wraplength=400,
            anchor="w",
            justify="left",
        )
        label.pack(fill="x", pady=4, padx=6)

        self.wj_root.update_idletasks()
        self.log_canvas.yview_moveto(1.0)

    def return_balance(self):
        """
        Retrieves the current user balance from the database. Redirects to
        the menu with an error if the user is not found or the balance is
        None. Returns 0 as a fallback to prevent arithmetic errors.

        Returns:
            float: The current balance or 0 if an error occurred.
        """
        balance_data = self.dbm.fetch_user_balance(self.user_data["username"])

        if not balance_data["found"]:
            self.return_to_menu(
                is_error=True, error=Exception("User not found in database.")
            )

        if balance_data["balance"] is not None:
            return balance_data["balance"]
        else:
            self.return_to_menu(
                is_error=True, error=Exception("Fetched balance returns 'None'")
            )
            return 0  # In order to prevent errors regarding 'None' errors.

    def check_balance(self):
        """
        Checks whether the user's balance is zero. For administrators,
        opens the balance modification dialog.

        Returns:
            bool: True if the user can continue playing, False if they have
                  been redirected away.
        """
        if self.return_balance() == 0:
            if self.user_data.get("administrator"):
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is £0. As an administrator, you can set a new balance.",
                )

                self.admin_modify_bet(self.main_frame)
                return True

            else:
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is now £0. Returning to menu.",
                )
                self.return_to_menu()
                return False
        return True

    def modify_user_balance(self, balance):
        """
        Updates the user's balance in the database, refreshes the balance
        label in the UI and logs the new balance to the game log.

        Args:
            balance (int): The new balance to set.
        """
        self.dbm.modify_user_balance(self.user_data["username"], balance)
        self.balance_label.config(text=f"Balance: £{balance}")
        self.log_message(text=f"You have a total of £{balance} in your account.")

    def start_round(self):
        """
        Validates the current bet, deducts it from the user's balance, deals
        two cards to both the player and dealer using a freshly shuffled deck,
        and begins the round. Prevents starting if a round is already active
        or the bet is invalid.
        """
        if self.round_active:
            return

        if not self.check_balance():
            return

        try:
            bet = int(self.bet_var.get())
        except ValueError:
            messagebox.showerror("Invalid bet", "Bet must be a number.")
            return

        balance = self.return_balance()

        if bet <= 0 or bet > balance:
            messagebox.showerror(
                "Invalid bet", f"You must bet between £1 and £{balance}."
            )
            return

        self.log_message(text="Starting new round...", round_start=True)

        self.current_bet = bet
        self.modify_user_balance(balance - bet)

        self.player_hand.clear()
        self.dealer_hand.clear()

        # Create and shuffle a new deck at the start of each round.
        self.deck = CasinoDeckManager(shuffle=True, game_mode="blackjack")
        self.log_message(text="The deck is being shuffled...")

        # Deal cards.
        self.player_hand.extend([self.deck.draw(1), self.deck.draw(1)])

        if self.deck.blackjack_hand_value(self.player_hand) == 21:
            self.log_message(text="You have been dealt a natural WhiteJoe!")
            balance = self.return_balance()
            balance += int(self.current_bet * 2.5)
            self.modify_user_balance(balance)
            # Prevents a second payout.
            self.current_bet = 0
            self.end_round(win=True)
            return

        self.dealer_hand.extend([self.deck.draw(1), self.deck.draw(1)])

        self.round_active = True
        self.update_button_states()
        self.logs_after_deal()

    def logs_after_deal(self):
        """
        Logs the initial deal state to the game log: the player's two cards
        and total, the dealer's visible card and its value and a prompt for
        the player to act.
        """
        player_value = self.deck.blackjack_hand_value(self.player_hand)
        self.log_message(
            text=f"You are given the cards {self.deck.treys_to_pretty(self.player_hand[0])}, {self.deck.treys_to_pretty(self.player_hand[1])} with a total value of {player_value}."
        )
        self.log_message(
            text=f"{self.dealer} has been dealt their cards. The dealer shows {self.deck.treys_to_pretty(self.dealer_hand[0])} with a total value of {self.deck.blackjack_hand_value([self.dealer_hand[0]])}."
        )
        self.log_message(text=f"{self.dealer} then motions for you to make your move.")

    def hit(self):
        """
        Draws one card for the player, logs the result and checks for a
        bust. If the player busts, ends the round as a loss. Otherwise logs
        a prompt to continue.
        """
        if not self.round_active:
            return

        self.log_message(text="You've chosen to hit.")

        self.player_hand.append(self.deck.draw(1))
        value = self.deck.blackjack_hand_value(self.player_hand)

        self.log_message(
            text=f"You draw {self.deck.treys_to_pretty(self.player_hand[-1])}."
        )

        player_cards = ", ".join(
            self.deck.treys_to_pretty(card) for card in self.player_hand
        )

        self.log_message(text=f"You have the cards {player_cards} totaling {value}.")

        if value > 21:
            self.log_message(text="You busted!")
            self.end_round(loss=True)
        else:
            self.log_message(text="You may choose to hit again or stand.")

    def stand(self):
        """
        Ends the player's turn and triggers dealer resolution.
        """
        if not self.round_active:
            return

        self.log_message(text="You've chosen to stand.")

        self.resolve_dealer()

    def double_down(self):
        """
        Doubles the current bet (deducting the additional amount from the
        user's balance), draws one card and resolves the dealer.
        Prevents doubling if the user has insufficient balance.
        """
        if not self.round_active:
            return

        self.log_message(text="You've chosen to double down.")

        balance_data = self.dbm.fetch_user_balance(self.user_data["username"])

        if not balance_data["found"]:
            self.return_to_menu(
                is_error=True, error=Exception("User not found in database.")
            )
            return

        balance = balance_data["balance"]

        if balance < self.current_bet:
            messagebox.showerror(
                "Cannot double down", "Not enough balance to double down."
            )
            return

        self.log_message(
            text=f"Doubling your bet from £{self.current_bet} to £{self.current_bet * 2}."
        )

        self.modify_user_balance(balance - self.current_bet)
        self.current_bet *= 2

        self.player_hand.append(self.deck.draw(1))
        value = self.deck.blackjack_hand_value(self.player_hand)

        self.log_message(
            text=f"You draw {self.deck.treys_to_pretty(self.player_hand[-1])}."
        )

        player_cards = ", ".join(
            self.deck.treys_to_pretty(card) for card in self.player_hand
        )

        self.log_message(text=f"You have the cards {player_cards} totaling {value}.")

        if value > 21:
            self.end_round(loss=True)
        else:
            self.resolve_dealer()

    def surrender(self):
        """
        Ends the current round immediately, returning half the current bet to
        the user's balance.
        """
        if not self.round_active:
            return

        self.log_message(text="You've chosen to surrender.")

        balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
        balance = balance_data["balance"] if balance_data["found"] else 0
        refund = self.current_bet // 2
        self.modify_user_balance(balance + refund)

        self.log_message(
            text=f"You get back £{refund} from your bet of £{self.current_bet}."
        )

        self.current_bet = 0
        self.current_bet_label.config(text="Current Bet: £0")
        self.round_active = False
        self.update_button_states()

    def resolve_dealer(self):
        """
        Reveals the dealer's hidden card and draws additional cards until the
        dealer's hand value reaches 17 or more. Then compares the final hand
        values to determine the round outcome and calls end_round accordingly.
        """
        self.log_message(
            text=f"{self.dealer} reveals their hidden card: "
            f"{self.deck.treys_to_pretty(self.dealer_hand[1])} with the "
            f"hand value of "
            f"{self.deck.blackjack_hand_value(self.dealer_hand)}."
        )

        while self.deck.blackjack_hand_value(self.dealer_hand) < 17:
            self.log_message(
                text=f"Given that {self.dealer}'s hand value is less than 17, "
                f"they must hit."
            )
            self.dealer_hand.append(self.deck.draw(1))
            self.log_message(
                text=f"{self.dealer} draws "
                f"{self.deck.treys_to_pretty(self.dealer_hand[-1])}, "
                f"bringing their hand value to "
                f"{self.deck.blackjack_hand_value(self.dealer_hand)}."
            )

        player = self.deck.blackjack_hand_value(self.player_hand)
        dealer = self.deck.blackjack_hand_value(self.dealer_hand)

        if dealer > 21 or player > dealer:
            if dealer > 21:
                self.log_message(text=f"{self.dealer} has busted!")
            if player > dealer:
                self.log_message(text="Your hand is higher than the dealer's!")
            self.end_round(win=True)
        elif player == dealer:
            self.end_round(push=True)
        else:
            if dealer <= 21 and dealer > player:
                self.log_message(text=f"{self.dealer}'s hand is higher than yours.")
            self.end_round(loss=True)

    def end_round(self, *, win=False, loss=False, push=False):
        """
        Concludes the current round by updating the user's balance based on
        the outcome, logging the result, resetting the bet and round state,
        and re-enabling the Start button.

        Args:
            win (bool): If True, pays out 2x the bet to the player's balance.
            loss (bool): If True, logs a loss message with a responsible
                         gambling reminder.
            push (bool): If True, returns the bet to the player's balance.
        """
        balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
        balance = balance_data["balance"] if balance_data["found"] else 0

        if win:
            balance += self.current_bet * 2
            self.log_message(text="Congrats! You've won this round.", is_win=True)
        elif loss:
            self.log_message(
                text="You've lost this round. Better luck next time.", is_loss=True
            )
        elif push:
            self.log_message(
                text="You and the dealer have the same hand. Therefore you tie "
                "and your bet is returned to you.",
                is_push=True,
            )
            balance += self.current_bet
            self.log_message(text=f"You have a total of £{balance} to your disposal.")

        self.modify_user_balance(balance)
        self.current_bet = 0
        self.current_bet_label.config(text="Current Bet: £0")
        self.round_active = False
        self.update_button_states()

        for button in self.action_buttons:
            button.config(state="disabled")

    def return_to_menu(self, is_error=False, error=None):
        """
        Destroys the game window and returns the user to the appropriate
        interface. Navigates to AdminInterface for administrators or
        CasinoInterface for regular users. Optionally displays an error dialog
        before returning.

        Args:
            is_error (bool): If True, displays an error message before
                             returning. Defaults to False.
            error (Exception, optional): The error to display if is_error is
                                         True.
        """
        if is_error:
            messagebox.showerror("Error", f"{error}, exiting game.")

        self.wj_root.destroy()

        CasinoInterface(
            administrator=True if self.user_data.get("administrator") else False,
            user_data=self.user_data,
        )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# poker_player_management.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# Timeout check: exit decision making early if no results after this many iterations.
TIME_OUT = 1000

# Betting size thresholds by difficulty band.
MIN_RAISE_FACTOR_LOW_DIFF = 0.5
MAX_RAISE_FACTOR_LOW_DIFF = 2.0
MIN_RAISE_FACTOR_HIGH_DIFF = 0.75
MAX_RAISE_FACTOR_HIGH_DIFF = 3.0

# Minimum rounds before a player's stored range is used.
EXPERIENCE_THRESHOLD = 50

# Default delta for range chart updates.
DEFAULT_DELTA = 0.05

# Maximum outs considered when estimating drawing equity.
MAX_OUTS = 20

# Fold-bias constants.
FOLD_BIAS_MAX = 0.40
FOLD_BIAS_MIN = 0.04


# POKER PLAYER MANAGEMENT


class HumanPokerPlayer:
    """
    A human player backed by the database.

    Loads statistics and a range chart on construction.
    Inexperienced players (rounds_played <= EXPERIENCE_THRESHOLD) receive a
    default range for gameplay while their stored range continues to be
    updated in the database.
    """

    def __init__(self, *, user_id):
        """
        Initialises a human player by loading their poker data from the database.

        Args:
            user_id (int): Database primary key for this player.

        Raises:
            ValueError: If poker data cannot be loaded from the database.
        """
        if not user_id:
            raise ValueError("user_id is required for human players.")

        self.user_id = user_id
        self.dbm = DatabaseManagement(DB_PATH)

        record = self.dbm.load_user_poker_data(self.user_id)
        if record is None:
            raise ValueError(f"Failed to load poker data for user_id={self.user_id}")

        self.record = record
        self.vpip = record["vpip"]
        self.pfr = record["pfr"]
        self.aggression_factor = self.pfr / max(1.0, self.vpip)
        self.fold_to_raise = record["fold_to_raise"]
        self.call_when_weak = record["call_when_weak"]

        self.statistics = {
            "rounds_played": record["rounds_played"],
            "avg_bet_size": record["avg_bet_size"],
        }

        stored_range = record["player_range"]

        if self.statistics["rounds_played"] <= EXPERIENCE_THRESHOLD:
            # Inexperienced: use a default range for gameplay.
            self.base_range = generate_range_chart()
            # Retain the stored range so it is updated correctly in the database.
            self.stored_range = stored_range if stored_range else generate_range_chart()
        else:
            self.base_range = stored_range if stored_range else generate_range_chart()
            self.stored_range = self.base_range

        # Active range starts as a session copy of base_range.
        self.active_range = self.base_range.copy()

    def refresh_from_db(self):
        """
        Reloads all player attributes from the database.
        """
        if not self.dbm or self.user_id is None:
            return

        record = self.dbm.load_user_poker_data(self.user_id)
        if not record:
            return

        self.record = record
        self.vpip = record["vpip"]
        self.pfr = record["pfr"]
        self.aggression_factor = self.pfr / max(1.0, self.vpip)
        self.fold_to_raise = record["fold_to_raise"]
        self.call_when_weak = record["call_when_weak"]

        self.statistics.update(
            {
                "rounds_played": record["rounds_played"],
                "avg_bet_size": record["avg_bet_size"],
            }
        )

        stored_range = record.get("player_range")
        if stored_range:
            self.base_range = stored_range
            self.stored_range = stored_range
            self.active_range = stored_range.copy()

    def reset_active_range(self):
        """
        Resets the active range to a fresh copy of the base range.
        """
        self.active_range = self.base_range.copy()

    def update_range_from_action(self, action, hand_notation):
        """
        Updates the player's active and stored range based on an observed action,
        then updates the result to the database.

        Args:
            action (str): 'raise', 'call' or 'fold'
            hand_notation (str): e.g. 'AKs', 'TT'
        """
        if not hand_notation or hand_notation not in self.active_range:
            return

        self.active_range = update_range(
            self.active_range,
            action,
            hand_notation,
        )

        self.stored_range = update_range(
            self.stored_range,
            action,
            hand_notation,
        )

        self.dbm.update_player_range(self.user_id, self.stored_range)

    def fetch_player_info(self):
        """
        Returns a summary dictionary of this player's characteristics.

        Returns:
            dict: Keys — user_id, vpip, pfr, aggression_factor, fold_to_raise,
                  call_when_weak, rounds_played, record.
        """
        return {
            "record": self.record,
            "user_id": self.user_id,
            "vpip": self.vpip,
            "pfr": self.pfr,
            "aggression_factor": self.aggression_factor,
            "fold_to_raise": self.fold_to_raise,
            "call_when_weak": self.call_when_weak,
            "rounds_played": self.statistics["rounds_played"],
        }

    def __repr__(self):
        """
        Returns a string representation of the human player.
        """
        return (
            f"HumanPokerPlayer(user_id={self.user_id}, "
            f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%, "
            f"Rounds Played={self.statistics['rounds_played']})"
        )


class BotPokerPlayer:
    """
    An bot player with generated tendencies.
    """

    def __init__(self, *, difficulty):
        """
        Initialises a bot with  generated tendencies scaled by difficulty.

        Args:
            difficulty (int): Bot difficulty level 0–100.

        Raises:
            ValueError: If difficulty is not set.
        """
        if difficulty is None:
            raise ValueError("difficulty is required for bot players.")

        self.difficulty = difficulty

        # Tendency parameters interpolated by difficulty.
        self.vpip = difficulty_curve(self.difficulty, 35, 18)
        self.pfr = difficulty_curve(self.difficulty, 10, 20)
        self.aggression_factor = self.pfr / max(1.0, self.vpip)
        self.bluff_freq = difficulty_curve(self.difficulty, 0.15, 0.40)
        self.fold_to_raise = difficulty_curve(self.difficulty, 0.60, 0.30)
        self.call_when_weak = difficulty_curve(self.difficulty, 0.50, 0.20)

        self.base_range = generate_bot_range(self.vpip, self.difficulty)

        self.bot_characteristics = BotCharacteristics(self.difficulty)
        # Active range starts as a session copy of base_range.
        self.active_range = self.base_range.copy()

    def decide(
        self, *, player_hand, community_cards, opponents, pot, to_call, balance, street
    ):
        """
        Makes a poker decision using game-theory principles and opponent modelling.
        Delegates to make_decision().

        Args:
            player_hand (list[str]): The player's two hole cards.
            community_cards (list[str]): The current community cards (0–5).
            opponents (list[HumanPokerPlayer | BotPokerPlayer]): The active opponent players.
            pot (float): The current pot size.
            to_call (float): The amount required to call.
            balance (float): The player's remaining chips.
            street (str): The current betting round ('preflop', 'flop', 'turn', 'river').

        Returns:
            tuple: One of ("fold",), ("call",), ("raise", amount).
        """
        opponent_ranges = [opp.active_range for opp in opponents]

        return make_decision(
            player_hand=player_hand,
            player_range=self.active_range,
            community_cards=community_cards,
            opponent_ranges=opponent_ranges,
            opponents=opponents,
            pot=pot,
            balance=balance,
            to_call=to_call,
            bot=self.bot_characteristics,
            street=street,
        )

    def fetch_player_info(self):
        """
        Returns a summary dictionary of this bot's characteristics.

        Returns:
            dict: Keys — difficulty, vpip, pfr, aggression_factor, fold_to_raise,
                  call_when_weak, bluff_freq.
        """
        return {
            "difficulty": self.difficulty,
            "vpip": self.vpip,
            "pfr": self.pfr,
            "aggression_factor": self.aggression_factor,
            "fold_to_raise": self.fold_to_raise,
            "call_when_weak": self.call_when_weak,
            "bluff_freq": self.bluff_freq,
        }

    def __repr__(self):
        """
        Returns a string representation of the bot player.
        """
        return (
            f"BotPokerPlayer(difficulty={self.difficulty}, "
            f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%)"
        )


class BotCharacteristics:
    """
    Parameters shaping bot decision-making according to difficulty. Higher
    difficulty yields more accurate and less noisy behaviour.
    """

    def __init__(self, difficulty):
        """
        Initialises all bot characteristics by interpolating each parameter
        between its low-difficulty and high-difficulty values using
        difficulty_curve().

        Args:
            difficulty (int): Bot difficulty level 0–100.
        """
        self.is_bot = True
        self.difficulty = difficulty

        # Simulation depth.
        self.simulations = int(difficulty_curve(difficulty, 500, 15000))

        # Lower noise value means more accurate decisions.
        self.noise_level = difficulty_curve(difficulty, 0.30, 0.02)

        # Bluffing attitude.
        self.bluff_multiplier = difficulty_curve(difficulty, 0.6, 1.6)

        self.risk_tolerance = difficulty_curve(difficulty, 0.85, 1.5)

        # Minimum Defence Frequency
        self.mdf_threshold = difficulty_curve(difficulty, 0.9, 0.3)

        self.range_adherence = difficulty_curve(difficulty, 0.6, 0.95)

        self.fold_bias = difficulty_curve(difficulty, FOLD_BIAS_MAX, FOLD_BIAS_MIN)

    def __repr__(self):
        """
        Returns a detailed string representation of all bot characteristics.
        """
        return (
            f"BotCharacteristics(difficulty={self.difficulty}, "
            f"simulations={self.simulations}, "
            f"noise={self.noise_level:.3f}, "
            f"bluff_mult={self.bluff_multiplier:.2f}, "
            f"risk_tolerance={self.risk_tolerance:.2f}, "
            f"mdf_threshold={self.mdf_threshold:.2f}, "
            f"fold_bias={self.fold_bias:.3f})"
        )


def generate_range_chart():
    """
    Generates a default poker range chart mapping all 169 distinct starting
    hand notations to an initial probability of 0.0.

    Returns:
        dict: Keys are hand notations (e.g. 'AA', 'AKs', 'T9o'), all
              mapped to 0.0.
    """
    chart = {}
    ranks = "23456789TJQKA"
    for i, r1 in enumerate(ranks[::-1]):
        for j, r2 in enumerate(ranks[::-1]):
            hand = (r1 + r2 + "s") if i < j else (r2 + r1 + "o") if i > j else (r1 + r2)
            chart[hand] = 0.0
    return chart


def hand_strength_rank(hand):
    """
    Calculates a relative numeric strength ranking for a hand notation.
    Used to sort hands by strength for range generation. Pocket pairs
    receive a bonus over non-pairs; suited hands rank above offsuit.

    Args:
        hand (str): A hand notation string (e.g. 'AA', 'AKs', 'T9o').

    Returns:
        int: Numeric strength ranking — higher values indicate stronger
             hands.
    """
    ranks = "23456789TJQKA"
    if len(hand) == 2:
        return 100 + ranks.index(hand[0])
    base = ranks.index(hand[0]) * 10 + ranks.index(hand[1])
    if hand.endswith("s"):
        base += 5
    return base


def generate_bot_range(vpip_target, difficulty):
    """
    Generates a bot's starting hand range based on a VPIP target and
    difficulty. Higher difficulty produces a non-linear hand
    selection through an exponent applied to the strength ranking.

    Args:
        vpip_target (float): Target VPIP percentage (0–100).
        difficulty (int): Bot difficulty level (0–100).

    Returns:
        dict: Hand notations mapped to 1.0 (in range) or 0.0 (out).
    """
    exponent = difficulty_curve(difficulty, 0.7, 2.3)
    ordered = sorted(
        generate_range_chart().keys(),
        key=lambda h: hand_strength_rank(h) ** exponent,
        reverse=True,
    )
    target = int(len(ordered) * vpip_target / 100)
    return {h: 1.0 if index < target else 0.0 for index, h in enumerate(ordered)}


def validate_hand_notation(hand):
    """
    Validates whether a string is a correctly formatted poker hand notation.

    Valid formats:
        - ''AA'', ''KK'' etc. (pocket pairs): two identical rank chars.
        - ''AKs'', ''QJs'' etc. (suited): two different ranks + 's'.
        - ''AKo'', ''T9o'' etc. (offsuit): two different ranks + 'o'.

    Args:
        hand (str): The string to validate.

    Returns:
        bool: True if the notation is valid, False otherwise.
    """
    valid_ranks = "23456789TJQKA"
    if len(hand) == 2:
        return hand[0] in valid_ranks and hand[0] == hand[1]
    if len(hand) == 3:
        return (
            hand[0] in valid_ranks
            and hand[1] in valid_ranks
            and hand[2] in ("s", "o")
            and hand[0] != hand[1]
        )
    return False


def update_range(chart, action, hand, delta=DEFAULT_DELTA):
    """
    Updates a range chart based on an observed action and then normalises the
    probabilities to sum to 1.0. Raising increases the hand's probability,
    folding decreases it and calling applies a smaller increase.

    Args:
        chart (dict): Current range chart mapping hand notations to
                      probabilities.
        action (str): Observed action — 'raise', 'call' or 'fold'.
        hand (str): Hand notation to update.
        delta (float): Base adjustment magnitude. Defaults to
                       DEFAULT_DELTA (0.05).

    Returns:
        dict: The updated and normalised range chart.

    Raises:
        ValueError: If the hand notation is invalid.
    """
    if not validate_hand_notation(hand):
        raise ValueError(f"Invalid hand notation: {hand}")

    updated = chart.copy()

    if action == "raise":
        updated[hand] = min(1.0, updated.get(hand, 0) + delta)
    elif action == "fold":
        updated[hand] = max(0.0, updated.get(hand, 0) - delta)
    elif action == "call":
        updated[hand] = min(1.0, updated.get(hand, 0) + delta * 0.5)

    total = sum(updated.values())
    if total > 0:
        updated = {h: v / total for h, v in updated.items()}

    return updated


def difficulty_curve(level, low, high):
    """
    Linearly interpolates between 'low' and 'high' based on a difficulty
    level clamped to the 0–100 range.

    Args:
        level (int or float): Difficulty level (0–100).
        low (float): Value at difficulty 0.
        high (float): Value at difficulty 100.

    Returns:
        float: The interpolated value.
    """
    t = max(0.0, min(1.0, level / 100.0))
    return low + (high - low) * t


def apply_noise(value, bot):
    """
    Applies difficulty-scaled random noise to a value, clamping the result
    to 0.0–1.0. Low-difficulty bots experience more noise, simulating
    less accurate decision-making.

    Args:
        value (float): The original value to perturb (expected 0.0–1.0).
        bot (BotCharacteristics): The bot whose noise_level and difficulty
                                  determine the noise magnitude.

    Returns:
        float: The perturbed value clamped to 0.0–1.0.
    """
    difficulty_factor = max(0.0, 1.0 - bot.difficulty / 100.0)
    effective_noise = bot.noise_level * difficulty_factor
    noise = random.uniform(-effective_noise, effective_noise)
    return max(0.0, min(1.0, value + noise))


def describe_hand(player_hand, community_cards):
    """
    Returns a string description of the hand strength category for the
    given hole cards and community cards using the treys evaluator.

    Args:
        player_hand (list[str]): The player's two hole cards.
        community_cards (list[str]): The current community cards.

    Returns:
        str: Hand category (e.g. 'Flush', 'Two Pair') or 'Unknown' on
             evaluation failure.
    """
    dm = CasinoDeckManager(game_mode="poker")
    try:
        return dm.evaluate_hand(player_hand, community_cards)[1]
    except Exception as exception:
        print(exception)
        return "Unknown"


def build_rank_index(available):
    """
    Pre-builds a rank -> card-string mapping from a list of card strings.

    Args:
        available (list[str]): Card strings currently in a deck.

    Returns:
        dict: Mapping of rank character to list of card strings.
    """
    index = {}
    for card in available:
        index.setdefault(card[0], []).append(card)
    return index


def hand_equity(player_hand, community_cards, opponent_range, bot=None):
    """
    Estimates the player's equity against a single opponent range through a
    Monte Carlo simulation.

    Args:
        player_hand (list[str]): The player's two hole cards.
        community_cards (list[str]): Known community cards (0–5).
        opponent_range (dict): Opponent range chart (notation -> probability).
        bot (BotCharacteristics or None): Bot parameters controlling
                                          simulation count.  Returns 0.5
                                          if None.

    Returns:
        float: Estimated equity in range 0.0–1.0.
    """
    if bot is None:
        return 0.5

    street_map = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
    street_key = street_map.get(len(community_cards), "preflop")
    sim_count = calculate_simulation_count(street_key, bot.difficulty)

    dm_base = CasinoDeckManager(shuffle=False, game_mode="poker")
    dm_base.deck.cards = list(CasinoDeckManager(shuffle=True).deck.cards)

    player = [dm_base.str_to_treys(c) for c in player_hand]
    board_known = [dm_base.str_to_treys(c) for c in community_cards]

    for card in player + board_known:
        dm_base.remove_card(card)

    valid_hands = [(h, p) for h, p in opponent_range.items() if p > 0]
    if not valid_hands:
        return 0.5

    hands, probs = zip(*valid_hands)
    wins = ties = total = 0
    cards_to_draw = 5 - len(board_known)

    for index in range(sim_count):
        if index > 0 and index % TIME_OUT == 0 and total == 0:
            return 0.5

        sim_dm = dm_base.copy()
        sim_dm.deck.cards = sim_dm.deck.cards[:]
        random.shuffle(sim_dm.deck.cards)

        if cards_to_draw > 0:
            drawn = sim_dm.deck.cards[:cards_to_draw]
            sim_dm.deck.cards = sim_dm.deck.cards[cards_to_draw:]
        else:
            drawn = []

        board = board_known + drawn

        try:
            player_score = sim_dm.evaluator.evaluate(player, board)
        except Exception:
            continue

        hand_notation = random.choices(hands, weights=probs, k=1)[0]
        available = sim_dm.str_deck()
        rank_index = build_rank_index(available)
        opp_hand_cards = notation_to_cards_with_index(hand_notation, rank_index, sim_dm)

        if opp_hand_cards is None:
            continue

        try:
            opp_score = sim_dm.evaluator.evaluate(opp_hand_cards, board)
        except Exception:
            continue

        total += 1
        if player_score < opp_score:
            wins += 1
        elif player_score == opp_score:
            ties += 1

    if total == 0:
        return 0.5

    return max(0.0, min(1.0, (wins + ties * 0.5) / total))


def notation_to_cards_with_index(hand_notation, rank_index, dm):
    """
    Converts a hand notation string to two treys card integers using a
    pre-built rank index. Returns None if the required cards are
    unavailable in the current simulation deck.

    Args:
        hand_notation (str): Hand notation (e.g. 'AKs', 'TT', 'QJo').
        rank_index (dict): Rank -> available card strings mapping.
        dm (CasinoDeckManager): The simulation deck manager.

    Returns:
        list[int] or None: Two treys card integers or None.
    """
    if len(hand_notation) == 2:
        cards = rank_index.get(hand_notation[0], [])
        if len(cards) < 2:
            return None
        chosen = random.sample(cards, 2)
        return [dm.str_to_treys(c) for c in chosen]

    r1, r2, suitedness = hand_notation
    cards1 = rank_index.get(r1, [])
    cards2 = rank_index.get(r2, [])

    if not cards1 or not cards2:
        return None

    combos = [
        (c1, c2)
        for c1 in cards1
        for c2 in cards2
        if (c1[1] == c2[1]) == (suitedness == "s")
    ]

    if not combos:
        return None

    c1, c2 = random.choice(combos)
    return [dm.str_to_treys(c1), dm.str_to_treys(c2)]


def calculate_simulation_count(street, difficulty):
    """
    Returns the number of simulations to run for equity
    estimation based on the current street and bot difficulty. Later
    streets and higher difficulties use more simulations.

    Args:
        street (str): Current street ('preflop', 'flop', 'turn', 'river').
        difficulty (int): Bot difficulty level 0–100.

    Returns:
        int: Number of simulations to run (minimum 100).
    """
    base = int(difficulty_curve(difficulty, 500, 15000))
    if street == "preflop":
        return max(100, base // 4)
    elif street == "flop":
        return max(200, base // 2)
    elif street == "turn":
        return max(300, int(base / 1.5))
    return base


def collective_hand_equity(player_hand, community_cards, opponent_ranges, bot=None):
    """
    Estimates the player's joint equity against multiple opponents by
    multiplying individual equities together.

    Args:
        player_hand (list[str]): The player's two hole cards.
        community_cards (list[str]): Known community cards.
        opponent_ranges (list[dict]): One range chart per opponent.
        bot (BotCharacteristics or None): Bot simulation parameters.

    Returns:
        float: Joint equity estimate in range 0.0–1.0.
    """
    if not opponent_ranges:
        # No opponents remain — the bot holds the pot uncontested.
        return 1.0

    joint = 1.0
    for opp_range in opponent_ranges:
        joint *= hand_equity(player_hand, community_cards, opp_range, bot)
    return joint


def pot_odds(current_pot, call_amount):
    """
    Returns the minimum equity required to break even on a call decision.

    Args:
        current_pot (float): Current pot size before the call.
        call_amount (float): Amount required to call.

    Returns:
        float: Required break-even equity (0.0–1.0).  Returns 0.0 if
               call_amount is zero or negative.
    """
    if call_amount <= 0:
        return 0.0
    return call_amount / (call_amount + current_pot)


def expected_value_of_call(pot, call_amount, equity):
    """
    Calculates the expected value of calling a bet.

    Args:
        pot (float): Current pot size.
        call_amount (float): Amount required to call.
        equity (float): Estimated win probability (0.0–1.0).

    Returns:
        float: Expected value in chips.  Positive = profitable call.
    """
    return equity * pot - (1 - equity) * call_amount


def estimate_outs(player_hand, community_cards):
    """
    Estimates the number of outs available to improve the hand.
    Considers flush draws, open-ended straight draws, gutshot straight
    draws and overcards. Capped at MAX_OUTS.

    Args:
        player_hand (list[str]): The player's two hole cards.
        community_cards (list[str]): Current community cards.

    Returns:
        int: Estimated outs in range 0–MAX_OUTS.
    """

    def rank_value(rank):
        """Maps a rank character to its numeric value (2–14)."""
        return {
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "T": 10,
            "J": 11,
            "Q": 12,
            "K": 13,
            "A": 14,
        }[rank]

    all_cards = player_hand + community_cards
    ranks = [c[0] for c in all_cards]
    suits = [c[1] for c in all_cards]
    outs = 0

    # Flush draw.
    for s in set(suits):
        if suits.count(s) == 4:
            outs += 9

    # Straight draws.
    rank_nums = sorted(set(rank_value(r) for r in ranks))
    for combo in combinations(rank_nums, min(4, len(rank_nums))):
        if len(combo) < 4:
            continue
        low, high = min(combo), max(combo)
        if high - low == 3:
            outs += 8
        elif high - low == 4:
            outs += 4

    # Overcards.
    community_ranks = [c[0] for c in community_cards]
    for card in player_hand:
        if card[0] not in community_ranks:
            outs += 2

    return min(outs, MAX_OUTS)


def probability_to_hit_by_river(outs, cards_remaining, cards_to_come):
    """
    Calculates the probability of hitting at least one out using the
    the cumulative miss probability.

    Args:
        outs (int): Number of cards that improve the hand.
        cards_remaining (int): Cards left in the deck.
        cards_to_come (int): Number of cards still to be dealt.

    Returns:
        float: Hit probability (0.0–1.0). Returns 0.0 if outs or
               cards_remaining are zero or negative.
    """
    if outs <= 0 or cards_remaining <= 0:
        return 0.0
    miss_prob = 1.0
    remaining = cards_remaining
    for _ in range(cards_to_come):
        if remaining <= 0:
            break
        miss_prob *= (remaining - outs) / remaining
        remaining -= 1
    return 1.0 - miss_prob


def minimum_defense_frequency(bet, pot):
    """
    Returns the Minimum Defense Frequency (MDF) required to prevent an
    opponent's bet from being automatically profitable.

    MDF = pot / (pot + bet)

    Args:
        bet (float): Size of the bet faced.
        pot (float): Size of the pot before the bet.

    Returns:
        float: MDF (0.0–1.0). Returns 0.0 if bet is zero or negative.
    """
    if bet <= 0:
        return 0.0
    return pot / (pot + bet)


def optimal_bluff_ratio(pot, bet):
    """
    Returns the optimal bluffing frequency that makes an
    opponent indifferent to calling or folding.

    Args:
        pot (float): Current pot size.
        bet (float): Size of the proposed bluff.

    Returns:
        float: Optimal bluff frequency (0.0–1.0). Returns 0.0 if either
               argument is zero or negative.
    """
    if bet <= 0 or pot <= 0:
        return 0.0
    return bet / (pot + bet)


def should_bluff_call(pot, to_call, equity, opponent_fold_to_raise, bot):
    """
    Determines whether the bot should bluff call.

    Args:
        pot (float): Current pot size.
        to_call (float): Amount required to call.
        equity (float): Current hand equity (0.0–1.0).
        opponent_fold_to_raise (float): Opponent fold-to-raise tendency.
        bot (BotCharacteristics): Bot decision parameters.

    Returns:
        bool: True if the bot should bluff-call.
    """
    if equity > pot_odds(pot, to_call) * 1.2:
        return False
    base = optimal_bluff_ratio(pot, to_call)
    adjusted = base * bot.bluff_multiplier * opponent_fold_to_raise
    return random.random() < adjusted


def should_bluff_raise(pot, raise_amount, equity, opponent_fold_to_raise, bot):
    """
    Determines whether the bot should make a bluff raise.

    Args:
        pot (float): Current pot size.
        raise_amount (float): Proposed raise size.
        equity (float): Current hand equity (0.0–1.0).
        opponent_fold_to_raise (float): Opponent fold-to-raise tendency.
        bot (BotCharacteristics): Bot decision parameters.

    Returns:
        bool: True if the bot should bluff-raise.
    """
    if equity > 0.6:
        return False
    base = optimal_bluff_ratio(pot, raise_amount)
    adjusted = base * bot.bluff_multiplier * opponent_fold_to_raise * 1.5
    return random.random() < adjusted


def calculate_raise_amount(pot, equity, balance, bot):
    """
    Calculates an appropriate raise amount based on pot size, hand equity,
    available balance and bot difficulty. High-difficulty bots use larger
    sizing. The result is rounded down to the nearest £5 and capped at
    the player's balance.

    Args:
        pot (float): Current pot size.
        equity (float): Hand equity used to scale the raise (0.0–1.0).
        balance (float): Player's available chips.
        bot (BotCharacteristics): Bot decision parameters.

    Returns:
        int: Proposed raise amount rounded to nearest £5.
    """
    if bot.difficulty >= 80:
        min_raise = pot * MIN_RAISE_FACTOR_HIGH_DIFF
        max_raise = pot * MAX_RAISE_FACTOR_HIGH_DIFF
    else:
        min_raise = pot * MIN_RAISE_FACTOR_LOW_DIFF
        max_raise = pot * MAX_RAISE_FACTOR_LOW_DIFF

    max_raise = min(max_raise, balance)
    proposed = min_raise + (max_raise - min_raise) * equity
    return int(proposed / 5) * 5


def cards_to_notation(player_hand):
    """
    Converts a two-card hole hand into its standard notation string with
    the higher-ranked card first.

    Args:
        player_hand (list[str]): Two card strings in 'Rs' format
                                 (e.g. '['As', 'Kh']').

    Returns:
        str: Notation string — pocket pair (e.g. ''AA''), suited
             (e.g. ''AKs'') or offsuit (e.g. ''AKo'').
    """
    ranks = "23456789TJQKA"

    rank1, suit1 = player_hand[0][0], player_hand[0][1]
    rank2, suit2 = player_hand[1][0], player_hand[1][1]

    if ranks.index(rank1) < ranks.index(rank2):
        rank1, rank2 = rank2, rank1
        suit1, suit2 = suit2, suit1

    if rank1 == rank2:
        return rank1 + rank2
    return rank1 + rank2 + ("s" if suit1 == suit2 else "o")


# POKER DECISION ENGINE


def make_decision(
    player_hand,
    player_range,
    community_cards,
    opponent_ranges,
    opponents,
    pot,
    balance,
    to_call,
    bot,
    street,
):
    """
    Makes a poker decision for a bot.

    Each step is applied in order. The first step that produces a
    conclusive action returns immediately.

    Args:
        player_hand (list[str]): The player's two hole cards.
        player_range (dict): The player's current range chart.
        community_cards (list[str]): Current community cards (0–5).
        opponent_ranges (list[dict]): One range chart per opponent.
        opponents (list[PokerPlayer]): Active opponent player objects.
        pot (float): Current pot size.
        balance (float): Player's available chips.
        to_call (float): Amount required to call.
        bot (BotCharacteristics): Bot decision-making parameters.
        street (str): Current betting round — 'preflop', 'flop', 'turn',
        or 'river'.

    Returns:
        tuple: One of:
               - '("fold",)'
               - '("call",)'
               - '("raise", amount)'
    """
    # Human players pass bot=None
    if bot is None:
        return ("call",) if to_call == 0 else ("fold",)

    error_prob = max(0.0, 1.0 - bot.difficulty / 100.0)

    # Preflop range check.
    if street == "preflop" and player_range is not None:
        hand_notation = cards_to_notation(player_hand)
        hand_strength_in_range = player_range.get(hand_notation, 0.0)

        if hand_strength_in_range == 0.0:
            # Hand not in range, fold unless range deviation roll passes.
            if random.random() > (1.0 - bot.range_adherence):
                pass  # Deviate, play as a bluff.
            else:
                return ("fold",) if to_call > 0 else ("call",)

        range_multiplier = 0.5 + (hand_strength_in_range * 0.5)
    else:
        hand_notation = None
        hand_strength_in_range = 0.5
        range_multiplier = 1.0

    # Equity calculation.
    equity = collective_hand_equity(
        player_hand,
        community_cards,
        opponent_ranges,
        bot,
    )
    equity = apply_noise(equity, bot)
    equity *= range_multiplier
    equity *= bot.risk_tolerance

    if random.random() < error_prob:
        equity *= random.uniform(0.5, 0.9)

    # Good river hands.
    if street == "river":
        if bot.difficulty >= 85 and bot.risk_tolerance >= 1.0:
            hand_type = describe_hand(player_hand, community_cards)
            if hand_type in ("Straight Flush", "Four of a Kind", "Full House"):
                raise_amount = calculate_raise_amount(pot, equity, balance, bot)
                return ("raise", raise_amount)

    # Pot-odds maths.
    pot_odds_required = pot_odds(pot, to_call)
    ev_call = expected_value_of_call(pot, to_call, equity)

    # Drawing logic (flop and turn only).
    if street in ("flop", "turn"):
        outs = estimate_outs(player_hand, community_cards)
        cards_remaining = 52 - len(player_hand) - len(community_cards)
        cards_to_come = 2 if street == "flop" else 1
        draw_equity = probability_to_hit_by_river(outs, cards_remaining, cards_to_come)
        equity = max(equity, draw_equity)

    # Value raise with strong hands.
    if equity > 0.65 and balance > 0:
        raise_amount = calculate_raise_amount(pot, equity, balance, bot)
        if 0 < raise_amount <= balance:
            return ("raise", raise_amount)

    # Clear positive-EV call.
    if bot.difficulty >= 50 and ev_call > 0:
        return ("call",)

    # Minimum Defence Frequency.
    mdf = minimum_defense_frequency(to_call, pot) * bot.mdf_threshold
    if equity >= pot_odds_required:
        mdf_check = mdf
        if random.random() < error_prob:
            mdf_check *= random.uniform(0.3, 0.8)
        if random.random() < mdf_check:
            return ("call",)

    # Bluffing logic.
    if opponents:
        avg_fold_to_raise = sum(o.fold_to_raise for o in opponents) / len(opponents)
        avg_call_when_weak = sum(o.call_when_weak for o in opponents) / len(opponents)
    else:
        avg_fold_to_raise = 0.5
        avg_call_when_weak = 0.5

    should_attempt_bluff = False
    bluff_action = None

    if equity < 0.4:
        if should_bluff_raise(pot, to_call * 3, equity, avg_fold_to_raise, bot):
            if avg_fold_to_raise > avg_call_when_weak:
                should_attempt_bluff = True
                bluff_action = "raise"
            elif random.random() < 0.3:
                should_attempt_bluff = True
                bluff_action = "raise"
    elif 0.4 <= equity < 0.5:
        if should_bluff_call(pot, to_call, equity, avg_fold_to_raise, bot):
            should_attempt_bluff = True
            bluff_action = "call"

    # Low-difficulty bots make random bluffing errors and
    # only applied when no deliberate bluff was already chosen.
    if not should_attempt_bluff and random.random() < error_prob:
        should_attempt_bluff = random.choice([True, False])
        bluff_action = random.choice(["raise", "call"])

    if should_attempt_bluff:
        if bluff_action == "raise":
            raise_amount = calculate_raise_amount(pot, equity, balance, bot)
            return ("raise", raise_amount if raise_amount <= balance else int(balance))
        elif bluff_action == "call" and to_call <= balance:
            return ("call",)

    # Fold bias
    if to_call <= balance and random.random() < bot.fold_bias:
        return ("call",)

    # Default action — fold
    return ("fold",)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# harrogate_hold_em.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


DEFAULT_BOT_LIST = [
    "Player1",
    "Player2",
    "Player3",
]


class TournamentManager:
    """
    Manages multi-round tournaments for Harrogate Hold 'Em.
    """

    def __init__(self, settings):
        self.total_rounds = settings.get("tournament_rounds", 5)
        self.base_small_blind = settings.get("small_blind", 50)
        self.base_big_blind = settings.get("big_blind", 100)

        self.current_round = 1
        self.rounds_survived = 0
        self.round_wins = 0
        self.tournament_over = False
        self.tournament_won = False

    @property
    def current_small_blind(self):
        escalation = max(1, (self.current_round - 1) // 3)
        raw = int(self.base_small_blind * (1.5**escalation))
        return min(raw, TOURNAMENT_SMALL_BLIND_CAP)

    @property
    def current_big_blind(self):
        escalation = max(1, (self.current_round - 1) // 3)
        raw = int(self.base_big_blind * (1.5**escalation))
        return min(raw, TOURNAMENT_BIG_BLIND_CAP)

    def advance_round(self, human_won_round):
        """
        Advances the tournament state after a round ends.

        Args:
            human_won_round (bool): True if the human won the betting round
                                    (i.e. end_round was called with win=True).
        Returns:
            dict: tournament_over, tournament_won, message.
        """
        if human_won_round:
            self.round_wins += 1
        self.rounds_survived += 1
        self.current_round += 1

        if self.current_round > self.total_rounds:
            self.tournament_over = True
            self.tournament_won = self.round_wins > 0
            message = (
                f"Tournament complete!\n"
                f"You won {self.round_wins} of {self.total_rounds} rounds.\n"
            )
            message += (
                "Tournament Victory!"
                if self.tournament_won
                else "Better luck next time."
            )
            return {
                "tournament_over": True,
                "tournament_won": self.tournament_won,
                "message": message,
            }

        return {
            "tournament_over": False,
            "tournament_won": False,
            "message": (
                f"Round {self.current_round - 1} complete.  "
                f"{'Round won!' if human_won_round else 'Round lost.'}\n"
                f"Round {self.current_round} of {self.total_rounds}.\n"
                f"Win condition: Win the betting round (pot).\n"
                f"Blinds: £{self.current_small_blind} / £{self.current_big_blind}"
            ),
        }

    def fetch_status_text(self):
        if not self.tournament_over:
            return (
                f"Tournament  |  Round {self.current_round}/{self.total_rounds}  |  "
                f"Round Wins: {self.round_wins}  |  "
                f"Blinds: £{self.current_small_blind} / £{self.current_big_blind}"
            )
        return f"Tournament Over  |  Round Wins: {self.round_wins}/{self.total_rounds}"


class HarrogateHoldEm:
    """
    Handles all game flow, betting logic, card dealing, bot interactions,
    tournament management and logging for Harrogate Hold'em. Runs its own
    tkinter mainloop and returns to the menu on exit.
    """

    def __init__(self, user_data, settings, bots):
        """
        Sets up external resources and initialises game state variables.
        """
        self.user_data = user_data

        self.window_bg = CS["casino"]
        self.hhe_root = Tk()
        self.main_frame, self.styles = create_window(
            self.hhe_root,
            "One Less Time Casino — Harrogate Hold 'Em",
            self.window_bg,
            is_main_frame=True,
        )
        self.hhe_root.protocol(
            "WM_DELETE_WINDOW", lambda: (self.hhe_root.quit(), sys.exit(0))
        )

        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        self.bot_decision_queue = Queue()
        self.bot_thinking = False

        self.dbm = DatabaseManagement(DB_PATH)

        if (
            not user_data.get("administrator")
            and user_data.get("user_id") is not None
            and not self.dbm.check_user_poker_data_exists(user_data["user_id"])
        ):
            self.dbm.initialise_user_poker_data(user_data["user_id"])

        self.tournament_mode = settings.get("tournament_mode", False)
        if self.tournament_mode:
            self.tournament = TournamentManager(settings)
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind
        else:
            self.tournament = None
            self.small_blind_value = settings.get("small_blind", 50)
            self.big_blind_value = settings.get("big_blind", 100)

        # Determine how many bots will be seated.
        seated_bot_count = (
            TOURNAMENT_BOT_COUNT
            if self.tournament_mode
            else settings.get("bot_count", len(bots))
        )

        # Build bot lookup.
        self.bots = {}
        for index, bot in enumerate(bots[:seated_bot_count]):
            self.bots[index] = {"name": bot[0], "difficulty": bot[1]}

        if self.tournament_mode:
            tournament_balance = TOURNAMENT_USER_START_BALANCE
        else:
            tournament_balance = None

        # Build player list.
        self.players = []

        player_model = None
        if self.user_data.get("user_id"):
            try:
                player_model = HumanPokerPlayer(user_id=self.user_data["user_id"])
            except Exception as exception:
                messagebox.showerror(
                    "Error", f"Failed to initialise player model: {exception}"
                )
                player_model = None

        self.players.append(
            {
                "player": user_data["username"] + " (You)",
                "position": None,
                "cards": [],
                "balance": (
                    tournament_balance
                    if tournament_balance is not None
                    else self.return_balance()
                ),
                "bet": 0,
                "status": "Waiting",
                "is_bot": False,
                "user_id": self.user_data["user_id"],
                "model": player_model,
            }
        )

        self.current_round_number = 1
        self.actions_logged = []

        bot_balance = (
            TOURNAMENT_BOT_START_BALANCE
            if self.tournament_mode
            else settings.get("bot_balance", 1000)
        )

        for index in range(seated_bot_count):
            self.players.append(
                {
                    "player": self.bots[index]["name"],
                    "position": None,
                    "cards": [],
                    "balance": bot_balance,
                    "bet": 0,
                    "status": "Waiting",
                    "is_bot": True,
                    "user_id": None,
                    "model": BotPokerPlayer(
                        difficulty=max(0, self.bots[index]["difficulty"])
                    ),
                }
            )

        random.shuffle(self.players)
        for position, player in enumerate(self.players, start=1):
            player["position"] = position

        self.player_count = len(self.players)
        self.player_go = None

        self.initial_position = -1
        self.current_position = 0
        self.action_position = 0

        self.small_blind_player = None
        self.big_blind_player = None

        self.current_bet = 0
        self.pot_size = 0

        self.player_turn = False
        self.round_active = False
        self.round_number = 1

        self.street = ""
        self.board = [[], []]
        self.flop = [[], []]
        self.turn = [[], []]
        self.river = [[], []]

        self.action_buttons = []

        if self.tournament_mode:
            self.start_balance = TOURNAMENT_USER_START_BALANCE
            set_view(self, self.hhe_screen)
            self.check_bot_decision_queue()
        elif not self.user_data.get("administrator"):
            balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
            if not balance_data["found"]:
                self.return_to_menu(
                    is_error=True, error=Exception("User not found in database.")
                )
                return
            self.start_balance = balance_data["balance"]
            set_view(self, self.hhe_screen)
            self.check_bot_decision_queue()
        else:
            self.start_balance = 0
            set_view(self, self.admin_modify_bet)

        self.hhe_root.mainloop()

    def admin_modify_bet(self, frame):
        """
        Opens a modal Toplevel dialog that allows the administrator to set
        a custom starting chip balance. The dialog cannot be dismissed through
        the window manager, a valid balance must be submitted.

        When called from __init__ (before hhe_screen has run) the
        dialog navigates to hhe_screen on submission. When called
        from check_balance mid-game it only updates the balance label and
        closes, preserving all active game state.

        Args:
            frame (Frame or Tk): The parent widget used to anchor the
                                 Toplevel dialog.
        """
        screen_built = getattr(self, "balance_label", None) is not None

        balance_window = Toplevel(frame)
        create_window(
            balance_window,
            "Set Starting Balance",
            self.window_bg,
        )
        balance_window.grab_set()
        balance_window.protocol("WM_DELETE_WINDOW", lambda: None)
        balance_window.focus_force()

        preset_label(
            balance_window,
            text="Enter starting balance (£):",
        ).pack(pady=8)

        balance_entry = preset_entry(
            balance_window,
            width=20,
        )
        balance_entry.pack(pady=5)

        def submit_balance():
            """
            Validates the balance entry and closes the dialog. If the main
            game screen has not yet been built, navigates to hhe_screen.
            If the screen is already live, updates the balance label in place
            without disturbing game state.
            """
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()
                self.start_balance = balance
                self.dbm.modify_user_balance(self.user_data["username"], balance)
                balance_window.destroy()
                if screen_built:
                    self.balance_label.config(text=f"Balance: £{balance}")
                else:
                    set_view(self, self.hhe_screen)
                    self.check_bot_decision_queue()

            except Exception:
                messagebox.showerror("Error", "Please enter a valid positive integer.")

        preset_button(
            balance_window,
            text="Submit",
            relief="flat",
            command=submit_balance,
        ).pack(pady=10)

    def hhe_screen(self, frame):
        """
        Builds the main five-panel game layout using a grid:

        - Top-left: game state labels (round, board, blinds, pot, turn,
          tournament status).
        - Bottom-left: scrollable colour-coded game log.
        - Top-right: user information, balance and Return to Menu button.
        - Middle-right: scrollable players list.
        - Bottom-right: scrollable bet entry controls and action buttons.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=2)
        frame.rowconfigure(2, weight=1)

        top_left_frame = Frame(frame, bd=2, relief="sunken", bg=CS["top_left"])
        top_left_frame.grid(column=0, row=0, sticky="nsew", padx=5, pady=5)

        self.round_number_label = preset_label(
            top_left_frame,
            bg=CS["round_label_bg"],
            fg=CS["round_label_fg"],
            relief="groove",
            anchor="w",
        )
        self.round_number_label.pack(fill="x", padx=10, pady=5)

        self.board_label = preset_label(
            top_left_frame,
            bg=CS["top_left"],
            relief="flat",
            anchor="w",
        )
        self.board_label.pack(fill="x", padx=10, pady=5)

        self.player_blinds_label = preset_label(
            top_left_frame,
            bg=CS["top_left"],
            relief="flat",
            anchor="w",
        )
        self.player_blinds_label.pack(fill="x", padx=10, pady=5)

        self.pot_size_label = preset_label(
            top_left_frame,
            bg=CS["top_left"],
            relief="flat",
            anchor="w",
        )
        self.pot_size_label.pack(fill="x", padx=10, pady=5)

        self.player_turn_label = preset_label(
            top_left_frame,
            font=self.styles["emphasis"],
            bg=CS["top_left"],
            relief="flat",
            anchor="w",
        )
        self.player_turn_label.pack(fill="x", padx=10, pady=5)

        self.tournament_label = preset_label(
            top_left_frame,
            font=self.styles["emphasis"],
            bg=CS["tournament_bg"],
            fg=CS["tournament_fg"],
            relief="flat",
        )
        if self.tournament_mode:
            self.tournament_label.pack(fill="x", padx=10, pady=4)

        bottom_left_frame = Frame(frame, bd=2, relief="sunken", bg=CS["bottom_left"])
        bottom_left_frame.grid(
            column=0, row=1, rowspan=2, sticky="nsew", padx=5, pady=5
        )

        self.log_canvas = Canvas(
            bottom_left_frame, bg=CS["bottom_left"], highlightthickness=0
        )
        log_sb = Scrollbar(
            bottom_left_frame, orient="vertical", command=self.log_canvas.yview
        )
        self.log_canvas.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_canvas.pack(side="left", fill="both", expand=True)

        self.log_frame = Frame(self.log_canvas, bg=CS["bottom_left"])
        self.log_window = self.log_canvas.create_window(
            (0, 0), window=self.log_frame, anchor="nw"
        )

        self.log_canvas.bind(
            "<Configure>",
            lambda e: self.log_canvas.itemconfig(self.log_window, width=e.width),
        )
        self.log_frame.bind(
            "<Configure>",
            lambda e: self.log_canvas.configure(
                scrollregion=self.log_canvas.bbox("all")
            ),
        )

        top_right_frame = Frame(frame, bd=2, relief="sunken", bg=CS["top_right"])
        top_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        preset_button(
            top_right_frame,
            text="Return to Menu",
            command=self.return_to_menu,
        ).pack(pady=5)

        labels = []
        for text in (
            f"Username: {self.user_data['username']}",
            f"Balance: £{self.start_balance}",
            "Current Bet: £0",
            f"Blinds: £{self.small_blind_value} / £{self.big_blind_value}",
        ):
            label = preset_label(
                top_right_frame,
                text=text,
                anchor="w",
            )
            label.pack(anchor="w", pady=5, padx=5)
            labels.append(label)

        self.balance_label = labels[1]
        self.current_bet_label = labels[2]
        self.blinds_label = labels[3]

        middle_right_frame = Frame(frame, bd=2, relief="sunken", bg=CS["middle_right"])
        middle_right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        middle_right_frame.columnconfigure(0, weight=1)
        middle_right_frame.columnconfigure(1, weight=0)
        middle_right_frame.rowconfigure(0, weight=1)

        self.players_canvas = Canvas(
            middle_right_frame, bg=CS["middle_right"], highlightthickness=0
        )
        self.players_canvas.grid(row=0, column=0, sticky="nsew")

        players_sb = Scrollbar(
            middle_right_frame, orient="vertical", command=self.players_canvas.yview
        )
        players_sb.grid(row=0, column=1, sticky="ns")
        self.players_canvas.configure(yscrollcommand=players_sb.set)

        self.players_frame = Frame(self.players_canvas, bg=CS["middle_right"])
        self.players_window = self.players_canvas.create_window(
            (0, 0), window=self.players_frame, anchor="nw"
        )

        self.players_canvas.bind(
            "<Configure>",
            lambda e: self.players_canvas.itemconfig(
                self.players_window, width=e.width
            ),
        )
        self.players_frame.bind(
            "<Configure>",
            lambda e: self.players_canvas.configure(
                scrollregion=self.players_canvas.bbox("all")
            ),
        )

        self.update_player_status()

        bottom_right_outer = Frame(frame, bd=2, relief="sunken", bg=CS["bottom_right"])
        bottom_right_outer.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        bottom_right_outer.columnconfigure(0, weight=1)
        bottom_right_outer.columnconfigure(1, weight=0)
        bottom_right_outer.rowconfigure(0, weight=1)

        bottom_right_canvas = Canvas(
            bottom_right_outer, bg=CS["bottom_right"], highlightthickness=0
        )
        bottom_right_canvas.grid(row=0, column=0, sticky="nsew")

        bottom_right_sb = Scrollbar(
            bottom_right_outer, orient="vertical", command=bottom_right_canvas.yview
        )
        bottom_right_sb.grid(row=0, column=1, sticky="ns")
        bottom_right_canvas.configure(yscrollcommand=bottom_right_sb.set)

        bottom_right_frame = Frame(bottom_right_canvas, bg=CS["bottom_right"])
        bottom_right_window = bottom_right_canvas.create_window(
            (0, 0), window=bottom_right_frame, anchor="nw"
        )

        bottom_right_canvas.bind(
            "<Configure>",
            lambda e: bottom_right_canvas.itemconfig(
                bottom_right_window, width=e.width
            ),
        )
        bottom_right_frame.bind(
            "<Configure>",
            lambda e: bottom_right_canvas.configure(
                scrollregion=bottom_right_canvas.bbox("all")
            ),
        )

        def check_bet_input(amount=0):
            try:
                current_value = int(self.bet_var.get())
                new_value = max(0, current_value + amount)
                balance = self.return_balance()
                if balance is not None:
                    new_value = min(new_value, int(balance))
            except (ValueError, TypeError):
                new_value = 0

            self.bet_var.set(str(new_value))
            self.current_bet_label.config(text=f"Raise Amount: £{new_value}")

            state = (
                "normal" if (new_value > 0 and not self.round_active) else "disabled"
            )
            self.start_button.config(state=state)

        # Increment rows
        for inc in (1, 10, 100, 1000):
            row = Frame(
                bottom_right_frame,
                padx=6,
                pady=3,
            )
            row.pack(fill="x", pady=3)

            preset_button(
                row,
                text="+",
                width=3,
                command=lambda v=inc: check_bet_input(amount=v),
            ).pack(side="left", padx=4)

            preset_label(
                row,
                text=str(inc),
                width=8,
                anchor="center",
            ).pack(side="left", expand=True)

            preset_button(
                row,
                text="-",
                width=3,
                command=lambda v=-inc: check_bet_input(amount=v),
            ).pack(side="right", padx=4)

        for text, command in (
            ("Raise", self.raise_bet),
            ("Call", self.call),
            ("Fold", self.fold),
        ):
            button = preset_button(
                bottom_right_frame,
                text=text,
                width=18,
                command=command,
                state="disabled",
            )
            button.pack(pady=6)
            self.action_buttons.append(button)

        self.start_button = preset_button(
            bottom_right_frame,
            text=f"Start Round {self.round_number}",
            width=18,
            cursor="hand2",
            command=self.check_round,
        )
        self.start_button.pack(pady=10)

        self.bet_var = StringVar(value="0")
        self.bet_var.trace_add("write", lambda *_: check_bet_input())

        self.update_button_states()

    def update_player_status(self):
        """
        Rebuilds the players list panel inside self.players_frame.
        Displays for each player: name with position indicators ([SB], [BB],
        current-turn arrow <), hole cards (visible for the human player and at
        showdown; face-down [?] [?] for bots otherwise), balance,
        current-round bet and status string.

        Called both on initial layout and by update_player_status() on every
        refresh so that styling is always consistent.
        """
        for widget in self.players_frame.winfo_children():
            widget.destroy()

        preset_label(
            self.players_frame,
            text="Players",
            bg=CS["middle_right"],
            font=self.styles["subheading"],
        ).pack(anchor="w", padx=8, pady=(6, 10))

        Frame(self.players_frame, height=1, bg=CS["widget_bg"]).pack(
            fill="x", padx=8, pady=2
        )

        for player in self.players:
            row_f = Frame(self.players_frame, bg=CS["middle_right"])
            row_f.pack(fill="x", padx=8, pady=4)

            left_f = Frame(row_f, bg=CS["middle_right"])
            left_f.pack(side="left", fill="x", expand=True)

            pos_text = ""
            if self.round_active:
                if player is self.small_blind_player:
                    pos_text = "  [SB]"
                elif player is self.big_blind_player:
                    pos_text = "  [BB]"
                if (
                    player["position"] - 1 == self.current_position
                    and player["status"] == "Waiting"
                ):
                    pos_text += "  <"

            preset_label(
                left_f,
                text=player["player"] + pos_text,
                bg=CS["middle_right"],
                relief="flat",
                anchor="w",
                wraplength=180,
            ).pack(fill="x")

            if self.round_active and player["cards"]:
                if not player["is_bot"] or self.street == "showdown":
                    cards_text = (
                        " ".join(player["cards"][1]) if len(player["cards"]) > 1 else ""
                    )
                    if cards_text:
                        preset_label(
                            left_f,
                            text=f"Cards:  {cards_text}",
                            bg=CS["middle_right"],
                            relief="flat",
                            anchor="w",
                        ).pack(fill="x")
                else:
                    preset_label(
                        left_f,
                        text="Cards:  [?]  [?]",
                        bg=CS["middle_right"],
                        relief="flat",
                        anchor="w",
                    ).pack(fill="x")

            right_f = Frame(row_f, bg=CS["middle_right"])
            right_f.pack(side="right")

            preset_label(
                right_f,
                text=f"£{player['balance']}",
                bg=CS["middle_right"],
                relief="flat",
                anchor="e",
                width=8,
            ).pack(anchor="e")

            if player["bet"] > 0:
                preset_label(
                    right_f,
                    text=f"Bet:  £{player['bet']}",
                    bg=CS["middle_right"],
                    relief="flat",
                    anchor="e",
                ).pack(anchor="e")

            preset_label(
                right_f,
                text=player["status"],
                bg=CS["middle_right"],
                relief="flat",
                anchor="e",
            ).pack(anchor="e")

            Frame(self.players_frame, height=1, bg=CS["widget_bg"]).pack(
                fill="x", padx=8, pady=2
            )

    def update_ui(self):
        """
        Refreshes all three UI components,
        labels, button states and the players list panel in one call.
        """
        self.update_labels()
        self.update_button_states()
        self.update_player_status()

    def update_labels(self):
        """
        Refreshes all dynamic game-state labels: balance, blinds, round
        number, board cards, blind assignments, pot size, current turn,
        and (when in tournament mode) the tournament status banner.
        Guards safely against updating already-destroyed widgets.
        """
        if (
            not getattr(self, "balance_label", None)
            or not self.balance_label.winfo_exists()
        ):
            return

        human_index = linear_search(self.players, "is_bot", False)
        human_balance = self.players[human_index]["balance"] if human_index != -1 else 0
        self.balance_label.config(text=f"Balance: £{human_balance}")

        if getattr(self, "blinds_label", None) and self.blinds_label.winfo_exists():
            self.blinds_label.config(
                text=f"Blinds: £{self.small_blind_value} / £{self.big_blind_value}"
            )

        if (
            getattr(self, "tournament_label", None)
            and self.tournament_label.winfo_exists()
        ):
            if self.tournament_mode and self.tournament:
                self.tournament_label.config(text=self.tournament.fetch_status_text())

        if (
            not getattr(self, "round_number_label", None)
            or not self.round_number_label.winfo_exists()
        ):
            return

        if not self.round_active:
            self.round_number_label.config(
                text="Harrogate Hold 'Em"
                + ("TOURNAMENT" if self.tournament_mode else "")
            )
            board_text = (
                f"Tournament Round {self.tournament.current_round}/{self.tournament.total_rounds}"
                if self.tournament_mode and self.tournament
                else "Casual mode."
            )

            self.board_label.config(text=board_text)
            self.player_blinds_label.config(text="")
            self.pot_size_label.config(text="Waiting for round to commence…")
            self.player_turn_label.config(text="")
            return

        self.round_number_label.config(text=f"Round {self.round_number}")

        if self.street == "preflop":
            self.board_label.config(text="The Board:  |?|  |?|  |?|  |?|  |?|")
        elif self.street == "flop":
            self.board_label.config(
                text=f"The Board:  {' '.join(str(c) for c in self.flop[1])}  |?|  |?|"
            )
        elif self.street == "turn":
            flop_cards = self.flop[1] if self.flop[1] else []
            turn_cards = self.turn[1] if self.turn[1] else []
            self.board_label.config(
                text=f"The Board:  {' '.join(str(card) for card in flop_cards + turn_cards)}  |?|"
            )
        elif self.street in ("river", "showdown"):
            self.board_label.config(
                text=f"The Board:  {' '.join(str(c) for c in self.board[1])}"
            )
        else:
            self.board_label.config(text="")

        if self.small_blind_player and self.big_blind_player:
            self.player_blinds_label.config(
                text=(
                    f"Small Blind: {self.small_blind_player['player']}  |  "
                    f"Big Blind: {self.big_blind_player['player']}"
                )
            )

        self.pot_size_label.config(text=f"Pot: £{self.pot_size}")

        if self.street == "showdown":
            self.player_turn_label.config(text="— SHOWDOWN —")
        elif self.player_go and self.street:
            self.player_turn_label.config(text=f"It is {self.player_go}'s turn.")
        else:
            self.player_turn_label.config(text="")

    def update_button_states(self):
        """
        Enables or disables the Start Round and action buttons based on
        the current game and turn state.

        During the human player's turn the buttons are labelled to reflect
        the exact call amount and minimum raise. The Raise button is
        disabled when the player cannot afford the minimum raise. All
        action buttons are disabled outside the human player's turn.
        """
        self.start_button.config(state="disabled" if self.round_active else "normal")

        if self.round_active and self.player_turn:
            human_index = linear_search(self.players, "is_bot", False)
            human = self.players[human_index] if human_index != -1 else None
            if human:
                call_amount = max(0, self.current_bet - human["bet"])
                min_raise = max(
                    self.current_bet - human["bet"] + self.big_blind_value,
                    self.big_blind_value,
                )
                raise_state = "normal" if human["balance"] > 0 else "disabled"
                self.action_buttons[0].config(
                    text=f"Raise  (min £{min_raise})", state=raise_state
                )
                if call_amount == 0:
                    self.action_buttons[1].config(text="Check", state="normal")
                else:
                    self.action_buttons[1].config(
                        text=f"Call  £{call_amount}",
                        state=(
                            "normal" if call_amount <= human["balance"] else "disabled"
                        ),
                    )
                self.action_buttons[2].config(state="normal")
            else:
                for button in self.action_buttons:
                    button.config(state="disabled")
        else:
            self.action_buttons[0].config(text="Raise", state="disabled")
            self.action_buttons[1].config(text="Call", state="disabled")
            self.action_buttons[2].config(text="Fold", state="disabled")

    def reset_players(self):
        """
        Prepares all players for a new round by clearing their hole cards,
        resetting bets to zero and restoring status to 'Waiting'.
        Players whose status is 'OUT' are left unchanged.
        """
        for player in self.players:
            self.modify_player(player, cards=[], refresh_player_model=True)
            if player["status"] != "OUT":
                player["status"] = "Waiting"
            player["bet"] = 0

    def modify_player(
        self,
        player,
        cards=None,
        change_balance=None,
        bet=None,
        status=None,
        refresh_player_model=False,
    ):
        """
        Updates one or more attributes of a player dictionary in-place.
        Parameters passed as None are left unchanged.

        Args:
            player (dict): The player dictionary to modify.
            cards (list or None): If an empty list, clears the player's
                cards. If a non-empty list of treys card integers,
                converts and stores them through deck.treys_to_str_pretty().
            change_balance (float or None): Amount to add to (positive)
                or subtract from (negative) the player's current balance.
            bet (float or None): New absolute bet amount to assign.
            status (str or None): New status string to assign.
            refresh_player_model (bool): If True and the player is human,
                reloads their poker statistics from the database and resets
                their active range. Defaults to False.
        """
        if player is None:
            return
        if cards is not None:
            player["cards"] = self.deck.treys_to_str_pretty(cards) if cards else cards
        if change_balance is not None:
            player["balance"] += change_balance
        if bet is not None:
            player["bet"] = bet
        if status is not None:
            player["status"] = status
        if refresh_player_model and not player["is_bot"] and player["model"]:
            player["model"].refresh_from_db()
            player["model"].reset_active_range()

    def log_message(
        self,
        text,
        *,
        round_start=False,
        is_win=False,
        is_loss=False,
        tie=False,
        is_thinking=False,
        is_tournament=False,
    ):
        """
        Appends a message to the log queue and starts the queue processor
        if it is not already running.

        Args:
            text (str): The message to display.
            round_start (bool): Style as a round-start entry.
            is_win (bool): Style as a win entry.
            is_loss (bool): Style as a loss entry.
            tie (bool): Style as a tie entry.
            is_thinking (bool): Style as a bot-thinking entry.
            is_tournament (bool): Style as a tournament-event entry.
        """
        self.log_queue.append(
            (text, round_start, is_win, is_loss, tie, is_thinking, is_tournament)
        )
        if not self.log_active:
            self.process_log_queue()

    def process_log_queue(self):
        """
        Pops and renders the next entry from the log queue and then schedules
        itself to run again after log_delay_ms milliseconds. Stops when
        the queue is empty or the log frame has been destroyed. No errors
        are printed if the application stops runnings while the queue is
        processing.
        """
        try:
            if (
                not getattr(self, "log_frame", None)
                or not self.log_frame.winfo_exists()
            ):
                self.log_queue.clear()
                self.log_active = False
                return

            if not self.log_queue:
                self.log_active = False
                return

            self.log_active = True
            item = self.log_queue.pop(0)

            text, round_start, is_win, is_loss, tie, is_thinking, is_tournament = item

            self.render_log(
                text, round_start, is_win, is_loss, tie, is_thinking, is_tournament
            )
            self.hhe_root.after(self.log_delay_ms, self.process_log_queue)
        except Exception:
            pass

    def render_log(
        self, text, round_start, is_win, is_loss, tie, is_thinking, is_tournament=False
    ):
        """
        Creates and packs a colour-coded Label into the log frame for the
        given message and then scrolls the log canvas to the bottom.

        Args:
            text (str): The message text to display.
            round_start (bool): Apply round-start colour.
            is_win (bool): Apply win colour.
            is_loss (bool): Apply loss colour.
            tie (bool): Apply tie colour.
            is_thinking (bool): Apply thinking colour.
            is_tournament (bool): Apply tournament colour.
        """
        if not getattr(self, "log_frame", None) or not self.log_frame.winfo_exists():
            return

        bg = (
            CS["tournament_bg"]
            if is_tournament
            else (
                CS["start_bg"]
                if round_start
                else (
                    CS["win_bg"]
                    if is_win
                    else (
                        CS["loss_bg"]
                        if is_loss
                        else (
                            CS["tie_bg"]
                            if tie
                            else (CS["thinking_bg"] if is_thinking else CS["log_bg"])
                        )
                    )
                )
            )
        )
        fg = (
            CS["tournament_fg"]
            if is_tournament
            else (
                CS["start_fg"]
                if round_start
                else (
                    CS["win_fg"]
                    if is_win
                    else (
                        CS["loss_fg"]
                        if is_loss
                        else (
                            CS["tie_fg"]
                            if tie
                            else (CS["thinking_fg"] if is_thinking else CS["log_fg"])
                        )
                    )
                )
            )
        )

        preset_label(
            self.log_frame,
            text=text,
            bg=bg,
            fg=fg,
            bd=1,
            relief="groove",
            padx=6,
            pady=4,
            wraplength=400,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=3, padx=6)

        self.hhe_root.update_idletasks()
        if getattr(self, "log_canvas", None) and self.log_canvas.winfo_exists():
            self.log_canvas.yview_moveto(1.0)

    def return_balance(self):
        """
        Returns the current balance for the player.

        Returns:
            float: The current balance, or 0 on error.
        """
        if self.tournament_mode:
            human_index = linear_search(self.players, "is_bot", False)
            if human_index != -1:
                return self.players[human_index]["balance"]
            return 0

        balance_data = self.dbm.fetch_user_balance(self.user_data["username"])

        if not balance_data["found"]:
            self.return_to_menu(
                is_error=True, error=Exception("User not found in database.")
            )
            return 0

        if balance_data["balance"] is not None:
            return balance_data["balance"]
        else:
            self.return_to_menu(
                is_error=True, error=Exception("Fetched balance returns 'None'")
            )
            return 0

    def check_balance(self):
        """
        Checks whether the user's balance is zero. For administrators,
        opens the balance modification dialog.

        Returns:
            bool: True if the user can continue playing, False if they have
                  been redirected away.
        """
        if self.return_balance() == 0:
            if self.user_data.get("administrator"):
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is £0. As an administrator, you can set a new balance.",
                )

                self.admin_modify_bet(self.main_frame)
                return True

            else:
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is now £0. Returning to menu.",
                )
                self.return_to_menu()
                return False
        return True

    def modify_user_balance(self, balance):
        """
        Updates a new balance for the player to the database
        and updates the balance label in the UI if it still exists.

        Args:
            balance (int or float): The new balance to store.
        """
        self.dbm.modify_user_balance(self.user_data["username"], balance)
        try:
            if (
                getattr(self, "balance_label", None)
                and self.balance_label.winfo_exists()
            ):
                self.balance_label.config(text=f"Balance: £{balance}")
        except Exception:
            pass

    def log_player_action_to_db(self, action, bet_size):
        """
        Logs the human player's action for the current street and round
        to the database and appends it to the in-memory actions_logged
        list for end-of-round statistics updating.

        Args:
            action (str): The action taken — 'fold', 'call', 'raise',
                          or 'check'.
            bet_size (float): The chip amount committed.
        """
        for player in self.players:
            if not player["is_bot"] and player["user_id"]:
                success = self.dbm.log_player_action(
                    user_id=player["user_id"],
                    round_number=self.current_round_number,
                    street=self.street,
                    action=action,
                    bet_size=bet_size,
                    pot_size=self.pot_size,
                )
                if success:
                    self.actions_logged.append(
                        {
                            "street": self.street,
                            "action": action,
                            "bet_size": bet_size,
                        }
                    )
                break

    def check_round(self):
        """
        Initiates a new round. Clears any pending log entries, resets
        action tracking, logs the round-start message, resets player
        states, refreshes the UI and delegates to play_round().
        """
        self.round_active = True
        self.log_queue.clear()
        self.log_active = False
        self.actions_logged = []

        self.log_message(f"Starting Round {self.round_number}.", round_start=True)
        self.reset_players()
        self.pot_size = 0
        self.update_ui()
        self.play_round()

    def blind_management(self):
        """
        Assigns small blind, big blind and first-action positions for
        the current round. Skips players with 'OUT' status when
        rotating.

        Posts the blinds by deducting from player balances (capped at
        each player's available balance to prevent negative chips),
        adding the amounts to the pot and setting current_bet to the
        big blind amount.
        """
        # Advance dealer button each round for rotation.
        self.initial_position = (self.initial_position + 1) % self.player_count

        # Small blind.
        for attempt in range(self.player_count):
            index = (self.initial_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.small_blind_position = index
                self.small_blind_player = self.players[index]
                break

        # Big blind.
        for attempt in range(self.player_count):
            index = (self.small_blind_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.big_blind_position = index
                self.big_blind_player = self.players[index]
                break

        # Action starts.
        for attempt in range(self.player_count):
            index = (self.big_blind_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.current_position = index
                break

        self.action_position = self.current_position

        # Post blinds.
        for player, amount in (
            (self.small_blind_player, self.small_blind_value),
            (self.big_blind_player, self.big_blind_value),
        ):
            if player is None:
                continue
            actual = min(amount, player["balance"])
            self.modify_player(
                player, bet=actual, change_balance=-actual, status="Decided"
            )

        if self.big_blind_player is not None:
            self.current_bet = self.big_blind_player["bet"]

        if self.small_blind_player is not None and self.big_blind_player is not None:
            self.pot_size += (
                self.small_blind_player["bet"] + self.big_blind_player["bet"]
            )

    def distribute_cards(self):
        """
        Creates a newly shuffled deck, deals two hole cards to each
        active player and then deals and stores five community
        cards split into flop (3), turn (1) and river (1) components.
        """
        self.deck = CasinoDeckManager(shuffle=True, game_mode="poker")

        for player in self.players:
            if player["status"] != "OUT":
                self.modify_player(player, cards=[self.deck.draw(1), self.deck.draw(1)])

        raw_board = [self.deck.draw(1) for _ in range(5)]
        self.board = self.deck.treys_to_str_pretty(raw_board)

        (
            self.flop[0],
            self.flop[1],
            self.turn[0],
            self.turn[1],
            self.river[0],
            self.river[1],
        ) = (
            self.board[0][:3],
            self.board[1][:3],
            self.board[0][3:4],
            self.board[1][3:4],
            self.board[0][4:],
            self.board[1][4:],
        )

    def play_round(self):
        if self.tournament_mode and self.tournament:
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind

        self.blind_management()
        self.distribute_cards()

        for player in self.players:
            if not player["is_bot"]:
                self.log_message(f"Your cards:  {' '.join(player['cards'][1])}")
                break

        self.update_ui()

        self.street_sequence = ["preflop", "flop", "turn", "river", "showdown"]
        self.current_street_index = 0
        self.next_street()

    def decisions(self):
        for attempt in range(self.player_count):
            player = self.players[self.current_position]

            if player["status"] not in ("Decided", "Folded", "OUT", "All-in"):
                self.player_go = player["player"]

                if player["is_bot"]:
                    self.player_turn = False
                    self.update_ui()
                    self.start_bot_decision_queue(player)
                    return
                else:
                    self.player_turn = True
                    self.update_ui()
                    self.log_message("It's your turn to play.")
                    return

            self.current_position = (self.current_position + 1) % self.player_count

            if (
                self.current_position == self.action_position
                and attempt > 0
                and self.is_betting_complete()
            ):
                self.advance_street()
                return

        self.advance_street()

    def start_bot_decision_queue(self, player):
        """
        Launches a bot's decision calculation in a background daemon thread.
        Immediately displays a 'thinking' message in the log.  Calculates a
        difficulty-scaled minimum thinking delay to ensure a consistent pause
        regardless of actual compute time.

        Does nothing if a bot decision is already in progress.

        Args:
            player (dict): The bot player dictionary whose bot model will
                           produce the decision.
        """
        if self.bot_thinking:
            return

        self.bot_thinking = True
        self.log_message(f"{player['player']} is thinking…", is_thinking=True)

        base_ms = 800 + (player["model"].difficulty / 100.0) * 1700
        jitter = random.uniform(-200, 200)
        min_ms = int(base_ms + jitter)

        Thread(
            target=self.bot_decision_worker,
            args=(player, min_ms),
            daemon=True,
        ).start()

    def bot_decision_worker(self, player, min_thinking_ms):
        """
        Background thread worker that computes the bot's decision and
        enforces the minimum thinking delay before placing the result (or
        any exception) onto bot_decision_queue for the main thread.

        Args:
            player (dict): The bot player dictionary.
            min_thinking_ms (int): Minimum elapsed time in milliseconds
                                   before the result is queued.
        """
        start = time()
        try:
            decision = self.bot_decision(player)
            elapsed_ms = (time() - start) * 1000
            remaining = max(0, min_thinking_ms - elapsed_ms)
            if remaining > 0:
                sleep(remaining / 1000.0)
            self.bot_decision_queue.put((player, decision, None))
        except Exception as exception:
            self.bot_decision_queue.put((player, None, exception))

    def check_bot_decision_queue(self):
        """
        Polls the bot decision queue on the main thread every 50 ms.  When
        a completed decision is available, clears bot_thinking, executes
        or error-handles the decision, advances current_position and
        schedules the next call to decisions() after log_delay_ms.

        Reschedules itself regardless of whether a decision was ready.
        """
        try:
            player, decision, error = self.bot_decision_queue.get_nowait()
            self.bot_thinking = False

            if error:
                self.bot_error(player, error)
            else:
                self.execute_bot_decision(player, decision)

            self.update_ui()
            self.current_position = (self.current_position + 1) % self.player_count
            self.hhe_root.after(self.log_delay_ms, self.decisions)

        except Empty:
            pass

        self.hhe_root.after(50, self.check_bot_decision_queue)

    def bot_decision(self, player):
        """
        Triggers the bot player's bot model to make a decision for the
        current game state.

        Args:
            player (dict): The bot player dictionary.

        Returns:
            tuple: One of '("fold",)', '("call",)' or
                   '("raise", amount)'.
        """
        model = player["model"]
        opponents = [
            p["model"]
            for p in self.players
            if p.get("model") is not None
            and p["model"] is not model
            and p["status"] not in ("Folded", "OUT")
        ]
        to_call = max(0, self.current_bet - player["bet"])
        community_cards = self.get_community_cards()

        return model.decide(
            player_hand=player["cards"][0],
            community_cards=community_cards,
            opponents=opponents,
            pot=self.pot_size,
            to_call=to_call,
            balance=player["balance"],
            street=self.street,
        )

    def execute_bot_decision(self, player, decision):
        """
        Applies a bot's decision to the game state.

        Handles all three actions:

        - **fold**: sets status to 'Folded' and logs the action.
        - **call**: handles check (call_amount == 0), all-in call
          (call_amount >= balance) and normal call; logs and updates pot.
        - **raise**: enforces the minimum raise, caps at player balance,
          updates pot and current_bet, logs and resets other players through
          reset_after_raise().

        Args:
            player (dict): The bot player dictionary.
            decision (tuple): As returned by bot_decision().
        """
        action = decision[0]
        name = player["player"]

        if action == "fold":
            self.log_message(f"{name} folds.")
            self.modify_player(player, status="Folded")

        elif action == "call":
            call_amount = max(0, self.current_bet - player["bet"])
            if call_amount == 0:
                self.log_message(f"{name} checks.")
                self.modify_player(player, status="Decided")
            elif call_amount >= player["balance"]:
                all_in = player["balance"]
                self.modify_player(player, change_balance=-all_in)
                self.modify_player(player, bet=player["bet"] + all_in)
                self.pot_size += all_in
                self.log_message(f"{name} calls £{all_in} (ALL-IN).")
                self.modify_player(player, status="All-in")
            else:
                self.modify_player(player, change_balance=-call_amount)
                self.modify_player(player, bet=player["bet"] + call_amount)
                self.pot_size += call_amount
                self.log_message(f"{name} calls £{call_amount}.")
                self.modify_player(player, status="Decided")

        elif action == "raise":
            raise_amount = decision[1] if len(decision) > 1 else self.current_bet * 2
            min_raise = max(
                self.current_bet - player["bet"] + self.big_blind_value,
                self.big_blind_value,
            )
            raise_amount = max(raise_amount, min_raise)
            raise_amount = min(raise_amount, player["balance"])

            self.modify_player(player, change_balance=-raise_amount)
            self.modify_player(player, bet=player["bet"] + raise_amount)
            self.pot_size += raise_amount
            self.current_bet = player["bet"]

            self.log_message(f"{name} raises to £{self.current_bet}.")

            # Mark as All-in if they committed their entire stack.
            if player["balance"] == 0:
                self.modify_player(player, status="All-in")
            else:
                self.modify_player(player, status="Decided")

            self.reset_after_raise(except_player=player)

    def is_betting_complete(self):
        active = [p for p in self.players if p["status"] not in ("Folded", "OUT")]
        if len(active) < 2:
            return True
        for player in active:
            if player["status"] == "Waiting":
                return False
            if player["status"] == "All-in":
                continue
            if player["bet"] < self.current_bet and player["balance"] > 0:
                return False
        return True

    def reset_after_raise(self, except_player):
        """
        Resets all active players (except the raiser) that are not 'All-in'
        to 'Waiting' so they must act again after a raise. Sets action_position
        to the player immediately after the raiser.

        Args:
            except_player (dict): The player who made the raise.
        """
        raiser_position = except_player["position"] - 1
        self.action_position = (raiser_position + 1) % self.player_count
        for player in self.players:
            if player is except_player:
                continue
            if player["status"] not in ("Folded", "OUT", "All-in"):
                player["status"] = "Waiting"

    def bot_error(self, player, error):
        """
        Handles a bot decision error. Displays a messagebox,
        logs the event and marks the bot as 'OUT'.

        Args:
            player (dict): The bot player that caused the error.
            error (Exception): The exception that was raised.
        """
        try:
            messagebox.showerror(
                "Bot Error",
                f"Error with {player['player']}:\n\n{error}\n\nBot will fold.",
            )
        except Exception:
            print(f"Bot error ({player['player']}): {error}")
        self.log_message(
            f"{player['player']} encountered an error and has been folded."
        )
        self.modify_player(player, status="OUT")

    def get_community_cards(self):
        """
        Returns the community cards visible on the current street as a list
        of standard string card representations.

        Returns:
            list[str]: Community cards for the current street.
                       Empty list for preflop; 3 cards for flop;
                       4 for turn; 5 for river/showdown.
        """
        if self.street == "preflop":
            return []
        if self.street == "flop":
            return list(self.flop[0]) if self.flop else []
        if self.street == "turn":
            return list(self.flop[0] or []) + list(self.turn[0] or [])
        if self.street in ("river", "showdown"):
            return list(self.board[0]) if self.board else []
        return []

    def next_street(self):
        """
        Advances to the next street in the street sequence (preflop ->
        flop -> turn -> river -> showdown).

        For preflop, preserves blind 'Decided' statuses and sets action
        to start after the big blind. For all post-flop streets, resets
        all active players to 'Waiting', clears per-street bets and
        sets action to start left of the dealer.

        Calls showdown() at the showdown street, otherwise calls
        decisions() to begin the betting loop.
        """
        if self.current_street_index >= len(self.street_sequence):
            return

        self.street = self.street_sequence[self.current_street_index]
        self.current_street_index += 1

        if self.street == "preflop":
            for player in self.players:
                if player["status"] not in ("Folded", "OUT", "Decided", "All-in"):
                    player["status"] = "Waiting"
            self.current_position = (self.initial_position + 3) % self.player_count
            self.action_position = self.current_position

        else:
            for player in self.players:
                # Reset to Waiting only if they can still act this street.
                if player["status"] not in ("Folded", "OUT", "All-in"):
                    player["status"] = "Waiting"
            self.current_bet = 0
            for player in self.players:
                if player["status"] not in ("Folded", "OUT"):
                    player["bet"] = 0

            for attempt in range(self.player_count):
                index = (self.initial_position + 1 + attempt) % self.player_count
                if self.players[index]["status"] != "OUT":
                    self.current_position = index
                    break
            self.action_position = self.current_position

        self.update_ui()

        if self.street == "showdown":
            self.showdown()
        else:
            self.decisions()

    def advance_street(self):
        """
        Called when all players have acted on the current street. Logs
        the street completion, checks for a single remaining active
        player (awarding the pot immediately without a showdown) and
        advances to the next street otherwise.
        """
        self.log_message(f"{self.street.capitalize()} betting complete.")

        active = [p for p in self.players if p["status"] not in ("Folded", "OUT")]

        if len(active) == 1:
            winner = active[0]
            if winner["is_bot"]:
                self.log_message(f"{winner['player']} wins by default.")
                self.end_round(loss=True)
            else:
                self.log_message("You win by default!")
                self.end_round(win=True)
            return

        self.next_street()

    def showdown(self):
        """
        Evaluates all remaining active players' hands against the full
        board using the treys evaluator then determines the winner(s),
        logs each player's hand and the outcome and schedules end_round()
        after the log queue has finished rendering.

        Handles split pots when multiple players tie.
        """
        self.log_message("— SHOWDOWN —", round_start=True)
        self.log_message("Board cards: " + " ".join(self.board[1]))
        self.update_ui()

        active = [p for p in self.players if p["status"] not in ("Folded", "OUT")]

        if not active:
            self.log_message("Error: no active players at showdown.")
            self.end_round(tie=True)
            return

        if len(active) == 1:
            winner = active[0]
            self.log_message(f"{winner['player']} wins (last remaining player).")
            self.end_round(
                loss=True if winner["is_bot"] else False,
                win=False if winner["is_bot"] else True,
            )
            return

        player_hands = []
        for player in active:
            if not player["cards"] or len(player["cards"][0]) < 2:
                continue
            try:
                score = self.deck.evaluator.evaluate(
                    [self.deck.str_to_treys(c) for c in player["cards"][0]],
                    [self.deck.str_to_treys(c) for c in self.board[0]],
                )
                rank_class = self.deck.evaluator.get_rank_class(score)
                hand_name = self.deck.evaluator.class_to_string(rank_class)
                player_hands.append(
                    {
                        "player": player,
                        "score": score,
                        "hand_name": hand_name,
                    }
                )
                self.log_message(
                    f"{player['player']}:  "
                    f"{' '.join(player['cards'][1])}  —  {hand_name}"
                )
            except Exception as exception:
                self.log_message(
                    f"Error evaluating {player['player']}'s hand: {exception}"
                )

        if not player_hands:
            self.log_message("Error: could not evaluate any hands.")
            self.end_round(tie=True)
            return

        player_hands.sort(key=lambda x: x["score"])
        best_score = player_hands[0]["score"]
        winners = [ph for ph in player_hands if ph["score"] == best_score]
        delay = self.log_delay_ms * (len(self.log_queue) + 2)

        if len(winners) > 1:
            names = ", ".join(w["player"]["player"] for w in winners)
            human_won = any(not w["player"]["is_bot"] for w in winners)
            self.log_message(f"Split pot between {len(winners)} players: {names}.")
            if human_won:
                self.hhe_root.after(
                    delay,
                    lambda: self.end_round(
                        win=True, split_pot=True, split_count=len(winners)
                    ),
                )
            else:
                self.hhe_root.after(delay, lambda: self.end_round(loss=True))
        else:
            winner = winners[0]["player"]
            self.log_message(f"{winner['player']} wins with {winners[0]['hand_name']}!")
            if winner["is_bot"]:
                winner["balance"] += self.pot_size // max(1, len(winners))

                self.hhe_root.after(delay, lambda: self.end_round(loss=True))
            else:
                self.hhe_root.after(delay, lambda: self.end_round(win=True))

    def update_user_poker_data(self):
        """
        Reads the player's in-round action log and updates
        their poker statistics in the database. Derives VPIP, PFR and
        faced-raise flags from actions_logged and then calls
        update_hand_statistics and resolve_player_actions.
        """
        for player in self.players:
            if not player["is_bot"] and player["user_id"]:
                model = player.get("model")

                if model and self.actions_logged:
                    try:
                        hand_notation = cards_to_notation(player["cards"][0])
                    except Exception:
                        hand_notation = None

                    for action_log in self.actions_logged:
                        if action_log["street"] == "preflop" and hand_notation:
                            model.update_range_from_action(
                                action_log["action"],
                                hand_notation,
                            )

                voluntarily_entered = False
                preflop_raised = False
                faced_raise = False
                total_bet = 0

                for al in self.actions_logged:
                    if al["street"] == "preflop":
                        if al["action"] in ("call", "raise"):
                            voluntarily_entered = True
                        if al["action"] == "raise":
                            preflop_raised = True
                    total_bet += al["bet_size"]
                    if al["action"] == "fold":
                        faced_raise = True

                final_action = (
                    self.actions_logged[-1]["action"] if self.actions_logged else "fold"
                )

                self.dbm.update_hand_statistics(
                    user_id=player["user_id"],
                    action=final_action,
                    bet_size=total_bet,
                    voluntarily_entered=voluntarily_entered,
                    preflop_raised=preflop_raised,
                    faced_raise=faced_raise,
                )
                self.dbm.resolve_player_actions(
                    player["user_id"], self.current_round_number
                )
                break

    def end_round(
        self, *, win=False, loss=False, tie=False, split_pot=False, split_count=1
    ):
        human_index = linear_search(self.players, "is_bot", False)
        human = self.players[human_index] if human_index != -1 else None
        if not human:
            return

        if win:
            if split_pot and split_count > 1:
                winnings = self.pot_size // split_count
                human["balance"] += winnings
                self.log_message(f"You split the pot and won £{winnings}!", is_win=True)
            else:
                human["balance"] += self.pot_size
                self.log_message(
                    f"Congratulations! You won £{self.pot_size}!", is_win=True
                )
        elif loss:
            self.log_message(
                "You lost this round. Better luck next time.", is_loss=True
            )
        elif tie:
            self.log_message("It's a tie!", tie=True)

        if not self.tournament_mode:
            self.dbm.modify_user_balance(self.user_data["username"], human["balance"])

        if getattr(self, "balance_label", None) and self.balance_label.winfo_exists():
            self.balance_label.config(text=f"Balance: £{human['balance']}")

        self.log_message(f"Your balance: £{human['balance']}.")

        self.update_user_poker_data()

        self.current_round_number += 1
        self.actions_logged = []

        if self.tournament_mode and self.tournament:
            result = self.tournament.advance_round(human_won_round=win)
            self.log_message(result["message"], is_tournament=True)

            if result["tournament_over"]:
                delay = self.log_delay_ms * (len(self.log_queue) + 2)
                self.hhe_root.after(
                    delay,
                    lambda r=result: self.finish_tournament(r),
                )
                return

            # Update blinds label for next round.
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind

            if getattr(self, "blinds_label", None) and self.blinds_label.winfo_exists():
                self.blinds_label.config(
                    text=f"Blinds: £{self.small_blind_value} / £{self.big_blind_value}"
                )

        # Schedule teardown after log queue drains.
        delay = self.log_delay_ms * (len(self.log_queue) + 1)
        self.hhe_root.after(delay, self.finish_end_round)

    def finish_tournament(self, result):
        """
        Called once a tournament has fully concluded.
        Displays a summary dialog and returns to the main menu.

        Always attempts to update the player's personal best for consecutive
        rounds survived, regardless of whether the tournament was won.

        Args:
            result (dict): The result dict returned by
                           TournamentManager.advance_round() when
                           tournament_over is True.
        """
        message = (
            "Tournament Victory!" if result["tournament_won"] else "Tournament Over"
        )

        self.dbm.update_tournament_best(
            self.user_data["user_id"],
            self.tournament.rounds_survived,
        )

        messagebox.showinfo(message, result["message"])
        self.return_to_menu()

    def finish_end_round(self):
        """
        Completes round after the log queue has finished rendering.
        Resets the current-bet label, eliminates bots with
        zero chips, marks the human player as 'OUT' if they have no chips,
        checks for game-over conditions, increments the round display
        number and re-enables the Start Round button.
        """
        self.current_bet = 0
        if (
            getattr(self, "current_bet_label", None)
            and self.current_bet_label.winfo_exists()
        ):
            self.current_bet_label.config(text="Raise Amount: £0")

        for player in self.players:
            if player["is_bot"] and player["balance"] <= 0:
                player["status"] = "OUT"
                self.log_message(f"{player['player']} has been eliminated.")

        human_index = linear_search(self.players, "is_bot", False)
        human = self.players[human_index] if human_index != -1 else None

        if human and human["balance"] <= 0:
            human["status"] = "OUT"

        if self.check_game_over():
            return

        self.round_active = False
        self.round_number += 1

        if getattr(self, "start_button", None) and self.start_button.winfo_exists():
            self.start_button.config(text=f"Start Round {self.round_number}")

        self.update_ui()

    def check_game_over(self):
        """
        Checks whether the game has ended. The game ends if the human
        player's status is 'OUT' (loss) or if all bots are 'OUT'
        (victory).

        When balance reaches zero, a message is shown and the player is
        returned to the main menu (no account termination).

        Returns:
            bool: True if the game is over and the window is being
                  closed; False if the game should continue.
        """
        human_index = linear_search(self.players, "is_bot", False)
        human = self.players[human_index] if human_index != -1 else None

        if human and human["status"] == "OUT":
            messagebox.showinfo(
                "Game Over",
                "Your chip balance has reached £0.  "
                "You will be returned to the main menu.",
            )
            self.return_to_menu()
            return True

        active_bots = [p for p in self.players if p["is_bot"] and p["status"] != "OUT"]
        if len(active_bots) == 0:
            messagebox.showinfo(
                "Victory!",
                "Congratulations! You have eliminated all opponents "
                "and won the game!",
            )
            self.return_to_menu()
            return True

        return False

    def fold(self):
        """
        Handles the human player choosing to fold. Sets their status to
        'Folded', logs the action to the database, advances
        current_position and continues the decision loop.
        """
        for player in self.players:
            if not player["is_bot"]:
                self.log_message(f"{player['player']} folds.")
                self.modify_player(player, status="Folded")
                self.player_turn = False
                self.log_player_action_to_db("fold", 0)
                self.current_position = (self.current_position + 1) % self.player_count
                self.update_ui()
                self.decisions()
                break

    def call(self):
        """
        Handles the human player choosing to call (or check).

        Determines the call amount and handles three cases:
        - Call amount is zero -> check.
        - Call amount >= balance -> all-in call for exact balance.
        - Normal call -> deduct call_amount, update pot.

        Logs the action to the database, advances current_position and
        continues the decision loop.
        """
        for player in self.players:
            if not player["is_bot"]:
                call_amount = max(0, self.current_bet - player["bet"])

                if call_amount == 0:
                    self.log_message(f"{player['player']} checks.")
                    action, bet_size = "check", 0
                    self.modify_player(player, status="Decided")

                elif call_amount >= player["balance"]:
                    all_in = player["balance"]
                    self.modify_player(player, change_balance=-all_in)
                    self.modify_player(player, bet=player["bet"] + all_in)
                    self.pot_size += all_in
                    self.log_message(f"{player['player']} calls £{all_in} (ALL-IN).")
                    action, bet_size = "call", all_in
                    self.modify_player(player, status="All-in")

                else:
                    self.modify_player(player, change_balance=-call_amount)
                    self.modify_player(player, bet=player["bet"] + call_amount)
                    self.pot_size += call_amount
                    self.log_message(f"{player['player']} calls £{call_amount}.")
                    action, bet_size = "call", call_amount
                    self.modify_player(player, status="Decided")

                self.player_turn = False
                self.log_player_action_to_db(action, bet_size)
                self.current_position = (self.current_position + 1) % self.player_count
                self.update_ui()
                self.decisions()
                break

    def raise_bet(self):
        """
        Handles the human player choosing to raise.

        Validates the entered amount against the minimum raise and the
        player's available balance. Executes the raise, resets other
        players through reset_after_raise(), logs the action to the database,
        and continues the decision loop.
        """
        try:
            raise_amount = int(self.bet_var.get())
        except ValueError:
            messagebox.showerror("Invalid Raise", "Please enter a valid number.")
            return

        if raise_amount <= 0:
            messagebox.showerror("Invalid Raise", "Raise must be greater than 0.")
            return

        for player in self.players:
            if not player["is_bot"]:

                call_amount = max(0, self.current_bet - player["bet"])
                min_raise = call_amount + self.big_blind_value

                if raise_amount < min_raise:
                    messagebox.showerror(
                        "Invalid Raise",
                        f"The minimum raise is £{min_raise}.",
                    )
                    return

                if raise_amount > player["balance"]:
                    raise_amount = player["balance"]

                # Apply raise
                self.modify_player(player, change_balance=-raise_amount)
                self.modify_player(player, bet=player["bet"] + raise_amount)

                self.pot_size += raise_amount
                self.current_bet = max(p["bet"] for p in self.players)

                if player["balance"] == 0:
                    self.modify_player(player, status="All-in")
                else:
                    self.modify_player(player, status="Decided")

                self.log_message(f"{player['player']} raises to £{self.current_bet}.")
                self.log_player_action_to_db("raise", raise_amount)

                self.reset_after_raise(except_player=player)

                self.current_position = (self.current_position + 1) % self.player_count
                self.player_turn = False

                self.update_ui()
                self.decisions()
                break

    def return_to_menu(self, is_error=False, error=None):
        """
        Destroys the game window and returns the user to the appropriate
        interface: AdminInterface for administrators, CasinoInterface
        for regular users. Optionally shows an error dialog
        before navigating.

        Args:
            is_error (bool): If True, display an error message first.
            error (Exception or None): The error to show if is_error is
                                       True.
        """
        if is_error:
            messagebox.showerror("Error", f"{error}\n\nExiting game.")
        self.hhe_root.destroy()

        CasinoInterface(
            administrator=True if self.user_data.get("administrator") else False,
            user_data=self.user_data,
        )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Entry point
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == "__main__":
    AdminInterface() if "--admin" in sys.argv else CasinoInterface(False)
