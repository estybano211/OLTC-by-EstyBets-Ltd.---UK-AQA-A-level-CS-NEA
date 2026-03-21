# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# one_more_time_casino.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# This is a compilation of 15 separate programs:
# 1. database_management_and_logging_V6.py ~ lines
# 2. gui_helpers_V6.py ~ lines
# 3. search_sort_algorithms_V6.py ~ lines
# 4. encryption_software_V6.py ~ lines
# 5. check_systems_V6.py ~ lines
# 6. admin_interface_V6.py ~ lines
# 7. admin_console_V6.py ~ lines
# 8. terms_and_conditions_V6.py ~ lines
# 9. user_interface_V6.py ~ lines
# 10. casino_interface_V6.py ~ lines
# 11. game_rules_V6.py ~ lines
# 12. deck_management_V6.py ~ lines
# 13. whitejoe_V6.py ~ lines
# 14. poker_player_management_V6.py ~ lines
# 15. harrogate_hold_em_V6.py ~ lines

import sys
import os
import sqlite3
import pandas as pd
import csv
import json
from time import time, sleep
from datetime import datetime
import logging
from queue import Queue, Empty
from threading import Thread, Event
from typing import cast
from tkinter import (
    BOTH,
    BOTTOM,
    BooleanVar,
    Button,
    Canvas,
    Checkbutton,
    DISABLED,
    END,
    Entry,
    Frame,
    filedialog,
    font,
    HORIZONTAL,
    IntVar,
    Label,
    messagebox,
    NORMAL,
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
# database_management_and_logging_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Database file paths
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "OMTC_database.db")


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes custom log messages directly into the 'db_logs'
    table. It uses a queue-based worker thread to prevent database locking issues
    during concurrent operations. All log entries are processed asynchronously
    to avoid blocking the main application thread.
    """

    def __init__(self):
        """
        Initialises the database log handler with a queue and worker thread.
        Creates a daemon thread that continuously processes log entries from
        the queue and writes them to the database one at a time.
        """
        super().__init__()

        self.DB_FILE = DB_FILE

        self.queue = Queue()

        self.stop_event = Event()

        self.worker_thread = Thread(target=self.processor, daemon=True)

        self.worker_thread.start()

    def emit(self, record: logging.LogRecord):
        """
        Captures a log record, formats it, and adds it to the processing queue.
        Then extracts the log level and current timestamp, then queues the entry
        to write to the database. If an error occurs during emit, it is then
        handled to prevent program crashes.

        Args:
            record (logging.LogRecord): The log record object containing the
                                        custom log message and metadata.
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
        Worker thread that processes the queue and writes logs to the database
        one at a time to avoid locking issues. Runs continuously until the
        stop_event is set to prevent the thread from hanging indefinitely.
        """
        while not self.stop_event.is_set():
            try:
                # Wait for a log entry (timeout prevents thread from hanging forever).
                timestamp, level, log_entry = self.queue.get(timeout=1)

                with sqlite3.connect(self.DB_FILE, timeout=5) as conn:
                    conn.execute(
                        """
                        INSERT INTO db_logs(timestamp, level, log_entry)
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
        Stops the worker thread and closes the handler. Sets the stop event to
        signal the worker thread to exit, then waits for it to finish before
        calling the parent class's close method.
        """
        self.stop_event.set()
        self.worker_thread.join()
        super().close()


# Create a named logger for the database module.
database_logger = logging.getLogger("omtc_db")

database_logger.setLevel(logging.DEBUG)

if not database_logger.handlers:
    db_handler = DatabaseLogHandler()

    db_handler.setLevel(logging.DEBUG)

    db_formatter = logging.Formatter("%(message)s")

    db_handler.setFormatter(db_formatter)
    database_logger.addHandler(db_handler)


class AdminLogHandler(logging.Handler):
    """
    Custom logging handler that writes log messages directly into the
    'admin_logs' table. Uses a queue-based worker thread to prevent database
    locking issues during concurrent operations. All admin action entries are
    processed asynchronously to avoid blocking the main application thread.
    """

    def __init__(self):
        """
        Initialises the admin log handler with a queue and worker thread.
        Creates a daemon thread that continuously processes admin log entries
        from the queue and writes them to the database one at a time.
        """
        super().__init__()

        self.DB_FILE = DB_FILE

        self.queue = Queue()

        self.stop_event = Event()

        self.worker_thread = Thread(target=self.processor, daemon=True)

        self.worker_thread.start()

    def emit(self, record: logging.LogRecord):
        """
        Captures an admin log record, formats it, and adds it to the processing
        queue. Extracts the log level and current timestamp, then queues the
        entry for database insertion. If an error occurs during emit, it is
        handled gracefully to prevent program crashes.

        Args:
            record (logging.LogRecord): The log record object containing the
                                        admin action message and metadata.
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
        Worker thread that processes the queue and writes admin logs to the
        database one at a time. Runs continuously until the stop_event is set
        to prevent the thread from hanging indefinitely.
        """
        while not self.stop_event.is_set():
            try:
                timestamp, level, log_entry = self.queue.get(timeout=1)

                with sqlite3.connect(self.DB_FILE, timeout=5) as conn:
                    conn.execute(
                        """
                        INSERT INTO admin_logs(timestamp, level, log_entry)
                        VALUES (?, ?, ?)""",
                        (timestamp, level, log_entry),
                    )
                    conn.commit()

                self.queue.task_done()

            except Exception:
                pass

    def close(self):
        """
        Stops the worker thread and closes the handler. Sets the stop event to
        signal the worker thread to exit, then waits for it to finish before
        calling the parent class's close method.
        """
        self.stop_event.set()
        self.worker_thread.join()
        super().close()


# Create a named logger for admin actions.
admin_logger = logging.getLogger("omtc_admin")

admin_logger.setLevel(logging.DEBUG)

if not admin_logger.handlers:
    admin_handler = AdminLogHandler()
    admin_handler.setLevel(logging.DEBUG)

    admin_formatter = logging.Formatter("%(message)s")
    admin_handler.setFormatter(admin_formatter)

    admin_logger.addHandler(admin_handler)


class DatabaseManagement:
    """
    Handles all database creation, connection, and data operations.
    Manages user accounts, game statistics, logging tables, and
    provides methods for querying, updating, and maintaining the SQLite
    database.
    """

    def __init__(self):
        """
        Initialises the DatabaseManagement class with the database file path.
        """
        self.DB_FILE = DB_FILE

    def check_database_exists(self):
        """
        Checks if the database file exists in the same directory as the
        program. Constructs the full database path and verifies file existence.

        Returns:
            bool: True if the database file exists, False otherwise.
        """
        return os.path.exists(self.DB_FILE)

    # SQL Database Schema.
    # Each dictionary value is a CREATE TABLE statement run during database creation.
    SCHEMA = {
        # Logs for database access and amendments.
        "db_logs": """
        CREATE TABLE IF NOT EXISTS db_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            log_entry TEXT
        )  
        """,
        # Logs for administrative actions.
        "admin_logs": """
        CREATE TABLE IF NOT EXISTS admin_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT NOT NULL,
            log_entry TEXT
        )
        """,
        # Users account table.
        "users": """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            registered INTEGER,
            balance REAL DEFAULT 10000 CHECK (balance >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        # Poker data per user.
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
            gauntlet_max_rounds INTEGER DEFAULT 0,
            endless_high_score INTEGER DEFAULT 0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """,
        # Logs of user poker actions during hands.
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
        Establishes a connection to the SQLite database. Enables row factory
        for dictionary-like row access and enforces foreign key constraints.

        Returns:
            sqlite3.Connection: Database connection object with Row factory and
                                foreign keys enabled.
        """
        conn = sqlite3.connect(DB_FILE)

        conn.row_factory = sqlite3.Row

        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def create_database(self):
        """
        Creates all tables defined in the SCHEMA dictionary if they do not
        already exist. Iterates through each table definition, executes the
        CREATE TABLE statement, then creates the default administrator account.
        """
        with self.connect() as conn:
            try:
                for table, table in self.SCHEMA.items():
                    conn.execute(table)

                    database_logger.info(f"Table: '{table}' created.")

                conn.commit()

                database_logger.info(f"File: '{DB_FILE}' created.")

                self.admin_account()

                database_logger.info("Administrator account added to 'users' table.")

            except sqlite3.Error as error:
                database_logger.exception(f"'create_database' error. {error}")

    def admin_account(self):
        """
        Ensures that a default Administrator account exists in the database.
        Creates the account with a predefined password if it does not already
        exist.
        """
        admin_password = "Password1"

        hashed_password = hash_function(admin_password)

        with self.connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    SELECT 1 FROM users
                    WHERE username = ?
                    """,
                    ("Administrator",),
                )

                if cursor.fetchone() is None:
                    conn.execute(
                        """
                        INSERT INTO users
                        (username, password_hash, registered, balance) 
                        VALUES (?, ?, ?, ?)
                        """,
                        ("Administrator", (hashed_password), 1, 0.0),
                    )

                    database_logger.info("Administrator account created.")

            except sqlite3.Error as error:
                database_logger.exception(f"'admin_account' error. {error}")

    def admin_logged_in(self):
        """
        Creates a log entry in the admin_logs table recording that the
        administrator has successfully logged in.
        """
        admin_logger.info("Administrator logged in.")

    def admin_accessed_system(self, system):
        """
        Creates a log entry recording when the administrator accesses a
        specific system.

        Args:
            system (str): The name of the system accessed by the administrator.
        """
        admin_logger.info(f"Administrator accessed system: '{system}'.")

    def change_admin_password(self, new_password):
        """
        Changes the administrator password to a new hashed value. Hashes the
        new password before storing it in the database.

        Args:
            new_password (str): The new plaintext password to be hashed and
                                stored.
        """
        with self.connect() as conn:
            try:
                admin_logger.info("Request to change Admin Password.")

                database_logger.info("Request to change Administrator password.")

                password_hash = hash_function(new_password)

                conn.execute(
                    """
                    UPDATE users 
                    SET password_hash = ? 
                    WHERE username = ?
                    """,
                    (password_hash, "Administrator"),
                )

                database_logger.info("Administrator password changed.")

                admin_logger.info("Administrator password change request successful.")

            except sqlite3.Error as error:
                admin_logger.error("Administrator password change request failed.")

                database_logger.exception(f"'change_admin_password' error. {error}")

    def view_database(self, table):
        """
        Returns a DataFrame of all rows in the requested table for
        viewing.

        Args:
            table (str): The name of the database table to view.

        Returns:
            pd.DataFrame: DataFrame containing all rows from the specified
                          table, or an empty DataFrame on error or if no table
                          is provided.
        """
        if not table:
            database_logger.error("No table provided for admin_view_database().")
            return pd.DataFrame()

        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to view Table: '{table}'")

                database_logger.info(f"Attempting to read data from Table: '{table}'.")

                dataframe = pd.read_sql_query(f"SELECT * FROM {table}", conn)

                database_logger.info(f"Data from Table: '{table}' read successfully.")

                admin_logger.info("View table request successful.")

                return dataframe

            except sqlite3.Error as error:
                admin_logger.error("View table request failed.")

                database_logger.exception(f"'view_database' error. {error}")
                return pd.DataFrame()

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
        Updates one or more fields on a user record by delegating to the
        relevant individual change methods for each non-None argument. Fields
        that are passed as None are left unchanged.

        Args:
            user_id (int): The user ID of the record to modify.
            new_username (str, optional): New username to assign.
            new_password (str, optional): New plaintext password and will be
                                          hashed before storage.
            new_account_type (int, optional): New registered status (0 or 1).
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
        Changes a user's username to the given value.

        Args:
            user_id (int): The user ID whose username will be changed.
            new_username (str): The new username to assign.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to change User ID: '{user_id}' username.")

                database_logger.info(
                    f"Request to change User ID: '{user_id}' username."
                )

                conn.execute(
                    """
                    UPDATE users
                    SET username = ?
                    WHERE user_id = ?
                    """,
                    (new_username, user_id),
                )

                admin_logger.info("Change username request successful.")

                database_logger.info("User username changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change username request failed.")

                database_logger.exception(f"'change_user_username' error. {error}")

    def change_user_password(self, user_id, new_password):
        """
        Changes a user's password to a new hashed value. Hashes the new
        password before storing it in the database.

        Args:
            user_id (int): The user ID whose password will be changed.
            new_password (str): The new plaintext password to be hashed and
                                stored.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to change User: '{user_id}' password.")

                database_logger.info(f"Request to change User: '{user_id}' password.")

                password_hash = hash_function(new_password)

                conn.execute(
                    """
                    UPDATE users
                    SET password_hash = ?
                    WHERE user_id = ?
                    """,
                    (password_hash, user_id),
                )

                admin_logger.info("Change user password request successful.")

                database_logger.info("User password changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user password request failed.")

                database_logger.exception(f"'change_user_password' error. {error}")

    def change_user_account_type(self, user_id, registered):
        """
        Changes a user's account type (registered status).

        Args:
            user_id (int): The user ID whose account type will be changed.
            registered (int): The new registered status (0 for guest,
                              1 for registered).
        """
        with self.connect() as conn:
            try:
                admin_logger.info(
                    f"Request to change User ID: '{user_id}' account type."
                )

                database_logger.info(
                    f"Request to change User ID: '{user_id}' account type."
                )

                conn.execute(
                    """
                    UPDATE users 
                    SET registered = ? 
                    WHERE user_id = ?
                    """,
                    (registered, user_id),
                )

                admin_logger.info("Change user account type request successful.")

                database_logger.info(f"User account type changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user account type request failed.")

                database_logger.exception(f"'change_user_account_type' error. {error}")

    def change_user_balance(self, user_id, new_balance):
        """
        Changes a user's account balance to the specified value.

        Args:
            user_id (int): The user ID whose balance will be changed.
            new_balance (float): The new balance to assign.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to change User ID: '{user_id}' balance.")

                database_logger.info(f"Request to change User ID: '{user_id}' balance.")

                conn.execute(
                    """
                    UPDATE users 
                    SET balance = ? 
                    WHERE user_id = ?
                    """,
                    (float(new_balance), user_id),
                )

                admin_logger.info("Change user balance request successful.")

                database_logger.info("User balance changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user balance request failed.")

                database_logger.exception(f"'change_user_balance' error. {error}")

    def delete_user_record(self, user_id):
        """
        Permanently deletes a user record from the users table by user ID.

        Args:
            user_id (int): The user ID to delete from the database.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to delete User ID: '{user_id}' record.")

                database_logger.info(f"Request to delete User ID: '{user_id}' record.")

                conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))

                admin_logger.info("Delete user record request successful.")

                database_logger.info("User record deleted.")

            except sqlite3.Error as error:
                admin_logger.error("Delete user record request failed.")

                database_logger.exception(f"'delete_user_record' error. {error}")

    def fetch_user_full_record(self, *, user_id=None, username=None):
        """
        Fetches the complete user record for a given user_id or username.
        Returns all columns from the users table as a dictionary.

        Args:
            user_id (int, optional): The user ID to search for.
            username (str, optional): The username to search for.

        Returns:
            dict: Dictionary containing all user fields, or None if the user
                  was not found or an error occurred.

        Raises:
            ValueError: If neither user_id nor username is provided.
        """
        if user_id is None and username is None:
            raise ValueError("Either user_id or username must be provided")

        with self.connect() as conn:
            try:
                if user_id is not None:
                    cursor = conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", (user_id,)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM users WHERE username = ?", (username,)
                    )

                row = cursor.fetchone()
                return dict(row) if row else None

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_full_record' error. {error}")
                return None

    def fetch_user_presence(self, username=None):
        """
        Checks whether a user with the given username exists in the database.

        Args:
            username (str, optional): The username to search for.

        Returns:
            dict: A dictionary with a single key 'found' (bool), True if the
                  user exists, False otherwise.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Searching for User: '{username}'.")

                cursor = conn.execute(
                    """
                    SELECT 1 
                    FROM users 
                    WHERE username = ?
                    """,
                    (username,),
                )

                row = cursor.fetchone()
                found = row is not None

                if found:
                    database_logger.info(f"User '{username}' found.")
                else:
                    database_logger.info(f"User '{username}' not found.")

                return {"found": found}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_presence' error. {error}")
                return {"found": False}

    def sign_in_user(self, username, password, registered):
        """
        Registers a new user in the database with a hashed password, registered
        status, and an initial balance of £10,000. Guest accounts may be created
        with a None password.

        Args:
            username (str): The username for the new account (must be unique).
            password (str or None): The plaintext password to hash and store.
                                    Pass None for guest accounts.
            registered (int): Registration status (0 for guest, 1 for
                               registered).

        Returns:
            str: The username of the created account.

        Raises:
            ValueError: If username is not a non-empty string.
            sqlite3.IntegrityError: If the username already exists.
            sqlite3.Error: For other database errors.
        """
        if not username or not isinstance(username, str):
            raise ValueError("'username' must be a non-empty string")

        if username.strip().lower() == "administrator":
            raise ValueError("The username 'Administrator' cannot be used.")

        password_hash = hash_function(password) if password else None

        INIT_BALANCE = 10000.0

        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Request to make an account for User: '{username}'."
                )

                conn.execute(
                    """
                    INSERT INTO users
                    (username, password_hash, registered, balance) 
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        username,
                        password_hash,
                        int(float(registered)),
                        float(INIT_BALANCE),
                    ),
                )

                database_logger.info(f"Created User: '{username}' record.")

                return username

            except sqlite3.IntegrityError:
                database_logger.warning(f"User: '{username}' record already exists.")
                raise

            except sqlite3.Error as error:
                database_logger.exception(f"'sign_in_user' error. {error}")
                raise

    def verify_user_password(self, username, password):
        """
        Verifies whether a provided plaintext password matches the stored hash
        for the given username.

        Args:
            username (str): The username whose password will be verified.
            password (str): The plaintext password to verify.

        Returns:
            dict: Dictionary with 'found' (bool) and 'verified' (bool) keys.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Request to search for User: '{username}' 'password_hash'."
                )

                cursor = conn.execute(
                    """
                    SELECT password_hash 
                    FROM users 
                    WHERE username = ?
                    """,
                    (username,),
                )

                row = cursor.fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'verify_user_password' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.info(f"'password_hash' for User: '{username}' not found.")
            return {"found": False, "verified": False}

        verified = verify_hash(row["password_hash"], password)

        if verified:
            database_logger.info("Password verification successful'.")
        else:
            database_logger.info("Failed password attempt.")

        return {"found": True, "verified": verified}

    def fetch_user_id(self, username):
        """
        Retrieves the user ID for the given username.

        Args:
            username (str): The username to look up.

        Returns:
            dict: Dictionary with 'found' (bool) and 'user_id' (int or None)
                  keys.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to fetch User: '{username}' user_id.")

                cursor = conn.execute(
                    """
                    SELECT user_id 
                    FROM users 
                    WHERE username = ?
                    """,
                    (username,),
                )
                row = cursor.fetchone()

                if row:
                    database_logger.info("User 'user_id' found.")
                    return {"found": True, "user_id": row["user_id"]}
                else:
                    database_logger.info("User 'user_id' not found.")
                    return {"found": False, "user_id": None}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_id' error. {error}")
                return {"found": False, "user_id": None}

    def fetch_username(self, user_id):
        """
        Retrieves the username for the given user ID.

        Args:
            user_id (int): The user ID to look up.

        Returns:
            dict: Dictionary with 'found' (bool) and 'username' (str or None)
                  keys.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to fetch User ID: '{user_id}' username.")

                cursor = conn.execute(
                    """
                    SELECT username 
                    FROM users 
                    WHERE user_id = ?
                    """,
                    (user_id,),
                )
                row = cursor.fetchone()

                if row:
                    database_logger.info("User 'username' found.")
                    return {"found": True, "username": row["username"]}
                else:
                    database_logger.info("User 'username' not found.")
                    return {"found": False, "username": None}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_username' error. {error}")
                return {"found": False, "username": None}

    def fetch_user_balance(self, username):
        """
        Retrieves the account balance for the given username.

        Args:
            username (str): The username whose balance will be retrieved.

        Returns:
            dict: Dictionary with 'found' (bool) and 'balance' (float) keys.
                  Balance defaults to 0.0 if the user is not found or an error
                  occurs.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to fetch User: '{username}' balance.")

                cursor = conn.execute(
                    """
                    SELECT balance 
                    FROM users 
                    WHERE username = ?
                    """,
                    (username,),
                )
                row = cursor.fetchone()

                if row:
                    database_logger.info("User 'balance' found.")
                    return {"found": True, "balance": float(row["balance"])}
                else:
                    database_logger.info("User 'balance' not found.")
                    return {"found": False, "balance": 0.0}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_balance' error. {error}")
                return {"found": False, "balance": 0.0}

    def modify_user_balance(self, username, new_balance):
        """
        Updates a user's account balance to the specified value.

        Args:
            username (str): The username whose balance will be modified.
            new_balance (float): The new balance to assign.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to modify User: '{username}' balance.")

                conn.execute(
                    """
                    UPDATE users 
                    SET balance = ? 
                    WHERE username = ?
                    """,
                    (float(new_balance), username),
                )

                database_logger.info("User balance modified.")
                return

            except sqlite3.Error as error:
                database_logger.exception(f"'modify_user_balance' error. {error}")

    def admin_password_check(self, password):
        """
        Verifies a provided password against the stored administrator password
        hash.

        Args:
            password (str): The plaintext password to verify.

        Returns:
            dict: Dictionary with 'found' (bool) and 'verified' (bool) keys.
        """
        with self.connect() as conn:
            try:
                database_logger.info("Request for Administrator password_hash.")

                cursor = conn.execute(
                    """
                    SELECT password_hash
                    FROM users 
                    WHERE username = ?
                    """,
                    ("Administrator",),
                )

                row = cursor.fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'admin_password_check' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.debug("'password_hash' for Administrator not found.")
            return {"found": False, "verified": False}

        verified = verify_hash(row["password_hash"], password)

        if verified:
            database_logger.info("Administrator password verification successful.")
        else:
            database_logger.info("Administrator password verification failed.")

        return {"found": True, "verified": verified}

    def check_user_poker_data_exists(self, user_id):
        """
        Checks whether a poker data record exists for the given user ID.

        Args:
            user_id (int): The user ID to check.

        Returns:
            bool: True if a record exists, False otherwise or on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Checking if poker data exists for User ID: '{user_id}'."
                )

                exists = conn.execute(
                    """
                    SELECT 1 FROM user_poker_data WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                database_logger.info(
                    f"Poker data existence for User: {'found' if exists else 'not found'}."
                )

                return exists is not None

            except sqlite3.Error as error:
                database_logger.exception(
                    f"'check_user_poker_data_exists' error. {error}"
                )
                return False

    def initialise_user_poker_data(self, user_id):
        """
        Creates a new poker data record for the given user with default values
        and a new base range chart. If a record already exists then no changes
        are made.

        Args:
            user_id (int): The user ID to initialise poker data for.

        Returns:
            bool: True if initialisation was successful or data already exists,
                  False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Initialising poker data for User ID: '{user_id}'."
                )

                exists = conn.execute(
                    """
                    SELECT 1 FROM user_poker_data WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if exists:
                    database_logger.info("User poker data already exists")
                    return True

                conn.execute(
                    """
                    INSERT INTO user_poker_data (user_id)
                    VALUES (?)
                    """,
                    (user_id,),
                )

                # Create a base range chart
                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET player_range = ?
                    WHERE user_id = ?
                    """,
                    (json.dumps(generate_range_chart()), user_id),
                )

                database_logger.info("User poker data initialised.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(
                    f"'initialise_user_poker_data' error. {error}"
                )
                return False

    def load_user_poker_data(self, user_id):
        """
        Loads the complete poker data record for a user.  Retrieves all stored
        statistics, calculates derived values (avg_bet_size), and normalises
        fold_to_raise and call_when_weak to a 0.0–1.0 range.

        Args:
            user_id (int): The user ID to load data for.

        Returns:
            dict: Dictionary containing all poker data fields plus derived
                  statistics (avg_bet_size), with player_range
                  deserialised from JSON. Returns None if the user is not found
                  or an error occurs.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Loading poker data for User ID: '{user_id}'.")

                # Get user data with poker statistics
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
                    database_logger.warning("User not found in poker data")
                    return None

                # Convert to dictionary
                record = dict(row)

                # Parse player_range JSON
                record["player_range"] = (
                    json.loads(record["player_range"])
                    if record.get("player_range")
                    else None
                )

                # Calculate derived statistics
                rounds = max(1, record["rounds_played"])
                record["avg_bet_size"] = record["total_bets"] / rounds

                # Normalise fold_to_raise and call_when_weak to 0.0-1.0
                # These are stored as counts, convert to frequencies
                total_pressure_situations = (
                    record["fold_to_raise"] + record["call_when_weak"]
                )
                if total_pressure_situations > 0:
                    record["fold_to_raise"] = (
                        record["fold_to_raise"] / total_pressure_situations
                    )
                    record["call_when_weak"] = (
                        record["call_when_weak"] / total_pressure_situations
                    )
                else:
                    # Default values if no data
                    record["fold_to_raise"] = 0.5
                    record["call_when_weak"] = 0.5

                database_logger.info(
                    f"Poker data for User ID: '{user_id}' loaded successfully."
                )

                return record

            except sqlite3.Error as error:
                database_logger.exception(f"'load_user_poker_data' error. {error}")
                return None
            except json.JSONDecodeError as error:
                database_logger.exception(f"'load_user_poker_data' error. {error}")
                return None

    def update_player_range(self, user_id, player_range):
        """
        Serialises and stores a player's range chart in the database, updating
        the last_updated timestamp.

        Args:
            user_id (int): The user ID whose range will be updated.
            player_range (dict): The range dictionary to store.

        Returns:
            bool: True if successful, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Updating player range for User ID: '{user_id}'.")

                range_json = json.dumps(player_range)

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET 
                        player_range = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (range_json, user_id),
                )

                database_logger.info("User player range updated.")

                return True

            except (sqlite3.Error, json.JSONDecodeError) as error:
                database_logger.exception(f"'update_player_range' error. {error}")
                return False

    def log_player_action(
        self, *, user_id, round_number, street, action, bet_size, pot_size
    ):
        """
        Logs a player action to the user_poker_actions table.

        Args:
            user_id (int): The user ID performing the action.
            round_number (int): The unique hand/round identifier.
            street (str): The current betting round ('preflop', 'flop',
                          'turn', 'river').
            action (str): The action taken ('fold', 'call', 'raise').
            bet_size (float): The amount bet or raised.
            pot_size (float): The total pot size at the time of the action.

        Returns:
            bool: True if successful, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Logging action for User ID: '{user_id}'.")

                conn.execute(
                    """
                    INSERT INTO user_poker_actions(
                        user_id,
                        round_number,
                        street,
                        action,
                        bet_size,
                        pot_size
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        round_number,
                        street,
                        action,
                        bet_size,
                        pot_size,
                    ),
                )

                database_logger.info("Action logged for User.")

                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'log_player_action' error. {error}")
                return False

    def resolve_player_actions(self, user_id, round_number):
        """
        Marks all actions for a specific round as resolved by setting the
        resolved flag to 1.

        Args:
            user_id (int): The user ID whose actions will be resolved.
            round_number (int): The round number to mark as resolved.

        Returns:
            bool: True if successful, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Resolving actions for User ID: '{user_id}'.")

                conn.execute(
                    """
                    UPDATE user_poker_actions
                    SET resolved = 1
                    WHERE user_id = ?
                    AND round_number = ?
                    """,
                    (user_id, round_number),
                )

                database_logger.info("User actions resolved.")

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
        Updates all aggregate poker statistics for a user after a hand
        completes. Increments counters and recalculates VPIP/PFR.

        Args:
            user_id (int): The user ID to update.
            action (str): The final action taken ('fold', 'call', 'raise').
            bet_size (float): The amount bet during the hand.
            voluntarily_entered (bool): Whether the player voluntarily put
                                        money in the pot (contributes to VPIP).
            preflop_raised (bool): Whether the player raised preflop
                                   (contributes to PFR).
            faced_raise (bool): Whether the player faced a raise during the
                                hand.

        Returns:
            bool: True if successful, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Updating hand statistics for User ID: '{user_id}'."
                )

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET
                        rounds_played = rounds_played + 1,
                        total_hands_played = total_hands_played + ?,
                        total_hands_raised = total_hands_raised + ?,
                        total_bets = total_bets + ?,
                        pot_size = pot_size + ?,
                        fold_to_raise = fold_to_raise + ?,
                        call_when_weak = call_when_weak + ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (
                        int(voluntarily_entered),  # VPIP counter
                        int(preflop_raised),  # PFR counter
                        bet_size,  # Total bets
                        int(faced_raise and action == "fold"),  # Fold to raise
                        int(faced_raise and action == "call"),  # Call when weak
                        user_id,
                    ),
                )

                # Recalculate VPIP and PFR percentages
                self.recalculate_frequencies(conn, user_id)

                database_logger.info("User hand statistics updated.")

                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_hand_statistics' error. {error}")
                return False

    def recalculate_frequencies(self, conn, user_id):
        """
        Recalculates and updates VPIP and PFR percentage values based on the
        current aggregate counters.

        Args:
            conn (sqlite3.Connection): An active database connection to use.
            user_id (int): The user ID whose frequencies will be recalculated.
        """
        try:
            database_logger.info(f"Recalculating frequencies for User ID: '{user_id}'.")

            row = conn.execute(
                """
                SELECT
                    rounds_played,
                    total_hands_played,
                    total_hands_raised
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
                """
                UPDATE user_poker_data
                SET vpip = ?, pfr = ?
                WHERE user_id = ?
                """,
                (vpip, pfr, user_id),
            )

            database_logger.info("User frequencies recalculated.")

        except sqlite3.Error as error:
            database_logger.exception(f"'recalculate_frequencies' error. {error}")

    def fetch_player_statistics(self, user_id):
        """
        Retrieves a summary poker statistics for a player.

        Args:
            user_id (int): The user ID to retrieve statistics for.

        Returns:
            dict: Dictionary of statistics, or None if the user is not found
                  or an error occurs.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Fetching player statistics for User ID: '{user_id}'."
                )

                row = conn.execute(
                    """
                    SELECT
                        user_id,
                        rounds_played,
                        vpip,
                        pfr,
                        total_bets,
                        fold_to_raise,
                        call_when_weak
                    FROM user_poker_data
                    WHERE user_id = ?
                """,
                    (user_id,),
                ).fetchone()

                if not row:
                    return None

                statistics = dict(row)

                # Calculate derived statistics
                rounds = max(1, statistics["rounds_played"])
                statistics["avg_bet_size"] = statistics["total_bets"] / rounds

                database_logger.info("User player statistics fetched.")

                return statistics

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_player_statistics' error. {error}")
                return None

    def fetch_all_players_data(self):
        """
        Retrieves poker data for all players who have played at least one
        round.

        Returns:
            list: A list of player data dictionaries ordered by rounds played
                  descending, or an empty list on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info("Fetching poker data for all players.")

                rows = conn.execute("""
                    SELECT
                        user_id,
                        rounds_played,
                        vpip,
                        pfr,
                        total_bets
                    FROM user_poker_data
                    WHERE rounds_played > 0
                    ORDER BY rounds_played DESC
                    """).fetchall()

                players = []
                for row in rows:
                    player = dict(row)
                    rounds = max(1, player["rounds_played"])
                    player["avg_bet_size"] = player["total_bets"] / rounds
                    players.append(player)

                database_logger.info(f"Fetched data for {len(players)} players.")

                return players

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_all_players_data' error. {error}")
                return []

    def export_to_csv(self, table, file_path):
        """
        Exports a database table to a CSV text file.
        This provides non-SQL table access - the data is written as
        comma-separated text with a header row.

        Args:
            table (str): The SQLite table to export.
            file_path (str): The path to the CSV text file.

        Returns:
            bool: True on success, False on error.
        """
        try:
            with self.connect() as conn:
                database_logger.info(
                    f"Exporting table '{table}' to a CSV text file at '{file_path}'."
                )

                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    database_logger.warning(f"Table '{table}' is empty.")
                    return False

                headers = list(rows[0].keys())  # Get column names from the first row

                with open(file_path, "w") as file:
                    writer = csv.writer(file)
                    writer.writerow(headers)
                    writer.writerows(rows)

                database_logger.info(
                    f"Successfully exported table '{table}' to a CSV text file at '{file_path}'."
                )
                return True

        except Exception as error:
            database_logger.exception(f"'export_to_csv' error. {error}")
            return False

    def import_from_csv(self, file_path):
        """
        Reads a CSV text file and returns its contents as a list of dictionaries.

        Args:
            file_path (str): The path to the CSV text file.

        Returns:
            list: A list of dictionaries representing the CSV rows.
        """
        records = []
        try:
            with open(file_path, "r") as file:
                headers = file.readline().strip().split(",")  # Read header line
                for line in file:
                    values = line.strip().split(",")
                    record = dict(zip(headers, values))
                    records.append(record)
            database_logger.info(
                f"Successfully imported data from CSV text file at '{file_path}'."
            )
        except Exception as error:
            database_logger.exception(f"'import_from_csv' error. {error}")
            return records

    def reset_player_statistics(self, user_id, keep_range=True):
        """
        Resets all poker statistics for a player to zero.

        Args:
            user_id (int): The user ID to reset.
            keep_range (bool): If True, the player_range is preserved.
                               Defaults to True.

        Returns:
            bool: True if successful, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Resetting player statistics for User ID: '{user_id}'. Keep range: {keep_range}"
                )

                if keep_range:
                    conn.execute(
                        """
                        UPDATE user_poker_data
                        SET
                            rounds_played = 0,
                            vpip = 0,
                            pfr = 0,
                            total_hands_played = 0,
                            total_hands_raised = 0,
                            total_bets = 0,
                            fold_to_raise = 0,
                            call_when_weak = 0,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        (user_id,),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE user_poker_data
                        SET
                            rounds_played = 0,
                            player_range = NULL,
                            vpip = 0,
                            pfr = 0,
                            total_hands_played = 0,
                            total_hands_raised = 0,
                            total_bets = 0,
                            fold_to_raise = 0,
                            call_when_weak = 0,
                            last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                        """,
                        (user_id,),
                    )

                database_logger.info("User statistics reset.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'reset_player_statistics' error. {error}")
                return False

    def fetch_special_mode_scores(self, user_id):
        """
        Retrieves the Gauntlet and Endless personal-best scores for a user.

        Args:
            user_id (int): The user ID to query.

        Returns:
            dict: Dictionary with keys 'gauntlet_max_rounds' (int) and
                'endless_high_score' (int), or None if the user is not
                found or an error occurs.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Fetching special-mode scores for User ID: '{user_id}'."
                )

                row = conn.execute(
                    """
                    SELECT gauntlet_max_rounds, endless_high_score
                    FROM   user_poker_data
                    WHERE  user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if not row:
                    database_logger.info(
                        f"No special-mode scores found for user_id {user_id}."
                    )
                    return None

                database_logger.info("User special-mode scores fetched.")

                return {
                    "gauntlet_max_rounds": int(row["gauntlet_max_rounds"] or 0),
                    "endless_high_score": int(row["endless_high_score"] or 0),
                }

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_special_mode_scores' error. {error}")
                return None

    def update_special_mode_score(self, user_id, column, new_score):
        """
        Updates a special-mode personal best only if 'new_score' exceeds
        the currently stored value. Uses a conditional UPDATE so the record
        is never downgraded (e.g. after a short run following a long one).

        Args:
            user_id  (int): The user ID to update.
            column   (str): Either 'gauntlet_max_rounds' or
                            'endless_high_score'.
            new_score (int): The candidate new personal best.

        Returns:
            bool: True if the update executed without error, False otherwise.

        Raises:
            ValueError: If 'column' is not one of the two allowed values.
        """
        with self.connect() as conn:
            try:
                conn.execute(
                    f"""
                    UPDATE user_poker_data
                    SET {column} = ?,
                    last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    AND {column} < ?
                    """,
                    (new_score, user_id, new_score),
                )
                database_logger.info(f"Updated {column} to {new_score}")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_special_mode_score' error. {error}")
                return False


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# gui_helpers_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def fetch_font_settings(root):
    """
    Creates and returns a dictionary of named tkinter Font objects for consistent
    styling across the project.

    Args:
        root: The root Tk window used to bind the font objects.

    Returns:
        dict: A dictionary mapping style names (e.g. 'heading', 'text') to
              tkinter Font instances.
    """
    styles = {
        "title": font.Font(
            root=root, family="Times New Roman", size=35, weight="bold", underline=True
        ),
        "heading": font.Font(
            root=root, family="Arial", size=28, weight="bold", underline=True
        ),
        "subheading": font.Font(root=root, family="Helvetica", size=24, weight="bold"),
        "text": font.Font(root=root, family="Verdana", size=20),
        "button": font.Font(root=root, family="Tahoma", size=18, weight="bold"),
        "terms_and_conditions": font.Font(
            root=root, family="Helvetica", size=20, weight="bold"
        ),
        "emphasis": font.Font(
            root=root, family="Georgia", size=12, weight="bold", slant="italic"
        ),
    }
    return styles


# Default delay for message logging in seconds
DELAY = 1.5


def clear_current_section(self):
    """
    Destroys the currently active section frame if one exists, and resets the
    reference to None.

    Args:
        self: The parent interface object that holds a 'current_section_frame'
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

    Args:
        self: The parent interface object that holds 'main_frame' and
              'current_section_frame' attributes.
        view_builder (callable): A function that accepts a Frame as its sole
                                 argument and populates it with widgets.
    """
    clear_current_section(self)

    self.current_section_frame = Frame(self.main_frame)
    self.current_section_frame.pack(expand=True, fill="both")

    view_builder(self.current_section_frame)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# search_sort_algorithms_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def linear_search(array, key, value):
    """
    Performs a linear search through a list of dictionaries.
    Checks every element from a starting index 0 until the target is found.
    Time complexity: O(n).

    Arg:
        array (list): A list of dictionaries to search.
        key (str): The dictionary key to inspect.
        value : The value to search for.

    Returns:
        int: Index of the first matching element, or -1 if not found.
    """
    for index in range(len(array)):
        if array[index].get(key) == value:
            return index
    return -1


def bubble_sort(array, key, reverse):
    """
    Sorts a list of dictionaries by a given key using bubble sort.
    Compares adjacent pairs and swaps if out of order.
    Time complexity: O(n^2)

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
        ):  # Last 'pass_num' elements are already sorted
            value_a = array[index].get(key)
            value_b = array[index + 1].get(key)
            if (reverse and value_a < value_b) or (
                not reverse and value_a > value_b
            ):  # Compare based on sort order
                array[index], array[index + 1] = array[index + 1], array[index]
                swapped = True
        if not swapped:  # No swaps means the array is already sorted
            break
    return array


