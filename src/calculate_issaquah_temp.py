#!/usr/bin/env python3
"""Build and validate daily Issaquah Creek temperature proxies for 1997-2025.

This is a hindcast/interpolation model, not a continuous sensor record. It is
calibrated to King County grab samples at station 0631 using continuous USGS
daily discharge, NOAA daily air temperature, and seasonal terms. The modeled
responses are day-level proxies for grab-sample water temperature; they are not
observed daily maxima and must not be presented as regulatory 7DADMax. The
pipeline also validates pre-specified biological windows, audits extrapolation,
and builds a life-stage exposure table before association testing.

The implementation intentionally uses only the Python standard library so the
acquisition and model can run before the project's optional analysis packages
are installed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_START = date(1997, 1, 1)
DEFAULT_END = date(2025, 12, 31)
NOAA_STATION = "USW00024233"
NOAA_STATION_NAME = "Seattle-Tacoma International Airport"
USGS_SITE = "12121600"
KING_COUNTY_LOCATOR = "0631"
KING_COUNTY_SITE_NAME = "Issaquah Creek at SE 56th St"
MAX_INTERPOLATION_GAP_DAYS = 3
MIN_WATER_TEMP_C = 0.0
MAX_WATER_TEMP_C = 30.0
RIDGE_ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)


@dataclass(frozen=True)
class CalibrationRow:
    sample_date: date
    target_c: float
    sample_count: int
    features: tuple[float, ...]


@dataclass(frozen=True)
class WindowDefinition:
    window_id: str
    analysis_id: str
    species: str
    life_stage: str
    start_month: int
    start_day: int
    end_month: int
    end_day: int
    return_year_offset: int
    alignment_definition: str

    def contains(self, item_date: date) -> bool:
        month_day = (item_date.month, item_date.day)
        return (self.start_month, self.start_day) <= month_day <= (
            self.end_month,
            self.end_day,
        )

    def start_date(self, year: int) -> date:
        return date(year, self.start_month, self.start_day)

    def end_date(self, year: int) -> date:
        return date(year, self.end_month, self.end_day)


HYPOTHESIS_WINDOWS = (
    WindowDefinition(
        window_id="jun_sep",
        analysis_id="A5",
        species="Coho",
        life_stage="juvenile_rearing",
        start_month=6,
        start_day=1,
        end_month=9,
        end_day=30,
        return_year_offset=2,
        alignment_definition=(
            "primary Coho cohort proxy: exposure_year = return_year - 2"
        ),
    ),
    WindowDefinition(
        window_id="aug15_sep30",
        analysis_id="A1",
        species="Chinook",
        life_stage="adult_migration",
        start_month=8,
        start_day=15,
        end_month=9,
        end_day=30,
        return_year_offset=0,
        alignment_definition="adult migration exposure_year = return_year",
    ),
    WindowDefinition(
        window_id="sep15_oct31",
        analysis_id="A3",
        species="Coho",
        life_stage="adult_migration",
        start_month=9,
        start_day=15,
        end_month=10,
        end_day=31,
        return_year_offset=0,
        alignment_definition="adult migration exposure_year = return_year",
    ),
)


@dataclass
class RidgeModel:
    feature_names: tuple[str, ...]
    feature_means: tuple[float, ...]
    feature_scales: tuple[float, ...]
    standardized_coefficients: tuple[float, ...]
    intercept_standardized: float
    alpha: float

    def predict_one(self, features: Sequence[float]) -> float:
        standardized = [
            (value - mean) / scale
            for value, mean, scale in zip(
                features, self.feature_means, self.feature_scales
            )
        ]
        return self.intercept_standardized + sum(
            coefficient * value
            for coefficient, value in zip(
                self.standardized_coefficients, standardized
            )
        )

    def raw_coefficients(self) -> dict[str, float]:
        coefficients = {
            name: coefficient / scale
            for name, coefficient, scale in zip(
                self.feature_names,
                self.standardized_coefficients,
                self.feature_scales,
            )
        }
        coefficients["intercept"] = self.intercept_standardized - sum(
            coefficients[name] * mean
            for name, mean in zip(self.feature_names, self.feature_means)
        )
        return coefficients


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a continuous daily Issaquah Creek temperature proxy "
            "calibrated to King County grab samples."
        )
    )
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=DEFAULT_START,
        help="First output date (default: 1997-01-01).",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=DEFAULT_END,
        help="Last output date (default: 2025-12-31).",
    )
    parser.add_argument(
        "--snapshot-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Access date used for the immutable raw-data snapshot directory.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Raw cache directory. Defaults to data/bronze/temperature_proxy/<date>.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "temperature_proxy",
        help="Directory for daily, annual, calibration, and diagnostic outputs.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require cached raw files and make no network requests.",
    )
    return parser.parse_args()


def inclusive_dates(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError(f"End date {end} precedes start date {start}.")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def request_bytes(url: str, attempts: int = 3, timeout_seconds: int = 120) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "issaquah-salmon-study/temperature-proxy"},
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"Unable to download {url}: {last_error}") from last_error


def load_or_fetch(
    path: Path,
    url: str,
    validator: Callable[[bytes], object],
    offline: bool,
) -> tuple[bytes, object, str]:
    if path.exists():
        payload = path.read_bytes()
        return payload, validator(payload), "cached"
    if offline:
        raise FileNotFoundError(f"Offline mode requires cached source: {path}")
    payload = request_bytes(url)
    parsed = validator(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return payload, parsed, "downloaded"


def usgs_url(start: date, end: date) -> str:
    parameters = {
        "format": "json",
        "sites": USGS_SITE,
        "startDT": start.isoformat(),
        "endDT": end.isoformat(),
        "statCd": "00003",
        "parameterCd": "00060",
    }
    return "https://waterservices.usgs.gov/nwis/dv/?" + urllib.parse.urlencode(parameters)


def noaa_url(start: date, end: date) -> str:
    parameters = {
        "dataset": "daily-summaries",
        "stations": NOAA_STATION,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dataTypes": "TMAX,TMIN",
        "units": "metric",
        "format": "csv",
    }
    return "https://www.ncei.noaa.gov/access/services/data/v1?" + urllib.parse.urlencode(
        parameters
    )


def king_county_url() -> str:
    parameters = {
        "$limit": "50000",
        "$where": f"parameter='Temperature' AND locator='{KING_COUNTY_LOCATOR}'",
        "$order": "collect_datetime",
    }
    return "https://data.kingcounty.gov/resource/vwmt-pvjw.csv?" + urllib.parse.urlencode(
        parameters
    )


def parse_usgs(payload: bytes) -> dict[date, tuple[float, str]]:
    document = json.loads(payload.decode("utf-8"))
    series = document.get("value", {}).get("timeSeries", [])
    discharge_series = None
    for item in series:
        codes = item.get("variable", {}).get("variableCode", [])
        if any(code.get("value") == "00060" for code in codes):
            discharge_series = item
            break
    if discharge_series is None:
        raise ValueError("USGS response has no parameter 00060 discharge series.")

    values_groups = discharge_series.get("values", [])
    if not values_groups:
        raise ValueError("USGS discharge series has no values block.")
    output: dict[date, tuple[float, str]] = {}
    for item in values_groups[0].get("value", []):
        value = float(item["value"])
        if value <= -999000:
            continue
        item_date = date.fromisoformat(item["dateTime"][:10])
        qualifiers = ";".join(item.get("qualifiers", []))
        output[item_date] = (value, qualifiers)
    if not output:
        raise ValueError("USGS response contains no usable discharge observations.")
    return output


def optional_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value)


def parse_noaa(payload: bytes) -> dict[date, tuple[float | None, float | None]]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    required = {"STATION", "DATE", "TMAX", "TMIN"}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError(f"NOAA response is missing columns: {sorted(required)}")
    output: dict[date, tuple[float | None, float | None]] = {}
    for row in reader:
        if row["STATION"] != NOAA_STATION:
            continue
        item_date = date.fromisoformat(row["DATE"][:10])
        output[item_date] = (optional_float(row["TMIN"]), optional_float(row["TMAX"]))
    if not output:
        raise ValueError(
            f"NOAA response contains no observations for station {NOAA_STATION}."
        )
    return output


def parse_king_county(payload: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    required = {
        "collect_datetime",
        "locator",
        "site",
        "parameter",
        "value",
        "units",
        "qualityid",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError(f"King County response is missing columns: {sorted(required)}")
    rows = list(reader)
    if not rows:
        raise ValueError("King County response contains no temperature samples.")
    return rows


def interpolate_short_gaps(
    values: list[float | None],
    label: str,
    max_gap: int = MAX_INTERPOLATION_GAP_DAYS,
) -> tuple[list[float], list[bool]]:
    filled = list(values)
    interpolated = [False] * len(values)
    index = 0
    while index < len(filled):
        if filled[index] is not None:
            index += 1
            continue
        gap_start = index
        while index < len(filled) and filled[index] is None:
            index += 1
        gap_end = index
        gap_length = gap_end - gap_start
        has_bounds = gap_start > 0 and gap_end < len(filled)
        if has_bounds and gap_length <= max_gap:
            previous = float(filled[gap_start - 1])
            following = float(filled[gap_end])
            for offset in range(gap_length):
                fraction = (offset + 1) / (gap_length + 1)
                filled[gap_start + offset] = previous + fraction * (following - previous)
                interpolated[gap_start + offset] = True

    missing_indices = [index for index, value in enumerate(filled) if value is None]
    if missing_indices:
        raise ValueError(
            f"{label} has {len(missing_indices)} unfilled values; only internal gaps of "
            f"at most {max_gap} days may be interpolated."
        )
    return [float(value) for value in filled], interpolated


def trailing_mean(values: Sequence[float], window: int) -> list[float]:
    output: list[float] = []
    running_sum = 0.0
    for index, value in enumerate(values):
        running_sum += value
        if index >= window:
            running_sum -= values[index - window]
        denominator = min(index + 1, window)
        output.append(running_sum / denominator)
    return output


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Regression matrix is singular.")
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                value - factor * pivot_row_value
                for value, pivot_row_value in zip(augmented[row], augmented[column])
            ]
    return [augmented[row][-1] for row in range(size)]


def fit_ridge(
    feature_names: Sequence[str],
    rows: Sequence[CalibrationRow],
    alpha: float,
) -> RidgeModel:
    if len(rows) <= len(feature_names):
        raise ValueError("Insufficient calibration rows for the regression model.")
    columns = list(zip(*(row.features for row in rows)))
    means = [statistics.fmean(column) for column in columns]
    scales = [
        math.sqrt(statistics.fmean((value - mean) ** 2 for value in column))
        for column, mean in zip(columns, means)
    ]
    if any(scale < 1e-12 for scale in scales):
        raise ValueError("At least one regression feature is constant.")
    standardized = [
        [(value - mean) / scale for value, mean, scale in zip(row.features, means, scales)]
        for row in rows
    ]
    targets = [row.target_c for row in rows]
    target_mean = statistics.fmean(targets)
    centered_targets = [target - target_mean for target in targets]
    feature_count = len(feature_names)
    gram = [[0.0] * feature_count for _ in range(feature_count)]
    rhs = [0.0] * feature_count
    for feature_row, target in zip(standardized, centered_targets):
        for first in range(feature_count):
            rhs[first] += feature_row[first] * target
            for second in range(feature_count):
                gram[first][second] += feature_row[first] * feature_row[second]
    for feature in range(feature_count):
        gram[feature][feature] += alpha
    coefficients = solve_linear_system(gram, rhs)
    return RidgeModel(
        feature_names=tuple(feature_names),
        feature_means=tuple(means),
        feature_scales=tuple(scales),
        standardized_coefficients=tuple(coefficients),
        intercept_standardized=target_mean,
        alpha=alpha,
    )


def clamp(
    value: float,
    lower: float = MIN_WATER_TEMP_C,
    upper: float = MAX_WATER_TEMP_C,
) -> float:
    return min(upper, max(lower, value))


def metrics(observed: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    residuals = [actual - estimate for actual, estimate in zip(observed, predicted)]
    mean_observed = statistics.fmean(observed)
    sum_squared_error = sum(residual**2 for residual in residuals)
    total_sum_squares = sum((actual - mean_observed) ** 2 for actual in observed)
    return {
        "rmse_c": math.sqrt(statistics.fmean(residual**2 for residual in residuals)),
        "mae_c": statistics.fmean(abs(residual) for residual in residuals),
        "bias_observed_minus_predicted_c": statistics.fmean(residuals),
        "r_squared": 1.0 - sum_squared_error / total_sum_squares,
    }


def leave_year_out_predictions(
    feature_names: Sequence[str],
    rows: Sequence[CalibrationRow],
    alpha: float,
) -> list[float]:
    predictions = [math.nan] * len(rows)
    years = sorted({row.sample_date.year for row in rows})
    for held_out_year in years:
        training = [row for row in rows if row.sample_date.year != held_out_year]
        model = fit_ridge(feature_names, training, alpha)
        for index, row in enumerate(rows):
            if row.sample_date.year == held_out_year:
                predictions[index] = clamp(model.predict_one(row.features))
    if any(math.isnan(value) for value in predictions):
        raise AssertionError("Leave-year-out validation did not predict every calibration row.")
    return predictions


def seasonal_baseline_predictions(rows: Sequence[CalibrationRow]) -> list[float]:
    predictions = [math.nan] * len(rows)
    years = sorted({row.sample_date.year for row in rows})
    for held_out_year in years:
        training = [row for row in rows if row.sample_date.year != held_out_year]
        overall_mean = statistics.fmean(row.target_c for row in training)
        month_means: dict[int, float] = {}
        for month in range(1, 13):
            values = [row.target_c for row in training if row.sample_date.month == month]
            month_means[month] = statistics.fmean(values) if values else overall_mean
        for index, row in enumerate(rows):
            if row.sample_date.year == held_out_year:
                predictions[index] = month_means[row.sample_date.month]
    return predictions


def longest_run_at_or_above(values: Sequence[float], threshold: float) -> int:
    longest = 0
    current = 0
    for value in values:
        if value >= threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarize_exposure_window(
    window_dates: Sequence[date],
    prediction_by_date: dict[date, float],
) -> dict[str, object]:
    # Use the same three-decimal values published in the daily CSV so threshold
    # counts and window summaries are exactly reproducible from that artifact.
    values = [round(prediction_by_date[item_date], 3) for item_date in window_dates]
    if len(values) < 7:
        raise ValueError("Exposure windows must contain at least seven days.")
    rolling = trailing_mean(values, 7)
    eligible_rolling = [
        (window_dates[index], rolling[index]) for index in range(6, len(values))
    ]
    max_rolling_date, max_rolling_value = max(
        eligible_rolling, key=lambda item: item[1]
    )
    max_daily_index = max(range(len(values)), key=values.__getitem__)
    return {
        "complete_days": len(values),
        "window_mean_proxy_c": statistics.fmean(values),
        "window_max_modeled_daily_proxy_c": values[max_daily_index],
        "window_max_modeled_daily_proxy_date": window_dates[
            max_daily_index
        ].isoformat(),
        "window_max_within_window_7day_mean_proxy_c": max_rolling_value,
        "window_max_within_window_7day_mean_date": max_rolling_date.isoformat(),
        "days_proxy_ge_17_5c": sum(value >= 17.5 for value in values),
        "days_proxy_ge_19c": sum(value >= 19.0 for value in values),
        "days_proxy_ge_21c": sum(value >= 21.0 for value in values),
        "longest_proxy_spell_ge_17_5c_days": longest_run_at_or_above(
            values, 17.5
        ),
    }


def quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a quantile of an empty sequence.")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = position - lower_index
    return ordered[lower_index] + fraction * (
        ordered[upper_index] - ordered[lower_index]
    )


def round_or_blank(value: float | None, digits: int = 3) -> str | float:
    return "" if value is None else round(value, digits)


def atomic_write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def atomic_write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def main() -> int:
    args = parse_args()
    if args.end_date < args.start_date:
        raise ValueError("--end-date must not precede --start-date.")
    feature_start = args.start_date - timedelta(days=29)
    all_dates = inclusive_dates(feature_start, args.end_date)
    output_dates = inclusive_dates(args.start_date, args.end_date)
    cache_dir = args.cache_dir or (
        PROJECT_ROOT
        / "data"
        / "bronze"
        / "temperature_proxy"
        / args.snapshot_date.isoformat()
    )
    output_dir = args.output_dir

    source_definitions = {
        "usgs_discharge": {
            "path": cache_dir
            / f"usgs_{USGS_SITE}_daily_discharge_{feature_start}_{args.end_date}.json",
            "url": usgs_url(feature_start, args.end_date),
            "validator": parse_usgs,
        },
        "noaa_air_temperature": {
            "path": cache_dir
            / f"noaa_{NOAA_STATION}_daily_air_temperature_{feature_start}_{args.end_date}.csv",
            "url": noaa_url(feature_start, args.end_date),
            "validator": parse_noaa,
        },
        "king_county_grab_temperature": {
            "path": cache_dir / "king_county_0631_temperature_grab_samples.csv",
            "url": king_county_url(),
            "validator": parse_king_county,
        },
    }

    loaded: dict[str, object] = {}
    manifest_sources: dict[str, dict[str, object]] = {}
    for source_name, definition in source_definitions.items():
        payload, parsed, acquisition_status = load_or_fetch(
            definition["path"],
            definition["url"],
            definition["validator"],
            args.offline,
        )
        loaded[source_name] = parsed
        manifest_sources[source_name] = {
            "acquisition_status": acquisition_status,
            "path": relative_path(definition["path"]),
            "sha256": sha256_bytes(payload),
            "url": definition["url"],
        }
        print(f"{source_name}: {acquisition_status} {definition['path']}")

    usgs = loaded["usgs_discharge"]
    noaa = loaded["noaa_air_temperature"]
    grab_rows = loaded["king_county_grab_temperature"]
    assert isinstance(usgs, dict)
    assert isinstance(noaa, dict)
    assert isinstance(grab_rows, list)

    flow_raw: list[float | None] = []
    flow_qualifiers: list[str] = []
    air_min_raw: list[float | None] = []
    air_max_raw: list[float | None] = []
    for item_date in all_dates:
        flow_item = usgs.get(item_date)
        flow_raw.append(flow_item[0] if flow_item else None)
        flow_qualifiers.append(flow_item[1] if flow_item else "")
        air_item = noaa.get(item_date)
        air_min_raw.append(air_item[0] if air_item else None)
        air_max_raw.append(air_item[1] if air_item else None)

    flow, flow_interpolated = interpolate_short_gaps(flow_raw, "USGS daily discharge")
    air_min, air_min_interpolated = interpolate_short_gaps(
        air_min_raw, "NOAA daily minimum air temperature"
    )
    air_max, air_max_interpolated = interpolate_short_gaps(
        air_max_raw, "NOAA daily maximum air temperature"
    )
    if any(value < 0 for value in flow):
        raise ValueError("USGS discharge contains a negative value.")
    if any(minimum > maximum for minimum, maximum in zip(air_min, air_max)):
        raise ValueError("NOAA daily minimum exceeds daily maximum on at least one date.")

    air_mid = [(minimum + maximum) / 2.0 for minimum, maximum in zip(air_min, air_max)]
    air_range = [maximum - minimum for minimum, maximum in zip(air_min, air_max)]
    log_flow = [math.log1p(value) for value in flow]
    air_mean_3d = trailing_mean(air_mid, 3)
    air_mean_7d = trailing_mean(air_mid, 7)
    air_mean_30d = trailing_mean(air_mid, 30)
    log_flow_mean_7d = trailing_mean(log_flow, 7)

    feature_names = (
        "air_mid_c",
        "air_mid_trailing_3d_c",
        "air_mid_trailing_7d_c",
        "air_mid_trailing_30d_c",
        "air_range_c",
        "log1p_flow_cfs",
        "log1p_flow_trailing_7d",
        "sin_day_of_year",
        "cos_day_of_year",
        "sin_2x_day_of_year",
        "cos_2x_day_of_year",
    )
    feature_by_date: dict[date, tuple[float, ...]] = {}
    predictor_metadata: dict[date, dict[str, object]] = {}
    for index, item_date in enumerate(all_dates):
        angle = 2.0 * math.pi * (item_date.timetuple().tm_yday - 1) / 365.2425
        feature_by_date[item_date] = (
            air_mid[index],
            air_mean_3d[index],
            air_mean_7d[index],
            air_mean_30d[index],
            air_range[index],
            log_flow[index],
            log_flow_mean_7d[index],
            math.sin(angle),
            math.cos(angle),
            math.sin(2.0 * angle),
            math.cos(2.0 * angle),
        )
        predictor_metadata[item_date] = {
            "flow_cfs": flow[index],
            "flow_qualifier": flow_qualifiers[index],
            "air_min_c": air_min[index],
            "air_max_c": air_max[index],
            "air_mid_c": air_mid[index],
            "air_predictor_interpolated": (
                air_min_interpolated[index] or air_max_interpolated[index]
            ),
            "flow_predictor_interpolated": flow_interpolated[index],
            "predictor_interpolated": (
                flow_interpolated[index]
                or air_min_interpolated[index]
                or air_max_interpolated[index]
            ),
        }

    grab_values: dict[date, list[float]] = defaultdict(list)
    grab_quality_ids: dict[date, set[str]] = defaultdict(set)
    for row in grab_rows:
        if row.get("locator") != KING_COUNTY_LOCATOR:
            continue
        if row.get("parameter", "").strip().lower() != "temperature":
            continue
        if "deg c" not in row.get("units", "").strip().lower():
            continue
        sample_date = date.fromisoformat(row["collect_datetime"][:10])
        if sample_date < args.start_date or sample_date > args.end_date:
            continue
        value = optional_float(row.get("value"))
        if value is None:
            continue
        if not MIN_WATER_TEMP_C <= value <= MAX_WATER_TEMP_C:
            raise ValueError(
                f"King County temperature {value} C is outside physical checks on {sample_date}."
            )
        grab_values[sample_date].append(value)
        grab_quality_ids[sample_date].add(row.get("qualityid", ""))

    calibration_rows = [
        CalibrationRow(
            sample_date=sample_date,
            target_c=statistics.fmean(values),
            sample_count=len(values),
            features=feature_by_date[sample_date],
        )
        for sample_date, values in sorted(grab_values.items())
    ]
    calibration_years = sorted({row.sample_date.year for row in calibration_rows})
    expected_years = list(range(args.start_date.year, args.end_date.year + 1))
    if calibration_years != expected_years:
        missing_years = sorted(set(expected_years) - set(calibration_years))
        raise ValueError(f"Calibration has no grab samples for years: {missing_years}")
    if len(calibration_rows) < 100:
        raise ValueError("Fewer than 100 unique-date calibration observations are available.")

    observed = [row.target_c for row in calibration_rows]
    alpha_results: dict[float, dict[str, float]] = {}
    alpha_predictions: dict[float, list[float]] = {}
    for alpha in RIDGE_ALPHAS:
        predictions = leave_year_out_predictions(feature_names, calibration_rows, alpha)
        alpha_predictions[alpha] = predictions
        alpha_results[alpha] = metrics(observed, predictions)
    selected_alpha = min(
        RIDGE_ALPHAS,
        key=lambda alpha: (alpha_results[alpha]["rmse_c"], -alpha),
    )
    cross_validated_predictions = alpha_predictions[selected_alpha]
    validation_metrics = alpha_results[selected_alpha]
    baseline_predictions = seasonal_baseline_predictions(calibration_rows)
    baseline_metrics = metrics(observed, baseline_predictions)
    final_model = fit_ridge(feature_names, calibration_rows, selected_alpha)

    cross_validated_residuals = [
        actual - predicted
        for actual, predicted in zip(observed, cross_validated_predictions)
    ]
    residual_lower = quantile(cross_validated_residuals, 0.025)
    residual_upper = quantile(cross_validated_residuals, 0.975)

    # Model T2 is deliberately independent of streamflow. It uses the same
    # response observations, air-temperature features, seasonal harmonics,
    # validation folds, and model-selection rule as T1, but removes both USGS
    # flow features from its design matrix.
    t2_feature_indices = (0, 1, 2, 3, 4, 7, 8, 9, 10)
    t2_feature_names = tuple(feature_names[index] for index in t2_feature_indices)
    t2_feature_by_date = {
        item_date: tuple(features[index] for index in t2_feature_indices)
        for item_date, features in feature_by_date.items()
    }
    t2_calibration_rows = [
        CalibrationRow(
            sample_date=row.sample_date,
            target_c=row.target_c,
            sample_count=row.sample_count,
            features=t2_feature_by_date[row.sample_date],
        )
        for row in calibration_rows
    ]
    t2_alpha_results: dict[float, dict[str, float]] = {}
    t2_alpha_predictions: dict[float, list[float]] = {}
    for alpha in RIDGE_ALPHAS:
        predictions = leave_year_out_predictions(
            t2_feature_names, t2_calibration_rows, alpha
        )
        t2_alpha_predictions[alpha] = predictions
        t2_alpha_results[alpha] = metrics(observed, predictions)
    t2_selected_alpha = min(
        RIDGE_ALPHAS,
        key=lambda alpha: (t2_alpha_results[alpha]["rmse_c"], -alpha),
    )
    t2_cross_validated_predictions = t2_alpha_predictions[t2_selected_alpha]
    t2_validation_metrics = t2_alpha_results[t2_selected_alpha]
    t2_final_model = fit_ridge(
        t2_feature_names, t2_calibration_rows, t2_selected_alpha
    )
    t2_cross_validated_residuals = [
        actual - predicted
        for actual, predicted in zip(observed, t2_cross_validated_predictions)
    ]
    t2_residual_lower = quantile(t2_cross_validated_residuals, 0.025)
    t2_residual_upper = quantile(t2_cross_validated_residuals, 0.975)

    # Range flags apply only to measured/derived air and flow predictors. The
    # harmonic terms intentionally span a fixed [-1, 1] seasonal cycle, so
    # comparing their exact extrema with sparse sample dates creates false
    # extrapolation flags around solstices.
    extrapolation_feature_names = feature_names[:7]
    feature_minima = [
        min(row.features[index] for row in calibration_rows)
        for index in range(len(extrapolation_feature_names))
    ]
    feature_maxima = [
        max(row.features[index] for row in calibration_rows)
        for index in range(len(extrapolation_feature_names))
    ]

    # Predict the 29-day feature warm-up period as well as the requested output
    # period. This makes the first requested 7-day window (1997-01-01 by
    # default) a genuine seven-consecutive-day model average rather than a
    # partial window.
    raw_prediction_by_date = {
        item_date: final_model.predict_one(feature_by_date[item_date])
        for item_date in all_dates
    }
    prediction_by_date = {
        item_date: clamp(raw_prediction)
        for item_date, raw_prediction in raw_prediction_by_date.items()
    }
    all_point_predictions = [prediction_by_date[item_date] for item_date in all_dates]
    all_rolling_7day = trailing_mean(all_point_predictions, 7)
    rolling_7day_by_date = {
        item_date: all_rolling_7day[index]
        for index, item_date in enumerate(all_dates)
        if index >= 6
    }

    t2_extrapolation_feature_names = t2_feature_names[:5]
    t2_feature_minima = [
        min(row.features[index] for row in t2_calibration_rows)
        for index in range(len(t2_extrapolation_feature_names))
    ]
    t2_feature_maxima = [
        max(row.features[index] for row in t2_calibration_rows)
        for index in range(len(t2_extrapolation_feature_names))
    ]
    t2_raw_prediction_by_date = {
        item_date: t2_final_model.predict_one(t2_feature_by_date[item_date])
        for item_date in all_dates
    }
    t2_prediction_by_date = {
        item_date: clamp(raw_prediction)
        for item_date, raw_prediction in t2_raw_prediction_by_date.items()
    }
    t2_all_point_predictions = [
        t2_prediction_by_date[item_date] for item_date in all_dates
    ]
    t2_all_rolling_7day = trailing_mean(t2_all_point_predictions, 7)
    t2_rolling_7day_by_date = {
        item_date: t2_all_rolling_7day[index]
        for index, item_date in enumerate(all_dates)
        if index >= 6
    }

    daily_records: list[dict[str, object]] = []
    point_predictions: list[float] = []
    point_was_clipped: list[bool] = []
    for item_date in output_dates:
        features = feature_by_date[item_date]
        raw_prediction = raw_prediction_by_date[item_date]
        point_prediction = prediction_by_date[item_date]
        clipped = not math.isclose(raw_prediction, point_prediction, abs_tol=1e-12)
        lower = clamp(point_prediction + residual_lower)
        upper = clamp(point_prediction + residual_upper)
        extrapolation_features = [
            name
            for name, value, minimum, maximum in zip(
                extrapolation_feature_names,
                features[: len(extrapolation_feature_names)],
                feature_minima,
                feature_maxima,
            )
            if value < minimum or value > maximum
        ]
        observed_values = grab_values.get(item_date, [])
        observed_value = statistics.fmean(observed_values) if observed_values else None
        metadata = predictor_metadata[item_date]
        point_predictions.append(point_prediction)
        point_was_clipped.append(clipped)
        daily_records.append(
            {
                "date": item_date.isoformat(),
                "usgs_flow_cfs": round(float(metadata["flow_cfs"]), 3),
                "usgs_flow_qualifier": metadata["flow_qualifier"],
                "noaa_air_tmin_c": round(float(metadata["air_min_c"]), 3),
                "noaa_air_tmax_c": round(float(metadata["air_max_c"]), 3),
                "noaa_air_mid_c": round(float(metadata["air_mid_c"]), 3),
                "modeled_daily_water_temp_proxy_c": round(point_prediction, 3),
                "modeled_lower_95_c": round(lower, 3),
                "modeled_upper_95_c": round(upper, 3),
                "observed_grab_temp_c": round_or_blank(observed_value),
                "observed_grab_count": len(observed_values),
                "observed_minus_modeled_c": round_or_blank(
                    observed_value - point_prediction if observed_value is not None else None
                ),
                "modeled_7day_mean_proxy_c": round(
                    rolling_7day_by_date[item_date], 3
                ),
                "predictor_interpolated": str(metadata["predictor_interpolated"]).lower(),
                "prediction_clipped_to_physical_range": str(clipped).lower(),
                "outside_calibration_predictor_range": str(bool(extrapolation_features)).lower(),
                "outside_range_features": ";".join(extrapolation_features),
                "value_status": "modeled_proxy_calibrated_to_grab_samples",
            }
        )

    annual_records: list[dict[str, object]] = []
    for year in expected_years:
        indices = [
            index for index, item_date in enumerate(output_dates) if item_date.year == year
        ]
        yearly_predictions = [point_predictions[index] for index in indices]
        eligible_rolling = [
            (output_dates[index], rolling_7day_by_date[output_dates[index]])
            for index in indices
        ]
        max_rolling_date, max_rolling_value = max(
            eligible_rolling, key=lambda item: item[1]
        )
        annual_records.append(
            {
                "year": year,
                "days": len(indices),
                "modeled_annual_mean_proxy_c": round(
                    statistics.fmean(yearly_predictions), 3
                ),
                "modeled_annual_max_daily_proxy_c": round(max(yearly_predictions), 3),
                "annual_max_modeled_7day_mean_proxy_c": round(max_rolling_value, 3),
                "annual_max_modeled_7day_mean_date": max_rolling_date.isoformat(),
                "grab_sample_dates": sum(
                    1 for row in calibration_rows if row.sample_date.year == year
                ),
                "metric_warning": (
                    "Modeled proxy; not observed daily maximum or regulatory 7DADMax"
                ),
            }
        )

    calibration_output: list[dict[str, object]] = []
    final_fitted_predictions = [
        clamp(final_model.predict_one(row.features)) for row in calibration_rows
    ]
    for row, cross_validated, fitted in zip(
        calibration_rows, cross_validated_predictions, final_fitted_predictions
    ):
        calibration_output.append(
            {
                "date": row.sample_date.isoformat(),
                "year": row.sample_date.year,
                "month": row.sample_date.month,
                "observed_grab_temp_c": round(row.target_c, 3),
                "grab_count": row.sample_count,
                "quality_ids": ";".join(sorted(grab_quality_ids[row.sample_date])),
                "leave_year_out_prediction_c": round(cross_validated, 3),
                "leave_year_out_residual_c": round(row.target_c - cross_validated, 3),
                "final_model_fitted_c": round(fitted, 3),
            }
        )

    t2_daily_records: list[dict[str, object]] = []
    t2_point_predictions: list[float] = []
    t2_point_was_clipped: list[bool] = []
    for item_date in output_dates:
        features = t2_feature_by_date[item_date]
        raw_prediction = t2_raw_prediction_by_date[item_date]
        point_prediction = t2_prediction_by_date[item_date]
        clipped = not math.isclose(raw_prediction, point_prediction, abs_tol=1e-12)
        lower = clamp(point_prediction + t2_residual_lower)
        upper = clamp(point_prediction + t2_residual_upper)
        extrapolation_features = [
            name
            for name, value, minimum, maximum in zip(
                t2_extrapolation_feature_names,
                features[: len(t2_extrapolation_feature_names)],
                t2_feature_minima,
                t2_feature_maxima,
            )
            if value < minimum or value > maximum
        ]
        observed_values = grab_values.get(item_date, [])
        observed_value = statistics.fmean(observed_values) if observed_values else None
        metadata = predictor_metadata[item_date]
        t2_point_predictions.append(point_prediction)
        t2_point_was_clipped.append(clipped)
        t2_daily_records.append(
            {
                "model_id": "T2",
                "date": item_date.isoformat(),
                "noaa_air_tmin_c": round(float(metadata["air_min_c"]), 3),
                "noaa_air_tmax_c": round(float(metadata["air_max_c"]), 3),
                "noaa_air_mid_c": round(float(metadata["air_mid_c"]), 3),
                "modeled_daily_water_temp_proxy_c": round(point_prediction, 3),
                "modeled_lower_95_c": round(lower, 3),
                "modeled_upper_95_c": round(upper, 3),
                "observed_grab_temp_c": round_or_blank(observed_value),
                "observed_grab_count": len(observed_values),
                "observed_minus_modeled_c": round_or_blank(
                    observed_value - point_prediction if observed_value is not None else None
                ),
                "modeled_7day_mean_proxy_c": round(
                    t2_rolling_7day_by_date[item_date], 3
                ),
                "predictor_interpolated": str(
                    metadata["air_predictor_interpolated"]
                ).lower(),
                "prediction_clipped_to_physical_range": str(clipped).lower(),
                "outside_calibration_predictor_range": str(
                    bool(extrapolation_features)
                ).lower(),
                "outside_range_features": ";".join(extrapolation_features),
                "value_status": (
                    "modeled_proxy_t2_air_seasonal_calibrated_to_grab_samples"
                ),
            }
        )

    t2_annual_records: list[dict[str, object]] = []
    for year in expected_years:
        indices = [
            index for index, item_date in enumerate(output_dates) if item_date.year == year
        ]
        yearly_predictions = [t2_point_predictions[index] for index in indices]
        eligible_rolling = [
            (output_dates[index], t2_rolling_7day_by_date[output_dates[index]])
            for index in indices
        ]
        max_rolling_date, max_rolling_value = max(
            eligible_rolling, key=lambda item: item[1]
        )
        t2_annual_records.append(
            {
                "model_id": "T2",
                "year": year,
                "days": len(indices),
                "modeled_annual_mean_proxy_c": round(
                    statistics.fmean(yearly_predictions), 3
                ),
                "modeled_annual_max_daily_proxy_c": round(max(yearly_predictions), 3),
                "annual_max_modeled_7day_mean_proxy_c": round(max_rolling_value, 3),
                "annual_max_modeled_7day_mean_date": max_rolling_date.isoformat(),
                "grab_sample_dates": sum(
                    1 for row in t2_calibration_rows if row.sample_date.year == year
                ),
                "metric_warning": (
                    "Modeled proxy; not observed daily maximum or regulatory 7DADMax"
                ),
            }
        )

    t2_calibration_output: list[dict[str, object]] = []
    t2_final_fitted_predictions = [
        clamp(t2_final_model.predict_one(row.features))
        for row in t2_calibration_rows
    ]
    for row, cross_validated, fitted in zip(
        t2_calibration_rows,
        t2_cross_validated_predictions,
        t2_final_fitted_predictions,
    ):
        t2_calibration_output.append(
            {
                "model_id": "T2",
                "date": row.sample_date.isoformat(),
                "year": row.sample_date.year,
                "month": row.sample_date.month,
                "observed_grab_temp_c": round(row.target_c, 3),
                "grab_count": row.sample_count,
                "quality_ids": ";".join(sorted(grab_quality_ids[row.sample_date])),
                "leave_year_out_prediction_c": round(cross_validated, 3),
                "leave_year_out_residual_c": round(row.target_c - cross_validated, 3),
                "final_model_fitted_c": round(fitted, 3),
            }
        )

    # Validate the already-held-out predictions within the three pre-specified
    # hypothesis windows. No model is refit on a window, and no salmon response
    # data are read or tested here.
    window_validation_records: list[dict[str, object]] = []
    window_validation_summary: dict[str, dict[str, object]] = {}
    for window in HYPOTHESIS_WINDOWS:
        indices = [
            index
            for index, row in enumerate(calibration_rows)
            if window.contains(row.sample_date)
        ]
        if len(indices) < 2:
            raise ValueError(
                f"Hypothesis window {window.window_id} has fewer than two calibration dates."
            )
        window_observed = [observed[index] for index in indices]
        window_t1_predictions = [
            cross_validated_predictions[index] for index in indices
        ]
        window_t2_predictions = [
            t2_cross_validated_predictions[index] for index in indices
        ]
        window_baseline_predictions = [baseline_predictions[index] for index in indices]
        t1_window_metrics = metrics(window_observed, window_t1_predictions)
        t2_window_metrics = metrics(window_observed, window_t2_predictions)
        baseline_window_metrics = metrics(window_observed, window_baseline_predictions)
        represented_years = sorted(
            {calibration_rows[index].sample_date.year for index in indices}
        )
        common = {
            "window_id": window.window_id,
            "analysis_id": window.analysis_id,
            "species": window.species,
            "life_stage": window.life_stage,
            "window_start": f"{window.start_month:02d}-{window.start_day:02d}",
            "window_end": f"{window.end_month:02d}-{window.end_day:02d}",
            "calibration_unique_dates": len(indices),
            "calibration_raw_samples": sum(
                calibration_rows[index].sample_count for index in indices
            ),
            "calibration_years_represented": len(represented_years),
            "first_calibration_year": represented_years[0],
            "last_calibration_year": represented_years[-1],
            "baseline_rmse_c": round(baseline_window_metrics["rmse_c"], 6),
            "baseline_mae_c": round(baseline_window_metrics["mae_c"], 6),
            "baseline_r_squared": round(
                baseline_window_metrics["r_squared"], 6
            ),
        }
        for model_id, uses_flow, model_metrics in (
            ("T1", "true", t1_window_metrics),
            ("T2", "false", t2_window_metrics),
        ):
            window_validation_records.append(
                {
                    **common,
                    "model_id": model_id,
                    "uses_usgs_flow": uses_flow,
                    "leave_year_out_rmse_c": round(model_metrics["rmse_c"], 6),
                    "leave_year_out_mae_c": round(model_metrics["mae_c"], 6),
                    "leave_year_out_bias_c": round(
                        model_metrics["bias_observed_minus_predicted_c"], 6
                    ),
                    "leave_year_out_r_squared": round(
                        model_metrics["r_squared"], 6
                    ),
                    "rmse_improvement_over_window_climatology_pct": round(
                        100.0
                        * (
                            baseline_window_metrics["rmse_c"]
                            - model_metrics["rmse_c"]
                        )
                        / baseline_window_metrics["rmse_c"],
                        3,
                    ),
                    "t2_minus_t1_rmse_c": round(
                        t2_window_metrics["rmse_c"]
                        - t1_window_metrics["rmse_c"],
                        6,
                    ),
                    "validation_status": (
                        "window_subset_of_leave_year_out_predictions"
                    ),
                }
            )
        window_validation_summary[window.window_id] = {
            "analysis_id": window.analysis_id,
            "calibration_unique_dates": len(indices),
            "calibration_years_represented": len(represented_years),
            "t1": t1_window_metrics,
            "t2": t2_window_metrics,
            "monthly_climatology": baseline_window_metrics,
            "t2_minus_t1_rmse_c": (
                t2_window_metrics["rmse_c"] - t1_window_metrics["rmse_c"]
            ),
        }

    # Audit every T1 day outside the calibration predictor range. The audit is
    # day-level (295 rows for the accepted 1997-2025 snapshot), with explicit
    # emphasis on June-October and the hypothesis-window memberships.
    t1_daily_by_date = {
        date.fromisoformat(str(record["date"])): record for record in daily_records
    }
    t2_daily_by_date = {
        date.fromisoformat(str(record["date"])): record
        for record in t2_daily_records
    }
    calibration_ranges = {
        name: (minimum, maximum)
        for name, minimum, maximum in zip(
            extrapolation_feature_names, feature_minima, feature_maxima
        )
    }
    extrapolation_audit_records: list[dict[str, object]] = []
    extrapolation_feature_counts: Counter[str] = Counter()
    extrapolation_month_counts: Counter[str] = Counter()
    extrapolation_year_counts: Counter[str] = Counter()
    extrapolation_window_counts: Counter[str] = Counter()
    extrapolation_severity_counts: Counter[str] = Counter()
    for item_date in output_dates:
        daily_record = t1_daily_by_date[item_date]
        if daily_record["outside_calibration_predictor_range"] != "true":
            continue
        features = feature_by_date[item_date]
        feature_values = {
            name: value
            for name, value in zip(extrapolation_feature_names, features)
        }
        outside_features = [
            name
            for name in extrapolation_feature_names
            if feature_values[name] < calibration_ranges[name][0]
            or feature_values[name] > calibration_ranges[name][1]
        ]
        detail_parts: list[str] = []
        normalized_distances: list[float] = []
        for name in outside_features:
            value = feature_values[name]
            minimum, maximum = calibration_ranges[name]
            distance = minimum - value if value < minimum else value - maximum
            span = maximum - minimum
            normalized_distance = distance / span if span > 0 else math.inf
            normalized_distances.append(normalized_distance)
            detail_parts.append(
                f"{name}={value:.6f}|range={minimum:.6f}..{maximum:.6f}"
                f"|distance_fraction={normalized_distance:.6f}"
            )
            extrapolation_feature_counts[name] += 1
        max_normalized_distance = max(normalized_distances)
        if max_normalized_distance <= 0.05:
            severity = "within_5pct_beyond_calibration_range"
        elif max_normalized_distance <= 0.20:
            severity = "5_to_20pct_beyond_calibration_range"
        else:
            severity = "over_20pct_beyond_calibration_range"
        window_ids = [
            window.window_id for window in HYPOTHESIS_WINDOWS if window.contains(item_date)
        ]
        for window_id in window_ids:
            extrapolation_window_counts[window_id] += 1
        month_key = f"{item_date.month:02d}-{item_date.strftime('%b')}"
        extrapolation_month_counts[month_key] += 1
        extrapolation_year_counts[str(item_date.year)] += 1
        extrapolation_severity_counts[severity] += 1
        extrapolation_audit_records.append(
            {
                "date": item_date.isoformat(),
                "year": item_date.year,
                "month": item_date.month,
                "month_name": item_date.strftime("%b"),
                "june_through_october": str(6 <= item_date.month <= 10).lower(),
                "hypothesis_windows": ";".join(window_ids),
                "outside_feature_count": len(outside_features),
                "outside_range_features": ";".join(outside_features),
                "outside_feature_details": ";".join(detail_parts),
                "max_distance_fraction_of_calibration_span": round(
                    max_normalized_distance, 6
                ),
                "screening_severity": severity,
                "usgs_flow_cfs": daily_record["usgs_flow_cfs"],
                "noaa_air_mid_c": daily_record["noaa_air_mid_c"],
                "t1_modeled_daily_water_temp_proxy_c": daily_record[
                    "modeled_daily_water_temp_proxy_c"
                ],
                "t2_modeled_daily_water_temp_proxy_c": t2_daily_by_date[item_date][
                    "modeled_daily_water_temp_proxy_c"
                ],
                "t2_minus_t1_c": round(
                    float(
                        t2_daily_by_date[item_date][
                            "modeled_daily_water_temp_proxy_c"
                        ]
                    )
                    - float(daily_record["modeled_daily_water_temp_proxy_c"]),
                    3,
                ),
                "observed_grab_temp_c": daily_record["observed_grab_temp_c"],
                "audit_status": "flagged_for_predictor_range_extrapolation",
            }
        )

    june_october_extrapolation_days = sum(
        record["june_through_october"] == "true"
        for record in extrapolation_audit_records
    )
    june_october_records = [
        record
        for record in extrapolation_audit_records
        if record["june_through_october"] == "true"
    ]
    june_october_calendar_days = sum(
        6 <= item_date.month <= 10 for item_date in output_dates
    )
    june_october_feature_counts = Counter(
        feature_name
        for record in june_october_records
        for feature_name in str(record["outside_range_features"]).split(";")
        if feature_name
    )
    june_october_severity_counts = Counter(
        str(record["screening_severity"]) for record in june_october_records
    )
    june_october_year_counts = Counter(
        str(record["year"]) for record in june_october_records
    )
    maximum_distance_record = max(
        extrapolation_audit_records,
        key=lambda record: float(
            record["max_distance_fraction_of_calibration_span"]
        ),
    )
    extrapolation_audit_summary = {
        "model_id": "T1",
        "total_extrapolation_days": len(extrapolation_audit_records),
        "total_output_days": len(output_dates),
        "total_extrapolation_pct": 100.0
        * len(extrapolation_audit_records)
        / len(output_dates),
        "observed_grab_overlap_days": sum(
            record["observed_grab_temp_c"] != ""
            for record in extrapolation_audit_records
        ),
        "june_through_october": {
            "extrapolation_days": june_october_extrapolation_days,
            "calendar_days": june_october_calendar_days,
            "extrapolation_pct": 100.0
            * june_october_extrapolation_days
            / june_october_calendar_days,
            "by_feature": dict(sorted(june_october_feature_counts.items())),
            "by_year": dict(sorted(june_october_year_counts.items())),
            "screening_severity": dict(
                sorted(june_october_severity_counts.items())
            ),
        },
        "by_feature": dict(sorted(extrapolation_feature_counts.items())),
        "by_month": dict(sorted(extrapolation_month_counts.items())),
        "by_year": dict(sorted(extrapolation_year_counts.items())),
        "by_hypothesis_window": {
            window.window_id: {
                "extrapolation_days": extrapolation_window_counts[window.window_id],
                "calendar_days": sum(window.contains(item_date) for item_date in output_dates),
                "extrapolation_pct": 100.0
                * extrapolation_window_counts[window.window_id]
                / sum(window.contains(item_date) for item_date in output_dates),
            }
            for window in HYPOTHESIS_WINDOWS
        },
        "screening_severity": dict(sorted(extrapolation_severity_counts.items())),
        "maximum_distance_day": {
            "date": maximum_distance_record["date"],
            "outside_range_features": maximum_distance_record[
                "outside_range_features"
            ],
            "max_distance_fraction_of_calibration_span": maximum_distance_record[
                "max_distance_fraction_of_calibration_span"
            ],
            "screening_severity": maximum_distance_record[
                "screening_severity"
            ],
            "t1_modeled_daily_water_temp_proxy_c": maximum_distance_record[
                "t1_modeled_daily_water_temp_proxy_c"
            ],
            "t2_modeled_daily_water_temp_proxy_c": maximum_distance_record[
                "t2_modeled_daily_water_temp_proxy_c"
            ],
        },
        "severity_definition": (
            "maximum distance beyond a calibration min/max divided by that "
            "feature's calibration span; screening categories are descriptive only"
        ),
    }

    # Construct the pre-association, life-stage-specific exposure table. Each
    # year-window row contains matched T1/T2 proxy metrics and explicit cohort
    # or same-year alignment. Seven-day metrics are recalculated strictly from
    # days inside each biological window.
    life_stage_exposure_records: list[dict[str, object]] = []
    for exposure_year in expected_years:
        for window in HYPOTHESIS_WINDOWS:
            window_dates = inclusive_dates(
                window.start_date(exposure_year), window.end_date(exposure_year)
            )
            t1_exposure = summarize_exposure_window(
                window_dates, prediction_by_date
            )
            t2_exposure = summarize_exposure_window(
                window_dates, t2_prediction_by_date
            )
            expected_days = len(window_dates)
            t1_extrapolation_days = sum(
                t1_daily_by_date[item_date][
                    "outside_calibration_predictor_range"
                ]
                == "true"
                for item_date in window_dates
            )
            t2_extrapolation_days = sum(
                t2_daily_by_date[item_date][
                    "outside_calibration_predictor_range"
                ]
                == "true"
                for item_date in window_dates
            )
            observed_dates = [
                item_date for item_date in window_dates if item_date in grab_values
            ]
            primary_return_year = exposure_year + window.return_year_offset
            life_stage_exposure_records.append(
                {
                    "exposure_year": exposure_year,
                    "analysis_id": window.analysis_id,
                    "window_id": window.window_id,
                    "species": window.species,
                    "life_stage": window.life_stage,
                    "window_start_date": window_dates[0].isoformat(),
                    "window_end_date": window_dates[-1].isoformat(),
                    "primary_return_year": primary_return_year,
                    "return_year_in_1997_2025": str(
                        args.start_date.year
                        <= primary_return_year
                        <= args.end_date.year
                    ).lower(),
                    "alignment_definition": window.alignment_definition,
                    "expected_days": expected_days,
                    "observed_grab_sample_dates": len(observed_dates),
                    "observed_grab_samples": sum(
                        len(grab_values[item_date]) for item_date in observed_dates
                    ),
                    "t1_complete_days": t1_exposure["complete_days"],
                    "t1_window_mean_proxy_c": round(
                        float(t1_exposure["window_mean_proxy_c"]), 3
                    ),
                    "t1_window_max_modeled_daily_proxy_c": round(
                        float(t1_exposure["window_max_modeled_daily_proxy_c"]), 3
                    ),
                    "t1_window_max_modeled_daily_proxy_date": t1_exposure[
                        "window_max_modeled_daily_proxy_date"
                    ],
                    "t1_window_max_within_window_7day_mean_proxy_c": round(
                        float(
                            t1_exposure[
                                "window_max_within_window_7day_mean_proxy_c"
                            ]
                        ),
                        3,
                    ),
                    "t1_window_max_within_window_7day_mean_date": t1_exposure[
                        "window_max_within_window_7day_mean_date"
                    ],
                    "t1_days_proxy_ge_17_5c": t1_exposure[
                        "days_proxy_ge_17_5c"
                    ],
                    "t1_days_proxy_ge_19c": t1_exposure["days_proxy_ge_19c"],
                    "t1_days_proxy_ge_21c": t1_exposure["days_proxy_ge_21c"],
                    "t1_longest_proxy_spell_ge_17_5c_days": t1_exposure[
                        "longest_proxy_spell_ge_17_5c_days"
                    ],
                    "t1_extrapolation_days": t1_extrapolation_days,
                    "t1_extrapolation_pct": round(
                        100.0 * t1_extrapolation_days / expected_days, 3
                    ),
                    "t2_complete_days": t2_exposure["complete_days"],
                    "t2_window_mean_proxy_c": round(
                        float(t2_exposure["window_mean_proxy_c"]), 3
                    ),
                    "t2_window_max_modeled_daily_proxy_c": round(
                        float(t2_exposure["window_max_modeled_daily_proxy_c"]), 3
                    ),
                    "t2_window_max_modeled_daily_proxy_date": t2_exposure[
                        "window_max_modeled_daily_proxy_date"
                    ],
                    "t2_window_max_within_window_7day_mean_proxy_c": round(
                        float(
                            t2_exposure[
                                "window_max_within_window_7day_mean_proxy_c"
                            ]
                        ),
                        3,
                    ),
                    "t2_window_max_within_window_7day_mean_date": t2_exposure[
                        "window_max_within_window_7day_mean_date"
                    ],
                    "t2_days_proxy_ge_17_5c": t2_exposure[
                        "days_proxy_ge_17_5c"
                    ],
                    "t2_days_proxy_ge_19c": t2_exposure["days_proxy_ge_19c"],
                    "t2_days_proxy_ge_21c": t2_exposure["days_proxy_ge_21c"],
                    "t2_longest_proxy_spell_ge_17_5c_days": t2_exposure[
                        "longest_proxy_spell_ge_17_5c_days"
                    ],
                    "t2_extrapolation_days": t2_extrapolation_days,
                    "t2_extrapolation_pct": round(
                        100.0 * t2_extrapolation_days / expected_days, 3
                    ),
                    "t2_minus_t1_window_mean_c": round(
                        float(t2_exposure["window_mean_proxy_c"])
                        - float(t1_exposure["window_mean_proxy_c"]),
                        3,
                    ),
                    "value_status": (
                        "modeled_proxy_exposure_ready_for_exploratory_sensitivity_only"
                    ),
                    "metric_warning": (
                        "Modeled grab-temperature proxies; daily maxima, threshold "
                        "counts, and seven-day means are not observed/regulatory metrics"
                    ),
                }
            )

    expected_exposure_rows = len(expected_years) * len(HYPOTHESIS_WINDOWS)
    exposure_rows_by_window = Counter(
        str(record["window_id"]) for record in life_stage_exposure_records
    )
    exposure_table_complete = (
        len(life_stage_exposure_records) == expected_exposure_rows
        and all(
            exposure_rows_by_window[window.window_id] == len(expected_years)
            for window in HYPOTHESIS_WINDOWS
        )
        and all(
            record["t1_complete_days"] == record["expected_days"]
            and record["t2_complete_days"] == record["expected_days"]
            for record in life_stage_exposure_records
        )
    )
    preassociation_validation = {
        "gate_status": (
            "PASS_FOR_EXPLORATORY_PROXY_INPUT_CONSTRUCTION"
            if exposure_table_complete
            else "FAIL"
        ),
        "salmon_association_tests_run": False,
        "exposure_table": {
            "rows": len(life_stage_exposure_records),
            "expected_rows": expected_exposure_rows,
            "years": [expected_years[0], expected_years[-1]],
            "rows_by_window": dict(sorted(exposure_rows_by_window.items())),
            "complete": exposure_table_complete,
        },
        "hypothesis_window_validation": window_validation_summary,
        "t1_extrapolation_audit": extrapolation_audit_summary,
        "interpretation": (
            "Passing this gate validates construction and provenance only. "
            "It does not convert modeled proxies into observed temperatures, "
            "validate regulatory 7DADMax, or authorize causal claims."
        ),
    }

    daily_path = output_dir / (
        f"issaquah_creek_daily_temperature_proxy_{args.start_date.year}_{args.end_date.year}.csv"
    )
    annual_path = output_dir / (
        f"issaquah_creek_annual_temperature_proxy_{args.start_date.year}_{args.end_date.year}.csv"
    )
    calibration_path = output_dir / "issaquah_temperature_proxy_calibration.csv"
    diagnostics_path = output_dir / "issaquah_temperature_proxy_diagnostics.json"
    t2_daily_path = output_dir / (
        "issaquah_creek_daily_temperature_proxy_t2_air_seasonal_"
        f"{args.start_date.year}_{args.end_date.year}.csv"
    )
    t2_annual_path = output_dir / (
        "issaquah_creek_annual_temperature_proxy_t2_air_seasonal_"
        f"{args.start_date.year}_{args.end_date.year}.csv"
    )
    t2_calibration_path = output_dir / (
        "issaquah_temperature_proxy_t2_air_seasonal_calibration.csv"
    )
    t2_diagnostics_path = output_dir / (
        "issaquah_temperature_proxy_t2_air_seasonal_diagnostics.json"
    )
    comparison_path = output_dir / "issaquah_temperature_proxy_model_comparison.csv"
    window_validation_path = output_dir / (
        "issaquah_temperature_proxy_hypothesis_window_validation.csv"
    )
    extrapolation_audit_path = output_dir / (
        "issaquah_temperature_proxy_t1_extrapolation_audit.csv"
    )
    extrapolation_summary_path = output_dir / (
        "issaquah_temperature_proxy_t1_extrapolation_summary.json"
    )
    life_stage_exposure_path = output_dir / (
        "issaquah_life_stage_temperature_exposure_"
        f"{args.start_date.year}_{args.end_date.year}.csv"
    )
    preassociation_validation_path = output_dir / (
        "issaquah_temperature_proxy_preassociation_validation.json"
    )
    manifest_path = cache_dir / "source_manifest.json"

    atomic_write_csv(daily_path, list(daily_records[0]), daily_records)
    atomic_write_csv(annual_path, list(annual_records[0]), annual_records)
    atomic_write_csv(calibration_path, list(calibration_output[0]), calibration_output)
    atomic_write_csv(t2_daily_path, list(t2_daily_records[0]), t2_daily_records)
    atomic_write_csv(t2_annual_path, list(t2_annual_records[0]), t2_annual_records)
    atomic_write_csv(
        t2_calibration_path,
        list(t2_calibration_output[0]),
        t2_calibration_output,
    )
    comparison_records = [
        {
            "model_id": "T1",
            "predictors": "air temperature + streamflow + seasonal terms",
            "uses_usgs_flow": "true",
            "selected_alpha": selected_alpha,
            "leave_year_out_rmse_c": round(validation_metrics["rmse_c"], 6),
            "leave_year_out_mae_c": round(validation_metrics["mae_c"], 6),
            "leave_year_out_bias_c": round(
                validation_metrics["bias_observed_minus_predicted_c"], 6
            ),
            "leave_year_out_r_squared": round(validation_metrics["r_squared"], 6),
            "rmse_improvement_over_climatology_pct": round(
                100.0
                * (baseline_metrics["rmse_c"] - validation_metrics["rmse_c"])
                / baseline_metrics["rmse_c"],
                3,
            ),
        },
        {
            "model_id": "T2",
            "predictors": "air temperature + seasonal terms",
            "uses_usgs_flow": "false",
            "selected_alpha": t2_selected_alpha,
            "leave_year_out_rmse_c": round(t2_validation_metrics["rmse_c"], 6),
            "leave_year_out_mae_c": round(t2_validation_metrics["mae_c"], 6),
            "leave_year_out_bias_c": round(
                t2_validation_metrics["bias_observed_minus_predicted_c"], 6
            ),
            "leave_year_out_r_squared": round(
                t2_validation_metrics["r_squared"], 6
            ),
            "rmse_improvement_over_climatology_pct": round(
                100.0
                * (baseline_metrics["rmse_c"] - t2_validation_metrics["rmse_c"])
                / baseline_metrics["rmse_c"],
                3,
            ),
        },
    ]
    atomic_write_csv(comparison_path, list(comparison_records[0]), comparison_records)
    atomic_write_csv(
        window_validation_path,
        list(window_validation_records[0]),
        window_validation_records,
    )
    atomic_write_csv(
        extrapolation_audit_path,
        list(extrapolation_audit_records[0]),
        extrapolation_audit_records,
    )
    atomic_write_json(extrapolation_summary_path, extrapolation_audit_summary)
    atomic_write_csv(
        life_stage_exposure_path,
        list(life_stage_exposure_records[0]),
        life_stage_exposure_records,
    )
    atomic_write_json(preassociation_validation_path, preassociation_validation)

    diagnostics = {
        "model": {
            "model_id": "T1",
            "type": (
                "ridge_linear_regression_with_engineered_air_flow_and_seasonal_features"
            ),
            "selected_alpha": selected_alpha,
            "candidate_alpha_leave_year_out_metrics": {
                str(alpha): values for alpha, values in alpha_results.items()
            },
            "feature_names": list(feature_names),
            "raw_scale_coefficients": final_model.raw_coefficients(),
            "physical_prediction_bounds_c": [MIN_WATER_TEMP_C, MAX_WATER_TEMP_C],
        },
        "calibration": {
            "target": "King County station 0631 grab-sample water temperature",
            "site": KING_COUNTY_SITE_NAME,
            "unique_sample_dates": len(calibration_rows),
            "raw_samples_in_period": sum(row.sample_count for row in calibration_rows),
            "date_range": [
                calibration_rows[0].sample_date.isoformat(),
                calibration_rows[-1].sample_date.isoformat(),
            ],
            "years": [calibration_years[0], calibration_years[-1]],
            "leave_year_out_metrics": validation_metrics,
            "leave_year_out_month_climatology_baseline_metrics": baseline_metrics,
            "rmse_improvement_over_baseline_pct": 100.0
            * (baseline_metrics["rmse_c"] - validation_metrics["rmse_c"])
            / baseline_metrics["rmse_c"],
            "empirical_95_percent_residual_offsets_c": [
                residual_lower,
                residual_upper,
            ],
        },
        "coverage": {
            "output_start": args.start_date.isoformat(),
            "output_end": args.end_date.isoformat(),
            "daily_rows": len(daily_records),
            "expected_daily_rows": (args.end_date - args.start_date).days + 1,
            "predictor_interpolated_days": sum(
                record["predictor_interpolated"] == "true" for record in daily_records
            ),
            "prediction_clipped_days": sum(point_was_clipped),
            "outside_calibration_predictor_range_days": sum(
                record["outside_calibration_predictor_range"] == "true"
                for record in daily_records
            ),
        },
        "sources": {
            "usgs": f"USGS {USGS_SITE} daily mean discharge",
            "noaa": f"GHCN-Daily {NOAA_STATION}, {NOAA_STATION_NAME}",
            "king_county": (
                f"Station {KING_COUNTY_LOCATOR}, {KING_COUNTY_SITE_NAME}"
            ),
        },
        "limitations": [
            "The daily values are modeled estimates, not continuous in-stream observations.",
            "The calibration target consists of sparse grab samples and does not identify daily maxima.",
            "modeled_7day_mean_proxy_c is not regulatory 7DADMax and must not be labeled as observed 7DADMax.",
            "The empirical interval uses leave-year-out residuals and does not include all structural or source-data uncertainty.",
            "Sea-Tac air temperature is a regional proxy and may not capture all microclimate conditions in the Issaquah Creek watershed.",
        ],
        "outputs": {
            "daily": relative_path(daily_path),
            "annual": relative_path(annual_path),
            "calibration": relative_path(calibration_path),
            "model_comparison": relative_path(comparison_path),
            "hypothesis_window_validation": relative_path(
                window_validation_path
            ),
            "extrapolation_audit": relative_path(extrapolation_audit_path),
            "extrapolation_summary": relative_path(
                extrapolation_summary_path
            ),
            "life_stage_exposure_table": relative_path(
                life_stage_exposure_path
            ),
            "preassociation_validation": relative_path(
                preassociation_validation_path
            ),
        },
    }
    atomic_write_json(diagnostics_path, diagnostics)
    t2_diagnostics = {
        "model": {
            "model_id": "T2",
            "type": (
                "ridge_linear_regression_with_engineered_air_and_seasonal_features"
            ),
            "uses_usgs_flow": False,
            "selected_alpha": t2_selected_alpha,
            "candidate_alpha_leave_year_out_metrics": {
                str(alpha): values for alpha, values in t2_alpha_results.items()
            },
            "feature_names": list(t2_feature_names),
            "raw_scale_coefficients": t2_final_model.raw_coefficients(),
            "physical_prediction_bounds_c": [MIN_WATER_TEMP_C, MAX_WATER_TEMP_C],
        },
        "calibration": {
            "target": "King County station 0631 grab-sample water temperature",
            "site": KING_COUNTY_SITE_NAME,
            "unique_sample_dates": len(t2_calibration_rows),
            "raw_samples_in_period": sum(
                row.sample_count for row in t2_calibration_rows
            ),
            "date_range": [
                t2_calibration_rows[0].sample_date.isoformat(),
                t2_calibration_rows[-1].sample_date.isoformat(),
            ],
            "years": [calibration_years[0], calibration_years[-1]],
            "leave_year_out_metrics": t2_validation_metrics,
            "leave_year_out_month_climatology_baseline_metrics": baseline_metrics,
            "rmse_improvement_over_baseline_pct": 100.0
            * (baseline_metrics["rmse_c"] - t2_validation_metrics["rmse_c"])
            / baseline_metrics["rmse_c"],
            "rmse_change_from_t1_pct": 100.0
            * (t2_validation_metrics["rmse_c"] - validation_metrics["rmse_c"])
            / validation_metrics["rmse_c"],
            "empirical_95_percent_residual_offsets_c": [
                t2_residual_lower,
                t2_residual_upper,
            ],
        },
        "coverage": {
            "output_start": args.start_date.isoformat(),
            "output_end": args.end_date.isoformat(),
            "daily_rows": len(t2_daily_records),
            "expected_daily_rows": (args.end_date - args.start_date).days + 1,
            "air_predictor_interpolated_days": sum(
                record["predictor_interpolated"] == "true"
                for record in t2_daily_records
            ),
            "prediction_clipped_days": sum(t2_point_was_clipped),
            "outside_calibration_predictor_range_days": sum(
                record["outside_calibration_predictor_range"] == "true"
                for record in t2_daily_records
            ),
        },
        "sources": {
            "noaa": f"GHCN-Daily {NOAA_STATION}, {NOAA_STATION_NAME}",
            "king_county": (
                f"Station {KING_COUNTY_LOCATOR}, {KING_COUNTY_SITE_NAME}"
            ),
        },
        "limitations": [
            "The daily values are modeled estimates, not continuous in-stream observations.",
            "T2 intentionally excludes streamflow and cannot represent flow-specific thermal effects.",
            "The calibration target consists of sparse grab samples and does not identify daily maxima.",
            "modeled_7day_mean_proxy_c is not regulatory 7DADMax and must not be labeled as observed 7DADMax.",
            "The empirical interval uses leave-year-out residuals and does not include all structural or source-data uncertainty.",
            "Sea-Tac air temperature is a regional proxy and may not capture all microclimate conditions in the Issaquah Creek watershed.",
        ],
        "outputs": {
            "daily": relative_path(t2_daily_path),
            "annual": relative_path(t2_annual_path),
            "calibration": relative_path(t2_calibration_path),
            "model_comparison": relative_path(comparison_path),
            "hypothesis_window_validation": relative_path(
                window_validation_path
            ),
            "life_stage_exposure_table": relative_path(
                life_stage_exposure_path
            ),
            "preassociation_validation": relative_path(
                preassociation_validation_path
            ),
        },
    }
    atomic_write_json(t2_diagnostics_path, t2_diagnostics)
    manifest = {
        "access_date": args.snapshot_date.isoformat(),
        "created_at": datetime.now().astimezone().isoformat(),
        "sources": manifest_sources,
    }
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_sources = existing_manifest.get("sources", {})
        for source_name, source_details in manifest_sources.items():
            existing_details = existing_sources.get(source_name, {})
            if existing_details.get("sha256") != source_details["sha256"]:
                raise ValueError(
                    f"Cached source hash no longer matches immutable manifest: {source_name}"
                )
            if existing_details.get("url") != source_details["url"]:
                raise ValueError(
                    f"Cached source URL no longer matches immutable manifest: {source_name}"
                )
    else:
        atomic_write_json(manifest_path, manifest)

    if len(daily_records) != (args.end_date - args.start_date).days + 1:
        raise AssertionError("T1 daily output row count is incomplete.")
    if len(t2_daily_records) != (args.end_date - args.start_date).days + 1:
        raise AssertionError("T2 daily output row count is incomplete.")
    if any("flow" in feature_name.lower() for feature_name in t2_feature_names):
        raise AssertionError("T2 feature matrix unexpectedly contains a flow variable.")
    flagged_t1_days = sum(
        record["outside_calibration_predictor_range"] == "true"
        for record in daily_records
    )
    if len(extrapolation_audit_records) != flagged_t1_days:
        raise AssertionError("T1 extrapolation audit does not cover every flagged day.")
    if (
        args.start_date == DEFAULT_START
        and args.end_date == DEFAULT_END
        and len(extrapolation_audit_records) != 295
    ):
        raise AssertionError(
            "Accepted 1997-2025 T1 snapshot no longer has the expected 295 extrapolation days."
        )
    if len(window_validation_records) != 2 * len(HYPOTHESIS_WINDOWS):
        raise AssertionError("Hypothesis-window validation output is incomplete.")
    if not exposure_table_complete:
        raise AssertionError("Life-stage-specific exposure table failed completeness checks.")
    if preassociation_validation["salmon_association_tests_run"] is not False:
        raise AssertionError("Temperature preparation must not run salmon association tests.")
    if validation_metrics["rmse_c"] >= baseline_metrics["rmse_c"]:
        raise RuntimeError(
            "T1 did not improve on the held-out seasonal baseline; output is not accepted."
        )
    if t2_validation_metrics["rmse_c"] >= baseline_metrics["rmse_c"]:
        raise RuntimeError(
            "T2 did not improve on the held-out seasonal baseline; output is not accepted."
        )

    print(
        "T1 calibration: "
        f"{len(calibration_rows)} unique dates, alpha={selected_alpha:g}, "
        f"leave-year-out RMSE={validation_metrics['rmse_c']:.3f} C, "
        f"MAE={validation_metrics['mae_c']:.3f} C, "
        f"R2={validation_metrics['r_squared']:.3f}."
    )
    print(
        f"Baseline RMSE={baseline_metrics['rmse_c']:.3f} C; "
        f"hybrid improvement="
        f"{diagnostics['calibration']['rmse_improvement_over_baseline_pct']:.1f}%."
    )
    print(
        "T2 calibration: "
        f"{len(t2_calibration_rows)} unique dates, alpha={t2_selected_alpha:g}, "
        f"leave-year-out RMSE={t2_validation_metrics['rmse_c']:.3f} C, "
        f"MAE={t2_validation_metrics['mae_c']:.3f} C, "
        f"R2={t2_validation_metrics['r_squared']:.3f}."
    )
    print(
        f"T2 baseline improvement="
        f"{t2_diagnostics['calibration']['rmse_improvement_over_baseline_pct']:.1f}%; "
        f"RMSE change from T1="
        f"{t2_diagnostics['calibration']['rmse_change_from_t1_pct']:.1f}%."
    )
    print(f"Wrote {len(daily_records)} T1 daily proxy rows to {daily_path}")
    print(f"Wrote {len(t2_daily_records)} T2 daily proxy rows to {t2_daily_path}")
    print(f"Wrote T1 and T2 annual proxy metrics to {output_dir}")
    for window in HYPOTHESIS_WINDOWS:
        summary = window_validation_summary[window.window_id]
        print(
            f"{window.window_id} held-out validation: "
            f"n={summary['calibration_unique_dates']}, "
            f"T1 RMSE={summary['t1']['rmse_c']:.3f} C, "
            f"T2 RMSE={summary['t2']['rmse_c']:.3f} C."
        )
    print(
        f"Audited {len(extrapolation_audit_records)} T1 extrapolation days; "
        f"{june_october_extrapolation_days} occur June-October."
    )
    print(
        f"Wrote {len(life_stage_exposure_records)} pre-association "
        f"life-stage exposure rows to {life_stage_exposure_path}"
    )
    print("WARNING: modeled_7day_mean_proxy_c is not observed or regulatory 7DADMax.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
