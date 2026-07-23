# ClassTran temporal and geographical flexibility results

Source workbook: Ecolane Reservation and Trip Data July 2022 - June 2023.xlsx

## Demand segment and policy

Demand segment = Purpose + 1.5-mile origin grid zone + weekday.

Workshop, Employment, Education, and Medical are treated as rigid. Both indices are NA for those purposes, and their candidate pools are empty.

A reliable segment has at least 10 trips and at least 3 distinct service dates.

## Temporal index construction

Promised Pick-up Time is grouped into 30-minute half-open bins. For segment s and time bin t, p(s,t) is the bin's trip share and t* is the peak bin.

$$A_s=1-p_{s,t_s^*}$$

### A_s: alternative-time share

A_s is the proportion of trips in segment s historically observed outside the peak 30-minute bin. It ranges from 0 to 1 and is usually displayed as a percentage. A_s = 0 means no alternative-time evidence; A_s = 0.40 means 40% of trips occurred outside the peak. It measures how common alternatives are, not how far away they are, and it is not the guaranteed share of current peak trips that can be moved.

$$D_s=\frac{\sum_{t\ne t_s^*}p_{s,t}|t-t_s^*|}{A_s}$$

### D_s: average alternative shift

D_s is the weighted average absolute distance, in minutes, from the peak among non-peak observations. A value of 30 means alternatives are on average 30 minutes from the peak. D_s is NA when A_s = 0. Because it is absolute, it does not show direction; signed_shift_minutes in the candidate table identifies earlier (negative) and later (positive) alternatives.

Using H = 120 minutes:

$$T_s=\sum_{t\ne t_s^*}p_{s,t}\min\left(\frac{|t-t_s^*|}{H},1\right)$$

### T_s: temporal flexibility index

T_s combines alternative-time prevalence and distance. It ranges from 0 to 1 and has no unit. Each distance is normalized by H = 120 minutes and capped at one, so rare extreme times cannot dominate. T_s = 0 means no non-peak time was observed; higher values mean alternatives are more prevalent, farther from the peak, or both.

When all alternative distances are at most H, T_s = A_s(D_s/H). Therefore, neither high A_s nor high D_s alone guarantees high T_s. This is observed segment-level shift potential, not evidence of individual rider consent.

## Geographical index construction

For allowable purposes, candidates are observed 1.5-mile destination zones from the same demand segment. For destination share p(s,d):

### p(s,d): destination visit share

p(s,d) = n(s,d)/N(s), where n(s,d) is the number of visits to destination zone d and N(s) is the segment's total trips. It ranges from 0 to 1, all shares within a segment sum to 1, and the destination with the largest share is the dominant destination.

$$G_s=1-\sum_d p_{s,d}^2$$

### G_s: geographical flexibility index

G_s is the Gini-Simpson diversity index. It ranges from 0 to less than 1 and incorporates both the number of destinations and the balance of their visit shares. G_s = 0 means every trip uses one destination. It can also be interpreted as the probability that two randomly selected trips from the segment have different destination zones. With equal shares, one, two, five, and ten destinations produce scores of 0, 0.50, 0.80, and 0.90.

$$N_{effective}=\frac{1}{\sum_d p_{s,d}^2}$$

### N_effective: effective destination count

N_effective is the number of equally used destinations that would have the same diversity as the observed distribution. Its minimum is 1. For example, N_effective = 3 means the distribution has the same diversity as three equally used zones, even if more zones were observed. It is related to G_s by G_s = 1 - 1/N_effective.

### Why the ranked candidate table is also necessary

The indices summarize diversity but do not identify locations. The candidate table reports destination zone, visits, p(s,d), rank, and a dominant-destination flag. Rank 1 is the highest-visit destination; lower ranks are observed alternatives. Rigid purposes have empty candidate pools and an NA geographical index.

## Data coverage

- Loaded source records: 121,281
- Usable records: 121,281
- Demand segments: 3,400
- Reliable segments: 1,527
- Published temporal scores: 745
- Published geographical scores: 745
- Temporal alternative rows: 2,091
- Geographical candidate rows: 3,060

### Purpose eligibility and reliability

