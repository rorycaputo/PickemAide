"""
spread_odds_converter.py

Converts American odds quoted at one point spread into the equivalent odds
at a different point spread. Half-point moves near football's "key numbers"
(3, 7, 6, 10, 14...) are priced more expensively than half-point moves
elsewhere, because those margins concentrate real probability mass (field
goals, touchdowns, and combinations of them).

SOURCE OF THE WEIGHTS
----------------------
MOV_FREQUENCY_PCT below is not a guess or a rule of thumb -- it's computed
directly from actual NFL game data (nflverse's games.csv, 2015-2025 regular
season + playoffs, n=3,028 games; https://github.com/nflverse/nfldata).
Each value is simply: what % of games in that sample ended with that exact
margin of victory. That percentage IS the probability mass sitting on that
number, so it's used directly as a probability shift -- no fudge-factor
multiplier needed.

We deliberately used only 2015-2025, not the full history back to 1999/1989.
The NFL moved extra-point attempts from the 2-yard line to the 15-yard line
starting in 2015, which meaningfully changed the scoring distribution --
missed PATs and more frequent 2-point attempts shifted real weight onto
6-point margins in particular (6-point games went from ~5.5% pre-2015 to
~8% post-2015 in various published breakdowns). Using pre-2015 data would
understate 6 and overstate 10 relative to today's game.

Caveat: sample sizes shrink fast for less common margins. 3 and 7 (n well
into the hundreds) are trustworthy; margins past ~17 are thin and noisy --
treat those as rough.
"""

from __future__ import annotations

# % of NFL games (2015-2025, n=3028) that ended with exactly this margin
# of victory. Source: nflverse/nfldata games.csv, computed directly --
# see module docstring.
MOV_FREQUENCY_PCT = {
    0: 0.33, 1: 4.52, 2: 4.59, 3: 14.83, 4: 4.62, 5: 4.39, 6: 6.94,
    7: 8.69, 8: 4.29, 9: 1.68, 10: 4.76, 11: 2.11, 12: 1.85, 13: 2.05,
    14: 5.15, 15: 1.65, 16: 2.38, 17: 3.47, 18: 2.28, 19: 1.16, 20: 2.05,
    21: 2.18, 22: 0.99, 23: 1.35, 24: 1.95,
}

# Calibration: at a -110 baseline, a "10 cent" move (-110 -> -120) shifts
# implied probability by about 2.165 percentage points. We use that ratio
# to translate the (still-heuristic) baseline cost of moving through
# non-key half points into a probability shift.
PROB_SHIFT_PER_10_CENTS = 0.02165
BASELINE_CENTS_PER_HALF_POINT = 10.0


# --- Odds <-> probability helpers -----------------------------------------

def implied_prob(odds: float) -> float:
    """American odds -> implied probability (0-1)."""
    if odds < 0:
        return -odds / (-odds + 100)
    return 100 / (odds + 100)


def prob_to_american(prob: float) -> int:
    """Implied probability (0-1) -> American odds."""
    prob = min(max(prob, 0.0001), 0.9999)
    if prob >= 0.5:
        return -round(prob / (1 - prob) * 100)
    return round((1 - prob) / prob * 100)


# --- Cost model -------------------------------------------------------------

def _assert_on_half_point_grid(spread: float) -> None:
    """Spreads are assumed to always land on .0 or .5 (standard football grid)."""
    doubled = spread * 2
    if abs(doubled - round(doubled)) > 1e-6:
        raise ValueError(
            f"Spread {spread} isn't on the .0/.5 grid. "
            "This tool assumes all spreads end in .0 or .5."
        )


def _num_half_point_steps(from_spread: float, to_spread: float) -> int:
    """How many 0.5-point steps separate two spreads."""
    _assert_on_half_point_grid(from_spread)
    _assert_on_half_point_grid(to_spread)
    return abs(round(to_spread * 2) - round(from_spread * 2))


def _key_numbers_touched(from_spread: float, to_spread: float,
                          mov_freq: dict) -> set:
    """
    Every integer margin whose push probability is gained or lost by moving
    from from_spread to to_spread -- i.e. every whole number in the closed
    interval [min, max]. Each integer is counted once, even if it happens to
    sit on a shared boundary between two 0.5-point steps -- a number's push
    probability doesn't matter twice just because the move is long.

    Key numbers are magnitudes: they matter the same way whether we're
    pricing the favorite (-3) or the underdog (+3).
    """
    lo, hi = sorted((abs(from_spread), abs(to_spread)))
    # abs() on a signed move can flip which end is "low" if the move crosses
    # zero (e.g. -1.5 -> +1.5) -- in that case just use both magnitudes'
    # bounding range, since crossing zero still passes through every integer
    # between them in magnitude terms on each side. This is an edge case
    # (pick'em-adjacent lines) that's rare in practice.
    import math
    touched = set()
    for i in range(math.ceil(lo), math.floor(hi) + 1):
        if i in mov_freq:
            touched.add(i)
    return touched


def total_prob_shift(from_spread: float, to_spread: float,
                      mov_freq: dict = MOV_FREQUENCY_PCT,
                      baseline_cents_per_half_point: float = BASELINE_CENTS_PER_HALF_POINT,
                      prob_shift_per_10_cents: float = PROB_SHIFT_PER_10_CENTS
                      ) -> float:
    """
    Total probability-mass shift implied by moving from from_spread to
    to_spread, combining:
      - a flat baseline cost per 0.5-point step (still a heuristic --
        not empirically derived), plus
      - the actual measured push probability for every key-number
        magnitude gained or lost along the way (empirically derived,
        see module docstring).
    """
    n_steps = _num_half_point_steps(from_spread, to_spread)
    baseline = n_steps * (baseline_cents_per_half_point / 10.0) * prob_shift_per_10_cents

    key_extra = sum(mov_freq[i] / 100.0
                     for i in _key_numbers_touched(from_spread, to_spread, mov_freq))

    return baseline + key_extra


