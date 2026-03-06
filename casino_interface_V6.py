from tkinter import (
    Tk,
    Label,
    Button,
    Frame,
    Entry,
    messagebox,
    Spinbox,
    IntVar,
    StringVar,
    BooleanVar,
    Scale,
    HORIZONTAL,
)
from tkinter.ttk import Combobox
from gui_helpers_V6 import set_view, fetch_font_settings

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
    "tournament_players": 4,  # total players including user
    "win_criteria": "eliminate_all",
    "win_criteria_target": 1000,  # used when criteria is "earn_target"
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


# Casino_Interface


class Casino_Interface:
    """
    Main casino interface for users and administrators. Handles login,
    account management, game selection, and mode-specific rules such as
    tournament, gauntlet and endless play.
    """

    def __init__(self, administrator, user_data=None):
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

        from database_management_and_logging_V6 import DatabaseManagement

        self.dbm = DatabaseManagement()

        self.styles = fetch_font_settings(self.interface_root)
        self.signed_in = False

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
            self.signed_in = True

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
            stats = self.dbm.fetch_player_statistics(user_id)
            return int(stats["rounds_played"]) if stats else 0
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
            stats = self.dbm.fetch_player_statistics(user_id)
            if not stats:
                return 0, 0
            gauntlet_pb = int(stats.get("gauntlet_max_rounds", 0))
            endless_pb = int(stats.get("endless_high_score", 0))
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
        acct_text = "Account Information" if linked else "Sign in to access user info"
        Button(
            frame,
            text=acct_text,
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
        set_view(self, lambda f: self.username_input(f, is_register=True))

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
        set_view(self, lambda f: self.username_input(f, is_register=False))

    def username_input(self, frame, is_register):
        """
        Displays a username input form used for both registration and login.

        Args:
            frame (Frame): The parent frame to build the view into.
            is_register (bool): If True, validates uniqueness for registration.
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

            if is_register and self.dbm.fetch_user_presence(username).get("found"):
                messagebox.showerror("Error", "Username already exists.")
                return

            if is_register:
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
        from check_systems_V6 import passwords_confirmation

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
            set_view(self, lambda f: self.username_input(f, is_register=False))
            return

        Label(
            frame,
            text=f"Login for '{username}'",
            font=self.styles["heading"],
        ).pack(pady=10)

        Label(frame, text="Enter Password:", font=self.styles["text"]).pack(pady=5)

        pwd_entry = Entry(frame, show="*", font=self.styles["text"])
        pwd_entry.pack(pady=5)

        def submit_password():
            """Verifies the password and navigates accordingly."""
            password = pwd_entry.get().strip()
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
                pwd_entry.delete(0, "end")
                set_view(self, lambda f: self.username_input(f, is_register=False))

            else:
                messagebox.showerror("Error", "Username not found or login failed.")
                set_view(self, lambda f: self.username_input(f, is_register=False))

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

        for key, value in [
            ("Username", record["username"]),
            ("Account Type", "Registered" if record["registered"] else "Guest"),
            ("Balance", record["balance"]),
            ("Created", record["created_at"]),
            (
                "Account Status",
                (
                    f"Terminated\nAt {record['terminated_at']}\n"
                    f"Reason: \"{record['termination_reason']}\""
                    if record["terminated"]
                    else "Active"
                ),
            ),
        ]:
            Label(
                frame,
                text=f"{key}: {value}",
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

    # Game settings

    def game_settings(self, frame):
        """
        Displays the Harrogate Hold 'Em Setting Modifier panel.

        Requires an account to be linked; redirects if not.

        Sections
        --
        1. Table Settings — bot count, balances, blinds
        2. Bot Difficulty — global slider
        3. Tournament Mode — gated behind TOURNAMENT_MIN_ROUNDS
        4. Gauntlet Mode — styled card with ramp preview and launch button
        5. Endless Mode — styled card with high-score and launch button
        6. Notes — reference information

        Args:
            frame (Frame): The parent frame to build the view into.
        """
        if not self.require_linked("Game Settings"):
            set_view(self, self.casino_menu)
            return

        Label(
            frame,
            text="Game Settings",
            font=self.styles["heading"],
        ).pack(pady=(10, 2))

        Label(
            frame,
            text="Configure Harrogate Hold 'Em, Tournament, Gauntlet, and Endless modes.",
            font=self.styles["emphasis"],
        ).pack(pady=(0, 8))

        # Scrollable content area
        from tkinter import Canvas, Scrollbar

        container = Frame(frame)
        container.pack(expand=True, fill="both")

        canvas = Canvas(container, highlightthickness=0)
        scrollbar = Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = Frame(canvas)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(win_id, width=e.width),
        )

        # Layout helpers

        def section_label(text, colour="#555555"):
            """Displays a coloured section header with a divider line."""
            Label(
                inner,
                text=text,
                font=self.styles["subheading"],
                anchor="w",
                pady=5,
            ).pack(fill="x", padx=20, pady=(14, 0))
            Frame(inner, height=2, bg=colour).pack(fill="x", padx=20, pady=(0, 4))

        def row(label_text, widget_factory):
            """Creates a label + widget pair on a single row."""
            r = Frame(inner)
            r.pack(fill="x", padx=20, pady=3)
            Label(
                r,
                text=label_text,
                font=self.styles["text"],
                width=30,
                anchor="w",
            ).pack(side="left")
            w = widget_factory(r)
            w.pack(side="left", padx=10)
            return w

        def mode_card(
            parent,
            bg_colour,
            border_colour,
            title_text,
            title_fg,
            body_widgets_fn,
            launch_text=None,
            launch_command=None,
        ):
            """
            Displays a styled card with a coloured banner and content area.

            An optional launch button may be appended if 'launch_text' is
            provided; this keeps the helper useful for both game modes and the
            regular settings sections.

            Args:
                parent: Parent widget.
                bg_colour: Card background colour.
                border_colour: Left-border accent colour.
                title_text: Text shown in the banner.
                title_fg: Banner text colour.
                body_widgets_fn: Callable(inner_frame) that adds widgets to the
                                 card body.
                launch_text (str, optional): Label for the launch button.
                launch_command (callable, optional): Callback for the launch
                                                    button.
            """
            # Outer border frame (provides left-side accent bar)
            outer = Frame(parent, bg=border_colour)
            outer.pack(fill="x", padx=20, pady=6)

            # Left accent bar
            Frame(outer, width=6, bg=border_colour).pack(side="left", fill="y")

            # Card body
            card = Frame(outer, bg=bg_colour)
            card.pack(side="left", fill="both", expand=True)

            # Banner
            banner = Frame(card, bg=border_colour)
            banner.pack(fill="x")
            Label(
                banner,
                text=title_text,
                font=self.styles["subheading"],
                bg=border_colour,
                fg=title_fg,
                anchor="w",
                padx=10,
                pady=6,
            ).pack(fill="x")

            # Content area
            body = Frame(card, bg=bg_colour)
            body.pack(fill="x", padx=12, pady=8)
            body_widgets_fn(body)

            # Optional launch button row
            if launch_text and launch_command:
                button_row = Frame(card, bg=bg_colour)
                button_row.pack(fill="x", padx=12, pady=(0, 10))
                Button(
                    button_row,
                    text=launch_text,
                    font=self.styles["button"],
                    bg=border_colour,
                    fg=title_fg,
                    activebackground=bg_colour,
                    relief="flat",
                    bd=0,
                    padx=14,
                    pady=6,
                    command=launch_command,
                ).pack(side="left")

        # Live variables
        v_bot_count = IntVar(value=self.settings["bot_count"])
        v_bot_balance = StringVar(value=str(self.settings["bot_balance"]))
        v_small_blind = StringVar(value=str(self.settings["small_blind"]))
        v_big_blind = StringVar(value=str(self.settings["big_blind"]))
        v_bot_diff = IntVar(value=self.settings["bot_difficulty"])

        v_tournament = BooleanVar(value=self.settings["tournament_mode"])
        v_t_rounds = IntVar(value=self.settings["tournament_rounds"])
        v_t_players = IntVar(value=self.settings["tournament_players"])
        v_win_criteria = StringVar(value=self.settings["win_criteria"])
        v_win_target = StringVar(value=str(self.settings["win_criteria_target"]))

        v_gauntlet_diff = IntVar(
            value=self.settings.get(
                "gauntlet_start_difficulty", GAUNTLET_START_DIFFICULTY
            )
        )

        # Colour‑coded cards for each setting section

        # Helpers to build the contents of each card
        def build_table_body(body):
            row(
                "Number of bots  (1–9):",
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
                    p,
                    textvariable=v_bot_balance,
                    width=10,
                    font=self.styles["text"],
                ),
            )

            row(
                "Small blind (£):",
                lambda p: Entry(
                    p,
                    textvariable=v_small_blind,
                    width=10,
                    font=self.styles["text"],
                ),
            )

            row(
                "Big blind (£):",
                lambda p: Entry(
                    p,
                    textvariable=v_big_blind,
                    width=10,
                    font=self.styles["text"],
                ),
            )

        mode_card(
            inner,
            bg_colour="#e8f3fa",
            border_colour="#4a7a9b",
            title_text="Table Settings",
            title_fg="#ffffff",
            body_widgets_fn=build_table_body,
        )

        def build_botdiff_body(body):
            diff_frame = Frame(body)
            diff_frame.pack(fill="x", padx=20, pady=4)

            Label(
                diff_frame,
                text="Global bot difficulty  (0 = easy, 100 = hard):",
                font=self.styles["text"],
            ).pack(anchor="w")

            diff_label = Label(
                diff_frame,
                text=f"Current: {v_bot_diff.get()}",
                font=self.styles["emphasis"],
            )
            diff_label.pack(anchor="w")

            Scale(
                diff_frame,
                from_=0,
                to=100,
                orient=HORIZONTAL,
                variable=v_bot_diff,
                font=self.styles["text"],
                length=400,
                command=lambda val: diff_label.config(
                    text=f"Current: {int(float(val))}"
                ),
            ).pack(anchor="w", pady=4)

        mode_card(
            inner,
            bg_colour="#e8f3fa",
            border_colour="#4a7a9b",
            title_text="Bot Difficulty  (Standard Mode)",
            title_fg="#ffffff",
            body_widgets_fn=build_botdiff_body,
        )

        def build_tournament_body(body):
            rounds_played = self.fetch_rounds_played()
            rounds_needed = max(0, TOURNAMENT_MIN_ROUNDS - rounds_played)

            if rounds_needed > 0:
                Label(
                    body,
                    text=(
                        f"Tournament Mode is locked.\n\n"
                        f"You have played {rounds_played} round"
                        f"{'s' if rounds_played != 1 else ''}.  "
                        f"Play {rounds_needed} more round"
                        f"{'s' if rounds_needed != 1 else ''} of Harrogate Hold 'Em "
                        f"to unlock Tournament Mode.\n\n"
                        f"This ensures your hand-range statistics are meaningful "
                        f"enough to support a fair tournament experience."
                    ),
                    font=self.styles["emphasis"],
                    anchor="w",
                    justify="left",
                    wraplength=500,
                ).pack(fill="x", padx=20, pady=8)

                self.settings["tournament_mode"] = False
                v_tournament.set(False)

            else:
                t_toggle_frame = Frame(body)
                t_toggle_frame.pack(fill="x", padx=20, pady=4)

                Label(
                    t_toggle_frame,
                    text="Enable Tournament Mode:",
                    font=self.styles["text"],
                    width=30,
                    anchor="w",
                ).pack(side="left")

                from tkinter import Checkbutton as CBN

                CBN(
                    t_toggle_frame,
                    variable=v_tournament,
                    font=self.styles["text"],
                ).pack(side="left")

                Label(
                    body,
                    text=f"Rounds played: {rounds_played}.",
                    font=self.styles["emphasis"],
                    anchor="w",
                ).pack(fill="x", padx=20, pady=(0, 4))

                section_label(
                    "Tournament Options:",
                    "#9b7bb8",
                )

                row(
                    "Number of rounds:",
                    lambda p: Spinbox(
                        p,
                        from_=1,
                        to=50,
                        textvariable=v_t_rounds,
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
                        textvariable=v_t_players,
                        width=6,
                        font=self.styles["text"],
                    ),
                )

                crit_frame = Frame(body)
                crit_frame.pack(fill="x", padx=20, pady=4)

                Label(
                    crit_frame,
                    text="Round win criteria:",
                    font=self.styles["text"],
                    width=30,
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
                crit_box.pack(side="left", padx=10)

                crit_desc = Label(
                    body,
                    text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), ""),
                    font=self.styles["emphasis"],
                    anchor="w",
                )
                crit_desc.pack(fill="x", padx=20)

                target_frame = Frame(body)
                Label(
                    target_frame,
                    text="Earn target (£):",
                    font=self.styles["text"],
                    width=30,
                    anchor="w",
                ).pack(side="left")
                Entry(
                    target_frame,
                    textvariable=v_win_target,
                    width=12,
                    font=self.styles["text"],
                ).pack(side="left", padx=10)

                def on_criteria_change(event=None):
                    crit_desc.config(
                        text=TOURNAMENT_WIN_CRITERIA.get(v_win_criteria.get(), "")
                    )
                    if v_win_criteria.get() == "earn_target":
                        target_frame.pack(fill="x", padx=20, pady=4)
                    else:
                        target_frame.pack_forget()

                crit_box.bind("<<ComboboxSelected>>", on_criteria_change)

                if v_win_criteria.get() == "earn_target":
                    target_frame.pack(fill="x", padx=20, pady=4)

        mode_card(
            inner,
            bg_colour="#f4e8ff",
            border_colour="#7b68ee",
            title_text="Tournament Mode",
            title_fg="#ffffff",
            body_widgets_fn=build_tournament_body,
        )

        # Gauntlet Mode card
        section_label("Gauntlet Mode", "#b85c38")

        gauntlet_pb, _ = self.fetch_special_scores()

        # Ramp preview
        def ramp_preview_text(start_diff):
            """Returns a formatted ramp schedule string for display."""
            lines = []
            d = max(0, min(90, start_diff))
            prev_round = 1
            for interval in range(9):
                rnd_start = interval * GAUNTLET_RAMP_INTERVAL + 1
                rnd_end = rnd_start + GAUNTLET_RAMP_INTERVAL - 1
                diff_val = min(100, d + interval * GAUNTLET_DIFFICULTY_STEP)
                if diff_val > 100:
                    break
                lines.append(
                    f"Rounds {rnd_start:>2}–{rnd_end:<2}  →  Difficulty {diff_val}"
                )
                if diff_val == 100:
                    lines.append(
                        f"Round  {rnd_end + 1}+      →  Difficulty 100  (maximum)"
                    )
                    break
            return "\n".join(lines)

        def build_gauntlet_body(body):
            """Populates the Gauntlet card body."""
            Label(
                body,
                text=(
                    f"Face {GAUNTLET_BOT_COUNT} bots in an escalating challenge.\n"
                    f"Bot difficulty increases by +{GAUNTLET_DIFFICULTY_STEP} "
                    f"every {GAUNTLET_RAMP_INTERVAL} rounds.  Survive as long as you can."
                ),
                font=self.styles["text"],
                anchor="w",
                justify="left",
                bg="#2a1810",
                fg="#e8c8b0",
                wraplength=460,
            ).pack(fill="x", pady=(0, 6))

            # Personal best badge
            pb_text = (
                f"🏆  Personal best:  {gauntlet_pb} round"
                f"{'s' if gauntlet_pb != 1 else ''}"
                if gauntlet_pb > 0
                else "No score yet — be the first!"
            )
            Label(
                body,
                text=pb_text,
                font=self.styles["emphasis"],
                anchor="w",
                bg="#2a1810",
                fg="#f0a060",
            ).pack(fill="x", pady=(0, 8))

            # Starting difficulty row
            diff_row = Frame(body, bg="#2a1810")
            diff_row.pack(fill="x", pady=(0, 6))

            Label(
                diff_row,
                text="Starting difficulty:",
                font=self.styles["text"],
                bg="#2a1810",
                fg="#e8c8b0",
                width=20,
                anchor="w",
            ).pack(side="left")

            Spinbox(
                diff_row,
                from_=0,
                to=90,
                increment=10,
                textvariable=v_gauntlet_diff,
                width=5,
                font=self.styles["text"],
                bg="#3a2010",
                fg="#e8c8b0",
                command=lambda: ramp_lbl.config(
                    text=ramp_preview_text(v_gauntlet_diff.get())
                ),
            ).pack(side="left", padx=8)

            Label(
                diff_row,
                text="(steps of 10, from 0 to 90)",
                font=self.styles["emphasis"],
                bg="#2a1810",
                fg="#a08060",
            ).pack(side="left")

            # Live ramp preview
            Label(
                body,
                text="Difficulty ramp preview:",
                font=self.styles["emphasis"],
                anchor="w",
                bg="#2a1810",
                fg="#c8a070",
            ).pack(fill="x", pady=(4, 2))

            ramp_lbl = Label(
                body,
                text=ramp_preview_text(v_gauntlet_diff.get()),
                font=self.styles["text"],
                anchor="w",
                justify="left",
                bg="#1e1008",
                fg="#c8a878",
                padx=10,
                pady=6,
                relief="groove",
            )
            ramp_lbl.pack(fill="x")

            # Bind spinbox Entry widget so the preview updates on keystroke too
            diff_row.winfo_children()[1].bind(
                "<KeyRelease>",
                lambda e: ramp_lbl.config(
                    text=ramp_preview_text(
                        max(0, min(90, int(v_gauntlet_diff.get() or 0)))
                    )
                ),
            )

        def launch_gauntlet():
            """Saves starting difficulty and launches Gauntlet Mode."""
            sd = max(0, min(90, int(v_gauntlet_diff.get())))
            self.settings["gauntlet_start_difficulty"] = sd
            self.settings["gauntlet_mode"] = True
            self.settings["endless_mode"] = False
            self.start_gauntlet(sd)

        mode_card(
            inner,
            bg_colour="#2a1810",
            border_colour="#b85c38",
            title_text="⚔  Gauntlet Mode",
            title_fg="#ffe8d0",
            body_widgets_fn=build_gauntlet_body,
            launch_text="⚔  Start Gauntlet",
            launch_command=launch_gauntlet,
        )

        # Endless Mode card
        section_label("Endless Mode", "#2e6b4f")

        _, endless_pb = self.fetch_special_scores()

        def build_endless_body(body):
            """Populates the Endless card body."""
            Label(
                body,
                text=(
                    f"Face the maximum {ENDLESS_BOT_COUNT} bots simultaneously.\n"
                    f"Bot difficulties are randomly distributed (0–100) and "
                    f"reshuffled every round. There is no win condition — "
                    f"survive as long as possible."
                ),
                font=self.styles["text"],
                anchor="w",
                justify="left",
                bg="#0e2018",
                fg="#a8d8b8",
                wraplength=460,
            ).pack(fill="x", pady=(0, 6))

            # High-score badge
            hs_text = (
                f"High score:  {endless_pb} round"
                f"{'s' if endless_pb != 1 else ''} survived"
                if endless_pb > 0
                else "No score yet — be the first!"
            )
            Label(
                body,
                text=hs_text,
                font=self.styles["emphasis"],
                anchor="w",
                bg="#0e2018",
                fg="#60d090",
            ).pack(fill="x", pady=(0, 6))

            # Stats row
            stats_frame = Frame(body, bg="#0e2018")
            stats_frame.pack(fill="x", pady=(0, 4))

            for stat_text in (
                f"Opponents:  {ENDLESS_BOT_COUNT} bots",
                "Difficulties:  0–100 random",
                "Win condition:  none",
            ):
                Label(
                    stats_frame,
                    text=f"  •  {stat_text}",
                    font=self.styles["text"],
                    bg="#0e2018",
                    fg="#80c898",
                    anchor="w",
                ).pack(anchor="w")

        def launch_endless():
            """Launches Endless Mode."""
            self.settings["endless_mode"] = True
            self.settings["gauntlet_mode"] = False
            self.start_endless()

        mode_card(
            inner,
            bg_colour="#0e2018",
            border_colour="#2e6b4f",
            title_text="∞  Endless Mode",
            title_fg="#c0ffdc",
            body_widgets_fn=build_endless_body,
            launch_text="∞  Start Endless",
            launch_command=launch_endless,
        )

        # Notes
        section_label("Notes", "#666666")

        Label(
            inner,
            text=(
                "- Standard Mode uses the Table Settings and Bot Difficulty above.\n"
                "- Blind escalation in Tournament: see win criteria for escalation rules.\n"
                "- All monetary values must be positive integers.\n"
                "- Big blind must be ≥ small blind.\n"
                f"- Tournament Mode requires {TOURNAMENT_MIN_ROUNDS} rounds played to unlock.\n"
                f"- Gauntlet Mode uses {GAUNTLET_BOT_COUNT} bots; difficulty caps at 100.\n"
                f"- Endless Mode always uses {ENDLESS_BOT_COUNT} bots with random difficulties.\n"
                "- Gauntlet and Endless scores are saved to your profile automatically."
            ),
            font=self.styles["text"],
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=20, pady=6)

        # Bottom buttons
        button_frame = Frame(frame)
        button_frame.pack(pady=10)

        def save_settings():
            """Validates and saves Standard and Tournament settings."""
            errors = []

            try:
                bc = int(v_bot_count.get())
                assert 1 <= bc <= 9
            except Exception:
                errors.append("Bot count must be between 1 and 9.")
                bc = self.settings["bot_count"]

            try:
                bb_val = int(v_bot_balance.get())
                assert bb_val > 0
            except Exception:
                errors.append("Bot balance must be a positive integer.")
                bb_val = self.settings["bot_balance"]

            try:
                sb = int(v_small_blind.get())
                assert sb > 0
            except Exception:
                errors.append("Small blind must be a positive integer.")
                sb = self.settings["small_blind"]

            try:
                bigb = int(v_big_blind.get())
                assert bigb >= sb
            except Exception:
                errors.append("Big blind must be ≥ small blind.")
                bigb = self.settings["big_blind"]

            try:
                diff = max(0, min(100, int(v_bot_diff.get())))
            except Exception:
                diff = self.settings["bot_difficulty"]

            try:
                t_rounds = int(v_t_rounds.get())
                assert t_rounds >= 1
            except Exception:
                errors.append("Tournament rounds must be ≥ 1.")
                t_rounds = self.settings["tournament_rounds"]

            try:
                t_players = int(v_t_players.get())
                assert 2 <= t_players <= 10
            except Exception:
                errors.append("Tournament players must be between 2 and 10.")
                t_players = self.settings["tournament_players"]

            try:
                w_target = int(v_win_target.get())
                assert w_target > 0
            except Exception:
                errors.append("Win target must be a positive integer.")
                w_target = self.settings["win_criteria_target"]

            try:
                g_start = max(0, min(90, int(v_gauntlet_diff.get())))
            except Exception:
                g_start = self.settings.get(
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
                    "bot_count": bc,
                    "bot_balance": bb_val,
                    "small_blind": sb,
                    "big_blind": bigb,
                    "bot_difficulty": diff,
                    "tournament_mode": tournament_on,
                    "tournament_rounds": t_rounds,
                    "tournament_players": t_players,
                    "win_criteria": v_win_criteria.get(),
                    "win_criteria_target": w_target,
                    "gauntlet_start_difficulty": g_start,
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

            ranked = sorted(
                [p for p in all_data if p.get(key, 0)],
                key=lambda p: p[key],
                reverse=True,
            )[:5]

            if not ranked:
                Label(
                    frame,
                    text="No scores recorded yet.",
                    font=self.styles["text"],
                ).pack(pady=4)
                return

            for i, entry in enumerate(ranked, 1):
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
                    text=f"  {i}.  {username:<20}  {score} {unit}",
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
        from game_rules_V6 import ShowGameRules

        ShowGameRules(self.interface_root).show_whitejoe_rules(
            lambda: self.start_whitejoe()
        )

    def start_whitejoe(self):
        """
        Instantiates and launches the WhiteJoe game, passing the current
        user data.
        """
        from whitejoe_V6 import WhiteJoe

        WhiteJoe(self.user_data)

        self.interface_root.destroy()

    def harrogate_hold_em_rules(self):
        """
        Launches the Harrogate Hold 'Em rules window. Requires a linked
        account. On the user agreeing to the rules, starts the game.
        """
        if not self.require_linked("Harrogate Hold 'Em"):
            return
        from game_rules_V6 import ShowGameRules

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
        from harrogate_hold_em_V6 import HarrogateHoldEm, DEFAULT_BOT_ROSTER
        import random

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
        bots = [[roster[i % len(roster)], difficulty] for i in range(bot_count)]

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
        from harrogate_hold_em_V6 import HarrogateHoldEm, DEFAULT_BOT_ROSTER
        import random

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
            [roster[i % len(roster)], start_difficulty]
            for i in range(GAUNTLET_BOT_COUNT)
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
        from harrogate_hold_em_V6 import HarrogateHoldEm, DEFAULT_BOT_ROSTER
        import random

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
        difficulties = [min(100, i * step) for i in range(ENDLESS_BOT_COUNT)]
        random.shuffle(difficulties)

        bots = [
            [roster[i % len(roster)], difficulties[i]] for i in range(ENDLESS_BOT_COUNT)
        ]

        HarrogateHoldEm(self.user_data, settings, bots)

        rounds = int(settings.get("rounds_survived", 0))
        self.show_special_mode_summary("endless", rounds)

        self.interface_root.destroy()


if __name__ == "__main__":
    Casino_Interface(True)
