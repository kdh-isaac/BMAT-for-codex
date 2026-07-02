# Hypothesis Tournament Template

Use for `idea-discovery-team` standard/deep workflows and for broad research
council ideation when the user asks for candidate ideas, ranked mechanisms, or
experimentable hypotheses.

## Tournament Header

| field | value |
|---|---|
| tournament_id | HT-YYYYMMDD-001 |
| schema_version | 0.6 |
| context_lock |  |
| source_scope | source-checked / partially source-checked / not source-checked |
| candidate_budget |  |
| branch_budget |  |
| iteration_budget | quick=1 / standard=2 / deep=3 / audit=1-2 |
| max_pairwise_matches |  |
| compute_budget_status | within-budget / budget-exhausted / not-tracked |

## Candidate Pool

| hypothesis_id | hypothesis | cluster_id | status | notes |
|---|---|---|---|---|
| H-001 |  |  | active / merged / held / discarded / winner |  |

## Rounds

| round_id | round_type | output_summary |
|---|---|---|
| R0 | context/entity/source scope lock |  |
| R1 | diverse generation |  |
| R2 | proximity clustering and duplicate collapse |  |
| R3 | novelty/plausibility filter |  |
| R4 | pairwise debate or tournament |  |
| R5 | evolution or recombination |  |
| R6 | Elo or qualitative pairwise aggregation plus expected information gain ranking |  |
| R7 | contradiction red-team and claim ledger |  |
| R7b | meta-review synthesis |  |
| R7c | stop-criterion decision |  |
| R8 | final recommendation and kill-tests |  |

## Iteration Log

| iteration_id | input_guidance | new_candidate_count | active_candidate_count | output_summary | stop_decision |
|---|---|---:|---:|---|---|
| I-001 | Initial generation from locked context. |  |  |  | continue / stop / block |

## Pairwise Matches

| match_id | candidate_a | candidate_b | outcome | winner_id | loser_id | rationale |
|---|---|---|---|---|---|---|
| M-001 | H-001 | H-002 | a_wins / b_wins / tie / no_decision |  |  |  |

## Rating Table

Ratings are prioritization aids only. They are not evidence strength, biological
truth, or validation.

| hypothesis_id | rating_model | rating | matches | wins | losses | ties | rating_interpretation |
|---|---|---:|---:|---:|---:|---:|---|
| H-001 | elo / qualitative / not-applicable |  |  |  |  |  | prioritization-only |

## Meta-Review

| iteration_id | recurring_weakness_patterns | generation_guidance_for_next_round | ranking_sensitivity_notes | stop_or_continue_recommendation |
|---|---|---|---|---|
| I-001 |  |  |  | continue / stop / block |

## Stop Decisions

| iteration_id | criterion | decision | rationale |
|---|---|---|---|
| I-001 | rank_stability / novelty_exhaustion / unresolved_blockers / budget_exhausted / human_stop | continue / stop / block |  |

## Ranking Criteria

| hypothesis_id | novelty | evidence_strength | mechanism_specificity | assayability | feasibility | safety_or_privacy_risk | CAR_cell_relevance | rating | expected_information_gain | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| H-001 | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | prioritization-only | low / moderate / high | advance / hold / discard |

## Safety Rule

Do not select a winner only because it is novel. For biomedical hypotheses,
penalize weak assayability, uncontrolled confounding, unsafe disclosure,
translational overreach, and low expected information gain.
