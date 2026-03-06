import random
from tkinter import (
    Tk,
    Toplevel,
    Frame,
    Label,
    Button,
    Entry,
    StringVar,
    messagebox,
    Canvas,
    Scrollbar,
)
from typing import cast
from queue import Queue, Empty
import threading

from gui_helpers_V6 import set_view, DELAY, fetch_font_settings
from deck_management_V6 import CasinoDeckManager
from poker_player_management_V6 import PokerPlayer

# Bot roster

DEFAULT_BOT_ROSTER = [
    "Angus",
    "Angeban",
    "Grey",
    "Mr Rhodes",
    "Leon S. Kennedy",
    "Ada Wong",
    "Albert Wesker",
    "Jack Krauser",
    "Luis Serra",
    "Nathan Drake",
    "Joel Miller",
    "Tobias Rieper",
    "Arthur Morgan",
    "Dutch Van Der Linde",
    "Jin Sakai",
    "Atsu Onryo",
    "Alfred",
    "Danny Trejo",
    "Bagley",
    "Sauron",
    "Morgoth",
    "Han Solo",
    "Gordon Freeman",
    "Mr Chips",
    "Dante from Devil May Cry",
    "Cal Kestis",
    "Master Chief",
    "Lara Croft",
    "Vector the Crocodile",
    "Rayman",
    "Hideo Kojima",
    "Naked Snake",
    "Big Boss",
    "Venom Snake",
    "Liquid Snake",
    "Solidus Snake",
    "Archimedes",
    "Giancarlo Esposito",
    "Kinji Hakari",
    "Toji Fushiguro",
    "Jon Snow",
    "Pikmin",
    "Hatsune Miku",
    "Oggdo Bogdo",
    "Spawn of Oggdo",
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
        total_players (int): Total player count (human + bots).
        win_criteria (str): Active win-criteria key constant.
        target_amount (int): Chip target for WIN_CRITERIA_EARN_TARGET.
        base_small_blind (int): Starting small blind before escalation.
        base_big_blind (int): Starting big blind before escalation.
        current_round (int): The current round number (1-indexed).
        rounds_survived (int): How many rounds the human has survived.
        human_chips_at_round_start (int): Human's chip count at the start
                                          of the current round.
        round_wins (int): Number of rounds the human has won.
        tournament_over (bool): True once the tournament has concluded.
        tournament_won (bool): True if the human won the tournament.
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
            bool: True if the human has won this round.
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
            human_won_round (bool): Whether the human met the win criteria
                                    for the round that just finished.

        Returns:
            dict: A result dictionary with keys:
                  - 'tournament_over' (bool)
                  - 'tournament_won' (bool)
                  - 'message' (str) — human-readable outcome message.
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
        (human + bots), UI layout, and the background bot-decision queue
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
            self.hhe_root.attributes("-fullscreen", True)
        except Exception:
            pass

        # Log queue
        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        # Bot decision queue
        self.bot_decision_queue = Queue()
        self.bot_thinking = False

        from database_management_and_logging_V6 import DatabaseManagement

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
            bots = [[roster[i % len(roster)], difficulty] for i in range(bot_count)]

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
        for i, bot in enumerate(bots[: settings.get("bot_count", len(bots))]):
            self.bots[i] = {"name": bot[0], "difficulty": bot[1]}

        # Build player list
        self.players = []

        player_model = None
        if self.user_data.get("user_id"):
            try:
                player_model = PokerPlayer(
                    user_id=self.user_data["user_id"], is_bot=False
                )
            except Exception as exc:
                messagebox.showerror(
                    "Error", f"Failed to initialise player model: {exc}"
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

        for i in range(settings.get("bot_count", len(self.bots))):
            self.players.append(
                {
                    "player": self.bots[i]["name"],
                    "position": None,
                    "cards": [],
                    "balance": settings.get("bot_balance", 1000),
                    "bet": 0,
                    "status": "Waiting",
                    "is_bot": True,
                    "user_id": None,
                    "model": PokerPlayer(
                        is_bot=True, difficulty=max(0, self.bots[i]["difficulty"])
                    ),
                }
            )

        random.shuffle(self.players)
        for pos, player in enumerate(self.players, start=1):
            player["position"] = pos

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

        self.colour_scheme = {
            # Left-hand panels
            "top_left_bg": "#ddd3bc",
            "bottom_left_bg": "#e6dcc6",
            # Right-hand panels
            "top_right_bg": "#2e7d73",
            "middle_right_bg": "#286b62",
            "bottom_right_bg": "#5b2a3c",
            # Interactive widgets
            "widget_bg": "#6a2e4f",
            "text_bg": "#141414",
            "text_fg": "#f2f2f2",
            "left_fg": "#1e1e1e",
            # Log panel
            "log_bg": "#1a1a1a",
            "log_fg": "#cfcfcf",
            # Log entry colour coding
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
            lbl = Label(
                top_right,
                text=text,
                font=self.styles["text"],
                bg=cs["top_right_bg"],
                fg=cs["text_fg"],
                anchor="w",
            )
            lbl.pack(anchor="w", pady=5, padx=5)
            labels.append(lbl)

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

        def adjust_current_bet(amount):
            try:
                value = int(self.bet_var.get())
            except Exception:
                value = 0
            value += amount
            bal = self.return_balance()
            if bal is not None:
                value = max(1, min(value, int(bal)))
            self.bet_var.set(str(value))
            self.current_bet_label.config(text=f"Current Bet: £{value}")

        def check_bet_input(*_):
            try:
                value = int(self.bet_var.get())
                value = max(0, value)
                bal = self.return_balance()
                if bal is not None and value > bal:
                    value = int(bal)
            except Exception:
                value = 0
            self.bet_var.set(str(value))
            self.current_bet_label.config(text=f"Current Bet: £{value}")

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
            flop_c = self.flop[1] if isinstance(self.flop, list) else []
            turn_c = self.turn[1] if isinstance(self.turn, list) else []
            self.board_label.config(
                text=f"The Board:  {' '.join(str(c) for c in flop_c + turn_c)}  |?|"
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
            human = next((p for p in self.players if not p["is_bot"]), None)
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
        Kept as a separate public method so external callers continue to work
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
        bal_win = Toplevel(frame)
        bal_win.title("Set Starting Balance")
        bal_win.grab_set()
        bal_win.protocol("WM_DELETE_WINDOW", lambda: None)
        bal_win.configure(bg=self.colour_scheme["top_left_bg"])

        Label(
            bal_win,
            text="Enter starting balance (£):",
            font=self.styles["text"],
            bg=self.colour_scheme["top_left_bg"],
            fg=self.colour_scheme["text_fg"],
        ).pack(pady=8)

        bal_entry = Entry(
            bal_win,
            width=20,
            font=self.styles["text"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            insertbackground=self.colour_scheme["text_fg"],
        )
        bal_entry.pack(pady=5)

        err_lbl = Label(
            bal_win,
            text="",
            font=self.styles["emphasis"],
            fg="#e08080",
            bg=self.colour_scheme["top_left_bg"],
        )
        err_lbl.pack(pady=4)

        def submit_balance():
            """Validates the entry, updates the UI and database, and closes
            the dialog. Shows an inline error on invalid input."""
            try:
                balance = int(bal_entry.get().strip())
                if balance < 0:
                    raise ValueError()
                self.balance_label.config(text=f"Balance: £{balance}")
                bal_win.destroy()
                self.dbm.modify_user_balance(self.user_data["username"], balance)
            except Exception:
                err_lbl.config(text="Please enter a valid positive integer.")

        Button(
            bal_win,
            text="Submit",
            font=self.styles["button"],
            bg=self.colour_scheme["widget_bg"],
            fg=self.colour_scheme["text_fg"],
            relief="flat",
            bd=0,
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
            idx = (self.initial_position + 1 + attempt) % self.player_count
            if self.players[idx]["status"] != "OUT":
                self.small_blind_position = idx
                self.small_blind_player = self.players[idx]
                break

        # Big blind: first active player after small blind
        for attempt in range(self.player_count):
            idx = (self.small_blind_position + 1 + attempt) % self.player_count
            if self.players[idx]["status"] != "OUT":
                self.big_blind_position = idx
                self.big_blind_player = self.players[idx]
                break

        # Action starts: first active player after big blind
        for attempt in range(self.player_count):
            idx = (self.big_blind_position + 1 + attempt) % self.player_count
            if self.players[idx]["status"] != "OUT":
                self.current_position = idx
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
            human = next((p for p in self.players if not p["is_bot"]), None)
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

        threading.Thread(
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
        import time

        start = time.time()
        try:
            decision = self.bot_decision(player)
            elapsed_ms = (time.time() - start) * 1000
            remaining = max(0, min_thinking_ms - elapsed_ms)
            if remaining > 0:
                time.sleep(remaining / 1000.0)
            self.bot_decision_queue.put((player, decision, None))
        except Exception as exc:
            self.bot_decision_queue.put((player, None, exc))

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
        raiser_pos = except_player["position"] - 1
        self.action_position = (raiser_pos + 1) % self.player_count
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
                idx = (self.initial_position + 1 + attempt) % self.player_count
                if self.players[idx]["status"] != "OUT":
                    self.current_position = idx
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
            except Exception as exc:
                self.log_message(f"Error evaluating {player['player']}'s hand: {exc}")

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
                    pot_size=self.pot_size,
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
        human = next((p for p in self.players if not p["is_bot"]), None)
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
                    lambda r=result: self._finish_tournament(r),
                )
                return

            # Update blinds for next round
            self.small_blind_value = self.tournament.current_small_blind
            self.big_blind_value = self.tournament.current_big_blind

        # Schedule teardown after log queue drains
        delay = self.log_delay_ms * (len(self.log_queue) + 1)
        self.hhe_root.after(delay, self.finish_end_round)

    def _finish_tournament(self, result):
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
        zero chips, marks the human as 'OUT' if they have no chips,
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

        human = next((p for p in self.players if not p["is_bot"]), None)
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
        human = next((p for p in self.players if not p["is_bot"]), None)

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

        if self.user_data.get("administrator"):
            from admin_interface_V6 import Admin_Interface

            Admin_Interface(True)
        else:
            from casino_interface_V6 import Casino_Interface

            Casino_Interface(self.user_data)

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
