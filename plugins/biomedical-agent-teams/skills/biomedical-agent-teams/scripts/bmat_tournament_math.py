"""Recompute tournament bookkeeping, without treating preferences as evidence."""
from __future__ import annotations

import math
import json
import statistics
from itertools import combinations

AXES = ('novelty', 'evidence_strength', 'mechanistic_specificity', 'assayability',
        'feasibility', 'safety', 'expected_information_gain', 'execution_priority')


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def close(left, right):
    return number(left) and math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)


def score_matrix(scores, order, config):
    errors = []
    if not isinstance(order, list) or len(order) != len(set(order)) or not order:
        return {}, [('TOURNAMENT_PRESENTATION_ORDER_INVALID', 'Each order must contain every candidate once.')]
    if not isinstance(scores, list) or not scores:
        return {}, [('TOURNAMENT_JUDGE_SCORE_MATRIX_INCOMPLETE', 'Preserve the actual judge scores for this round.')]
    by_judge = {}
    judgment_ids = set()
    for row in scores:
        if not isinstance(row, dict):
            errors.append(('TOURNAMENT_SCORE_INVALID', 'Score rows must be objects.'))
            continue
        judge, cid = row.get('judge_id'), row.get('blinded_candidate_id')
        judgment_id = row.get('judgment_id')
        if not isinstance(judgment_id, str) or not judgment_id or judgment_id in judgment_ids:
            errors.append(('TOURNAMENT_JUDGMENT_ID_INVALID', 'Judgment IDs must be unique within each preserved round.'))
        else:
            judgment_ids.add(judgment_id)
        if not isinstance(judge, str) or not judge or cid not in order:
            errors.append(('TOURNAMENT_SCORE_INVALID', 'Unknown candidate or missing judge.'))
            continue
        bucket = by_judge.setdefault(judge, {})
        if cid in bucket:
            errors.append(('TOURNAMENT_DUPLICATE_JUDGE_SCORE', f'Duplicate score for {judge}/{cid}.'))
        bucket[cid] = row
        if row.get('presentation_order') != order.index(cid) + 1 or isinstance(row.get('presentation_order'), bool):
            errors.append(('TOURNAMENT_PRESENTATION_ORDER_INVALID', f'{judge}/{cid} does not match the recorded order.'))
        if any(not number(row.get(axis)) or not 0 <= row[axis] <= 1 for axis in AXES):
            errors.append(('TOURNAMENT_SCORE_INVALID', f'{judge}/{cid} requires finite axis scores in [0,1].'))
    if any(set(bucket) != set(order) for bucket in by_judge.values()):
        errors.append(('TOURNAMENT_JUDGE_SCORE_MATRIX_INCOMPLETE', 'Every judge must score every candidate.'))
    method = config.get('method') if isinstance(config, dict) else None
    if method not in {'mean', 'weighted-mean'}:
        errors.append(('TOURNAMENT_AGGREGATION_METHOD_REQUIRED', 'Record mean or weighted-mean aggregation.'))
    weights = config.get('axis_weights', {}) if isinstance(config, dict) else {}
    judge_weights = config.get('judge_weights', {}) if isinstance(config, dict) else {}
    if method == 'mean':
        if weights or judge_weights:
            errors.append(('TOURNAMENT_WEIGHTS_INVALID', 'Mean aggregation must not silently ignore weights.'))
        weights = dict.fromkeys(AXES, 1.0)
        judge_weights = dict.fromkeys(by_judge, 1.0)
    elif method == 'weighted-mean':
        if not isinstance(weights, dict) or set(weights) != set(AXES) or any(not number(v) or v < 0 for v in weights.values()) or sum(weights.values()) <= 0:
            errors.append(('TOURNAMENT_WEIGHTS_INVALID', 'Axis weights must cover all axes with a positive finite total.'))
        if not judge_weights:
            judge_weights = dict.fromkeys(by_judge, 1.0)
        if not isinstance(judge_weights, dict) or set(judge_weights) != set(by_judge) or any(not number(v) or v <= 0 for v in judge_weights.values()):
            errors.append(('TOURNAMENT_WEIGHTS_INVALID', 'Judge weights must cover every judge with positive finite values.'))
    if errors:
        return {}, errors
    output = {}
    for cid in order:
        axis_means = {axis: sum(bucket[cid][axis] * judge_weights[judge] for judge, bucket in by_judge.items()) / sum(judge_weights.values()) for axis in AXES}
        output[cid] = {'aggregate_score': sum(axis_means[axis] * weights[axis] for axis in AXES) / sum(weights.values()),
                       'evidence_strength': axis_means['evidence_strength'], 'execution_priority': axis_means['execution_priority']}
        for axis in ('evidence_strength', 'execution_priority'):
            values = [bucket[cid][axis] for bucket in by_judge.values()]
            output[cid][axis + '_range'] = max(values) - min(values)
            output[cid][axis + '_population-sd'] = statistics.pstdev(values)
    return output, []


