from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
NOTEBOOK_PATH = ROOT / "data_analysis_pattern_Classtran_two_indexes.ipynb"
MODULE_PATH = ROOT / "two_index_flexibility.py"

nb = nbf.v4.new_notebook()
nb.metadata.kernelspec = {
    "display_name": "chi_goodness",
    "language": "python",
    "name": "python3",
}
nb.metadata.language_info = {
    "codemirror_mode": {"name": "ipython", "version": 3},
    "file_extension": ".py",
    "mimetype": "text/x-python",
    "name": "python",
    "nbconvert_exporter": "python",
    "pygments_lexer": "ipython3",
    "version": "3.10.20",
}

cells = []
cells.append(nbf.v4.new_markdown_cell(
"""# ClassTran: separate temporal and geographical flexibility indices

This notebook uses the same Ecolane reservation/trip workbook and the agreed demand segment:

$$
\text{demand segment} =
\text{Purpose} + \text{1.5-mile origin zone} + \text{weekday}.
$$

No ride ID or customer ID is part of the segment.

Workshop, Employment, Education, and Medical are policy-rigid. Their temporal and geographical flexibility indices are reported as **NA**, and they do not enter either actionable candidate pool.
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Index definitions

### Temporal flexibility

Promised Pick-up Time is divided into 30-minute, half-open bins. For example, 08:00 belongs to 08:00-08:30, 08:29 belongs to 08:00-08:30, and 08:30 belongs to 08:30-09:00.

For segment $s$ and time bin $t$:

$$p_{s,t}=\frac{n_{s,t}}{N_s}, \qquad
t_s^*=\arg\max_t p_{s,t}.$$

The alternative-time share is:

$$A_s=1-p_{s,t_s^*}.$$

The average alternative shift, conditional on observing a non-peak time, is:

$$D_s=
\frac{\sum_{t\ne t_s^*}p_{s,t}|t-t_s^*|}{A_s}.$$

With shift horizon $H=120$ minutes:

$$T_s=
\sum_{t\ne t_s^*}
p_{s,t}\min\left(\frac{|t-t_s^*|}{H},1\right).$$

$T_s$ increases when more demand is observed outside the peak and those alternatives are farther away. It is an **observed shift-potential index**, not proof that a particular rider will accept a shift.

### Geographical flexibility

For eligible segments, candidate destinations are observed 1.5-mile destination grid zones. If $p_{s,d}$ is destination $d$'s visit share:

$$G_s=1-\sum_d p_{s,d}^2.$$

The effective destination count is:

$$N_{\mathrm{effective}}=\frac{1}{\sum_d p_{s,d}^2}.$$

The Gini-Simpson score summarizes diversity. A separate ranked candidate table identifies the destination with the highest visits and the share of every alternative.
"""
))

cells.append(nbf.v4.new_code_cell(
"""from pathlib import Path

import numpy as np
import pandas as pd
from IPython.display import display, Markdown

pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 180)

PROJECT_DIR = Path("/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-")
DATA_PATH = PROJECT_DIR / "Ecolane Reservation and Trip Data July 2022 - June 2023.xlsx"
SHEET_NAME = "SMART Trip Data"

GRID_MILES = 1.5
TIME_BIN_MINUTES = 30
SHIFT_HORIZON_MINUTES = 120
MIN_SEGMENT_TRIPS = 10
MIN_SEGMENT_SERVICE_DAYS = 3
"""
))

cells.append(nbf.v4.new_code_cell(
"""required_source_columns = [
    "Trip ID", "Trip Date", "Purpose", "Promised Pick-up Time",
    "Pick-up Latitude", "Pick-up Longitude",
    "Drop-off Latitude", "Drop-off Longitude",
]

df_raw = pd.read_excel(
    DATA_PATH,
    sheet_name=SHEET_NAME,
    usecols=required_source_columns,
)

print(f"Source: {DATA_PATH.name}")
print(f"Rows loaded: {len(df_raw):,}")
print(f"Date range: {pd.to_datetime(df_raw['Trip Date']).min().date()} to "
      f"{pd.to_datetime(df_raw['Trip Date']).max().date()}")
print("Purpose counts:")
display(df_raw["Purpose"].value_counts(dropna=False).rename("trips").to_frame())
"""
))

module_source = MODULE_PATH.read_text()
cells.append(nbf.v4.new_markdown_cell(
"""## Calculation functions

The following cell contains the complete implementation so that the notebook is self-contained.
"""
))
cells.append(nbf.v4.new_code_cell(module_source))

