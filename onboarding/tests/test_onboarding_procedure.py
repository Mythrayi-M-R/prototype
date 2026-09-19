"""onboarding.onboarding_procedure.ONBOARDING_PROCEDURE is the single
source of truth for the real vehicle-setup flow -- these tests make it a
LIVING spec, validated here against THIS package's own VehicleProfile
(independent of scoring_pandera). scoring_pandera/tests/unit/
test_onboarding_procedure_consistency.py separately validates the same
spec against scoring_pandera's own VehicleConfig, loading this file by
path -- two independent checks on the same spec, one per side of the
boundary, matching the deliberate independence of this package."""

from onboarding.onboarding_procedure import ONBOARDING_PROCEDURE
from onboarding.vehicle_profile import VehicleProfile


def test_every_populated_field_is_a_real_vehicle_profile_field():
    real_fields = set(VehicleProfile.model_fields.keys())
    for step in ONBOARDING_PROCEDURE:
        for field in step.populates:
            assert field in real_fields, f"step {step.order} ({step.title!r}) claims to populate " \
                f"{field!r}, which is not a real VehicleProfile field"


def test_steps_are_numbered_consecutively_from_one():
    orders = [step.order for step in ONBOARDING_PROCEDURE]
    assert orders == list(range(1, len(ONBOARDING_PROCEDURE) + 1))


def test_every_step_has_a_frequency():
    for step in ONBOARDING_PROCEDURE:
        assert step.frequency in ("one-time", "recurring (every fill-up)")


def test_driver_is_never_asked_for_fields_the_service_can_derive_itself():
    intentional_refinements = {"engine_efficiency"}
    derived_by_step_1 = set(ONBOARDING_PROCEDURE[0].populates)
    for step in ONBOARDING_PROCEDURE[1:]:
        overlap = derived_by_step_1 & set(step.populates) - intentional_refinements
        assert not overlap, f"step {step.order} ({step.title!r}) re-asks for {overlap}, " \
            f"already derived by step 1"


def test_every_field_with_no_safe_generic_default_is_covered_by_some_step():
    all_populated = {field for step in ONBOARDING_PROCEDURE for field in step.populates}
    must_be_covered = {
        "vehicle_type", "fuel_type", "lever_arm_vehicle_frame_m", "lever_arm_calibrated",
        "depth_scale_factor", "depth_scale_factor_calibrated", "engine_efficiency",
    }
    missing = must_be_covered - all_populated
    assert not missing, f"fields with no safe generic default but no onboarding step: {missing}"


def test_mileage_report_step_is_skipped_for_electric_vehicles():
    """Decided 2026-09-19 ("we can skip calibration for evs right"): an
    EV's engine_efficiency varies far less than a combustion engine's
    real-world part-load efficiency, so the literature-backed default
    from step 1 is treated as good enough without per-driver
    recalibration -- step 5 must not claim to apply to fuel_type=
    "electric"."""
    mileage_step = next(step for step in ONBOARDING_PROCEDURE if step.title == "Mileage report")
    assert mileage_step.applies_to_fuel_types is not None
    assert "electric" not in mileage_step.applies_to_fuel_types


def test_every_step_restricting_fuel_types_only_uses_real_vehicle_profile_values():
    real_fuel_types = set(VehicleProfile.model_fields["fuel_type"].annotation.__args__)
    for step in ONBOARDING_PROCEDURE:
        if step.applies_to_fuel_types is not None:
            assert set(step.applies_to_fuel_types) <= real_fuel_types