| Purpose | policy_flexible | segments | trips | reliable_segments | temporal_scores | geographical_scores |
| --- | --- | --- | --- | --- | --- | --- |
| Nutrition | True | 546 | 64285 | 433 | 433 | 433 |
| Medical | False | 1065 | 17015 | 453 | 0 | 0 |
| Employment | False | 354 | 13619 | 220 | 0 | 0 |
| Dialysis | True | 260 | 13186 | 157 | 157 | 157 |
| Workshop | False | 134 | 5511 | 71 | 0 | 0 |
| Personal | True | 428 | 2689 | 76 | 76 | 76 |
| Shopping | True | 330 | 2192 | 56 | 56 | 56 |
| Education | False | 116 | 1526 | 38 | 0 | 0 |
| Recreation | True | 135 | 1001 | 23 | 23 | 23 |
| Missing / Unknown | False | 25 | 245 | 0 | 0 | 0 |
| Trolley | True | 7 | 12 | 0 | 0 | 0 |

## Index distributions

| index | n | mean | q25 | median | q75 | max |
| --- | --- | --- | --- | --- | --- | --- |
| Temporal | 745 | 0.1567 | 0.0411 | 0.1237 | 0.2214 | 0.8500 |
| Geographical | 745 | 0.2092 | 0.0000 | 0.0000 | 0.4942 | 0.9019 |

## Highest observed temporal flexibility segments

| Purpose | origin_zone | weekday | trips | service_days | peak_time_bin | peak_time_share | active_time_bins | A_s | D_s_minutes | expected_shift_potential_minutes | T_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Personal | r22_c16 | Tuesday | 20 | 3 | 10:00-10:30 | 15.0% | 10 | 85.0% | 232.9 | 198.0 | 0.8500 |
| Personal | r14_c24 | Friday | 24 | 10 | 10:30-11:00 | 12.5% | 13 | 87.5% | 181.4 | 158.8 | 0.7604 |
| Personal | r21_c17 | Friday | 10 | 7 | 09:00-09:30 | 20.0% | 7 | 80.0% | 206.2 | 165.0 | 0.7500 |
| Personal | r29_c17 | Thursday | 19 | 6 | 13:00-13:30 | 15.8% | 10 | 84.2% | 131.2 | 110.5 | 0.7368 |
| Personal | r23_c16 | Tuesday | 10 | 4 | 11:30-12:00 | 30.0% | 5 | 70.0% | 188.6 | 132.0 | 0.7000 |
| Personal | r29_c17 | Friday | 25 | 6 | 10:00-10:30 | 20.0% | 9 | 80.0% | 205.5 | 164.4 | 0.7000 |
| Shopping | r10_c14 | Friday | 13 | 7 | 12:00-12:30 | 30.8% | 5 | 69.2% | 140.0 | 96.9 | 0.6731 |
| Dialysis | r29_c17 | Wednesday | 82 | 49 | 15:30-16:00 | 29.3% | 12 | 70.7% | 219.3 | 155.1 | 0.6616 |
| Personal | r24_c11 | Friday | 10 | 4 | 13:30-14:00 | 20.0% | 6 | 80.0% | 105.0 | 84.0 | 0.6500 |
| Personal | r14_c24 | Monday | 12 | 6 | 09:00-09:30 | 16.7% | 7 | 83.3% | 120.0 | 100.0 | 0.6458 |

### Example temporal alternatives

| Purpose | origin_zone | weekday | peak_time_bin | pickup_time_bin | time_bin_trips | p_s_t | signed_shift_minutes | temporal_index_contribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 13:00-13:30 | 3 | 15.0% | +180 | 0.1500 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 12:00-12:30 | 2 | 10.0% | +120 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 12:30-13:00 | 2 | 10.0% | +150 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 14:00-14:30 | 2 | 10.0% | +240 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 14:30-15:00 | 2 | 10.0% | +270 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 15:00-15:30 | 2 | 10.0% | +300 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 16:00-16:30 | 2 | 10.0% | +360 | 0.1000 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 13:30-14:00 | 1 | 5.0% | +210 | 0.0500 |
| Personal | r22_c16 | Tuesday | 10:00-10:30 | 15:30-16:00 | 1 | 5.0% | +330 | 0.0500 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 13:00-13:30 | 3 | 12.5% | +150 | 0.1250 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 14:00-14:30 | 3 | 12.5% | +210 | 0.1250 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 12:00-12:30 | 2 | 8.3% | +90 | 0.0625 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 13:30-14:00 | 2 | 8.3% | +180 | 0.0833 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 14:30-15:00 | 2 | 8.3% | +240 | 0.0833 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 15:00-15:30 | 2 | 8.3% | +270 | 0.0833 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 16:00-16:30 | 2 | 8.3% | +330 | 0.0833 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 09:00-09:30 | 1 | 4.2% | -90 | 0.0312 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 09:30-10:00 | 1 | 4.2% | -60 | 0.0208 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 10:00-10:30 | 1 | 4.2% | -30 | 0.0104 |
| Personal | r14_c24 | Friday | 10:30-11:00 | 11:00-11:30 | 1 | 4.2% | +30 | 0.0104 |