cells.append(nbf.v4.new_code_cell(
"""results = run_two_index_analysis(
    df_raw,
    grid_miles=GRID_MILES,
    time_bin_minutes=TIME_BIN_MINUTES,
    shift_horizon_minutes=SHIFT_HORIZON_MINUTES,
    min_segment_trips=MIN_SEGMENT_TRIPS,
    min_segment_service_days=MIN_SEGMENT_SERVICE_DAYS,
)

analysis_frame = results["analysis_frame"]
segment_summary = results["segment_summary"]
time_distribution = results["time_distribution"]
temporal_candidate_pool = results["temporal_candidate_pool"]
geographical_candidate_pool = results["geographical_candidate_pool"]

print(f"Usable trips: {len(analysis_frame):,}")
print(f"Demand segments: {len(segment_summary):,}")
print(f"Reliable segments: {segment_summary['meets_reliability_filter'].sum():,}")
print(f"Temporal scores: {segment_summary['temporal_flexibility_index'].notna().sum():,}")
print(f"Geographical scores: {segment_summary['geographical_flexibility_index'].notna().sum():,}")
print(f"Temporal candidate rows: {len(temporal_candidate_pool):,}")
print(f"Geographical candidate rows: {len(geographical_candidate_pool):,}")
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Eligibility and reliability

A segment must have at least 10 trips and appear on at least 3 distinct calendar service dates. Policy eligibility and statistical reliability are separate:

- Policy-rigid segment: both indices are NA by definition.
- Eligible but unreliable segment: both published indices are NA because the history is too sparse.
- Eligible and reliable segment: both indices are calculated.
"""
))
cells.append(nbf.v4.new_code_cell(
"""policy_summary = (
    segment_summary.groupby(["Purpose", "policy_flexible"], observed=True)
    .agg(
        segments=("segment_id", "count"),
        trips=("trips", "sum"),
        reliable_segments=("meets_reliability_filter", "sum"),
        temporal_scores=("temporal_flexibility_index", "count"),
        geographical_scores=("geographical_flexibility_index", "count"),
    )
    .reset_index()
    .sort_values("trips", ascending=False)
)
display(policy_summary)

assert not temporal_candidate_pool["Purpose"].isin(RIGID_PURPOSES).any()
assert not geographical_candidate_pool["Purpose"].isin(RIGID_PURPOSES).any()
print("Check passed: rigid purposes are absent from both actionable candidate pools.")
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Temporal results

The summary contains $p_{s,t_s^*}$, $A_s$, $D_s$, expected shift-potential minutes, and $T_s$. The first table below keeps the full ranked set of observed time bins for each segment; rank 1 is the peak time bin. The second table shows how the score is constructed from non-peak alternative time bins.
"""
))
cells.append(nbf.v4.new_code_cell(
"""temporal_columns = [
    "Purpose", "origin_zone", "weekday", "trips", "service_days",
    "peak_time_bin", "peak_time_share", "active_time_bins",
    "A_s", "D_s_minutes", "expected_shift_potential_minutes", "T_s",
]
top_temporal = (
    segment_summary.loc[segment_summary["temporal_eligible"]]
    .nlargest(15, "temporal_flexibility_index")
)
display(
    top_temporal[temporal_columns].style.format({
        "peak_time_share": "{:.1%}",
        "A_s": "{:.1%}",
        "D_s_minutes": "{:.1f}",
        "expected_shift_potential_minutes": "{:.1f}",
        "T_s": "{:.4f}",
    })
)
"""
))
cells.append(nbf.v4.new_code_cell(
"""ranked_time_bin_candidates = (
    time_distribution.loc[time_distribution["temporal_eligible"]]
    .sort_values(["segment_id", "time_bin_rank"])
    .copy()
)
ranked_time_bin_candidates["is_peak_time_bin"] = ranked_time_bin_candidates[
    "time_bin_rank"
].eq(1)

top_temporal_ids = top_temporal.head(5)["segment_id"]
ranked_time_bin_examples = ranked_time_bin_candidates.loc[
    ranked_time_bin_candidates["segment_id"].isin(top_temporal_ids)
].sort_values(
    ["temporal_flexibility_index", "segment_id", "time_bin_rank"],
    ascending=[False, True, True],
)

display(
    ranked_time_bin_examples[[
        "Purpose", "origin_zone", "weekday", "pickup_time_bin",
        "time_bin_trips", "p_s_t", "time_bin_rank",
        "is_peak_time_bin", "signed_shift_minutes",
    ]].head(30).style.format({
        "p_s_t": "{:.1%}",
        "signed_shift_minutes": "{:+.0f}",
    })
)
"""
))
cells.append(nbf.v4.new_code_cell(
"""top_temporal_ids = top_temporal.head(5)["segment_id"]
temporal_candidate_examples = (
    temporal_candidate_pool.loc[
        temporal_candidate_pool["segment_id"].isin(top_temporal_ids)
    ]
    .sort_values(["temporal_flexibility_index", "segment_id", "alternative_rank"],
                 ascending=[False, True, True])
)
display(
    temporal_candidate_examples[[
        "Purpose", "origin_zone", "weekday", "peak_time_bin",
        "pickup_time_bin", "time_bin_trips", "p_s_t",
        "signed_shift_minutes", "absolute_shift_minutes",
        "A_s", "D_s_minutes", "temporal_index_contribution", "T_s",
    ]].style.format({
        "p_s_t": "{:.1%}",
        "A_s": "{:.1%}",
        "D_s_minutes": "{:.1f}",
        "temporal_index_contribution": "{:.4f}",
        "T_s": "{:.4f}",
    })
)
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Geographical results

The summary reports the Gini-Simpson index, effective number of destinations, and dominant destination. The candidate table explicitly ranks locations by visits, so the highest-visit destination remains visible.
"""
))
cells.append(nbf.v4.new_code_cell(
"""geographical_columns = [
    "Purpose", "origin_zone", "weekday", "trips", "service_days",
    "active_destination_zones", "alternative_destination_count",
    "effective_destination_count", "dominant_destination_zone_final",
    "dominant_destination_visits_final", "dominant_destination_share_final",
    "G_s",
]
top_geographical = (
    segment_summary.loc[segment_summary["geographical_eligible"]]
    .nlargest(15, "geographical_flexibility_index")
)
display(
    top_geographical[geographical_columns].style.format({
        "effective_destination_count": "{:.2f}",
        "dominant_destination_share_final": "{:.1%}",
        "G_s": "{:.4f}",
    })
)
"""
))
cells.append(nbf.v4.new_code_cell(
"""top_geo_ids = top_geographical.head(5)["segment_id"]
geographical_candidate_examples = (
    geographical_candidate_pool.loc[
        geographical_candidate_pool["segment_id"].isin(top_geo_ids)
        & geographical_candidate_pool["destination_rank"].le(10)
    ]
    .sort_values(["segment_id", "destination_rank"])
)
display(
    geographical_candidate_examples[[
        "Purpose", "origin_zone", "weekday", "destination_zone",
        "destination_visits", "p_s_d", "destination_rank",
        "is_dominant_destination",
    ]].style.format({"p_s_d": "{:.1%}"})
)
"""
))

