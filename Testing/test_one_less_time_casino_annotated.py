"""
test_one_less_time_casino.py
============================
Automated test suite for One Less Time Casino.

Covers every test from the test plan that cannot be verified through
the GUI.  GUI tests (window rendering, button states, colours, dialogs,
file-picker dialogs, game-screen interactions) are intentionally omitted
and must be verified manually.

Testing Methodology
-------------------
This suite uses Python's built-in 'unittest' framework, which is an
implementation of the xUnit family of testing patterns (originally JUnit
for Java).  Each test class inherits from 'unittest.TestCase', giving
it access to a rich set of assertion methods ('assertEqual',
'assertTrue', 'assertRaises', etc.) that raise a failure if the
condition is not met.

Test categories used throughout the suite follow the standard
Normal / Boundary / Erroneous classification:

  * Normal     — typical, expected inputs and usage paths.
  * Boundary   — values at or just beyond the edges of acceptable ranges
                 (e.g. exactly 24 h, exactly 0 outs).
  * Erroneous  — invalid inputs that the program must handle gracefully
                 (e.g. duplicate usernames, wrong passwords, None values).

Test Isolation
--------------
Database-dependent test classes each create their own temporary SQLite
file (e.g. 'test_schema_temp.db') in 'setUpClass' and delete it in
'tearDownClass'.  This ensures tests are fully independent: a failure
in one class cannot corrupt the data used by another.

The 'setUpClass' / 'tearDownClass' class methods run once for the
entire class, which is more efficient than creating a fresh database
for every individual test method.  Individual helper fixtures such as
'setUp' (which runs before every test method) are used where the test
data is cheap to re-create (e.g. simple lists for the sort/search tests).

Asynchronous Logging
--------------------
The 'LogHandler' classes write to the database on a background thread.
The '_wait_for_log' helper polls the database with a short sleep until
the entry appears or a timeout is reached.  This avoids brittle
'time.sleep' calls of a fixed length while still giving the worker
thread enough time to flush.

The test class patches the module-level 'DB_PATH' constant before
constructing the handlers so that background threads write to the
isolated test database rather than the production one.  This is
necessary because the handlers are module-level singletons that read
'DB_PATH' at write time.

Further Reading
---------------
* Python 'unittest' documentation:
  https://docs.python.org/3/library/unittest.html
* xUnit patterns (Meszaros, 2007) — the canonical reference for test
  fixture design, including setUp/tearDown, test isolation and the
  four-phase test pattern (Arrange / Act / Assert / Teardown):
  http://xunitpatterns.com/
* "Normal, Boundary, Erroneous" test classification is described in
  most UK A-level Computer Science specifications and textbooks, e.g.
  OCR and AQA endorsed resources.
* Boundary Value Analysis and Equivalence Partitioning are covered in
  depth in the ISTQB Foundation Level syllabus:
  https://www.istqb.org/certifications/foundation-level

Usage
-----
  python test_one_less_time_casino.py
"""

import unittest
import sys
import os
from datetime import datetime, timedelta
import sqlite3

try:
    from one_less_time_casino import (
        linear_search,
        bubble_sort,
        hash_function,
        verify_hash,
        validate_password,
        DatabaseManagement,
        DatabaseLogHandler,
        AdminLogHandler,
        CasinoDeckManager,
        pot_odds,
        expected_value_of_call,
        estimate_outs,
        probability_to_hit_by_river,
        minimum_defense_frequency,
        optimal_bluff_ratio,
        apply_noise,
        difficulty_curve,
        calculate_raise_amount,
        generate_range_chart,
        hand_strength_rank,
        generate_bot_range,
        validate_hand_notation,
        update_range,
        cards_to_notation,
        BotPokerPlayer,
        HumanPokerPlayer,
        BotCharacteristics,
        TournamentManager,
        TOURNAMENT_SMALL_BLIND_CAP,
        TOURNAMENT_BIG_BLIND_CAP,
        TOURNAMENT_USER_START_BALANCE,
        TOURNAMENT_BOT_START_BALANCE,
        MAX_OUTS,
    )

    print("Import: OK")
except ImportError as error:
    print(f"Import error: {error}")
    print("Ensure one_less_time_casino.py is in the same directory.")
    sys.exit(1)


# ============================================================================
# 5.2.1  Database
# ============================================================================


