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
    angle_of_basis_id, create_entangled_pair, measure_one_side, measure_other_side,
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
