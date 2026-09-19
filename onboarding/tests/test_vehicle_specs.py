"""onboarding.vehicle_specs resolves a real VehicleProfile from only a
vehicle model string and an optional physical lever-arm measurement.
Ported test suite (adapted for this package's own VehicleProfile, not
scoring_pandera's VehicleConfig) from scoring_pandera/tests/unit/
test_vehicle_specs.py -- see that file's own history for the two real
bugs these tests were built to catch (source_notes leaking into a real
profile; MODEL_SPECS replacing the bucket instead of merging)."""

import pytest

from onboarding.vehicle_specs import (
    MODEL_SPECS, classify_vehicle_type, lever_arm_from_front_tire_measurement,
    resolve_vehicle_profile, resolve_vehicle_specs, VEHICLE_GEOMETRY,
)


def test_curated_model_match_beats_the_vehicle_type_bucket():
    vtype, specs = resolve_vehicle_specs("TVS Scooty Pep plus")
    assert vtype == "bike"
    assert specs["wheelbase_m"] == 1.23
    assert specs != VEHICLE_GEOMETRY["bike"]


def test_unmatched_model_falls_back_to_vehicle_type_bucket():
    vtype, specs = resolve_vehicle_specs("Maruti Swift VXI")
    assert vtype == "car"
    assert specs == VEHICLE_GEOMETRY["car"]


def test_no_model_at_all_falls_back_to_car_bucket():
    vtype, specs = resolve_vehicle_specs(None)
    assert vtype == "car"
    assert specs == VEHICLE_GEOMETRY["car"]


def test_valid_vehicle_type_override_wins_over_model_string_guess():
    vtype, _ = resolve_vehicle_specs("Honda BRV", vehicle_type_override="bike")
    assert vtype == "bike"


def test_invalid_vehicle_type_override_falls_back_to_guessing():
    vtype, _ = resolve_vehicle_specs("Honda BRV", vehicle_type_override="not_a_real_type")
    assert vtype == "car"


def test_source_notes_never_leaks_into_a_real_vehicle_profile():
    """Real bug found and fixed 2026-09-18 (scoring_pandera side):
    pydantic's model_copy(update=...) does NOT enforce extra="forbid" --
    an unfiltered "source_notes" citation string (a real field in the
    JSON database, NOT a VehicleProfile field) would silently attach as
    a phantom attribute rather than raising or being cleanly absent."""
    p = resolve_vehicle_profile("Honda Amaze")
    assert "source_notes" not in p.model_dump()


def test_every_real_fleet_model_string_resolves_to_exactly_one_curated_entry():
    """Confirmed directly against the live Supabase vehicle_details
    table 2026-09-18."""
    real_fleet_models_and_expected_keys = {
        "Alto vxi": "alto", "Ertiga": "ertiga", "Himalayan": "himalayan",
        "Honda Amaze": "amaze", "Honda BRV": "honda brv", "Honda Brio": "brio",
        "Honda CB350 Hness": "cb350", "Honda Civic": "civic", "Renault Kwid": "kwid",
        "Swift dezire": "dezire", "TVS Scooty Pep plus": "scooty", "fz": "fz",
        "passion pro": "passion pro", "suzuki avenis": "avenis", "tvs jupiter": "jupiter",
    }
    for model, expected_key in real_fleet_models_and_expected_keys.items():
        m = model.strip().lower()
        matches = [key for key in MODEL_SPECS if key in m]
        assert matches == [expected_key], f"{model!r} matched {matches}, expected [{expected_key!r}]"


def test_cb350_and_himalayan_mass_includes_rider_load():
    cb350 = resolve_vehicle_profile("Honda CB350 Hness")
    assert cb350.mass_kg == 231.0
    himalayan = resolve_vehicle_profile("Himalayan")
    assert himalayan.mass_kg == 249.0


def test_classify_vehicle_type_matches_known_categories():
    assert classify_vehicle_type("Honda Civic") == "car"
    assert classify_vehicle_type("TVS Jupiter") == "bike"
    assert classify_vehicle_type("Tata Starbus") == "bus"
    assert classify_vehicle_type("Bajaj RE") == "auto_rickshaw"
    assert classify_vehicle_type(None) == "car"
    assert classify_vehicle_type("") == "car"


def test_lever_arm_zero_offset_equals_tire_to_rear_axle_vector():
    lever = lever_arm_from_front_tire_measurement(
        (0.0, 0.0, 0.0), wheelbase_m=2.6, track_width_m=1.6, driver_side="right")
    assert lever == (-2.6, 0.8, 0.0)


def test_lever_arm_left_hand_drive_mirrors_the_lateral_correction():
    right = lever_arm_from_front_tire_measurement(
        (0.0, 0.0, 0.0), wheelbase_m=2.6, track_width_m=1.6, driver_side="right")
    left = lever_arm_from_front_tire_measurement(
        (0.0, 0.0, 0.0), wheelbase_m=2.6, track_width_m=1.6, driver_side="left")
    assert right[0] == left[0]
    assert right[1] == -left[1]


def test_lever_arm_rejects_invalid_driver_side():
    with pytest.raises(ValueError):
        lever_arm_from_front_tire_measurement((0, 0, 0), wheelbase_m=2.6, track_width_m=1.6, driver_side="front")


def test_resolve_vehicle_profile_without_measurement_stays_uncalibrated():
    p = resolve_vehicle_profile("Maruti Swift VXI")
    assert p.lever_arm_calibrated is False


def test_resolve_vehicle_profile_with_measurement_becomes_calibrated():
    p = resolve_vehicle_profile("Maruti Swift VXI", front_tire_to_phone_m=(1.5, -0.4, 0.6))
    assert p.lever_arm_calibrated is True
    assert p.lever_arm_vehicle_frame_m == pytest.approx((-4.1, 1.2, -0.6))


def test_real_ev_models_resolve_to_electric_fuel_type_not_petrol():
    """Mirrors scoring_pandera's own test of the same real bug fix
    (2026-09-19, "include EV also"): ather/ola s1/chetak were already
    matched bike keywords with no fuel-physics entry until now."""
    for model, expected_mass_kg in [("Ather 450", 161.0), ("Ola S1", 171.0), ("Bajaj Chetak", 184.0)]:
        p = resolve_vehicle_profile(model)
        assert p.vehicle_type == "bike"
        assert p.fuel_type == "electric"
        assert p.engine_efficiency == pytest.approx(0.85)
        assert p.mass_kg == pytest.approx(expected_mass_kg)


def test_fuel_type_override_electric_applies_to_an_uncurated_bike_model():
    petrol_p = resolve_vehicle_profile("Some Unknown Two Wheeler Xyz", vehicle_type_override="bike")
    assert petrol_p.fuel_type == "petrol"
    ev_p = resolve_vehicle_profile(
        "Some Unknown Two Wheeler Xyz", vehicle_type_override="bike", fuel_type_override="electric",
    )
    assert ev_p.fuel_type == "electric"
    assert ev_p.engine_efficiency == pytest.approx(0.85)
    assert ev_p.idle_fuel_lph == pytest.approx(0.01)


def test_fuel_type_override_electric_is_a_noop_for_an_unsupported_vehicle_type():
    p = resolve_vehicle_profile("Ashok Leyland City Bus", fuel_type_override="electric")
    assert p.vehicle_type == "bus"
    assert p.fuel_type == "diesel"


def test_curated_ev_model_beats_the_generic_electric_override():
    p = resolve_vehicle_profile("Ather 450", fuel_type_override="electric")
    assert p.mass_kg == pytest.approx(161.0)
