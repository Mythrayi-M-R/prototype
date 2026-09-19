"""Vehicle identity resolution -- step 1 of ONBOARDING_PROCEDURE."""

from __future__ import annotations

import json
from pathlib import Path

from .vehicle_profile import VehicleProfile

# Per-vehicle-type defaults, used when model isn't in MODEL_SPECS.
VEHICLE_GEOMETRY: dict[str, dict] = {
    "car": {"cog_height_m": 0.55, "track_width_m": 1.60, "mass_kg": 1200.0, "frontal_area_m2": 2.2,
            "drag_coefficient": 0.32, "rolling_resistance_coefficient": 0.012,
            "idle_fuel_lph": 0.6, "wheelbase_m": 2.6},
    "auto_rickshaw": {"cog_height_m": 0.68, "track_width_m": 1.30, "mass_kg": 550.0, "frontal_area_m2": 1.3,
                       "drag_coefficient": 0.6, "rolling_resistance_coefficient": 0.015,
                       "idle_fuel_lph": 0.3, "wheelbase_m": 2.0},
    "bike": {"cog_height_m": 0.60, "track_width_m": 0.00, "mass_kg": 150.0, "frontal_area_m2": 0.6,
             "drag_coefficient": 0.6, "rolling_resistance_coefficient": 0.015,
             "idle_fuel_lph": 0.2, "wheelbase_m": 1.4},
    "bus": {"cog_height_m": 1.40, "track_width_m": 2.30, "mass_kg": 9000.0, "frontal_area_m2": 7.5,
            "drag_coefficient": 0.6, "rolling_resistance_coefficient": 0.008,
            "idle_fuel_lph": 2.5, "engine_efficiency": 0.30, "fuel_type": "diesel", "wheelbase_m": 6.2},
}

# fuel_type="electric" overrides, applied on top of VEHICLE_GEOMETRY,
# below a curated MODEL_SPECS match. No bus/auto_rickshaw entry.
ELECTRIC_PROPULSION_DEFAULTS: dict[str, dict] = {
    "car":  {"fuel_type": "electric", "engine_efficiency": 0.85, "idle_fuel_lph": 0.05},
    "bike": {"fuel_type": "electric", "engine_efficiency": 0.85, "idle_fuel_lph": 0.01},
}

_BIKE_MODEL_KEYWORDS = (
    "himalayan", "jupiter", "avenis", "cb350", "hness", "fz", "passion", "scooty", "sp125",
    "splendor", "splendour", "activa", "pep", "shine", "pulsar", "apache", "classic 350",
    "bullet", "royal enfield", "duke", "ktm", "ntorq", "access", "burgman", "gixxer",
    "unicorn", "hornet", "dio", "ather", "ola s1", "chetak", "meteor", "continental gt",
    "yamaha", "hero", "moto", "scooter", "bike", "motorcycle",
)
_BUS_MODEL_KEYWORDS = ("bus", "coach", "starbus", "volvo b", "traveller")
_AUTO_RICKSHAW_MODEL_KEYWORDS = (
    "bajaj re", "piaggio ape", "tvs king", "mahindra treo", "mahindra alfa", "atul gem",
    "auto rickshaw", "autorickshaw", "3 wheeler", "3-wheeler", "three wheeler", "three-wheeler",
    "tuk tuk", "tuk-tuk", "tuktuk",
)
_CAR_MODEL_KEYWORDS = (
    "brv", "civic", "kwid", "ertiga", "amaze", "brio", "alto", "swift", "dezire", "wagon",
    "innova", "creta", "verna", "i10", "i20", "baleno", "city", "wr-v", "seltos", "venue",
    "nexon", "punch", "xuv", "scorpio", "thar", "fortuner", "camry", "corolla",
)

_KNOWN_VEHICLE_TYPES = frozenset(VEHICLE_GEOMETRY.keys())
_MODEL_SPECS_PATH = Path(__file__).parent / "data" / "vehicle_model_specs.json"


def _load_model_specs() -> dict[str, dict]:
    with open(_MODEL_SPECS_PATH) as f:
        return json.load(f)["entries"]


