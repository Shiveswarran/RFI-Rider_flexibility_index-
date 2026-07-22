# ClassTran temporal and geographical flexibility results

Source workbook: Ecolane Reservation and Trip Data July 2022 - June 2023.xlsx

## Demand segment and policy

Demand segment = Purpose + 2-mile origin grid zone + weekday.

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

For allowable purposes, candidates are observed 2-mile destination zones from the same demand segment. For destination share p(s,d):

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
- Demand segments: 2,845
- Reliable segments: 1,390
- Published temporal scores: 673
- Published geographical scores: 673
- Temporal alternative rows: 2,152
- Geographical candidate rows: 2,785

### Purpose eligibility and reliability

| Purpose | policy_flexible | segments | trips | reliable_segments | temporal_scores | geographical_scores |
| --- | --- | --- | --- | --- | --- | --- |
| Nutrition | True | 446 | 64285 | 360 | 360 | 360 |
| Medical | False | 800 | 17015 | 403 | 0 | 0 |
| Employment | False | 308 | 13619 | 207 | 0 | 0 |
| Dialysis | True | 233 | 13186 | 149 | 149 | 149 |
| Workshop | False | 128 | 5511 | 69 | 0 | 0 |
| Personal | True | 377 | 2689 | 80 | 80 | 80 |
| Shopping | True | 288 | 2192 | 61 | 61 | 61 |
| Education | False | 114 | 1526 | 38 | 0 | 0 |
| Recreation | True | 126 | 1001 | 23 | 23 | 23 |
| Missing / Unknown | False | 18 | 245 | 0 | 0 | 0 |
| Trolley | True | 7 | 12 | 0 | 0 | 0 |

## Index distributions

| index | n | mean | q25 | median | q75 | max |
| --- | --- | --- | --- | --- | --- | --- |
| Temporal | 673 | 0.1819 | 0.0588 | 0.1439 | 0.2653 | 0.7604 |
| Geographical | 673 | 0.2368 | 0.0000 | 0.0411 | 0.4937 | 0.8784 |

## Highest observed temporal flexibility segments

| Purpose | origin_zone | weekday | trips | service_days | peak_time_bin | peak_time_share | active_time_bins | A_s | D_s_minutes | expected_shift_potential_minutes | T_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Personal | r10_c18 | Friday | 24 | 10 | 10:30-11:00 | 12.5% | 13 | 87.5% | 181.4 | 158.8 | 0.7604 |
| Dialysis | r20_c9 | Thursday | 13 | 5 | 09:30-10:00 | 30.8% | 5 | 69.2% | 316.7 | 219.2 | 0.6923 |
| Personal | r25_c14 | Tuesday | 26 | 9 | 10:00-10:30 | 23.1% | 11 | 76.9% | 174.0 | 133.8 | 0.6827 |
| Personal | r24_c7 | Friday | 11 | 4 | 09:30-10:00 | 18.2% | 7 | 81.8% | 123.3 | 100.9 | 0.6591 |
| Personal | r18_c8 | Friday | 10 | 4 | 13:30-14:00 | 20.0% | 6 | 80.0% | 105.0 | 84.0 | 0.6500 |
| Personal | r10_c18 | Monday | 12 | 6 | 09:00-09:30 | 16.7% | 7 | 83.3% | 120.0 | 100.0 | 0.6458 |
| Personal | r10_c18 | Thursday | 31 | 10 | 13:30-14:00 | 16.1% | 12 | 83.9% | 151.2 | 126.8 | 0.6452 |
| Personal | r21_c13 | Friday | 21 | 5 | 10:00-10:30 | 23.8% | 9 | 76.2% | 172.5 | 131.4 | 0.6429 |
| Recreation | r20_c13 | Friday | 11 | 5 | 09:00-09:30 | 18.2% | 8 | 81.8% | 180.0 | 147.3 | 0.6364 |
| Personal | r10_c18 | Tuesday | 38 | 13 | 12:30-13:00 | 21.1% | 11 | 78.9% | 107.0 | 84.5 | 0.5921 |

### Example temporal alternatives