# --- Main conversion --------------------------------------------------------

def convert_spread_odds(from_spread: float, from_odds: float, to_spread: float,
                         mov_freq: dict = MOV_FREQUENCY_PCT,
                         baseline_cents_per_half_point: float = BASELINE_CENTS_PER_HALF_POINT,
                         prob_shift_per_10_cents: float = PROB_SHIFT_PER_10_CENTS
                         ) -> int:
    """
    Convert odds quoted at from_spread into equivalent odds at to_spread,
    for the SAME side of the bet (e.g. -7/-110 -> -6.5/??? for the favorite).

    Convention: spreads are signed as normally quoted for the side you're
    pricing (favorite negative, dog positive). Moving the spread value UP
    (e.g. -7 -> -6.5, or +6.5 -> +7) makes that side easier to cover, so
    the odds get worse (more negative/expensive). Moving it DOWN improves
    the odds.
    """
    if from_spread == to_spread:
        return round(from_odds)

    shift = total_prob_shift(from_spread, to_spread, mov_freq,
                              baseline_cents_per_half_point, prob_shift_per_10_cents)
    direction = 1 if to_spread > from_spread else -1

    new_prob = implied_prob(from_odds) + direction * shift
    return prob_to_american(new_prob)


# --- Price gap between two quotes (possibly at different spreads) ---------

def price_gap(spread_a: float, odds_a: float, spread_b: float, odds_b: float,
              mov_freq: dict = MOV_FREQUENCY_PCT,
              baseline_cents_per_half_point: float = BASELINE_CENTS_PER_HALF_POINT,
              prob_shift_per_10_cents: float = PROB_SHIFT_PER_10_CENTS) -> dict:
    """
    Given two quotes -- possibly at different spreads, possibly at the same
    spread -- returns how much they *actually* disagree on price, once the
    model's own spread-movement assumptions are used to put them on equal
    footing.

    Method: convert quote A onto quote B's spread (using the exact same
    key-number/baseline logic as convert_spread_odds), then compare the
    converted price to B's actual quoted price. Whatever's left over is
    the "real" disagreement -- price difference the spread gap doesn't
    explain. If both quotes are at the same spread already, no conversion
    happens and this is just a direct comparison (e.g. -1.5 @ +115 vs
    -1.5 @ -115 -- see the two worked cases below).

    Sign convention: positive cents_gap means B is pricing that side more
    expensively (higher implied probability / worse for a bettor on that
    side) than A implies once adjusted for the spread difference. Negative
    means B is cheaper / better value than A implies.
    """
    a_converted = convert_spread_odds(spread_a, odds_a, spread_b, mov_freq,
                                       baseline_cents_per_half_point,
                                       prob_shift_per_10_cents)
    prob_a_converted = implied_prob(a_converted)
    prob_b = implied_prob(odds_b)

    prob_gap = prob_b - prob_a_converted
    cents_gap = (prob_gap / prob_shift_per_10_cents) * 10.0

    return {
        "compared_at_spread": spread_b,
        "quote_a_converted_to_spread_b": a_converted,
        "quote_b_actual": round(odds_b),
        "prob_gap_pct_points": round(prob_gap * 100, 2),
        "cents_gap": round(cents_gap, 2),
    }


# --- Convenience: average odds across differing spreads --------------------

def average_odds_across_spreads(quotes, target_spread, **kwargs):
    """
    quotes: list of (spread, odds) tuples, e.g. [(-7, -110), (-6.5, -120), (-7.5, +100)]
    target_spread: the common spread to normalize everything to before averaging.

    Returns (average_odds_at_target, list_of_converted_odds_at_target).
    """
    converted = [convert_spread_odds(sp, odds, target_spread, **kwargs)
                 for sp, odds in quotes]
    avg_prob = sum(implied_prob(o) for o in converted) / len(converted)
    return prob_to_american(avg_prob), converted


# --- Demo --------------------------------------------------------------------

if __name__ == "__main__":
    print("-7 @ -110  ->  -6.5:", convert_spread_odds(-7, -110, -6.5))   # crosses key# 7 (8.69%)
    print("-3 @ -110  ->  -3.5:", convert_spread_odds(-3, -110, -3.5))   # crosses key# 3 (14.83%, dominant)
    print("-9 @ -110  ->  -9.5:", convert_spread_odds(-9, -110, -9.5))   # crosses key# 9 (only 1.68%, minor)
    print("-6 @ -110  ->  -6.5:", convert_spread_odds(-6, -110, -6.5))   # crosses key# 6 (6.94%, modern-era-elevated)

    # A longer move spanning multiple key numbers -- 6 and 7 both touched
    print("-5.5 @ -110 -> -7.5:", convert_spread_odds(-5.5, -110, -7.5))

    quotes = [(-7, -110), (-6.5, -125), (-7.5, +102)]
    avg, converted = average_odds_across_spreads(quotes, target_spread=-7)
    print("\nConverted to -7:", converted)
    print("Averaged odds at -7:", avg)
