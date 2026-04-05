from treys import Card as TreysCard, Deck as TreysDeck, Evaluator

SUITS = ["♠", "♣", "♥", "♦"]
SUIT_MAP = {"♠": "s", "♣": "c", "♥": "h", "♦": "d"}
REVERSE_SUIT_MAP = {v: k for k, v in SUIT_MAP.items()}

VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


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

    def set_game_mode(self, mode):
        """
        Sets the active game mode, controlling which evaluation logic is used
        in evaluate_hand().

        Args:
            mode (str): The game mode to set. Must be 'poker' or 'blackjack'.

        Raises:
            ValueError: If mode is not 'poker' or 'blackjack'.
        """
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
            int: The count of remaining cards.
        """
        return len(self.deck.cards)

    def copy(self):
        """
        Creates an independent copy of this deck manager instance.
        The copied deck shares the same Evaluator (which is stateless) but
        has its own independent card list. Used to ensure Monte Carlo
        simulations do not interfere with each other.

        Returns:
            CasinoDeckManager: A new deck manager instance with a copied
                               deck state and the same game mode.
        """
        new_dm = CasinoDeckManager(shuffle=False, game_mode=self.game_mode)

        # Copy deck state.
        new_dm.deck.cards = self.deck.cards.copy()

        # Evaluator is stateless and safe to reuse.
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