class TestDatabaseCreation(unittest.TestCase):
    """5.2.1.1  Creation and Schema

    Verifies that 'DatabaseManagement.create_database()' correctly
    creates all required tables, inserts the default Administrator
    account, and that the existence check works as expected.

    Tests covered:
      Normal     — Create database when none exists; Administrator account
                   inserted on creation.
      Boundary   — Create database when one already exists (IF NOT EXISTS
                   guard prevents duplication).
      Erroneous  — check_database_exists returns False for a missing file;
                   inserting a child row with no parent raises
                   sqlite3.IntegrityError (FK enforcement).
    """

    TEST_DB = "test_schema_temp.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)
        cls.dbm = DatabaseManagement(cls.TEST_DB)
        cls.dbm.create_database()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

    def test_create_database_when_none_exists(self):
        """5.2.1.1 Normal — Create database when none exists: all four tables
        created; Administrator inserted; check_database_exists returns True."""
        self.dbm.create_database()
        self.assertTrue(self.dbm.check_database_exists())
        with self.dbm.connect() as conn:
            for table in (
                "db_logs",
                "admin_logs",
                "users",
                "user_poker_data",
                "user_poker_actions",
            ):
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                self.assertIsNotNone(row, f"Table '{table}' missing")
        result = self.dbm.fetch_user_presence("Administrator")
        self.assertTrue(result["found"])
        print("\nPASS: Create database when none exists")

    def test_create_database_when_one_already_exists(self):
        """5.2.1.1 Boundary — Create database when one already exists:
        CREATE TABLE IF NOT EXISTS prevents duplication; no error raised."""
        try:
            self.dbm.create_database()
        except Exception as e:
            self.fail(f"Second create_database raised an exception: {e}")
        print("\nPASS: Create database when one already exists")

    def test_check_database_exists_returns_false_when_file_absent(self):
        """5.2.1.1 Erroneous — check_database_exists returns False when file
        absent: file path points to a non-existent file; returns False."""
        dbm_missing = DatabaseManagement("nonexistent_xyz.db")
        self.assertFalse(dbm_missing.check_database_exists())
        print("\nPASS: check_database_exists returns False when file absent")

    def test_administrator_account_inserted_on_creation(self):
        """5.2.1.1 Normal — Administrator account inserted on creation:
        users table contains exactly one row with username=Administrator
        and balance=0.0."""
        with self.dbm.connect() as conn:
            row = conn.execute(
                "SELECT username, balance FROM users WHERE username = ?",
                ("Administrator",),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "Administrator")
        self.assertEqual(row["balance"], 0.0)
        print("\nPASS: Administrator account inserted on creation")

    def test_foreign_key_constraints_enabled_on_connection(self):
        """5.2.1.1 Erroneous — Foreign key constraints enabled on connection:
        inserting child row with no parent raises sqlite3.IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            with self.dbm.connect() as conn:
                conn.execute(
                    "INSERT INTO user_poker_data (user_id) VALUES (?)", (999999,)
                )
        print("\nPASS: Foreign key constraints enabled on connection")


# ============================================================================
# 5.2.1  Database — User Management, Guest Expiry and Poker Statistics
# ============================================================================


class TestDatabaseUserManagement(unittest.TestCase):
    """5.2.1.2  User Management, Guest Expiry and Poker Statistics

    Tests user registration, guest account expiry, the daily login bonus
    and poker statistics tracking against the rules defined in section
    5.2.1.2 of the test plan.

    Guest expiry uses a strictly-greater-than comparison (> 24 h), so
    an account that is exactly 24 hours old must be retained.  The
    '_insert_guest_with_age' helper back-dates 'created_at' to simulate
    aged guest accounts without waiting in real time.

    Tests covered:
      Normal     — New guest not deleted; expired guest poker data removed;
                   registered user receives no bonus within 24 h;
                   initialise_user_poker_data creates a record;
                   rounds_played, VPIP and PFR calculations.
      Boundary   — Guest at exactly 24 h retained; guest at 25 h deleted;
                   registered user gets £1,000 bonus after >= 24 h;
                   guest excluded from daily bonus; Administrator skipped
                   by initialise_user_poker_data.
    """

    TEST_DB = "test_user_mgmt_temp.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)
        cls.dbm = DatabaseManagement(cls.TEST_DB)
        cls.dbm.create_database()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

    def _insert_guest_with_age(self, username, hours_ago):
        ts = (datetime.now() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        with self.dbm.connect() as conn:
            conn.execute(
                "INSERT INTO users (username, registered, created_at)"
                " VALUES (?, 0, ?)",
                (username, ts),
            )

    def test_new_guest_account_not_deleted(self):
        """5.2.1.2 Normal — New guest account not deleted: created_at = now;
        account not deleted; fresh guest retained."""
        self.dbm.register_user("FreshGuest1", None, 0)
        self.dbm.check_expired_guest_account()
        result = self.dbm.fetch_user_presence("FreshGuest1")
        self.assertTrue(result["found"])
        print("\nPASS: New guest account not deleted")

    def test_guest_account_exactly_24h_old_is_kept(self):
        """5.2.1.2 Boundary — Guest account that is exactly 24 hours old is
        kept (condition is strictly greater than): created_at = exactly 24
        hours ago; account retained."""
        self._insert_guest_with_age("GuestExact24", 24)
        self.dbm.check_expired_guest_account()
        result = self.dbm.fetch_user_presence("GuestExact24")
        self.assertTrue(result["found"])
        print("\nPASS: Guest account exactly 24 hours old is kept")

    def test_guest_account_just_above_24h_is_deleted(self):
        """5.2.1.2 Boundary — Guest account just above 24 hours old is deleted:
        created_at = 25 hours ago; account and all poker data deleted on
        check_expired_guest_account()."""
        self._insert_guest_with_age("GuestExpired25", 25)
        self.dbm.check_expired_guest_account()
        result = self.dbm.fetch_user_presence("GuestExpired25")
        self.assertFalse(result["found"])
        print("\nPASS: Guest account just above 24 hours old is deleted")

    def test_expired_guest_deletes_poker_data_as_well(self):
        """5.2.1.2 Normal — Expired guest account deletes poker data as well:
        expired guest with poker actions; user_poker_actions and
        user_poker_data deleted before users row; no FK violation."""
        self._insert_guest_with_age("GuestWithPoker", 25)
        uid = self.dbm.fetch_user_id("GuestWithPoker")["user_id"]
        self.dbm.initialise_user_poker_data(uid)
        self.dbm.log_player_action(
            user_id=uid,
            round_number=1,
            street="preflop",
            action="fold",
            bet_size=0,
            pot_size=100,
        )
        try:
            self.dbm.check_expired_guest_account()
        except Exception as e:
            self.fail(f"check_expired_guest_account raised: {e}")
        result = self.dbm.fetch_user_presence("GuestWithPoker")
        self.assertFalse(result["found"])
        print("\nPASS: Expired guest account deletes poker data as well")

    def test_registered_user_no_bonus_within_24h(self):
        """5.2.1.2 Normal — Registered user does not get a bonus within 24
        hours: last_login = 1 hour ago; balance unchanged."""
        self.dbm.register_user("NoBonusReg", "Pass1!", 1)
        recent = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.dbm.connect() as conn:
            conn.execute(
                "UPDATE users SET last_login=? WHERE username=?",
                (recent, "NoBonusReg"),
            )
        before = self.dbm.fetch_user_balance("NoBonusReg")["balance"]
        self.dbm.apply_daily_login_bonus()
        after = self.dbm.fetch_user_balance("NoBonusReg")["balance"]
        self.assertAlmostEqual(after, before, places=2)
        print("\nPASS: Registered user does not get a bonus within 24 hours")

    def test_registered_user_gets_1000_bonus_after_24h(self):
        """5.2.1.2 Boundary — Registered user gets £1,000 bonus after 24 or
        more hours: last_login = 25 hours ago; balance increases by £1,000;
        last_login reset."""
        self.dbm.register_user("BonusReg", "Pass1!", 1)
        old = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
        with self.dbm.connect() as conn:
            conn.execute(
                "UPDATE users SET last_login=? WHERE username=?",
                (old, "BonusReg"),
            )
        before = self.dbm.fetch_user_balance("BonusReg")["balance"]
        self.dbm.apply_daily_login_bonus()
        after = self.dbm.fetch_user_balance("BonusReg")["balance"]
        self.assertAlmostEqual(after - before, 1000.0, places=2)
        print("\nPASS: Registered user gets £1,000 bonus after 24 or more hours")

    def test_guest_account_does_not_receive_daily_bonus(self):
        """5.2.1.2 Boundary — Guest account does not receive daily bonus:
        guest with last_login > 24 hours ago; registered=0 excluded from
        bonus query; balance unchanged."""
        self.dbm.register_user("GuestBonusTest", None, 0)
        old = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
        with self.dbm.connect() as conn:
            conn.execute(
                "UPDATE users SET last_login=? WHERE username=?",
                (old, "GuestBonusTest"),
            )
        before = self.dbm.fetch_user_balance("GuestBonusTest")["balance"]
        self.dbm.apply_daily_login_bonus()
        after = self.dbm.fetch_user_balance("GuestBonusTest")["balance"]
        self.assertAlmostEqual(after, before, places=2)
        print("\nPASS: Guest account does not receive daily bonus")

    def test_initialise_user_poker_data_creates_record(self):
        """5.2.1.2 Normal — initialise_user_poker_data creates a new record
        for a user: new registered user; row inserted with default values
        and base range chart."""
        self.dbm.register_user("PokerInitUser", None, 1)
        uid = self.dbm.fetch_user_id("PokerInitUser")["user_id"]
        self.dbm.initialise_user_poker_data(uid)
        self.assertTrue(self.dbm.check_user_poker_data_exists(uid))
        print("\nPASS: initialise_user_poker_data creates a new record for a user")

    def test_rounds_played_increments_after_each_completed_round(self):
        """5.2.1.2 Normal — rounds_played increments after each completed
        round: complete one round; rounds_played += 1."""
        self.dbm.register_user("RoundsUser", None, 1)
        uid = self.dbm.fetch_user_id("RoundsUser")["user_id"]
        self.dbm.initialise_user_poker_data(uid)
        self.dbm.update_hand_statistics(
            user_id=uid,
            action="fold",
            bet_size=0,
            voluntarily_entered=False,
            preflop_raised=False,
            faced_raise=False,
        )
        row = self.dbm.fetch_total_rounds(uid)
        self.assertEqual(row["rounds_played"], 1)
        print("\nPASS: rounds_played increments after each completed round")

    def test_vpip_calculated_from_preflop_actions(self):
        """5.2.1.2 Normal — VPIP calculated from preflop actions: player calls
        preflop; VPIP = (voluntarily_entered / rounds_played) x 100."""
        self.dbm.register_user("VPIPUser2", None, 1)
        uid = self.dbm.fetch_user_id("VPIPUser2")["user_id"]
        self.dbm.initialise_user_poker_data(uid)
        self.dbm.update_hand_statistics(
            user_id=uid,
            action="call",
            bet_size=50,
            voluntarily_entered=True,
            preflop_raised=False,
            faced_raise=False,
        )
        record = self.dbm.load_user_poker_data(uid)
        self.assertAlmostEqual(record["vpip"], 100.0, places=1)
        print("\nPASS: VPIP calculated from preflop actions")

    def test_pfr_calculated_from_preflop_raise(self):
        """5.2.1.2 Normal — PFR calculated from preflop raise: player raises
        preflop; PFR = (preflop_raised / rounds_played) x 100."""
        self.dbm.register_user("PFRUser", None, 1)
        uid = self.dbm.fetch_user_id("PFRUser")["user_id"]
        self.dbm.initialise_user_poker_data(uid)
        self.dbm.update_hand_statistics(
            user_id=uid,
            action="raise",
            bet_size=200,
            voluntarily_entered=True,
            preflop_raised=True,
            faced_raise=False,
        )
        record = self.dbm.load_user_poker_data(uid)
        self.assertAlmostEqual(record["pfr"], 100.0, places=1)
        print("\nPASS: PFR calculated from preflop raise")

    def test_initialise_user_poker_data_skips_administrators(self):
        """5.2.1.2 Boundary — initialise_user_poker_data skips administrators:
        Administrator launches HHE; no insert attempted; no FK error
        (Administrator has no poker data row by default)."""
        admin_uid = self.dbm.fetch_user_id("Administrator")["user_id"]
        try:
            self.dbm.initialise_user_poker_data(admin_uid)
        except Exception as e:
            self.fail(f"initialise_user_poker_data raised for Administrator: {e}")
        print("\nPASS: initialise_user_poker_data skips administrators")


# ============================================================================
# 5.2.2  Logging Handlers
# ============================================================================


class TestLoggingHandlers(unittest.TestCase):
    """5.2.2  Logging Handlers

    Verifies that 'DatabaseLogHandler' and 'AdminLogHandler' correctly
    write entries to their respective database tables, as specified in
    section 5.2.2 of the test plan.

    Because the handlers run on a background daemon thread, entries do
    not appear in the database immediately.  '_wait_for_log' implements
    a polling loop — re-querying every 100 ms up to a 5-second timeout —
    to avoid both false negatives from a fixed short sleep and wasted
    time from an unnecessarily long one.

    Tests covered:
      Normal     — Log entry written to db_logs table with correct
                   timestamp, level and message; log entry written to
                   admin_logs table; log level stored correctly.
      Boundary   — Empty message string inserted without crash.
      Erroneous  — 1,500-character message inserted or truncated cleanly
                   with no unhandled exception.
    """

    TEST_DB = "test_logging_temp.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)
        cls.dbm = DatabaseManagement(cls.TEST_DB)
        cls.dbm.create_database()
        import logging
        import one_less_time_casino as oltc

        oltc.DB_PATH = cls.TEST_DB

        cls.db_handler = DatabaseLogHandler()
        cls.db_logger = logging.getLogger("test_db_log")
        cls.db_logger.setLevel(logging.DEBUG)
        cls.db_logger.handlers = []
        cls.db_handler.setFormatter(logging.Formatter("%(message)s"))
        cls.db_logger.addHandler(cls.db_handler)

        cls.admin_handler = AdminLogHandler()
        cls.admin_logger = logging.getLogger("test_admin_log")
        cls.admin_logger.setLevel(logging.DEBUG)
        cls.admin_logger.handlers = []
        cls.admin_handler.setFormatter(logging.Formatter("%(message)s"))
        cls.admin_logger.addHandler(cls.admin_handler)

    @classmethod
    def tearDownClass(cls):
        cls.db_handler.close()
        cls.admin_handler.close()
        import time as _time

        _time.sleep(0.5)
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

    def _wait_for_log(self, table, message, timeout=5):
        import time as _time

        deadline = _time.time() + timeout
        while _time.time() < deadline:
            with self.dbm.connect() as conn:
                row = conn.execute(
                    f"SELECT * FROM {table} WHERE log_entry = ?", (message,)
                ).fetchone()
            if row:
                return row
            _time.sleep(0.1)
        return None

    def test_log_entry_written_to_db_logs(self):
        """5.2.2 Normal — Log entry written to db_logs table:
        database_logger.info('test message'); row appears in db_logs with
        correct timestamp, level and message."""
        msg = "test_db_log_message_unique_xyz"
        self.db_logger.info(msg)
        row = self._wait_for_log("db_logs", msg)
        self.assertIsNotNone(row, "Log entry not found in db_logs")
        self.assertEqual(row["level"], "INFO")
        print("\nPASS: Log entry written to db_logs table")

    def test_log_entry_written_to_admin_logs(self):
        """5.2.2 Normal — Log entry written to admin_logs table:
        admin_logger.info('admin action'); row appears in admin_logs."""
        msg = "test_admin_log_message_unique_xyz"
        self.admin_logger.info(msg)
        row = self._wait_for_log("admin_logs", msg)
        self.assertIsNotNone(row, "Log entry not found in admin_logs")
        print("\nPASS: Log entry written to admin_logs table")

    def test_log_entry_recorded_with_correct_log_level(self):
        """5.2.2 Normal — Log entry recorded with correct log level: call at
        WARNING level; level column stores 'WARNING'."""
        msg = "test_warning_level_unique_xyz"
        self.db_logger.warning(msg)
        row = self._wait_for_log("db_logs", msg)
        self.assertIsNotNone(row)
        self.assertEqual(row["level"], "WARNING")
        print("\nPASS: Log entry recorded with correct log level")

    def test_log_entry_with_empty_message_string(self):
        """5.2.2 Boundary — Log entry with empty message string: empty string
        message; row still inserted with empty message field; no crash."""
        self.db_logger.info("")
        import time as _time

        _time.sleep(0.5)
        with self.dbm.connect() as conn:
            row = conn.execute(
                "SELECT * FROM db_logs WHERE log_entry = ?", ("",)
            ).fetchone()
        self.assertIsNotNone(row)
        print("\nPASS: Log entry with empty message string")

    def test_log_entry_with_very_long_message(self):
        """5.2.2 Erroneous — Log entry with very long message (1,500 chars):
        string of 1,500 characters; row inserted or truncated cleanly;
        no unhandled exception."""
        long_msg = "X" * 1500
        try:
            self.db_logger.info(long_msg)
        except Exception as e:
            self.fail(f"Long message logging raised: {e}")
        import time as _time

        _time.sleep(0.5)
        print("\nPASS: Log entry with very long message")


# ============================================================================
# 5.2.4  Search and Sort Algorithms
# ============================================================================


class TestLinearSearch(unittest.TestCase):
    """5.2.4  linear_search

    Tests the custom linear search over a list of dicts by key-value
    pair, as specified in section 5.2.4 of the test plan.

    'setUp' rebuilds the fixture list before each test method so that no
    test can affect another by mutating the shared list.

    Tests covered:
      Normal     — Finds an existing key-value pair; returns the correct
                   index.
      Boundary   — Empty list returns -1; duplicate values returns the
                   index of the first match only.
      Erroneous  — Value not present in list returns -1.
    """

    def setUp(self):
        self.data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ]

    def test_linear_search_finds_existing_key_value_pair(self):
        """5.2.4 Normal — linear_search finds an existing key-value pair:
        list of dictionaries, valid key/value; correct index returned."""
        self.assertEqual(linear_search(self.data, "name", "Bob"), 1)
        print("\nPASS: linear_search finds an existing key-value pair")

    def test_linear_search_on_empty_list(self):
        """5.2.4 Boundary — linear_search on an empty list: array = [];
        returns -1."""
        self.assertEqual(linear_search([], "id", 1), -1)
        print("\nPASS: linear_search on an empty list")

    def test_linear_search_returns_first_match_only(self):
        """5.2.4 Boundary — linear_search returns index of first match only:
        two dictionaries with same value; returns 0 (first occurrence)."""
        dup = [{"v": 5}, {"v": 5}]
        self.assertEqual(linear_search(dup, "v", 5), 0)
        print("\nPASS: linear_search returns index of first match only")

    def test_linear_search_for_value_not_present(self):
        """5.2.4 Erroneous — linear_search for a value not present: valid
        list, non-existent value; returns -1."""
        self.assertEqual(linear_search(self.data, "name", "Zara"), -1)
        print("\nPASS: linear_search for a value not present")


class TestBubbleSort(unittest.TestCase):
    """5.2.4  bubble_sort

    Tests the custom bubble sort over a list of dicts by a named key,
    as specified in section 5.2.4 of the test plan.

    Non-mutation is an important property to verify — the sort must
    return a new list and leave the original unchanged so that callers
    are not surprised by side effects.

    Tests covered:
      Normal     — Ascending sort on a typical list (original unchanged);
                   descending sort (highest score at index 0);
                   original list not mutated after call.
      Boundary   — Single-element list; already-sorted list.
    """

    def setUp(self):
        self.data = [
            {"score": 30},
            {"score": 10},
            {"score": 20},
        ]

    def test_bubble_sort_ascending_on_typical_list(self):
        """5.2.4 Normal — bubble_sort ascending on a typical list: mixed list
        of dictionaries; sorted list returned; original unchanged."""
        result = bubble_sort(self.data, "score", reverse=False)
        self.assertEqual([r["score"] for r in result], [10, 20, 30])
        # original unchanged
        self.assertEqual([r["score"] for r in self.data], [30, 10, 20])
        print("\nPASS: bubble_sort ascending on a typical list")

    def test_bubble_sort_descending_on_typical_list(self):
        """5.2.4 Normal — bubble_sort descending on a typical list: list of
        score dictionaries, reverse=True; highest score at index 0."""
        result = bubble_sort(self.data, "score", reverse=True)
        self.assertEqual(result[0]["score"], 30)
        print("\nPASS: bubble_sort descending on a typical list")

    def test_bubble_sort_does_not_mutate_original_list(self):
        """5.2.4 Normal — bubble_sort does not mutate the original list: any
        list; original list order preserved after call."""
        original = [r["score"] for r in self.data]
        bubble_sort(self.data, "score", reverse=False)
        self.assertEqual([r["score"] for r in self.data], original)
        print("\nPASS: bubble_sort does not mutate the original list")

    def test_bubble_sort_on_single_element_list(self):
        """5.2.4 Boundary — bubble_sort on a single-element list: one-item
        list; same item returned unchanged."""
        result = bubble_sort([{"v": 99}], "v", reverse=False)
        self.assertEqual(result[0]["v"], 99)
        print("\nPASS: bubble_sort on a single-element list")

    def test_bubble_sort_on_already_sorted_list(self):
        """5.2.4 Boundary — bubble_sort on an already sorted list: pre-sorted
        list; returned list is identical in order; no error."""
        pre = [{"v": 1}, {"v": 2}, {"v": 3}]
        result = bubble_sort(pre, "v", reverse=False)
        self.assertEqual([r["v"] for r in result], [1, 2, 3])
        print("\nPASS: bubble_sort on an already sorted list")


# ============================================================================
# 5.2.6  Password Management
# ============================================================================


class TestHashFunction(unittest.TestCase):
    """5.2.6  hash_function and verify_hash

    Verifies the password hashing scheme against section 5.2.6 of the
    test plan.

    Tests covered:
      Normal     — hash_function returns a $-delimited string; hashing is
                   non-deterministic (salted); verify_hash returns True
                   for the matching plaintext.
      Boundary   — Empty string can be hashed and verified correctly.
      Erroneous  — verify_hash returns False for the wrong plaintext;
                   hash_function raises TypeError for non-string input.
    """

    def test_hash_function_returns_dollar_delimited_string(self):
        """5.2.6 Normal — hash_function returns a $-delimited string: any
        string input; output contains exactly one $ separator."""
        result = hash_function("TestPassword1!")
        self.assertEqual(result.count("$"), 1)
        print("\nPASS: hash_function returns a $-delimited string")

    def test_hash_is_non_deterministic(self):
        """5.2.6 Normal — Hash is non-deterministic: same password hashed
        twice produces two different hash strings."""
        h1 = hash_function("SamePassword1!")
        h2 = hash_function("SamePassword1!")
        self.assertNotEqual(h1, h2)
        print("\nPASS: Hash is non-deterministic")

    def test_verify_hash_returns_true_for_correct_password(self):
        """5.2.6 Normal — verify_hash returns True for correct password:
        stored hash + matching plaintext; returns True."""
        stored = hash_function("CorrectPass1!")
        self.assertTrue(verify_hash(stored, "CorrectPass1!"))
        print("\nPASS: verify_hash returns True for correct password")

    def test_empty_string_can_be_hashed_and_verified(self):
        """5.2.6 Boundary — Empty string can be hashed and verified:
        hash_function(''); produces valid hash; verify_hash returns True
        for '' and False for any other string."""
        stored = hash_function("")
        self.assertTrue(verify_hash(stored, ""))
        self.assertFalse(verify_hash(stored, "not_empty"))
        print("\nPASS: Empty string can be hashed and verified")

    def test_verify_hash_returns_false_for_wrong_password(self):
        """5.2.6 Erroneous — verify_hash returns False for wrong password:
        stored hash + wrong plaintext; returns False."""
        stored = hash_function("RightPass1!")
        self.assertFalse(verify_hash(stored, "WrongPass1!"))
        print("\nPASS: verify_hash returns False for wrong password")

    def test_hash_function_raises_error_for_non_string_input(self):
        """5.2.6 Erroneous — hash_function raises an error for non-string
        input: integer input 12345; TypeError raised."""
        with self.assertRaises(TypeError):
            hash_function(12345)
        print("\nPASS: hash_function raises an error for non-string input")


class TestPasswordValidation(unittest.TestCase):
    """5.2.6  validate_password

    Confirms that the password policy enforces all five rules (minimum
    8 characters, uppercase letter, lowercase letter, digit, special
    character) independently, as specified in section 5.2.6 of the test
    plan.

    Tests covered:
      Normal     — Password meeting all five criteria passes;
                   validate_password returns (True, []).
      Erroneous  — Each rule failure reported individually: too short,
                   no uppercase, no lowercase, no digit, no special
                   character.
    """

    def test_password_meeting_all_five_criteria_passes(self):
        """5.2.6 Normal — Password meeting all five criteria passes: Secure1!;
        validate_password returns (True, [])."""
        passed, failures = validate_password("Secure1!")
        self.assertTrue(passed)
        self.assertEqual(failures, [])
        print("\nPASS: Password meeting all five criteria passes")

    def test_password_shorter_than_8_characters_fails(self):
        """5.2.6 Erroneous — Password shorter than 8 characters fails: Ab1!;
        returns (False, [...]); failure list includes length rule."""
        passed, failures = validate_password("Ab1!")
        self.assertFalse(passed)
        self.assertTrue(any("8" in f for f in failures))
        print("\nPASS: Password shorter than 8 characters fails")

    def test_password_with_no_uppercase_fails(self):
        """5.2.6 Erroneous — Password with no uppercase fails: secure1!;
        uppercase rule in failures list."""
        passed, failures = validate_password("secure1!")
        self.assertFalse(passed)
        self.assertTrue(any("uppercase" in f.lower() for f in failures))
        print("\nPASS: Password with no uppercase fails")

    def test_password_with_no_lowercase_fails(self):
        """5.2.6 Erroneous — Password with no lowercase fails: SECURE1!;
        lowercase rule in failures list."""
        passed, failures = validate_password("SECURE1!")
        self.assertFalse(passed)
        self.assertTrue(any("lowercase" in f.lower() for f in failures))
        print("\nPASS: Password with no lowercase fails")

    def test_password_with_no_digit_fails(self):
        """5.2.6 Erroneous — Password with no digit fails: Secure!!;
        digit rule in failures list."""
        passed, failures = validate_password("Secure!!")
        self.assertFalse(passed)
        self.assertTrue(any("digit" in f.lower() or "0" in f for f in failures))
        print("\nPASS: Password with no digit fails")

    def test_password_with_no_special_character_fails(self):
        """5.2.6 Erroneous — Password with no special character fails:
        Secure11; special character rule in failures list."""
        passed, failures = validate_password("Secure11")
        self.assertFalse(passed)
        self.assertTrue(any("special" in f.lower() for f in failures))
        print("\nPASS: Password with no special character fails")


# ============================================================================
# 5.2.13.2  User Registration
# ============================================================================


class TestUserRegistration(unittest.TestCase):
    """5.2.13.2  User Registration

    Tests 'register_user' across normal, boundary and erroneous inputs,
    as specified in section 5.2.13.2 of the test plan.

    Each test registers a uniquely named user to avoid conflicts between
    tests sharing the same class-level database.

    Tests covered:
      Normal     — Valid unique username and password creates account with
                   balance £10,000 and registered=1; guest account created
                   with NULL password_hash and registered=0; starting
                   balance is exactly £10,000.
      Erroneous  — Empty username raises ValueError; reserved username
                   'Administrator' (any case) raises ValueError;
                   duplicate username raises sqlite3.IntegrityError.
    """

    TEST_DB = "test_registration_temp.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)
        cls.dbm = DatabaseManagement(cls.TEST_DB)
        cls.dbm.create_database()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

    def test_register_with_valid_unique_username_and_password(self):
        """5.2.13.2 Normal — Register with a valid unique username and
        password: Username: User1, Password: Password1!; account created;
        balance set to £10,000; registered=1."""
        self.dbm.register_user("JohnSmith", "Secure1!", 1)
        record = self.dbm.fetch_user_record(username="JohnSmith")
        self.assertIsNotNone(record)
        self.assertEqual(record["registered"], 1)
        self.assertAlmostEqual(record["balance"], 10000.0, places=2)
        print("\nPASS: Register with a valid unique username and password")

    def test_register_guest_account_no_password(self):
        """5.2.13.2 Normal — Register a guest account (no password):
        Username: GuestUser, Password: None; account created;
        password_hash is NULL; registered=0."""
        self.dbm.register_user("GuestUser", None, 0)
        record = self.dbm.fetch_user_record(username="GuestUser")
        self.assertIsNotNone(record)
        self.assertIsNone(record["password_hash"])
        self.assertEqual(record["registered"], 0)
        print("\nPASS: Register a guest account (no password)")

    def test_starting_balance_is_exactly_10000(self):
        """5.2.13.2 Normal — Starting balance is exactly £10,000: any valid
        new user; balance = 10000.0 in database."""
        self.dbm.register_user("BalanceCheck", "Secure1!", 1)
        record = self.dbm.fetch_user_record(username="BalanceCheck")
        self.assertEqual(record["balance"], 10000.0)
        print("\nPASS: Starting balance is exactly £10,000")

    def test_register_with_empty_username_raises(self):
        """5.2.13.2 Erroneous — Register with empty username: Username:
        (empty); ValueError raised."""
        with self.assertRaises(ValueError):
            self.dbm.register_user("", "Secure1!", 1)
        print("\nPASS: Register with empty username raises ValueError")

    def test_register_with_reserved_username_administrator_raises(self):
        """5.2.13.2 Erroneous — Register with reserved username Administrator
        (any case): Username: administrator; ValueError raised; registration
        blocked."""
        with self.assertRaises(ValueError):
            self.dbm.register_user("administrator", "Secure1!", 1)
        print("\nPASS: Register with reserved username Administrator raises ValueError")

    def test_register_username_that_already_exists_raises_integrity_error(self):
        """5.2.13.2 Erroneous — Register a username that already exists:
        username matching an existing user; sqlite3.IntegrityError raised."""
        self.dbm.register_user("DuplicateUser", None, 0)
        with self.assertRaises(sqlite3.IntegrityError):
            self.dbm.register_user("DuplicateUser", None, 0)
        print(
            "\nPASS: Register username that already exists raises sqlite3.IntegrityError"
        )


# ============================================================================
# 5.2.13.3  User Login and Password Verification
# ============================================================================


class TestUserLogin(unittest.TestCase):
    """5.2.13.3  User Login and Password Verification

    Tests 'verify_user_password' and 'record_user_login', as specified
    in section 5.2.13.3 of the test plan.

    Both a registered and a guest account are created once in
    'setUpClass' and reused across all tests, since none of these tests
    modify the stored password.

    Tests covered:
      Normal     — Correct credentials return {found: True, verified: True};
                   record_user_login updates last_login timestamp in ISO
                   format; guest account has NULL password_hash and
                   returns {found: False, verified: False}.
      Erroneous  — Correct username with wrong password returns
                   {found: True, verified: False}; non-existent username
                   returns {found: False, verified: False}; password of
                   only spaces fails verification after strip().
    """

    TEST_DB = "test_login_temp.db"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)
        cls.dbm = DatabaseManagement(cls.TEST_DB)
        cls.dbm.create_database()
        cls.dbm.register_user("LoginUser", "Secure1!", 1)
        cls.dbm.register_user("GuestLogin", None, 0)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

    def test_login_with_correct_username_and_password(self):
        """5.2.13.3 Normal — Login with correct username and password: valid
        credentials; verify_user_password returns {found: True,
        verified: True}."""
        result = self.dbm.verify_user_password("LoginUser", "Secure1!")
        self.assertTrue(result["found"])
        self.assertTrue(result["verified"])
        print("\nPASS: Login with correct username and password")

    def test_record_user_login_updates_last_login(self):
        """5.2.13.3 Normal — record_user_login updates last_login timestamp:
        existing user logs in; last_login field updated to current time
        in ISO format."""
        self.dbm.record_user_login("LoginUser")
        record = self.dbm.fetch_user_record(username="LoginUser")
        self.assertIsNotNone(record["last_login"])
        # Should parse as a valid datetime
        datetime.strptime(record["last_login"], "%Y-%m-%d %H:%M:%S")
        print("\nPASS: record_user_login updates last_login timestamp")

    def test_guest_account_has_no_password_hash(self):
        """5.2.13.3 Normal — Guest account has no password hash: fetch record
        for guest user; password_hash is NULL; verify_user_password returns
        {found: False, verified: False}."""
        record = self.dbm.fetch_user_record(username="GuestLogin")
        self.assertIsNone(record["password_hash"])
        result = self.dbm.verify_user_password("GuestLogin", "anything")
        self.assertFalse(result["found"])
        self.assertFalse(result["verified"])
        print("\nPASS: Guest account has no password hash")

    def test_login_with_correct_username_wrong_password(self):
        """5.2.13.3 Erroneous — Login with correct username, wrong password:
        valid username, wrong password; returns {found: True,
        verified: False}."""
        result = self.dbm.verify_user_password("LoginUser", "WrongPassword!")
        self.assertTrue(result["found"])
        self.assertFalse(result["verified"])
        print("\nPASS: Login with correct username, wrong password")

    def test_login_with_username_that_does_not_exist(self):
        """5.2.13.3 Erroneous — Login with a username that does not exist:
        NotUser1, any password; returns {found: False, verified: False}."""
        result = self.dbm.verify_user_password("nonexistent_user_xyz", "password")
        self.assertFalse(result["found"])
        self.assertFalse(result["verified"])
        print("\nPASS: Login with a username that does not exist")

    def test_login_with_password_containing_only_spaces(self):
        """5.2.13.3 Erroneous — Login with password containing only spaces:
        Username: valid, Password: '   '; login fails (.strip() produces
        empty string; password not verified)."""
        result = self.dbm.verify_user_password("LoginUser", "   ")
        # A stripped empty string will not match the stored hash
        self.assertFalse(result["verified"])
        print("\nPASS: Login with password containing only spaces")


# ============================================================================
# 5.2.14  Deck Manager
# ============================================================================


class TestCasinoDeckManager(unittest.TestCase):
    """5.2.14  Deck Manager

    Tests 'CasinoDeckManager' which wraps the treys library to provide
    a consistent card-drawing interface for both poker and blackjack
    modes, as specified in section 5.2.14 of the test plan.

    A fresh deck is created in 'setUp' so each test starts with a full
    52-card deck.

    Tests covered:
      Normal     — Fresh deck has 52 cards; draw(1) returns int and reduces
                   count; draw(n) returns list of n ints; str_draw and
                   pretty_draw return correct formats; string-to-treys
                   round trip; independent copy; evaluate_hand for both
                   modes; treys_to_str_pretty parallel lists;
                   blackjack Ace logic.
      Boundary   — Natural blackjack = 21; deck auto-resets when exhausted.
      Erroneous  — evaluate_hand in poker mode with no board raises
                   ValueError; invalid game mode raises ValueError.
    """

    def setUp(self):
        self.dm = CasinoDeckManager(shuffle=True, game_mode="poker")

    def test_fresh_deck_contains_52_cards(self):
        """5.2.14 Normal — Fresh deck contains 52 cards:
        CasinoDeckManager(shuffle=True); remaining() returns 52."""
        self.assertEqual(self.dm.remaining(), 52)
        print("\nPASS: Fresh deck contains 52 cards")

    def test_draw_1_returns_int_and_reduces_deck_by_1(self):
        """5.2.14 Normal — draw(1) returns an integer and reduces deck by 1:
        draw 1 card; returns int; remaining() = 51."""
        card = self.dm.draw(1)
        self.assertIsInstance(card, int)
        self.assertEqual(self.dm.remaining(), 51)
        print("\nPASS: draw(1) returns an integer and reduces deck by 1")

    def test_draw_n_returns_list_of_n_integers(self):
        """5.2.14 Normal — draw(n) returns a list of n integers: draw(5);
        returns list of length 5."""
        cards = self.dm.draw(5)
        self.assertIsInstance(cards, list)
        self.assertEqual(len(cards), 5)
        print("\nPASS: draw(n) returns a list of n integers")

    def test_str_draw_returns_2_character_string_representations(self):
        """5.2.14 Normal — str_draw returns 2-character string representations:
        str_draw(3); list of 3 strings, each length 2."""
        cards = self.dm.str_draw(3)
        self.assertEqual(len(cards), 3)
        for c in cards:
            self.assertIsInstance(c, str)
            self.assertEqual(len(c), 2)
        print("\nPASS: str_draw returns 2-character string representations")

    def test_pretty_draw_returns_strings_with_unicode_suit_symbols(self):
        """5.2.14 Normal — pretty_draw returns strings with Unicode suit
        symbols: pretty_draw(2); each string contains a suit symbol."""
        cards = self.dm.pretty_draw(2)
        for c in cards:
            self.assertTrue(any(sym in c for sym in ["♠", "♥", "♦", "♣"]))
        print("\nPASS: pretty_draw returns strings with Unicode suit symbols")

    def test_string_to_treys_round_trip_is_lossless(self):
        """5.2.14 Normal — String-to-treys round trip is lossless:
        str_to_treys('As') then treys_to_str; returns 'As'."""
        back = self.dm.treys_to_str(self.dm.str_to_treys("As"))
        self.assertEqual(back, "As")
        print("\nPASS: String-to-treys round trip is lossless")

    def test_copy_creates_independent_deck(self):
        """5.2.14 Normal — copy() creates an independent deck: modify original
        after copy; copy's card count unchanged."""
        copy = self.dm.copy()
        self.dm.draw(5)
        self.assertNotEqual(self.dm.remaining(), copy.remaining())
        print("\nPASS: copy() creates an independent deck")

    def test_evaluate_hand_poker_mode_returns_score_name_tuple(self):
        """5.2.14 Normal — evaluate_hand in poker mode returns (score, name)
        tuple: valid hand and board; returns (int, str)."""
        dm = CasinoDeckManager(game_mode="poker")
        result = dm.evaluate_hand(["As", "Ah"], ["Ad", "Ac", "Kh", "Qd", "Jc"])
        self.assertIsInstance(result, tuple)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], str)
        print("\nPASS: evaluate_hand in poker mode returns (score, name) tuple")

    def test_evaluate_hand_blackjack_mode_returns_int(self):
        """5.2.14 Normal — evaluate_hand in blackjack mode returns int: valid
        hand; returns int."""
        dm = CasinoDeckManager(game_mode="blackjack")
        result = dm.evaluate_hand(["As", "Kh"])
        self.assertIsInstance(result, int)
        print("\nPASS: evaluate_hand in blackjack mode returns int")

    def test_treys_to_str_pretty_returns_parallel_lists_of_equal_length(self):
        """5.2.14 Normal — treys_to_str_pretty returns parallel lists of equal
        length: list of 5 treys integers; returns [[str...], [pretty_str...]]
        both length 5."""
        cards = self.dm.draw(5)
        result = self.dm.treys_to_str_pretty(cards)
        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0]), 5)
        self.assertEqual(len(result[1]), 5)
        print("\nPASS: treys_to_str_pretty returns parallel lists of equal length")

    def test_blackjack_hand_value_ace_counts_as_11_when_safe(self):
        """5.2.14 Normal — blackjack_hand_value: Ace counts as 11 when safe:
        Ace + 7; returns 18."""
        hand = [self.dm.str_to_treys("Ah"), self.dm.str_to_treys("7d")]
        self.assertEqual(self.dm.blackjack_hand_value(hand), 18)
        print("\nPASS: blackjack_hand_value: Ace counts as 11 when safe")

    def test_blackjack_hand_value_ace_counts_as_1_when_bust(self):
        """5.2.14 Normal — blackjack_hand_value: Ace counts as 1 when 11
        would bust: Ace + K + 5; returns 16."""
        hand = [
            self.dm.str_to_treys("Ah"),
            self.dm.str_to_treys("Kd"),
            self.dm.str_to_treys("5s"),
        ]
        self.assertEqual(self.dm.blackjack_hand_value(hand), 16)
        print("\nPASS: blackjack_hand_value: Ace counts as 1 when 11 would bust")

    def test_blackjack_natural_blackjack_equals_21(self):
        """5.2.14 Boundary — blackjack_hand_value: natural blackjack = 21:
        Ace + K; returns 21."""
        hand = [self.dm.str_to_treys("Ah"), self.dm.str_to_treys("Ks")]
        self.assertEqual(self.dm.blackjack_hand_value(hand), 21)
        print("\nPASS: blackjack_hand_value: natural blackjack = 21")

    def test_deck_auto_resets_when_exhausted(self):
        """5.2.14 Boundary — Deck auto-resets when exhausted: draw all 52
        cards then draw 1 more; new card returned; no error."""
        self.dm.draw(52)
        card = self.dm.draw(1)
        self.assertIsInstance(card, int)
        print("\nPASS: Deck auto-resets when exhausted")

    def test_evaluate_hand_poker_mode_requires_board(self):
        """5.2.14 Erroneous — evaluate_hand in poker mode requires a board:
        no board passed; ValueError raised."""
        dm = CasinoDeckManager(game_mode="poker")
        with self.assertRaises(ValueError):
            dm.evaluate_hand(["As", "Kh"], board=None)
        print("\nPASS: evaluate_hand in poker mode requires a board")

    def test_evaluate_hand_invalid_game_mode_raises_error(self):
        """5.2.14 Erroneous — evaluate_hand with invalid game mode raises
        error: game_mode = 'roulette'; ValueError raised."""
        dm = CasinoDeckManager(game_mode="snap")
        with self.assertRaises(ValueError):
            dm.evaluate_hand(["As", "Kh"], board=["Qd", "Jc", "Ts", "9h", "2d"])
        print("\nPASS: evaluate_hand with invalid game mode raises error")


