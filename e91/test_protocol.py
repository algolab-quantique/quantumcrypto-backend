"""
E91 protocol physics — the acceptance suite, translated from the frontend's
``lib/e91/protocol.test.ts``. Same 31 tests, same numbers, same tolerances:
the two implementations are only safe together if the same tests hold both.

Two layers, and the second is the point:
  §10.10 — four headline numbers. Necessary, and NOT sufficient.
  §10.14 — seven properties a wrong implementation can violate while still
           producing all four headline numbers correctly.

Statistical assertions run a fixed sample with tolerances computed in σ (4σ or
more), so they catch a wrong MODEL without failing at random.

Pure Python — run from the backend root, no Django or server needed:
    python3 -m unittest e91.test_protocol -v
"""

import math
import random
import unittest

from e91.protocol import (
    ALICE_ANGLES, BOB_ANGLES, CHSH_COMBINATIONS, EVE_ANGLES, Round,
    angle_of_basis_id, basis_id_of_angle, chsh_term_counts, chsh_value,
    classify_combination, correlations, create_entangled_pair,
    create_entangled_pairs, create_product_pair, describe_run, eavesdrop,
    generate_random_bases, measure_one_side, measure_other_side, measure_pair,
    prob_different, run_e91_protocol, sift_key_bits,
)

N = 40000
SQRT1_2 = math.sqrt(0.5)


def play(n, a, b, with_eve):
    """Play ``n`` rounds at fixed angles and return them."""
    rounds = []
    for _ in range(n):
        pair = eavesdrop(create_entangled_pair()).sent if with_eve else create_entangled_pair()
        alice_bit, bob_bit = measure_pair(pair, a, b)
        rounds.append(Round(a, b, alice_bit, bob_bit))
    return rounds


def E(a, b, with_eve, n=N):
    return correlations(play(n, a, b, with_eve))[f'{a}/{b}']


def S(with_eve):
    return chsh_value({f'{a}/{b}': E(a, b, with_eve) for a, b in CHSH_COMBINATIONS})


def run_protocol(n, with_eve):
    """A FULL run the way the reference workshop does it: random bases on both
    sides, measure, sift, Bell test — the only test of the whole pipeline."""
    alice_angles = generate_random_bases(n, ALICE_ANGLES)
    bob_angles = generate_random_bases(n, BOB_ANGLES)
    alice_bits, bob_bits, rounds = [], [], []
    for i in range(n):
        pair = eavesdrop(create_entangled_pair()).sent if with_eve else create_entangled_pair()
        alice_bit, bob_bit = measure_pair(pair, alice_angles[i], bob_angles[i])
        alice_bits.append(alice_bit)
        bob_bits.append(bob_bit)
        rounds.append(Round(alice_angles[i], bob_angles[i], alice_bit, bob_bit))

    alice_key = sift_key_bits(alice_bits, alice_angles, bob_angles)
    bob_key = sift_key_bits(bob_bits, alice_angles, bob_angles)
    errors = sum(1 for x, y in zip(alice_key, bob_key) if x != y)
    return {
        'alice_key': alice_key,
        'bob_key': bob_key,
        'key_error_rate': errors / len(alice_key) if alice_key else 0,
        'S': chsh_value(correlations(rounds)),
        'bell_rounds': sum(1 for r in rounds
                           if classify_combination(r.alice_angle, r.bob_angle) == 'chsh'),
    }


# ─────────────────────────────────────────────────────────────────────────────
class EndToEnd(unittest.TestCase):
    """10 000 pairs, not the workshop's 2 000: at 2 000, σ(S) ≈ 0.134 and
    "S > 2.5" is a 2.4σ claim that fails ~1 run in 100. At 10 000, σ(S) ≈ 0.060
    and every assertion clears 5σ. Identical keys hold at any size."""

    def test_without_eve_S_reaches_2root2_and_keys_are_identical(self):
        r = run_protocol(10000, False)
        self.assertGreater(r['S'], 2.5)            # the workshop's own threshold
        self.assertLess(r['S'], 3.0)
        self.assertEqual(r['key_error_rate'], 0)   # matching bases never disagree
        self.assertEqual(r['alice_key'], r['bob_key'])
        self.assertGreater(len(r['alice_key']), 1800)  # ≈ 2/9 of 10 000
        self.assertGreater(r['bell_rounds'], 3900)     # ≈ 4/9 of 10 000

    def test_with_eve_S_collapses_and_keys_diverge(self):
        r = run_protocol(10000, True)
        self.assertLess(r['S'], 2)                 # Bell inequality restored
        self.assertGreater(r['S'], 1.1)            # ≈ √2, 5σ either side
        self.assertGreater(r['key_error_rate'], 0.22)
        self.assertLess(r['key_error_rate'], 0.28)
        self.assertNotEqual(r['alice_key'], r['bob_key'])

    def test_the_verdict_a_student_would_reach_is_right_in_both_runs(self):
        # The whole point of E91: the Bell test, not the key, reveals her.
        self.assertTrue(run_protocol(10000, False)['S'] > 2.5)
        self.assertFalse(run_protocol(10000, True)['S'] > 2.5)


