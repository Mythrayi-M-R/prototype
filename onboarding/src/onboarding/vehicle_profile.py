"""VehicleProfile -- output of ONBOARDING_PROCEDURE. Field names match
scoring_pandera's VehicleConfig 1:1 (enforced by scoring_pandera's own
test suite, not by this package)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VehicleProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_type: Literal["car", "bike", "bus", "auto_rickshaw"] = "car"
    mass_kg: float = 1200.0
    frontal_area_m2: float = 2.2
    drag_coefficient: float = 0.32
    rolling_resistance_coefficient: float = 0.012
    cog_height_m: float = 0.55
    track_width_m: float = 1.60
    wheelbase_m: float = 2.6
    idle_fuel_lph: float = 0.6
    engine_efficiency: float = 0.22
    fuel_type: Literal["petrol", "diesel", "cng", "electric"] = "petrol"

    lever_arm_vehicle_frame_m: tuple[float, float, float] = (0.0, 0.0, 0.0)
    lever_arm_calibrated: bool = False

    depth_scale_factor: float = 1.0
    depth_scale_factor_calibrated: bool = False