| Purpose | origin_zone | weekday | peak_time_bin | pickup_time_bin | time_bin_trips | p_s_t | signed_shift_minutes | temporal_index_contribution |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Personal | r10_c18 | Friday | 10:30-11:00 | 13:00-13:30 | 3 | 12.5% | +150 | 0.1250 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 14:00-14:30 | 3 | 12.5% | +210 | 0.1250 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 12:00-12:30 | 2 | 8.3% | +90 | 0.0625 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 13:30-14:00 | 2 | 8.3% | +180 | 0.0833 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 14:30-15:00 | 2 | 8.3% | +240 | 0.0833 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 15:00-15:30 | 2 | 8.3% | +270 | 0.0833 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 16:00-16:30 | 2 | 8.3% | +330 | 0.0833 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 09:00-09:30 | 1 | 4.2% | -90 | 0.0312 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 09:30-10:00 | 1 | 4.2% | -60 | 0.0208 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 10:00-10:30 | 1 | 4.2% | -30 | 0.0104 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 11:00-11:30 | 1 | 4.2% | +30 | 0.0104 |
| Personal | r10_c18 | Friday | 10:30-11:00 | 15:30-16:00 | 1 | 4.2% | +300 | 0.0417 |
| Dialysis | r20_c9 | Thursday | 09:30-10:00 | 15:00-15:30 | 4 | 30.8% | +330 | 0.3077 |
| Dialysis | r20_c9 | Thursday | 09:30-10:00 | 14:00-14:30 | 2 | 15.4% | +270 | 0.1538 |
| Dialysis | r20_c9 | Thursday | 09:30-10:00 | 14:30-15:00 | 2 | 15.4% | +300 | 0.1538 |
| Dialysis | r20_c9 | Thursday | 09:30-10:00 | 16:00-16:30 | 1 | 7.7% | +390 | 0.0769 |
| Personal | r25_c14 | Tuesday | 10:00-10:30 | 14:00-14:30 | 6 | 23.1% | +240 | 0.2308 |
| Personal | r25_c14 | Tuesday | 10:00-10:30 | 09:00-09:30 | 2 | 7.7% | -60 | 0.0385 |
| Personal | r25_c14 | Tuesday | 10:00-10:30 | 12:00-12:30 | 2 | 7.7% | +120 | 0.0769 |
| Personal | r25_c14 | Tuesday | 10:00-10:30 | 13:00-13:30 | 2 | 7.7% | +180 | 0.0769 |

## Highest observed geographical flexibility segments

| Purpose | origin_zone | weekday | trips | service_days | active_destination_zones | alternative_destination_count | effective_destination_count | dominant_destination_zone_final | dominant_destination_visits_final | dominant_destination_share_final | G_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Recreation | r22_c11 | Thursday | 50 | 7 | 12.0 | 11.0 | 8.22 | r23_c10 | 12.0 | 24.0% | 0.8784 |
| Nutrition | r17_c12 | Thursday | 822 | 52 | 9.0 | 8.0 | 7.08 | r18_c12 | 165.0 | 20.1% | 0.8588 |
| Nutrition | r17_c12 | Monday | 693 | 52 | 7.0 | 6.0 | 6.81 | r17_c12 | 136.0 | 19.6% | 0.8531 |
| Nutrition | r17_c12 | Tuesday | 688 | 52 | 9.0 | 8.0 | 6.80 | r18_c11 | 124.0 | 18.0% | 0.8530 |
| Nutrition | r17_c12 | Friday | 757 | 53 | 7.0 | 6.0 | 6.75 | r17_c12 | 151.0 | 19.9% | 0.8518 |
| Personal | r25_c14 | Thursday | 26 | 14 | 8.0 | 7.0 | 6.63 | r25_c18 | 6.0 | 23.1% | 0.8491 |
| Shopping | r12_c12 | Wednesday | 30 | 14 | 8.0 | 7.0 | 6.52 | r9_c18 | 7.0 | 23.3% | 0.8467 |
| Nutrition | r17_c12 | Wednesday | 732 | 52 | 7.0 | 6.0 | 5.99 | r17_c12 | 198.0 | 27.0% | 0.8330 |
| Shopping | r26_c17 | Friday | 18 | 11 | 7.0 | 6.0 | 5.79 | r21_c11 | 4.0 | 22.2% | 0.8272 |
| Personal | r22_c12 | Tuesday | 24 | 10 | 10.0 | 9.0 | 5.76 | r8_c13 | 8.0 | 33.3% | 0.8264 |

### Example ranked destination candidates