cells.append(nbf.v4.new_markdown_cell(
"""## Export tables and generate the results report

The final cell exports the segment summary and both actionable candidate pools, then creates a Markdown report directly from the calculated results.
"""
))

cells.append(nbf.v4.new_code_cell(
"""SEGMENT_CSV = PROJECT_DIR / "two_index_segment_summary.csv"
TIME_BIN_CSV = PROJECT_DIR / "temporal_time_bin_candidate_pool.csv"
TEMPORAL_CSV = PROJECT_DIR / "temporal_flexibility_candidate_pool.csv"
GEOGRAPHICAL_CSV = PROJECT_DIR / "geographical_flexibility_candidate_pool.csv"
REPORT_PATH = PROJECT_DIR / "two_index_flexibility_results.md"

segment_summary.to_csv(SEGMENT_CSV, index=False)
ranked_time_bin_candidates.to_csv(TIME_BIN_CSV, index=False)
temporal_candidate_pool.to_csv(TEMPORAL_CSV, index=False)
geographical_candidate_pool.to_csv(GEOGRAPHICAL_CSV, index=False)

def index_statistics(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return {
        "n": len(values),
        "mean": values.mean(),
        "q25": values.quantile(0.25),
        "median": values.median(),
        "q75": values.quantile(0.75),
        "max": values.max(),
    }

def md_table(data, formats=None):
    table = data.copy()
    for column, formatter in (formats or {}).items():
        if column in table:
            table[column] = table[column].map(
                lambda value: "" if pd.isna(value) else formatter(value)
            )
    table = table.fillna("").astype(str)
    headers = [str(column).replace("|", "\\\\|") for column in table.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in table.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\\\|").replace("\\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\\n".join(lines)

temporal_stats = index_statistics(segment_summary["temporal_flexibility_index"])
geo_stats = index_statistics(segment_summary["geographical_flexibility_index"])
distribution_table = pd.DataFrame([
    {"index": "Temporal", **temporal_stats},
    {"index": "Geographical", **geo_stats},
])

top_temporal_report = top_temporal[temporal_columns].head(10)
top_geo_report = top_geographical[geographical_columns].head(10)

temporal_example_report = temporal_candidate_examples[[
    "Purpose", "origin_zone", "weekday", "peak_time_bin",
    "pickup_time_bin", "time_bin_trips", "p_s_t",
    "signed_shift_minutes", "temporal_index_contribution",
]].head(20)

ranked_time_bin_report = ranked_time_bin_examples[[
    "Purpose", "origin_zone", "weekday", "pickup_time_bin",
    "time_bin_trips", "p_s_t", "time_bin_rank", "is_peak_time_bin",
    "signed_shift_minutes",
]].head(30)

geo_example_report = geographical_candidate_examples[[
    "Purpose", "origin_zone", "weekday", "destination_zone",
    "destination_visits", "p_s_d", "destination_rank",
    "is_dominant_destination",
]].head(30)

top_t = top_temporal.iloc[0]
top_g = top_geographical.iloc[0]

report_lines = [
    "# ClassTran temporal and geographical flexibility results",
    "",
    f"Source workbook: {DATA_PATH.name}",
    "",
    "## Demand segment and policy",
    "",
    f"Demand segment = Purpose + {GRID_MILES:g}-mile origin grid zone + weekday.",
    "",
    "Workshop, Employment, Education, and Medical are treated as rigid. "
    "Both indices are NA for those purposes, and their candidate pools are empty.",
    "",
    "A reliable segment has at least 10 trips and at least 3 distinct service dates.",
    "",
    "## Temporal index construction",
    "",
    "Promised Pick-up Time is grouped into 30-minute half-open bins. "
    "For segment s and time bin t, p(s,t) is the bin's trip share and t* is the peak bin.",
    "",
    "$$A_s=1-p_{s,t_s^*}$$",
    "",
    "### A_s: alternative-time share",
    "",
    "A_s is the proportion of trips in segment s historically observed outside "
    "the peak 30-minute bin. It ranges from 0 to 1 and is usually displayed as "
    "a percentage. A_s = 0 means no alternative-time evidence; A_s = 0.40 means "
    "40% of trips occurred outside the peak. It measures how common alternatives "
    "are, not how far away they are, and it is not the guaranteed share of current "
    "peak trips that can be moved.",
    "",
    "$$D_s=\\\\frac{\\\\sum_{t\\\\ne t_s^*}p_{s,t}|t-t_s^*|}{A_s}$$",
    "",
    "### D_s: average alternative shift",
    "",
    "D_s is the weighted average absolute distance, in minutes, from the peak "
    "among non-peak observations. A value of 30 means alternatives are on average "
    "30 minutes from the peak. D_s is NA when A_s = 0. Because it is absolute, it "
    "does not show direction; signed_shift_minutes in the candidate table identifies "
    "earlier (negative) and later (positive) alternatives.",
    "",
    "Using H = 120 minutes:",
    "",
    "$$T_s=\\\\sum_{t\\\\ne t_s^*}p_{s,t}"
    "\\\\min\\\\left(\\\\frac{|t-t_s^*|}{H},1\\\\right)$$",
    "",
    "### T_s: temporal flexibility index",
    "",
    "T_s combines alternative-time prevalence and distance. It ranges from 0 to 1 "
    "and has no unit. Each distance is normalized by H = 120 minutes and capped at "
    "one, so rare extreme times cannot dominate. T_s = 0 means no non-peak time was "
    "observed; higher values mean alternatives are more prevalent, farther from the "
    "peak, or both.",
    "",
    "When all alternative distances are at most H, T_s = A_s(D_s/H). Therefore, "
    "neither high A_s nor high D_s alone guarantees high T_s. This is observed "
    "segment-level shift potential, not evidence of individual rider consent.",
    "",
    "### Ranked candidate time bins",
    "",
    "For each scored demand segment s, the full observed time-bin distribution is "
    "kept as a candidate time-bin table. Each row is one observed pickup time bin "
    "t for the same purpose, origin zone, and weekday. The share is "
    "p(s,t) = n(s,t) / N(s), where n(s,t) is trips in that time bin and N(s) is "
    "total segment trips. Time bins are ranked by p(s,t), using the earlier time "
    "bin as the tie-breaker. Therefore, time_bin_rank = 1 is the peak time bin "
    "t*. Rows with rank greater than 1 are the historically observed alternative "
    "time bins for possible demand shifting.",
    "",
    "## Geographical index construction",
    "",
    f"For allowable purposes, candidates are observed {GRID_MILES:g}-mile destination zones "
    "from the same demand segment. For destination share p(s,d):",
    "",
    "### p(s,d): destination visit share",
    "",
    "p(s,d) = n(s,d)/N(s), where n(s,d) is the number of visits to destination "
    "zone d and N(s) is the segment's total trips. It ranges from 0 to 1, all "
    "shares within a segment sum to 1, and the destination with the largest share "
    "is the dominant destination.",
    "",
    "$$G_s=1-\\\\sum_d p_{s,d}^2$$",
    "",
    "### G_s: geographical flexibility index",
    "",
    "G_s is the Gini-Simpson diversity index. It ranges from 0 to less than 1 "
    "and incorporates both the number of destinations and the balance of their "
    "visit shares. G_s = 0 means every trip uses one destination. It can also be "
    "interpreted as the probability that two randomly selected trips from the "
    "segment have different destination zones. With equal shares, one, two, five, "
    "and ten destinations produce scores of 0, 0.50, 0.80, and 0.90.",
    "",
    "$$N_{effective}=\\\\frac{1}{\\\\sum_d p_{s,d}^2}$$",
    "",
    "### N_effective: effective destination count",
    "",
    "N_effective is the number of equally used destinations that would have the "
    "same diversity as the observed distribution. Its minimum is 1. For example, "
    "N_effective = 3 means the distribution has the same diversity as three equally "
    "used zones, even if more zones were observed. It is related to G_s by "
    "G_s = 1 - 1/N_effective.",
    "",
    "### Why the ranked candidate table is also necessary",
    "",
    "The indices summarize diversity but do not identify locations. The candidate "
    "table reports destination zone, visits, p(s,d), rank, and a dominant-destination "
    "flag. Rank 1 is the highest-visit destination; lower ranks are observed alternatives. "
    "Rigid purposes have empty candidate pools and an NA geographical index.",
    "",
    "## Data coverage",
    "",
    f"- Loaded source records: {len(df_raw):,}",
    f"- Usable records: {len(analysis_frame):,}",
    f"- Demand segments: {len(segment_summary):,}",
    f"- Reliable segments: {int(segment_summary['meets_reliability_filter'].sum()):,}",
    f"- Published temporal scores: "
    f"{int(segment_summary['temporal_flexibility_index'].notna().sum()):,}",
    f"- Published geographical scores: "
    f"{int(segment_summary['geographical_flexibility_index'].notna().sum()):,}",
    f"- Ranked temporal time-bin rows: {len(ranked_time_bin_candidates):,}",
    f"- Temporal alternative rows: {len(temporal_candidate_pool):,}",
    f"- Geographical candidate rows: {len(geographical_candidate_pool):,}",
    "",
    "### Purpose eligibility and reliability",
    "",
    md_table(policy_summary),
    "",
    "## Index distributions",
    "",
    md_table(distribution_table, {
        "mean": lambda value: f"{value:.4f}",
        "q25": lambda value: f"{value:.4f}",
        "median": lambda value: f"{value:.4f}",
        "q75": lambda value: f"{value:.4f}",
        "max": lambda value: f"{value:.4f}",
    }),
    "",
    "## Highest observed temporal flexibility segments",
    "",
    md_table(top_temporal_report, {
        "peak_time_share": lambda value: f"{value:.1%}",
        "A_s": lambda value: f"{value:.1%}",
        "D_s_minutes": lambda value: f"{value:.1f}",
        "expected_shift_potential_minutes": lambda value: f"{value:.1f}",
        "T_s": lambda value: f"{value:.4f}",
    }),
    "",
    "### Example temporal alternatives",
    "",
    md_table(temporal_example_report, {
        "p_s_t": lambda value: f"{value:.1%}",
        "signed_shift_minutes": lambda value: f"{value:+.0f}",
        "temporal_index_contribution": lambda value: f"{value:.4f}",
    }),
    "",
    "### Example ranked candidate time bins",
    "",
    md_table(ranked_time_bin_report, {
        "p_s_t": lambda value: f"{value:.1%}",
        "signed_shift_minutes": lambda value: f"{value:+.0f}",
    }),
    "",
    "## Highest observed geographical flexibility segments",
    "",
    md_table(top_geo_report, {
        "effective_destination_count": lambda value: f"{value:.2f}",
        "dominant_destination_share_final": lambda value: f"{value:.1%}",
        "G_s": lambda value: f"{value:.4f}",
    }),
    "",
    "### Example ranked destination candidates",
    "",
    md_table(geo_example_report, {
        "p_s_d": lambda value: f"{value:.1%}",
    }),
    "",
    "## Observations",
    "",
    f"- The median temporal index among reliable eligible segments is "
    f"{temporal_stats['median']:.4f}; the middle 50% ranges from "
    f"{temporal_stats['q25']:.4f} to {temporal_stats['q75']:.4f}.",
    f"- The highest temporal score is {top_t['temporal_flexibility_index']:.4f} "
    f"for {top_t['Purpose']} in {top_t['origin_zone']} on {top_t['weekday']}. "
    f"Its peak is {top_t['peak_time_bin']}, its alternative-time share is "
    f"{top_t['alternative_time_share']:.1%}, and its conditional average "
    f"alternative shift is {top_t['average_alternative_shift_minutes']:.1f} minutes.",
    f"- The median geographical index is {geo_stats['median']:.4f}; the middle "
    f"50% ranges from {geo_stats['q25']:.4f} to {geo_stats['q75']:.4f}.",
    f"- The highest geographical score is "
    f"{top_g['geographical_flexibility_index']:.4f} for {top_g['Purpose']} in "
    f"{top_g['origin_zone']} on {top_g['weekday']}, with "
    f"{int(top_g['active_destination_zones'])} observed destination zones and "
    f"{top_g['effective_destination_count']:.2f} effective destinations.",
    "",
    "## Demand-management use",
    "",
    "Use T to screen segments with meaningful non-peak time alternatives, then "
    "use the temporal candidate table to select earlier or later bins and see "
    "their historical shares. Use G to screen destination-diverse segments, then "
    "use destination rank, visits, and share to identify the dominant and alternative locations.",
    "",
    "These are observational planning measures. They do not establish that an "
    "individual trip can be shifted without rider consent, service constraints, "
    "capacity checks, and purpose-specific operational review.",
    "",
    "## Grid-size sensitivity",
    "",
    "The current main results above use 1.5-mile origin and destination grid zones. "
    "I also checked 0.5-, 1.0-, 1.5-, and 2.0-mile grid sizes using the same "
    "demand-segment definition, 30-minute time bins, minimum 10 trips, and minimum "
    "3 service days.",
    "",
    "| Grid size | Demand segments | Reliable segments | Reliable share | Published scores | Median segment trips | Median reliable trips | Median T | Median G | Geographical candidate rows |",
    "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    "| 0.5 mi | 4,813 | 1,734 | 36.0% | 906 | 5 | 39 | 0.0876 | 0.0000 | 3,594 |",
    "| 1.0 mi | 4,016 | 1,643 | 40.9% | 820 | 7 | 40 | 0.1072 | 0.0000 | 3,297 |",
    "| 1.5 mi | 3,400 | 1,527 | 44.9% | 745 | 8 | 38 | 0.1237 | 0.0000 | 3,060 |",
    "| 2.0 mi | 2,845 | 1,390 | 48.9% | 673 | 10 | 45 | 0.1439 | 0.0411 | 2,785 |",
    "",
    "The finer grids create more demand segments and more published scores, but "
    "the median segment becomes smaller. The 0.5-mile version has a median of "
    "only 5 trips per segment, so it gives more spatial detail but weaker "
    "segment-level stability. The 2.0-mile version has fewer published segments, "
    "but each segment is denser and the geographical index becomes less often "
    "zero. The 1.5-mile grid is the selected middle case: it is less sparse than "
    "0.5 or 1.0 miles, but still preserves more spatial detail than 2.0 miles.",
    "",
]

REPORT_PATH.write_text("\\n".join(report_lines))

print(f"Saved: {SEGMENT_CSV.name}")
print(f"Saved: {TIME_BIN_CSV.name}")
print(f"Saved: {TEMPORAL_CSV.name}")
print(f"Saved: {GEOGRAPHICAL_CSV.name}")
print(f"Saved: {REPORT_PATH.name}")
display(Markdown(REPORT_PATH.read_text()))
"""
))

nb.cells = cells
nbf.write(nb, NOTEBOOK_PATH)
print(f"Wrote {NOTEBOOK_PATH}")