MODEL_SPECS: dict[str, dict] = _load_model_specs()


def classify_vehicle_type(model: str | None) -> str:
    """car/bike/bus/auto_rickshaw from a free-text model string. Defaults
    to "car" when empty/ambiguous (the safer failure mode: wider
    rollover-risk ratio, not a narrower one)."""
    if not model:
        return "car"
    m = model.strip().lower()
    if any(k in m for k in _BUS_MODEL_KEYWORDS):
        return "bus"
    if any(k in m for k in _AUTO_RICKSHAW_MODEL_KEYWORDS):
        return "auto_rickshaw"
    if any(k in m for k in _BIKE_MODEL_KEYWORDS):
        return "bike"
    return "car"


def resolve_vehicle_specs(
    model: str | None,
    vehicle_type_override: str | None = None,
    fuel_type_override: str | None = None,
) -> tuple[str, dict]:
    """Returns (vehicle_type, specs_dict): curated MODEL_SPECS match
    merged on top of the vehicle_type bucket. `*_override` values (from
    the onboarding pickers) win over guessing from `model`."""
    if vehicle_type_override and vehicle_type_override in _KNOWN_VEHICLE_TYPES:
        vehicle_type = vehicle_type_override
    else:
        vehicle_type = classify_vehicle_type(model)
    bucket = VEHICLE_GEOMETRY.get(vehicle_type, VEHICLE_GEOMETRY["car"])
    if fuel_type_override == "electric":
        electric_overrides = ELECTRIC_PROPULSION_DEFAULTS.get(vehicle_type)
        if electric_overrides:
            bucket = {**bucket, **electric_overrides}
    m = (model or "").strip().lower()
    for key, specs in MODEL_SPECS.items():
        if key in m:
            # "source_notes" is a citation string in the JSON, not a real field.
            real_fields = {k: v for k, v in specs.items() if k in VehicleProfile.model_fields}
            return vehicle_type, {**bucket, **real_fields}
    return vehicle_type, bucket


def lever_arm_from_front_tire_measurement(
    front_tire_to_phone_m: tuple[float, float, float],
    wheelbase_m: float, track_width_m: float, driver_side: str = "right",
) -> tuple[float, float, float]:
    """Driver-side-front-tire-relative measurement (forward, left, up
    meters; India/RHD default driver_side="right") -> phone-to-rear-
    axle-center lever arm."""
    if driver_side not in ("left", "right"):
        raise ValueError(f"driver_side must be 'left' or 'right', got {driver_side!r}")

    fwd, left, up = front_tire_to_phone_m
    phone_to_tire = (-fwd, -left, -up)

    half_track = track_width_m / 2.0
    tire_to_rear_axle_left = half_track if driver_side == "right" else -half_track
    tire_to_rear_axle = (-wheelbase_m, tire_to_rear_axle_left, 0.0)

    return (
        phone_to_tire[0] + tire_to_rear_axle[0],
        phone_to_tire[1] + tire_to_rear_axle[1],
        phone_to_tire[2] + tire_to_rear_axle[2],
    )


def resolve_vehicle_profile(
    model: str | None,
    front_tire_to_phone_m: tuple[float, float, float] | None = None,
    driver_side: str = "right",
    vehicle_type_override: str | None = None,
    fuel_type_override: str | None = None,
) -> VehicleProfile:
    """The onboarding entrypoint: model string (always available) plus
    an optional physical lever-arm measurement -> a fully-resolved
    VehicleProfile ready to persist to Supabase."""
    vehicle_type, specs = resolve_vehicle_specs(model, vehicle_type_override, fuel_type_override)
    profile = VehicleProfile(vehicle_type=vehicle_type, **specs)

    if front_tire_to_phone_m is not None:
        lever_arm = lever_arm_from_front_tire_measurement(
            front_tire_to_phone_m, profile.wheelbase_m, profile.track_width_m, driver_side,
        )
        profile = profile.model_copy(update={
            "lever_arm_vehicle_frame_m": lever_arm, "lever_arm_calibrated": True,
        })

    return profile