| Purpose | origin_zone | weekday | destination_zone | destination_visits | p_s_d | destination_rank | is_dominant_destination |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nutrition | r17_c12 | Friday | r17_c12 | 151 | 19.9% | 1 | True |
| Nutrition | r17_c12 | Friday | r18_c13 | 117 | 15.5% | 2 | False |
| Nutrition | r17_c12 | Friday | r16_c11 | 111 | 14.7% | 3 | False |
| Nutrition | r17_c12 | Friday | r18_c11 | 111 | 14.7% | 4 | False |
| Nutrition | r17_c12 | Friday | r17_c11 | 95 | 12.5% | 5 | False |
| Nutrition | r17_c12 | Friday | r16_c10 | 86 | 11.4% | 6 | False |
| Nutrition | r17_c12 | Friday | r18_c12 | 86 | 11.4% | 7 | False |
| Nutrition | r17_c12 | Monday | r17_c12 | 136 | 19.6% | 1 | True |
| Nutrition | r17_c12 | Monday | r16_c11 | 101 | 14.6% | 2 | False |
| Nutrition | r17_c12 | Monday | r18_c11 | 99 | 14.3% | 3 | False |
| Nutrition | r17_c12 | Monday | r18_c12 | 99 | 14.3% | 4 | False |
| Nutrition | r17_c12 | Monday | r17_c11 | 90 | 13.0% | 5 | False |
| Nutrition | r17_c12 | Monday | r18_c13 | 88 | 12.7% | 6 | False |
| Nutrition | r17_c12 | Monday | r16_c10 | 80 | 11.5% | 7 | False |
| Nutrition | r17_c12 | Thursday | r18_c12 | 165 | 20.1% | 1 | True |
| Nutrition | r17_c12 | Thursday | r17_c12 | 145 | 17.6% | 2 | False |
| Nutrition | r17_c12 | Thursday | r16_c10 | 115 | 14.0% | 3 | False |
| Nutrition | r17_c12 | Thursday | r16_c11 | 107 | 13.0% | 4 | False |
| Nutrition | r17_c12 | Thursday | r18_c11 | 104 | 12.7% | 5 | False |
| Nutrition | r17_c12 | Thursday | r17_c11 | 74 | 9.0% | 6 | False |
| Nutrition | r17_c12 | Thursday | r18_c13 | 58 | 7.1% | 7 | False |
| Nutrition | r17_c12 | Thursday | r15_c10 | 53 | 6.4% | 8 | False |
| Nutrition | r17_c12 | Thursday | r17_c13 | 1 | 0.1% | 9 | False |
| Nutrition | r17_c12 | Tuesday | r18_c11 | 124 | 18.0% | 1 | True |
| Nutrition | r17_c12 | Tuesday | r18_c13 | 114 | 16.6% | 2 | False |
| Nutrition | r17_c12 | Tuesday | r16_c11 | 108 | 15.7% | 3 | False |
| Nutrition | r17_c12 | Tuesday | r18_c12 | 107 | 15.6% | 4 | False |
| Nutrition | r17_c12 | Tuesday | r17_c12 | 88 | 12.8% | 5 | False |
| Nutrition | r17_c12 | Tuesday | r16_c10 | 86 | 12.5% | 6 | False |
| Nutrition | r17_c12 | Tuesday | r17_c11 | 54 | 7.8% | 7 | False |

## Observations

- The median temporal index among reliable eligible segments is 0.1439; the middle 50% ranges from 0.0588 to 0.2653.
- The highest temporal score is 0.7604 for Personal in r10_c18 on Friday. Its peak is 10:30-11:00, its alternative-time share is 87.5%, and its conditional average alternative shift is 181.4 minutes.
- The median geographical index is 0.0411; the middle 50% ranges from 0.0000 to 0.4937.
- The highest geographical score is 0.8784 for Recreation in r22_c11 on Thursday, with 12 observed destination zones and 8.22 effective destinations.

## Demand-management use

Use T to screen segments with meaningful non-peak time alternatives, then use the temporal candidate table to select earlier or later bins and see their historical shares. Use G to screen destination-diverse segments, then use destination rank, visits, and share to identify the dominant and alternative locations.

These are observational planning measures. They do not establish that an individual trip can be shifted without rider consent, service constraints, capacity checks, and purpose-specific operational review.
