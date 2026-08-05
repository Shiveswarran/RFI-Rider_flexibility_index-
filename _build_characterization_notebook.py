from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
NOTEBOOK_PATH = ROOT / "Characterization_two_index.ipynb"

nb = nbf.v4.new_notebook()
nb.metadata.kernelspec = {
    "display_name": "chi_goodness",
    "language": "python",
    "name": "python3",
}
nb.metadata.language_info = {"name": "python", "version": "3.10.20"}

cells = []
cells.append(nbf.v4.new_markdown_cell(
"""# ClassTran two-index contemporaneous characterization

This notebook characterizes the study area using the temporal flexibility index
and geographical flexibility index constructed in
`data_analysis_pattern_Classtran_two_indexes.ipynb`.

The unit of analysis is the demand segment:

$$
s = (\text{Purpose},\ \text{1.5-mile origin zone},\ \text{weekday}).
$$

The analysis is contemporaneous: flexibility and trip outcomes come from the
same July 2022-June 2023 period. Therefore, all outcome results are descriptive
associations, not causal effects. Completion and cancellation are used only for
characterization; they do not enter any flexibility or demand-management score.
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Analysis choices

- Reuse the same raw workbook, 1.5-mile grid, 30-minute promised-pickup bins,
  120-minute shift horizon, and reliability filter as the two-index notebook.
- Reliable means at least 10 trips observed on at least 3 distinct service dates.
- Workshop, Employment, Education, and Medical remain policy-rigid; their two
  published indices are NA and they are excluded from scored-index comparisons.
- The primary outcome denominator contains trips whose status is recognized as
  completed or cancelled. Other statuses are reported separately rather than
  silently assigned to either outcome.
- Segment-level group rates are trip-weighted: total completed trips divided by
  total completed-plus-cancelled trips in the group.
"""
))

cells.append(nbf.v4.new_code_cell(
"""from pathlib import Path
import os
import sys

os.environ.setdefault("MPLCONFIGDIR", "/tmp/classTran-matplotlib")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display
from scipy.stats import spearmanr

PROJECT_DIR = Path("/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-")
DATA_PATH = PROJECT_DIR / "Ecolane Reservation and Trip Data July 2022 - June 2023.xlsx"
SHEET_NAME = "SMART Trip Data"

GRID_MILES = 1.5
TIME_BIN_MINUTES = 30
SHIFT_HORIZON_MINUTES = 120
MIN_SEGMENT_TRIPS = 10
MIN_SEGMENT_SERVICE_DAYS = 3

sys.path.insert(0, str(PROJECT_DIR))
from two_index_flexibility import RIGID_PURPOSES, run_two_index_analysis

pd.set_option("display.max_columns", 60)
pd.set_option("display.width", 180)
plt.style.use("seaborn-v0_8-whitegrid")
"""
))