## Highest observed geographical flexibility segments

| Purpose | origin_zone | weekday | trips | service_days | active_destination_zones | alternative_destination_count | effective_destination_count | dominant_destination_zone_final | dominant_destination_visits_final | dominant_destination_share_final | G_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Recreation | r29_c15 | Thursday | 44 | 6 | 14.0 | 13.0 | 10.19 | r33_c16 | 7.0 | 15.9% | 0.9019 |
| Nutrition | r16_c16 | Monday | 320 | 52 | 9.0 | 8.0 | 6.94 | r16_c14 | 60.0 | 18.8% | 0.8559 |
| Personal | r34_c18 | Thursday | 26 | 14 | 8.0 | 7.0 | 6.63 | r34_c24 | 6.0 | 23.1% | 0.8491 |
| Nutrition | r23_c16 | Thursday | 822 | 52 | 11.0 | 10.0 | 6.61 | r24_c17 | 220.0 | 26.8% | 0.8486 |
| Nutrition | r16_c16 | Wednesday | 463 | 52 | 10.0 | 9.0 | 6.52 | r16_c16 | 129.0 | 27.9% | 0.8466 |
| Personal | r14_c24 | Thursday | 25 | 10 | 9.0 | 8.0 | 6.44 | r13_c24 | 6.0 | 24.0% | 0.8448 |
| Nutrition | r23_c16 | Friday | 757 | 53 | 8.0 | 7.0 | 5.94 | r24_c17 | 203.0 | 26.8% | 0.8317 |
| Nutrition | r23_c16 | Monday | 693 | 52 | 8.0 | 7.0 | 5.93 | r24_c17 | 187.0 | 27.0% | 0.8314 |
| Shopping | r35_c23 | Thursday | 30 | 14 | 9.0 | 8.0 | 5.84 | r34_c18 | 8.0 | 26.7% | 0.8289 |
| Shopping | r35_c23 | Friday | 18 | 11 | 7.0 | 6.0 | 5.79 | r28_c14 | 4.0 | 22.2% | 0.8272 |

### Example ranked destination candidates