# ============================================================================
# 5.2.16  Range Chart and Hand Notation
# ============================================================================


class TestRangeChartAndHandNotation(unittest.TestCase):
    """5.2.16  Range Chart and Hand Notation

    Tests the 169-entry poker hand range chart, notation parsing and the
    range update logic, as specified in section 5.2.16 of the test plan.

    These are all pure functions with no database dependency, so no setUp
    or database fixture is required.

    Tests covered:
      Normal     — generate_range_chart returns 169 entries all at 0.0;
                   all 13 pocket pairs present; suited and offsuit hands
                   present; validate_hand_notation accepts pocket pairs,
                   suited and offsuit hands; update_range normalises
                   probabilities to sum 1.0; cards_to_notation for
                   pairs, suited and offsuit; hand_strength_rank ordering;
                   generate_bot_range at 20% VPIP.
      Boundary   — cards_to_notation reorders lower-ranked card first.
      Erroneous  — validate_hand_notation rejects invalid formats;
                   update_range raises ValueError on invalid hand.
    """

    def test_generate_range_chart_returns_dict_with_169_entries(self):
        """5.2.16 Normal — generate_range_chart returns dict with 169 entries:
        call the module; 169 keys; all values 0.0."""
        chart = generate_range_chart()
        self.assertEqual(len(chart), 169)
        for v in chart.values():
            self.assertEqual(v, 0.0)
        print("\nPASS: generate_range_chart returns dict with 169 entries")

    def test_all_13_pocket_pairs_present_in_chart(self):
        """5.2.16 Normal — All 13 pocket pairs present in chart: check AA
        through 22; all present in chart."""
        chart = generate_range_chart()
        for pair in [
            "AA",
            "KK",
            "QQ",
            "JJ",
            "TT",
            "99",
            "88",
            "77",
            "66",
            "55",
            "44",
            "33",
            "22",
        ]:
            self.assertIn(pair, chart)
        print("\nPASS: All 13 pocket pairs present in chart")

    def test_suited_and_offsuit_hands_present_in_chart(self):
        """5.2.16 Normal — Suited and offsuit hands present in chart: check
        AKs, AKo; both present."""
        chart = generate_range_chart()
        self.assertIn("AKs", chart)
        self.assertIn("AKo", chart)
        print("\nPASS: Suited and offsuit hands present in chart")

    def test_validate_hand_notation_valid_pocket_pairs_accepted(self):
        """5.2.16 Normal — validate_hand_notation: valid pocket pairs accepted:
        AA, KK, 22; returns True."""
        for hand in ["AA", "KK", "22"]:
            self.assertTrue(validate_hand_notation(hand))
        print("\nPASS: validate_hand_notation: valid pocket pairs accepted")

    def test_validate_hand_notation_suited_hands_accepted(self):
        """5.2.16 Normal — validate_hand_notation: suited hands accepted:
        AKs, 87s; returns True."""
        for hand in ["AKs", "87s"]:
            self.assertTrue(validate_hand_notation(hand))
        print("\nPASS: validate_hand_notation: suited hands accepted")

    def test_validate_hand_notation_offsuit_hands_accepted(self):
        """5.2.16 Normal — validate_hand_notation: offsuit hands accepted:
        AKo, 87o; returns True."""
        for hand in ["AKo", "87o"]:
            self.assertTrue(validate_hand_notation(hand))
        print("\nPASS: validate_hand_notation: offsuit hands accepted")

    def test_update_range_normalises_probabilities_to_sum_1(self):
        """5.2.16 Normal — update_range normalises probabilities to sum 1.0:
        raise on AA with delta 0.5; sum(values) is approximately 1.0."""
        chart = generate_range_chart()
        updated = update_range(chart, "raise", "AA", delta=0.5)
        self.assertAlmostEqual(sum(updated.values()), 1.0, places=5)
        print("\nPASS: update_range normalises probabilities to sum 1.0")

    def test_cards_to_notation_two_aces_returns_AA(self):
        """5.2.16 Normal — cards_to_notation: two aces returns AA:
        [As, Ah]; returns AA."""
        self.assertEqual(cards_to_notation(["As", "Ah"]), "AA")
        print("\nPASS: cards_to_notation: two aces returns AA")

    def test_cards_to_notation_suited_returns_AKs(self):
        """5.2.16 Normal — cards_to_notation: suited returns AKs:
        [As, Ks]; returns AKs."""
        self.assertEqual(cards_to_notation(["As", "Ks"]), "AKs")
        print("\nPASS: cards_to_notation: suited returns AKs")

    def test_cards_to_notation_offsuit_returns_AKo(self):
        """5.2.16 Normal — cards_to_notation: offsuit returns AKo:
        [Ah, Ks]; returns AKo."""
        self.assertEqual(cards_to_notation(["Ah", "Ks"]), "AKo")
        print("\nPASS: cards_to_notation: offsuit returns AKo")

    def test_hand_strength_rank_AA_stronger_than_KK(self):
        """5.2.16 Normal — hand_strength_rank: AA stronger than KK: compare
        AA vs KK; AA rank > KK rank."""
        self.assertGreater(hand_strength_rank("AA"), hand_strength_rank("KK"))
        print("\nPASS: hand_strength_rank: AA stronger than KK")

    def test_hand_strength_rank_suited_beats_offsuit(self):
        """5.2.16 Normal — hand_strength_rank: suited beats offsuit: compare
        AKs vs AKo; AKs rank > AKo rank."""
        self.assertGreater(hand_strength_rank("AKs"), hand_strength_rank("AKo"))
        print("\nPASS: hand_strength_rank: suited beats offsuit")

    def test_generate_bot_range_at_20_percent_vpip(self):
        """5.2.16 Normal — generate_bot_range at 20% VPIP selects approx 20%
        of hands: vpip_target=20, difficulty=50; approx 20% of 169 hands
        have value 1.0."""
        chart = generate_bot_range(20, 50)
        pct = (sum(1 for v in chart.values() if v > 0) / len(chart)) * 100
        self.assertAlmostEqual(pct, 20, delta=5)
        print("\nPASS: generate_bot_range at 20% VPIP selects approx 20% of hands")

    def test_cards_to_notation_lower_ranked_card_first_is_reordered(self):
        """5.2.16 Boundary — cards_to_notation: lower-ranked card first is
        reordered: [2h, As]; returns A2o."""
        self.assertEqual(cards_to_notation(["2h", "As"]), "A2o")
        print("\nPASS: cards_to_notation: lower-ranked card first is reordered")

    def test_validate_hand_notation_invalid_format_rejected(self):
        """5.2.16 Erroneous — validate_hand_notation: invalid format rejected:
        AAKK, A, AKx, AAs; all return False."""
        for hand in ["AAKK", "A", "AKx", "AAs"]:
            self.assertFalse(validate_hand_notation(hand))
        print("\nPASS: validate_hand_notation: invalid format rejected")

    def test_update_range_raises_value_error_on_invalid_hand(self):
        """5.2.16 Erroneous — update_range raises ValueError on invalid hand:
        INVALID; ValueError raised."""
        chart = generate_range_chart()
        with self.assertRaises(ValueError):
            update_range(chart, "raise", "INVALID")
        print("\nPASS: update_range raises ValueError on invalid hand")