cells.append(nbf.v4.new_markdown_cell("## 1. Load the same trip data and reconstruct the two indices"))
cells.append(nbf.v4.new_code_cell(
"""source_columns = [
    "Trip ID", "Trip Date", "Trip Status", "Cancel Type", "Purpose",
    "Promised Pick-up Time", "Pick-up Latitude", "Pick-up Longitude",
    "Drop-off Latitude", "Drop-off Longitude",
]

df_raw = pd.read_excel(DATA_PATH, sheet_name=SHEET_NAME, usecols=source_columns)
results = run_two_index_analysis(
    df_raw,
    grid_miles=GRID_MILES,
    time_bin_minutes=TIME_BIN_MINUTES,
    shift_horizon_minutes=SHIFT_HORIZON_MINUTES,
    min_segment_trips=MIN_SEGMENT_TRIPS,
    min_segment_service_days=MIN_SEGMENT_SERVICE_DAYS,
)

analysis_frame = results["analysis_frame"]
segment_summary = results["segment_summary"].copy()
metadata = results["metadata"]

print(f"Raw rows: {len(df_raw):,}")
print(f"Usable trips for index construction: {len(analysis_frame):,}")
print(f"Demand segments: {len(segment_summary):,}")
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 2. Attach trip outcomes to the same demand segments

Outcome fields are aligned by original workbook row. This is safer than joining
only on `Trip ID` if an identifier appears more than once. Status labels are
normalized to lower case. A status beginning with `comp` is completed and a
status beginning with `cancel` is cancelled; every other status is retained as
`other` and excluded from the primary binary-outcome denominator.
"""
))
cells.append(nbf.v4.new_code_cell(
"""outcome_trips = analysis_frame[["Trip ID", "segment_id"]].copy()
outcome_trips[["Trip Status", "Cancel Type"]] = df_raw.loc[
    outcome_trips.index, ["Trip Status", "Cancel Type"]
]

outcome_trips["status_normalized"] = (
    outcome_trips["Trip Status"].astype("string").str.strip().str.lower()
)
outcome_trips["is_completed"] = outcome_trips["status_normalized"].str.startswith(
    "comp", na=False
)
outcome_trips["is_cancelled"] = outcome_trips["status_normalized"].str.startswith(
    "cancel", na=False
)
outcome_trips["is_other_status"] = ~(
    outcome_trips["is_completed"] | outcome_trips["is_cancelled"]
)

status_counts = (
    outcome_trips.groupby("status_normalized", dropna=False)
    .size().rename("trips").reset_index().sort_values("trips", ascending=False)
)
display(status_counts)

segment_outcomes = (
    outcome_trips.groupby("segment_id", observed=True)
    .agg(
        status_trips=("Trip ID", "count"),
        completed_trips=("is_completed", "sum"),
        cancelled_trips=("is_cancelled", "sum"),
        other_status_trips=("is_other_status", "sum"),
    )
    .reset_index()
)
segment_outcomes["outcome_trips"] = (
    segment_outcomes["completed_trips"] + segment_outcomes["cancelled_trips"]
)
segment_outcomes["completion_rate"] = (
    segment_outcomes["completed_trips"] / segment_outcomes["outcome_trips"]
)
segment_outcomes["cancellation_rate"] = (
    segment_outcomes["cancelled_trips"] / segment_outcomes["outcome_trips"]
)

characterization = segment_summary.merge(segment_outcomes, on="segment_id", how="left")
scored = characterization.loc[
    characterization["temporal_flexibility_index"].notna()
    & characterization["geographical_flexibility_index"].notna()
    & characterization["outcome_trips"].gt(0)
].copy()

assert np.allclose(
    scored["completion_rate"] + scored["cancellation_rate"], 1.0
)
print(f"Scored segments with binary outcomes: {len(scored):,}")
"""
))

cells.append(nbf.v4.new_markdown_cell("## 3. Coverage and score availability"))
cells.append(nbf.v4.new_code_cell(
"""coverage = pd.DataFrame({
    "stage": [
        "All demand segments",
        "Reliable segments",
        "Reliable policy-rigid segments",
        "Published temporal scores",
        "Published geographical scores",
        "Scored segments with binary outcomes",
    ],
    "segments": [
        len(characterization),
        int(characterization["meets_reliability_filter"].sum()),
        int((characterization["meets_reliability_filter"] & ~characterization["policy_flexible"]).sum()),
        int(characterization["temporal_flexibility_index"].notna().sum()),
        int(characterization["geographical_flexibility_index"].notna().sum()),
        len(scored),
    ],
})
display(coverage)

purpose_coverage = (
    characterization.groupby(["Purpose", "policy_flexible"], observed=True)
    .agg(
        segments=("segment_id", "size"),
        trips=("trips", "sum"),
        reliable_segments=("meets_reliability_filter", "sum"),
        temporal_scores=("temporal_flexibility_index", "count"),
        geographical_scores=("geographical_flexibility_index", "count"),
    )
    .reset_index().sort_values("trips", ascending=False)
)
display(purpose_coverage)
"""
))

