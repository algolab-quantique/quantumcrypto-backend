"""
Multiplayer E91 on the server: measuring one player's click from what the
round stores, using the physics in ``protocol.py``.

The round (``E91Iteration``) stores bases as strings of ids '1'..'4' and bits
as strings of '0'/'1'. This module only translates between that and
``protocol.py``; it decides no physics itself (docs/protocol-physics.md §10.13,
frontend repository).

Pure Python, no Django import, so it is tested with plain ``unittest``
(``test_multiplayer.py``) — ``consumers.py`` cannot be, and only calls this.
"""

from e91.protocol import (
    angle_of_basis_id, basis_id_of_angle, create_entangled_pair, create_product_pair,
    eavesdrop, measure_one_side, measure_other_side, sift_key_bits,
)


def measure_side_without_eve(my_bases: str, their_bits: str | None,
                             their_bases: str | None) -> str:
    """
    One player's click in a round without Eve, where every pair is entangled.

    First click (the other side has not measured yet): a fair coin per photon.
    Second click: each photon correlated against what the other side got, at
    the two angles — "first one gets a coin, second one follows" (§10.13).

    Raises ValueError if the stored strings have different lengths: measuring
    misaligned photons would silently pair the wrong ones.
    """
    pair = create_entangled_pair()  # an intact pair carries nothing: one serves all
    if not their_bits:
        return ''.join(measure_one_side(pair, angle_of_basis_id(b)) for b in my_bases)
    return ''.join(
        measure_other_side(pair, angle_of_basis_id(mine), their_bit,
                           angle_of_basis_id(theirs))
        for mine, their_bit, theirs in zip(my_bases, their_bits, their_bases,
                                            strict=True))


def draw_eve_photons(photon_number: int) -> tuple[str, str]:
    """
    Eve on every photon of a round, before either player measures: for each,
    ``protocol.eavesdrop`` picks her angle, measures, and builds the photon she
    re-sends. Returns what the round stores — the angles of the re-sent photons
    as basis ids, and their bits (which are the bits she read: she relays, she
    never fabricates).
    """
    sent = [eavesdrop(create_entangled_pair()).sent for _ in range(photon_number)]
    return (''.join(basis_id_of_angle(p.angle) for p in sent),
            ''.join(p.bit for p in sent))


def measure_side_with_eve(my_bases: str, eve_angles: str, eve_bits: str) -> str:
    """
    One player's click in a round where Eve intercepted every photon.

    Each photon is the one she re-sent — ordinary, no longer entangled — so each
    side is measured on its own, and who clicks first does not matter (§10.13).

    Raises ValueError if the stored strings have different lengths.
    """
    return ''.join(
        measure_one_side(create_product_pair(angle_of_basis_id(eve_angle), eve_bit),
                         angle_of_basis_id(mine))
        for mine, eve_angle, eve_bit in zip(my_bases, eve_angles, eve_bits, strict=True))


def eve_summary(alice_bases: str, bob_bases: str, eve_angles: str) -> dict[str, int]:
    """
    The round-end line about Eve, as solo shows it (frontend Task 72): she
    measured ``n`` photons of ``m``, and holds ``k`` of the ``l`` key bits for
    certain — those where her angle was the basis both players used, so the
    photon she re-sent carried exactly their bit. Anywhere else she holds a
    guess, not a read. The same count as solo's (``solo-basis-tab.tsx``).

    Raises ValueError if the stored strings have different lengths.
    """
    alice = [angle_of_basis_id(b) for b in alice_bases]
    bob = [angle_of_basis_id(b) for b in bob_bases]
    eve_on_key = sift_key_bits(list(eve_angles), alice, bob)
    alice_on_key = sift_key_bits(list(alice_bases), alice, bob)
    return {'n': len(eve_angles), 'm': len(alice_bases),
            'k': sum(e == a for e, a in zip(eve_on_key, alice_on_key)),
            'l': len(alice_on_key)}
