"""Single source of truth for the vehicle-setup sequence: what a driver
is asked, when, and which VehicleProfile/VehicleConfig field it
populates. Validated against both by their respective test suites."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OnboardingStep:
    order: int
    title: str
    frequency: str  # "one-time" | "recurring"
    asks_driver_for: str
    populates: tuple[str, ...]  # VehicleProfile/VehicleConfig field names this step sets
    real_gap: str | None = None  # None if fully wired today; otherwise what's missing
    applies_to_fuel_types: tuple[str, ...] | None = None  # None = all fuel types


ONBOARDING_PROCEDURE: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        order=1, title="Vehicle identity", frequency="one-time",
        asks_driver_for="vehicle model (free text) + vehicle type (car/two-wheeler/bus/auto-rickshaw picker)",
        populates=("vehicle_type", "mass_kg", "frontal_area_m2", "drag_coefficient",
                   "rolling_resistance_coefficient", "cog_height_m", "track_width_m", "wheelbase_m",
                   "idle_fuel_lph", "engine_efficiency"),
        real_gap=None,
    ),
    OnboardingStep(
        order=2, title="Fuel type", frequency="one-time",
        asks_driver_for="Petrol / Diesel / CNG / Electric (single-choice picker)",
        populates=("fuel_type",),
        real_gap="vehicle_details has no fuel_type column yet -- app-team ask",
    ),
    OnboardingStep(
        order=3, title="Phone lever-arm measurement", frequency="one-time",
        asks_driver_for="tape-measure distance from the driver-side front tire to the mounted phone",
        populates=("lever_arm_vehicle_frame_m", "lever_arm_calibrated"),
        real_gap="no live camera_offset_forward_m/_left_m/_up_m columns yet -- fetch already wired, "
                 "ready once the app adds them",
    ),
    OnboardingStep(
        order=4, title="Following-distance camera calibration", frequency="one-time",
        asks_driver_for="one photo of a real reference vehicle/object at a measured distance (10.0m recommended)",
        populates=("depth_scale_factor", "depth_scale_factor_calibrated"),
        real_gap="no live depth_scale_factor/depth_scale_factor_calibrated columns yet -- fetch already wired, ready once the app adds them",
    ),
    OnboardingStep(
        order=5, title="Mileage report", frequency="recurring (every fill-up)",
        asks_driver_for="liters (or kg for CNG) of fuel purchased since their last fill-up",
        populates=("engine_efficiency",),
        real_gap="vehicle_details.average_mileage is live but currently always null -- no app UI "
                 "collects it yet; scoring_pandera's calibrate_engine_efficiency_from_user_mileage.py "
                 "already reads it automatically once populated",
        applies_to_fuel_types=("petrol", "diesel", "cng"),  # skipped for electric -- see README.md
    ),
)
