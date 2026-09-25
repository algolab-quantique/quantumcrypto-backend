"""
Multiplayer measurement on the server, from the round's stored strings.

Pure Python — run from the backend root, no Django or server needed:
    python3 -m unittest e91.test_multiplayer -v
"""

import random
import unittest

from e91.multiplayer import measure_side_without_eve
from e91.protocol import Round, angle_of_basis_id, chsh_value, correlations


def random_bases(n, ids):
    return ''.join(random.choice(ids) for _ in range(n))


def S_of(alice_bases, bob_bases, alice_bits, bob_bits):
    rounds = [Round(angle_of_basis_id(a), angle_of_basis_id(b), x, y)
              for a, b, x, y in zip(alice_bases, bob_bases, alice_bits, bob_bits)]
    return chsh_value(correlations(rounds))


class WithoutEve(unittest.TestCase):

    def test_first_click_gives_one_bit_per_photon(self):
        bits = measure_side_without_eve('1231231', None, None)
        self.assertEqual(len(bits), 7)
        self.assertTrue(set(bits) <= {'0', '1'})

    def test_an_empty_stored_string_also_means_first(self):
        # The round stores '' or None before a side measures; both mean "first".
        self.assertEqual(len(measure_side_without_eve('123', '', '')), 3)

    def test_first_click_is_a_fair_coin(self):
        # σ = 0.0035 at 20 000 photons: ±0.014 is 4σ.
        bits = measure_side_without_eve('2' * 20000, None, None)
        self.assertGreater(bits.count('1') / 20000, 0.486)
        self.assertLess(bits.count('1') / 20000, 0.514)

    def test_second_click_at_the_same_angle_copies_exactly(self):
        their_bases = random_bases(2000, '23')   # the two key angles, 45° and 90°
        their_bits = ''.join(random.choice('01') for _ in range(2000))
        self.assertEqual(
            measure_side_without_eve(their_bases, their_bits, their_bases), their_bits)

    def test_a_whole_round_in_both_click_orders_reaches_2root2(self):
        # Through the stored strings, as the server will run it. 10 000
        # photons: σ(S) ≈ 0.045, so 2.6 and 3.05 are each ≥ 4.9σ from 2√2.
        for alice_first in (True, False):
            alice_bases = random_bases(10000, '123')
            bob_bases = random_bases(10000, '234')
            if alice_first:
                alice_bits = measure_side_without_eve(alice_bases, None, None)
                bob_bits = measure_side_without_eve(bob_bases, alice_bits, alice_bases)
            else:
                bob_bits = measure_side_without_eve(bob_bases, None, None)
                alice_bits = measure_side_without_eve(alice_bases, bob_bits, bob_bases)

            s = S_of(alice_bases, bob_bases, alice_bits, bob_bits)
            self.assertGreater(s, 2.6)
            self.assertLess(s, 3.05)
            key = [(x, y) for a, b, x, y
                   in zip(alice_bases, bob_bases, alice_bits, bob_bits) if a == b]
            self.assertTrue(all(x == y for x, y in key))  # identical keys, exactly

    def test_misaligned_stored_strings_are_refused(self):
        with self.assertRaises(ValueError):
            measure_side_without_eve('123', '01', '12')


if __name__ == '__main__':
    unittest.main()
