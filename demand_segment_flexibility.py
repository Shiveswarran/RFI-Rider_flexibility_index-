"""Demand-segment flexibility analysis for ClassTran.

This module implements the redesigned flexibility idea:

    segment = purpose + origin grid zone + weekday

The main index is interactive: it is based on the joint distribution of
pickup-time bins and destination zones.  Time-only and destination-only
distributions are kept as diagnostics, not separate flexibility indices.
"""

from __future__ import annotations

from pathlib import Path
import re

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd
from IPython.display import Image, display


COMPLETED_STATUSES = {"comp", "completed"}
CANCELLED_STATUSES = {"cancel", "canceled", "cancelled"}
NOSHOW_STATUSES = {"noshow", "no show", "no-show"}


def _status_clean(series):
    return series.astype("string").str.strip().str.lower()


def _time_minutes(series):
    text = series.astype("string").str.strip()
    parsed = pd.to_datetime(text, format="%H:%M:%S", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(text.loc[missing], format="%H:%M", errors="coerce")
    return parsed.dt.hour * 60 + parsed.dt.minute


def _entropy_from_counts(counts):
    values = np.asarray(counts, dtype=float)
    values = values[values > 0]
    if values.size == 0:
        return np.nan
    probabilities = values / values.sum()
    return float(-(probabilities * np.log(probabilities)).sum())


def _effective_options(counts):
    entropy = _entropy_from_counts(counts)
    if pd.isna(entropy):
        return np.nan
    return float(np.exp(entropy))


def _option_score(counts, possible_options):
    """Convert a distribution into a 0-1 score using effective option count.

    A single dominant option receives 0.  Equal use of every possible option
    receives 1.  Intermediate values reflect both richness and balance.
    """
    possible_options = int(possible_options)
    if possible_options <= 1:
        return 0.0
    effective = _effective_options(counts)
    if pd.isna(effective):
        return np.nan
    return float(np.clip((effective - 1.0) / (possible_options - 1.0), 0.0, 1.0))


def _top_share(counts):
    values = np.asarray(counts, dtype=float)
    total = values.sum()
    if total <= 0:
        return np.nan
    return float(values.max() / total)


def _format_time_bin(time_bin):
    if pd.isna(time_bin):
        return pd.NA
    minutes = int(time_bin)
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def _make_grid_zone(lat, lon, lat0, lon0, lat_step, lon_step):
    lat_values = pd.to_numeric(lat, errors="coerce").to_numpy(dtype=float)
    lon_values = pd.to_numeric(lon, errors="coerce").to_numpy(dtype=float)
    lat_idx = np.floor((lat_values - lat0) / lat_step).astype(int)
    lon_idx = np.floor((lon_values - lon0) / lon_step).astype(int)
    return pd.Series(
        "r" + pd.Series(lat_idx, index=lat.index).astype(str)
        + "_c" + pd.Series(lon_idx, index=lon.index).astype(str),
        index=lat.index,
    )


def _build_segment_frame(df_raw, grid_miles, time_bin_minutes):
    df_source = df_raw.copy()
    alias_map = {
        "pickup_lat": "Pick-up Latitude",
        "pickup_lon": "Pick-up Longitude",
        "dropoff_lat": "Drop-off Latitude",
        "dropoff_lon": "Drop-off Longitude",
    }
    for alias, source in alias_map.items():
        if alias not in df_source.columns and source in df_source.columns:
            df_source[alias] = df_source[source]

    required = [
        "Trip ID", "Trip Date", "Trip Status", "Purpose", "Earliest Pick-up",
        "pickup_lat", "pickup_lon", "dropoff_lat", "dropoff_lon",
    ]
    missing = [col for col in required if col not in df_source.columns]
    if missing:
        raise ValueError(f"Missing required columns for demand-segment analysis: {missing}")

    frame = df_source.loc[:, required].copy()
    frame["Purpose"] = (
        frame["Purpose"].astype("string").str.strip().fillna("Missing / Unknown")
        .replace("", "Missing / Unknown")
    )
    frame["status_clean"] = _status_clean(frame["Trip Status"])
    frame["trip_date"] = pd.to_datetime(frame["Trip Date"], errors="coerce")
    frame["weekday"] = frame["trip_date"].dt.day_name()
    frame["pickup_minutes"] = _time_minutes(frame["Earliest Pick-up"])
    frame["pickup_time_bin_min"] = (
        np.floor(frame["pickup_minutes"] / time_bin_minutes) * time_bin_minutes
    )
    frame["pickup_time_bin_label"] = frame["pickup_time_bin_min"].apply(_format_time_bin)

    numeric_cols = ["pickup_lat", "pickup_lon", "dropoff_lat", "dropoff_lon"]
    for col in numeric_cols:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    finite_coordinates = np.isfinite(frame[numeric_cols].to_numpy(dtype=float)).all(axis=1)
    frame = frame.loc[finite_coordinates].copy()

    frame = frame.dropna(
        subset=[
            "Trip ID", "trip_date", "weekday", "Purpose", "pickup_time_bin_min",
            "pickup_lat", "pickup_lon", "dropoff_lat", "dropoff_lon",
        ]
    ).copy()

    mile_per_degree_lat = 69.0
    mean_lat_rad = np.deg2rad(frame["pickup_lat"].mean())
    mile_per_degree_lon = max(69.0 * np.cos(mean_lat_rad), 1e-6)
    lat_step = grid_miles / mile_per_degree_lat
    lon_step = grid_miles / mile_per_degree_lon
    lat0 = min(frame["pickup_lat"].min(), frame["dropoff_lat"].min())
    lon0 = min(frame["pickup_lon"].min(), frame["dropoff_lon"].min())

    frame["origin_zone"] = _make_grid_zone(
        frame["pickup_lat"], frame["pickup_lon"], lat0, lon0, lat_step, lon_step
    )
    frame["destination_zone"] = _make_grid_zone(
        frame["dropoff_lat"], frame["dropoff_lon"], lat0, lon0, lat_step, lon_step
    )
    frame["segment_id"] = (
        frame["Purpose"].astype("string")
        + " | " + frame["origin_zone"].astype("string")
        + " | " + frame["weekday"].astype("string")
    )
    frame["time_destination_pair"] = (
        frame["pickup_time_bin_label"].astype("string")
        + " -> " + frame["destination_zone"].astype("string")
    )
    frame["completed_flag"] = frame["status_clean"].isin(COMPLETED_STATUSES)
    frame["cancelled_flag"] = frame["status_clean"].isin(CANCELLED_STATUSES)
    frame["noshow_flag"] = frame["status_clean"].isin(NOSHOW_STATUSES)

    metadata = {
        "grid_miles": grid_miles,
        "time_bin_minutes": time_bin_minutes,
        "lat_step": lat_step,
        "lon_step": lon_step,
        "lat_origin": lat0,
        "lon_origin": lon0,
    }
    return frame, metadata


def _distribution_table(frame, value_col, name):
    rows = (
        frame.groupby(["segment_id", value_col], dropna=False)
        .agg(trips=("Trip ID", "count"))
        .reset_index()
        .rename(columns={value_col: name})
    )
    totals = rows.groupby("segment_id")["trips"].transform("sum")
    rows["share"] = rows["trips"] / totals
    return rows.sort_values(["segment_id", "trips"], ascending=[True, False])


def _weighted_mean(values, weights):
    values = pd.to_numeric(values, errors="coerce")
    weights = pd.to_numeric(weights, errors="coerce")
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return np.nan
    return float(np.average(values.loc[valid], weights=weights.loc[valid]))


def _origin_zone_grid_map(segment_summary, metadata, output_path, weekday=None):
    reliable = segment_summary.loc[segment_summary["meets_reliability_filter"]].copy()
    if weekday is not None:
        reliable = reliable.loc[reliable["weekday"].eq(weekday)].copy()
    if reliable.empty:
        return None

    zone_summary = (
        reliable.groupby("origin_zone", dropna=False)
        .apply(
            lambda group: pd.Series({
                "trips": group["trips"].sum(),
                "segments": len(group),
                "interactive_flexibility_index": _weighted_mean(
                    group["interactive_flexibility_index"], group["trips"]
                ),
            })
        )
        .reset_index()
    )

    zone_pattern = re.compile(r"r(-?\d+)_c(-?\d+)")
    zone_summary[["row", "col"]] = (
        zone_summary["origin_zone"].str.extract(zone_pattern).astype(int)
    )

    lat0 = metadata["lat_origin"]
    lon0 = metadata["lon_origin"]
    lat_step = metadata["lat_step"]
    lon_step = metadata["lon_step"]

    values = zone_summary["interactive_flexibility_index"]
    vmin = float(values.quantile(0.05))
    vmax = float(values.quantile(0.95))
    if np.isclose(vmin, vmax):
        vmin = float(values.min())
        vmax = float(values.max())
    if np.isclose(vmin, vmax):
        vmax = vmin + 1e-6

    fig, ax = plt.subplots(figsize=(10, 9))
    cmap = plt.get_cmap("YlOrRd")
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    for _, row in zone_summary.iterrows():
        lat = lat0 + row["row"] * lat_step
        lon = lon0 + row["col"] * lon_step
        ax.add_patch(
            Rectangle(
                (lon, lat),
                lon_step,
                lat_step,
                facecolor=cmap(norm(row["interactive_flexibility_index"])),
                edgecolor="white",
                linewidth=0.25,
                alpha=0.9,
            )
        )

    ax.set_xlim(
        lon0 + (zone_summary["col"].min() - 1) * lon_step,
        lon0 + (zone_summary["col"].max() + 2) * lon_step,
    )
    ax.set_ylim(
        lat0 + (zone_summary["row"].min() - 1) * lat_step,
        lat0 + (zone_summary["row"].max() + 2) * lat_step,
    )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    title_context = "All weekdays" if weekday is None else str(weekday)
    ax.set_title(
        f"Origin Grid Flexibility Index - {title_context}\n"
        "Trip-weighted mean across reliable demand segments"
    )
    mean_lat = lat0 + zone_summary["row"].mean() * lat_step
    ax.set_aspect(1 / max(np.cos(np.deg2rad(mean_lat)), 1e-6))

    scalar = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    scalar.set_array([])
    cbar = fig.colorbar(scalar, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Interactive flexibility index")

    output_path = Path(output_path)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return str(output_path)


def _origin_zone_grid_maps(segment_summary, metadata, aggregate_output_path):
    aggregate_output_path = Path(aggregate_output_path)
    map_paths = {
        "aggregate": _origin_zone_grid_map(
            segment_summary, metadata, aggregate_output_path, weekday=None
        ),
        "weekday": {},
    }
    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    for weekday in weekday_order:
        if not segment_summary["weekday"].eq(weekday).any():
            continue
        weekday_path = aggregate_output_path.with_name(
            f"{aggregate_output_path.stem}_{weekday.lower()}{aggregate_output_path.suffix}"
        )
        result = _origin_zone_grid_map(
            segment_summary, metadata, weekday_path, weekday=weekday
        )
        if result:
            map_paths["weekday"][weekday] = result
    return map_paths


def _top_candidate_alternatives(frame, demand_management_candidates, top_segments=10, top_pairs=8):
    if demand_management_candidates.empty:
        return pd.DataFrame()

    candidate_keys = demand_management_candidates.head(top_segments)[
        ["Purpose", "origin_zone", "weekday", "demand_management_priority"]
    ].copy()
    candidate_keys["_candidate_rank"] = np.arange(1, len(candidate_keys) + 1)

    rows = []
    for _, candidate in candidate_keys.iterrows():
        mask = (
            frame["Purpose"].eq(candidate["Purpose"])
            & frame["origin_zone"].eq(candidate["origin_zone"])
            & frame["weekday"].eq(candidate["weekday"])
        )
        segment_frame = frame.loc[mask].copy()
        segment_trips = len(segment_frame)
        if segment_trips == 0:
            continue
        pair_summary = (
            segment_frame
            .groupby(["pickup_time_bin_label", "destination_zone"], dropna=False)
            .agg(
                trip_count=("Trip ID", "count"),
            )
            .reset_index()
        )
        pair_summary["share_within_segment"] = pair_summary["trip_count"] / segment_trips
        pair_summary = pair_summary.sort_values(
            ["trip_count", "share_within_segment"],
            ascending=[False, False],
        ).head(top_pairs)
        pair_summary.insert(0, "weekday", candidate["weekday"])
        pair_summary.insert(0, "origin_zone", candidate["origin_zone"])
        pair_summary.insert(0, "Purpose", candidate["Purpose"])
        pair_summary.insert(0, "candidate_rank", candidate["_candidate_rank"])
        pair_summary["segment_trips"] = segment_trips
        pair_summary["demand_management_priority"] = candidate["demand_management_priority"]
        rows.append(pair_summary)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def _top_candidate_time_shift_options(
    frame, demand_management_candidates, top_segments=10, top_time_bins=6
):
    if demand_management_candidates.empty:
        return pd.DataFrame()

    candidate_keys = demand_management_candidates.head(top_segments)[
        [
            "Purpose", "origin_zone", "weekday", "peak_time_label",
            "time_peak_share", "demand_management_priority",
        ]
    ].copy()
    candidate_keys["_candidate_rank"] = np.arange(1, len(candidate_keys) + 1)

    rows = []
    for _, candidate in candidate_keys.iterrows():
        mask = (
            frame["Purpose"].eq(candidate["Purpose"])
            & frame["origin_zone"].eq(candidate["origin_zone"])
            & frame["weekday"].eq(candidate["weekday"])
        )
        segment_frame = frame.loc[mask].copy()
        segment_trips = len(segment_frame)
        if segment_trips == 0:
            continue

        time_summary = (
            segment_frame
            .groupby("pickup_time_bin_label", dropna=False)
            .agg(
                trips_in_time_bin=("Trip ID", "count"),
                active_destination_zones=("destination_zone", "nunique"),
                effective_destination_zones=("destination_zone", lambda s: _effective_options(s.value_counts())),
            )
            .reset_index()
        )
        time_summary["share_within_segment"] = (
            time_summary["trips_in_time_bin"] / segment_trips
        )
        time_summary["is_peak_time_bin"] = (
            time_summary["pickup_time_bin_label"].eq(candidate["peak_time_label"])
        )
        time_summary["alternative_time_share"] = np.where(
            time_summary["is_peak_time_bin"], 0.0, time_summary["share_within_segment"]
        )
        time_summary = time_summary.sort_values(
            ["is_peak_time_bin", "trips_in_time_bin"],
            ascending=[False, False],
        ).head(top_time_bins)
        time_summary.insert(0, "weekday", candidate["weekday"])
        time_summary.insert(0, "origin_zone", candidate["origin_zone"])
        time_summary.insert(0, "Purpose", candidate["Purpose"])
        time_summary.insert(0, "candidate_rank", candidate["_candidate_rank"])
        time_summary["segment_trips"] = segment_trips
        time_summary["segment_peak_time_label"] = candidate["peak_time_label"]
        time_summary["segment_time_peak_share"] = candidate["time_peak_share"]
        time_summary["demand_management_priority"] = candidate["demand_management_priority"]
        rows.append(time_summary)

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def run_demand_segment_flexibility_analysis(
    df_raw,
    grid_miles=1.0,
    time_bin_minutes=30,
    min_segment_trips=10,
    min_segment_service_days=3,
    density_reference_trips=100,
    map_output_path="demand_segment_origin_grid_flexibility_map.png",
):
    """Compute demand-segment flexibility using observed distributions."""
    frame, metadata = _build_segment_frame(df_raw, grid_miles, time_bin_minutes)

    possible_by_purpose_weekday = (
        frame.groupby(["Purpose", "weekday"], dropna=False)
        .agg(
            possible_destination_zones=("destination_zone", "nunique"),
            possible_time_destination_pairs=("time_destination_pair", "nunique"),
        )
        .reset_index()
    )

    rows = []
    for keys, group in frame.groupby(["Purpose", "origin_zone", "weekday"], dropna=False):
        purpose, origin_zone, weekday = keys
        time_counts = group["pickup_time_bin_min"].value_counts()
        destination_counts = group["destination_zone"].value_counts()
        pair_counts = group["time_destination_pair"].value_counts()
        peak_time_bin = time_counts.idxmax() if not time_counts.empty else np.nan
        rows.append({
            "Purpose": purpose,
            "origin_zone": origin_zone,
            "weekday": weekday,
            "segment_id": f"{purpose} | {origin_zone} | {weekday}",
            "trips": len(group),
            "service_days": group["trip_date"].dt.date.nunique(),
            "completed_trips": int(group["completed_flag"].sum()),
            "cancelled_trips": int(group["cancelled_flag"].sum()),
            "noshow_trips": int(group["noshow_flag"].sum()),
            "completion_rate": group["completed_flag"].mean(),
            "cancellation_rate": group["cancelled_flag"].mean(),
            "noshow_rate": group["noshow_flag"].mean(),
            "active_time_bins": int(time_counts.size),
            "effective_time_bins": _effective_options(time_counts),
            "time_peak_share": _top_share(time_counts),
            "peak_time_bin": peak_time_bin,
            "peak_time_label": _format_time_bin(peak_time_bin),
            "active_destination_zones": int(destination_counts.size),
            "effective_destination_zones": _effective_options(destination_counts),
            "destination_peak_share": _top_share(destination_counts),
            "active_time_destination_pairs": int(pair_counts.size),
            "effective_time_destination_pairs": _effective_options(pair_counts),
            "interaction_peak_share": _top_share(pair_counts),
        })

    segment_summary = pd.DataFrame(rows).merge(
        possible_by_purpose_weekday,
        on=["Purpose", "weekday"],
        how="left",
    )
    interaction_denominator = segment_summary["possible_time_destination_pairs"] - 1
    segment_summary["interactive_diversity_index"] = np.where(
        interaction_denominator.gt(0),
        (segment_summary["effective_time_destination_pairs"] - 1) / interaction_denominator,
        0.0,
    )
    segment_summary["interactive_diversity_index"] = (
        segment_summary["interactive_diversity_index"].clip(0, 1)
    )
    segment_summary["density_weight"] = (
        np.log1p(segment_summary["trips"]) / np.log1p(density_reference_trips)
    ).clip(0, 1)
    segment_summary["interactive_flexibility_index"] = (
        segment_summary["interactive_diversity_index"] * segment_summary["density_weight"]
    )
    segment_summary["meets_reliability_filter"] = (
        segment_summary["trips"].ge(min_segment_trips)
        & segment_summary["service_days"].ge(min_segment_service_days)
    )

    reliable = segment_summary.loc[segment_summary["meets_reliability_filter"]].copy()
    if reliable.empty:
        relationship_by_band = pd.DataFrame()
        demand_management_candidates = pd.DataFrame()
    else:
        reliable["flexibility_band"] = pd.qcut(
            reliable["interactive_flexibility_index"],
            q=min(5, reliable["interactive_flexibility_index"].nunique()),
            labels=False,
            duplicates="drop",
        )
        reliable["flexibility_band"] = reliable["flexibility_band"].apply(
            lambda x: pd.NA if pd.isna(x) else f"Q{int(x) + 1}"
        )
        relationship_by_band = (
            reliable.groupby("flexibility_band", dropna=False)
            .agg(
                segments=("segment_id", "count"),
                trips=("trips", "sum"),
                mean_interactive_flexibility_index=("interactive_flexibility_index", "mean"),
                mean_interactive_diversity_index=("interactive_diversity_index", "mean"),
                mean_density_weight=("density_weight", "mean"),
                mean_active_time_bins=("active_time_bins", "mean"),
                mean_effective_time_bins=("effective_time_bins", "mean"),
                mean_active_destination_zones=("active_destination_zones", "mean"),
                mean_effective_destination_zones=("effective_destination_zones", "mean"),
                mean_active_time_destination_pairs=("active_time_destination_pairs", "mean"),
                mean_effective_time_destination_pairs=("effective_time_destination_pairs", "mean"),
                trip_weighted_completion_rate=(
                    "completed_trips",
                    lambda s: s.sum() / reliable.loc[s.index, "trips"].sum(),
                ),
                trip_weighted_cancellation_rate=(
                    "cancelled_trips",
                    lambda s: s.sum() / reliable.loc[s.index, "trips"].sum(),
                ),
                mean_time_peak_share=("time_peak_share", "mean"),
            )
            .reset_index()
        )

        demand_management_candidates = reliable.assign(
            demand_management_priority=(
                reliable["interactive_flexibility_index"]
                * reliable["time_peak_share"]
            )
        ).sort_values("demand_management_priority", ascending=False)

    time_distribution = _distribution_table(frame, "pickup_time_bin_label", "pickup_time_bin")
    destination_distribution = _distribution_table(frame, "destination_zone", "destination_zone")
    interaction_distribution = _distribution_table(
        frame, "time_destination_pair", "time_destination_pair"
    )
    origin_grid_map_paths = _origin_zone_grid_maps(
        segment_summary, metadata, map_output_path
    )
    origin_grid_map_path = origin_grid_map_paths["aggregate"]
    top_candidate_alternatives = _top_candidate_alternatives(
        frame, demand_management_candidates
    )
    top_candidate_time_shift_options = _top_candidate_time_shift_options(
        frame, demand_management_candidates
    )

    print("Demand-segment definition: Purpose + 1-mile origin grid zone + weekday")
    print(f"Rows with valid purpose/time/coordinate fields: {len(frame):,}")
    print(f"Segments: {len(segment_summary):,}")
    print(
        "Reliable segments: "
        f"{int(segment_summary['meets_reliability_filter'].sum()):,} "
        f"(min {min_segment_trips} trips and {min_segment_service_days} service days)"
    )
    print(
        "The flexibility index is multiplicative: interactive diversity * density weight. "
        f"Density is capped at {density_reference_trips:,} trips."
    )

    display_cols = [
        "Purpose", "origin_zone", "weekday", "trips", "service_days",
        "interactive_flexibility_index", "interactive_diversity_index", "density_weight",
        "active_time_bins", "effective_time_bins",
        "active_destination_zones", "effective_destination_zones",
        "active_time_destination_pairs", "effective_time_destination_pairs",
        "peak_time_label", "time_peak_share", "interaction_peak_share",
    ]
    print("Largest demand segments:")
    display(
        segment_summary.sort_values("trips", ascending=False)
        .head(25)[display_cols]
        .style.format({
            "interactive_flexibility_index": "{:.3f}",
            "interactive_diversity_index": "{:.3f}",
            "density_weight": "{:.3f}",
            "effective_time_bins": "{:.2f}",
            "effective_destination_zones": "{:.2f}",
            "effective_time_destination_pairs": "{:.2f}",
            "time_peak_share": "{:.1%}",
            "interaction_peak_share": "{:.1%}",
        })
    )

    if not relationship_by_band.empty:
        print("Relationship between demand-segment flexibility bands and outcomes:")
        display(
            relationship_by_band.style.format({
                "mean_interactive_flexibility_index": "{:.3f}",
                "mean_interactive_diversity_index": "{:.3f}",
                "mean_density_weight": "{:.3f}",
                "mean_active_time_bins": "{:.1f}",
                "mean_effective_time_bins": "{:.2f}",
                "mean_active_destination_zones": "{:.1f}",
                "mean_effective_destination_zones": "{:.2f}",
                "mean_active_time_destination_pairs": "{:.1f}",
                "mean_effective_time_destination_pairs": "{:.2f}",
                "trip_weighted_completion_rate": "{:.1%}",
                "trip_weighted_cancellation_rate": "{:.1%}",
                "mean_time_peak_share": "{:.1%}",
            })
        )

        print("High-priority demand-management candidates:")
        display(
            demand_management_candidates.head(25)[
                display_cols + ["demand_management_priority"]
            ].style.format({
                "interactive_flexibility_index": "{:.3f}",
                "interactive_diversity_index": "{:.3f}",
                "density_weight": "{:.3f}",
                "effective_time_bins": "{:.2f}",
                "effective_destination_zones": "{:.2f}",
                "effective_time_destination_pairs": "{:.2f}",
                "time_peak_share": "{:.1%}",
                "interaction_peak_share": "{:.1%}",
                "demand_management_priority": "{:.3f}",
            })
        )

        if not top_candidate_time_shift_options.empty:
            print("Peak and alternative pickup-time bins within highest-priority candidates:")
            display(
                top_candidate_time_shift_options.style.format({
                    "demand_management_priority": "{:.3f}",
                    "trips_in_time_bin": "{:,.0f}",
                    "segment_trips": "{:,.0f}",
                    "share_within_segment": "{:.1%}",
                    "alternative_time_share": "{:.1%}",
                    "segment_time_peak_share": "{:.1%}",
                    "effective_destination_zones": "{:.2f}",
                })
            )

        if not top_candidate_alternatives.empty:
            print("Top observed time-destination pairs within highest-priority candidates:")
            display(
                top_candidate_alternatives.style.format({
                    "demand_management_priority": "{:.3f}",
                    "trip_count": "{:,.0f}",
                    "segment_trips": "{:,.0f}",
                    "share_within_segment": "{:.1%}",
                })
            )

    if origin_grid_map_path:
        print(f"Origin grid flexibility map saved to: {origin_grid_map_path}")
        display(Image(filename=origin_grid_map_path))
    for weekday, path in origin_grid_map_paths["weekday"].items():
        print(f"{weekday} origin grid flexibility map saved to: {path}")
        display(Image(filename=path))

    return {
        "segment_trip_frame": frame,
        "segment_summary": segment_summary,
        "relationship_by_band": relationship_by_band,
        "demand_management_candidates": demand_management_candidates,
        "time_distribution": time_distribution,
        "destination_distribution": destination_distribution,
        "interaction_distribution": interaction_distribution,
        "top_candidate_alternatives": top_candidate_alternatives,
        "top_candidate_time_shift_options": top_candidate_time_shift_options,
        "origin_grid_map_path": origin_grid_map_path,
        "origin_grid_map_paths": origin_grid_map_paths,
        "metadata": metadata,
    }
