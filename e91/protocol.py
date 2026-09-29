"""
E91 protocol physics — a faithful translation of the frontend's
``lib/e91/protocol.ts``.

The TypeScript file is the single source of truth, and it is itself a
transcription of ``docs/protocol-physics.md`` §10 (frontend repository). This
file exists only because multiplayer measures on the server: the physics must
run here too. It mirrors the TypeScript function for function so the two can be
read side by side. **Change one, change the other**, and keep
``test_protocol.py`` (a translation of ``protocol.test.ts``) green in both.
If this file and the spec ever disagree, the spec is right.

It is expected to be deleted, not maintained forever: once E91's physics moves
entirely into the frontend (Task 40 Phase 5), the server only stores the pair.

Pure Python — no Django import — so it can be tested with plain ``unittest``.

Name map (TypeScript → Python):
    probDifferent        prob_different
    createEntangledPair  create_entangled_pair   (and ...Pairs)
    createProductPair    create_product_pair
    generateRandomBases  generate_random_bases
    measureOneSide       measure_one_side
    measureOtherSide     measure_other_side
    measurePair          measure_pair            (returns a tuple)
    eavesdrop            eavesdrop
    classifyCombination  classify_combination
    siftKeyBits          sift_key_bits
    correlations         correlations
    chshTermCounts       chsh_term_counts
    chshValue            chsh_value
    angleOfBasisId       angle_of_basis_id
    basisIdOfAngle       basis_id_of_angle
    runE91Protocol       run_e91_protocol
    describeRun          describe_run
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# ─────────────────────────────────────────────────────────────────────────────
# Types and constants (§10.2)
# ─────────────────────────────────────────────────────────────────────────────

# Bits are the strings '0' / '1', as everywhere in the app, so a key prints as
# itself. Angles are Bloch-sphere angles in DEGREES (0, 45, 90, 135), not
# polarizer angles: orthogonal is 180° apart, which is why the rule has Δ/2.

# Tuples, not lists: these are module-wide singletons, and one stray append
# would corrupt every game the server plays.
ALICE_ANGLES = (0, 45, 90)
BOB_ANGLES = (45, 90, 135)

# Eve draws from every angle: she does not know which two will be compared.
EVE_ANGLES = (0, 45, 90, 135)

# The four Bell-test combinations, ORDERED (Alice, Bob).
CHSH_COMBINATIONS = ((0, 45), (0, 135), (90, 45), (90, 135))


@dataclass(frozen=True)
class Pair:
    """
    A pair between the source and the detectors (§10.8).

    ``entangled`` carries nothing: neither particle has a value or a direction
    until measured. ``product`` is an ordinary pair, both particles definite
    along ``angle`` with value ``bit`` — what Eve forwards.
    """
    kind: str                 # 'entangled' | 'product'
    angle: int | None = None  # product only
    bit: str | None = None    # product only


# ─────────────────────────────────────────────────────────────────────────────
# The one physical rule (§10.3)
# ─────────────────────────────────────────────────────────────────────────────

def prob_different(from_degrees: float, to_degrees: float) -> float:
    """
    How often a measurement at one angle disagrees with a state defined at
    another. The only physics in this file; everything below is built from it.

    NOT normalised to an acute angle: Δ = 135° must give 0.854, not 0.146.
    """
    return math.sin(math.radians(from_degrees - to_degrees) / 2) ** 2


def _coin() -> str:
    return '0' if random.random() < 0.5 else '1'


def _flip(bit: str) -> str:
    return '1' if bit == '0' else '0'


def _maybe_flip(bit: str, p: float) -> str:
    return _flip(bit) if random.random() < p else bit


# ─────────────────────────────────────────────────────────────────────────────
# Making pairs, choosing bases (§10.9 steps 1–2)
# ─────────────────────────────────────────────────────────────────────────────

def create_entangled_pair() -> Pair:
    return Pair('entangled')


def create_entangled_pairs(n: int) -> list[Pair]:
    """n of them, all identical — an intact pair carries nothing to differ in."""
    return [create_entangled_pair() for _ in range(n)]


def create_product_pair(angle: int, bit: str) -> Pair:
    """An ordinary pair, both particles definite along ``angle``. Eve builds these."""
    return Pair('product', angle, bit)


def generate_random_bases(n: int, available: tuple[int, ...]) -> list[int]:
    return [random.choice(available) for _ in range(n)]


# ─────────────────────────────────────────────────────────────────────────────
# Measuring (§10.9 steps 3–4)
# ─────────────────────────────────────────────────────────────────────────────
#
# Why three of these when a Qiskit notebook needs one: multiplayer splits the
# single "measure the pair" line across two requests from two browsers.
#
#     solo                       measure_pair        (both sides, one act)
#     multiplayer, first click   measure_one_side    (no other angle known yet)
#     multiplayer, second click  measure_other_side  (correlate against them)
#     Eve                        measure_one_side    then create_product_pair
#
# measure_other_side reads the result the other side already got. No real
# detector does that; we compute a non-local correlation on one machine, so the
# information has to travel somewhere. It never reaches a player.

def measure_one_side(pair: Pair, angle: int) -> str:
    """
    Measure ONE side, with nothing to go on — Eve, or multiplayer's first click.
    An entangled pair gives a fair coin in every basis; a product pair is
    already definite, so the rule applies.
    """
    if pair.kind == 'entangled':
        return _coin()
    return _maybe_flip(pair.bit, prob_different(angle, pair.angle))


def measure_other_side(pair: Pair, my_angle: int,
                       their_bit: str, their_angle: int) -> str:
    """
    Measure the OTHER side, once one side has been measured — multiplayer's
    second click. An entangled pair correlates against what the other side got;
    a product pair ignores them: it is local, which is what Eve made it.
    """
    if pair.kind == 'entangled':
        return _maybe_flip(their_bit, prob_different(my_angle, their_angle))
    return measure_one_side(pair, my_angle)


def measure_pair(pair: Pair, alice_angle: int, bob_angle: int) -> tuple[str, str]:
    """
    Both sides at once. A COMPOSITION of the two rules above, never a third
    rule — a second copy of the correlation is the defect this file prevents.
    Returns ``(alice_bit, bob_bit)``.
    """
    alice_bit = measure_one_side(pair, alice_angle)
    return alice_bit, measure_other_side(pair, bob_angle, alice_bit, alice_angle)


@dataclass(frozen=True)
class Interception:
    """What Eve did to one pair: the angle she measured at, what she READ, and
    the pair she sent on. ``sent.bit`` is ``bit``: she relays, she never
    fabricates."""
    angle: int
    bit: str
    sent: Pair


def eavesdrop(pair: Pair) -> Interception:
    """
    Eve: measure what arrived, then prepare and forward a NEW pair (§10.5).

    Returns her READ as well as the pair. Without it, an Eve that measured and
    then forwarded an unrelated coin would pass every headline number (S still
    √2, key error still 25 %) while her knowledge silently dropped to zero.
    """
    angle = random.choice(EVE_ANGLES)
    bit = measure_one_side(pair, angle)
    return Interception(angle, bit, create_product_pair(angle, bit))


# ─────────────────────────────────────────────────────────────────────────────
# Sifting (§10.9 step 5)
# ─────────────────────────────────────────────────────────────────────────────

def classify_combination(alice: int, bob: int) -> str:
    """
    'key' | 'chsh' | 'discard'. The pair is ORDERED: (90, 45) is a Bell round and
    (45, 90) is discarded. An unordered check silently promotes discarded rounds
    into Bell data — and S still comes out at 2√2, so nothing notices.
    """
    if alice == bob:
        return 'key'
    return 'chsh' if (alice, bob) in CHSH_COMBINATIONS else 'discard'


def sift_key_bits(bits: list[str], alice_angles: list[int],
                  bob_angles: list[int]) -> list[str]:
    """
    The key: the rounds where both chose the same angle.

    Refuses misaligned arrays: sifting them would read out-of-range positions
    as values — the exact shape of the BB84 bug the physics doc opens with.
    """
    if len(bits) != len(alice_angles) or len(bits) != len(bob_angles):
        raise ValueError(
            f'sift_key_bits: length mismatch — {len(bits)} bits, '
            f'{len(alice_angles)} Alice angles, {len(bob_angles)} Bob angles. '
            'Sifting misaligned arrays silently corrupts the key.')
    return [bit for bit, a, b in zip(bits, alice_angles, bob_angles) if a == b]


# ─────────────────────────────────────────────────────────────────────────────
# The Bell test (§10.4)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Round:
    alice_angle: int
    bob_angle: int
    alice_bit: str
    bob_bit: str


def _key(a: int, b: int) -> str:
    return f'{a}/{b}'


def correlations(rounds: list[Round]) -> dict[str, float]:
    """E(a,b) = P(same) − P(different), for every combination present."""
    tally: dict[str, list[int]] = {}
    for r in rounds:
        same_total = tally.setdefault(_key(r.alice_angle, r.bob_angle), [0, 0])
        same_total[1] += 1
        if r.alice_bit == r.bob_bit:
            same_total[0] += 1
    return {k: (2 * same / total - 1 if total > 0 else 0.0)
            for k, (same, total) in tally.items()}


def chsh_term_counts(rounds: list[Round]) -> dict[str, int]:
    """How many rounds stand behind each CHSH term — 0 means that term is a guess."""
    counts = {_key(a, b): 0 for a, b in CHSH_COMBINATIONS}
    for r in rounds:
        k = _key(r.alice_angle, r.bob_angle)
        if k in counts:
            counts[k] += 1
    return counts


def chsh_value(corr: dict[str, float]) -> float:
    """S = |E(0,45) − E(0,135) + E(90,45) + E(90,135)|. A missing term counts 0."""
    def at(a: int, b: int) -> float:
        return corr.get(_key(a, b), 0.0)
    return abs(at(0, 45) - at(0, 135) + at(90, 45) + at(90, 135))


# ─────────────────────────────────────────────────────────────────────────────
# The boundary with the stored data
# ─────────────────────────────────────────────────────────────────────────────

# The app stores bases as the ids '1'..'4'. Physics speaks degrees, so the
# translation lives here, at the edge.
_ANGLE_OF_BASIS_ID = {'1': 0, '2': 45, '3': 90, '4': 135}
_BASIS_ID_OF_ANGLE = {angle: basis_id for basis_id, angle in _ANGLE_OF_BASIS_ID.items()}


def angle_of_basis_id(basis_id: str) -> int | None:
    return _ANGLE_OF_BASIS_ID.get(basis_id)


def basis_id_of_angle(angle: int) -> str:
    return _BASIS_ID_OF_ANGLE[angle]


# ─────────────────────────────────────────────────────────────────────────────
# The whole protocol, in one call (§10.6)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProtocolRun:
    photons: int
    eve_fraction: float
    rounds: list[Round]
    alice_key: list[str]
    bob_key: list[str]
    keys_match: bool
    key_error_rate: float
    correlations: dict[str, float]
    term_counts: dict[str, int]
    chsh: float
    eve_guessed_right_bits: int  # key bits where Eve's basis matched theirs


def run_e91_protocol(photons: int = 2000, eve_fraction: float = 0) -> ProtocolRun:
    """
    Run E91 end to end, the way the reference workshop does.

    ``eve_fraction`` is the share of pairs she intercepts. A partial tap can
    hide: S = 2√2 · (1 − f/2) crosses 2 only at f ≈ 0.586.
    """
    alice_angles = generate_random_bases(photons, ALICE_ANGLES)
    bob_angles = generate_random_bases(photons, BOB_ANGLES)
    alice_bits: list[str] = []
    bob_bits: list[str] = []
    rounds: list[Round] = []
    eve_reads: list[Interception | None] = []

    for i in range(photons):
        tapped = random.random() < eve_fraction
        interception = eavesdrop(create_entangled_pair()) if tapped else None
        eve_reads.append(interception)

        pair = interception.sent if interception else create_entangled_pair()
        alice_bit, bob_bit = measure_pair(pair, alice_angles[i], bob_angles[i])
        alice_bits.append(alice_bit)
        bob_bits.append(bob_bit)
        rounds.append(Round(alice_angles[i], bob_angles[i], alice_bit, bob_bit))

    alice_key = sift_key_bits(alice_bits, alice_angles, bob_angles)
    bob_key = sift_key_bits(bob_bits, alice_angles, bob_angles)
    mismatches = sum(1 for a, b in zip(alice_key, bob_key) if a != b)

    # Key bits Eve GUESSED RIGHT: only a basis matching theirs leaves her
    # holding their exact bit. NOT "her bit equals Alice's" (62.5 %, which
    # overstates her 2.5×). Must match what the game reports (Task 60 B2).
    eve_guessed_right_bits = sum(
        1 for i, angle in enumerate(alice_angles)
        if angle == bob_angles[i] and eve_reads[i] is not None
        and eve_reads[i].angle == angle)

    corr = correlations(rounds)
    return ProtocolRun(
        photons=photons, eve_fraction=eve_fraction, rounds=rounds,
        alice_key=alice_key, bob_key=bob_key,
        keys_match=len(alice_key) == len(bob_key) and mismatches == 0,
        key_error_rate=mismatches / len(alice_key) if alice_key else 0.0,
        correlations=corr,
        term_counts=chsh_term_counts(rounds),
        chsh=chsh_value(corr),
        eve_guessed_right_bits=eve_guessed_right_bits,
    )


def describe_run(run: ProtocolRun) -> str:
    """A run, rendered for a human. Returns a string rather than printing."""
    line = '═' * 64

    def count(combination: str) -> int:
        return sum(1 for r in run.rounds
                   if classify_combination(r.alice_angle, r.bob_angle) == combination)

    def pct(x: float) -> str:
        return f'{x * 100:.1f}%'

    out = [
        line,
        f'E91 — {run.photons} entangled pairs — Eve on {pct(run.eve_fraction)} of them',
        line,
        f"  key rounds (same basis) : {count('key')}",
        f"  Bell-test rounds        : {count('chsh')}",
        f"  discarded               : {count('discard')}",
        '',
    ]
    for a, b in CHSH_COMBINATIONS:
        k = _key(a, b)
        out.append(f'  E({a:>2}°,{b:>3}°) = '
                   f'{run.correlations.get(k, 0.0):>7.4f}   ({run.term_counts[k]} rounds)')
    verdict = ('→ above the classical bound: entanglement survived' if run.chsh > 2
               else '→ at or below 2: the channel was tampered with')
    out += [
        '',
        f'  S  = {run.chsh:.4f}   {verdict}',
        '       (undisturbed 2√2 ≈ 2.8284 · fully tapped √2 ≈ 1.4142)',
        '',
        f'  key length              : {len(run.alice_key)}',
        f"  keys identical          : {'YES' if run.keys_match else 'NO'}",
        f'  key error rate          : {pct(run.key_error_rate)}',
        f'  key bits Eve learned    : {run.eve_guessed_right_bits} / {len(run.alice_key)}',
        '',
        f"  Alice : {''.join(run.alice_key[:48])}{'…' if len(run.alice_key) > 48 else ''}",
        f"  Bob   : {''.join(run.bob_key[:48])}{'…' if len(run.bob_key) > 48 else ''}",
        line,
    ]
    return '\n'.join(out)
