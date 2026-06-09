# Hypothesis Tournament Template

Use for `idea-discovery-team` standard/deep workflows and for broad research
council ideation when the user asks for candidate ideas, ranked mechanisms, or
experimentable hypotheses.

## Tournament Header

| field | value |
|---|---|
| tournament_id | HT-YYYYMMDD-001 |
| context_lock |  |
| source_scope | source-checked / partially source-checked / not source-checked |
| candidate_budget |  |
| branch_budget |  |

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
| R6 | Bayesian expected information gain ranking |  |
| R7 | contradiction red-team and claim ledger |  |
| R8 | final recommendation and kill-tests |  |

## Ranking Criteria

| hypothesis_id | novelty | evidence_strength | mechanism_specificity | assayability | feasibility | safety_or_privacy_risk | CAR_cell_relevance | expected_information_gain | verdict |
|---|---|---|---|---|---|---|---|---|---|
| H-001 | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | low / moderate / high | advance / hold / discard |

## Safety Rule

Do not select a winner only because it is novel. For biomedical hypotheses,
penalize weak assayability, uncontrolled confounding, unsafe disclosure,
translational overreach, and low expected information gain.
