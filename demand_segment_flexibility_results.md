# Demand-Segment Flexibility Results

Generated from the executed `data_analysis_pattern_Classtran_new.ipynb` using the current multiplicative demand-flexibility index.

## Current Setup

The demand segment is:

```text
demand_segment = purpose + 1-mile origin grid zone + weekday
```

The time component currently uses:

```text
30-minute pickup time bin from Earliest Pick-up
```

Each bin is a half-open interval:

```text
07:00 bin = [07:00, 07:30)
07:30 bin = [07:30, 08:00)
14:00 bin = [14:00, 14:30)
14:30 bin = [14:30, 15:00)
```

So `14:17` is assigned to the `14:00` bin, while `14:30` is assigned to the `14:30` bin.

The interactive pattern is:

```text
pickup time bin + destination grid zone
```

The final index is multiplicative:

```text
interactive_flexibility_index =
    interactive_diversity_index * density_weight
```

where:

```text
interactive_diversity_index =
    entropy-derived effective number of time-destination pairs,
    normalized by possible pairs in the same purpose-weekday context

density_weight =
    log-scaled segment trip density,
    capped at 100 trips
```

This means both conditions are required: a segment needs observed time-destination alternatives and enough historical density to support those alternatives.

Current run summary:

```text
valid trip rows: 121,281
all demand segments: 4,016
reliable segments: 1,643
```

Reliable segments use:

```text
minimum segment trips: 10
minimum service days: 3
density reference trips: 100
```

Metric definitions:

```text
trips =
    total number of trip records in the demand segment

service_days =
    number of distinct calendar dates observed for the demand segment

min_segment_trips =
    minimum total trips required before trusting the segment pattern

min_segment_service_days =
    minimum distinct dates required before treating the pattern as repeatable

meets_reliability_filter =
    trips >= min_segment_trips
    and service_days >= min_segment_service_days
```

With the current threshold, reliable segments by weekday are:

```text
Monday       313
Tuesday      353
Wednesday    334
Thursday     347
Friday       296
Saturday       0
Sunday         0
```

Weekend records exist, but they remain too sparse to pass the reliability filter.

## Maps

The notebook generates one aggregate map and separate weekday maps:

| Map | File |
|---|---|
| Aggregate | [demand_segment_origin_grid_flexibility_map.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map.png) |
| Monday | [demand_segment_origin_grid_flexibility_map_monday.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map_monday.png) |
| Tuesday | [demand_segment_origin_grid_flexibility_map_tuesday.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map_tuesday.png) |
| Wednesday | [demand_segment_origin_grid_flexibility_map_wednesday.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map_wednesday.png) |
| Thursday | [demand_segment_origin_grid_flexibility_map_thursday.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map_thursday.png) |
| Friday | [demand_segment_origin_grid_flexibility_map_friday.png](/scratch/umni5/a/li5125/DOE_analysis/RFI-Rider_flexibility_index-/demand_segment_origin_grid_flexibility_map_friday.png) |

The aggregate map averages across all weekday-specific segments in the same origin grid. The weekday maps show only reliable segments for that weekday.

## 1. Relationship With Completion

The current relationship between flexibility bands and completion/cancellation is:

| Flexibility band | Segments | Trips | Mean flexibility index | Mean diversity | Mean density | Completion rate | Cancellation rate | Mean peak share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Q1 lowest | 329 | 16,498 | 0.0004 | 0.0006 | 0.7995 | 61.1% | 34.5% | 92.9% |
| Q2 | 328 | 12,132 | 0.0021 | 0.0031 | 0.7200 | 55.2% | 41.3% | 62.2% |
| Q3 | 329 | 16,068 | 0.0039 | 0.0054 | 0.7664 | 51.8% | 44.1% | 52.2% |
| Q4 | 328 | 17,089 | 0.0073 | 0.0098 | 0.7876 | 49.0% | 48.7% | 49.6% |
| Q5 highest | 329 | 50,795 | 0.0277 | 0.0331 | 0.8390 | 54.4% | 43.9% | 47.5% |

Peak-share definitions:

