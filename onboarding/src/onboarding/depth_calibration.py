"""Following-distance camera calibration -- step 4 of ONBOARDING_PROCEDURE."""

from __future__ import annotations


def calibrate_depth_scale_factor(known_distance_m: float, estimated_distance_m: float) -> float:
    if known_distance_m <= 0:
        raise ValueError(f"known_distance_m must be positive, got {known_distance_m}")
    if estimated_distance_m <= 0:
        raise ValueError(f"estimated_distance_m must be positive, got {estimated_distance_m}")
    return known_distance_m / estimated_distance_m
