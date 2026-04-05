import sys
from tkinter import (
    Tk,
    Toplevel,
    Frame,
    StringVar,
    messagebox,
    Canvas,
    Scrollbar,
)
from typing import cast
from deck_management import CasinoDeckManager
from gui_helpers import DELAY, CS, create_window, preset_label, preset_button, preset_entry, set_view


class WhiteJoe:
    """
    Handles all game state, betting logic, card dealing, dealer resolution,
    and balance management. Supports both regular user and administrator
    sessions.
    """

    def __init__(self, user_data):
        """
        Initialises the WhiteJoe game window, sets up external resources,
        initialises game state variables and builds the main game interface.

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

        from database_management_and_logging import DatabaseManagement, DB_PATH
        self.dbm = DatabaseManagement(DB_PATH)

        self.action_buttons = []

        # Game state.
        self.player_hand = []
        self.dealer_hand = []
        self.dealer = "Genghis Khan"
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
        a custom starting chip balance. The dialog cannot be dismissed via
        the window manager — a valid balance must be submitted.

        When called from __init__ (before whitejoe_screen has run) the
        dialog navigates to whitejoe_screen on submission. When called
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
            game screen has not yet been built, navigates to whitejoe_screen.
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

        self.balance_label = cast(preset_label, labels[1])
        self.current_bet_label = cast(preset_label, labels[2])

        # Bottom-right panel
        bottom_right_frame = Frame(frame, bd=2, relief="sunken", bg=CS["bottom_right"])
        bottom_right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        def check_bet_input(amount=0):
            """
            Updates the current bet by the given amount, clamping the result
            between 0 and the player's current balance. Updates bet_var,
            the current-bet label, and the Start Round button state.
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
                        else (CS["tie_bg"] if is_push else CS["log_fg"])
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

    def modify_user_balance(self, balance: int):
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
        user's balance), draws exactly one card and resolves the dealer.
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

        from system_interfaces import CasinoInterface
        CasinoInterface(
            administrator=True if self.user_data.get("administrator") else False,
            user_data=self.user_data,
        )



if __name__ == "__main__":
    user_data = {"username": "Administrator", "administrator": True}
    wj = WhiteJoe(user_data)
    wj.run()
