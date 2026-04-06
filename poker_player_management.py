from deck_management import CasinoDeckManager
import random
from itertools import combinations

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

# Difficulty levels (0 to 100) affect bot betting behavior. At difficulty 0, bot makes
# looser plays (higher fold override bias). At difficulty 100, bot approaches optimal
# strategy. Constants below control how much the bot deviates from optimal play.

# Fold-bias constants.
""" At difficulty 0  a bot has a FOLD_BIAS_MAX chance each decision of
converting a marginal fold into a call.  At difficulty 100 the chance
drops to FOLD_BIAS_MIN, keeping high-difficulty bots close to optimal."""
FOLD_BIAS_MAX = 0.40  # 40% override at difficulty 0.
FOLD_BIAS_MIN = 0.04  # 4% override at difficulty 100.


# POKER PLAYER MANAGEMENT


class HumanPokerPlayer:
    """
    A human player backed by the database.

    Loads real statistics and a persisted range chart on construction.
    Inexperienced players (rounds_played <= EXPERIENCE_THRESHOLD) receive a
    default range for gameplay while their stored range continues to be
    updated in the database.

    Attributes:
        user_id (int): Database primary key for this player.
        dbm (DatabaseManagement): Database manager instance.
        record (dict): Raw record loaded from user_poker_data.
        vpip (float): Voluntarily Put money In Pot percentage.
        pfr (float): Pre-Flop Raise percentage.
        aggression_factor (float): pfr / max(1.0, vpip).
        fold_to_raise (float): Normalised fold-to-raise frequency.
        call_when_weak (float): Normalised call-when-weak frequency.
        statistics (dict): rounds_played and avg_bet_size.
        base_range (dict): Range chart used as the session baseline.
        stored_range (dict): Range chart that is persisted to the database.
        active_range (dict): Session copy of base_range (modified in play).
    """

    def __init__(self, *, user_id: int):
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

        from database_management_and_logging import DatabaseManagement, DB_PATH

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

    def decide(
        self, *, player_hand, community_cards, opponents, pot, to_call, balance, street
    ):
        """
        Makes a poker decision by delegating to make_decision().

        Args:
            player_hand (list[str]): The player's two hole cards.
            community_cards (list[str]): The current community cards (0–5).
            opponents (list[BasePokerPlayer]): The active opponent players.
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
            bot=None,
            street=street,
        )

    def refresh_from_db(self):
        """
        Reloads all player attributes from the database. Useful when
        another process has updated the database since this instance was
        initialised.
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
        Returns a concise string representation of the human player.
        """
        return (
            f"HumanPokerPlayer(user_id={self.user_id}, "
            f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%, "
            f"Rounds Played={self.statistics['rounds_played']})"
        )


class BotPokerPlayer:
    """
    An AI bot player with synthetically generated tendencies.

    All parameters are derived from the difficulty level using
    difficulty_curve(). No database interaction occurs.

    Attributes:
        difficulty (int): Bot difficulty level 0–100.
        bot_characteristics (BotCharacteristics): Full AI parameter set.
        vpip (float): Voluntarily Put money In Pot percentage.
        pfr (float): Pre-Flop Raise percentage.
        aggression_factor (float): pfr / max(1.0, vpip).
        bluff_freq (float): Base bluffing frequency.
        fold_to_raise (float): Tendency to fold when facing a raise.
        call_when_weak (float): Tendency to call with a weak hand.
        statistics (dict): Placeholder statistics (always zeros for bots).
        base_range (dict): Hand range generated from vpip and difficulty.
        active_range (dict): Session copy of base_range.
    """

    def __init__(self, *, difficulty: int):
        """
        Initialises an AI bot with synthetically generated tendencies scaled by difficulty.

        Args:
            difficulty (int): Bot difficulty level 0–100.

        Raises:
            ValueError: If difficulty is not set.
        """
        if difficulty is None:
            raise ValueError("difficulty is required for bot players.")

        self.difficulty = difficulty
        self.user_id = None
        self.dbm = None
        self.record = None

        # Tendency parameters interpolated by difficulty.
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
            opponents (list[BasePokerPlayer]): The active opponent players.
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

    def reset_active_range(self):
        """
        Resets the active range to a fresh copy of the base range.
        """
        self.active_range = self.base_range.copy()

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
        Returns a concise string representation of the bot player.
        """
        return (
            f"BotPokerPlayer(difficulty={self.difficulty}, "
            f"VPIP={self.vpip:.1f}%, PFR={self.pfr:.1f}%)"
        )


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

        # Accuracy / simulation depth.
        self.simulations = int(difficulty_curve(difficulty, 500, 15000))

        # Decision noise, lower value means sharper decisions.
        self.noise_level = difficulty_curve(difficulty, 0.30, 0.02)

        # Bluffing.
        self.bluff_multiplier = difficulty_curve(difficulty, 0.6, 1.6)

        # Risk appetite.
        self.risk_tolerance = difficulty_curve(difficulty, 0.85, 1.5)

        # Minimum Defence Frequency scaling.
        self.mdf_threshold = difficulty_curve(difficulty, 0.9, 0.3)

        # Range discipline.
        self.range_adherence = difficulty_curve(difficulty, 0.6, 0.95)

        # Fold-bias. easy bots are reluctant to fold and hard bots are more rational.
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
    Updates a range chart based on an observed action and then normalises the
    probabilities to sum to 1.0. Raising increases the hand's probability,
    folding decreases it and calling applies a smaller increase.

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
        difficulty is applied, the range multiplier is factored in and
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
    # Human players pass bot=None; return a sensible default rather than crash.
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

    # Premium river hands (high difficulty only).
    if street == "river":
        hand_type = describe_hand(player_hand, community_cards)
        if bot.difficulty >= 85 and bot.risk_tolerance >= 1.0:
            if hand_type in ("Straight Flush", "Four of a Kind", "Full House"):
                raise_amt = calculate_raise_amount(pot, equity, balance, bot)
                return ("raise", raise_amt)
    else:
        hand_type = None

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
        raise_amt = calculate_raise_amount(pot, equity, balance, bot)
        if 0 < raise_amt <= balance:
            return ("raise", raise_amt)

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
    elif 0.2 < equity < 0.5:
        if should_bluff_call(pot, to_call, equity, avg_fold_to_raise, bot):
            should_attempt_bluff = True
            bluff_action = "call"

    # Low-difficulty bots make random bluffing errors.
    if random.random() < error_prob:
        should_attempt_bluff = random.choice([True, False])
        bluff_action = random.choice(["raise", "call"])

    if should_attempt_bluff:
        if bluff_action == "raise":
            raise_amt = calculate_raise_amount(pot, equity, balance, bot)
            return ("raise", raise_amt if raise_amt <= balance else int(balance))
        elif bluff_action == "call" and to_call <= balance:
            return ("call",)

    # Fold bias
    """ All bots have a small tendency to call rather than fold in marginal
    spots. The bias is much stronger for easy bots
    and diminishes toward the threshold FOLD_BIAS_MIN for hard bots.
    Only applied when the bot can actually afford the call."""
    if to_call <= balance and random.random() < bot.fold_bias:
        return ("call",)

    # Default action — fold
    return ("fold",)
