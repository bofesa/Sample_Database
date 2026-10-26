"""Node identifier generation and collision-risk calculations."""

from __future__ import annotations

import math
import secrets


DEFAULT_ID_TOTAL_LENGTH = 6
MIN_ID_TOTAL_LENGTH = 6
MAX_ID_TOTAL_LENGTH = 32
DEFAULT_COLLISION_TARGET = 0.0001  # 0.01%
MAX_GENERATION_ATTEMPTS = 1000


def validate_id_total_length(value):
    try:
        length = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("ID length must be a whole number.") from exc
    if not MIN_ID_TOTAL_LENGTH <= length <= MAX_ID_TOTAL_LENGTH:
        raise ValueError(
            f"ID length must be between {MIN_ID_TOTAL_LENGTH} and {MAX_ID_TOTAL_LENGTH}."
        )
    return length


def identifier_space(total_length, processing_step=False):
    length = validate_id_total_length(total_length)
    random_digits = length - 1 if processing_step else length
    return 16 ** random_digits


def collision_probability(node_count, total_length, processing_step=False):
    """Return the birthday probability of at least one duplicate."""
    try:
        count = int(node_count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Node count must be a whole number.") from exc
    if count < 0:
        raise ValueError("Node count cannot be negative.")
    if count < 2:
        return 0.0

    space = identifier_space(total_length, processing_step=processing_step)
    if count > space:
        return 1.0

    # Exact log-product for normal planning ranges; the stable birthday
    # approximation avoids an expensive UI calculation for very large input.
    if count <= 10000:
        log_no_collision = sum(math.log1p(-index / space) for index in range(count))
    else:
        pairs = count * (count - 1) / 2
        log_no_collision = -pairs / space
    return min(1.0, max(0.0, -math.expm1(log_no_collision)))


def recommend_total_length(node_count, target_probability=DEFAULT_COLLISION_TARGET):
    try:
        target = float(target_probability)
    except (TypeError, ValueError) as exc:
        raise ValueError("Collision target must be a number.") from exc
    if not 0 < target < 1:
        raise ValueError("Collision target must be between 0 and 1.")

    for length in range(MIN_ID_TOTAL_LENGTH, MAX_ID_TOTAL_LENGTH + 1):
        if collision_probability(node_count, length, processing_step=False) <= target:
            return length
    return None


def generate_random_id(total_length=DEFAULT_ID_TOTAL_LENGTH, processing_step=False):
    length = validate_id_total_length(total_length)
    random_digits = length - 1 if processing_step else length
    random_hex = secrets.token_hex((random_digits + 1) // 2)[:random_digits]
    return f"P{random_hex}" if processing_step else random_hex


def generate_unique_id(existing_ids, total_length, processing_step=False,
                       candidate_factory=None, max_attempts=MAX_GENERATION_ATTEMPTS):
    """Generate an ID unique only within the supplied in-memory identifier set."""
    known = {str(value).strip().casefold() for value in existing_ids}
    factory = candidate_factory or generate_random_id
    for _attempt in range(max_attempts):
        candidate = factory(total_length, processing_step)
        if candidate.casefold() not in known:
            return candidate
    raise RuntimeError(
        f"Could not generate a unique {total_length}-character ID after "
        f"{max_attempts} attempts."
    )
