# vehnway-onboarding

Vehicle-setup / calibration service for `scoring_pandera`. Produces a
`VehicleProfile` from what a driver can actually provide plus a spec
lookup. Independent of `scoring_pandera`'s dependencies (pandas, numpy,
pandera, torch) — deploys as its own small service.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Test

```bash
.venv/bin/python -m pytest -q
```

## Environment

| Variable | Purpose |
|---|---|
| `VEHNWAY_SUPABASE_URL` | Supabase project URL |
| `VEHNWAY_SUPABASE_SERVICE_KEY` | Service-role key (not anon — reads/writes `vehicle_details` directly) |

Read directly from the environment, no `.env` layer.

## Modules

| File | Purpose |
|---|---|
| `vehicle_profile.py` | `VehicleProfile` — output record. Field names match `scoring_pandera.VehicleConfig` 1:1. |
| `vehicle_specs.py` | Model string + type → mass/wheelbase/geometry/fuel resolution. |
| `depth_calibration.py` | Following-distance camera scale-factor calibration. |
| `mileage.py` | Mileage-based `engine_efficiency` calibration + the Supabase reads it needs. |
| `supabase_client.py` | Minimal REST client (list-of-dicts, no pandas). |
| `onboarding_procedure.py` | `ONBOARDING_PROCEDURE` — the setup sequence, single source of truth. |
| `data/vehicle_model_specs.json` | Curated per-model spec database. Canonical copy — edit here first. |

## Onboarding sequence

`onboarding_procedure.ONBOARDING_PROCEDURE` is the authoritative version
of this table (tested against both `VehicleProfile` and `scoring_pandera.VehicleConfig`).

| # | Step | Frequency | Asks driver for | Populates | Status |
|---|---|---|---|---|---|
| 1 | Vehicle identity | one-time | model (free text) + vehicle type picker | `vehicle_type`, `mass_kg`, `frontal_area_m2`, `drag_coefficient`, `rolling_resistance_coefficient`, `cog_height_m`, `track_width_m`, `wheelbase_m`, `idle_fuel_lph`, `engine_efficiency` | live |
| 2 | Fuel type | one-time | Petrol / Diesel / CNG / Electric picker | `fuel_type` | `vehicle_details.fuel_type` column doesn't exist yet |
| 3 | Lever-arm measurement | one-time | tape-measure distance, driver-side front tire → phone (fwd/left/up, m) | `lever_arm_vehicle_frame_m`, `lever_arm_calibrated` | `camera_offset_forward_m/_left_m/_up_m` columns don't exist yet; fetch pre-wired in `scoring_pandera/run_from_supabase.py` |
| 4 | Camera depth calibration | one-time | one photo of a reference object at a measured distance (10.0m recommended) | `depth_scale_factor`, `depth_scale_factor_calibrated` | columns don't exist yet; fetch pre-wired in `scoring_pandera/run_from_supabase.py` (applied only when `depth_scale_factor_calibrated` is true) |
| 5 | Mileage report | recurring (fill-up) | liters (kg for CNG) since last fill-up | `engine_efficiency` | `vehicle_details.average_mileage` live, no UI writes it yet. **Skipped for `fuel_type="electric"`.** |

Never asked of the driver: `drivetrain_efficiency`, phone mount
orientation (`r_phone_to_vehicle` — fixed, universal mount: landscape,
screen facing driver, left-bottom corner, camera on road).

Model not in `data/vehicle_model_specs.json` → falls back to the
`vehicle_type` bucket default. Adding a new model is a data change to
that JSON file, not a code change.

## Naming conventions

- `resolve_*` functions take a free-text `model` and optional
  `*_override` params (real values from app pickers, e.g.
  `vehicle_type_override`, `fuel_type_override`); an override always
  wins over guessing from `model`.
- `*_calibrated: bool` fields mark whether a value is a measured
  per-vehicle input (`True`) or an unmeasured default (`False`).
- Lever arm convention: `[forward, left, up]` meters, **from phone to
  rear-axle center** (not front tire — see `lever_arm_from_front_tire_measurement`
  for the conversion from what a driver can actually measure).
- `driver_side`: `"right"` = India/RHD (the default).
- CNG mileage/fuel figures are "liters at typical storage density"
  (~200 bar), not mass — Indian CNG stations sell by kg; convert before
  calling `mileage.py`.
- `fuel_type="electric"`: `idle_fuel_lph` is actually **kWh/h** (not
  L/h) for this fuel type, and `engine_efficiency` means combined
  motor+inverter efficiency, not thermal efficiency. See
  `scoring_pandera`'s `fuel_profile.FUEL_DEFAULTS["electric"]` for the
  matching unit reinterpretation on the scoring side (1 kWh = 3.6 MJ
  reused as the LHV constant).
- `MODEL_SPECS` keys are lowercase substrings matched against
  `vehicle_details.model`, first match wins. `source_notes` in the JSON
  is a citation string, not a schema field.

## Duplication with scoring_pandera

`vehicle_specs.py`'s `VEHICLE_GEOMETRY`, `ELECTRIC_PROPULSION_DEFAULTS`,
model keyword lists, and `data/vehicle_model_specs.json` are real
duplicates of `scoring_pandera`'s own copies, not a shared library —
`scoring_pandera` still resolves specs independently for direct/offline
runs. This package's `vehicle_model_specs.json` is canonical
(producer-side); sync to `scoring_pandera`'s copy manually.

## Not yet built

No HTTP/worker entrypoint — this is the logic layer only. Needs a
decision: HTTP API called by the mobile app, or a worker reacting to
new `vehicle_details` rows.