cells.append(nbf.v4.new_markdown_cell("## 4. Marginal distributions of the two indices"))
cells.append(nbf.v4.new_code_cell(
"""index_columns = {
    "Temporal flexibility (T_s)": "temporal_flexibility_index",
    "Geographical flexibility (G_s)": "geographical_flexibility_index",
}

distribution_rows = []
for label, column in index_columns.items():
    values = scored[column].dropna()
    distribution_rows.append({
        "index": label,
        "n": len(values),
        "mean": values.mean(),
        "std": values.std(),
        "minimum": values.min(),
        "q25": values.quantile(0.25),
        "median": values.median(),
        "q75": values.quantile(0.75),
        "maximum": values.max(),
        "zero_share": values.eq(0).mean(),
    })
index_distribution = pd.DataFrame(distribution_rows)
display(index_distribution.style.format({
    "mean": "{:.4f}", "std": "{:.4f}", "minimum": "{:.4f}",
    "q25": "{:.4f}", "median": "{:.4f}", "q75": "{:.4f}",
    "maximum": "{:.4f}", "zero_share": "{:.1%}",
}))

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
for ax, (label, column) in zip(axes, index_columns.items()):
    ax.hist(scored[column], bins=25, color="#3977a8", edgecolor="white")
    ax.axvline(scored[column].median(), color="#b33b32", linestyle="--", label="Median")
    ax.set(title=label, xlabel="Index value", ylabel="Number of demand segments")
    ax.legend()
plt.tight_layout()
plt.show()
"""
))

cells.append(nbf.v4.new_code_cell(
"""purpose_distribution = (
    scored.groupby("Purpose", observed=True)
    .agg(
        segments=("segment_id", "size"),
        trips=("trips", "sum"),
        temporal_mean=("temporal_flexibility_index", "mean"),
        temporal_median=("temporal_flexibility_index", "median"),
        geographical_mean=("geographical_flexibility_index", "mean"),
        geographical_median=("geographical_flexibility_index", "median"),
        single_destination_share=("geographical_flexibility_index", lambda x: x.eq(0).mean()),
    )
    .reset_index().sort_values("trips", ascending=False)
)
display(purpose_distribution.style.format({
    "temporal_mean": "{:.4f}", "temporal_median": "{:.4f}",
    "geographical_mean": "{:.4f}", "geographical_median": "{:.4f}",
    "single_destination_share": "{:.1%}",
}))

fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
purpose_order = purpose_distribution["Purpose"].tolist()
for ax, column, title in [
    (axes[0], "temporal_flexibility_index", "Temporal flexibility by purpose"),
    (axes[1], "geographical_flexibility_index", "Geographical flexibility by purpose"),
]:
    data = [scored.loc[scored["Purpose"].eq(p), column].to_numpy() for p in purpose_order]
    ax.boxplot(data, labels=purpose_order, showfliers=False)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylabel("Index value")
plt.tight_layout()
plt.show()
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 5. Joint temporal-geographical characterization

The scatterplot keeps both indices continuous. For an interpretable operational
typology, temporal flexibility is split at its scored-segment median, while
geographical flexibility distinguishes a single observed destination ($G_s=0$)
from observed destination diversity ($G_s>0$).
"""
))
cells.append(nbf.v4.new_code_cell(
"""rho_tg, p_tg = spearmanr(
    scored["temporal_flexibility_index"],
    scored["geographical_flexibility_index"],
)
print(f"Spearman T_s vs G_s: rho={rho_tg:.3f}, p={p_tg:.4g}, n={len(scored):,}")

fig, ax = plt.subplots(figsize=(8, 6))
sizes = 18 + 110 * np.sqrt(scored["trips"] / scored["trips"].max())
scatter = ax.scatter(
    scored["temporal_flexibility_index"],
    scored["geographical_flexibility_index"],
    s=sizes, c=scored["cancellation_rate"], cmap="magma", alpha=0.68,
    edgecolor="white", linewidth=0.3,
)
ax.set(
    xlabel="Temporal flexibility index (T_s)",
    ylabel="Geographical flexibility index (G_s)",
    title="Joint flexibility distribution\\ncolor = contemporaneous cancellation rate; size = segment trips",
)
fig.colorbar(scatter, ax=ax, label="Cancellation rate")
plt.tight_layout()
plt.show()

temporal_median = scored["temporal_flexibility_index"].median()
scored["temporal_class"] = np.where(
    scored["temporal_flexibility_index"].ge(temporal_median),
    "Higher temporal flexibility", "Lower temporal flexibility",
)
scored["geographical_class"] = np.where(
    scored["geographical_flexibility_index"].gt(0),
    "Destination diversity observed", "Single destination observed",
)
scored["flexibility_type"] = (
    scored["temporal_class"] + " / " + scored["geographical_class"]
)

def grouped_outcome_summary(frame, group_columns):
    result = (
        frame.groupby(group_columns, observed=True)
        .agg(
            segments=("segment_id", "size"),
            trips=("trips", "sum"),
            outcome_trips=("outcome_trips", "sum"),
            completed_trips=("completed_trips", "sum"),
            cancelled_trips=("cancelled_trips", "sum"),
            temporal_mean=("temporal_flexibility_index", "mean"),
            geographical_mean=("geographical_flexibility_index", "mean"),
        )
        .reset_index()
    )
    result["weighted_completion_rate"] = result["completed_trips"] / result["outcome_trips"]
    result["weighted_cancellation_rate"] = result["cancelled_trips"] / result["outcome_trips"]
    return result

flexibility_typology = grouped_outcome_summary(scored, ["flexibility_type"])
display(flexibility_typology.style.format({
    "temporal_mean": "{:.4f}", "geographical_mean": "{:.4f}",
    "weighted_completion_rate": "{:.1%}", "weighted_cancellation_rate": "{:.1%}",
}))
"""
))