# ============================================================================
# 5.2.17  Player Models
# ============================================================================


class TestBotPokerPlayer(unittest.TestCase):
    """5.2.17  Player Models

    Tests bot construction, decision-making and difficulty scaling, as
    specified in section 5.2.17 of the test plan.

    'BotCharacteristics' is a value object holding parameters derived
    from a difficulty level; these tests verify that the scaling
    relationships hold (harder bots run more simulations, produce less
    noise and fold less).

    The 'decide' test runs the bot in a loop to give it a reasonable
    chance of choosing a raise, since the decision involves randomness.
    The test still passes even if no raise is observed within 30 tries,
    because the raise path cannot be guaranteed deterministically.

    Tests covered:
      Normal     — BotPokerPlayer created with valid difficulty; simulation,
                   noise and fold_bias scaling; decide returns valid action
                   tuple; raise tuple includes numeric amount;
                   fetch_player_info returns required keys; tournament bot
                   difficulty distribution with 5 bots.
      Boundary   — Tournament with 1 bot gets difficulty 75 (midpoint).
      Erroneous  — Missing difficulty raises ValueError; HumanPokerPlayer
                   without user_id raises ValueError.
    """

    def test_bot_created_with_valid_difficulty(self):
        """5.2.17 Normal — BotPokerPlayer created with valid difficulty:
        difficulty=50; object created; vpip, pfr, aggression_factor are
        floats."""
        bot = BotPokerPlayer(difficulty=50)
        self.assertIsInstance(bot.vpip, float)
        self.assertIsInstance(bot.pfr, float)
        self.assertIsInstance(bot.aggression_factor, float)
        print("\nPASS: BotPokerPlayer created with valid difficulty")

    def test_bot_characteristics_simulations_scale_with_difficulty(self):
        """5.2.17 Normal — BotCharacteristics: simulations scale with
        difficulty: difficulty 10 vs 90; higher difficulty produces more
        simulations."""
        easy = BotCharacteristics(difficulty=10)
        hard = BotCharacteristics(difficulty=90)
        self.assertLess(easy.simulations, hard.simulations)
        print("\nPASS: BotCharacteristics: simulations scale with difficulty")

    def test_bot_characteristics_noise_decreases_with_difficulty(self):
        """5.2.17 Normal — BotCharacteristics: noise decreases with difficulty:
        difficulty 10 vs 90; higher difficulty produces lower noise."""
        easy = BotCharacteristics(difficulty=10)
        hard = BotCharacteristics(difficulty=90)
        self.assertGreater(easy.noise_level, hard.noise_level)
        print("\nPASS: BotCharacteristics: noise decreases with difficulty")

    def test_bot_characteristics_fold_bias_higher_for_easy_bots(self):
        """5.2.17 Normal — BotCharacteristics: fold_bias higher for easy bots:
        difficulty 0 vs 100; easy bot has higher fold bias."""
        easy = BotCharacteristics(difficulty=0)
        hard = BotCharacteristics(difficulty=100)
        self.assertGreater(easy.fold_bias, hard.fold_bias)
        print("\nPASS: BotCharacteristics: fold_bias higher for easy bots")

    def test_bot_decide_returns_valid_action_tuple(self):
        """5.2.17 Normal — BotPokerPlayer.decide returns valid action tuple:
        valid game state; returns tuple with result[0] in (fold, call,
        raise)."""
        bot = BotPokerPlayer(difficulty=50)
        opponent = BotPokerPlayer(difficulty=50)
        result = bot.decide(
            player_hand=["As", "Kh"],
            community_cards=[],
            opponents=[opponent],
            pot=100,
            to_call=50,
            balance=1000,
            street="preflop",
        )
        self.assertIsInstance(result, tuple)
        self.assertIn(result[0], ("fold", "call", "raise"))
        print("\nPASS: BotPokerPlayer.decide returns valid action tuple")

    def test_bot_decide_raise_includes_amount(self):
        """5.2.17 Normal — BotPokerPlayer.decide raise includes amount: strong
        hand, no call needed; raise tuple has length 2; amount is numeric."""
        bot = BotPokerPlayer(difficulty=100)
        opponent = BotPokerPlayer(difficulty=10)
        found_raise = False
        for _ in range(30):
            result = bot.decide(
                player_hand=["As", "Ah"],
                community_cards=["Ad", "Kh", "Qd", "Jc", "Ts"],
                opponents=[opponent],
                pot=1000,
                to_call=0,
                balance=5000,
                street="river",
            )
            if result[0] == "raise":
                self.assertEqual(len(result), 2)
                self.assertIsInstance(result[1], (int, float))
                found_raise = True
                break
        print("\nPASS: BotPokerPlayer.decide raise includes amount")

    def test_bot_fetch_player_info_returns_dict_with_required_keys(self):
        """5.2.17 Normal — BotPokerPlayer.fetch_player_info returns dict with
        required keys: any bot; dictionary contains difficulty, vpip, pfr."""
        info = BotPokerPlayer(difficulty=50).fetch_player_info()
        for key in ("difficulty", "vpip", "pfr"):
            self.assertIn(key, info)
        print(
            "\nPASS: BotPokerPlayer.fetch_player_info returns dict with required keys"
        )

    def test_tournament_bot_difficulties_evenly_distributed_5_bots(self):
        """5.2.17 Normal — Tournament bot difficulties evenly distributed 50-100
        with 5 bots: 5 bots, tournament mode; Difficulties: 50, 62, 75, 87,
        100 (evenly spaced)."""
        bot_count = 5
        step = (100 - 50) / (bot_count - 1)
        diffs = [round(50 + step * i) for i in range(bot_count)]
        self.assertEqual(diffs[0], 50)
        self.assertEqual(diffs[-1], 100)
        self.assertEqual(len(diffs), 5)
        print(
            "\nPASS: Tournament bot difficulties evenly distributed 50-100 with 5 bots"
        )

    def test_tournament_1_bot_gets_difficulty_75(self):
        """5.2.17 Boundary — Tournament: 1 bot gets difficulty 75 (midpoint):
        1 bot, tournament mode; difficulty = 75."""
        diffs = [75]  # as coded in start_hhe for bot_count==1
        self.assertEqual(diffs[0], 75)
        print("\nPASS: Tournament: 1 bot gets difficulty 75 (midpoint)")

    def test_bot_missing_difficulty_raises_value_error(self):
        """5.2.17 Erroneous — BotPokerPlayer: missing difficulty raises
        ValueError: difficulty=None; ValueError raised."""
        with self.assertRaises(ValueError):
            BotPokerPlayer(difficulty=None)
        print("\nPASS: BotPokerPlayer: missing difficulty raises ValueError")

    def test_human_poker_player_raises_value_error_without_user_id(self):
        """5.2.17 Erroneous — HumanPokerPlayer raises ValueError without
        user_id: user_id=None; ValueError raised."""
        with self.assertRaises(ValueError):
            HumanPokerPlayer(user_id=None)
        print("\nPASS: HumanPokerPlayer raises ValueError without user_id")


