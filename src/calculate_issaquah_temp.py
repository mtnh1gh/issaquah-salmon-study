#!/usr/bin/env python3
"""Build a daily Issaquah Creek water-temperature proxy for 1997-2025.

This is a hindcast/interpolation model, not a continuous sensor record. It is
calibrated to King County grab samples at station 0631 using continuous USGS
daily discharge, NOAA daily air temperature, and seasonal terms. The modeled
response is a day-level proxy for grab-sample water temperature; it is not an
observed daily maximum and must not be presented as regulatory 7DADMax.

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
from collections import defaultdict
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

    daily_path = output_dir / (
        f"issaquah_creek_daily_temperature_proxy_{args.start_date.year}_{args.end_date.year}.csv"
    )
    annual_path = output_dir / (
        f"issaquah_creek_annual_temperature_proxy_{args.start_date.year}_{args.end_date.year}.csv"
    )
    calibration_path = output_dir / "issaquah_temperature_proxy_calibration.csv"
    diagnostics_path = output_dir / "issaquah_temperature_proxy_diagnostics.json"
    manifest_path = cache_dir / "source_manifest.json"

    atomic_write_csv(daily_path, list(daily_records[0]), daily_records)
    atomic_write_csv(annual_path, list(annual_records[0]), annual_records)
    atomic_write_csv(calibration_path, list(calibration_output[0]), calibration_output)

    diagnostics = {
        "model": {
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
        },
    }
    atomic_write_json(diagnostics_path, diagnostics)
    manifest = {
        "access_date": args.snapshot_date.isoformat(),
        "created_at": datetime.now().astimezone().isoformat(),
        "sources": manifest_sources,
    }
    atomic_write_json(manifest_path, manifest)

    if len(daily_records) != (args.end_date - args.start_date).days + 1:
        raise AssertionError("Daily output row count is incomplete.")
    if validation_metrics["rmse_c"] >= baseline_metrics["rmse_c"]:
        raise RuntimeError(
            "Hybrid model did not improve on the held-out seasonal baseline; output is not accepted."
        )

    print(
        "Calibration: "
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
    print(f"Wrote {len(daily_records)} daily proxy rows to {daily_path}")
    print(f"Wrote annual proxy metrics to {annual_path}")
    print("WARNING: modeled_7day_mean_proxy_c is not observed or regulatory 7DADMax.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