def binary_search_by_id(array, target_id):
    """
    Binary search on a list of dictionaries sorted ascending by 'user_id'.
    Time complexity: O(log n). List must be sorted first.

    Args:
        array (list): List of dictionaries sorted by 'user_id' ascending.
        target_id (int): The user_id to find.

    Returns:
        int: Index of the matching element, or -1 if not found.
    """
    low, high = 0, len(array) - 1
    while low <= high:
        mid = (low + high) // 2
        mid_id = array[mid].get("user_id", -1)
        if mid_id == target_id:
            return mid  # Target founf
        elif mid_id < target_id:
            low = mid + 1  # Target is in the upper half.
        else:
            high = mid - 1  # Target is in the lower half.
    return -1


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# encryption_software_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Encryption_Software:
    """
    GUI tool for hybrid RSA/AES file encryption and decryption. Used by
    administrators to secure database files or other data.
    """

    def __init__(self):
        """
        Initialises the root window, applies GUI styles, logs the system access
        event via DatabaseManagement, sets the AES key placeholder to None, and
        starts the main interface.
        """
        self.enc_soft_root = Tk()
        self.enc_soft_root.title("One More Time Casino - Encryption Software")
        try:
            self.enc_soft_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.enc_soft_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.styles = fetch_font_settings(self.enc_soft_root)

        try:
            self.dbm = DatabaseManagement()
            self.dbm.admin_accessed_system("Encryption Software")
        except:
            # In case that this software is not used with the casino software.
            # However, it will still require 'gui_helpers_V6.py' to run, so it is not fully standalone.
            pass

        self.aes_key = None

        self.main_frame = Frame(self.enc_soft_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.create_main_interface)

        self.enc_soft_root.mainloop()

    def create_main_interface(self, frame):
        """
        Builds the main menu interface with buttons for all available
        operations: generating an RSA keypair, generating and encrypting an AES
        key, loading an encrypted AES key, encrypting a file, decrypting a
        file, and exiting.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Encryption Software", font=self.styles["heading"]).pack(
            pady=10
        )

        buttons = [
            ("Generate RSA Keypair", self.generate_rsa_keys),
            ("Generate & Encrypt AES Key", self.generate_encrypted_aes_key),
            ("Load Encrypted AES Key", self.load_rsa_aes_key),
            ("Encrypt File", self.encrypt_file),
            ("Decrypt File", self.decrypt_file),
            ("Exit", self.enc_soft_root.destroy),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=40, command=command
            ).pack(pady=5)

    def generate_rsa_keys(self):
        """
        Generates a 2048-bit RSA keypair and saves both the private and public
        keys as PEM files to a user-selected directory. Filenames include a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file paths, or an error message if generation or saving fails.
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
        RSA public key via PKCS1-OAEP, and saves the encrypted result as a
        binary file to a user-selected directory. The filename includes a
        timestamp in DD-Month-YYYY format. Displays a success message with the
        saved file path, or an error message on failure.
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
        key file, then decrypts the AES key using PKCS1-OAEP and stores it in
        memory as self.aes_key. The loaded key is used for subsequent encrypt
        and decrypt operations. Displays a success message on completion, or an
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
        extension appended. The file contains the nonce, authentication tag, and
        ciphertext concatenated in that order. Displays a warning if no AES key
        is loaded, a success message with the output path on completion, or an
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
        in EAX mode. Reads the nonce, authentication tag, and ciphertext from
        the file, verifies the authentication tag, and writes the decrypted
        plaintext to disk. The output path is the input path with the .enc
        extension removed, or with .dec appended if the file does not end in
        .enc. Displays a warning if no AES key is loaded, a success message
        with the output path on completion, or an error message if decryption
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
# check_systems_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PBKDF2_ITERATIONS = 200_000  # Iterations for password hashing. (Password-Based Key Derivation Function 2)
SALT_BYTES = 16  # Number of random bytes for salt


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

    # Generate a random salt
    salt = os.urandom(SALT_BYTES)

    # Derive the hash using PBKDF2-HMAC-SHA256
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    # Return the salt and hash joined by a '$' character
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(derived_key).decode()}"


