# Hypothesis Tournament Template

Use for domain-neutral idea discovery and broad research-council ideation. Load
specialty axes only from the selected domain pack. Tournament results prioritize
follow-up; they are not evidence strength, biological proof, or validation.

## Tournament Header

| field | value |
|---|---|
| tournament_id | HT-YYYYMMDD-001 |
| schema_version | 2.0 |
| workflow_run_id |  |
| selected_domain_pack | generic-biomedical / cell-therapy / immuno-oncology |
| domain_pack_version |  |
| selection_reason |  |
| domain_specific_assumptions | [] for generic-biomedical |
| context_lock |  |
| source_scope | source-checked / partially source-checked / not source-checked |
| candidate_budget |  |
| iteration_budget | quick=1 / standard=2 / deep=3 / audit=1-2 |
| max_pairwise_matches |  |
| candidate_order_randomization_method |  |
| randomization_seed_or_receipt |  |
| same_model_correlated_judgment_limitation |  |
| compute_budget_status | within-budget / budget-exhausted / not-tracked |

## Candidate Pool and Blinding Map

Keep the hypothesis text separate from the blinded ID presented to judges.

| hypothesis_id | blinded_candidate_id | hypothesis | cluster_id | status | notes |
|---|---|---|---|---|---|
| H-001 | C-017 |  |  | active / merged / held / discarded / prioritized |  |

## Duplicate-Collapse Ledger

| collapse_id | retained_hypothesis_id | merged_hypothesis_ids | similarity_basis | substantive_difference_review | decision_rationale |
|---|---|---|---|---|---|
| DC-001 | H-001 | H-004 |  |  |  |

## Rounds

| round_id | round_type | randomized_order_ref | output_summary |
|---|---|---|---|
| R0 | context/entity/source/domain-pack lock |  |  |
| R1 | diverse generation |  |  |
| R2 | proximity clustering and duplicate collapse |  |  |
| R3 | novelty/plausibility filter |  |  |
| R4 | blinded pairwise judging |  |  |
| R5 | evolution or recombination |  |  |
| R6 | qualitative and optional Elo/Bradley-Terry ranking |  |  |
| R7 | contradiction red-team and claim ledger |  |  |
| R7b | meta-review synthesis |  |  |
| R7c | stop-criterion decision |  |  |
| R8 | prioritization and kill-tests |  |  |

## Per-Judge Score Ledger

Preserve individual judgments before aggregation.

| judgment_id | judge_id | independence_class | blinded_candidate_id | presentation_order | novelty | evidence_strength | mechanistic_specificity | assayability | feasibility | safety | expected_information_gain | execution_priority | rationale |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| J-001 | judge-01 | same-model-separate-context / separate-model / external-tool / human | C-017 | 1 |  |  |  |  |  |  |  |  |  |

## Pairwise Matches

| match_id | judge_id | presentation_order | candidate_a_blinded | candidate_b_blinded | outcome | winner_blinded_id | rationale |
|---|---|---|---|---|---|---|---|
| M-001 | judge-01 | A/B | C-017 | C-204 | a_wins / b_wins / tie / no_decision |  |  |

## Aggregate Ranking and Disagreement

Keep qualitative rank, model-based rank, evidence strength, and execution
priority separate. Do not collapse judge disagreement into the aggregate score.

| hypothesis_id | qualitative_rank | rating_model | model_rating | evidence_strength | execution_priority | aggregate_score | judge_disagreement | expected_information_gain | verdict |
|---|---:|---|---:|---|---|---:|---|---|---|
| H-001 |  | elo / bradley-terry / not-applicable |  | low / moderate / high | low / moderate / high |  | range / SD / IQR / qualitative | low / moderate / high | advance / hold / discard |

## Ranking Uncertainty

| hypothesis_id | method | resamples | interval_or_stability | limitations |
|---|---|---:|---|---|
| H-001 | bootstrap / permutation / qualitative / not-run |  |  |  |

## Order-Sensitivity Check

| check_id | alternate_order_method | changed_pairwise_outcomes | rank_change | sensitivity_verdict | limitation |
|---|---|---:|---:|---|---|
| OS-001 | reverse / reshuffle / Latin-square / not-run |  |  | stable / sensitive / not-assessed |  |

## Iteration and Meta-Review

| iteration_id | input_guidance | new_candidate_count | active_candidate_count | recurring_weaknesses | ranking_sensitivity | next_round_guidance | stop_decision |
|---|---|---:|---:|---|---|---|---|
| I-001 |  |  |  |  |  |  | continue / stop / block |

## Safety and Interpretation Rules

- Do not select a candidate only because it is novel.
- Do not describe Elo, Bradley-Terry, or aggregate judge score as evidence strength.
- Apply specialty relevance only after the corresponding domain pack is selected.
- Penalize weak assayability, uncontrolled confounding, unsafe disclosure,
  translational overreach, and low expected information gain.
- State same-model correlation and incomplete independence explicitly.
- A prioritized candidate still requires source support, experiment design,
  human scientific review, and biological validation.