class RunE91Protocol(unittest.TestCase):

    def test_no_eve_keys_identical_no_errors_S_above_bound(self):
        r = run_e91_protocol(photons=2000, eve_fraction=0)
        self.assertTrue(r.keys_match)
        self.assertEqual(r.key_error_rate, 0)
        self.assertEqual(r.eve_guessed_right_bits, 0)
        self.assertGreater(r.chsh, 2.5)

    def test_eve_on_every_pair_keys_diverge_25pc_errors_S_below_2(self):
        r = run_e91_protocol(photons=2000, eve_fraction=1)
        self.assertFalse(r.keys_match)
        # ~444 key bits, so σ ≈ 0.021: ±0.09 is ~4.3σ.
        self.assertGreater(r.key_error_rate, 0.16)
        self.assertLess(r.key_error_rate, 0.34)
        self.assertLess(r.chsh, 2)
        # Only a matching basis leaves her holding their bit — about 1 in 4.
        # Not "her bit equals Alice's" (62.5 %, overstates her 2.5×).
        ratio = r.eve_guessed_right_bits / len(r.alice_key)
        self.assertGreater(ratio, 0.18)
        self.assertLess(ratio, 0.32)

    def test_an_eve_on_half_the_pairs_hides_from_the_bell_test(self):
        # S = 2.12 sits only 0.12 above the bound; at 40 000 photons
        # σ(S) ≈ 0.030, so "S > 2" is a 4σ claim.
        r = run_e91_protocol(photons=40000, eve_fraction=0.5)
        self.assertGreater(r.chsh, 2)             # invisible to the Bell test
        self.assertLess(r.chsh, 2.3)              # ≈ 2.121, nowhere near 2√2
        self.assertGreater(r.key_error_rate, 0.08)  # but the errors show

    def test_describe_run_renders_the_run_without_printing_it(self):
        text = describe_run(run_e91_protocol(photons=200, eve_fraction=0))
        self.assertIn('E91 — 200 entangled pairs', text)
        self.assertIn('keys identical          : YES', text)
        self.assertRegex(text, r'E\( 0°, 45°\) =')


# ─────────────────────────────────────────────────────────────────────────────
class HeadlineNumbers(unittest.TestCase):
    """§10.10 — the four headline numbers."""

    def test_S_is_2root2_on_undisturbed_pairs(self):
        self.assertAlmostEqual(S(False), 2 * math.sqrt(2), places=1)

    def test_S_falls_to_root2_once_eve_has_been_there(self):
        s = S(True)
        self.assertAlmostEqual(s, math.sqrt(2), places=1)
        self.assertLess(s, 2)

    def test_key_rounds_never_disagree_without_eve_and_25pc_with_her(self):
        for angle in (45, 90):
            clean = play(N, angle, angle, False)
            self.assertEqual(sum(1 for r in clean if r.alice_bit != r.bob_bit), 0)

            dirty = play(N, angle, angle, True)
            errors = sum(1 for r in dirty if r.alice_bit != r.bob_bit) / N
            # σ = 0.0022, so ±0.01 is ~4.6σ and still catches a 1-point shift.
            self.assertGreater(errors, 0.24)
            self.assertLess(errors, 0.26)

    def test_every_outcome_is_a_fair_coin_per_side_and_per_angle(self):
        for with_eve in (False, True):
            for a in ALICE_ANGLES:
                for b in BOB_ANGLES:
                    rounds = play(6000, a, b, with_eve)
                    alice_ones = sum(1 for r in rounds if r.alice_bit == '1') / 6000
                    bob_ones = sum(1 for r in rounds if r.bob_bit == '1') / 6000
                    self.assertGreater(alice_ones, 0.45)
                    self.assertLess(alice_ones, 0.55)
                    self.assertGreater(bob_ones, 0.45)
                    self.assertLess(bob_ones, 0.55)