cells.append(nbf.v4.new_markdown_cell("## 6. Relationships with completion and cancellation"))
cells.append(nbf.v4.new_code_cell(
"""correlation_rows = []
for index_label, index_column in index_columns.items():
    for outcome_label, outcome_column in [
        ("Completion rate", "completion_rate"),
        ("Cancellation rate", "cancellation_rate"),
    ]:
        valid = scored[[index_column, outcome_column]].dropna()
        rho, p_value = spearmanr(valid[index_column], valid[outcome_column])
        correlation_rows.append({
            "index": index_label,
            "outcome": outcome_label,
            "segments": len(valid),
            "spearman_rho": rho,
            "p_value": p_value,
        })
correlations = pd.DataFrame(correlation_rows)
display(correlations.style.format({"spearman_rho": "{:.3f}", "p_value": "{:.4g}"}))

scored["temporal_quartile"] = pd.qcut(
    scored["temporal_flexibility_index"],
    q=4, labels=["Q1 lowest", "Q2", "Q3", "Q4 highest"], duplicates="drop",
)

positive_geo = scored["geographical_flexibility_index"].gt(0)
scored["geographical_group"] = "G=0 single destination"
if positive_geo.sum() >= 3:
    scored.loc[positive_geo, "geographical_group"] = pd.qcut(
        scored.loc[positive_geo, "geographical_flexibility_index"],
        q=3, labels=["G>0 lower", "G>0 middle", "G>0 higher"], duplicates="drop",
    ).astype("string")

temporal_bins = grouped_outcome_summary(scored, ["temporal_quartile"])
geographical_bins = grouped_outcome_summary(scored, ["geographical_group"])
display(temporal_bins.style.format({
    "temporal_mean": "{:.4f}", "geographical_mean": "{:.4f}",
    "weighted_completion_rate": "{:.1%}", "weighted_cancellation_rate": "{:.1%}",
}))
display(geographical_bins.style.format({
    "temporal_mean": "{:.4f}", "geographical_mean": "{:.4f}",
    "weighted_completion_rate": "{:.1%}", "weighted_cancellation_rate": "{:.1%}",
}))

fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
axes[0].plot(temporal_bins["temporal_quartile"].astype(str),
             temporal_bins["weighted_cancellation_rate"], marker="o")
axes[0].set(title="Cancellation across temporal-flexibility quartiles",
            xlabel="Temporal group", ylabel="Trip-weighted cancellation rate")
axes[0].tick_params(axis="x", rotation=25)
axes[1].plot(geographical_bins["geographical_group"].astype(str),
             geographical_bins["weighted_cancellation_rate"], marker="o")
axes[1].set(title="Cancellation across geographical-flexibility groups",
            xlabel="Geographical group", ylabel="Trip-weighted cancellation rate")
axes[1].tick_params(axis="x", rotation=25)
plt.tight_layout()
plt.show()
"""
))

