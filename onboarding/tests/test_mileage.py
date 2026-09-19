import pytest

from onboarding.mileage import (
    calibrate_engine_efficiency, fetch_period_fuel_summary, fetch_vehicle_average_mileage,
    implied_fuel_consumed, real_mileage_km_per_l,
)


def test_real_mileage_is_a_plain_distance_over_fuel_ratio():
    assert real_mileage_km_per_l(300.0, 15.0) == 20.0


def test_real_mileage_rejects_non_physical_inputs():
    with pytest.raises(ValueError):
        real_mileage_km_per_l(100.0, 0.0)
    with pytest.raises(ValueError):
        real_mileage_km_per_l(-5.0, 10.0)


def test_calibration_lowers_efficiency_when_real_consumption_is_higher():
    eta = calibrate_engine_efficiency(
        current_engine_efficiency=0.22, model_predicted_total_fuel_l=12.0,
        model_predicted_idle_fuel_l=2.0, actual_fuel_consumed=15.0,
    )
    assert eta < 0.22


def test_calibration_raises_efficiency_when_real_consumption_is_lower():
    eta = calibrate_engine_efficiency(
        current_engine_efficiency=0.22, model_predicted_total_fuel_l=12.0,
        model_predicted_idle_fuel_l=2.0, actual_fuel_consumed=9.0,
    )
    assert eta > 0.22


def test_calibration_is_a_no_op_when_actual_matches_prediction_exactly():
    eta = calibrate_engine_efficiency(
        current_engine_efficiency=0.22, model_predicted_total_fuel_l=12.0,
        model_predicted_idle_fuel_l=2.0, actual_fuel_consumed=12.0,
    )
    assert eta == pytest.approx(0.22)


def test_calibration_rejects_reported_fuel_at_or_below_idle_estimate():
    with pytest.raises(ValueError):
        calibrate_engine_efficiency(
            current_engine_efficiency=0.22, model_predicted_total_fuel_l=12.0,
            model_predicted_idle_fuel_l=2.0, actual_fuel_consumed=1.5,
        )


def test_implied_fuel_consumed_is_distance_over_mileage():
    assert implied_fuel_consumed(total_distance_km=300.0, average_mileage_km_per_l=20.0) == 15.0


def test_implied_fuel_consumed_rejects_non_positive_mileage():
    with pytest.raises(ValueError):
        implied_fuel_consumed(total_distance_km=300.0, average_mileage_km_per_l=0.0)


class FakeClient:
    def __init__(self, rows_by_table: dict[str, list[dict]]):
        self.rows_by_table = rows_by_table
        self.calls = []

    def fetch_table(self, table, filters=None, select="*"):
        self.calls.append((table, filters, select))
        return self.rows_by_table.get(table, [])


def test_fetch_period_fuel_summary_sums_real_trips_only():
    client = FakeClient({"trip_scores": [
        {"session_id": "s1", "start_time": "2026-09-01T08:00:00Z", "distance_km": 20.0,
         "fuel": {"total_fuel_l": 1.0, "idle_fuel_l": 0.1}},
        {"session_id": "s2", "start_time": "2026-09-05T08:00:00Z", "distance_km": 15.0,
         "fuel": {"total_fuel_l": 0.8, "idle_fuel_l": 0.05}},
        {"session_id": "s3", "start_time": "2026-09-10T08:00:00Z", "distance_km": None, "fuel": None},
        {"session_id": "s4", "start_time": "2026-10-01T08:00:00Z", "distance_km": 50.0,
         "fuel": {"total_fuel_l": 3.0, "idle_fuel_l": 0.2}},
    ]})

    summary = fetch_period_fuel_summary(client, vehicle_id=42, start_date="2026-09-01", end_date="2026-09-30")

    assert summary is not None
    assert summary.n_trips == 2
    assert summary.total_distance_km == pytest.approx(35.0)
    assert summary.model_predicted_total_fuel_l == pytest.approx(1.8)
    assert summary.model_predicted_idle_fuel_l == pytest.approx(0.15)


def test_fetch_period_fuel_summary_returns_none_for_no_rows():
    client = FakeClient({"trip_scores": []})
    assert fetch_period_fuel_summary(client, vehicle_id=42, start_date="2026-09-01", end_date="2026-09-30") is None


def test_fetch_vehicle_average_mileage_returns_the_real_value():
    client = FakeClient({"vehicle_details": [{"vehicleid": 42, "average_mileage": 35.5}]})
    assert fetch_vehicle_average_mileage(client, vehicle_id=42) == pytest.approx(35.5)


def test_fetch_vehicle_average_mileage_returns_none_when_unset():
    client = FakeClient({"vehicle_details": [{"vehicleid": 42, "average_mileage": None}]})
    assert fetch_vehicle_average_mileage(client, vehicle_id=42) is None