# ─────────────────────────────────────────────────────────────────────────────
class Property1ChshSigns(unittest.TestCase):
    """Summing magnitudes also gives 2.83; only the signs show the geometry."""

    def test_E_0_135_is_negative_the_other_three_positive(self):
        self.assertAlmostEqual(E(0, 45, False), SQRT1_2, places=1)
        self.assertAlmostEqual(E(0, 135, False), -SQRT1_2, places=1)
        self.assertLess(E(0, 135, False), -0.6)
        self.assertAlmostEqual(E(90, 45, False), SQRT1_2, places=1)
        self.assertAlmostEqual(E(90, 135, False), SQRT1_2, places=1)


class Property2OrderedCombinations(unittest.TestCase):
    """cos(45−90) = cos(0−45): an unordered check leaves S at exactly 2√2
    while the sifter is corrupt."""

    def test_90_45_is_a_bell_round_45_90_is_discarded(self):
        self.assertEqual(classify_combination(90, 45), 'chsh')
        self.assertEqual(classify_combination(45, 90), 'discard')

    def test_partitions_all_nine_as_2_key_4_chsh_3_discard(self):
        seen = {'key': [], 'chsh': [], 'discard': []}
        for a in ALICE_ANGLES:
            for b in BOB_ANGLES:
                seen[classify_combination(a, b)].append(f'{a}/{b}')
        self.assertEqual(sorted(seen['key']), ['45/45', '90/90'])
        self.assertEqual(sorted(seen['chsh']), ['0/135', '0/45', '90/135', '90/45'])
        self.assertEqual(sorted(seen['discard']), ['0/90', '45/135', '45/90'])


class Property3NoSignalling(unittest.TestCase):
    """A Bob biased per Alice's angle would still average 50 % overall — and
    would be faster-than-light signalling."""

    def test_bobs_marginal_is_50pc_for_each_of_alices_angles(self):
        for a in ALICE_ANGLES:
            rounds = play(20000, a, 45, False)
            ones = sum(1 for r in rounds if r.bob_bit == '1') / 20000
            self.assertGreater(ones, 0.485)
            self.assertLess(ones, 0.515)


class Property4EveForwardsWhatSheRead(unittest.TestCase):

    def test_forwards_the_bit_she_read_she_never_fabricates(self):
        # The one mutation testing caught: an Eve sending an unrelated coin
        # passed every other test. Only comparing read to sent sees it.
        for _ in range(4000):
            e = eavesdrop(create_entangled_pair())
            self.assertEqual(e.sent.kind, 'product')
            self.assertEqual(e.sent.bit, e.bit)
            self.assertEqual(e.sent.angle, e.angle)

    def test_when_her_angle_matches_theirs_all_three_bits_are_identical(self):
        for _ in range(4000):
            e = eavesdrop(create_entangled_pair())
            alice_bit, bob_bit = measure_pair(e.sent, e.angle, e.angle)
            self.assertEqual(alice_bit, e.bit)
            self.assertEqual(bob_bit, e.bit)

    def test_45_off_on_agreeing_key_rounds_she_has_their_bit_97_1pc(self):
        agreed = 0
        she_knew = 0
        for _ in range(60000):
            sent = create_product_pair(0, '0' if random.random() < 0.5 else '1')
            alice_bit, bob_bit = measure_pair(sent, 45, 45)
            if alice_bit != bob_bit:
                continue
            agreed += 1
            if sent.bit == alice_bit:
                she_knew += 1
        self.assertAlmostEqual(she_knew / agreed, 0.971, places=2)


class Property5NoAcuteNormalisation(unittest.TestCase):

    def test_delta_135_gives_0_854_never_0_146(self):
        self.assertEqual(prob_different(0, 0), 0)
        self.assertAlmostEqual(prob_different(0, 45), 0.1464, places=3)
        self.assertAlmostEqual(prob_different(0, 90), 0.5, places=10)
        self.assertAlmostEqual(prob_different(0, 135), 0.8536, places=3)
        self.assertGreater(prob_different(0, 135), 0.85)

    def test_is_symmetric_in_its_two_angles(self):
        self.assertAlmostEqual(prob_different(0, 135), prob_different(135, 0), places=10)