cells.append(nbf.v4.new_code_cell(
"""purpose_outcomes = grouped_outcome_summary(scored, ["Purpose"])
weekday_outcomes = grouped_outcome_summary(scored, ["weekday"])
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
weekday_outcomes["weekday"] = pd.Categorical(
    weekday_outcomes["weekday"], categories=weekday_order, ordered=True
)
weekday_outcomes = weekday_outcomes.sort_values("weekday")

print("Purpose-level characterization")
display(purpose_outcomes.style.format({
    "temporal_mean": "{:.4f}", "geographical_mean": "{:.4f}",
    "weighted_completion_rate": "{:.1%}", "weighted_cancellation_rate": "{:.1%}",
}))
print("Weekday-level characterization")
display(weekday_outcomes.style.format({
    "temporal_mean": "{:.4f}", "geographical_mean": "{:.4f}",
    "weighted_completion_rate": "{:.1%}", "weighted_cancellation_rate": "{:.1%}",
}))
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""### Within-purpose association check

The overall index-outcome correlation can reflect differences in the mix of trip
purposes. The following table therefore repeats the Spearman calculation within
each purpose that has enough scored segments. This is a stratified descriptive
check, not a causal or predictive model.
"""
))
cells.append(nbf.v4.new_code_cell(
"""within_purpose_rows = []
for purpose, group in scored.groupby("Purpose", observed=True):
    if len(group) < 10:
        continue
    for index_label, index_column in index_columns.items():
        if group[index_column].nunique() < 2 or group["cancellation_rate"].nunique() < 2:
            rho, p_value = np.nan, np.nan
        else:
            rho, p_value = spearmanr(group[index_column], group["cancellation_rate"])
        within_purpose_rows.append({
            "Purpose": purpose,
            "index": index_label,
            "segments": len(group),
            "spearman_rho_with_cancellation": rho,
            "p_value": p_value,
        })
within_purpose_correlations = pd.DataFrame(within_purpose_rows)
display(within_purpose_correlations.style.format({
    "spearman_rho_with_cancellation": "{:.3f}", "p_value": "{:.4g}"
}))
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 7. Origin-grid characterization

Each origin zone is summarized across its scored purpose-weekday segments.
Index means are weighted by segment trip counts. Marker size represents scored
trip volume, so a visually high index based on little demand is not mistaken for
a major operating opportunity. These are grid maps, not street basemaps.
"""
))
cells.append(nbf.v4.new_code_cell(
"""scored_grid = scored.assign(
    temporal_weighted_total=(
        scored["trips"] * scored["temporal_flexibility_index"]
    ),
    geographical_weighted_total=(
        scored["trips"] * scored["geographical_flexibility_index"]
    ),
)
origin_grid = (
    scored_grid.groupby("origin_zone", observed=True)
    .agg(
        scored_segments=("segment_id", "size"),
        scored_trips=("trips", "sum"),
        temporal_weighted_total=("temporal_weighted_total", "sum"),
        geographical_weighted_total=("geographical_weighted_total", "sum"),
        outcome_trips=("outcome_trips", "sum"),
        cancelled_trips=("cancelled_trips", "sum"),
    )
    .reset_index()
)
origin_grid["temporal_weighted_mean"] = (
    origin_grid["temporal_weighted_total"] / origin_grid["scored_trips"]
)
origin_grid["geographical_weighted_mean"] = (
    origin_grid["geographical_weighted_total"] / origin_grid["scored_trips"]
)
origin_grid["weighted_cancellation_rate"] = (
    origin_grid["cancelled_trips"] / origin_grid["outcome_trips"]
)
origin_grid = origin_grid.drop(columns=[
    "temporal_weighted_total", "geographical_weighted_total"
])
zone_parts = origin_grid["origin_zone"].str.extract(r"r(?P<row>-?\d+)_c(?P<col>-?\d+)").astype(int)
origin_grid = pd.concat([origin_grid, zone_parts], axis=1)
origin_grid["longitude_center"] = metadata["longitude_origin"] + (origin_grid["col"] + 0.5) * metadata["longitude_step"]
origin_grid["latitude_center"] = metadata["latitude_origin"] + (origin_grid["row"] + 0.5) * metadata["latitude_step"]

fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharex=True, sharey=True)
for ax, column, title, cmap in [
    (axes[0], "temporal_weighted_mean", "Trip-weighted temporal flexibility", "viridis"),
    (axes[1], "geographical_weighted_mean", "Trip-weighted geographical flexibility", "plasma"),
]:
    sizes = 20 + 260 * np.sqrt(origin_grid["scored_trips"] / origin_grid["scored_trips"].max())
    points = ax.scatter(
        origin_grid["longitude_center"], origin_grid["latitude_center"],
        c=origin_grid[column], s=sizes, cmap=cmap, alpha=0.8,
        edgecolor="black", linewidth=0.25,
    )
    ax.set(title=title, xlabel="Longitude", ylabel="Latitude", aspect="equal")
    fig.colorbar(points, ax=ax, label="Weighted index")
plt.tight_layout()
plt.show()

display(origin_grid.nlargest(15, "scored_trips").style.format({
    "temporal_weighted_mean": "{:.4f}", "geographical_weighted_mean": "{:.4f}",
    "weighted_cancellation_rate": "{:.1%}",
    "longitude_center": "{:.4f}", "latitude_center": "{:.4f}",
}))
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 8. Segments for operational interpretation

The tables below retain the two indices separately. `temporal_demand_opportunity`
and `geographical_demand_opportunity` multiply the relevant index by historical
trip volume. Completion and cancellation do not enter either opportunity measure.
"""
))
cells.append(nbf.v4.new_code_cell(
"""scored["temporal_demand_opportunity"] = scored["trips"] * scored["temporal_flexibility_index"]
scored["geographical_demand_opportunity"] = scored["trips"] * scored["geographical_flexibility_index"]

interpretation_columns = [
    "segment_id", "Purpose", "origin_zone", "weekday", "trips",
    "temporal_flexibility_index", "geographical_flexibility_index",
    "temporal_demand_opportunity", "geographical_demand_opportunity",
    "completion_rate", "cancellation_rate", "flexibility_type",
]
print("Highest temporal demand opportunity")
display(scored.nlargest(15, "temporal_demand_opportunity")[interpretation_columns])
print("Highest geographical demand opportunity")
display(scored.nlargest(15, "geographical_demand_opportunity")[interpretation_columns])
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## 9. Save the characterization tables

The exported segment table supports later filtering and follow-up analysis. It
contains outcomes for description, but no outcome field is used to construct
either flexibility index or either demand-opportunity measure.
"""
))
cells.append(nbf.v4.new_code_cell(
"""SEGMENT_OUTPUT = PROJECT_DIR / "two_index_characterization_segments.csv"
ORIGIN_OUTPUT = PROJECT_DIR / "two_index_characterization_origin_grids.csv"

scored.sort_values(["Purpose", "origin_zone", "weekday"]).to_csv(SEGMENT_OUTPUT, index=False)
origin_grid.sort_values("scored_trips", ascending=False).to_csv(ORIGIN_OUTPUT, index=False)

print(f"Saved: {SEGMENT_OUTPUT.name}")
print(f"Saved: {ORIGIN_OUTPUT.name}")
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Interpretation guardrails and next step

1. These indices summarize observed historical distributions; they do not prove
   that an individual rider will accept a proposed time or destination change.
2. Same-period outcome associations can reflect purpose, weekday, demand volume,
   service conditions, or cancellation mechanisms. They are not causal effects.
3. Completion and cancellation are complements when the denominator contains only
   those two statuses, so their correlations mirror one another.
4. A later validation can estimate flexibility from an earlier period and examine
   outcomes in a later period. That temporal validation is intentionally outside
   the scope of this contemporaneous notebook.
"""
))

nb["cells"] = cells
nbf.write(nb, NOTEBOOK_PATH)
print(f"Built {NOTEBOOK_PATH}")