```text
time_peak_share =
    within one demand segment,
    the share of trips in the most common 30-minute pickup time bin

mean_time_peak_share =
    within one flexibility band,
    the average time_peak_share across all segments in that band
```

For example, if a segment has 100 trips and 80 of them occur in the 14:00 pickup bin:

```text
time_peak_share = 80 / 100 = 80%
```

Main observations:

1. Higher-flexibility bands have lower peak concentration. Q1 has a mean peak share of 92.9%, while Q5 has 47.5%. This supports the demand-management idea: flexible segments are less locked into one pickup time bin.

2. Completion does not increase with flexibility. Completion is highest in Q1 and lower in Q2-Q5. This suggests that the index is finding operational variability and possible shift opportunities, not simply better-performing demand.

Interpretation:

```text
low flexibility:
    dense or stable demand with little observed time-destination substitutability

high flexibility:
    demand with observed alternatives and enough density to trust the pattern

high flexibility + high peak share:
    strongest candidate for flattening interventions
```

## 2. Demand Management To Make Schedules Flatter

For schedule flattening, we do not need completion or cancellation rates in the demand-management table. The operational question is:

```text
Can trips in the peak pickup-time bin be offered another observed pickup-time bin
within the same purpose + origin zone + weekday segment?
```

The demand-management priority is:

```text
demand_management_priority =
    interactive_flexibility_index * time_peak_share
```

This gives priority to segments that have both:

```text
observed interactive flexibility
and
strong pickup-time peak concentration
```

Top current candidates for flattening:

| Purpose | Origin zone | Weekday | Trips | Service days | Flexibility index | Diversity | Density | Peak time | Time peak share |
|---|---|---|---:|---:|---:|---:|---:|---|---:|
| Workshop | r38_c21 | Friday | 232 | 52 | 0.1358 | 0.1358 | 1.0000 | 14:00 | 97.4% |
| Workshop | r38_c21 | Tuesday | 420 | 52 | 0.1322 | 0.1322 | 1.0000 | 14:00 | 98.8% |
| Workshop | r38_c21 | Thursday | 415 | 52 | 0.1202 | 0.1202 | 1.0000 | 14:00 | 98.3% |
| Workshop | r41_c25 | Tuesday | 304 | 48 | 0.0873 | 0.0873 | 1.0000 | 14:00 | 97.7% |
| Workshop | r41_c25 | Thursday | 313 | 48 | 0.0806 | 0.0806 | 1.0000 | 14:00 | 97.4% |
| Workshop | r38_c21 | Monday | 113 | 44 | 0.0784 | 0.0784 | 1.0000 | 14:00 | 98.2% |
| Workshop | r41_c25 | Monday | 173 | 48 | 0.0568 | 0.0568 | 1.0000 | 14:00 | 100.0% |
| Education | r41_c25 | Thursday | 98 | 45 | 0.0539 | 0.0541 | 0.9957 | 14:00 | 94.9% |
| Education | r41_c25 | Tuesday | 100 | 45 | 0.0455 | 0.0455 | 1.0000 | 14:00 | 99.0% |
| Workshop | r54_c25 | Wednesday | 14 | 8 | 0.0669 | 0.1141 | 0.5868 | 15:30 | 57.1% |

The strongest immediate candidates remain Workshop and Education segments. However, the time-shift table below shows an important constraint: many top Workshop/Education candidates are extremely concentrated at 14:00, and the historically observed non-peak pickup-time bins are small. That means these are good candidates for targeted alternative-offer pilots, but the historical data does not show a large existing off-peak pool.

## Time-Shift Options For Peak Flattening

The notebook now returns:

```text
segment_flexibility_results['top_candidate_time_shift_options']
```

This is the main table for flattening. It shows the peak pickup-time bin and the observed non-peak pickup-time bins inside each highest-priority candidate segment.

Columns:

```text
pickup_time_bin_label =
    30-minute pickup time bin

trips_in_time_bin =
    number of segment trips in that pickup-time bin

share_within_segment =
    trips_in_time_bin / segment_trips

is_peak_time_bin =
    whether this is the segment's most common pickup-time bin

alternative_time_share =
    share_within_segment for non-peak bins, 0 for the peak bin

active_destination_zones =
    number of destination grid zones observed in that time bin

effective_destination_zones =
    entropy-derived effective number of destination zones in that time bin
```