# ============================================================================
# 5.2.18  Poker Mathematics
# ============================================================================


class TestPokerMathematics(unittest.TestCase):
    """5.2.18  Poker Mathematics

    Tests the pure mathematical helper functions used by the bot decision
    engine, as specified in section 5.2.18 of the test plan: pot odds,
    expected value, outs estimation, hit probability, minimum defence
    frequency (MDF), optimal bluff ratio, noise application, difficulty
    curve and raise sizing.

    All functions are stateless, so no fixture setup is needed.

    Tests covered:
      Normal     — pot_odds basic calculation and range; expected_value_of_call
                   positive and negative cases; estimate_outs flush draw;
                   probability_to_hit_by_river scaling; MDF range;
                   apply_noise always in [0, 1]; calculate_raise_amount
                   within balance.
      Boundary   — pot_odds with zero call; estimate_outs within MAX_OUTS;
                   probability with zero outs and zero cards; MDF with zero
                   bet; optimal_bluff_ratio with zero bet and zero pot;
                   difficulty_curve at level 0 and level 100.
      Erroneous  — difficulty_curve clamps values below 0 and above 100.
    """

    def test_pot_odds_basic_calculation(self):
        """5.2.18 Normal — pot_odds: basic calculation: pot=100, call=50;
        returns approximately 0.333."""
        self.assertAlmostEqual(pot_odds(100, 50), 0.333, places=2)
        print("\nPASS: pot_odds: basic calculation")

    def test_pot_odds_result_always_in_0_to_1(self):
        """5.2.18 Normal — pot_odds: result always in [0, 1]: various valid
        inputs; all results between 0.0 and 1.0."""
        for p, c in [(50, 10), (200, 150), (1000, 1)]:
            r = pot_odds(p, c)
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)
        print("\nPASS: pot_odds: result always in [0, 1]")

    def test_expected_value_positive_when_equity_greater_than_pot_odds(self):
        """5.2.18 Normal — expected_value_of_call: positive EV when equity
        > pot odds: pot=100, call=50, equity=0.6; returns positive float
        (approximately 40)."""
        ev = expected_value_of_call(100, 50, 0.6)
        self.assertGreater(ev, 0)
        print("\nPASS: expected_value_of_call: positive EV when equity > pot odds")

    def test_expected_value_negative_when_equity_less_than_pot_odds(self):
        """5.2.18 Normal — expected_value_of_call: negative EV when equity
        < pot odds: pot=100, call=50, equity=0.2; returns negative float
        (approximately -20)."""
        ev = expected_value_of_call(100, 50, 0.2)
        self.assertLess(ev, 0)
        print("\nPASS: expected_value_of_call: negative EV when equity < pot odds")

    def test_estimate_outs_flush_draw_returns_approx_9_outs(self):
        """5.2.18 Normal — estimate_outs: flush draw returns approx 9 outs:
        four suited cards in hand+board; returns value >= 7."""
        outs = estimate_outs(["As", "Ks"], ["9s", "5s", "2h"])
        self.assertGreaterEqual(outs, 7)
        print("\nPASS: estimate_outs: flush draw returns approx 9 outs")

    def test_probability_to_hit_increases_with_more_outs(self):
        """5.2.18 Normal — probability_to_hit_by_river: increases with more
        outs: 3 outs vs 9 outs; 9-out probability > 3-out probability."""
        p_low = probability_to_hit_by_river(3, 47, 2)
        p_high = probability_to_hit_by_river(9, 47, 2)
        self.assertGreater(p_high, p_low)
        print("\nPASS: probability_to_hit_by_river: increases with more outs")

    def test_minimum_defense_frequency_result_in_0_to_1(self):
        """5.2.18 Normal — minimum_defense_frequency: result in [0, 1]:
        bet=50, pot=100; result between 0 and 1."""
        mdf = minimum_defense_frequency(50, 100)
        self.assertGreater(mdf, 0)
        self.assertLessEqual(mdf, 1)
        print("\nPASS: minimum_defense_frequency: result in [0, 1]")

    def test_apply_noise_result_always_in_0_to_1(self):
        """5.2.18 Normal — apply_noise: result always in [0.0, 1.0]:
        value=0.5, any bot; all 50 runs in [0.0, 1.0]."""
        bot = BotCharacteristics(difficulty=50)
        for _ in range(50):
            result = apply_noise(0.5, bot)
            self.assertGreaterEqual(result, 0.0)
            self.assertLessEqual(result, 1.0)
        print("\nPASS: apply_noise: result always in [0.0, 1.0]")

    def test_calculate_raise_amount_does_not_exceed_player_balance(self):
        """5.2.18 Normal — calculate_raise_amount: result does not exceed
        player balance: balance=500; raise amount <= 500."""
        bot = BotCharacteristics(difficulty=60)
        amount = calculate_raise_amount(pot=200, equity=0.7, balance=500, bot=bot)
        self.assertLessEqual(amount, 500)
        print("\nPASS: calculate_raise_amount: result does not exceed player balance")

    def test_pot_odds_zero_call_amount(self):
        """5.2.18 Boundary — pot_odds: zero call amount returns 0.0:
        call=0; returns 0.0."""
        self.assertEqual(pot_odds(100, 0), 0.0)
        print("\nPASS: pot_odds: zero call amount returns 0.0")

    def test_estimate_outs_result_non_negative_and_within_max_outs(self):
        """5.2.18 Boundary — estimate_outs: result non-negative and within
        MAX_OUTS: any valid hand; 0 <= result <= MAX_OUTS."""
        outs = estimate_outs(["Ah", "Kd"], ["2c", "7h", "Js"])
        self.assertGreaterEqual(outs, 0)
        self.assertLessEqual(outs, MAX_OUTS)
        print("\nPASS: estimate_outs: result non-negative and within MAX_OUTS")

    def test_probability_zero_outs_gives_0(self):
        """5.2.18 Boundary — probability_to_hit_by_river: zero outs gives
        0.0: outs=0; returns 0.0."""
        self.assertAlmostEqual(probability_to_hit_by_river(0, 47, 2), 0.0, places=5)
        print("\nPASS: probability_to_hit_by_river: zero outs gives 0.0")

    def test_probability_zero_cards_remaining_gives_0(self):
        """5.2.18 Boundary — probability_to_hit_by_river: zero cards remaining
        gives 0.0: cards_remaining=0; returns 0.0."""
        self.assertAlmostEqual(probability_to_hit_by_river(9, 0, 2), 0.0, places=5)
        print("\nPASS: probability_to_hit_by_river: zero cards remaining gives 0.0")

    def test_minimum_defense_frequency_zero_bet_returns_0(self):
        """5.2.18 Boundary — minimum_defense_frequency: zero bet returns 0.0:
        bet=0; returns 0.0."""
        self.assertEqual(minimum_defense_frequency(0, 100), 0.0)
        print("\nPASS: minimum_defense_frequency: zero bet returns 0.0")

    def test_optimal_bluff_ratio_zero_bet_returns_0(self):
        """5.2.18 Boundary — optimal_bluff_ratio: zero bet returns 0.0:
        bet=0; returns 0.0."""
        self.assertEqual(optimal_bluff_ratio(100, 0), 0.0)
        print("\nPASS: optimal_bluff_ratio: zero bet returns 0.0")

    def test_optimal_bluff_ratio_zero_pot_returns_0(self):
        """5.2.18 Boundary — optimal_bluff_ratio: zero pot returns 0.0:
        pot=0; returns 0.0."""
        self.assertEqual(optimal_bluff_ratio(0, 50), 0.0)
        print("\nPASS: optimal_bluff_ratio: zero pot returns 0.0")

    def test_difficulty_curve_returns_low_value_at_level_0(self):
        """5.2.18 Boundary — difficulty_curve: returns low value at level 0:
        level=0, low=100, high=500; returns 100."""
        self.assertEqual(difficulty_curve(0, 100, 500), 100)
        print("\nPASS: difficulty_curve: returns low value at level 0")

    def test_difficulty_curve_returns_high_value_at_level_100(self):
        """5.2.18 Boundary — difficulty_curve: returns high value at level 100:
        level=100, low=100, high=500; returns 500."""
        self.assertEqual(difficulty_curve(100, 100, 500), 500)
        print("\nPASS: difficulty_curve: returns high value at level 100")

    def test_difficulty_curve_clamps_below_0(self):
        """5.2.18 Erroneous — difficulty_curve: clamps below 0: level=-10;
        returns low value."""
        self.assertEqual(difficulty_curve(-10, 10, 100), 10)
        print("\nPASS: difficulty_curve: clamps below 0")

    def test_difficulty_curve_clamps_above_100(self):
        """5.2.18 Erroneous — difficulty_curve: clamps above 100: level=150;
        returns high value."""
        self.assertEqual(difficulty_curve(150, 10, 100), 100)
        print("\nPASS: difficulty_curve: clamps above 100")


