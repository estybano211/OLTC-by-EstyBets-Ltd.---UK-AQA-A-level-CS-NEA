import tkinter as tk
from tkinter import Label, Button, scrolledtext, Toplevel, Checkbutton, IntVar
from gui_helpers_V6 import fetch_font_settings


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
        text area, a confirmation checkbox, and a Continue button that is
        disabled until the checkbox is ticked. The window cannot be closed
        via the window manager's close button. Calls the callback and destroys
        the window when the user clicks Continue.

        Args:
            title (str): The window title and heading label text.
            rules_text (str): The full rules text to display.
            callback (callable): A zero-argument function called when the
                                  user clicks Continue.
        """
        window = Toplevel(self.interface_root)
        window.title(title)
        window.geometry("850x650")
        window.grab_set()
        window.protocol("WM_DELETE_WINDOW", lambda: None)  # Disable X button

        try:
            window.attributes("-fullscreen", True)
        except Exception:
            pass

        # Heading label
        heading = Label(window, text=title, font=self.styles["title"])
        heading.pack(pady=10)

        # Scrollable text area
        text_area = scrolledtext.ScrolledText(
            window, wrap=tk.WORD, font=self.styles["terms_and_conditions"]
        )
        text_area.pack(expand=True, fill=tk.BOTH, padx=10)
        text_area.insert(tk.END, rules_text)
        text_area.configure(state="disabled")
        text_area.yview_moveto(0)

        # Bottom controls
        bottom_frame = tk.Frame(window)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        continue_button = Button(
            bottom_frame,
            text="Continue",
            command=lambda: (window.destroy(), callback()),
        )
        continue_button.pack(pady=10)