Examples from the current top candidates:

| Candidate | Purpose | Origin | Weekday | Time bin | Trips in bin | Segment trips | Share | Peak? | Alternative share | Active destination zones |
|---:|---|---|---|---|---:|---:|---:|---|---:|---:|
| 1 | Workshop | r38_c21 | Friday | 14:00 | 226 | 232 | 97.4% | Yes | 0.0% | 8 |
| 1 | Workshop | r38_c21 | Friday | 15:00 | 4 | 232 | 1.7% | No | 1.7% | 4 |
| 1 | Workshop | r38_c21 | Friday | 09:00 | 1 | 232 | 0.4% | No | 0.4% | 1 |
| 1 | Workshop | r38_c21 | Friday | 12:30 | 1 | 232 | 0.4% | No | 0.4% | 1 |
| 2 | Workshop | r38_c21 | Tuesday | 14:00 | 415 | 420 | 98.8% | Yes | 0.0% | 15 |
| 2 | Workshop | r38_c21 | Tuesday | 14:30 | 3 | 420 | 0.7% | No | 0.7% | 3 |
| 2 | Workshop | r38_c21 | Tuesday | 08:30 | 2 | 420 | 0.5% | No | 0.5% | 2 |
| 10 | Workshop | r54_c25 | Wednesday | 15:30 | 8 | 14 | 57.1% | Yes | 0.0% | 1 |
| 10 | Workshop | r54_c25 | Wednesday | 15:00 | 3 | 14 | 21.4% | No | 21.4% | 1 |
| 10 | Workshop | r54_c25 | Wednesday | 16:00 | 2 | 14 | 14.3% | No | 14.3% | 1 |

Interpretation:

The highest-volume Workshop candidates have strong destination variety at the 14:00 peak, but very little observed demand in other time bins. For these segments, flattening may require creating new accepted alternatives through rider/agency coordination, not simply shifting into a large existing historical off-peak pattern.

The smaller Workshop `r54_c25` Wednesday segment has a weaker peak and clearer nearby alternative bins, but it has only 14 trips. It is operationally interesting but less reliable than the large repeated Workshop segments.

## Practical Workflow

1. Start with `demand_management_candidates` to find high-priority segments.

2. Use `top_candidate_time_shift_options` to inspect whether meaningful non-peak pickup-time bins exist.

3. If non-peak bins exist, identify the most plausible alternative pickup-time bins within:

   ```text
   same purpose
   same origin zone
   same weekday
   ```

4. If non-peak bins are very small, treat the segment as a pilot for offering newly negotiated alternatives, not as evidence that many trips already shift historically.

5. Use the weekday maps to decide whether a spatial area is consistently flexible or only flexible on certain weekdays.

6. Offer alternatives, do not automatically reschedule.

7. Track whether accepted shifts reduce:

   ```text
   peak trips per 30-minute bin
   peak-to-mean ratio
   vehicle idle/overload imbalance
   ```

## Map Interpretation

The map outputs now include both broad spatial overview and weekday-specific operational views.

Observation from the current maps: higher-flexibility grid cells are concentrated around the main service area, but the pattern changes by weekday. The aggregate map is useful for seeing the general geography of flexible demand, while the weekday maps are better for schedule-flattening decisions because the demand segment itself includes weekday.

Use:

```text
aggregate map:
    broad planning overview

weekday maps:
    operational schedule-flattening decisions
```

Hotter cells indicate origin zones with higher trip-weighted flexibility index among reliable segments. A hot cell still needs to be checked by purpose and weekday before making an intervention.

## Destination Detail

The notebook also returns:

```text
segment_flexibility_results['top_candidate_alternatives']
```

This table shows the most common pickup-time/destination-zone pairs inside the highest-priority candidate segments. It is useful after the time-shift screen, because it tells us which destination zones dominate each peak bin.

For flattening, use `top_candidate_time_shift_options` first, then use `top_candidate_alternatives` to inspect the destination-zone detail within the candidate segment.
