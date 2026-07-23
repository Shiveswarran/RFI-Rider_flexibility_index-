"""Separate temporal and geographical flexibility indices for ClassTran.

Demand segment: Purpose + 1.5-mile origin grid zone + weekday.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


RIGID_PURPOSES = {"Workshop", "Employment", "Education", "Medical"}


def _clean_purpose(series):
    return (
        series.astype("string").str.strip().replace("", pd.NA)
        .fillna("Missing / Unknown")
    )


def _time_minutes(series):
    """Convert Excel/Python clock-time values to minutes after midnight."""
    text = series.astype("string").str.strip()
    parsed = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(
            text.loc[missing], format="%H:%M", errors="coerce"
        )
    return parsed.dt.hour * 60 + parsed.dt.minute + parsed.dt.second / 60


def _clock_label(minutes):
    minutes = int(minutes) % 1440
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _interval_label(start_minutes, width):
    return f"{_clock_label(start_minutes)}-{_clock_label(start_minutes + width)}"


def _make_grid_zone(lat, lon, lat0, lon0, lat_step, lon_step):
    lat_index = np.floor((lat.to_numpy(dtype=float) - lat0) / lat_step).astype(int)
    lon_index = np.floor((lon.to_numpy(dtype=float) - lon0) / lon_step).astype(int)
    return pd.Series(
        "r" + pd.Series(lat_index, index=lat.index).astype(str)
        + "_c" + pd.Series(lon_index, index=lon.index).astype(str),
        index=lat.index,
    )


def build_analysis_frame(df_raw, grid_miles=1.5, time_bin_minutes=30):
    """Clean source fields and construct the agreed demand segments."""
    required = [
        "Trip ID", "Trip Date", "Purpose", "Promised Pick-up Time",
        "Pick-up Latitude", "Pick-up Longitude",
        "Drop-off Latitude", "Drop-off Longitude",
    ]
    missing = [column for column in required if column not in df_raw.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    frame = df_raw.loc[:, required].copy()
    frame["Purpose"] = _clean_purpose(frame["Purpose"])
    frame["trip_date"] = pd.to_datetime(frame["Trip Date"], errors="coerce")
    frame["weekday"] = frame["trip_date"].dt.day_name()
    frame["promised_pickup_minutes"] = _time_minutes(frame["Promised Pick-up Time"])
    frame["pickup_time_bin_min"] = (
        np.floor(frame["promised_pickup_minutes"] / time_bin_minutes)
        * time_bin_minutes
    )

    coordinate_columns = [
        "Pick-up Latitude", "Pick-up Longitude",
        "Drop-off Latitude", "Drop-off Longitude",
    ]
    for column in coordinate_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(
        subset=[
            "Trip ID", "trip_date", "weekday", "promised_pickup_minutes",
            *coordinate_columns,
        ]
    ).copy()
    finite = np.isfinite(frame[coordinate_columns].to_numpy(dtype=float)).all(axis=1)
    frame = frame.loc[finite].copy()

    miles_per_degree_latitude = 69.0
    mean_latitude_radians = np.deg2rad(frame["Pick-up Latitude"].mean())
    miles_per_degree_longitude = max(
        69.0 * np.cos(mean_latitude_radians), 1e-6
    )
    latitude_step = grid_miles / miles_per_degree_latitude
    longitude_step = grid_miles / miles_per_degree_longitude
    latitude_origin = min(
        frame["Pick-up Latitude"].min(), frame["Drop-off Latitude"].min()
    )
    longitude_origin = min(
        frame["Pick-up Longitude"].min(), frame["Drop-off Longitude"].min()
    )

    frame["origin_zone"] = _make_grid_zone(
        frame["Pick-up Latitude"], frame["Pick-up Longitude"],
        latitude_origin, longitude_origin, latitude_step, longitude_step,
    )
    frame["destination_zone"] = _make_grid_zone(
        frame["Drop-off Latitude"], frame["Drop-off Longitude"],
        latitude_origin, longitude_origin, latitude_step, longitude_step,
    )
    frame["pickup_time_bin"] = frame["pickup_time_bin_min"].map(
        lambda value: _interval_label(value, time_bin_minutes)
    )
    frame["segment_id"] = (
        frame["Purpose"].astype("string")
        + " | " + frame["origin_zone"].astype("string")
        + " | " + frame["weekday"].astype("string")
    )
    frame["policy_flexible"] = (
        ~frame["Purpose"].isin(RIGID_PURPOSES)
        & frame["Purpose"].ne("Missing / Unknown")
    )
    metadata = {
        "grid_miles": grid_miles,
        "time_bin_minutes": time_bin_minutes,
        "latitude_origin": latitude_origin,
        "longitude_origin": longitude_origin,
        "latitude_step": latitude_step,
        "longitude_step": longitude_step,
    }
    return frame, metadata


def calculate_temporal_flexibility(
    frame,
    shift_horizon_minutes=120,
    min_segment_trips=10,
    min_segment_service_days=3,
):
    """Calculate the peak-based distance-weighted temporal index."""
    keys = ["segment_id", "Purpose", "origin_zone", "weekday"]
    distribution = (
        frame.groupby(
            keys + ["pickup_time_bin_min", "pickup_time_bin"], observed=True
        )
        .agg(
            time_bin_trips=("Trip ID", "count"),
            time_bin_service_days=("trip_date", "nunique"),
        )
        .reset_index()
    )
    segment_totals = (
        frame.groupby(keys, observed=True)
        .agg(
            trips=("Trip ID", "count"),
            service_days=("trip_date", "nunique"),
            policy_flexible=("policy_flexible", "first"),
        )
        .reset_index()
    )
    distribution = distribution.merge(segment_totals, on=keys, how="left")
    distribution["p_time"] = distribution["time_bin_trips"] / distribution["trips"]
    distribution["p_s_t"] = distribution["p_time"]

    peak = (
        distribution.sort_values(
            ["segment_id", "time_bin_trips", "pickup_time_bin_min"],
            ascending=[True, False, True],
        )
        .drop_duplicates("segment_id")
        .loc[:, [
            "segment_id", "pickup_time_bin_min", "pickup_time_bin", "p_time"
        ]]
        .rename(columns={
            "pickup_time_bin_min": "peak_time_bin_min",
            "pickup_time_bin": "peak_time_bin",
            "p_time": "peak_time_share",
        })
    )
    distribution = distribution.merge(peak, on="segment_id", how="left")
    signed = distribution["pickup_time_bin_min"] - distribution["peak_time_bin_min"]
    distribution["signed_shift_minutes"] = np.where(
        signed > 720, signed - 1440,
        np.where(signed < -720, signed + 1440, signed),
    )
    distribution["absolute_shift_minutes"] = distribution[
        "signed_shift_minutes"
    ].abs()
    distribution["is_peak_time"] = distribution["absolute_shift_minutes"].eq(0)
    distribution["is_alternative_time"] = ~distribution["is_peak_time"]
    distribution["capped_shift_minutes"] = distribution[
        "absolute_shift_minutes"
    ].clip(upper=shift_horizon_minutes)
    distribution["expected_shift_contribution_minutes"] = (
        distribution["p_time"] * distribution["absolute_shift_minutes"]
    )
    distribution["temporal_index_contribution"] = (
        distribution["p_time"]
        * distribution["capped_shift_minutes"]
        / shift_horizon_minutes
    )

    def summarize(group):
        peak_share = float(group["peak_time_share"].iloc[0])
        alternative_share = 1.0 - peak_share
        alternatives = group.loc[group["is_alternative_time"]]
        weighted_shift = float(
            alternatives["expected_shift_contribution_minutes"].sum()
        )
        average_shift = (
            weighted_shift / alternative_share if alternative_share > 0 else np.nan
        )
        return pd.Series({
            "peak_time_bin": group["peak_time_bin"].iloc[0],
            "peak_time_share": peak_share,
            "active_time_bins": group["pickup_time_bin"].nunique(),
            "alternative_time_share_raw": alternative_share,
            "average_alternative_shift_minutes_raw": average_shift,
            "expected_shift_potential_minutes_raw": weighted_shift,
            "temporal_flexibility_index_raw": float(
                alternatives["temporal_index_contribution"].sum()
            ),
        })

    temporal_metrics = (
        distribution.groupby("segment_id", observed=True, group_keys=False)
        .apply(summarize)
        .reset_index()
    )
    summary = segment_totals.merge(temporal_metrics, on="segment_id", how="left")
    summary["meets_reliability_filter"] = (
        summary["trips"].ge(min_segment_trips)
        & summary["service_days"].ge(min_segment_service_days)
    )
    summary["temporal_eligible"] = (
        summary["policy_flexible"] & summary["meets_reliability_filter"]
    )
    final_to_raw = {
        "alternative_time_share": "alternative_time_share_raw",
        "average_alternative_shift_minutes": "average_alternative_shift_minutes_raw",
        "expected_shift_potential_minutes": "expected_shift_potential_minutes_raw",
        "temporal_flexibility_index": "temporal_flexibility_index_raw",
    }
    for final_column, raw_column in final_to_raw.items():
        summary[final_column] = summary[raw_column].where(
            summary["temporal_eligible"]
        )
    summary["A_s"] = summary["alternative_time_share"]
    summary["D_s_minutes"] = summary["average_alternative_shift_minutes"]
    summary["T_s"] = summary["temporal_flexibility_index"]

    distribution = distribution.merge(
        summary.loc[:, [
            "segment_id", "temporal_eligible", "meets_reliability_filter",
            *final_to_raw.keys(), "A_s", "D_s_minutes", "T_s",
        ]],
        on="segment_id",
        how="left",
    )
    candidate_pool = distribution.loc[
        distribution["temporal_eligible"] & distribution["is_alternative_time"]
    ].copy()
    candidate_pool["alternative_rank"] = (
        candidate_pool.groupby("segment_id")["time_bin_trips"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    candidate_pool = candidate_pool.sort_values(
        ["segment_id", "alternative_rank", "absolute_shift_minutes"]
    )
    return summary, distribution, candidate_pool


def calculate_geographical_flexibility(frame, segment_summary):
    """Calculate Gini-Simpson destination diversity for allowable purposes."""
    keys = ["segment_id", "Purpose", "origin_zone", "weekday"]
    eligible_frame = frame.loc[frame["policy_flexible"]].copy()
    candidate_pool = (
        eligible_frame.groupby(keys + ["destination_zone"], observed=True)
        .agg(
            destination_visits=("Trip ID", "count"),
            destination_service_days=("trip_date", "nunique"),
        )
        .reset_index()
    )
    totals = candidate_pool.groupby("segment_id")[
        "destination_visits"
    ].transform("sum")
    candidate_pool["destination_share"] = (
        candidate_pool["destination_visits"] / totals
    )
    candidate_pool["p_s_d"] = candidate_pool["destination_share"]
    candidate_pool = candidate_pool.sort_values(
        ["segment_id", "destination_visits", "destination_zone"],
        ascending=[True, False, True],
    )
    candidate_pool["destination_rank"] = (
        candidate_pool.groupby("segment_id").cumcount() + 1
    )
    candidate_pool["is_dominant_destination"] = candidate_pool[
        "destination_rank"
    ].eq(1)

    geo_metrics = (
        candidate_pool.groupby("segment_id", observed=True)
        .agg(
            active_destination_zones=("destination_zone", "nunique"),
            sum_squared_destination_shares=(
                "destination_share", lambda values: float(np.square(values).sum())
            ),
        )
        .reset_index()
    )
    geo_metrics["alternative_destination_count_raw"] = (
        geo_metrics["active_destination_zones"] - 1
    ).clip(lower=0)
    geo_metrics["effective_destination_count_raw"] = (
        1.0 / geo_metrics["sum_squared_destination_shares"]
    )
    geo_metrics["geographical_flexibility_index_raw"] = (
        1.0 - geo_metrics["sum_squared_destination_shares"]
    )
    dominant = (
        candidate_pool.loc[candidate_pool["is_dominant_destination"], [
            "segment_id", "destination_zone", "destination_visits",
            "destination_share",
        ]]
        .rename(columns={
            "destination_zone": "dominant_destination_zone",
            "destination_visits": "dominant_destination_visits",
            "destination_share": "dominant_destination_share",
        })
    )
    geo_metrics = geo_metrics.merge(dominant, on="segment_id", how="left")
    summary = segment_summary.merge(geo_metrics, on="segment_id", how="left")
    summary["geographical_eligible"] = (
        summary["policy_flexible"] & summary["meets_reliability_filter"]
    )
    final_to_raw = {
        "alternative_destination_count": "alternative_destination_count_raw",
        "effective_destination_count": "effective_destination_count_raw",
        "geographical_flexibility_index": "geographical_flexibility_index_raw",
        "dominant_destination_zone_final": "dominant_destination_zone",
        "dominant_destination_visits_final": "dominant_destination_visits",
        "dominant_destination_share_final": "dominant_destination_share",
    }
    for final_column, raw_column in final_to_raw.items():
        summary[final_column] = summary[raw_column].where(
            summary["geographical_eligible"]
        )
    summary["G_s"] = summary["geographical_flexibility_index"]
    return summary, candidate_pool


def run_two_index_analysis(
    df_raw,
    grid_miles=1.5,
    time_bin_minutes=30,
    shift_horizon_minutes=120,
    min_segment_trips=10,
    min_segment_service_days=3,
):
    frame, metadata = build_analysis_frame(
        df_raw, grid_miles=grid_miles, time_bin_minutes=time_bin_minutes
    )
    temporal_summary, time_distribution, temporal_candidates = (
        calculate_temporal_flexibility(
            frame,
            shift_horizon_minutes=shift_horizon_minutes,
            min_segment_trips=min_segment_trips,
            min_segment_service_days=min_segment_service_days,
        )
    )
    segment_summary, geographical_candidates = (
        calculate_geographical_flexibility(frame, temporal_summary)
    )
    parameters = {
        "grid_miles": grid_miles,
        "time_bin_minutes": time_bin_minutes,
        "shift_horizon_minutes": shift_horizon_minutes,
        "min_segment_trips": min_segment_trips,
        "min_segment_service_days": min_segment_service_days,
        "rigid_purposes": sorted(RIGID_PURPOSES),
    }
    return {
        "analysis_frame": frame,
        "segment_summary": segment_summary,
        "time_distribution": time_distribution,
        "temporal_candidate_pool": temporal_candidates,
        "geographical_candidate_pool": geographical_candidates,
        "metadata": metadata,
        "parameters": parameters,
    }
