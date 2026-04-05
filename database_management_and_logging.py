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
    Subclasses supply only the name of the table they write to via the
    TABLE class attribute.

    The worker thread runs as a daemon so it never prevents the process
    from exiting. A stop_event is used to signal clean shutdown.
    """

    # Subclasses must override this with their target table name.
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

    Accepts a db_path at construction time and stores it as instance
    state. Provides methods for creating and viewing the database, registering users, verifying
    passwords, fetching user records, modifying user data.

    Usage:
        dbm = DatabaseManagement(DB_PATH)
        dbm.create_database()
        record = dbm.fetch_user_full_record(username="user1")
    """

    def __init__(self, db_path):
        """
        Stores the database file path as instance state.

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
            endless_high_score INTEGER DEFAULT 0,
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
        Opens and returns a connection to self.db_path with row factory (for dictionary like access)
        and foreign key constraints enabled.

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
                    database_logger.info(f"Table: '{name}' created.")

                conn.commit()
                database_logger.info(f"File: '{self.db_path}' created.")

                self.admin_account()
                database_logger.info("Administrator account added to 'users' table.")

            except sqlite3.Error as error:
                database_logger.exception(f"'create_database' error. {error}")

    def admin_account(self):
        """
        Inserts the default Administrator account if it does not already
        exist.
        """

        from encryption_software import hash_function
        hashed_password = hash_function("Password1")

        with self.connect() as conn:
            try:
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
                database_logger.info("Request for Administrator password_hash.")

                cursor = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    ("Administrator",),
                )
                row = cursor.fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'admin_password_check' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.debug("'password_hash' for Administrator not found.")
            return {"found": False, "verified": False}

        from encryption_software import verify_hash
        verified = verify_hash(row["password_hash"], password)

        database_logger.info(
            "Password verification successful."
            if verified
            else "Failed password attempt."
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
                admin_logger.info("Request to change Admin Password.")
                database_logger.info("Request to change Administrator password.")

                from encryption_software import hash_function
                password_hash = hash_function(new_password)

                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE username = ?",
                    (password_hash, "Administrator"),
                )

                database_logger.info("Administrator password changed.")
                admin_logger.info("Administrator password change request successful.")

            except sqlite3.Error as error:
                admin_logger.error("Administrator password change request failed.")
                database_logger.exception(f"'change_admin_password' error. {error}")

    # DATABASE VIEW AND EXPORT OPERATIONS

    def view_database(self, table):
        """
        Returns all rows from the requested table as a DataFrame.

        Args:
            table (str): The table name to read.

        Returns:
            pd.DataFrame: All rows, or an empty DataFrame on error.
        """
        if not table:
            database_logger.error("No table provided for view_database().")
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
                    f"Exporting table '{table}' to CSV at '{file_path}'."
                )

                rows = conn.execute(f"SELECT * FROM {table}").fetchall()

                if not rows:
                    database_logger.warning(f"Table '{table}' is empty.")
                    return False

                headers = list(rows[0].keys())

                with open(file_path, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(headers)
                    writer.writerows(rows)

                database_logger.info(
                    f"Successfully exported table '{table}' to '{file_path}'."
                )
                return True

        except Exception as error:
            database_logger.exception(f"'export_table_to_csv' error. {error}")
            return False

    def import_from_csv(self, file_path):
        """
        Reads a CSV file and returns its contents as a list of dicts.

        Args:
            file_path (str): Path to the CSV file.

        Returns:
            list: List of row dictionaries.
        """
        records = []
        try:
            with open(file_path, "r") as file:
                headers = file.readline().strip().split(",")
                for line in file:
                    values = line.strip().split(",")
                    records.append(dict(zip(headers, values)))

            database_logger.info(
                f"Successfully imported data from CSV at '{file_path}'."
            )
        except Exception as error:
            database_logger.exception(f"'import_from_csv' error. {error}")

        return records

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
                admin_logger.info(f"Request to change User ID: '{user_id}' username.")
                database_logger.info(
                    f"Request to change User ID: '{user_id}' username."
                )

                conn.execute(
                    "UPDATE users SET username = ? WHERE user_id = ?",
                    (new_username, user_id),
                )

                admin_logger.info("Change username request successful.")
                database_logger.info("User username changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change username request failed.")
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
                admin_logger.info(f"Request to change User: '{user_id}' password.")
                database_logger.info(f"Request to change User: '{user_id}' password.")

                from encryption_software import hash_function

                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE user_id = ?",
                    (hash_function(new_password), user_id),
                )

                admin_logger.info("Change user password request successful.")
                database_logger.info("User password changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user password request failed.")
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
                    f"Request to change User ID: '{user_id}' account type."
                )
                database_logger.info(
                    f"Request to change User ID: '{user_id}' account type."
                )

                conn.execute(
                    "UPDATE users SET registered = ? WHERE user_id = ?",
                    (registered, user_id),
                )

                admin_logger.info("Change user account type request successful.")
                database_logger.info("User account type changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user account type request failed.")
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
                admin_logger.info(f"Request to change User ID: '{user_id}' balance.")
                database_logger.info(f"Request to change User ID: '{user_id}' balance.")

                conn.execute(
                    "UPDATE users SET balance = ? WHERE user_id = ?",
                    (float(new_balance), user_id),
                )

                admin_logger.info("Change user balance request successful.")
                database_logger.info("User balance changed.")

            except sqlite3.Error as error:
                admin_logger.error("Change user balance request failed.")
                database_logger.exception(f"'change_user_balance' error. {error}")

    def delete_user_record(self, user_id):
        """
        Permanently deletes a user record.

        Args:
            user_id (int): The user ID to delete.
        """
        with self.connect() as conn:
            try:
                admin_logger.info(f"Request to delete User ID: '{user_id}' record.")
                database_logger.info(f"Request to delete User ID: '{user_id}' record.")

                conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

                admin_logger.info("Delete user record request successful.")
                database_logger.info("User record deleted.")

            except sqlite3.Error as error:
                admin_logger.error("Delete user record request failed.")
                database_logger.exception(f"'delete_user_record' error. {error}")

    # USER LOOKUP AND AUTHENTICATION

    def fetch_user_full_record(self, *, user_id=None, username=None):
        """
        Returns all columns from the users table for the specified user.

        Args:
            user_id (int, optional): User ID to search by.
            username (str, optional): Username to search by.

        Returns:
            dict: All user fields, or None if not found.

        Raises:
            ValueError: If neither user_id nor username is provided.
        """
        if user_id is None and username is None:
            raise ValueError("Either user_id or username must be provided.")

        with self.connect() as conn:
            try:
                if user_id is not None:
                    row = conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", (user_id,)
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM users WHERE username = ?", (username,)
                    ).fetchone()

                return dict(row) if row else None

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_user_full_record' error. {error}")
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
                database_logger.info(f"Searching for User: '{username}'.")

                row = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?", (username,)
                ).fetchone()

                found = row is not None
                database_logger.info(
                    f"User '{username}' {'found' if found else 'not found'}."
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
            password (str or None): Plaintext password, or None for guests.
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

        from encryption_software import hash_function
        password_hash = hash_function(password) if password else None

        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Request to make an account for User: '{username}'."
                )

                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, registered, balance)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, password_hash, int(float(registered)), 10000.0),
                )

                database_logger.info(f"Created User: '{username}' record.")
                return username

            except sqlite3.IntegrityError:
                database_logger.warning(f"User: '{username}' record already exists.")
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
                    f"Request to search for User: '{username}' 'password_hash'."
                )

                row = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    (username,),
                ).fetchone()

            except sqlite3.Error as error:
                database_logger.exception(f"'verify_user_password' error. {error}")
                return {"found": False, "verified": False}

        if not row or not row["password_hash"]:
            database_logger.info(f"'password_hash' for User: '{username}' not found.")
            return {"found": False, "verified": False}

        from encryption_software import verify_hash
        verified = verify_hash(row["password_hash"], password)

        database_logger.info(
            "Password verification successful."
            if verified
            else "Failed password attempt."
        )

        return {"found": True, "verified": verified}

    def record_user_login(self, username):
        """
        Records a user login event.

        Args:
            username (str): The username of the user who logged in.
        """
        with self.connect() as conn:
            try:
                current_time = datetime.now().strftime("%d-%m-%Y | %H:%M:%S")
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE username = ?",
                    (current_time, username),
                )
                database_logger.info(
                    f"Recorded login for User: '{username}' at {current_time}."
                )
            except sqlite3.Error as error:
                database_logger.exception(f"'record_user_login' error. {error}")
                raise

    # Checks if its been 24 hours since a guest accounts creation not last login and deletes if so. Should be called at startup to clean up expired guest accounts.
    def check_expired_guest_account(self):
        try:
            with self.connect() as conn:
                database_logger.info("Checking for expired guest accounts.")
                current_time = datetime.now()
                conn.execute(
                    "DELETE FROM users WHERE registered = 0 AND "
                    "strftime('%s', 'now') - strftime('%s', created_at) > ?",
                    (24 * 3600,),
                )
                database_logger.info("Expired guest accounts deleted.")
        except sqlite3.Error as error:
            database_logger.exception(f"'startup_checks' error. {error}")

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
                database_logger.info(f"Request to fetch User: '{username}' user_id.")

                row = conn.execute(
                    "SELECT user_id FROM users WHERE username = ?", (username,)
                ).fetchone()

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
        Retrieves the username for a given user ID.

        Args:
            user_id (int): The user ID to look up.

        Returns:
            dict: {'found': bool, 'username': str or None}
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to fetch User ID: '{user_id}' username.")

                row = conn.execute(
                    "SELECT username FROM users WHERE user_id = ?", (user_id,)
                ).fetchone()

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
        Retrieves the account balance for a username.

        Args:
            username (str): The username to query.

        Returns:
            dict: {'found': bool, 'balance': float}
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to fetch User: '{username}' balance.")

                row = conn.execute(
                    "SELECT balance FROM users WHERE username = ?", (username,)
                ).fetchone()

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
        Sets a user's balance to the specified value.

        Args:
            username (str): The username to update.
            new_balance (float): The new balance.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Request to modify User: '{username}' balance.")

                conn.execute(
                    "UPDATE users SET balance = ? WHERE username = ?",
                    (float(new_balance), username),
                )

                database_logger.info("User balance modified.")

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
                    f"Checking if poker data exists for User ID: '{user_id}'."
                )

                exists = conn.execute(
                    "SELECT 1 FROM user_poker_data WHERE user_id = ?", (user_id,)
                ).fetchone()

                database_logger.info(
                    f"Poker data for User: {'found' if exists else 'not found'}."
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
                    f"Initialising poker data for User ID: '{user_id}'."
                )

                exists = conn.execute(
                    "SELECT 1 FROM user_poker_data WHERE user_id = ?", (user_id,)
                ).fetchone()

                if exists:
                    database_logger.info("User poker data already exists.")
                    return True

                conn.execute(
                    "INSERT INTO user_poker_data (user_id) VALUES (?)", (user_id,)
                )

                from poker_player_management import generate_range_chart
                conn.execute(
                    "UPDATE user_poker_data SET player_range = ? WHERE user_id = ?",
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
        Loads the complete poker data record for a user, including derived
        statistics and a deserialised range chart.

        Args:
            user_id (int): The user ID to load.

        Returns:
            dict: All poker data fields plus avg_bet_size, or None on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Loading poker data for User ID: '{user_id}'.")

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
                    database_logger.warning("User not found in poker data.")
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
                    f"Poker data for User ID: '{user_id}' loaded successfully."
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
                database_logger.info(f"Updating player range for User ID: '{user_id}'.")

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET player_range = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (json.dumps(player_range), user_id),
                )

                database_logger.info("User player range updated.")
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
            street (str): 'preflop', 'flop', 'turn', or 'river'.
            action (str): 'fold', 'call', or 'raise'.
            bet_size (float): Amount bet or raised.
            pot_size (float): Total pot at the time of the action.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info(f"Logging action for User ID: '{user_id}'.")

                conn.execute(
                    """
                    INSERT INTO user_poker_actions
                        (user_id, round_number, street, action, bet_size, pot_size)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, round_number, street, action, bet_size, pot_size),
                )

                database_logger.info("Action logged for User.")
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
                database_logger.info(f"Resolving actions for User ID: '{user_id}'.")

                conn.execute(
                    """
                    UPDATE user_poker_actions
                    SET resolved = 1
                    WHERE user_id = ? AND round_number = ?
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
        Increments aggregate poker statistics after a hand and
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
                    f"Updating hand statistics for User ID: '{user_id}'."
                )

                conn.execute(
                    """
                    UPDATE user_poker_data
                    SET
                        rounds_played       = rounds_played + 1,
                        total_hands_played  = total_hands_played + ?,
                        total_hands_raised  = total_hands_raised + ?,
                        total_bets          = total_bets + ?,
                        fold_to_raise       = fold_to_raise + ?,
                        call_when_weak      = call_when_weak + ?,
                        last_updated        = CURRENT_TIMESTAMP
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

                database_logger.info("User hand statistics updated.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_hand_statistics' error. {error}")
                return False

    def recalculate_frequencies(self, conn, user_id):
        """
        Recalculates and stores VPIP and PFR percentages from the raw
        counters. Called internally after updating hand statistics.

        Args:
            conn (sqlite3.Connection): Active connection to reuse.
            user_id (int): The user ID to recalculate for.
        """
        try:
            database_logger.info(f"Recalculating frequencies for User ID: '{user_id}'.")

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

            database_logger.info("User frequencies recalculated.")

        except sqlite3.Error as error:
            database_logger.exception(f"'recalculate_frequencies' error. {error}")

    def fetch_player_statistics(self, user_id):
        """
        Returns a summary of poker statistics for a player.

        Args:
            user_id (int): The user ID to retrieve statistics for.

        Returns:
            dict: Statistics dictionary, or None if not found.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Fetching player statistics for User ID: '{user_id}'."
                )

                row = conn.execute(
                    """
                    SELECT
                        user_id, rounds_played, vpip, pfr,
                        total_bets, fold_to_raise, call_when_weak
                    FROM user_poker_data
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()

                if not row:
                    return None

                statistics = dict(row)
                rounds = max(1, statistics["rounds_played"])
                statistics["avg_bet_size"] = statistics["total_bets"] / rounds

                database_logger.info("User player statistics fetched.")
                return statistics

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_player_statistics' error. {error}")
                return None

    def fetch_all_players_data(self):
        """
        Returns poker data for all players with at least one round played,
        ordered by rounds played descending.

        Returns:
            list: List of player data dictionaries, or empty list on error.
        """
        with self.connect() as conn:
            try:
                database_logger.info("Fetching poker data for all players.")

                rows = conn.execute("""
                    SELECT user_id, rounds_played, vpip, pfr, total_bets
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

    def reset_player_statistics(self, user_id, keep_range=True):
        """
        Resets all poker statistics for a player to zero.

        Args:
            user_id (int): The user ID to reset.
            keep_range (bool): If True, preserves the player_range.
                               Defaults to True.

        Returns:
            bool: True on success, False on error.
        """
        range_clause = "" if keep_range else "player_range = NULL,"

        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Resetting player statistics for User ID: '{user_id}'. "
                    f"Keep range: {keep_range}"
                )

                conn.execute(
                    f"""
                    UPDATE user_poker_data
                    SET
                        {range_clause}
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

                database_logger.info("User statistics reset.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'reset_player_statistics' error. {error}")
                return False

    # SPECIAL GAME MODE SCORES

    def fetch_special_mode_scores(self, user_id):
        """
        Retrieves the Endless mode personal-best score for a user.

        Args:
            user_id (int): The user ID to query.

        Returns:
            dict: {'endless_high_score': int}, or None if not found.
        """
        with self.connect() as conn:
            try:
                database_logger.info(
                    f"Fetching special-mode scores for User ID: '{user_id}'."
                )

                row = conn.execute(
                    "SELECT endless_high_score FROM user_poker_data WHERE user_id = ?",
                    (user_id,),
                ).fetchone()

                if not row:
                    database_logger.info(
                        f"No special-mode scores found for user_id {user_id}."
                    )
                    return None

                database_logger.info("User special-mode scores fetched.")
                return {"endless_high_score": int(row["endless_high_score"] or 0)}

            except sqlite3.Error as error:
                database_logger.exception(f"'fetch_special_mode_scores' error. {error}")
                return None

    def update_special_mode_score(self, user_id, column, new_score):
        """
        Updates a special-mode personal best only if new_score is higher
        than the currently stored value.

        Args:
            user_id (int): The user ID to update.
            column (str): Column name.
            new_score (int): Candidate new personal best.

        Returns:
            bool: True on success, False on error.
        """
        with self.connect() as conn:
            try:
                conn.execute(
                    f"""
                    UPDATE user_poker_data
                    SET {column} = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND {column} < ?
                    """,
                    (new_score, user_id, new_score),
                )

                database_logger.info(f"Updated {column} to {new_score}.")
                return True

            except sqlite3.Error as error:
                database_logger.exception(f"'update_special_mode_score' error. {error}")
                return False


if __name__ == "__main__":
    """
    Initialises the database by creating an instance of DatabaseManagement and
    calling create_database(). This can be run independently to set up the database
    schema and initial administrator account, or will be automatically invoked
    when the User_Interface is run if the database does not already exist.
    """

    dbm = DatabaseManagement()
    dbm.create_database()