def rank_stability(primary, alternate):
    scores = []
    for a, b in combinations(sorted(primary), 2):
        def sign(data):
            delta = data[a]['aggregate_score'] - data[b]['aggregate_score']
            return 0 if abs(delta) <= 1e-9 else (1 if delta > 0 else -1)
        x, y = sign(primary), sign(alternate)
        scores.append(1.0 if x == y else (0.5 if x == 0 or y == 0 else 0.0))
    return statistics.mean(scores) if scores else 1.0


def checks(payload, bundle=None):
    errors = []
    config = payload.get('aggregation', {})
    if not isinstance(config, dict):
        return [('TOURNAMENT_AGGREGATION_METHOD_REQUIRED', 'Aggregation must be an object.')]
    ids = [r.get('hypothesis_id') for r in payload.get('candidates', []) if isinstance(r, dict)]
    final_ids = [r.get('hypothesis_id') for r in payload.get('final_ranking', []) if isinstance(r, dict)]
    for ranking in (payload.get('qualitative_ranking', []), final_ids):
        if len(ranking) != len(ids) or set(ranking) != set(ids):
            errors.append(('TOURNAMENT_RANKING_COVERAGE_INVALID', 'Preserve a disposition for every candidate, including held and merged candidates.'))
    qualitative = config.get('method') == 'qualitative'
    if qualitative:
        if payload.get('ranking_model') != 'qualitative' or any(payload.get(k) for k in ('judge_scores', 'aggregate_scores', 'judge_disagreement', 'model_based_ranking', 'elo_input')) or any(r.get('rating') is not None for r in payload.get('final_ranking', [])):
            errors.append(('TOURNAMENT_QUALITATIVE_NUMERIC_CONFLICT', 'Qualitative evaluation does not certify numeric scores.'))
        sensitivity = payload.get('order_sensitivity_check', {})
        if sensitivity.get('performed'):
            from bmat_release_integrity import bound_file, local_file
            primary = payload.get('candidate_order_randomization', {}).get('randomized_order', [])
            alternate = sensitivity.get('alternate_order', [])
            alternate_rank = sensitivity.get('alternate_ranking', [])
            if len(alternate) != len(primary) or set(alternate) != set(primary) or alternate == primary or len(alternate_rank) != len(ids) or set(alternate_rank) != set(ids):
                errors.append(('TOURNAMENT_ALTERNATE_ORDER_INVALID', 'Preserve a different permutation and a complete alternate ranking.'))
            ref = sensitivity.get('review_artifact_ref')
            review = None
            if bundle is not None and bound_file(bundle, ref, sensitivity.get('review_artifact_sha256')):
                try:
                    review = json.loads(local_file(bundle, ref).read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    pass
            if not isinstance(review, dict) or any(review.get(k) != v for k, v in (
                    ('primary_order', primary), ('primary_ranking', payload.get('qualitative_ranking')),
                    ('alternate_order', alternate), ('alternate_ranking', alternate_rank))) or not str(review.get('rationale', '')).strip():
                errors.append(('TOURNAMENT_ALTERNATE_EVIDENCE_REQUIRED', 'Preserve actual qualitative alternate-order findings.'))
        if sensitivity.get('rank_stability') is not None:
            errors.append(('TOURNAMENT_STABILITY_UNVERIFIED', 'Qualitative comparison reports reasoning, not an uncomputed numeric stability.'))
        return errors
    order = payload.get('candidate_order_randomization', {}).get('randomized_order', [])
    primary, problems = score_matrix(payload.get('judge_scores'), order, config)
    errors.extend(problems)
    if not primary:
        return errors
    candidate_lookup = {r.get('blinded_candidate_id'): r.get('hypothesis_id') for r in payload.get('candidates', []) if isinstance(r, dict)}
    if set(candidate_lookup) != set(primary):
        return errors + [('TOURNAMENT_RANDOMIZED_ORDER_INCOMPLETE', 'Score matrix and candidate IDs must agree.')]
    for row in payload.get('aggregate_scores', []):
        expected = primary.get(row.get('blinded_candidate_id')) if isinstance(row, dict) else None
        if expected and any(not close(row.get(axis), expected[axis]) for axis in ('aggregate_score', 'evidence_strength', 'execution_priority')):
            errors.append(('TOURNAMENT_AGGREGATE_MISMATCH', 'Aggregate values differ from the preserved judge scores.'))
    for row in payload.get('judge_disagreement', []):
        expected = primary.get(row.get('blinded_candidate_id')) if isinstance(row, dict) else None
        method = row.get('method') if isinstance(row, dict) else None
        if method not in {'range', 'population-sd'}:
            errors.append(('TOURNAMENT_DISAGREEMENT_METHOD_INVALID', 'Use range or population-sd.'))
        elif expected and any(not close(row.get(axis + '_dispersion'), expected[axis + '_' + method]) for axis in ('evidence_strength', 'execution_priority')):
            errors.append(('TOURNAMENT_DISAGREEMENT_MISMATCH', 'Disagreement values differ from the judge scores.'))
    sensitivity = payload.get('order_sensitivity_check', {})
    if sensitivity.get('performed'):
        alternate_order = sensitivity.get('alternate_order', [])
        if set(alternate_order) != set(order) or alternate_order == order:
            errors.append(('TOURNAMENT_ALTERNATE_ORDER_INVALID', 'A real alternate permutation, not just a different seed, is required.'))
        alternate, problems = score_matrix(sensitivity.get('alternate_judge_scores'), alternate_order, config)
        errors.extend(problems)
        if alternate and set(alternate) == set(primary):
            expected = rank_stability(primary, alternate)
            if sensitivity.get('metric') != 'pairwise-order-agreement' or not close(sensitivity.get('rank_stability'), expected):
                errors.append(('TOURNAMENT_STABILITY_MISMATCH', 'Recompute pairwise-order-agreement from both score matrices.'))
            lookup = {r['blinded_candidate_id']: r['hypothesis_id'] for r in payload.get('candidates', [])}
            expected_order = [lookup[c] for c in sorted(alternate, key=lambda c: (-alternate[c]['aggregate_score'], lookup[c]))]
            if sensitivity.get('alternate_ranking') != expected_order:
                errors.append(('TOURNAMENT_ALTERNATE_RANKING_MISMATCH', 'Alternate ranking must match recomputed scores, with ID ordering for exact ties.'))
    else:
        errors.append(('TOURNAMENT_ALTERNATE_EVIDENCE_REQUIRED', 'Quantitative order sensitivity requires preserved alternate scores.'))
    lookup = {r['blinded_candidate_id']: r['hypothesis_id'] for r in payload.get('candidates', [])}
    if payload.get('ranking_model') == 'weighted-score':
        expected_order = [lookup[c] for c in sorted(primary, key=lambda c: (-primary[c]['aggregate_score'], lookup[c]))]
        if payload.get('model_based_ranking') != expected_order:
            errors.append(('TOURNAMENT_MODEL_RANKING_MISMATCH', 'Stored ranking differs from aggregate scores.'))
    elif payload.get('ranking_model') not in {'elo'}:
        errors.append(('TOURNAMENT_MODEL_UNVERIFIED', 'Use reproducible Elo/weighted-score, or record a qualitative assessment without unverified numeric ratings.'))
    if payload.get('ranking_model') == 'elo':
        import bmat_elo
        elo_input = payload.get('elo_input')
        if not isinstance(elo_input, dict):
            errors.append(('TOURNAMENT_ELO_INPUT_REQUIRED', 'Preserve Elo settings and match outcomes.'))
        else:
            try:
                elo = bmat_elo.aggregate(elo_input)
                ratings = {r['hypothesis_id']: r['elo_rating'] for r in elo['ratings']}
            except (SystemExit, ValueError, KeyError, TypeError):
                errors.append(('TOURNAMENT_ELO_INPUT_INVALID', 'Elo input is not reproducible.'))
            else:
                expected_order = sorted(ratings, key=lambda c: (-ratings[c], c))
                if set(ratings) != set(lookup.values()) or payload.get('model_based_ranking') != expected_order:
                    errors.append(('TOURNAMENT_ELO_RANKING_MISMATCH', 'Stored model ranking differs from the Elo match replay.'))
                for row in payload.get('final_ranking', []):
                    if row.get('rating') is not None and not close(row['rating'], ratings.get(row.get('hypothesis_id'), float('nan'))):
                        errors.append(('TOURNAMENT_ELO_RATING_MISMATCH', 'Stored rating differs from match replay.'))
    if payload.get('model_based_ranking') and [r.get('hypothesis_id') for r in sorted(payload.get('final_ranking', []), key=lambda r:r.get('rank',0))] != payload['model_based_ranking']:
        if not str(payload.get('ranking_override_reason', '')).strip():
            errors.append(('TOURNAMENT_RANKING_OVERRIDE_REASON_REQUIRED', 'Preserve the researcher rationale for overriding numeric ranking.'))
    return errors
