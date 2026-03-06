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
from deck_management_V6 import CasinoDeckManager
from gui_helpers_V6 import set_view, DELAY, fetch_font_settings


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
        self.user_data = user_data

        # Delay for message logging
        self.log_queue = []
        self.log_active = False
        self.log_delay_ms = int(DELAY * 1000)

        self.wj_root = Tk()
        self.wj_root.title("One More Time Casino - WhiteJoe")

        try:
            self.wj_root.attributes("-fullscreen", True)
        except Exception:
            pass

        from database_management_and_logging_V6 import DatabaseManagement

        self.dbm = DatabaseManagement()

        self.styles = fetch_font_settings(self.wj_root)

        self.main_frame = Frame(self.wj_root)
        self.main_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.action_buttons = []

        self.colour_scheme = {
            # Left-hand panels
            "left_bg": "#e6dcc6",
            # Right-hand panels
            "top_right_bg": "#2e7d73",
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
            state = "normal" if value > 0 else "disabled"
            self.start_button.config(state=state)

        def check_bet_input(*_):
            try:
                value = int(self.bet_var.get())
                if value < 0:
                    value = 0
                balance = self.return_balance()
                if balance is not None and value > balance:
                    value = int(balance)
            except Exception:
                value = 0
            self.bet_var.set(str(value))
            self.current_bet_label.config(text=f"Current Bet: £{value}")
            state = "normal" if value > 0 else "disabled"
            self.start_button.config(state=state)

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
        if self.round_active or bet <= 0:
            self.start_button.config(state="disabled")
        else:
            self.start_button.config(state="normal")

        # Action buttons
        state = "normal" if self.round_active else "disabled"
        for button in self.action_buttons:
            button.config(state=state)

    def admin_modify_bet(self, frame):
        """
        Opens a modal Toplevel dialog allowing the administrator to set a
        custom starting balance. Updates the balance label and database on
        submission. The dialog cannot be closed via the window manager.

        Args:
            frame: The parent widget used to position the Toplevel.
        """
        balance_label = Toplevel(frame)
        balance_label.title("Choose Balance")
        balance_label.grab_set()
        balance_label.protocol("WM_DELETE_WINDOW", lambda: None)

        Label(
            balance_label, text="Enter starting balance (£):", font=self.styles["text"]
        ).pack(pady=5)

        balance_entry = Entry(balance_label, width=30, font=self.styles["text"])
        balance_entry.pack(pady=5)

        error_label = Label(
            balance_label, text="", font=self.styles["emphasis"], fg="red"
        )
        error_label.pack(pady=5)

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
                balance_label.destroy()

                self.dbm.modify_user_balance(self.user_data["username"], balance)

            except Exception:
                error_label.config(text="Please enter a valid positive number.")

        Button(
            balance_label,
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
                            self.colour_scheme["push_bg"]
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
                            self.colour_scheme["push_fg"]
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
        opens the balance modification dialog. For regular users, terminates
        the account and returns to the menu.

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
                    "Your balance is now £0. Given that you have no more money, your account will be terminated.",
                )
                self.dbm.terminate_user_account(
                    self.user_data["username"], "Balance reached £0"
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

        if player == 21 and len(self.player_hand) == 2:
            self.log_message(text="You have WhiteJoe!")
            balance = self.return_balance()
            balance += int(self.current_bet * 2.5)
            self.modify_user_balance(balance)
            self.end_round(win=True)
            return

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

        if self.user_data.get("administrator"):
            from admin_interface_V6 import Admin_Interface

            Admin_Interface(True)
        else:
            from casino_interface_V6 import Casino_Interface

            Casino_Interface(self.user_data)

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


if __name__ == "__main__":
    user_data = {"username": "Administrator", "administrator": True}
    wj = WhiteJoe(user_data)
    wj.run()