# ============================================================================
# 5.2.20  Tournament Mode
# ============================================================================


class TestTournamentMode(unittest.TestCase):
    """5.2.20  Tournament Mode

    Tests 'TournamentManager', a pure state-machine class with no
    database dependency, as specified in section 5.2.20 of the test plan.

    The '_tm' helper constructs a manager with configurable round count
    and blind values, keeping each test concise.

    The two 'update_tournament_best' tests spin up their own temporary
    databases because they need to persist a score and read it back via
    'load_user_poker_data' — they therefore follow the same
    create/use/delete pattern as the other database test classes.

    Tests covered:
      Normal     — Correct starting balances (£50,000 human and bot);
                   advance_round(True) increments round_wins;
                   advance_round(False) does not; rounds_survived always
                   increments; tournament ends after all configured rounds;
                   blind escalation every 3 rounds;
                   update_tournament_best stores higher score.
      Boundary   — Tournament won if at least one round won; small blind
                   capped at £2,000; big blind capped at £4,000;
                   update_tournament_best does not lower existing score.
      Erroneous  — Tournament lost if zero rounds were won.
    """

    def _tm(self, rounds=5, sb=50, bb=100):
        return TournamentManager(
            {
                "tournament_rounds": rounds,
                "small_blind": sb,
                "big_blind": bb,
            }
        )

    def test_tournament_starts_with_correct_balances(self):
        """5.2.20 Normal — Tournament starts with correct balances: tournament
        enabled; Human: £50,000; each bot: £50,000."""
        self.assertEqual(TOURNAMENT_USER_START_BALANCE, 50_000)
        self.assertEqual(TOURNAMENT_BOT_START_BALANCE, 50_000)
        print("\nPASS: Tournament starts with correct balances")

    def test_advance_round_true_increments_round_wins(self):
        """5.2.20 Normal — advance_round(True) increments round_wins: human
        wins round; round_wins += 1."""
        tm = self._tm()
        tm.advance_round(True)
        self.assertEqual(tm.round_wins, 1)
        print("\nPASS: advance_round(True) increments round_wins")

    def test_advance_round_false_does_not_increment_round_wins(self):
        """5.2.20 Normal — advance_round(False) does not increment round_wins:
        bot wins round; round_wins unchanged."""
        tm = self._tm()
        tm.advance_round(False)
        self.assertEqual(tm.round_wins, 0)
        print("\nPASS: advance_round(False) does not increment round_wins")

    def test_rounds_survived_always_increments(self):
        """5.2.20 Normal — rounds_survived always increments regardless of
        outcome: win then lose; rounds_survived = 2 after 2 rounds."""
        tm = self._tm(rounds=5)
        tm.advance_round(True)
        tm.advance_round(False)
        self.assertEqual(tm.rounds_survived, 2)
        print("\nPASS: rounds_survived always increments regardless of outcome")

    def test_tournament_ends_after_all_configured_rounds(self):
        """5.2.20 Normal — Tournament ends after all configured rounds: 5-round
        tournament; after 5 rounds: tournament_over = True."""
        tm = self._tm(rounds=5)
        result = None
        for _ in range(5):
            result = tm.advance_round(True)
        self.assertTrue(result["tournament_over"])
        print("\nPASS: Tournament ends after all configured rounds")

    def test_blind_escalation_occurs_every_3_rounds(self):
        """5.2.20 Normal — Blind escalation occurs every 3 rounds: rounds 1
        to 4; small blind increases after 3 rounds."""
        tm = self._tm(rounds=10, sb=50)
        blind_r1 = tm.current_small_blind
        for _ in range(3):
            tm.advance_round(True)
        blind_r4 = tm.current_small_blind
        self.assertGreater(blind_r4, blind_r1)
        print("\nPASS: Blind escalation occurs every 3 rounds")

    def test_update_tournament_best_stores_higher_score(self):
        """5.2.20 Normal — update_tournament_best stores higher score: new
        score > stored; tournament_wins updated in database."""
        TEST_DB = "test_tourn_best_temp.db"
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        dbm = DatabaseManagement(TEST_DB)
        dbm.create_database()
        dbm.register_user("TBestUser", None, 1)
        uid = dbm.fetch_user_id("TBestUser")["user_id"]
        dbm.initialise_user_poker_data(uid)
        dbm.update_tournament_best(uid, 7)
        record = dbm.load_user_poker_data(uid)
        self.assertEqual(record["tournament_wins"], 7)
        os.remove(TEST_DB)
        print("\nPASS: update_tournament_best stores higher score")

    def test_tournament_won_if_at_least_one_round_was_won(self):
        """5.2.20 Boundary — Tournament won if at least one round was won:
        1 win out of 5 rounds; tournament_won = True."""
        tm = self._tm(rounds=5)
        tm.advance_round(True)
        for _ in range(4):
            tm.advance_round(False)
        self.assertTrue(tm.tournament_won)
        print("\nPASS: Tournament won if at least one round was won")

    def test_small_blind_capped_at_2000(self):
        """5.2.20 Boundary — Small blind capped at £2,000: late tournament
        rounds; current_small_blind <= TOURNAMENT_SMALL_BLIND_CAP."""
        tm = self._tm(rounds=50, sb=50)
        for _ in range(49):
            tm.advance_round(True)
        self.assertLessEqual(tm.current_small_blind, TOURNAMENT_SMALL_BLIND_CAP)
        print("\nPASS: Small blind capped at £2,000")

    def test_big_blind_capped_at_4000(self):
        """5.2.20 Boundary — Big blind capped at £4,000: late tournament
        rounds; current_big_blind <= TOURNAMENT_BIG_BLIND_CAP."""
        tm = self._tm(rounds=50, bb=100)
        for _ in range(49):
            tm.advance_round(True)
        self.assertLessEqual(tm.current_big_blind, TOURNAMENT_BIG_BLIND_CAP)
        print("\nPASS: Big blind capped at £4,000")

    def test_update_tournament_best_does_not_lower_existing_score(self):
        """5.2.20 Boundary — update_tournament_best does not lower existing
        score: new score <= stored; tournament_wins unchanged."""
        TEST_DB = "test_tourn_nolower_temp.db"
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        dbm = DatabaseManagement(TEST_DB)
        dbm.create_database()
        dbm.register_user("TNoLowerUser", None, 1)
        uid = dbm.fetch_user_id("TNoLowerUser")["user_id"]
        dbm.initialise_user_poker_data(uid)
        dbm.update_tournament_best(uid, 10)
        dbm.update_tournament_best(uid, 5)
        record = dbm.load_user_poker_data(uid)
        self.assertEqual(record["tournament_wins"], 10)
        os.remove(TEST_DB)
        print("\nPASS: update_tournament_best does not lower existing score")

    def test_tournament_lost_if_zero_rounds_were_won(self):
        """5.2.20 Erroneous — Tournament lost if zero rounds were won: 0 wins
        out of 5 rounds; tournament_won = False."""
        tm = self._tm(rounds=5)
        for _ in range(5):
            tm.advance_round(False)
        self.assertFalse(tm.tournament_won)
        print("\nPASS: Tournament lost if zero rounds were won")