| Purpose | origin_zone | weekday | destination_zone | destination_visits | p_s_d | destination_rank | is_dominant_destination |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nutrition | r16_c16 | Monday | r16_c14 | 60 | 18.8% | 1 | True |
| Nutrition | r16_c16 | Monday | r17_c17 | 55 | 17.2% | 2 | False |
| Nutrition | r16_c16 | Monday | r18_c16 | 52 | 16.2% | 3 | False |
| Nutrition | r16_c16 | Monday | r20_c20 | 50 | 15.6% | 4 | False |
| Nutrition | r16_c16 | Monday | r16_c15 | 37 | 11.6% | 5 | False |
| Nutrition | r16_c16 | Monday | r14_c16 | 32 | 10.0% | 6 | False |
| Nutrition | r16_c16 | Monday | r15_c15 | 21 | 6.6% | 7 | False |
| Nutrition | r16_c16 | Monday | r17_c16 | 9 | 2.8% | 8 | False |
| Nutrition | r16_c16 | Monday | r17_c15 | 4 | 1.2% | 9 | False |
| Nutrition | r16_c16 | Wednesday | r16_c16 | 129 | 27.9% | 1 | True |
| Nutrition | r16_c16 | Wednesday | r16_c14 | 66 | 14.3% | 2 | False |
| Nutrition | r16_c16 | Wednesday | r17_c17 | 57 | 12.3% | 3 | False |
| Nutrition | r16_c16 | Wednesday | r18_c16 | 57 | 12.3% | 4 | False |
| Nutrition | r16_c16 | Wednesday | r20_c20 | 52 | 11.2% | 5 | False |
| Nutrition | r16_c16 | Wednesday | r16_c15 | 35 | 7.6% | 6 | False |
| Nutrition | r16_c16 | Wednesday | r14_c16 | 29 | 6.3% | 7 | False |
| Nutrition | r16_c16 | Wednesday | r19_c16 | 22 | 4.8% | 8 | False |
| Nutrition | r16_c16 | Wednesday | r17_c16 | 10 | 2.2% | 9 | False |
| Nutrition | r16_c16 | Wednesday | r17_c15 | 6 | 1.3% | 10 | False |
| Nutrition | r23_c16 | Thursday | r24_c17 | 220 | 26.8% | 1 | True |
| Nutrition | r23_c16 | Thursday | r22_c15 | 161 | 19.6% | 2 | False |
| Nutrition | r23_c16 | Thursday | r23_c16 | 92 | 11.2% | 3 | False |
| Nutrition | r23_c16 | Thursday | r22_c14 | 83 | 10.1% | 4 | False |
| Nutrition | r23_c16 | Thursday | r24_c15 | 56 | 6.8% | 5 | False |
| Nutrition | r23_c16 | Thursday | r23_c17 | 54 | 6.6% | 6 | False |
| Nutrition | r23_c16 | Thursday | r21_c13 | 53 | 6.4% | 7 | False |
| Nutrition | r23_c16 | Thursday | r25_c15 | 48 | 5.8% | 8 | False |
| Nutrition | r23_c16 | Thursday | r21_c14 | 32 | 3.9% | 9 | False |
| Nutrition | r23_c16 | Thursday | r23_c15 | 20 | 2.4% | 10 | False |
| Personal | r34_c18 | Thursday | r34_c24 | 6 | 23.1% | 1 | True |

## Observations

- The median temporal index among reliable eligible segments is 0.1237; the middle 50% ranges from 0.0411 to 0.2214.
- The highest temporal score is 0.8500 for Personal in r22_c16 on Tuesday. Its peak is 10:00-10:30, its alternative-time share is 85.0%, and its conditional average alternative shift is 232.9 minutes.
- The median geographical index is 0.0000; the middle 50% ranges from 0.0000 to 0.4942.
- The highest geographical score is 0.9019 for Recreation in r29_c15 on Thursday, with 14 observed destination zones and 10.19 effective destinations.

## Demand-management use

Use T to screen segments with meaningful non-peak time alternatives, then use the temporal candidate table to select earlier or later bins and see their historical shares. Use G to screen destination-diverse segments, then use destination rank, visits, and share to identify the dominant and alternative locations.

These are observational planning measures. They do not establish that an individual trip can be shifted without rider consent, service constraints, capacity checks, and purpose-specific operational review.

## Grid-size sensitivity

The current main results above use 1.5-mile origin and destination grid zones. I also checked 0.5-, 1.0-, 1.5-, and 2.0-mile grid sizes using the same demand-segment definition, 30-minute time bins, minimum 10 trips, and minimum 3 service days.

| Grid size | Demand segments | Reliable segments | Reliable share | Published scores | Median segment trips | Median reliable trips | Median T | Median G | Geographical candidate rows |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.5 mi | 4,813 | 1,734 | 36.0% | 906 | 5 | 39 | 0.0876 | 0.0000 | 3,594 |
| 1.0 mi | 4,016 | 1,643 | 40.9% | 820 | 7 | 40 | 0.1072 | 0.0000 | 3,297 |
| 1.5 mi | 3,400 | 1,527 | 44.9% | 745 | 8 | 38 | 0.1237 | 0.0000 | 3,060 |
| 2.0 mi | 2,845 | 1,390 | 48.9% | 673 | 10 | 45 | 0.1439 | 0.0411 | 2,785 |

The finer grids create more demand segments and more published scores, but the median segment becomes smaller. The 0.5-mile version has a median of only 5 trips per segment, so it gives more spatial detail but weaker segment-level stability. The 2.0-mile version has fewer published segments, but each segment is denser and the geographical index becomes less often zero. The 1.5-mile grid is the selected middle case: it is less sparse than 0.5 or 1.0 miles, but still preserves more spatial detail than 2.0 miles.
