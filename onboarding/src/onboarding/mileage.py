"""User-reported mileage as ground truth -- step 5 of ONBOARDING_PROCEDURE.
Skipped for fuel_type="electric"."""

from __future__ import annotations

from dataclasses import dataclass

from .supabase_client import SupabaseRestClient


def real_mileage_km_per_l(distance_km: float, fuel_consumed: float) -> float:
    if fuel_consumed <= 0:
        raise ValueError(f"fuel_consumed must be positive, got {fuel_consumed}")
    if distance_km < 0:
        raise ValueError(f"distance_km must be non-negative, got {distance_km}")
    return distance_km / fuel_consumed


def calibrate_engine_efficiency(current_engine_efficiency: float, model_predicted_total_fuel_l: float,
                                 model_predicted_idle_fuel_l: float, actual_fuel_consumed: float) -> float:
    """Solves for the engine_efficiency that would make scoring_pandera's
    physics model predict `actual_fuel_consumed` instead of `model_
    predicted_total_fuel_l`, over the same trips."""
    if current_engine_efficiency <= 0:
        raise ValueError(f"current_engine_efficiency must be positive, got {current_engine_efficiency}")
    model_predicted_moving_fuel_l = model_predicted_total_fuel_l - model_predicted_idle_fuel_l
    if model_predicted_moving_fuel_l <= 0:
        raise ValueError(
            f"model_predicted_total_fuel_l ({model_predicted_total_fuel_l}) must exceed "
            f"model_predicted_idle_fuel_l ({model_predicted_idle_fuel_l}) -- can't calibrate "
            f"from a period with no real moving-fuel signal"
        )
    calibrated_moving_fuel_target = actual_fuel_consumed - model_predicted_idle_fuel_l
    if calibrated_moving_fuel_target <= 0:
        raise ValueError(
            f"actual_fuel_consumed ({actual_fuel_consumed}) is at or below the model's own "
            f"idle-fuel estimate for this period ({model_predicted_idle_fuel_l}) -- check the date range"
        )
    k = model_predicted_moving_fuel_l * current_engine_efficiency
    return k / calibrated_moving_fuel_target


def implied_fuel_consumed(total_distance_km: float, average_mileage_km_per_l: float) -> float:
    """distance/mileage -- lets a caller reuse calibrate_engine_efficiency's
    (distance, actual_fuel_consumed) interface from a mileage rate instead
    of a one-off fuel report."""
    if average_mileage_km_per_l <= 0:
        raise ValueError(f"average_mileage_km_per_l must be positive, got {average_mileage_km_per_l}")
    return total_distance_km / average_mileage_km_per_l


@dataclass
class PeriodFuelSummary:
    n_trips: int
    total_distance_km: float
    model_predicted_total_fuel_l: float
    model_predicted_idle_fuel_l: float


def fetch_period_fuel_summary(client: SupabaseRestClient, vehicle_id: int,
                               start_date: str, end_date: str) -> PeriodFuelSummary | None:
    """Sums scoring_pandera's own stored fuel predictions (trip_scores.
    fuel.total_fuel_l/idle_fuel_l) across real trips for one vehicle in
    one date range. None if no trip in range has a fuel section (rejected
    trips have fuel=None, correctly excluded rather than treated as zero)."""
    rows = client.fetch_table(
        "trip_scores", select="session_id,start_time,distance_km,fuel",
        filters={"vehicle_id": f"eq.{vehicle_id}", "start_time": f"gte.{start_date}"},
    )
    # end_date filtered client-side: a second lt. key would collide with gte. in one dict.
    rows = [r for r in rows if r.get("start_time") and r["start_time"] < end_date]
    if not rows:
        return None

    total_distance = 0.0
    total_fuel = 0.0
    total_idle_fuel = 0.0
    n_trips = 0
    for row in rows:
        fuel = row.get("fuel")
        if not isinstance(fuel, dict) or fuel.get("total_fuel_l") is None:
            continue  # rejected trip, or fuel_profile didn't run
        total_distance += row.get("distance_km") or 0.0
        total_fuel += fuel["total_fuel_l"]
        total_idle_fuel += fuel.get("idle_fuel_l") or 0.0
        n_trips += 1

    if n_trips == 0:
        return None

    return PeriodFuelSummary(
        n_trips=n_trips, total_distance_km=round(total_distance, 3),
        model_predicted_total_fuel_l=round(total_fuel, 4), model_predicted_idle_fuel_l=round(total_idle_fuel, 4),
    )


def fetch_vehicle_average_mileage(client: SupabaseRestClient, vehicle_id: int) -> float | None:
    """vehicle_details.average_mileage (km/L), or None if unset."""
    rows = client.fetch_table("vehicle_details", select="vehicleid,average_mileage",
                               filters={"vehicleid": f"eq.{vehicle_id}"})
    if not rows:
        return None
    value = rows[0].get("average_mileage")
    return float(value) if value is not None else None