class Property6EachSideMeasuresOnce(unittest.TestCase):
    """A product pair IS measured twice, once per side — and so is an
    entangled one in multiplayer. Neither may throw."""

    def test_both_sides_may_measure_the_same_product_pair(self):
        pair = create_product_pair(45, '1')
        self.assertEqual(measure_one_side(pair, 45), '1')
        self.assertEqual(measure_one_side(pair, 45), '1')

    def test_multiplayer_reads_one_entangled_pair_twice_one_call_per_side(self):
        pair = create_entangled_pair()
        first = measure_one_side(pair, 45)
        second = measure_other_side(pair, 45, first, 45)
        self.assertEqual(second, first)  # Δ=0 → they must agree


class Property7RoundsAreIndependent(unittest.TestCase):
    """State leaking between rounds is the exact shape of the BB84 bug, and
    aggregate statistics hide it completely."""

    @staticmethod
    def lag1(xs):
        mean = sum(xs) / len(xs)
        num = 0.0
        den = 0.0
        for i, x in enumerate(xs):
            den += (x - mean) ** 2
            if i > 0:
                num += (x - mean) * (xs[i - 1] - mean)
        return num / den

    def test_alices_outcomes_and_eves_angles_show_no_round_to_round_correlation(self):
        bits, angles = [], []
        for _ in range(20000):
            e = eavesdrop(create_entangled_pair())
            angles.append(e.angle)
            alice_bit, _ = measure_pair(e.sent, 45, 90)
            bits.append(1 if alice_bit == '1' else 0)
        self.assertLess(abs(self.lag1(bits)), 0.03)
        self.assertLess(abs(self.lag1(angles)), 0.03)


# ─────────────────────────────────────────────────────────────────────────────
class TheTwoTraps(unittest.TestCase):

    def test_sift_refuses_misaligned_arrays_instead_of_inventing_key_bits(self):
        bits = ['0', '1', '0', '1', '1', '1']
        with self.assertRaisesRegex(ValueError, 'length mismatch'):
            sift_key_bits(bits, [0, 45, 90, 0], [0, 90, 90, 45])

    def test_sift_keeps_exactly_the_matching_angle_rounds_when_aligned(self):
        self.assertEqual(
            sift_key_bits(['0', '1', '0', '1'], [45, 45, 90, 0], [45, 90, 90, 45]),
            ['0', '0'])

    def test_the_angle_tables_cannot_be_mutated_at_runtime(self):
        with self.assertRaises(AttributeError):
            ALICE_ANGLES.append(135)
        self.assertEqual(len(ALICE_ANGLES), 3)

    def test_chsh_term_counts_exposes_a_term_with_no_rounds_behind_it(self):
        # An empty term contributes 0, dragging S toward the classical range for
        # a reason that is not physics — 34 % of 20-photon games.
        rounds = play(10, 0, 45, False)
        counts = chsh_term_counts(rounds)
        self.assertEqual(counts['0/45'], 10)
        self.assertEqual(counts['0/135'], 0)
        self.assertLess(chsh_value(correlations(rounds)), 2)


# ─────────────────────────────────────────────────────────────────────────────
class ThePlumbing(unittest.TestCase):

    def test_makes_n_identical_entangled_pairs_carrying_nothing(self):
        pairs = create_entangled_pairs(3)
        self.assertEqual(len(pairs), 3)
        self.assertTrue(all(p.kind == 'entangled' for p in pairs))

    def test_draws_bases_only_from_the_set_it_was_given(self):
        bases = generate_random_bases(200, ALICE_ANGLES)
        self.assertEqual(len(bases), 200)
        self.assertTrue(all(b in ALICE_ANGLES for b in bases))
        self.assertGreater(len(set(bases)), 1)

    def test_eavesdrop_returns_a_new_product_pair_never_the_one_it_was_given(self):
        original = create_entangled_pair()
        e = eavesdrop(original)
        self.assertEqual(original.kind, 'entangled')  # untouched
        self.assertEqual(e.sent.kind, 'product')
        self.assertIn(e.angle, EVE_ANGLES)

    def test_translates_the_stored_basis_ids_both_ways_and_rejects_nonsense(self):
        self.assertEqual(angle_of_basis_id('1'), 0)
        self.assertEqual(angle_of_basis_id('4'), 135)
        self.assertIsNone(angle_of_basis_id('9'))
        self.assertEqual(basis_id_of_angle(135), '4')


if __name__ == '__main__':
    unittest.main()