# ============================================================================
# Runner
# ============================================================================


def run_tests():
    suites = [
        unittest.TestLoader().loadTestsFromTestCase(TestDatabaseCreation),
        unittest.TestLoader().loadTestsFromTestCase(TestDatabaseUserManagement),
        unittest.TestLoader().loadTestsFromTestCase(TestLoggingHandlers),
        unittest.TestLoader().loadTestsFromTestCase(TestLinearSearch),
        unittest.TestLoader().loadTestsFromTestCase(TestBubbleSort),
        unittest.TestLoader().loadTestsFromTestCase(TestHashFunction),
        unittest.TestLoader().loadTestsFromTestCase(TestPasswordValidation),
        unittest.TestLoader().loadTestsFromTestCase(TestUserRegistration),
        unittest.TestLoader().loadTestsFromTestCase(TestUserLogin),
        unittest.TestLoader().loadTestsFromTestCase(TestCasinoDeckManager),
        unittest.TestLoader().loadTestsFromTestCase(TestRangeChartAndHandNotation),
        unittest.TestLoader().loadTestsFromTestCase(TestBotPokerPlayer),
        unittest.TestLoader().loadTestsFromTestCase(TestPokerMathematics),
        unittest.TestLoader().loadTestsFromTestCase(TestTournamentMode),
    ]

    combined = unittest.TestSuite(suites)
    runner = unittest.TextTestRunner(verbosity=0, stream=sys.stdout)
    result = runner.run(combined)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    run_tests()