def verify_hash(stored_string, input_string):
    """
    Verifies a plaintext string against a stored PBKDF2-HMAC-SHA256 hash.
    Uses a constant-time comparison to prevent timing attacks.

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
        # The stored hash isn't in the expected format
        return False

    salt = binascii.unhexlify(salt_hex)
    stored_hash = binascii.unhexlify(hash_hex)

    # Derive a hash using the same salt and parameters
    input_hash = hashlib.pbkdf2_hmac(
        "sha256", input_string.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )

    return hmac.compare_digest(input_hash, stored_hash)


def passwords_confirmation(frame, root):
    """
    Opens a modal Toplevel dialog prompting the user to enter and confirm a
    new password. The dialog cannot be closed via the window manager's close
    button; the user must submit or cancel explicitly.

    Args:
        frame: The parent widget used to position the Toplevel window.
        root: The root Tk window, used for font settings and blocking via
              wait_window().

    Returns:
        dict: A dictionary with two keys:
              - 'confirmed' (bool): True if the user submitted matching
                non-empty passwords, False otherwise.
              - 'password' (str or None): The confirmed password string, or
                None if the dialog was cancelled or passwords did not match.
    """
    styles = fetch_font_settings(root)

    # Default return state
    password = {"confirmed": False, "password": None}

    password_window = Toplevel(frame)
    password_window.title("Confirm Password")
    password_window.protocol("WM_DELETE_WINDOW", lambda: None)
    try:
        password_window.attributes("-zoomed", True)  # MacOS/Linux
    except Exception:
        pass
    try:
        password_window.state("zoomed")  # Windows
    except Exception:
        pass

    Label(password_window, text="Enter password:", font=styles["text"]).pack(pady=5)

    password_entry_1 = Entry(password_window, show="*", width=30, font=styles["text"])
    password_entry_1.pack(pady=5)

    Label(password_window, text="Confirm password:", font=styles["text"]).pack(pady=5)

    password_entry_2 = Entry(password_window, show="*", width=30, font=styles["text"])
    password_entry_2.pack(pady=5)

    def validate_passwords():
        """
        Validates that both password fields are non-empty and identical.
        On success, updates the shared password dict and closes the dialog.
        On failure, displays an error message inside the dialog.
        """
        password_1 = password_entry_1.get().strip()
        password_2 = password_entry_2.get().strip()

        if password_1 and password_1 == password_2:
            password["confirmed"] = True
            password["password"] = password_1
            password_window.destroy()
        else:
            # Show an error message if passwords do not match or are empty, then clear the entry fields for another attempt.
            messagebox.showerror(
                "Error",
                "Passwords do not match or are empty. Please try again.",
                parent=password_window,
            )

    def cancel_password():
        """
        Closes the password dialog without confirming, leaving the shared
        password dict in its default unconfirmed state.
        """
        password_window.destroy()

    button = Frame(password_window)
    button.pack(pady=10)

    Button(
        button, text="Submit", font=styles["button"], command=validate_passwords
    ).pack(side="left", padx=5)

    Button(button, text="Cancel", font=styles["button"], command=cancel_password).pack(
        side="left", padx=5
    )

    root.wait_window(password_window)

    return password


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# admin_interface_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Admin_Interface:
    """
    Provides the administrator login screen and top-level navigation interface,
    giving access to the Admin Console and Casino Interface.
    Automatically creates the database if it does not already exist.
    """

    def __init__(self):
        """
        Initialises the Admin Interface window and navigates to either the
        password check or the main admin menu depending on whether the
        administrator is already authenticated.
        """
        self.interface_root = Tk()
        self.interface_root.title("One More Time Casino - Administrator Interface")
        try:
            self.interface_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.interface_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.dbm = DatabaseManagement()
        self.DB_FILE = DB_FILE

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.styles = fetch_font_settings(self.interface_root)

        self.main_frame = Frame(self.interface_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.administrative_check)

        self.interface_root.mainloop()

    def administrative_check(self, frame):
        """
        Renders a password entry form for authentication.
        On a correct password, navigates to the main admin interface.
        On an incorrect password, displays an error and clears the entry field.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame, text="Enter Administrator Password:", font=self.styles["text"]
        ).pack(pady=5)

        password_entry = Entry(frame, show="*", font=self.styles["text"])
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
                set_view(self, self.interface_init)
            else:
                messagebox.showerror("Error", "Incorrect password")
                password_entry.delete(0, "end")

        Button(frame, text="Submit", font=self.styles["button"], command=submit).pack(
            pady=10
        )

    def interface_init(self, frame):
        """
        Renders the main administrator navigation menu with options to access
        the Admin Console, the Casino Interface, or exit the application.
        Also logs the administrator login event to the database.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Welcome Administrator", font=self.styles["heading"]).pack(
            pady=20
        )

        self.dbm.admin_logged_in()

        buttons = [
            ("Access Admin Console", self.admin_console),
            ("Access Casino", self.access_casino),
            ("Exit", self.interface_root.destroy),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=3)

    def admin_console(self):
        """
        Opens the Admin Console window by instantiating the Admin_Console class
        from admin_console_V6.
        """

        Admin_Console()

    def access_casino(self):
        """
        Opens the Casino Interface in administrator mode by instantiating
        Casino_Interface with administrator=True from casino_interface_V6.
        """

        self.interface_root.destroy()

        Casino_Interface(True)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# admin_console_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Admin_Console:
    """
    Provides the administrator console interface, giving access to password
    management, the encryption software, database management, and user
    management. Sensitive operations are protected by a master password.
    """

    def __init__(self):
        """
        Initialises the Admin Console window, loads the database manager and
        font styles, and starts at the main console menu.
        """
        self.adm_console_root = Tk()
        self.adm_console_root.title("One More Time Casino - Administrator Console")
        try:
            self.adm_console_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.adm_console_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.dbm = DatabaseManagement()
        self.DB_FILE = DB_FILE

        self.MASTER_PASSWORD = "Master_Password"

        self.styles = fetch_font_settings(self.adm_console_root)

        self.main_frame = Frame(self.adm_console_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.show_console_menu)

        self.adm_console_root.mainloop()

    def show_console_menu(self, frame):
        """
        Renders the main admin console menu with navigation buttons for all
        available administrative operations.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
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
            ("Exit", self.adm_console_root.destroy),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def change_admin_password(self, frame):
        """
        Renders the admin password change flow. Requires master password
        verification before prompting for the current admin password, then
        uses passwords_confirmation to set a new one. Displays appropriate
        error or success dialogs at each stage and returns to the main menu
        on completion or cancellation.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return
        if messagebox.askyesno(
            "Confirm password change",
            "Are you sure you want to change the administrative password to the system?",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    Label(
                        frame,
                        text="Enter Old Administrator Password:",
                        font=self.styles["heading"],
                    ).pack(pady=20)

                    password_entry = Entry(frame, show="*", font=self.styles["text"])
                    password_entry.pack(pady=5)

                    def submit():
                        """
                        Verifies the current admin password, then launches the
                        password confirmation dialog to capture and store the
                        new password. Returns to the main menu on success.
                        """
                        old_password = password_entry.get()
                        result = self.dbm.admin_password_check(old_password)

                        if not (result.get("found") and result.get("verified")):
                            messagebox.showerror("Error", "Incorrect password")
                            password_entry.delete(0, "end")
                            return

                        password_state = passwords_confirmation(
                            frame, self.adm_console_root
                        )
                        if not password_state["confirmed"]:
                            return

                        new_password = password_state["password"]
                        self.dbm.change_admin_password(new_password)

                        messagebox.showinfo(
                            "Success", "Administrator password updated successfully!"
                        )

                        set_view(self, self.show_console_menu)

                    Button(
                        frame,
                        text="next",
                        font=self.styles["button"],
                        width=25,
                        command=submit,
                    ).pack(pady=10)

                    Button(
                        frame,
                        text="Back",
                        font=self.styles["button"],
                        width=25,
                        command=lambda: set_view(self, self.show_console_menu),
                    ).pack(pady=10)

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )
                    set_view(self, self.show_console_menu)

            except Exception as error:
                messagebox.showerror("Error", f": {error}")
        else:
            messagebox.showinfo("Cancelled", "Password change cancelled.")
            set_view(self, self.show_console_menu)

    def encryption_software_access(self):
        """
        Opens the Encryption Software window by instantiating the
        Encryption_Software class from encryption_software_V6.
        """

        Encryption_Software()

    def show_database_management(self, frame):
        """
        Renders the database management submenu with options to create or
        delete the database, view table contents, or return to the main menu.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Database Management", font=self.styles["heading"]).pack(
            pady=10
        )

        buttons = [
            ("Create Database", self.create_database),
            ("Delete Database", self.delete_database),
            ("View Database", lambda: set_view(self, self.show_view_database)),
            ("Export Table to CSV", self.table_to_csv),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def create_database(self):
        """
        Prompts for confirmation and master password verification before
        creating the database. If the database already exists, the operation
        is safe to run as all tables use CREATE TABLE IF NOT EXISTS. Displays
        a success or error message on completion.
        """
        if messagebox.askyesno(
            "Confirm Creation",
            f"Are you sure you want to create '{self.DB_FILE}'?\n Note: Nothing will change if the database is already present.",
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    self.dbm.create_database()
                    messagebox.showinfo(
                        "Success", f"'{self.DB_FILE}' created successfully."
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to create '{self.DB_FILE}': {error}"
                )

    def delete_database(self):
        """
        Checks the database exists, then prompts for confirmation and master
        password verification before permanently deleting the database file.
        Displays a success or error message on completion.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        if messagebox.askyesno(
            "Confirm Delete", f"Are you sure you want to delete '{self.DB_FILE}'?"
        ):
            try:
                password = simpledialog.askstring(
                    "Verification",
                    "Please enter Master Password to continue:",
                    show="*",
                    parent=self.adm_console_root,
                )

                if password == self.MASTER_PASSWORD:
                    os.remove(self.DB_FILE)
                    messagebox.showinfo(
                        "Success", f"'{self.DB_FILE}' deleted successfully."
                    )

                else:
                    messagebox.showerror(
                        "Error", "Incorrect password. Operation cancelled."
                    )

            except Exception as error:
                messagebox.showerror(
                    "Error", f"Failed to delete '{self.DB_FILE}': {error}"
                )

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
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        Label(frame, text="Select Table to View", font=self.styles["heading"]).pack(
            pady=10
        )

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
            Reads the selected table name from the dropdown, queries it via
            the database manager, and navigates to the table display view.
            Shows an error if no table is selected or the result is empty.
            """
            selected_table = dropdown.get().strip()
            if not selected_table:
                messagebox.showerror("Error", "Please select a table first.")
                return

            dataframe = self.dbm.view_database(selected_table)

            if dataframe.empty:
                messagebox.showinfo("Info", f"No data found in '{selected_table}'.")
                return

            set_view(self, lambda f: self.display_table(f, dataframe, selected_table))

        Button(
            frame,
            text="View Table",
            font=self.styles["button"],
            width=25,
            command=view_table,
        ).pack(pady=5)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text=f"'{table}' Table", font=self.styles["heading"]).pack(pady=10)

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

        # Insert rows with alternating tags for styling, the '_' character is used to prevent issues with special characters in the data interfering with tag assignment.
        for count, (_, row) in enumerate(dataframe.iterrows()):
            tag = "evenrow" if count % 2 == 0 else "oddrow"
            tree.insert("", "end", values=list(row), tags=(tag,))
        tree.tag_configure("evenrow", background="#a50b5e")
        tree.tag_configure("oddrow", background="#feb29c")

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_view_database),
        ).pack(pady=5)

    def table_to_csv(self):
        """
        Prompts the user to select a database table and a save location,
        then exports the selected table's contents to a CSV text file.
        """
        table = simpledialog.askstring(
            "Export Table",
            "Enter the name of the table to export:",
            parent=self.adm_console_root,
        )

        if not table:
            messagebox.showerror("Returning to Menu", "No table name provided.")
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
            self.dbm.export_table_to_csv(table, save_path)
            messagebox.showinfo("Success", f"'{table}' exported to:\n{save_path}")
        except Exception as error:
            messagebox.showerror("Error", f"Failed to export '{table}': {error}")

    def show_user_management(self, frame):
        """
        Renders the user management submenu with options to fetch, add, edit,
        or delete user records. Shows a warning if the database does not exist.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.dbm.check_database_exists():
            messagebox.showwarning("Warning", f"'{self.DB_FILE}' does not exist.")
            return

        Label(frame, text="User Management", font=self.styles["heading"]).pack(pady=10)

        buttons = [
            ("Return User Information", lambda: set_view(self, self.fetch_user_record)),
            ("Add User", lambda: set_view(self, self.add_user)),
            ("Edit User", lambda: set_view(self, self.edit_user)),
            ("Delete User", lambda: set_view(self, self.delete_user)),
            ("Back to Main Menu", lambda: set_view(self, self.show_console_menu)),
        ]

        for text, command in buttons:
            Button(
                frame, text=text, font=self.styles["button"], width=30, command=command
            ).pack(pady=5)

    def fetch_user_record(self, frame):
        """
        Renders a search form allowing lookup by user ID, username, or both.
        When both are provided, verifies that they refer to the same user
        before proceeding. Navigates to the record display view on a
        successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Enter User ID", font=self.styles["heading"]).pack(pady=10)
        user_id_entry = Entry(frame)
        user_id_entry.pack(pady=5)

        Label(frame, text="Enter Username", font=self.styles["heading"]).pack(pady=10)
        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def lookup_user():
            """
            Resolves the entered user ID and/or username to a full user record.
            Validates cross-referencing when both are provided, then navigates
            to the record display view. Shows appropriate errors for mismatches,
            non-numeric IDs, or missing users.
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
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))
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
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))
                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()
                record = self.dbm.fetch_user_full_record(username=username)
                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return
                set_view(self, lambda f: self.display_user_record(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        Button(
            frame,
            text="Search",
            font=self.styles["button"],
            width=25,
            command=lookup_user,
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def display_user_record(self, frame, record):
        """
        Renders a read-only view of a user's full record, including username,
        password hash, account type, balance, creation timestamp, and
        termination status with details if applicable.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The user record dictionary as returned by
                           fetch_user_full_record().
        """
        Label(
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
            Label(
                frame, text=f"{key}: {value}", font=self.styles["text"], anchor="w"
            ).pack(fill="x", padx=20, pady=2)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Enter Username", font=self.styles["heading"]).pack(pady=10)

        username_entry = Entry(frame)
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

        Button(
            frame, text="Next", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def choose_account_type(self, frame, username):
        """
        Presents a choice between creating a registered account (with password)
        or a temporary guest account (without password). Navigates to password
        creation for registered accounts, or creates the guest account
        immediately and returns to user management.

        Args:
            frame (Frame): The parent frame to build the view into.
            username (str): The username for the account being created.
        """
        Label(frame, text="Account Type", font=self.styles["heading"]).pack(pady=10)

        def register():
            """Navigates to the password creation view for a registered account."""
            set_view(self, lambda f: self.create_password(f, username))

        def guest():
            """
            Creates a temporary guest account with no password and navigates
            back to the user management menu.
            """
            self.dbm.sign_in_user(username, None, False)

            messagebox.showinfo(
                "Success", f"Temporary guest account '{username}' created successfully!"
            )

            set_view(self, self.show_user_management)

        Button(
            frame,
            text="Register Account",
            font=self.styles["button"],
            width=25,
            command=register,
        ).pack(pady=5)

        Button(
            frame,
            text="Temporary Guest Account",
            font=self.styles["button"],
            width=25,
            command=guest,
        ).pack(pady=5)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog in a loop until a valid
        confirmed password is provided, then creates the registered user
        account and returns to the user management menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        while True:
            password_state = passwords_confirmation(frame, self.adm_console_root)
            if password_state["confirmed"]:
                self.dbm.sign_in_user(username, password_state["password"], True)

                messagebox.showinfo(
                    "Success", f"Account for '{username}' created successfully!"
                )

                set_view(self, self.show_user_management)
                break

    def edit_user(self, frame):
        """
        Renders a search form for locating a user to edit, accepting a user ID,
        username, or both. Cross-validates when both are provided. Navigates to
        the edit form on a successful lookup.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Enter User ID:", font=self.styles["heading"]).pack(pady=10)

        user_id_entry = Entry(frame)
        user_id_entry.pack(pady=5)

        Label(frame, text="Enter Username:", font=self.styles["heading"]).pack(pady=10)

        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Resolves the entered user ID and/or username to a full user record,
            cross-validating when both are provided, then navigates to the edit
            form. Shows appropriate errors for mismatches, non-numeric IDs, or
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

                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))

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
                    record = self.dbm.fetch_user_full_record(user_id=int(user_id))

                    if not record:
                        messagebox.showinfo("Not Found", "User not found.")
                        return
                else:
                    messagebox.showerror("Error", "User ID must be numeric.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            elif username_entry.get().strip():
                username = username_entry.get().strip()
                if not username:
                    messagebox.showerror("Error", "No input provided.")
                    return

                record = self.dbm.fetch_user_full_record(username=username)

                if not record:
                    messagebox.showinfo("Not Found", "User not found.")
                    return

                set_view(self, lambda f: self.show_edit_form(f, record))

            else:
                messagebox.showerror("Error", "No input provided.")
                return

        Button(
            frame, text="Next", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)

    def show_edit_form(self, frame, record):
        """
        Renders an editable form pre-populated with the current user record.
        Allows changing username, password, account type, balance, and
        termination status. Calls change_user_record with only the fields
        that have been filled in.

        Args:
            frame (Frame): The parent frame to build the view into.
            record (dict): The current user record dictionary.
        """
        Label(
            frame,
            text=f"Edit User:\n{record['user_id']} | {record['username']}",
            font=self.styles["heading"],
        ).pack(pady=10)

        Label(frame, text="New Username:").pack()
        username_entry = Entry(frame)
        username_entry.pack()

        Label(frame, text="New Password:").pack()
        password_entry = Entry(frame, show="*")
        password_entry.pack()

        Label(frame, text="New Account Type:").pack()
        type_box = Combobox(frame, values=["Registered", "Temporary"], state="readonly")
        type_box.set("Registered" if not record.get("temporary") else "Temporary")
        type_box.pack()

        Label(frame, text="New Balance:").pack()
        balance_entry = Entry(frame)
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

            if type_box.get() == "Registered":
                kwargs["new_account_type"] = True
            else:
                kwargs["new_account_type"] = False

            try:
                kwargs["new_balance"] = float(balance_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Invalid balance.")
                return

            self.dbm.change_user_record(**kwargs)

            messagebox.showinfo("Success", "User updated successfully.")
            set_view(self, self.show_user_management)

        Button(
            frame,
            text="Save Changes",
            font=self.styles["button"],
            width=25,
            command=save,
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Enter Username to Delete", font=self.styles["heading"]).pack(
            pady=10
        )

        username_entry = Entry(frame)
        username_entry.pack(pady=5)

        def next():
            """
            Validates the entered username exists and is not the Administrator
            account, confirms deletion with the user, then resolves the
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

        Button(
            frame, text="Delete", font=self.styles["button"], width=25, command=next
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_user_management),
        ).pack(pady=5)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# terms_and_conditions_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def terms_and_conditions():
    return """
    ---

    **Terms and Conditions for One More Time Casino Ltd**

    ---

    ### © Belongs to ~~~ The composition of this code is original and not to be sold commercially unless stated otherwise by the owner.

    ### Last Updated: 12/09/2025 22:14:55 GMT

    ---

    **INTRODUCTION**

    Welcome to One More Time Casino Ltd (“we,” “us,” or “the Casino”). By accessing or using the services provided by One More Time Casino Ltd (the “Services”) through our future website, future mobile application, or other platforms (collectively referred to as the “Platform”), you agree to comply with and be bound by these Terms and Conditions (“Terms”). These Terms constitute a legally binding agreement between you (“the Player,” “User,” or “you”) and One More Time Casino Ltd. If you do not agree with these Terms, you should refrain from using the Platform or any Services provided by the Casino.

    Please read these Terms carefully before proceeding, as they outline your rights, obligations, and limitations as a Player on One More Time Casino Ltd.

    ---

    ### 1. GENERAL TERMS

    #### 1.1 Eligibility

    1.1.1 Players must be at least 2 months old to access and use the Services of the Casino. By creating an account, you confirm that you meet the minimum requirements and accept all responsibility.
    1.1.2 The Casino reserves the right to request proof of age and may suspend or terminate your account if appropriate verification is not provided. All funds shall be donated to the CEO's gaming funds.

    #### 1.2 Account Registration

    1.2.1 To access the data servers and hold the right to withdraw any money earned, Players must create a personal account (“Account”). The Player agrees to provide accurate, current, and complete information during the registration process and to update such information as necessary. If an account isn’t created, any money earned during the usage of a temporary account will return to the Casino.
    1.2.2 Each Player may only create and maintain one account. Multiple accounts for the same Player are prohibited, and the Casino reserves the right to suspend or terminate any duplicate accounts. Please consult Section 9 for further information.
    1.2.3 Players are responsible for maintaining the confidentiality of their login details. Any activities performed through your account, whether authorised or unauthorised, are your responsibility. You agree to notify the Casino immediately if you suspect any unauthorised use of your Account.

    ---

    ### 2. USE OF THE SERVICES

    #### 2.1 License to Use the Platform

    2.1.1 Upon successful registration, the Casino grants you a limited, non-transferable, and revocable license to use the Platform for personal entertainment purposes only.
    2.1.2 You agree not to:

    * Use the Platform for any unlawful or fraudulent activity.
    * Engage in any behaviour that disrupts or negatively impacts the Casino’s reputation, operations or services.
    * Reverse engineer, modify, or alter any part of the Platform or its software. If caught doing so, punishment Level 3 will be instigated.

    #### 2.2 Prohibited Activities

    2.2.1 Players must refrain from engaging in any activity that violates applicable laws, regulations, or Casino rules. This includes, but is not limited to:

    * Attempting to manipulate or interfere with the proper functioning of the Platform; any damages caused to the database must be paid in full.
    * Collusion or cheating, including any unauthorised use of software or bots to gain an unfair advantage.
    * Money laundering or using the Platform as a conduit for illegal financial transactions.
    * Anything the CEO perceives as unfavourable or detrimental.
    * Causing emotional distress to the CEO.

    ---

    ### 3. FINANCIAL TRANSACTIONS

    #### 3.1 Deposits

    3.1.1 Players may deposit funds into their Casino Account using payment methods made available by the Casino. The Casino reserves the right to determine which payment methods are accepted, and some methods may only be available based on the Player’s location.
    3.1.2 All deposits must be made in the Player’s name. Deposits by third parties may be deemed invalid, and the Casino reserves the right to refund or freeze such transactions and use them for the purchase of Pokémon cards.
    3.1.3 Players are responsible for ensuring that their deposit funds are legitimate. The Casino will not be liable for deposit delays or failures caused by external banking institutions or third-party providers.

    #### 3.2 Withdrawals

    3.2.1 Players may request withdrawals of available funds by following the procedures set out in the Platform. Withdrawals are subject to minimum and maximum limits outlined by the Casino.
    3.2.2 The Casino may require Players to verify their identity before processing withdrawal requests. Verification may include providing documents such as proof of identity, address, and payment method used. Most of the time a password will suffice.
    3.2.3 The Casino reserves the right to withhold or delay withdrawals if fraudulent activity is suspected or if wagering requirements tied to bonuses have not been fulfilled.
    3.2.4 Withdrawals will be processed using the same method as the deposit, where possible, or by an alternative method approved by the Casino.
    3.2.5 Withdrawals may be received between the next 5 minutes and G years, where G = g64: g1 = 3↑↑↑↑3, gn = 3↑gn−13.

    ---

    ### 4. BONUSES AND PROMOTIONS

    #### 4.1 General Terms for Bonuses

    4.1.1 The Casino may offer bonuses, promotions, or loyalty rewards to Players. Each bonus is subject to specific terms provided at the time of the offer. By accepting a bonus, the Player agrees to comply with its terms.
    4.1.2 Bonus offers are limited to one per person, household, email address, or IP address unless otherwise stated. Abuse may lead to Section 9, 9.4.

    #### 4.2 Wagering Requirements

    4.2.1 All bonuses are subject to wagering requirements before withdrawal. Wagering requirements refer to the amount a Player must bet before being eligible to withdraw bonus-related winnings.
    4.2.2 Certain games may contribute differently to fulfilment of wagering requirements. For example, slot games may contribute 100%, while table games like WhiteJoe may contribute a smaller percentage or none at all.

    #### 4.3 Bonus Abuse

    4.3.1 Bonus abuse includes using multiple accounts, colluding to exploit bonuses, or violating specific promotion terms.
    4.3.2 If detected, the Casino reserves the right to void any bonuses and associated winnings and may suspend the Player or instigate punishment levels.

    ---

    ### 5. RESPONSIBLE GAMBLING

    #### 5.1 Commitment to Responsible Gambling

    5.1.1 The Casino promotes responsible gambling and provides tools to help Players manage behaviour.
    5.1.2 Players may set limits on deposits, losses, wagering, and time spent on the Platform. Players may also request temporary or permanent self-exclusion by contacting the CEO.

    #### 5.2 Self-Exclusion

    5.2.1 Players may voluntarily opt for self-exclusion if developing problematic gambling behaviour. During self-exclusion, the Player will not be allowed to access their account or use services; the account will be suspended until the CEO consents to changes.
    5.2.2 The Casino will make reasonable efforts to enforce self-exclusion but is not liable if circumvention occurs.

    ---

    ### 6. ANTI-MONEY LAUNDERING (AML) AND FRAUD PREVENTION

    6.1 AML Compliance
    6.1.1 The Casino complies with international AML regulations and monitors suspicious activities.
    6.1.2 Players may be required to verify identity. The Casino may suspend or close accounts and freeze funds if AML concerns arise.

    6.2 Fraud Detection
    6.2.1 Attempts to defraud the Casino via identity theft, unauthorized credit card use, or system manipulation may result in immediate account termination, forfeiture of winnings, and punishment Level 3.
    6.2.2 The Casino may cooperate with law enforcement to investigate fraud.

    ---

    ### 7. PRIVACY AND DATA PROTECTION

    7.1 Collection of Personal Data
    7.1.1 By using the Platform, the Player consents to collection, processing, and storage of personal data in accordance with the Casino’s Privacy Policy.
    7.1.2 Collected data may include (but not limited to) name, address, date of birth, email, and payment information.

    7.2 Use of Personal Data
    7.2.1 Data may be used to provide and improve services, verify identities, conduct AML checks, marketing purposes, for profits by selling to the highest bidder, employee training, or AI training.

    7.3 Data Security
    7.3.1 The Casino uses advanced encryption technology but cannot guarantee absolute security and will not be liable for unauthorised access beyond its control.

    ---

    ### 8. DISPUTE RESOLUTION

    8.1 Internal Complaint Handling
    8.1.1 Complaints may be submitted to customer support. Resolution may take up to a millennia.
    8.1.2 Complaints must be submitted within 0-1 Planck second of the incident.

    8.2 Arbitration
    8.2.1 Disputes not resolved internally shall be settled via binding arbitration.
    8.2.2 Arbitration decisions are final and binding.

    ---

    ### 9. ENFORCEMENT OF PUNISHMENT

    9.1 Violation Level 1 → Player will have their screen time controlled until R\\$1,000,000 is paid to the CEO’s offshore bank account.
    9.2 Violation Level 2 → Player will have to play in League of Legend championships until 77,777 Lei is paid to the CEO’s Swiss bank.
    9.3 Violation Level 3 → Immediate deportation from home country; identity erased; all belongings and bank accounts repossessed. Exceptions: a Blu-ray LOTR collection, PS3 Uncharted case (no disk), and a Braille edition of *Dune Trilogy*.

    ---

    ### 10. LIMITATION OF LIABILITY

    10.1 The Casino is not liable for damages arising from use or inability to use the Platform, including indirect or consequential damages.
    10.2 Not liable for interruptions due to acts of God, internet outages, or technical failures.
    10.3 The Player agrees to indemnify the Casino for claims arising from use, violation of Terms, or infringement of third-party rights.
    10.4 The Casino is not liable for any health (including mental) related issues such as (in alphabetical order): Abdominal aortic aneurysm, Achilles tendinopathy, Acne, Acute cholecystitis, Acute pancreatitis, Addison’s disease, Adenomyosis, Alcohol-related liver disease, Allergic rhinitis, Allergies, Alzheimer’s disease, Anaphylaxis, Angina, Angioedema, Ankle sprain, Ankylosing spondylitis, Anorexia nervosa, Anxiety, Anxiety disorders, Appendicitis, Arterial thrombosis, Arthritis, Asbestosis, Asthma, Ataxia, Atopic eczema, Atrial fibrillation, Attention deficit hyperactivity disorder (ADHD), Autistic spectrum disorder (ASD), Benign prostate enlargement, Binge eating, Bipolar disorder, Blood poisoning (sepsis), Bowel incontinence, Bowel polyps, Brain stem death, Bronchiectasis, Bronchitis, Bulimia, Bunion, Cardiovascular disease, Carpal tunnel syndrome, Catarrh, Cellulitis, Cerebral palsy, Cervical spondylosis, Chest and rib injury, Chest infection, Chickenpox, Chilblains, Chlamydia, Chronic fatigue syndrome, Chronic kidney disease, Chronic obstructive pulmonary disease (COPD), Chronic pain, Chronic pancreatitis, Cirrhosis, Clostridium difficile, Coeliac disease, Cold sore, Coma, Common cold, Congenital heart disease, Conjunctivitis, Constipation, Coronary heart disease, Costochondritis, Cough, Crohn’s disease, Croup, Cystic fibrosis, Cystitis, Deaf blindness, Deep vein thrombosis, Dehydration, Delirium, Dementia, Dental abscess, Depression, Dermatitis herpetiformis, Diabetes, Diabetic retinopathy, Diarrhoea, Discoid eczema, Diverticular disease and diverticulitis, Dizziness, Down’s syndrome, Dry mouth, Dysphagia, Dystonia, Earache, Earwax build-up, Ebola virus disease, Ectopic pregnancy, Edwards’ syndrome, Endometriosis, Epilepsy, Erectile dysfunction, Escherichia coli (E. coli) O157, Febrile seizures, The feeling of something in your throat, Fever, Fibroids, Fibromyalgia, Flu, Foetal alcohol syndrome, Food allergy, Food poisoning, Frozen shoulder, Functional neurological disorder (FND), Fungal nail infection, Gallstones, Ganglion cyst, Gastroenteritis, Gastro-oesophageal reflux disease (GORD), Genital herpes, Genital symptoms, Genital warts, Glandular fever, Golfers elbow, Gonorrhoea, Gout, Greater trochanteric pain syndrome, Gum disease, Haemorrhoids (piles), Hay fever, Head lice and nits, Headaches, Hearing loss, Heart attack, Heart block, Heart failure, Heart palpitations, Hepatitis A, Hepatitis B, Hepatitis C, Hiatus hernia, High blood pressure (hypertension), High cholesterol, HIV, Huntington’s disease, Hyperglycaemia (high blood sugar), Hyperhidrosis, Hypoglycaemia (low blood sugar), Idiopathic pulmonary fibrosis, Impetigo, Indigestion, Ingrown toenail, Infertility, Inflammatory bowel disease (IBD), Insomnia, Iron deficiency anaemia, Irritable bowel syndrome (IBS), Itching, Itchy bottom, Itchy skin, Joint hypermobility, Kidney infection, Kidney stones, Labyrinthitis, Lactose intolerance, Laryngitis, Leg cramps, Lichen planus, Lipoedema, Liver disease, Loss of libido, Low blood pressure (hypotension), Lumbar stenosis, Lupus, Lyme disease, Lymphoedema, Lymphogranuloma venereum (LGV), Malaria, Malnutrition, Managing genital symptoms, Measles, Meningitis, Meniere’s disease, Menopause, Middle ear infection (otitis media), Migraine, Motor neurone disease (MND), Mouth ulcer, Multiple sclerosis (MS), Multiple system atrophy (MSA), Mumps, Munchausen’s syndrome, Myalgic encephalomyelitis (ME) or chronic fatigue syndrome (CFS), Myasthenia gravis, Neck problems, Non-alcoholic fatty liver disease (NAFLD), Norovirus, Nosebleed, Obesity, Obsessive compulsive disorder (OCD), Obstructive sleep apnoea, Oral thrush in adults, Osteoarthritis, Osteoarthritis of the hip, Osteoarthritis of the knee, Osteoarthritis of the thumb, Osteoporosis, Outer ear infection (otitis externa), Overactive thyroid, Pain in the ball of the foot, Panic disorder, Parkinson’s disease, Patau’s syndrome, Patellofemoral pain syndrome, Pelvic inflammatory disease, Pelvic organ prolapse, Peripheral neuropathy, Personality disorder, PIMS, Plantar heel pain, Pleurisy, Pneumonia, Polio, Polycystic ovary syndrome (PCOS), Polymyalgia rheumatica, Post-polio syndrome, Post-traumatic stress disorder (PTSD), Postural orthostatic tachycardia syndrome (PoTS), Postnatal depression, Pregnancy and baby, Pressure ulcers, Progressive supranuclear palsy (PSP), Psoriasis, Psoriatic arthritis, Psychosis, Pulmonary hypertension, Rare conditions, Raynaud’s phenomenon, Reactive arthritis, Restless legs syndrome, Respiratory syncytial virus (RSV), Rheumatoid arthritis, Ringworm and other fungal infections, Rosacea, Scabies, Scarlet fever, Schizophrenia, Sciatica, Scoliosis, Seasonal affective disorder (SAD), Sepsis, Septic shock, Shingles, Shortness of breath, Sudden Dwarfism, Sickle cell disease, Sinusitis, Sjogren’s syndrome, Skin light sensitivity (photosensitivity), Skin rashes in children, Slapped cheek syndrome, Sore throat, Spleen problems and spleen removal, Stomach ache and abdominal pain, Stomach ulcer, Streptococcus A (strep A), Stress and low mood, Stroke, Subacromial pain syndrome, Sunburn, Supraventricular tachycardia, Swollen glands, Syphilis, Tennis elbow, Thirst, Threadworms, Thrush, Tick bites, Tinnitus, Tonsillitis, Tooth decay, Toothache, Tourette’s syndrome, Transient ischaemic attack (TIA), Transverse myelitis, Trichomonas infection, Trigeminal neuralgia, Tuberculosis (TB), Type 1 diabetes, Type 2 diabetes, Ulcerative colitis, Underactive thyroid, Urinary incontinence, Urinary tract infection (UTI), Urticaria (hives), Varicose eczema, Varicose veins, Venous leg ulcer, Vertigo, Vitamin B12 or folate deficiency anaemia, Warts and verruca, Whiplash, Whooping cough, Wolff-Parkinson-White syndrome, Yellow fever.
    10.5 The Casino is not liable for mistakes in input or failure to use capital/incorrect letters.

    ---

    ### 11. AMENDMENTS TO THE TERMS

    11.1 The Casino may modify these Terms at any time; changes communicated via email or Platform notice or not at all.
    11.2 Continued use constitutes acceptance of revised Terms.

    ---

    ### 12. GOVERNING LAW AND JURISDICTION

    12.1 Terms governed by laws of the Casino's jurisdiction of incorporation (Just Kidding).
    12.2 Legal action subject to exclusive jurisdiction of the Casino’s courts (Also Kidding).

    ---

    ### 13. MISCELLANEOUS

    13.1 Severability: Invalid provisions do not affect remaining Terms.
    13.2 Assignment: The Casino may assign rights and obligations; the Player may not assign rights.
    13.3 Waiver: Delay or failure to exercise rights does not constitute waiver.

    ---

    **CONTACT INFORMATION**

    One More Time Casino Ltd
    Customer Support Email: support@onemoretimecasino.com
    Customer Support Number: 61016
    CEO Email: 19santoe@sjfchs.org.uk

    ---
    """


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# user_interface_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class User_Interface:
    """
    Provides the user-facing entry point to the casino application.
    Displays the Terms & Conditions and requires the user to agree before
    granting access to the Casino Interface.
    Automatically creates the database if it does not already exist.
    """

    def __init__(self):
        """
        Initialises the User Interface window, checks for database existence,
        and starts the application at the Terms & Conditions screen.
        """
        self.interface_root = Tk()
        self.interface_root.title("One More Time Casino - User Interface")
        try:
            self.interface_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.interface_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.dbm = DatabaseManagement()

        if not self.dbm.check_database_exists():
            self.dbm.create_database()

        self.styles = fetch_font_settings(self.interface_root)

        self.main_frame = Frame(self.interface_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        set_view(self, self.show_terms_and_conditions)

        self.interface_root.mainloop()

    def show_terms_and_conditions(self, frame):
        """
        Renders the Terms & Conditions screen. Displays the full T&C text in a
        scrollable, read-only text area. A checkbox must be ticked before the
        Continue button becomes active, at which point the user proceeds to the
        casino introduction screen.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(frame, text="Terms & Conditions", font=self.styles["title"]).pack(pady=10)

        # Create a scrolled text area for long T&C content
        text_area = scrolledtext.ScrolledText(
            frame, wrap=WORD, font=self.styles["terms_and_conditions"]
        )
        text_area.pack(expand=True, fill=BOTH)

        text_area.insert(END, terms_and_conditions())
        text_area.configure(state="disabled")

        agree_var = IntVar()
        tc_window_checkbutton = Checkbutton(
            frame, text="I Agree to the Terms & Conditions", variable=agree_var
        )
        tc_window_checkbutton.pack(pady=5)

        continue_button = Button(
            frame,
            text="Continue",
            state=DISABLED,
            command=lambda: set_view(self, self.casino_intro),
        )
        continue_button.pack(pady=5)

        def on_checkbox_change(*args):
            """
            Callback triggered when the agree checkbox value changes.
            Enables or disables the Continue button based on checkbox state.
            """
            continue_button.config(state=NORMAL if agree_var.get() == 1 else DISABLED)

        agree_var.trace_add("write", on_checkbox_change)

    def casino_intro(self, frame):
        """
        Renders the casino introduction screen with options to access the
        casino, re-read the Terms & Conditions, or exit the application.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame, text="Welcome to\nOne More Time Casino", font=self.styles["heading"]
        ).pack(pady=20)

        Button(
            frame,
            text="Access Casino",
            font=self.styles["button"],
            width=30,
            command=self.access_casino,
        ).pack(pady=5)

        Button(
            frame,
            text="Read Terms & Conditions",
            font=self.styles["button"],
            width=30,
            command=lambda: set_view(self, self.show_terms_and_conditions),
        ).pack(pady=5)

        Button(
            frame,
            text="Exit",
            font=self.styles["button"],
            width=30,
            command=self.interface_root.destroy,
        ).pack(pady=5)

    def access_casino(self):
        """
        Opens the Casino Interface in standard user mode by instantiating
        Casino_Interface with administrator=False from casino_interface_V6.
        """

        self.interface_root.destroy()

        Casino_Interface(False)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# casino_interface_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Minimum rounds played before a user may enable Tournament Mode.
# At 25 rounds the VPIP/PFR counters carry statistical weight and the
# hand-range chart has been updated to a reasonable level to reflect player tendencies.
TOURNAMENT_MIN_ROUNDS = 25

# Gauntlet Mode

# Bot difficulty starts at GAUNTLET_START_DIFFICULTY and increases by
# GAUNTLET_DIFFICULTY_STEP every GAUNTLET_RAMP_INTERVAL rounds.

GAUNTLET_START_DIFFICULTY = 10  # default starting difficulty
GAUNTLET_DIFFICULTY_STEP = 10  # +10 per ramp interval
GAUNTLET_RAMP_INTERVAL = 5  # ramp every N rounds
GAUNTLET_BOT_COUNT = 3  # fixed number of opponents

# Endless Mode

# Max bots, difficulties randomly distributed 0-100 and reshuffled each round.
ENDLESS_BOT_COUNT = 9

DEFAULT_SETTINGS = {
    # Harrogate Hold 'Em
    "bot_count": 3,
    "bot_balance": 1000,
    "small_blind": 50,
    "big_blind": 100,
    "bot_difficulty": 50,
    # Tournament
    "tournament_mode": False,
    "tournament_rounds": 5,
    "tournament_players": 4,  # Total players including user
    "win_criteria": "eliminate_all",
    "win_criteria_target": 1000,  # Used when criteria is "earn_target"
    # Gauntlet
    "gauntlet_mode": False,
    "gauntlet_start_difficulty": GAUNTLET_START_DIFFICULTY,
    # Endless
    "endless_mode": False,
    # General
    "starting_balance": 10000,
}

TOURNAMENT_WIN_CRITERIA = {
    "eliminate_all": "Eliminate all opponents",
    "earn_target": "Earn a target amount of money",
    "survive_rounds": "Survive a set number of rounds",
    "last_man_blind": "Outlast opponents as blinds escalate",
}


class Casino_Interface:
    """
    Main casino interface for users and administrators. Handles login,
    account management, game selection, and mode-specific rules such as
    tournament, gauntlet and endless play.
    """

    def __init__(self, administrator=False, user_data=None):
        """
        Initialises the Casino Interface window, sets up the database manager,
        font styles, and user data state. If launched in administrator mode,
        pre-populates user data and marks the session as signed in before
        starting the main menu.

        Args:
            administrator (bool): If True, the interface launches in
                                  administrator mode, bypassing login.
            user_data (dict, optional): A dictionary containing user information
                                        to pre-populate the session with.
                                        Expected keys: 'user_id', 'username',
                                        'administrator'. If None, defaults to
                                        an unsigned-in state.
        """
        self.interface_root = Tk()
        self.interface_root.title(
            "One More Time Casino — Administrator Access"
            if administrator
            else "One More Time Casino"
        )
        try:
            self.interface_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.interface_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.dbm = DatabaseManagement()

        self.styles = fetch_font_settings(self.interface_root)

        if user_data is not None:
            self.user_data = user_data
        else:
            self.user_data = {
                "user_id": None,
                "username": None,
                "administrator": False,
            }

        if administrator:
            self.user_data["user_id"] = 0
            self.user_data["username"] = "Administrator"
            self.user_data["administrator"] = True

        self.main_frame = Frame(self.interface_root)
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.current_section_frame = None

        # Personalised settings for casino games (starts from defaults)
        self.settings = dict(DEFAULT_SETTINGS)

        set_view(self, self.casino_menu)
        self.interface_root.mainloop()

    # Helpers

    def user_linked(self):
        """
        Returns True if a user account is currently linked to this session
        (i.e. the user is signed in or this is an administrator session).

        Returns:
            bool: True if a user is linked, False otherwise.
        """
        return bool(self.user_data.get("username"))

    def fetch_rounds_played(self):
        """
        Retrieves the number of poker rounds the current user has played
        from the database. Returns 0 for administrators or if the data
        cannot be fetched.

        Returns:
            int: Rounds played, or 0 on failure / admin session.
        """
        if self.user_data.get("administrator"):
            # Administrators are never blocked by the rounds threshold
            return TOURNAMENT_MIN_ROUNDS

        user_id = self.user_data.get("user_id")
        if not user_id:
            return 0

        try:
            statistics = self.dbm.fetch_player_statistics(user_id)
            return int(statistics["rounds_played"]) if statistics else 0
        except Exception:
            return 0

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

    def fetch_special_scores(self):
        """
        Retrieves the player's personal best scores for Gauntlet and Endless
        modes from the database.

        Returns:
            tuple: (gauntlet_pb, endless_pb) where each is an int representing
                   the maximum rounds survived, or 0 if no score exists.
        """
        user_id = self.user_data.get("user_id")
        if not user_id:
            return 0, 0

        try:
            statistics = self.dbm.fetch_player_statistics(user_id)
            if not statistics:
                return 0, 0
            gauntlet_pb = int(statistics.get("gauntlet_max_rounds", 0))
            endless_pb = int(statistics.get("endless_high_score", 0))
            # with:
            scores = self.dbm.fetch_special_mode_scores(user_id)
            if not scores:
                return 0, 0
            gauntlet_pb = scores["gauntlet_max_rounds"]
            endless_pb = scores["endless_high_score"]
            return gauntlet_pb, endless_pb
        except Exception:
            return 0, 0

    # Main menu

    def casino_menu(self, frame):
        """
        Displays the main casino menu. Displays a sign-in prompt if no user
        is logged in, or a personalised welcome message if one is.

        Game Menu and Game Settings buttons are disabled with an explanatory
        note when no account is linked.  All other buttons are always active.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame,
            text="One More Time Casino\nWelcome to the Casino",
            font=self.styles["heading"],
        ).pack(pady=15)

        linked = self.user_linked()

        if not linked:
            Label(
                frame,
                text="Please sign in.\nIf you do not have an account please register.",
                font=self.styles["emphasis"],
            ).pack(pady=10)
        else:
            Label(
                frame,
                text=f"Welcome, {self.user_data['username']}",
                font=self.styles["subheading"],
            ).pack(pady=10)

        # Game Menu
        Button(
            frame,
            text="Game Menu",
            font=self.styles["button"],
            width=30,
            state="normal" if linked else "disabled",
            command=lambda: set_view(self, self.show_game_menu),
        ).pack(pady=5)

        if not linked:
            Label(
                frame,
                text="Sign in to access the Game Menu.",
                font=self.styles["emphasis"],
            ).pack()

        # Account buttons
        Button(
            frame,
            text="Sign Up",
            font=self.styles["button"],
            width=30,
            command=self.user_sign_up,
        ).pack(pady=5)

        Button(
            frame,
            text="Login",
            font=self.styles["button"],
            width=30,
            command=self.user_login_setup,
        ).pack(pady=5)

        # Account information
        account_text = (
            "Account Information" if linked else "Sign in to access user info"
        )
        Button(
            frame,
            text=account_text,
            font=self.styles["button"],
            width=30,
            state="normal" if linked else "disabled",
            command=lambda: set_view(self, self.fetch_user_record),
        ).pack(pady=5)

        if not linked:
            Label(
                frame,
                text="Sign in to view account information.",
                font=self.styles["emphasis"],
            ).pack()

        Button(
            frame,
            text="Exit Casino",
            font=self.styles["button"],
            width=30,
            command=self.casino_exit,
        ).pack(pady=5)

    # Game menu

    def show_game_menu(self, frame):
        """
        Displays the game selection menu. Requires an account to be linked;
        redirects to the main menu with a warning if not.

        Gauntlet and Endless modes are configured and launched from Game
        Settings. The Leaderboard remains here for quick access.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("the Game Menu"):
            set_view(self, self.casino_menu)
            return

        Label(
            frame,
            text="Game Menu",
            font=self.styles["heading"],
        ).pack(pady=20)

        buttons = [
            ("WhiteJoe", self.whitejoe_rules),
            ("Harrogate Hold 'Em", self.harrogate_hold_em_rules),
            ("Leaderboard", lambda: set_view(self, self.show_leaderboard)),
            ("Game Settings", lambda: set_view(self, self.game_settings)),
            ("Return to Main Menu", lambda: set_view(self, self.casino_menu)),
        ]

        for text, command in buttons:
            Button(
                frame,
                text=text,
                font=self.styles["button"],
                width=30,
                command=command,
            ).pack(pady=5)

    # Registration & login

    def user_sign_up(self):
        """
        Initiates the registration flow. If the administrator is already
        signed in, prompts for confirmation before proceeding. Displays the
        age restriction warning required under the Gambling Act 2005 before
        navigating to the username input screen.
        """
        if self.user_data["administrator"]:
            if not messagebox.askyesno(
                "Administrator",
                "You are already signed in as an administrator.  "
                "Register a new account?",
            ):
                return

        messagebox.showwarning(
            "Age Restriction",
            "Under the Gambling Act 2005: Part 4, Protection of children and "
            "young persons. It is illegal to permit any person under the age "
            "of 18 to enter a licensed gambling premises. The only exception "
            "is licensed family entertainment centres. For further information "
            "please visit: https://www.legislation.gov.uk/ukpga/2005/19/contents.\n\n"
            "By proceeding you confirm that you are over the age of 18.",
        )
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
        Label(
            frame,
            text="Enter Username",
            font=self.styles["heading"],
        ).pack(pady=10)

        username_entry = Entry(frame, font=self.styles["text"])
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

            if registered:
                set_view(self, lambda f: self.set_account_type(f, username))
            else:
                set_view(self, lambda f: self.user_login(f, username))

        Button(
            frame,
            text="Next",
            font=self.styles["button"],
            width=25,
            command=proceed,
        ).pack(pady=10)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
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
        Label(frame, text="Account Type", font=self.styles["heading"]).pack(pady=10)

        def register():
            set_view(self, lambda f: self.create_password(f, username))

        def temporary():
            self.dbm.sign_in_user(username, None, False)
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
            Button(
                frame,
                text=text,
                font=self.styles["button"],
                width=25,
                command=command,
            ).pack(pady=5)

    def create_password(self, frame, username):
        """
        Launches the password confirmation dialog, creates the registered user
        account on success, and returns to the main casino menu.

        Args:
            frame (Frame): The parent frame used to position the dialog.
            username (str): The username for the account being created.
        """

        password_info = passwords_confirmation(frame, self.interface_root)
        if password_info["confirmed"]:
            self.dbm.sign_in_user(username, password_info["password"], True)
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

        Label(
            frame,
            text=f"Login for '{username}'",
            font=self.styles["heading"],
        ).pack(pady=10)

        Label(frame, text="Enter Password:", font=self.styles["text"]).pack(pady=5)

        password_entry = Entry(frame, show="*", font=self.styles["text"])
        password_entry.pack(pady=5)

        def submit_password():
            """Verifies the password and navigates accordingly."""
            password = password_entry.get().strip()
            result = self.dbm.verify_user_password(username, password)

            if result.get("found") and result.get("verified"):
                uid = self.dbm.fetch_user_id(username)
                self.user_data["user_id"] = uid["user_id"] if uid["found"] else None
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

        Button(
            frame,
            text="Login",
            font=self.styles["button"],
            width=25,
            command=submit_password,
        ).pack(pady=5)

        Button(
            frame,
            text="Cancel",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=5)

    # Account information

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

        record = self.dbm.fetch_user_full_record(username=self.user_data["username"])
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
        Label(
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
            Label(
                frame,
                text=f"{label}: {value}",
                font=self.styles["text"],
                anchor="w",
            ).pack(fill="x", padx=20, pady=2)

        Button(
            frame,
            text="Back",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.casino_menu),
        ).pack(pady=10)

    # Exit

    def casino_exit(self):
        """
        Prompts for confirmation before exiting the casino. Displays a
        thank-you and responsible gambling message on confirmation.
        """
        if messagebox.askyesno("Exit Casino", "Do you wish to exit the casino?"):
            messagebox.showinfo(
                "Thank You for Visiting",
                "Thank you for visiting One More Time Casino.  "
                "We hope to see you again soon.  "
                "And remember, when the fun stops, stop.",
            )
            self.interface_root.destroy()
            sys.exit(0)

    # Game settings

    def game_settings(self, frame):
        """
        Displays the Harrogate Hold 'Em settings panel.
        Requires an account to be linked; redirects if not.
        """
        if not self.require_linked("Game Settings"):
            set_view(self, self.casino_menu)
            return

        Label(frame, text="Game Settings", font=self.styles["heading"]).pack(
            pady=(10, 4)
        )

        # Live variables
        v_bot_count = IntVar(value=self.settings["bot_count"])
        v_bot_balance = StringVar(value=str(self.settings["bot_balance"]))
        v_small_blind = StringVar(value=str(self.settings["small_blind"]))
        v_big_blind = StringVar(value=str(self.settings["big_blind"]))
        v_bot_diff = IntVar(value=self.settings["bot_difficulty"])
        v_tournament = BooleanVar(value=self.settings["tournament_mode"])
        v_total_rounds = IntVar(value=self.settings["tournament_rounds"])
        v_total_players = IntVar(value=self.settings["tournament_players"])
        v_win_criteria = StringVar(value=self.settings["win_criteria"])
        v_win_target = StringVar(value=str(self.settings["win_criteria_target"]))
        v_gauntlet_diff = IntVar(
            value=self.settings.get(
                "gauntlet_start_difficulty", GAUNTLET_START_DIFFICULTY
            )
        )

        def label(text):
            Label(frame, text=text, font=self.styles["subheading"], anchor="w").pack(
                fill="x", padx=30, pady=(10, 2)
            )

        def row(label_text, widget_factory):
            row = Frame(frame)
            row.pack(fill="x", padx=30, pady=2)
            Label(
                row, text=label_text, font=self.styles["text"], width=32, anchor="w"
            ).pack(side="left")
            widget_factory(row).pack(side="left", padx=8)

        # Table Settings
        label("Table Settings")
        row(
            "Number of bots (1–9):",
            lambda p: Spinbox(
                p,
                from_=1,
                to=9,
                textvariable=v_bot_count,
                width=6,
                font=self.styles["text"],
            ),
        )
        row(
            "Bot starting balance (£):",
            lambda p: Entry(
                p, textvariable=v_bot_balance, width=10, font=self.styles["text"]
            ),
        )
        row(
            "Small blind (£):",
            lambda p: Entry(
                p, textvariable=v_small_blind, width=10, font=self.styles["text"]
            ),
        )
        row(
            "Big blind (£):",
            lambda p: Entry(
                p, textvariable=v_big_blind, width=10, font=self.styles["text"]
            ),
        )

        # Bot Difficulty
        label("Bot Difficulty  (0 = easy, 100 = hard)")
        difficulty_label = Label(
            frame,
            text=f"Current: {v_bot_diff.get()}",
            font=self.styles["emphasis"],
            anchor="w",
        )
        difficulty_label.pack(fill="x", padx=30)
        Scale(
            frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable=v_bot_diff,
            font=self.styles["text"],
            length=400,
            command=lambda v: difficulty_label.config(text=f"Current: {int(float(v))}"),
        ).pack(anchor="w", padx=30, pady=2)

        # Tournament Mode
        label("Tournament Mode")
        rounds_played = self.fetch_rounds_played()
        rounds_needed = max(0, TOURNAMENT_MIN_ROUNDS - rounds_played)

        if rounds_needed > 0:
            Label(
                frame,
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
            toggle_row = Frame(frame)
            toggle_row.pack(fill="x", padx=30, pady=2)
            Label(
                toggle_row,
                text="Enable Tournament Mode:",
                font=self.styles["text"],
                width=32,
                anchor="w",
            ).pack(side="left")
            Checkbutton(toggle_row, variable=v_tournament).pack(side="left")

            Label(
                frame,
                text=f"Rounds played: {rounds_played}",
                font=self.styles["emphasis"],
                anchor="w",
            ).pack(fill="x", padx=30, pady=(0, 4))

            row(
                "Number of rounds:",
                lambda p: Spinbox(
                    p,
                    from_=1,
                    to=50,
                    textvariable=v_total_rounds,
                    width=6,
                    font=self.styles["text"],
                ),
            )
            row(
                "Total players (inc. you):",
                lambda p: Spinbox(
                    p,
                    from_=2,
                    to=10,
                    textvariable=v_total_players,
                    width=6,
                    font=self.styles["text"],
                ),
            )

            crit_frame = Frame(frame)
            crit_frame.pack(fill="x", padx=30, pady=2)
            Label(
                crit_frame,
                text="Round win criteria:",
                font=self.styles["text"],
                width=32,
                anchor="w",
            ).pack(side="left")
            crit_box = Combobox(
                crit_frame,
                textvariable=v_win_criteria,
                values=list(TOURNAMENT_WIN_CRITERIA.keys()),
                state="readonly",
                font=self.styles["text"],
                width=20,
            )
            crit_box.pack(side="left", padx=8)

            crit_desc = Label(
                frame,
                text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), ""),
                font=self.styles["emphasis"],
                anchor="w",
            )
            crit_desc.pack(fill="x", padx=30)

            target_frame = Frame(frame)
            Label(
                target_frame,
                text="Earn target (£):",
                font=self.styles["text"],
                width=32,
                anchor="w",
            ).pack(side="left")
            Entry(
                target_frame,
                textvariable=v_win_target,
                width=12,
                font=self.styles["text"],
            ).pack(side="left", padx=8)

            def on_criteria_change(event=None):
                crit_desc.config(
                    text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), "")
                )
                if v_win_criteria.get() == "earn_target":
                    target_frame.pack(fill="x", padx=30, pady=2)
                else:
                    target_frame.pack_forget()

            crit_box.bind("<<ComboboxSelected>>", on_criteria_change)
            if v_win_criteria.get() == "earn_target":
                target_frame.pack(fill="x", padx=30, pady=2)

        # Gauntlet Mode
        label("Gauntlet Mode")
        gauntlet_pb, _ = self.fetch_special_scores()
        Label(
            frame,
            text=(
                f"Personal best: {gauntlet_pb} round"
                f"{'s' if gauntlet_pb != 1 else ''}"
                if gauntlet_pb > 0
                else "No score yet."
            ),
            font=self.styles["emphasis"],
            anchor="w",
        ).pack(fill="x", padx=30)
        row(
            "Starting difficulty (0–90):",
            lambda p: Spinbox(
                p,
                from_=0,
                to=90,
                increment=10,
                textvariable=v_gauntlet_diff,
                width=6,
                font=self.styles["text"],
            ),
        )
        Button(
            frame,
            text="Start Gauntlet",
            font=self.styles["button"],
            width=20,
            command=lambda: self.start_gauntlet(
                max(0, min(90, int(v_gauntlet_diff.get())))
            ),
        ).pack(anchor="w", padx=30, pady=4)

        # Endless Mode
        label("Endless Mode")
        _, endless_pb = self.fetch_special_scores()
        Label(
            frame,
            text=(
                f"High score: {endless_pb} round"
                f"{'s' if endless_pb != 1 else ''} survived"
                if endless_pb > 0
                else "No score yet."
            ),
            font=self.styles["emphasis"],
            anchor="w",
        ).pack(fill="x", padx=30)
        Button(
            frame,
            text="Start Endless",
            font=self.styles["button"],
            width=20,
            command=self.start_endless,
        ).pack(anchor="w", padx=30, pady=4)

        # Bottom buttons
        button_frame = Frame(frame)
        button_frame.pack(pady=12)

        def save_settings():
            """Validates and saves Standard and Tournament settings."""
            errors = []

            try:
                bot_count = int(v_bot_count.get())
                if not (1 <= bot_count <= 9):
                    raise Exception("Bot count out of range.")
            except Exception:
                errors.append("Bot count must be between 1 and 9.")
                bot_count = self.settings["bot_count"]

            try:
                bot_balance = int(v_bot_balance.get())
                if bot_balance <= 0:
                    raise Exception("Bot balance must be positive.")
            except Exception:
                errors.append("Bot balance must be a positive integer.")
                bot_balance = self.settings["bot_balance"]

            try:
                small_blind = int(v_small_blind.get())
                if small_blind <= 0:
                    raise Exception("Small blind must be positive.")
            except Exception:
                errors.append("Small blind must be a positive integer.")
                small_blind = self.settings["small_blind"]

            try:
                big_blind = int(v_big_blind.get())
                if big_blind <= 0:
                    raise Exception("Big blind must be a positive integer.")
                raw_small = (
                    int(v_small_blind.get())
                    if v_small_blind.get().isdigit()
                    else small_blind
                )
                if big_blind < raw_small:
                    raise Exception("Big blind must be ≥ small blind.")
            except Exception:
                errors.append("Big blind must be ≥ small blind.")
                big_blind = self.settings["big_blind"]

            try:
                difference = max(0, min(100, int(v_bot_diff.get())))
            except Exception:
                difference = self.settings["bot_difficulty"]

            try:
                total_rounds = int(v_total_rounds.get())
                if total_rounds < 1:
                    raise Exception("Tournament rounds must be ≥ 1.")
            except Exception:
                errors.append("Tournament rounds must be ≥ 1.")
                total_rounds = self.settings["tournament_rounds"]

            try:
                total_players = int(v_total_players.get())
                if not (2 <= total_players <= 10):
                    raise Exception("Tournament players out of range.")
            except Exception:
                errors.append("Tournament players must be between 2 and 10.")
                total_players = self.settings["tournament_players"]

            try:
                win_target = int(v_win_target.get())
                if win_target <= 0:
                    raise Exception("Win target must be positive.")
            except Exception:
                errors.append("Win target must be a positive integer.")
                win_target = self.settings["win_criteria_target"]

            try:
                gaunt_start_diff = max(0, min(90, int(v_gauntlet_diff.get())))
            except Exception:
                gaunt_start_diff = self.settings.get(
                    "gauntlet_start_difficulty", GAUNTLET_START_DIFFICULTY
                )

            if self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS:
                tournament_on = False
            else:
                tournament_on = bool(v_tournament.get())

            if errors:
                messagebox.showerror("Settings Error", "\n".join(errors))
                return

            self.settings.update(
                {
                    "bot_count": bot_count,
                    "bot_balance": bot_balance,
                    "small_blind": small_blind,
                    "big_blind": big_blind,
                    "bot_difficulty": difference,
                    "tournament_mode": tournament_on,
                    "tournament_rounds": total_rounds,
                    "tournament_players": total_players,
                    "win_criteria": v_win_criteria.get(),
                    "win_criteria_target": win_target,
                    "gauntlet_start_difficulty": gaunt_start_diff,
                }
            )

            messagebox.showinfo(
                "Settings Saved",
                "Settings updated successfully.",
            )

        def reset_defaults():
            """Resets all settings to DEFAULT_SETTINGS after confirmation."""
            if messagebox.askyesno(
                "Reset Settings",
                "Reset all settings to defaults?",
            ):
                self.settings = dict(DEFAULT_SETTINGS)
                set_view(self, self.game_settings)

        for text, command in (
            ("Save Settings", save_settings),
            ("Reset to Defaults", reset_defaults),
            ("Back to Game Menu", lambda: set_view(self, self.show_game_menu)),
        ):
            Button(
                button_frame,
                text=text,
                font=self.styles["button"],
                width=20,
                command=command,
            ).pack(side="left", padx=10)

    # Leaderboard

    def show_leaderboard(self, frame):
        """
        Displays a leaderboard showing the top Gauntlet and Endless scores
        across all players in the database. Uses get_all_players_data()
        to retrieve the full data set and sorts by each metric.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        Label(
            frame,
            text="Leaderboard",
            font=self.styles["heading"],
        ).pack(pady=(15, 5))

        try:
            all_data = self.dbm.fetch_all_players_data()
        except Exception:
            all_data = []

        def board_section(title, key, unit="rounds"):
            """Displays a titled top-5 table for a single metric."""
            Label(
                frame,
                text=title,
                font=self.styles["subheading"],
            ).pack(pady=(12, 2))
            Frame(frame, height=1, bg="#888888").pack(fill="x", padx=40)

            candidates = [
                p for p in all_data if p.get(key, 0)
            ]  # Filter out players with no score for this metric
            ranked = bubble_sort(candidates, key=key, reverse=True)[
                :5
            ]  # Sort and take top 5

            # Use binary_search_by_id for the username lookup
            sorted_by_id = bubble_sort(
                all_data, key="user_id"
            )  # Ensure data is sorted by user_id for binary search
            for entry in ranked:
                index = binary_search_by_id(sorted_by_id, entry["user_id"])
                if index != -1:
                    try:
                        result = self.dbm.fetch_username(sorted_by_id[index]["user_id"])
                        username = (
                            result["username"]
                            if result["found"]
                            else f"User {entry['user_id']}"
                        )
                    except Exception:
                        username = f"User {entry['user_id']}"
                else:
                    username = f"User {entry['user_id']}"

            if not ranked:
                Label(
                    frame,
                    text="No scores recorded yet.",
                    font=self.styles["text"],
                ).pack(pady=4)
                return

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

                score = int(entry[key])
                Label(
                    frame,
                    text=f"  {index}.  {username:<20}  {score} {unit}",
                    font=self.styles["text"],
                    anchor="w",
                ).pack(fill="x", padx=60, pady=1)

        board_section("Gauntlet — Most Rounds Survived", "gauntlet_max_rounds")
        board_section("Endless — Most Rounds Survived", "endless_high_score")

        Button(
            frame,
            text="Back to Game Menu",
            font=self.styles["button"],
            width=25,
            command=lambda: set_view(self, self.show_game_menu),
        ).pack(pady=14)

    # Post-game summary (special modes)

    def show_special_mode_summary(self, mode, rounds_survived):
        """
        Shows a post-game summary dialog for Gauntlet or Endless mode,
        comparing the result to the player's stored personal best and
        updating the database if a new record was set.

        Args:
            mode (str): Either "gauntlet" or "endless".
            rounds_survived (int): How many rounds the player survived.
        """
        user_id = self.user_data.get("user_id")
        gauntlet_pb, endless_pb = self.fetch_special_scores()

        if mode == "gauntlet":
            old_pb = gauntlet_pb
            pb_key = "gauntlet_max_rounds"
            label = "Gauntlet"
        else:
            old_pb = endless_pb
            pb_key = "endless_high_score"
            label = "Endless"

        new_record = rounds_survived > old_pb

        if new_record and user_id:
            try:
                self.dbm.update_special_mode_score(user_id, pb_key, rounds_survived)
            except Exception:
                pass

        if new_record:
            title = f"New Personal Best!"
            msg = (
                f"{label} Mode — Game Over\n\n"
                f"Rounds survived: {rounds_survived}\n"
                f"Previous best: {old_pb}\n\n"
                f"New personal best! Well played."
            )
        else:
            title = f"{label} Mode — Game Over"
            msg = (
                f"{label} Mode — Game Over\n\n"
                f"Rounds survived: {rounds_survived}\n"
                f"Personal best: {old_pb}\n\n"
                f"{'So close! ' if rounds_survived >= old_pb - 2 and old_pb > 0 else ''}"
                f"Keep going to beat your record!"
            )

        messagebox.showinfo(title, msg)
        set_view(self, self.show_game_menu)

    # Game launchers

    def whitejoe_rules(self):
        """
        Launches the WhiteJoe rules window. Requires a linked account.
        On the user agreeing to the rules, starts the WhiteJoe game.
        """
        if not self.require_linked("WhiteJoe"):
            return

        ShowGameRules(self.interface_root).show_whitejoe_rules(
            lambda: self.start_whitejoe()
        )

    def start_whitejoe(self):
        """
        Instantiates and launches the WhiteJoe game, passing the current
        user data.
        """

        WhiteJoe(self.user_data)

        self.interface_root.destroy()

    def harrogate_hold_em_rules(self):
        """
        Launches the Harrogate Hold 'Em rules window. Requires a linked
        account. On the user agreeing to the rules, starts the game.
        """
        if not self.require_linked("Harrogate Hold 'Em"):
            return

        ShowGameRules(self.interface_root).show_harrogate_hold_em_rules(
            lambda: self.start_harrogate()
        )

    def start_harrogate(self):
        """
        Builds a bot roster from self.settings and launches standard
        Harrogate Hold 'Em.

        If tournament_mode is True but the player is below the round
        threshold, tournament_mode is silently forced off as a safety net
        (the settings panel already prevents this scenario).
        """

        # Never allow tournament below the threshold
        settings = dict(self.settings)
        settings["gauntlet_mode"] = False
        settings["endless_mode"] = False
        if (
            settings.get("tournament_mode")
            and self.fetch_rounds_played() < TOURNAMENT_MIN_ROUNDS
        ):
            settings["tournament_mode"] = False

        bot_count = settings["bot_count"]
        difficulty = settings["bot_difficulty"]

        roster = list(DEFAULT_BOT_ROSTER)
        random.shuffle(roster)
        bots = [[roster[index % len(roster)], difficulty] for index in range(bot_count)]

        HarrogateHoldEm(self.user_data, settings, bots)

        self.interface_root.destroy()

    def start_gauntlet(self, start_difficulty=None):
        """
        Launches Gauntlet Mode.

        Builds a settings dict with 'gauntlet_mode=True' and the chosen
        starting difficulty. The game engine is expected to read
        'gauntlet_mode', 'gauntlet_start_difficulty',
        'gauntlet_difficulty_step', and 'gauntlet_ramp_interval' from
        the settings dict to implement the ramp.

        After the game returns, 'show_special_mode_summary' is called
        with the rounds survived, which the engine should store in
        'settings["rounds_survived"]' on exit.

        Args:
            start_difficulty (int, optional): Starting bot difficulty.
                Defaults to the GAUNTLET_START_DIFFICULTY constant.
        """

        if start_difficulty is None:
            start_difficulty = self.settings.get(
                "gauntlet_start_difficulty", GAUNTLET_START_DIFFICULTY
            )

        settings = dict(self.settings)
        settings["gauntlet_mode"] = True
        settings["endless_mode"] = False
        settings["tournament_mode"] = False
        settings["bot_count"] = GAUNTLET_BOT_COUNT
        settings["gauntlet_start_difficulty"] = start_difficulty
        settings["gauntlet_difficulty_step"] = GAUNTLET_DIFFICULTY_STEP
        settings["gauntlet_ramp_interval"] = GAUNTLET_RAMP_INTERVAL
        settings["rounds_survived"] = 0  # The engine writes here on exit

        roster = list(DEFAULT_BOT_ROSTER)
        random.shuffle(roster)
        bots = [
            [roster[index % len(roster)], start_difficulty]
            for index in range(GAUNTLET_BOT_COUNT)
        ]

        HarrogateHoldEm(self.user_data, settings, bots)

        rounds = int(settings.get("rounds_survived", 0))
        self.show_special_mode_summary("gauntlet", rounds)

        self.interface_root.destroy()

    def start_endless(self):
        """
        Launches Endless Mode.

        Nine bots are created with randomly distributed difficulties across
        the full 0–100 range. The settings dict carries 'endless_mode=True'
        so the engine can reshuffle bot difficulties each round and never
        declare a winner. Rounds survived are read back from
        'settings["rounds_survived"]' after the game returns.
        """

        settings = dict(self.settings)
        settings["endless_mode"] = True
        settings["gauntlet_mode"] = False
        settings["tournament_mode"] = False
        settings["bot_count"] = ENDLESS_BOT_COUNT
        settings["rounds_survived"] = 0  # The engine writes here on exit

        roster = list(DEFAULT_BOT_ROSTER)
        random.shuffle(roster)

        # Spread difficulties evenly across the range then shuffle
        step = 100 // ENDLESS_BOT_COUNT
        difficulties = [min(100, index * step) for index in range(ENDLESS_BOT_COUNT)]
        random.shuffle(difficulties)

        bots = [
            [roster[index % len(roster)], difficulties[index]]
            for index in range(ENDLESS_BOT_COUNT)
        ]

        HarrogateHoldEm(self.user_data, settings, bots)

        rounds = int(settings.get("rounds_survived", 0))
        self.show_special_mode_summary("endless", rounds)

        self.interface_root.destroy()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# game_rules_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class ShowGameRules:
    """
    Displays game rules for WhiteJoe and Harrogate Hold 'em in a modal
    Toplevel window. The user must scroll through the rules and tick a
    checkbox confirming they have read and understood them before the
    Continue button becomes active. The window cannot be closed via the
    window manager's close button.
    """

    def __init__(self, root):
        """
        Initialises the ShowGameRules instance, stores the root window
        reference for font settings and Toplevel parenting, and defines
        the full rules text for both games.

        Args:
            root: The root Tk window used to bind fonts and parent the
                  rules Toplevel.
        """
        self.interface_root = root

        self.styles = fetch_font_settings(root)

        self.wj_rules = """
        The aim of the game is to beat the dealer by getting higher than the dealer’s hand value.\n
        To beat the dealer you must either:\n
        \t1. Draw a hand value that is higher than the dealer’s hand value.\n
        \t2. The dealer draws a hand value that goes over 21.\n
        \t3. Draw a hand value of 21 on your first two cards, when the dealer does not.\n
        To lose the game:\n
        \t1. Your hand value exceeds 21.\n
        \t2. The dealers hand has a greater value than yours at the end of the round.\n
        You will start off with a whopping £1,000 (Can be distributed in any multiple of 10) and the buy in is already paid for.\n
        You will then be offered to place a bet with the amount of money you have, The screen will show how much you have in your possession.(Saved Data not available yet).\n
        The dealer will then deal out the cards clockwise (Multiplayer not available yet) with 2 cards facing upwards for you and 1 card facing up and another hidden for dealer.\n
        The dealer will start at the person on their left (also known as “first base”) and wait for that player to play their hand.\n
        You have two cards face up in front of your bet.\n
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

        self.hhe_rules = """
        The aim of the game is to use your hole cards in combination with the community cards to make the best possible five-card poker hand.
        \t*Each player is dealt two cards face down (the 'hole cards')
        \t*Over several betting rounds, five more cards are (eventually) dealt face up in the middle of the table.
        \t*These face-up cards are called the 'community cards'. Each player is free to use the community cards in combination with their hole cards to build a five-card poker hand.
        The community cards are revealed in 3 stages, 3 community cards are revealed in the 1st stage and 1 community card in the others:
        \t*1st stage is called the 'Flop'.
        \t*2nd stage is called the 'Turn'.
        \t*3rd stage is called the 'River'.
        Your goal is to construct your five-card poker hands using the best available five cards out of the seven total cards (your two hole cards and the five community cards).
        You can do that by using both your hole cards in combination with three community cards, one hole card in combination with four community cards, or no hole cards.
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
        \tAfter the first player acts, the play proceeds down the list with each player also having the same three options — to call, to raise, or fold.
        \tOnce the last bet is called and the action is 'closed', the preflop round is over and play moves on to the flop.
        *The Flop:
        \tAfter the first preflop betting round has been completed, the first three community cards are dealt and a second betting round follows involving only the players who have not folded already.
        \tIn this betting round (and subsequent ones), the action starts with the first active player to the left of the button.
        \tAlong with the options to bet, call, fold, or raise, a player now has the option to 'check' if no betting action has occurred beforehand. A check simply means to pass the action to the next player in the hand.
        \tAgain betting continues until the last bet or raise has been called (which closes the action). It also can happen that every player simply chooses not to bet and checks around the 'table', which also ends the betting round.
        *The Turn:
        \tThe fourth community card, called the turn, is dealt face-up following all betting action on the flop.
        \tOnce this has been completed, another round of betting occurs, similar to that on the previous round of play. Again players have the option to check, bet, call, fold, or raise.
        *The River:
        \tThe fifth community card, called the river, is dealt face-up following all betting action on the turn.
        \tOnce this has been completed, another round of betting occurs, similar to what took play on the previous round of play. Once more the remaining players have the option to options to check, bet, call, fold, or raise.
        \tAfter all betting action has been completed, the remaining players in the hand with hole cards now expose their holdings to determine a winner. This is called the showdown.
        *The Showdown:
        \tThe remaining players show their hole cards, and with the assistance of the dealer, a winning hand is determined.
        \tThe player with the best combination of five cards wins the pot according to the official poker hand rankings.
        \tA link to the official poker hand rankings will be attached to this document and in the game before you start. 
        \thttps://en.wikipedia.org/wiki/List_of_poker_hands
        Unique to this game is the opportunity to change difficulty (difficulty is regarding the opponents) and create custom characters however their actions are independent to single rounds and any money they lose or earn is not carried forward.
        Once again you are reminded to read the T&C's before playing.
        """

    def show_whitejoe_rules(self, callback):
        """
        Opens the rules window for WhiteJoe and calls the provided callback
        once the user confirms they have read and understood the rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("WhiteJoe Rules", self.wj_rules, callback)

    def show_harrogate_hold_em_rules(self, callback):
        """
        Opens the rules window for Harrogate Hold 'em and calls the provided
        callback once the user confirms they have read and understood the
        rules.

        Args:
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        self.show_rules_window("Harrogate Hold 'em Rules", self.hhe_rules, callback)

    def show_rules_window(self, title, rules_text, callback):
        """
        Creates and displays a modal rules window with a scrollable read-only
        text area and a Continue button.
        The window cannot be closed via the window manager's close button.
        Calls the callback and destroys the window when the user clicks Continue.

        Args:
            title (str): The window title and heading label text.
            rules_text (str): The full rules text to display.
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        window = Toplevel(self.interface_root)
        window.title(title)
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", lambda: None)
        try:
            window.attributes("-zoomed", True)
        except Exception:
            pass
        try:
            window.state("zoomed")
        except Exception:
            pass

        # Heading label
        heading = Label(window, text=title, font=self.styles["title"])
        heading.pack(pady=10)

        # Scrollable text area
        text_area = scrolledtext.ScrolledText(
            window, wrap=WORD, font=self.styles["terms_and_conditions"]
        )
        text_area.pack(expand=True, fill=BOTH, padx=10)
        text_area.insert(END, rules_text)
        text_area.configure(state="disabled")
        text_area.yview_moveto(0)

        # Bottom controls
        bottom_frame = Frame(window)
        bottom_frame.pack(side=BOTTOM, fill=X, pady=10)

        continue_button = Button(
            bottom_frame,
            text="Continue",
            command=lambda: (window.destroy(), callback()),
        )
        continue_button.pack(pady=10)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# deck_management_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SUITS = ["♠", "♣", "♥", "♦"]
SUIT_MAP = {"♠": "s", "♣": "c", "♥": "h", "♦": "d"}
REVERSE_SUIT_MAP = {v: k for k, v in SUIT_MAP.items()}

VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


class CasinoDeckManager:
    """
    Central manager for deck handling, card format conversion, and game logic
    for both poker and blackjack. Wraps the treys library to provide a unified
    interface for drawing cards, evaluating hands, and converting between
    string and integer card representations.
    """

    def __init__(self, shuffle=True, game_mode="poker"):
        """
        Initialises the deck manager with a fresh treys deck, a treys
        Evaluator instance, and the specified game mode. Optionally shuffles
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

    def set_game_mode(self, mode):
        """
        Sets the active game mode, controlling which evaluation logic is used
        in evaluate_hand().

        Args:
            mode (str): The game mode to set. Must be 'poker' or 'blackjack'.

        Raises:
            ValueError: If mode is not 'poker' or 'blackjack'.
        """
        # mode: 'poker' or 'blackjack'
        mode = mode.lower()

        if mode not in ("poker", "blackjack"):
            raise ValueError("Game mode must be 'poker' or 'blackjack'")

        self.game_mode = mode

    def str_deck(self):
        """
        Returns the current deck contents as a list of string representations.

        Returns:
            list[str]: All remaining cards in the deck as strings
                       (e.g. ['As', 'Kh', 'Td']).
        """
        return [self.treys_to_str(c) for c in self.deck.cards]

    def shuffle(self):
        """Shuffles the current deck in place."""
        self.deck.shuffle()

    def draw(self, n=1):
        """
        Draws n cards from the deck. If the deck has fewer than n cards
        remaining, resets and reshuffles the deck before drawing. Returns a
        single card integer when n=1, or a list of card integers when n>1.

        Args:
            n (int): The number of cards to draw. Defaults to 1.

        Returns:
            int or list[int]: A single treys card integer if n=1, or a list
                              of treys card integers if n>1.
        """
        if self.remaining() < n:
            self.deck = TreysDeck()
            self.deck.shuffle()
        if n != 1:
            cards = self.deck.draw(n)
        else:
            cards = self.deck.draw(n)[0]
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
            int: The count of remaining cards.
        """
        return len(self.deck.cards)

    def copy(self):
        """
        Creates an independent shallow copy of this deck manager instance.
        The copied deck shares the same Evaluator (which is stateless) but
        has its own independent card list. Used to ensure Monte Carlo
        simulations do not interfere with each other.

        Returns:
            CasinoDeckManager: A new deck manager instance with a copied
                               deck state and the same game mode.
        """
        new_dm = CasinoDeckManager(shuffle=False, game_mode=self.game_mode)

        # Copy deck state
        new_dm.deck.cards = self.deck.cards.copy()

        # Evaluator is stateless and safe to reuse
        new_dm.evaluator = self.evaluator

        return new_dm

    def str_to_treys(self, card_str):
        """
        Converts a card string to a treys integer representation.

        Args:
            card_str (str): A card string in the format 'Rs' where R is the
                            rank and s is the suit (e.g. 'As', 'Td', '2h').

        Returns:
            int: The treys integer representation of the card.
        """
        return TreysCard.new(card_str)

    def treys_to_str(self, card):
        """
        Converts a treys card integer to a standard string representation.

        Args:
            card (int): A treys card integer.

        Returns:
            str: The card as a string (e.g. 'As', 'Td', '2h').
        """
        rank = TreysCard.STR_RANKS[TreysCard.get_rank_int(card)]
        suit = TreysCard.INT_SUIT_TO_CHAR_SUIT[TreysCard.get_suit_int(card)]
        return rank + suit

    def treys_to_pretty(self, card):
        """
        Converts a treys card integer to a pretty-printed string using Unicode
        suit symbols.

        Args:
            card (int): A treys card integer.

        Returns:
            str: The card as a pretty string (e.g. 'A♠', 'T♦', '2♥').
        """
        rank = TreysCard.STR_RANKS[TreysCard.get_rank_int(card)]
        suit = TreysCard.INT_SUIT_TO_CHAR_SUIT[TreysCard.get_suit_int(card)]
        return rank + REVERSE_SUIT_MAP[suit]

    def treys_other(self, cards):
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

            # Ace
            if rank_int == 12:
                total += 11
                aces += 1
            # T, J, Q, K
            elif rank_int >= 8:
                total += 10
            # 2–9
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
        numerical hand value via blackjack_hand_value().

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
# whitejoe_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class WhiteJoe:
    """
    Starts a new window for the WhiteJoe game mode, which is a custom blackjack variant.
    Handles all game state, betting logic, card dealing, dealer resolution,
    and balance management. Supports both regular user and administrator
    sessions. All game events are logged to a scrollable message panel with
    colour-coded entries for wins, losses, and pushes.
    """

    def __init__(self, user_data):
        """
        Initialises the WhiteJoe game window, sets up external resources,
        initialises game state variables, and builds the main game interface.

        Args:
            user_data (dict): Dictionary containing at minimum 'username'
                              (str) and 'administrator' (bool) keys, and
                              optionally 'user_id'.
        """
        self.wj_root = Tk()
        self.wj_root.title("One More Time Casino - WhiteJoe")
        try:
            self.wj_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.wj_root.state("zoomed")  # Windows
        except Exception:
            pass

        self.user_data = user_data

        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        self.dbm = DatabaseManagement()

        self.styles = fetch_font_settings(self.wj_root)

        self.main_frame = Frame(self.wj_root)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.action_buttons = []

        self.colour_scheme = {
            # Left-hand panels
            "left_bg": "#252525",
            # Right-hand panels
            "top_right_bg": "#2e7d73",
            "bottom_right_bg": "#5b2a3c",
            # Widgets
            "widget_bg": "#6a2e4f",
            "text_bg": "#1a1a1a",
            "text_fg": "#f2f2f2",
            "left_fg": "#e8e8e8",
            # Log panel
            "log_bg": "#1a1a1a",
            "log_fg": "#cfcfcf",
            # Log entry
            "start_bg": "#243b7a",
            "start_fg": "#ffffff",
            "win_bg": "#244d3a",
            "win_fg": "#a8e6c1",
            "loss_bg": "#4a1e1e",
            "loss_fg": "#f2a3a3",
            "tie_bg": "#5c4a10",
            "tie_fg": "#f0d898",
        }

        # Game state
        self.player_hand = []
        self.dealer_hand = []
        self.dealer = "Genghis Khan"
        self.current_bet = 0
        self.round_active = False

        set_view(self, self.whitejoe_screen)

    def run(self):
        """
        Starts the tkinter main event loop for the WhiteJoe window.
        """
        self.wj_root.mainloop()

    def whitejoe_screen(self, frame):
        """
        Builds the main game layout using a three-panel grid. The left panel
        contains the scrollable game log, the top-right panel shows user
        information and balance, and the bottom-right panel contains the bet
        controls and action buttons.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        cs = self.colour_scheme

        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Left panel
        left_frame = Frame(frame, bd=2, relief="sunken", bg=cs["left_bg"])
        left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=5, pady=5)

        # Canvas + Scrollbar
        self.log_canvas = Canvas(left_frame, bg=cs["left_bg"], highlightthickness=0)
        scrollbar = Scrollbar(
            left_frame, orient="vertical", command=self.log_canvas.yview
        )
        self.log_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_canvas.pack(side="left", fill="both", expand=True)

        # Inner frame
        self.log_frame = Frame(self.log_canvas, bg=cs["left_bg"])
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
        top_right_frame = Frame(frame, bd=2, relief="sunken", bg=cs["top_right_bg"])
        top_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        Button(
            top_right_frame,
            text="Return to Menu",
            font=self.styles["button"],
            bg=cs["widget_bg"],
            fg=cs["text_fg"],
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.return_to_menu,
        ).pack(pady=5)

        balance = 0

        if not self.user_data.get("administrator"):
            balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
            if not balance_data["found"]:
                self.return_to_menu(
                    is_error=True, error=Exception("User not found in database.")
                )
                return
            balance = balance_data["balance"]
        else:
            self.admin_modify_bet(frame)

        labels = []
        for text in (
            f"Username: {self.user_data['username']}",
            f"Balance: £{balance}",
            "Current Bet: £0",
        ):
            label = Label(
                top_right_frame,
                text=text,
                font=self.styles["text"],
                bg=cs["top_right_bg"],
                fg=cs["text_fg"],
                anchor="w",
            )
            label.pack(anchor="w", pady=5, padx=5)
            labels.append(label)

        self.balance_label = cast(Label, labels[1])
        self.current_bet_label = cast(Label, labels[2])

        # Bottom-right panel
        bottom_right_frame = Frame(
            frame, bd=2, relief="sunken", bg=cs["bottom_right_bg"]
        )
        bottom_right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # Functions for user bet adjustment
        def adjust_current_bet(amount):
            try:
                value = int(self.bet_var.get())
            except Exception:
                value = 0
            value += amount
            balance = self.return_balance()
            if balance is not None:
                value = max(1, min(value, int(balance)))
            self.bet_var.set(str(value))
            self.current_bet_label.config(text=f"Current Bet: £{value}")
            self.update_button_states()

        def check_bet_input(*_):
            raw = self.bet_var.get()
            if raw in ("", "-"):
                self.current_bet_label.config(text="Current Bet: £0")
                self.start_button.config(state="disabled")
                return

            digits_only = "".join(c for c in raw if c.isdigit())
            if digits_only != raw:
                self.bet_var.set(digits_only if digits_only else "0")
                return
            try:
                value = int(digits_only) if digits_only else 0
            except Exception:
                value = 0

            balance = self.return_balance()
            if balance is not None:
                value = min(value, int(balance))
            self.current_bet_label.config(text=f"Current Bet: £{value}")
            self.update_button_states()

        # Bet entry
        self.bet_var = StringVar(value="0")
        self.bet_var.trace_add("write", check_bet_input)

        Entry(
            bottom_right_frame,
            textvariable=self.bet_var,
            width=12,
            font=self.styles["text"],
            bg=cs["widget_bg"],
            fg=cs["text_fg"],
            insertbackground=cs["text_fg"],
            relief="flat",
            bd=4,
            justify="center",
        ).pack(pady=(8, 6))

        # Increment rows
        for inc in (10, 100, 1000):
            row = Frame(
                bottom_right_frame,
                bg=cs["text_bg"],
                bd=2,
                relief="ridge",
                padx=6,
                pady=3,
            )
            row.pack(fill="x", pady=3)

            Button(
                row,
                text="+",
                font=self.styles["button"],
                width=3,
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda v=inc: adjust_current_bet(v),
            ).pack(side="left", padx=4)

            Label(
                row,
                text=str(inc),
                font=self.styles["text"],
                bg=cs["text_bg"],
                fg=cs["text_fg"],
                width=8,
                anchor="center",
            ).pack(side="left", expand=True)

            Button(
                row,
                text="-",
                font=self.styles["button"],
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                width=3,
                cursor="hand2",
                command=lambda v=-inc: adjust_current_bet(v),
            ).pack(side="right", padx=4)

        # Action buttons
        for text, command in (
            ("Hit", self.hit),
            ("Stand", self.stand),
            ("Double Down", self.double_down),
            ("Surrender", self.surrender),
        ):
            button = Button(
                bottom_right_frame,
                text=text,
                font=self.styles["button"],
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                width=18,
                cursor="hand2",
                command=command,
                state="disabled",
            )
            button.pack(pady=6)
            self.action_buttons.append(button)

        self.start_button = Button(
            bottom_right_frame,
            text="Start Round",
            font=self.styles["button"],
            bg=cs["start_bg"],
            fg=cs["start_fg"],
            relief="flat",
            bd=0,
            width=18,
            activebackground="#3a52a0",
            cursor="hand2",
            command=self.start_round,
        )
        self.start_button.pack(pady=10)

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
        self.start_button.config(
            state="disabled" if self.round_active or bet <= 0 else "normal"
        )

        # Action buttons
        state = "normal" if self.round_active else "disabled"
        for button in self.action_buttons:
            button.config(state=state)

    # Admin helper

    def admin_modify_bet(self, frame):
        """
        Opens a modal Toplevel dialog that allows the administrator to set
        a custom starting chip balance. The dialog cannot be dismissed
        via the window manager — a valid balance must be submitted.

        On submission, updates the balance label and persists the new
        balance to the database.

        Args:
            frame: The parent widget used to position the Toplevel.
        """
        balance_window = Toplevel(frame)
        balance_window.title("Set Starting Balance")
        balance_window.grab_set()
        balance_window.protocol("WM_DELETE_WINDOW", lambda: None)
        balance_window.configure(bg=self.colour_scheme["left_bg"])
        try:
            balance_window.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            balance_window.state("zoomed")  # Windows
        except Exception:
            pass

        Label(
            balance_window,
            text="Enter starting balance (£):",
            font=self.styles["text"],
            bg=self.colour_scheme["left_bg"],
            fg=self.colour_scheme["text_fg"],
        ).pack(pady=8)

        balance_entry = Entry(
            balance_window,
            width=20,
            font=self.styles["text"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            insertbackground=self.colour_scheme["text_fg"],
        )
        balance_entry.pack(pady=5)

        def submit_balance():
            """Validates the entry, updates the UI and database, and closes
            the dialog. Shows an error on invalid input."""
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()
                self.balance_label.config(text=f"Balance: £{balance}")
                balance_window.destroy()
                self.dbm.modify_user_balance(self.user_data["username"], balance)
            except Exception:
                messagebox.showerror(text="Please enter a valid positive integer.")

        Button(
            balance_window,
            text="Submit",
            font=self.styles["button"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            relief="flat",
            bd=0,
            command=submit_balance,
        ).pack(pady=10)

        def submit_balance():
            """
            Validates the entered balance as a non-negative integer, updates
            the balance label and database, and closes the dialog. Displays
            an inline error message if the value is invalid.
            """
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()

                self.balance_label.config(text=f"Balance: £{balance}")
                balance_window.destroy()

                self.dbm.modify_user_balance(self.user_data["username"], balance)

            except Exception:
                messagebox.showerror(text="Please enter a valid positive number.")

        Button(
            balance_window,
            text="Submit",
            font=self.styles["button"],
            command=submit_balance,
        ).pack(pady=10)

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
        Processes the next entry in the log queue, renders it, and schedules
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
        given message, then scrolls the log canvas to the bottom.

        Args:
            text (str): The message text to display.
            round_start (bool): Applies round-start background colour.
            is_win (bool): Applies win background colour.
            is_loss (bool): Applies loss background colour.
            is_push (bool): Applies push background colour.
        """
        label = Label(
            self.log_frame,
            text=text,
            font=self.styles["text"],
            bg=(
                self.colour_scheme["start_bg"]
                if round_start
                else (
                    self.colour_scheme["win_bg"]
                    if is_win
                    else (
                        self.colour_scheme["loss_bg"]
                        if is_loss
                        else (
                            self.colour_scheme["tie_bg"]
                            if is_push
                            else self.colour_scheme["log_bg"]
                        )
                    )
                )
            ),
            fg=(
                self.colour_scheme["start_fg"]
                if round_start
                else (
                    self.colour_scheme["win_fg"]
                    if is_win
                    else (
                        self.colour_scheme["loss_fg"]
                        if is_loss
                        else (
                            self.colour_scheme["tie_bg"]
                            if is_push
                            else self.colour_scheme["log_fg"]
                        )
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
            float: The current balance, or 0 if an error occurred.
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
            return 0  # In order to prevent errors regarding 'None' errors in mathematical operations.

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

                self.admin_modify_bet(self.wj_root)
                return True

            else:
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is now £0. Returning to menu.",
                )
                self.return_to_menu()
                return False
        return True

    def modify_user_balance(self, balance: int):
        """
        Updates the user's balance in the database, refreshes the balance
        label in the UI, and logs the new balance to the game log.

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

        self.check_balance()

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

        # Create and shuffle a new deck at the start of each round
        self.deck = CasinoDeckManager(shuffle=True, game_mode="blackjack")
        self.log_message(text="The deck is being shuffled...")

        # Deal cards
        self.player_hand.extend([self.deck.draw(1), self.deck.draw(1)])

        if self.deck.blackjack_hand_value(self.player_hand) == 21:
            self.log_message(text="You have been dealt a natural WhiteJoe!")
            balance = self.return_balance()
            balance += int(self.current_bet * 2.5)
            self.modify_user_balance(balance)
            self.end_round(win=True)

        self.dealer_hand.extend([self.deck.draw(1), self.deck.draw(1)])

        self.round_active = True
        self.update_button_states()
        self.logs_after_deal()

    def logs_after_deal(self):
        """
        Logs the initial deal state to the game log: the player's two cards
        and total, the dealer's visible card and its value, and a prompt for
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
        Draws one card for the player, logs the result, and checks for a
        bust. If the player busts, ends the round as a loss. Otherwise logs
        a prompt to continue. Does nothing if no round is active.
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
        Ends the player's turn and triggers dealer resolution. Does nothing
        if no round is active.
        """
        if not self.round_active:
            return

        self.log_message(text="You've chosen to stand.")

        self.resolve_dealer()

    def double_down(self):
        """
        Doubles the current bet (deducting the additional amount from the
        user's balance), draws exactly one card, and resolves the dealer.
        Prevents doubling if the user has insufficient balance. Does nothing
        if no round is active.
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
        the user's balance. Does nothing if no round is active.
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
        Handles WhiteJoe (natural blackjack on first two cards) as a special
        winning case paying 2.5x the bet.
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
            self.log_message(
                text="Did you know that most gambling losses are due to chasing "
                "losses? Remember to gamble responsibly!"
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
        interface. Navigates to Admin_Interface for administrators or
        Casino_Interface for regular users. Optionally displays an error dialog
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

        Casino_Interface(
            administrator=True if self.user_data.get("administrator") else False,
            user_data=self.user_data,
        )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# poker_player_management_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Timeout check: exit Monte Carlo early if no results after this many iterations
TIME_OUT = 1000

# Betting size thresholds by difficulty band
MIN_RAISE_FACTOR_LOW_DIFF = 0.5
MAX_RAISE_FACTOR_LOW_DIFF = 2.0
MIN_RAISE_FACTOR_HIGH_DIFF = 0.75
MAX_RAISE_FACTOR_HIGH_DIFF = 3.0

# Minimum rounds before a player's stored range is used
EXPERIENCE_THRESHOLD = 50

# Default delta for range chart updates
DEFAULT_DELTA = 0.05

# Maximum outs considered when estimating drawing equity
MAX_OUTS = 20

# Fold-bias constants

# At difficulty 0  a bot has a FOLD_BIAS_MAX chance each decision of
# converting a marginal fold into a call.  At difficulty 100 the chance
# drops to FOLD_BIAS_MIN, keeping high-difficulty bots close to optimal.
FOLD_BIAS_MAX = 0.40  # 40% override at difficulty 0
FOLD_BIAS_MIN = 0.04  # 4% override at difficulty 100

# PokerPlayer


class PokerPlayer:
    """
    Represents a poker participant, either a human player or a bot. Human players
    load and persist statistics while bots generate tendencies procedurally
    based on difficulty. Handles range charts and decision-making logic.
    """

    def __init__(self, *, user_id=None, is_bot=False, difficulty=None):
        """
        Initialises a poker player instance, delegating to init_player() for
        human players or init_bot() for AI bots. Sets active_range to a
        copy of base_range after initialisation.

        Args:
            user_id: Database ID for human players.  Required if
                     is_bot=False.
            is_bot (bool): True for AI opponents, False for human players.
                           Defaults to False.
            difficulty (int, optional): Bot difficulty level 0–100.
                                        Required if is_bot=True.

        Raises:
            ValueError: If user_id is missing for a human player, or
                        difficulty is missing for a bot.
        """
        self.user_id = user_id
        self.is_bot = bool(is_bot)
        self.difficulty = difficulty

        # Deck manager used for hand evaluation utilities
        self.dm = CasinoDeckManager(game_mode="poker")

        if not self.is_bot:
            self.init_player()
        else:
            self.init_bot()

        # Active range starts as a session copy of base_range so temporary
        # modifications do not corrupt the persisted range.
        self.active_range = self.base_range.copy()

    # Initialisation helpers

    def init_player(self):
        """
        Initialises a human player by loading their poker data from the
        database. Sets all statistical attributes from the loaded record.
        Uses a default range for inexperienced players (<=50 rounds) while
        preserving the stored range for future updates.

        Raises:
            ValueError: If user_id is not set or poker data cannot be
                        loaded from the database.
        """
        if not self.user_id:
            raise ValueError("user_id is required for human players.")

        self.dbm = DatabaseManagement()

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
            # Inexperienced: use a default range for gameplay but retain
            # the stored range so it is updated correctly in the database.
            self.base_range = generate_range_chart()
            self.stored_range = stored_range if stored_range else generate_range_chart()
        else:
            self.base_range = stored_range if stored_range else generate_range_chart()
            self.stored_range = self.base_range

        self.bot_characteristics = None

    def init_bot(self):
        """
        Initialises an AI bot with synthetically generated tendencies scaled
        by difficulty. Higher difficulty bots are tighter, more aggressive,
        bluff more optimally, and use more Monte Carlo simulations. No
        database interaction occurs.

        Raises:
            ValueError: If difficulty is not set.
        """
        if self.difficulty is None:
            raise ValueError("difficulty is required for bot players.")

        self.dbm = None
        self.record = None

        # Tendency parameters interpolated by difficulty
        self.vpip = difficulty_curve(self.difficulty, 35, 18)
        self.pfr = difficulty_curve(self.difficulty, 10, 20)
        self.aggression_factor = self.pfr / max(1.0, self.vpip)
        self.bluff_freq = difficulty_curve(self.difficulty, 0.15, 0.40)
        self.fold_to_raise = difficulty_curve(self.difficulty, 0.60, 0.30)
        self.call_when_weak = difficulty_curve(self.difficulty, 0.50, 0.20)

        self.base_range = generate_bot_range(self.vpip, self.difficulty)

        self.statistics = {
            "rounds_played": 0,
            "avg_bet_size": 0,
        }

        self.bot_characteristics = BotCharacteristics(self.difficulty)

    # Decision entry point

    def decide(
        self, *, player_hand, community_cards, opponents, pot, to_call, balance, street
    ):
        """
        Makes a poker decision for this player based on the current game
        state by delegating to make_decision().

        Args:
            player_hand (list[str]): The player's two hole cards.
            community_cards (list[str]): The current community cards (0–5).
            opponents (list[PokerPlayer]): The active opponent players.
            pot (float): The current pot size.
            to_call (float): The amount required to call.
            balance (float): The player's remaining chips.
            street (str): The current betting round ('preflop', 'flop',
            'turn', or 'river').

        Returns:
            tuple: One of:
                   - '("fold",)'
                   - '("call",)'
                   - '("raise", amount)'
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

    # State management

    def refresh_from_db(self):
        """
        Reloads all player attributes from the database.  Useful when
        another process has updated the database since this instance was
        initialised.  Does nothing for bots or if the database manager is
        unavailable.
        """
        if self.is_bot or not self.dbm or self.user_id is None:
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
        Should be called between hands to clear any temporary range
        modifications made during a session.
        """
        self.active_range = self.base_range.copy()

    # Introspection

    def fetch_player_info(self):
        """
        Returns a summary dictionary of this player's characteristics and
        statistics.

        Returns:
            dict: Keys — user_id, is_bot, difficulty, vpip, pfr,
                  aggression_factor, bluff_freq, fold_to_raise,
                  call_when_weak, rounds_played, record.
        """
        return {
            "record": self.record,
            "user_id": self.user_id,
            "is_bot": self.is_bot,
            "difficulty": self.difficulty,
            "vpip": self.vpip,
            "pfr": self.pfr,
            "aggression_factor": self.aggression_factor,
            "fold_to_raise": self.fold_to_raise,
            "call_when_weak": self.call_when_weak,
            "rounds_played": self.statistics["rounds_played"],
        }

    def __repr__(self):
        """
        Returns a concise string representation of the player including
        type, identity, and key statistics.
        """
        if self.is_bot:
            return (
                f"PokerPlayer(bot, difficulty={self.difficulty}, "
                f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%)"
            )
        return (
            f"PokerPlayer(user_id={self.user_id}, "
            f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%, "
            f"Rounds Played={self.statistics['rounds_played']})"
        )


# BotCharacteristics


class BotCharacteristics:
    """
    Parameters shaping AI decision-making according to difficulty. Higher
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

        # Accuracy / simulation depth
        self.simulations = int(difficulty_curve(difficulty, 500, 15000))

        # Decision noise (lower = sharper)
        self.noise_level = difficulty_curve(difficulty, 0.30, 0.02)

        # Bluffing
        self.bluff_multiplier = difficulty_curve(difficulty, 0.6, 1.6)

        # Risk appetite
        self.risk_tolerance = difficulty_curve(difficulty, 0.85, 1.5)

        # Minimum Defence Frequency scaling
        self.mdf_threshold = difficulty_curve(difficulty, 0.9, 0.3)

        # Range discipline
        self.range_adherence = difficulty_curve(difficulty, 0.6, 0.95)

        # Fold-bias: easy bots are reluctant to fold; hard bots are rational
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


# Range chart utilities


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
            if i < j:
                hand = r1 + r2 + "s"
            elif i > j:
                hand = r2 + r1 + "o"
            else:
                hand = r1 + r2
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
    difficulty. Higher difficulty produces more nuanced, non-linear hand
    selection via an exponent applied to the strength ranking. The top
    vpip_target percent of hands by adjusted strength are included.

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
    Updates a range chart based on an observed action, then normalises the
    probabilities to sum to 1.0. Raising increases the hand's probability,
    folding decreases it, and calling applies a smaller increase.

    Args:
        chart (dict): Current range chart mapping hand notations to
                      probabilities.
        action (str): Observed action — 'raise', 'call', or 'fold'.
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


# Maths helpers


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
        str: Hand category (e.g. 'Flush', 'Two Pair'), or 'Unknown' on
             evaluation failure.
    """
    dm = CasinoDeckManager(game_mode="poker")
    try:
        return str(dm.evaluate_hand(player_hand, community_cards))
    except Exception as exception:
        print(exception)
        return "Unknown"


# Monte Carlo equity estimation


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
    Estimates the player's equity against a single opponent range via Monte
    Carlo simulation.

    Performance notes:
        - Base deck built once; player and board cards removed once.
        - Each simulation copies the base deck and shuffles the copy.
        - Rank index is pre-built per simulation from remaining cards.
        - Opponent hand drawn from the copy so removals do not accumulate.
        - Early exit if no valid results after TIME_OUT iterations.

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

    sim_count = calculate_simulation_count(
        "river" if len(community_cards) == 5 else "preflop",
        bot.difficulty,
    )

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
        list[int] or None: Two treys card integers, or None.
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

    if suitedness == "s":
        combos = [(c1, c2) for c1 in cards1 for c2 in cards2 if c1[1] == c2[1]]
    else:
        combos = [(c1, c2) for c1 in cards1 for c2 in cards2 if c1[1] != c2[1]]

    if not combos:
        return None

    c1, c2 = random.choice(combos)
    return [dm.str_to_treys(c1), dm.str_to_treys(c2)]


def notation_to_specific_cards(hand_notation, dm):
    """
    Public wrapper: converts a hand notation to treys card integers using
    the cards available in 'dm'.

    Args:
        hand_notation (str): Hand notation string.
        dm (CasinoDeckManager): Deck manager to draw cards from.

    Returns:
        list[int] or None: Two treys card integers, or None if unavailable.
    """
    available = dm.str_deck()
    if not available:
        return None
    rank_index = build_rank_index(available)
    return notation_to_cards_with_index(hand_notation, rank_index, dm)


def calculate_simulation_count(street, difficulty):
    """
    Returns the number of Monte Carlo simulations to run for equity
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
        return 0.0

    joint = 1.0
    for opp_range in opponent_ranges:
        joint *= hand_equity(player_hand, community_cards, opp_range, bot)
    return joint


# Pot-odds and expected value helpers


def pot_odds(current_pot, call_amount):
    """
    Returns the minimum equity required to break even on a call decision.

    Args:
        current_pot (float): Current pot size before the call.
        call_amount (float): Amount required to call.

    Returns:
        float: Required break-even equity (0.0–1.0).  Returns 0.0 if
               call_amount is zero or negative.

    Reference:
        https://upswingpoker.com/pot-odds-step-by-step/
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
    draws, and overcards. Capped at MAX_OUTS.

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

    # Flush draw
    for s in set(suits):
        if suits.count(s) == 4:
            outs += 9

    # Straight draws
    rank_nums = sorted(set(rank_value(r) for r in ranks))
    for combo in combinations(rank_nums, min(4, len(rank_nums))):
        if len(combo) < 4:
            continue
        low, high = min(combo), max(combo)
        if high - low == 3:
            outs += 8  # Open-ended
        elif high - low == 4:
            outs += 4  # Gutshot

    # Overcards
    community_ranks = [c[0] for c in community_cards]
    for card in player_hand:
        if card[0] not in community_ranks:
            outs += 2

    return min(outs, MAX_OUTS)


def probability_to_hit_by_river(outs, cards_remaining, cards_to_come):
    """
    Calculates the probability of hitting at least one out using the
    complement of the cumulative miss probability.

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
    Returns the theoretically optimal bluffing frequency that makes an
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


# Bluffing decisions


def should_bluff_call(pot, to_call, equity, opponent_fold_to_raise, bot):
    """
    Determines whether the bot should call with the intention of bluffing
    on a later street.  More likely when the opponent folds frequently and
    current equity does not already justify a straightforward call.

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
    Determines whether the bot should make a bluff raise.  More likely
    against opponents who fold frequently and when current equity is low.

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


# Raise sizing


def calculate_raise_amount(pot, equity, balance, bot):
    """
    Calculates an appropriate raise amount based on pot size, hand equity,
    available balance, and bot difficulty. High-difficulty bots use larger
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


# Notation helper


def cards_to_notation(player_hand):
    """
    Converts a two-card hole hand into its standard notation string with
    the higher-ranked card first.

    Args:
        player_hand (list[str]): Two card strings in 'Rs' format
                                 (e.g. '['As', 'Kh']').

    Returns:
        str: Notation string — pocket pair (e.g. ''AA''), suited
             (e.g. ''AKs''), or offsuit (e.g. ''AKo'').
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


# Decision function


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
    Makes a poker decision using game-theory principles and opponent
    modelling.

    Each step is applied in order. The first step that produces a
    conclusive action returns immediately.

    **Step 1 — Preflop range check**
        If on the preflop street the bot's hand is not in its assigned
        range it folds (or limps) unless a random roll beats
        '(1 - range_adherence)', in which case it plays the hand as a
        bluff. Hands inside the range continue with a multiplier that
        scales their equity upward.

    **Step 2 — Equity calculation**
        Joint equity against all active opponents is estimated via Monte
        Carlo simulation ('collective_hand_equity'). Noise scaled by
        difficulty is applied, the range multiplier is factored in, and
        risk tolerance scales the result. Low-difficulty bots may further
        misestimate equity by a random factor.

    **Step 3 — Premium river hands (difficulty ≥ 85)**
        At the river, if the bot is highly skilled and holds a Straight
        Flush, Four of a Kind, or Full House with risk tolerance ≥ 1.0 it
        raises immediately.

    **Step 4 — Pot-odds maths**
        Pot-odds required to break even and the expected value of calling
        are computed for use in later steps.

    **Step 5 — Drawing hands (flop / turn only)**
        The number of outs is estimated and converted to a hit probability
        by the river. Equity is updated to the maximum of the Monte Carlo
        estimate and the draw-based estimate.

    **Step 6 — Value raise**
        If equity exceeds 0.65 and the player has chips, a raise is
        calculated and returned.

    **Step 7 — Clear positive-EV call (difficulty ≥ 50)**
        If the expected value of calling is positive the bot calls.

    **Step 8 — Minimum Defence Frequency**
        If equity meets the pot-odds threshold the bot defends at a
        frequency proportional to MDF scaled by 'mdf_threshold'.

    **Step 9 — Bluffing**
        With low equity the bot may attempt a bluff raise or bluff call
        based on opponent fold tendencies and 'bluff_multiplier'.
        Low-difficulty bots may make random bluffing errors.

    **Step 10 — Fold bias (anti-fold nudge)**
        Before the default fold action, a difficulty-scaled 'fold_bias'
        check is performed. If the random roll is below 'bot.fold_bias'
        the bot calls instead of folding.  Easy bots (fold_bias ≈ 0.40)
        are noticeably reluctant to fold; hard bots (fold_bias ≈ 0.04)
        are rarely swayed, keeping their play close to optimal. The bias
        only triggers when the bot can actually afford to call.

    **Step 11 — Default fold**
        If no earlier step returned an action the bot folds.

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
    error_prob = max(0.0, 1.0 - bot.difficulty / 100.0)

    # Step 1: Preflop range check
    if street == "preflop" and player_range is not None:
        hand_notation = cards_to_notation(player_hand)
        hand_strength_in_range = player_range.get(hand_notation, 0.0)

        if hand_strength_in_range == 0.0:
            # Hand not in range — fold unless range deviation roll passes
            if random.random() > (1.0 - bot.range_adherence):
                pass  # Deviate: play as a bluff
            else:
                return ("fold",) if to_call > 0 else ("call",)

        range_multiplier = 0.5 + (hand_strength_in_range * 0.5)
    else:
        hand_notation = None
        hand_strength_in_range = 0.5
        range_multiplier = 1.0

    # Step 2: Equity calculation
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

    # Step 3: Premium river hands (high difficulty only)
    if street == "river":
        hand_type = describe_hand(player_hand, community_cards)
        if bot.difficulty >= 85 and bot.risk_tolerance >= 1.0:
            if hand_type in ("Straight Flush", "Four of a Kind", "Full House"):
                raise_amt = calculate_raise_amount(pot, equity, balance, bot)
                return ("raise", raise_amt)
    else:
        hand_type = None

    # Step 4: Pot-odds maths
    pot_odds_required = pot_odds(pot, to_call)
    ev_call = expected_value_of_call(pot, to_call, equity)

    # Step 5: Drawing logic (flop / turn only)
    if street in ("flop", "turn"):
        outs = estimate_outs(player_hand, community_cards)
        cards_remaining = 52 - len(player_hand) - len(community_cards)
        cards_to_come = 2 if street == "flop" else 1
        draw_equity = probability_to_hit_by_river(outs, cards_remaining, cards_to_come)
        equity = max(equity, draw_equity)

    # Step 6: Value raise with strong hands
    if equity > 0.65 and balance > 0:
        raise_amt = calculate_raise_amount(pot, equity, balance, bot)
        if 0 < raise_amt <= balance:
            return ("raise", raise_amt)

    # Step 7: Clear positive-EV call
    if bot.difficulty >= 50 and ev_call > 0:
        return ("call",)

    # Step 8: Minimum Defence Frequency
    mdf = minimum_defense_frequency(to_call, pot) * bot.mdf_threshold
    if equity >= pot_odds_required:
        mdf_check = mdf
        if random.random() < error_prob:
            mdf_check *= random.uniform(0.3, 0.8)
        if random.random() < mdf_check:
            return ("call",)

    # Step 9: Bluffing logic
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
    elif 0.2 < equity < 0.5:
        if should_bluff_call(pot, to_call, equity, avg_fold_to_raise, bot):
            should_attempt_bluff = True
            bluff_action = "call"

    # Low-difficulty bots make random bluffing errors
    if random.random() < error_prob:
        should_attempt_bluff = random.choice([True, False])
        bluff_action = random.choice(["raise", "call"])

    if should_attempt_bluff:
        if bluff_action == "raise":
            raise_amt = calculate_raise_amount(pot, equity, balance, bot)
            return ("raise", raise_amt if raise_amt <= balance else int(balance))
        elif bluff_action == "call" and to_call <= balance:
            return ("call",)

    # Step 10: Fold bias — difficulty-scaled anti-fold nudge
    # All bots have a small tendency to call rather than fold in marginal
    # spots. The bias is much stronger for easy bots (who play too loose)
    # and diminishes toward the threshold FOLD_BIAS_MIN for hard bots.
    # Only applied when the bot can actually afford the call.
    if to_call <= balance and random.random() < bot.fold_bias:
        return ("call",)

    # Step 11: Default action — fold
    return ("fold",)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# harrogate_hold_em_V6.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Bot roster

DEFAULT_BOT_ROSTER = [
    "Angus",
    "Angeban",
    "Grey",
    "Mr Rhodes",
    "Leon S. Kennedy",
    "Albert Wesker",
    "Sauron",
    "Morgoth",
    "Han Solo",
]


# Tournament win-criteria constants


WIN_CRITERIA_ELIMINATE_ALL = "eliminate_all"
WIN_CRITERIA_EARN_TARGET = "earn_target"
WIN_CRITERIA_SURVIVE_ROUNDS = "survive_rounds"
WIN_CRITERIA_LAST_MAN_BLIND = "last_man_blind"


# TournamentManager


class TournamentManager:
    """
    Manages multi-round tournaments for Harrogate Hold 'Em.

    Stores settings such as rounds, player count and win criteria, and
    tracks progression, blinds and results.

    Attributes:
        total_rounds (int): Total rounds in the tournament.
        total_players (int): Total player count (human player + bots).
        win_criteria (str): Active win-criteria key constant.
        target_amount (int): Chip target for WIN_CRITERIA_EARN_TARGET.
        base_small_blind (int): Starting small blind before escalation.
        base_big_blind (int): Starting big blind before escalation.
        current_round (int): The current round number (1-indexed).
        rounds_survived (int): How many rounds the human player has survived.
        human_chips_at_round_start (int): Human's chip count at the start
                                          of the current round.
        round_wins (int): Number of rounds the human player has won.
        tournament_over (bool): True once the tournament has concluded.
        tournament_won (bool): True if the human player won the tournament.
    """

    def __init__(self, settings):
        """
        Initialises TournamentManager from the casino settings dictionary.

        Args:
            settings (dict): Casino settings dict. Keys read:
                             tournament_rounds, tournament_players,
                             win_criteria, win_criteria_target,
                             small_blind, big_blind.
        """
        self.total_rounds = settings.get("tournament_rounds", 5)
        self.total_players = settings.get("tournament_players", 4)
        self.win_criteria = settings.get("win_criteria", WIN_CRITERIA_ELIMINATE_ALL)
        self.target_amount = settings.get("win_criteria_target", 1000)

        self.base_small_blind = settings.get("small_blind", 50)
        self.base_big_blind = settings.get("big_blind", 100)

        self.current_round = 1
        self.rounds_survived = 0
        self.human_chips_at_round_start = 0
        self.round_wins = 0
        self.tournament_over = False
        self.tournament_won = False

    # Blind escalation properties

    @property
    def current_small_blind(self):
        """
        Returns the small blind for the current round. For
        WIN_CRITERIA_LAST_MAN_BLIND the blind doubles every round; all
        other modes escalate by 50 % every three rounds.

        Returns:
            int: The current small blind amount.
        """
        if self.win_criteria == WIN_CRITERIA_LAST_MAN_BLIND:
            return self.base_small_blind * (2 ** (self.current_round - 1))
        escalation = max(1, (self.current_round - 1) // 3)
        return int(self.base_small_blind * (1.5**escalation))

    @property
    def current_big_blind(self):
        """
        Returns the big blind for the current round using the same
        escalation logic as current_small_blind.

        Returns:
            int: The current big blind amount.
        """
        if self.win_criteria == WIN_CRITERIA_LAST_MAN_BLIND:
            return self.base_big_blind * (2 ** (self.current_round - 1))
        escalation = max(1, (self.current_round - 1) // 3)
        return int(self.base_big_blind * (1.5**escalation))

    # State mutators

    def record_round_start(self, human_balance):
        """
        Snapshots the human player's chip count at the beginning of a round
        for later reference (e.g. earn_target delta calculations).

        Args:
            human_balance (int): The human player's current chip balance.
        """
        self.human_chips_at_round_start = human_balance

    def evaluate_round_win(self, human_player, all_players):
        """
        Checks whether the human player has satisfied the active win criteria
        for the round that just completed.

        Args:
            human_player (dict): The human player dictionary.
            all_players (list[dict]): All player dictionaries in the game.

        Returns:
            bool: True if the human player has won this round.
        """
        if self.win_criteria == WIN_CRITERIA_ELIMINATE_ALL:
            active_bots = [
                p
                for p in all_players
                if p["is_bot"] and p["status"] not in ("Folded", "OUT")
            ]
            return len(active_bots) == 0

        if self.win_criteria == WIN_CRITERIA_EARN_TARGET:
            return human_player["balance"] >= self.target_amount

        if self.win_criteria in (
            WIN_CRITERIA_SURVIVE_ROUNDS,
            WIN_CRITERIA_LAST_MAN_BLIND,
        ):
            return human_player["status"] != "OUT"

        return False

    def advance_round(self, human_won_round):
        """
        Advances the tournament state after a round ends, updating win and
        survival counters and checking for tournament completion.

        Args:
            human_won_round (bool): Whether the human player met the win criteria
                                    for the round that just finished.

        Returns:
            dict: A result dictionary with keys:
                  - 'tournament_over' (bool)
                  - 'tournament_won' (bool)
                  - 'message' (str) — outcome message.
        """
        if human_won_round:
            self.round_wins += 1
        self.rounds_survived += 1
        self.current_round += 1

        if self.current_round > self.total_rounds:
            self.tournament_over = True
            self.tournament_won = self.round_wins > 0
            msg = (
                f"Tournament complete!\n"
                f"You won {self.round_wins} of {self.total_rounds} rounds.\n"
            )
            msg += (
                "🏆 Tournament Victory!"
                if self.tournament_won
                else "Better luck next time."
            )
            return {
                "tournament_over": True,
                "tournament_won": self.tournament_won,
                "message": msg,
            }

        criteria_desc = {
            WIN_CRITERIA_ELIMINATE_ALL: "Eliminate all opponents",
            WIN_CRITERIA_EARN_TARGET: f"Earn £{self.target_amount}",
            WIN_CRITERIA_SURVIVE_ROUNDS: "Survive the round",
            WIN_CRITERIA_LAST_MAN_BLIND: "Survive as blinds escalate",
        }.get(self.win_criteria, "")

        msg = (
            f"Round {self.current_round - 1} complete.  "
            f"{'Round won! ✓' if human_won_round else 'Round lost.'}\n"
            f"Round {self.current_round} of {self.total_rounds}.\n"
            f"Win criteria: {criteria_desc}\n"
            f"Blinds: £{self.current_small_blind} / £{self.current_big_blind}"
        )
        return {
            "tournament_over": False,
            "tournament_won": False,
            "message": msg,
        }

    def fetch_status_text(self):
        """
        Returns a single-line status string suitable for display in the
        tournament status label during active gameplay.

        Returns:
            str: Status text describing round, wins, and current blinds.
        """
        if not self.tournament_over:
            return (
                f"Tournament  |  Round {self.current_round}/{self.total_rounds}  |  "
                f"Wins: {self.round_wins}  |  "
                f"Blinds: £{self.current_small_blind} / £{self.current_big_blind}"
            )
        return f"Tournament Over  |  Wins: {self.round_wins}/{self.total_rounds}"


# HarrogateHoldEm


class HarrogateHoldEm:
    """
    GUI implementation of Harrogate Hold 'Em poker. Handles game flow,
    bot interactions, tournament management and logging. Runs its own
    tkinter mainloop and returns to the menu on exit.
    """

    def __init__(self, user_data, settings, bots):
        """
        Initialises the Harrogate Hold 'Em window, game state, player list
        (human player + bots), UI layout, and the background bot-decision queue
        checker.

        Args:
            user_data (dict): Must contain at minimum:
                              'username' (str), 'user_id',
                              'administrator' (bool).
            settings (dict): Game configuration.  Keys used:
                             'bot_count', 'bot_balance',
                             'small_blind', 'big_blind',
                             'bot_difficulty', 'tournament_mode',
                             'tournament_rounds', 'tournament_players',
                             'win_criteria', 'win_criteria_target'.
            bots (list or None): List of '[name, difficulty]' pairs for
                                 bot opponents.  If None, bots are
                                 auto-generated from settings and
                                 DEFAULT_BOT_ROSTER.
        """
        self.user_data = user_data

        self.hhe_root = Tk()
        self.hhe_root.title("One More Time Casino — Harrogate Hold 'Em")
        try:
            self.hhe_root.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            self.hhe_root.state("zoomed")  # Windows
        except Exception:
            pass

        # Log queue
        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        # Bot decision queue
        self.bot_decision_queue = Queue()
        self.bot_thinking = False

        self.dbm = DatabaseManagement()

        if not self.dbm.check_user_poker_data_exists(user_data["user_id"]):
            self.dbm.initialise_user_poker_data(user_data["user_id"])

        self.styles = fetch_font_settings(self.hhe_root)

        # Auto-generate bots if not supplied
        if bots is None:
            bot_count = settings.get("bot_count", 3)
            difficulty = settings.get("bot_difficulty", 50)
            roster = list(DEFAULT_BOT_ROSTER)
            random.shuffle(roster)
            bots = [
                [roster[index % len(roster)], difficulty] for index in range(bot_count)
            ]

        # Tournament setup
        self.tournament_mode = settings.get("tournament_mode", False)
        if self.tournament_mode:
            self.tournament = TournamentManager(settings)
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind
        else:
            self.tournament = None
            self.small_blind_value = settings.get("small_blind", 50)
            self.big_blind_value = settings.get("big_blind", 100)

        # Build bot lookup
        self.bots = {}
        for index, bot in enumerate(bots[: settings.get("bot_count", len(bots))]):
            self.bots[index] = {"name": bot[0], "difficulty": bot[1]}

        # Build player list
        self.players = []

        player_model = None
        if self.user_data.get("user_id"):
            try:
                player_model = PokerPlayer(
                    user_id=self.user_data["user_id"], is_bot=False
                )
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
                "balance": self.return_balance(),
                "bet": 0,
                "status": "Waiting",
                "is_bot": False,
                "user_id": self.user_data["user_id"],
                "model": player_model,
            }
        )

        self.current_round_number = 1
        self.actions_logged = []

        for index in range(settings.get("bot_count", len(self.bots))):
            self.players.append(
                {
                    "player": self.bots[index]["name"],
                    "position": None,
                    "cards": [],
                    "balance": settings.get("bot_balance", 1000),
                    "bet": 0,
                    "status": "Waiting",
                    "is_bot": True,
                    "user_id": None,
                    "model": PokerPlayer(
                        is_bot=True, difficulty=max(0, self.bots[index]["difficulty"])
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

        self.main_frame = Frame(self.hhe_root)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.action_buttons = []

        # AFTER
        self.colour_scheme = {
            # Left-hand panels
            "top_left_bg": "#252525",
            "bottom_left_bg": "#1e1e1e",
            # Right-hand panels
            "top_right_bg": "#2e7d73",
            "middle_right_bg": "#286b62",
            "bottom_right_bg": "#5b2a3c",
            # Widgets
            "widget_bg": "#6a2e4f",
            "text_bg": "#1a1a1a",
            "text_fg": "#e8e8e8",
            "left_fg": "#e8e8e8",
            # Log panel
            "log_bg": "#1a1a1a",
            "log_fg": "#cfcfcf",
            # Log entry
            "start_bg": "#243b7a",
            "start_fg": "#ffffff",
            "win_bg": "#244d3a",
            "win_fg": "#a8e6c1",
            "loss_bg": "#4a1e1e",
            "loss_fg": "#f2a3a3",
            "tie_bg": "#5c4a10",
            "tie_fg": "#f0d898",
            "thinking_bg": "#3c2a4a",
            "thinking_fg": "#d4b8e8",
            "tournament_bg": "#4a1e38",
            "tournament_fg": "#e8b8d0",
        }

        set_view(self, self.harrogate_hold_em_screen)
        self.check_bot_decision_queue()

    # Public entry point

    def run(self):
        """
        Starts the tkinter main event loop for the Harrogate Hold 'Em window.
        """
        self.hhe_root.mainloop()

    # Main screen layout

    def harrogate_hold_em_screen(self, frame):
        """
        Builds the main five-panel game layout using a grid:

        - Top-left: game state labels (round, board, blinds, pot, turn,
          tournament status).
        - Bottom-left: scrollable colour-coded game log.
        - Top-right: user information, balance, and Return to Menu button.
        - Middle-right: scrollable players list.
        - Bottom-right: bet entry controls and action buttons.

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        cs = self.colour_scheme

        frame.columnconfigure(0, weight=2)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        # Top-left
        top_left = Frame(frame, bd=2, relief="sunken", bg=cs["top_left_bg"])
        top_left.grid(column=0, row=0, sticky="nsew", padx=5, pady=5)

        self.round_number_label = Label(
            top_left,
            bg=cs["top_left_bg"],
            fg=cs["left_fg"],
            anchor="w",
            font=self.styles["text"],
        )
        self.round_number_label.pack(fill="x", padx=10, pady=5)

        self.board_label = Label(
            top_left,
            bg=cs["top_left_bg"],
            fg=cs["left_fg"],
            anchor="w",
            font=self.styles["text"],
        )
        self.board_label.pack(fill="x", padx=10, pady=5)

        self.player_blinds_label = Label(
            top_left,
            bg=cs["top_left_bg"],
            fg=cs["left_fg"],
            anchor="w",
            font=self.styles["text"],
        )
        self.player_blinds_label.pack(fill="x", padx=10, pady=5)

        self.pot_size_label = Label(
            top_left,
            bg=cs["top_left_bg"],
            fg=cs["left_fg"],
            anchor="w",
            font=self.styles["text"],
        )
        self.pot_size_label.pack(fill="x", padx=10, pady=5)

        self.player_turn_label = Label(
            top_left,
            bg=cs["top_left_bg"],
            fg=cs["left_fg"],
            anchor="w",
            font=self.styles["text"],
        )
        self.player_turn_label.pack(fill="x", padx=10, pady=5)

        self.tournament_label = Label(
            top_left,
            font=self.styles["emphasis"],
            bg=cs["tournament_bg"],
            fg=cs["tournament_fg"],
            pady=4,
            padx=6,
        )
        if self.tournament_mode:
            self.tournament_label.pack(fill="x", padx=10, pady=4)

        # Bottom-left
        bottom_left = Frame(frame, bd=2, relief="sunken", bg=cs["bottom_left_bg"])
        bottom_left.grid(column=0, row=1, rowspan=2, sticky="nsew", padx=5, pady=5)

        self.log_canvas = Canvas(
            bottom_left, bg=cs["bottom_left_bg"], highlightthickness=0
        )
        log_sb = Scrollbar(
            bottom_left, orient="vertical", command=self.log_canvas.yview
        )
        self.log_canvas.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_canvas.pack(side="left", fill="both", expand=True)

        self.log_frame = Frame(self.log_canvas, bg=cs["bottom_left_bg"])
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

        # Top-right
        top_right = Frame(frame, bd=2, relief="sunken", bg=cs["top_right_bg"])
        top_right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        Button(
            top_right,
            text="Return to Menu",
            font=self.styles["button"],
            bg=cs["widget_bg"],
            fg=cs["text_fg"],
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.return_to_menu,
        ).pack(pady=5)

        balance = 0
        if not self.user_data.get("administrator"):
            balance_data = self.dbm.fetch_user_balance(self.user_data["username"])
            if not balance_data["found"]:
                self.return_to_menu(
                    is_error=True,
                    error=Exception("User not found in database."),
                )
                return
            balance = balance_data["balance"]
        else:
            self.admin_modify_bet(frame)

        labels = []
        for text in (
            f"Username: {self.user_data['username']}",
            f"Balance: £{balance}",
            "Current Bet: £0",
            f"Blinds: £{self.small_blind_value} / £{self.big_blind_value}",
        ):
            label = Label(
                top_right,
                text=text,
                font=self.styles["text"],
                bg=cs["top_right_bg"],
                fg=cs["text_fg"],
                anchor="w",
            )
            label.pack(anchor="w", pady=5, padx=5)
            labels.append(label)

        self.balance_label = cast(Label, labels[1])
        self.current_bet_label = cast(Label, labels[2])
        self.blinds_label = cast(Label, labels[3])

        # Middle-right
        mid_right = Frame(frame, bd=2, relief="sunken", bg=cs["middle_right_bg"])
        mid_right.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        mid_right.columnconfigure(0, weight=1)
        mid_right.columnconfigure(1, weight=0)
        mid_right.rowconfigure(0, weight=1)

        self.players_canvas = Canvas(
            mid_right, bg=cs["middle_right_bg"], highlightthickness=0
        )
        self.players_canvas.grid(row=0, column=0, sticky="nsew")

        players_sb = Scrollbar(
            mid_right, orient="vertical", command=self.players_canvas.yview
        )
        players_sb.grid(row=0, column=1, sticky="ns")
        self.players_canvas.configure(yscrollcommand=players_sb.set)

        self.players_frame = Frame(self.players_canvas, bg=cs["middle_right_bg"])
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

        self.build_players_panel()

        # Bottom-right
        bot_right = Frame(frame, bd=2, relief="sunken", bg=cs["bottom_right_bg"])
        bot_right.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)

        # Functions for user bet adjustment
        def adjust_current_bet(amount):
            try:
                value = int(self.bet_var.get())
            except Exception:
                value = 0
            value += amount
            balance = self.return_balance()
            if balance is not None:
                value = max(1, min(value, int(balance)))
            self.bet_var.set(str(value))
            self.current_bet_label.config(text=f"Current Bet: £{value}")
            self.update_button_states()

        def check_bet_input(*_):
            raw = self.bet_var.get()
            if raw in ("", "-"):
                self.current_bet_label.config(text="Current Bet: £0")
                self.start_button.config(state="disabled")
                return

            digits_only = "".join(c for c in raw if c.isdigit())
            if digits_only != raw:
                self.bet_var.set(digits_only if digits_only else "0")
                return
            try:
                value = int(digits_only) if digits_only else 0
            except Exception:
                value = 0

            balance = self.return_balance()
            if balance is not None:
                value = min(value, int(balance))
            self.current_bet_label.config(text=f"Current Bet: £{value}")
            self.update_button_states()

        self.bet_var = StringVar(value="0")
        self.bet_var.trace_add("write", check_bet_input)

        Entry(
            bot_right,
            textvariable=self.bet_var,
            width=12,
            font=self.styles["text"],
            bg=cs["widget_bg"],
            fg=cs["text_fg"],
            insertbackground=cs["text_fg"],
            relief="flat",
            bd=4,
            justify="center",
        ).pack(pady=(8, 6))

        for inc in (10, 100, 1000):
            row_f = Frame(
                bot_right,
                bg=cs["text_bg"],
                bd=2,
                relief="ridge",
                padx=6,
                pady=3,
            )
            row_f.pack(fill="x", pady=3)

            Button(
                row_f,
                text="+",
                font=self.styles["button"],
                width=3,
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                cursor="hand2",
                command=lambda v=inc: adjust_current_bet(v),
            ).pack(side="left", padx=4)

            Label(
                row_f,
                text=str(inc),
                font=self.styles["text"],
                bg=cs["text_bg"],
                fg=cs["text_fg"],
                width=8,
                anchor="center",
            ).pack(side="left", expand=True)

            Button(
                row_f,
                text="−",
                font=self.styles["button"],
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                width=3,
                cursor="hand2",
                command=lambda v=-inc: adjust_current_bet(v),
            ).pack(side="right", padx=4)

        for text, command in (
            ("Raise", self.raise_bet),
            ("Call", self.call),
            ("Fold", self.fold),
        ):
            button = Button(
                bot_right,
                text=text,
                font=self.styles["button"],
                bg=cs["widget_bg"],
                fg=cs["text_fg"],
                relief="flat",
                bd=0,
                width=18,
                cursor="hand2",
                command=command,
                state="disabled",
            )
            button.pack(pady=6)
            self.action_buttons.append(button)

        self.start_button = Button(
            bot_right,
            text=f"Start Round {self.round_number}",
            font=self.styles["button"],
            bg=cs["start_bg"],
            fg=cs["start_fg"],
            relief="flat",
            bd=0,
            width=18,
            activebackground="#3a52a0",
            cursor="hand2",
            command=self.check_round,
        )
        self.start_button.pack(pady=10)

        self.update_labels()
        self.update_button_states()

    # Players panel helper

    def build_players_panel(self):
        """
        Rebuilds the players list panel from scratch inside self.players_frame.
        Displays for each player: name with position indicators ([SB], [BB],
        current-turn arrow <), hole cards (visible for the human player and at
        showdown; face-down [?] [?] for bots otherwise), chip balance,
        current-round bet, and status string.

        Called both on initial layout and by update_player_status() on every
        refresh so that styling is always consistent.
        """
        cs = self.colour_scheme

        for widget in self.players_frame.winfo_children():
            widget.destroy()

        Label(
            self.players_frame,
            text="Players",
            font=self.styles["subheading"],
            bg=cs["middle_right_bg"],
            fg=cs["text_fg"],
        ).pack(anchor="w", padx=8, pady=(6, 10))

        Frame(self.players_frame, height=1, bg=cs["widget_bg"]).pack(
            fill="x", padx=8, pady=2
        )

        for player in self.players:
            row_f = Frame(self.players_frame, bg=cs["middle_right_bg"])
            row_f.pack(fill="x", padx=8, pady=4)

            left_f = Frame(row_f, bg=cs["middle_right_bg"])
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

            Label(
                left_f,
                text=player["player"] + pos_text,
                font=self.styles["text"],
                bg=cs["middle_right_bg"],
                fg=cs["text_fg"],
                anchor="w",
                wraplength=180,
            ).pack(fill="x")

            if self.round_active and player["cards"]:
                if not player["is_bot"] or self.street == "showdown":
                    cards_text = (
                        " ".join(player["cards"][1]) if len(player["cards"]) > 1 else ""
                    )
                    if cards_text:
                        Label(
                            left_f,
                            text=f"Cards:  {cards_text}",
                            font=self.styles["text"],
                            bg=cs["middle_right_bg"],
                            fg=cs["text_fg"],
                            anchor="w",
                        ).pack(fill="x")
                else:
                    Label(
                        left_f,
                        text="Cards:  [?]  [?]",
                        font=self.styles["text"],
                        bg=cs["middle_right_bg"],
                        fg=cs["text_fg"],
                        anchor="w",
                    ).pack(fill="x")

            right_f = Frame(row_f, bg=cs["middle_right_bg"])
            right_f.pack(side="right")

            Label(
                right_f,
                text=f"£{player['balance']}",
                font=self.styles["text"],
                bg=cs["middle_right_bg"],
                fg=cs["text_fg"],
                anchor="e",
                width=8,
            ).pack(anchor="e")

            if player["bet"] > 0:
                Label(
                    right_f,
                    text=f"Bet:  £{player['bet']}",
                    font=self.styles["text"],
                    bg=cs["middle_right_bg"],
                    fg=cs["text_fg"],
                    anchor="e",
                ).pack(anchor="e")

            Label(
                right_f,
                text=player["status"],
                font=self.styles["text"],
                bg=cs["middle_right_bg"],
                fg=cs["text_fg"],
                anchor="e",
            ).pack(anchor="e")

            Frame(self.players_frame, height=1, bg=cs["widget_bg"]).pack(
                fill="x", padx=8, pady=2
            )

    # UI update helpers

    def update_ui(self):
        """
        Convenience wrapper that refreshes all three UI components —
        labels, button states, and the players list panel — in one call.
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

        self.balance_label.config(text=f"Balance: £{self.return_balance()}")

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
                + ("  —  TOURNAMENT" if self.tournament_mode else "")
            )
            if self.tournament_mode and self.tournament:
                board_text = (
                    f"Tournament Round "
                    f"{self.tournament.current_round}/"
                    f"{self.tournament.total_rounds}"
                )
            else:
                board_text = "Casual mode."
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
            flop_cards = self.flop[1] if isinstance(self.flop, list) else []
            turn_cards = self.turn[1] if isinstance(self.turn, list) else []
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
                raise_state = "normal" if min_raise <= human["balance"] else "disabled"
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

    def update_player_status(self):
        """
        Refreshes the players list panel by delegating to _build_players_panel().
        Kept as a separate method so external callers continue to work
        without change.
        """
        self.build_players_panel()

    # Player helpers

    def reset_players(self):
        """
        Prepares all players for a new round by clearing their hole cards,
        resetting bets to zero, and restoring status to 'Waiting'.
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
                converts and stores them via deck.treys_other().
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
            player["cards"] = self.deck.treys_other(cards) if cards else cards
        if change_balance is not None:
            player["balance"] += change_balance
        if bet is not None:
            player["bet"] = bet
        if status is not None:
            player["status"] = status
        if refresh_player_model and not player["is_bot"] and player["model"]:
            player["model"].refresh_from_db()
            player["model"].reset_active_range()

    def player_decision(self):
        """
        Enables the human player's action buttons and refreshes the UI,
        signalling that it is the human's turn to act.

        This is a utility stub; calling decisions() will also trigger the
        same state when it reaches the human player.
        """
        self.player_turn = True
        self.update_ui()

    # Admin helper

    def admin_modify_bet(self, frame):
        """
        Opens a modal Toplevel dialog that allows the administrator to set
        a custom starting chip balance. The dialog cannot be dismissed
        via the window manager — a valid balance must be submitted.

        On submission, updates the balance label and persists the new
        balance to the database.

        Args:
            frame: The parent widget used to position the Toplevel.
        """
        balance_window = Toplevel(frame)
        balance_window.title("Set Starting Balance")
        balance_window.grab_set()
        balance_window.protocol("WM_DELETE_WINDOW", lambda: None)
        balance_window.configure(bg=self.colour_scheme["left_bg"])
        try:
            balance_window.attributes("-zoomed", True)  # MacOS/Linux
        except Exception:
            pass
        try:
            balance_window.state("zoomed")  # Windows
        except Exception:
            pass

        Label(
            balance_window,
            text="Enter starting balance (£):",
            font=self.styles["text"],
            bg=self.colour_scheme["left_bg"],
            fg=self.colour_scheme["text_fg"],
        ).pack(pady=8)

        balance_entry = Entry(
            balance_window,
            width=20,
            font=self.styles["text"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            insertbackground=self.colour_scheme["text_fg"],
        )
        balance_entry.pack(pady=5)

        def submit_balance():
            """Validates the entry, updates the UI and database, and closes
            the dialog. Shows an error on invalid input."""
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()
                self.balance_label.config(text=f"Balance: £{balance}")
                balance_window.destroy()
                self.dbm.modify_user_balance(self.user_data["username"], balance)
            except Exception:
                messagebox.showerror(text="Please enter a valid positive integer.")

        Button(
            balance_window,
            text="Submit",
            font=self.styles["button"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            relief="flat",
            bd=0,
            command=submit_balance,
        ).pack(pady=10)

        def submit_balance():
            """
            Validates the entered balance as a non-negative integer, updates
            the balance label and database, and closes the dialog. Displays
            an error message if the value is invalid.
            """
            try:
                balance = int(balance_entry.get().strip())
                if balance < 0:
                    raise ValueError()

                self.balance_label.config(text=f"Balance: £{balance}")
                balance_window.destroy()

                self.dbm.modify_user_balance(self.user_data["username"], balance)

            except Exception:
                messagebox.showerror(text="Please enter a valid positive number.")

        Button(
            balance_window,
            text="Submit",
            font=self.styles["button"],
            command=submit_balance,
        ).pack(pady=10)

    # Logging

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
        Pops and renders the next entry from the log queue, then schedules
        itself to run again after log_delay_ms milliseconds.  Stops when
        the queue is empty or the log frame has been destroyed.
        """
        if not getattr(self, "log_frame", None) or not self.log_frame.winfo_exists():
            self.log_queue.clear()
            self.log_active = False
            return

        if not self.log_queue:
            self.log_active = False
            return

        self.log_active = True
        item = self.log_queue.pop(0)

        # Accept both 6-tuple and 7-tuple entries
        if len(item) == 6:
            text, round_start, is_win, is_loss, tie, is_thinking = item
            is_tournament = False
        else:
            text, round_start, is_win, is_loss, tie, is_thinking, is_tournament = item

        self.render_log(
            text, round_start, is_win, is_loss, tie, is_thinking, is_tournament
        )
        self.hhe_root.after(self.log_delay_ms, self.process_log_queue)

    def render_log(
        self, text, round_start, is_win, is_loss, tie, is_thinking, is_tournament=False
    ):
        """
        Creates and packs a colour-coded Label into the log frame for the
        given message, then scrolls the log canvas to the bottom.  Guards
        against rendering into a destroyed frame.

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

        cs = self.colour_scheme
        bg = (
            cs["tournament_bg"]
            if is_tournament
            else (
                cs["start_bg"]
                if round_start
                else (
                    cs["win_bg"]
                    if is_win
                    else (
                        cs["loss_bg"]
                        if is_loss
                        else (
                            cs["tie_bg"]
                            if tie
                            else cs["thinking_bg"] if is_thinking else cs["log_bg"]
                        )
                    )
                )
            )
        )
        fg = (
            cs["tournament_fg"]
            if is_tournament
            else (
                cs["start_fg"]
                if round_start
                else (
                    cs["win_fg"]
                    if is_win
                    else (
                        cs["loss_fg"]
                        if is_loss
                        else (
                            cs["tie_fg"]
                            if tie
                            else cs["thinking_fg"] if is_thinking else cs["log_fg"]
                        )
                    )
                )
            )
        )

        Label(
            self.log_frame,
            text=text,
            font=self.styles["text"],
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

    # Balance & database helpers

    def return_balance(self):
        """
        Retrieves the human player's current chip balance from the database.
        Redirects to the main menu with an error if the user is not found
        or the balance is None.

        Returns:
            int: The current balance, or 0 as a safe fallback.
        """
        data = self.dbm.fetch_user_balance(self.user_data["username"])
        if not data["found"]:
            self.return_to_menu(
                is_error=True, error=Exception("User not found in database.")
            )
            return 0
        if data["balance"] is None:
            self.return_to_menu(
                is_error=True,
                error=Exception("Fetched balance returned None."),
            )
            return 0
        return int(data["balance"])

    def check_balance(self, frame):
        """
        Checks whether the human player's balance has reached zero.

        For administrators, opens the balance modification dialog so they
        can set a new balance and continue. For regular users, displays
        an informational message and returns them to the main menu.

        Args:
            frame: Parent widget passed to admin_modify_bet if needed.

        Returns:
            bool: True if the player can continue, False if they have been
                  returned to the menu.
        """
        if self.return_balance() == 0:
            if self.user_data.get("administrator"):
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance is £0. As an administrator you may "
                    "set a new balance to continue.",
                )
                self.admin_modify_bet(frame)
                return True
            else:
                messagebox.showinfo(
                    "Balance Depleted",
                    "Your balance has reached £0.  "
                    "You will be returned to the main menu.",
                )
                self.return_to_menu()
                return False
        return True

    def modify_user_balance(self, balance):
        """
        Persists a new chip balance for the human player to the database
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
        to the database, and appends it to the in-memory actions_logged
        list for end-of-round statistics aggregation.

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

    # Round management

    def check_round(self):
        """
        Initiates a new round. Clears any pending log entries, resets
        action tracking, logs the round-start message, resets player
        states, refreshes the UI, and delegates to play_round().
        """
        self.round_active = True
        self.log_queue.clear()
        self.log_active = False
        self.actions_logged = []

        self.log_message(f"Starting Round {self.round_number}.", round_start=True)
        self.reset_players()
        self.update_ui()
        self.play_round()

    def blind_management(self):
        """
        Assigns small blind, big blind, and first-action positions for
        the current round. Skips players with 'OUT' status when
        rotating.

        Posts the blinds by deducting from player balances (capped at
        each player's available balance to prevent negative chips),
        adding the amounts to the pot, and setting current_bet to the
        big blind amount.
        """
        # Advance dealer button each round for proper rotation
        self.initial_position = (self.initial_position + 1) % self.player_count

        # Small blind: first active player after dealer
        for attempt in range(self.player_count):
            index = (self.initial_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.small_blind_position = index
                self.small_blind_player = self.players[index]
                break

        # Big blind: first active player after small blind
        for attempt in range(self.player_count):
            index = (self.small_blind_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.big_blind_position = index
                self.big_blind_player = self.players[index]
                break

        # Action starts: first active player after big blind
        for attempt in range(self.player_count):
            index = (self.big_blind_position + 1 + attempt) % self.player_count
            if self.players[index]["status"] != "OUT":
                self.current_position = index
                break

        self.action_position = self.current_position

        # Post blinds
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
        Creates a freshly shuffled deck, deals two hole cards to each
        active (non-OUT) player, then deals and stores five community
        cards split into flop (3), turn (1), and river (1) components.
        """
        self.deck = CasinoDeckManager(shuffle=True, game_mode="poker")

        for player in self.players:
            if player["status"] != "OUT":
                self.modify_player(player, cards=[self.deck.draw(1), self.deck.draw(1)])

        raw_board = [self.deck.draw(1) for _ in range(5)]
        self.board = self.deck.treys_other(raw_board)

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
        """
        Executes a complete poker round: updates blinds from the
        TournamentManager if active, records the tournament round-start
        snapshot, posts blinds, deals cards, logs the human player's hole
        cards, refreshes the UI, and begins the street sequence at
        preflop.
        """
        if self.tournament_mode and self.tournament:
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind

            human_index = linear_search(self.players, "is_bot", False)
            human = self.players[human_index] if human_index != -1 else None
            if human:
                self.tournament.record_round_start(human["balance"])

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

    # Betting & decision loop

    def decisions(self):
        """
        Processes decisions for all players who still need to act on the
        current street. Iterates from current_position, skipping players
        who have already decided, folded, or are out.

        For bot players, launches an asynchronous decision in a background
        thread via start_bot_decision_async() and returns, resuming when
        the queue result is processed by check_bot_decision_queue().

        For the human player, enables input buttons and returns to await
        interaction.

        Advances the street when all players have acted (is_betting_complete()
        returns True after a full cycle).
        """
        for attempt in range(self.player_count):
            player = self.players[self.current_position]

            if player["status"] not in ("Decided", "Folded", "OUT"):
                self.player_go = player["player"]

                if player["is_bot"]:
                    self.player_turn = False
                    self.update_ui()
                    self.start_bot_decision_async(player)
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

    def start_bot_decision_async(self, player):
        """
        Launches a bot's decision calculation in a background daemon thread.
        Immediately displays a 'thinking' message in the log.  Calculates a
        difficulty-scaled minimum thinking delay to ensure a consistent pause
        regardless of actual compute time.

        Does nothing if a bot decision is already in progress.

        Args:
            player (dict): The bot player dictionary whose AI model will
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
        or error-handles the decision, advances current_position, and
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
        Invokes the bot player's AI model to produce a decision for the
        current game state, gathering the required context (hole cards,
        community cards, opponents, pot, call amount, balance, street).

        Args:
            player (dict): The bot player dictionary.

        Returns:
            tuple: One of '("fold",)', '("call",)', or
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

    def execute_bot_decision(self, player, decision):
        """
        Applies a bot's decision to the game state.

        Handles all three actions:

        - **fold**: sets status to 'Folded' and logs the action.
        - **call**: handles check (call_amount == 0), all-in call
          (call_amount ≥ balance), and normal call; logs and updates pot.
        - **raise**: enforces the minimum raise, caps at player balance,
          updates pot and current_bet, logs, and resets other players via
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
                self.modify_player(player, status="Decided")
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
            self.modify_player(player, status="Decided")
            self.reset_after_raise(except_player=player)

    def is_betting_complete(self):
        """
        Determines whether the current betting round has concluded.

        Betting is complete when fewer than two active players remain, or
        when all active players have the status 'Decided' and each has
        either matched the current bet or has no remaining chips.

        Returns:
            bool: True if betting is complete.
        """
        active = [p for p in self.players if p["status"] not in ("Folded", "OUT")]
        if len(active) < 2:
            return True
        for player in active:
            if player["status"] == "Waiting":
                return False
            if player["bet"] < self.current_bet and player["balance"] > 0:
                return False
        return True

    def reset_after_raise(self, except_player):
        """
        Resets all active players (except the raiser) to 'Waiting' so
        they must act again after a raise. Sets action_position to the
        player immediately after the raiser.

        Args:
            except_player (dict): The player who made the raise.
        """
        raiser_position = except_player["position"] - 1
        self.action_position = (raiser_position + 1) % self.player_count
        for player in self.players:
            if player is except_player:
                continue
            if player["status"] not in ("Folded", "OUT"):
                player["status"] = "Waiting"

    def bot_error(self, player, error):
        """
        Handles a bot decision error gracefully. Displays a messagebox,
        logs the event, and marks the bot as 'OUT'.

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

    # Street management

    def next_street(self):
        """
        Advances to the next street in the street sequence (preflop →
        flop → turn → river → showdown).

        For preflop, preserves blind 'Decided' statuses and sets action
        to start after the big blind. For all post-flop streets, resets
        all active players to 'Waiting', clears per-street bets, and
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
                if player["status"] not in ("Folded", "OUT", "Decided"):
                    player["status"] = "Waiting"
            self.current_position = (self.initial_position + 3) % self.player_count
            self.action_position = self.current_position

        else:
            for player in self.players:
                if player["status"] not in ("Folded", "OUT"):
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
        player (awarding the pot immediately without a showdown), and
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

    # Showdown

    def showdown(self):
        """
        Evaluates all remaining active players' hands against the full
        board using the treys evaluator (lower score = stronger hand),
        determines the winner(s), logs each player's hand and the
        outcome, and schedules end_round() after the log queue has
        finished rendering.

        Handles split pots when multiple players tie.
        """
        self.log_message("— SHOWDOWN —", round_start=True)
        self.log_message("Board cards: " + " ".join(self.board[0]))
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

    # Statistics

    def update_user_poker_data(self):
        """
        Aggregates the human player's in-round action log and updates
        their poker statistics in the database. Derives VPIP, PFR, and
        faced-raise flags from actions_logged, then calls
        update_hand_statistics and resolve_player_actions.
        """
        for player in self.players:
            if not player["is_bot"] and player["user_id"]:
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

    # End round & tournament progression

    def end_round(
        self, *, win=False, loss=False, tie=False, split_pot=False, split_count=1
    ):
        """
        Concludes the current round.

        Updates the human player's chip balance based on the outcome
        (full pot for a solo win, split pot for a shared win, no change
        for a loss or tie), persists the new balance to the database,
        logs the outcome and remaining balance, updates poker statistics,
        increments the round counter, handles tournament progression if
        active, and schedules finish_end_round() after the log queue
        empties.

        Args:
            win (bool): Human player won. Defaults to False.
            loss (bool): Human player lost. Defaults to False.
            tie (bool): Round ended in a tie. Defaults to False.
            split_pot (bool): Pot was split among multiple winners.
                              Defaults to False.
            split_count (int): Number of winners in a split.
                               Defaults to 1.
        """

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

        self.dbm.modify_user_balance(self.user_data["username"], human["balance"])

        if getattr(self, "balance_label", None) and self.balance_label.winfo_exists():
            self.balance_label.config(text=f"Balance: £{human['balance']}")

        self.log_message(f"Your balance: £{human['balance']}.")

        self.update_user_poker_data()

        self.current_round_number += 1
        self.actions_logged = []

        # Tournament round evaluation
        if self.tournament_mode and self.tournament:
            round_won = self.tournament.evaluate_round_win(human, self.players)
            result = self.tournament.advance_round(round_won)
            self.log_message(result["message"], is_tournament=True)

            if result["tournament_over"]:
                delay = self.log_delay_ms * (len(self.log_queue) + 2)
                self.hhe_root.after(
                    delay,
                    lambda r=result: self.finish_tournament(r),
                )
                return

            # Update blinds for next round
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind

        # Schedule teardown after log queue drains
        delay = self.log_delay_ms * (len(self.log_queue) + 1)
        self.hhe_root.after(delay, self.finish_end_round)

    def finish_tournament(self, result):
        """
        Called once a tournament has fully concluded (all rounds played).
        Displays a summary dialog and returns to the main menu.

        Args:
            result (dict): The result dict returned by
                           TournamentManager.advance_round() when
                           tournament_over is True.
        """
        icon = "Tournament Victory!" if result["tournament_won"] else "Tournament Over"
        messagebox.showinfo(icon, result["message"])
        self.return_to_menu()

    def finish_end_round(self):
        """
        Completes round teardown after the log queue has finished
        rendering. Resets the current-bet label, eliminates bots with
        zero chips, marks the human player as 'OUT' if they have no chips,
        checks for game-over conditions, increments the round display
        number, and re-enables the Start Round button.
        """
        self.current_bet = 0
        if (
            getattr(self, "current_bet_label", None)
            and self.current_bet_label.winfo_exists()
        ):
            self.current_bet_label.config(text="Current Bet: £0")

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
        player's status is 'OUT' (loss), or if all bots are 'OUT'
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

    def return_to_menu(self, is_error=False, error=None):
        """
        Destroys the game window and returns the user to the appropriate
        interface: Admin_Interface for administrators, Casino_Interface
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

        Casino_Interface(
            administrator=True if self.user_data.get("administrator") else False,
            user_data=self.user_data,
        )

    # Human player action buttons

    def fold(self):
        """
        Handles the human player choosing to fold. Sets their status to
        'Folded', logs the action to the database, advances
        current_position, and continues the decision loop.
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
        - Call amount is zero → check.
        - Call amount ≥ balance → all-in call for exact balance.
        - Normal call → deduct call_amount, update pot.

        Logs the action to the database, advances current_position, and
        continues the decision loop.
        """
        for player in self.players:
            if not player["is_bot"]:
                call_amount = max(0, self.current_bet - player["bet"])

                if call_amount == 0:
                    self.log_message(f"{player['player']} checks.")
                    action, bet_size = "check", 0

                elif call_amount >= player["balance"]:
                    all_in = player["balance"]
                    self.modify_player(player, change_balance=-all_in)
                    self.modify_player(player, bet=player["bet"] + all_in)
                    self.pot_size += all_in
                    self.log_message(f"{player['player']} calls £{all_in} (ALL-IN).")
                    action, bet_size = "call", all_in

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
        players via reset_after_raise(), logs the action to the database,
        and continues the decision loop.
        """
        try:
            raise_amount = int(self.bet_var.get())
        except ValueError:
            messagebox.showerror("Invalid Raise", "Please enter a valid number.")
            return

        for player in self.players:
            if not player["is_bot"]:
                min_raise = max(
                    self.current_bet - player["bet"] + self.big_blind_value,
                    self.big_blind_value,
                )

                if raise_amount < min_raise:
                    messagebox.showerror(
                        "Invalid Raise",
                        f"The minimum raise is £{min_raise}.",
                    )
                    return

                if raise_amount > player["balance"]:
                    messagebox.showerror(
                        "Insufficient Funds",
                        "You do not have enough chips to raise by that amount.",
                    )
                    return

                self.modify_player(player, change_balance=-raise_amount)
                self.modify_player(player, bet=player["bet"] + raise_amount)
                self.pot_size += raise_amount
                self.current_bet = player["bet"]

                self.log_message(f"{player['player']} raises to £{self.current_bet}.")
                self.modify_player(player, status="Decided")
                self.log_player_action_to_db("raise", raise_amount)
                self.reset_after_raise(except_player=player)

                self.current_position = (self.current_position + 1) % self.player_count
                self.player_turn = False
                self.update_ui()
                self.decisions()
                break


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Entry point
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == "__main__":
    if "--admin" in sys.argv:
        Admin_Interface()
    else:
        User_Interface()
