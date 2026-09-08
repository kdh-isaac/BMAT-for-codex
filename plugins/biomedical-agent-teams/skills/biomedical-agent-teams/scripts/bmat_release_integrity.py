"""Deterministic review coverage and source extraction checks for BMAT.

Reviewers classify claims and assess meaning. These checks bind that assessment
to actual local artifacts; they do not infer scientific truth from prose.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import unicodedata
from typing import Any

from bmat_workflow_policy import plan_workflow


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_file(root: Path, ref: Any) -> Path | None:
    if not isinstance(ref, str) or not ref or '\\' in ref:
        return None
    path = Path(ref)
    if path.is_absolute() or PureWindowsPath(ref).drive or '..' in path.parts:
        return None
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def bound_file(root: Path, ref: Any, sha: Any) -> bool:
    path = local_file(root, ref)
    return path is not None and isinstance(sha, str) and digest(path.read_bytes()) == sha


def rows(value: Any, key: str) -> list[dict[str, Any]]:
    items = value.get(key, []) if isinstance(value, dict) else []
    return [row for row in items if isinstance(row, dict)] if isinstance(items, list) else []


def final_blocks(text: str) -> list[dict[str, str]]:
    """Blank-line delimited Markdown blocks; classification is reviewer-owned."""
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    blocks = [part.strip() for part in re.split(r'\n[ \t]*\n', text) if part.strip()]
    return [{'block_id': f'B{index:04d}', 'block_sha256': digest(part.encode('utf-8'))}
            for index, part in enumerate(blocks, 1)]


def review_binds(row: dict, root: Path, refs: list[str], checks: list[str]) -> bool:
    declared = row.get('input_artifact_refs', [])
    hashes = row.get('input_artifact_sha256', {})
    if not isinstance(declared, list) or not isinstance(hashes, dict):
        return False
    return (set(checks) <= set(row.get('covered_check_ids', []))
            and set(checks) <= set(row.get('checks_run', []))
            and all(ref in declared and bound_file(root, ref, hashes.get(ref)) for ref in refs))


def review_coverage(artifacts: dict, root: Path, skill: Path) -> list[tuple[str, str]]:
    state = artifacts.get('run_state') or {}
    alias = state.get('alias', '')
    template_path = skill / 'workflows' / f'{alias}.json'
    errors = []
    requirements = []
    if alias in {p.stem for p in (skill / 'workflows').glob('*.json')}:
        template = json.loads(template_path.read_text(encoding='utf-8'))
        tier = 'full' if state.get('final_label') == 'Full protocol followed' else state.get('workflow_tier', 'compact')
        planned = plan_workflow(template, state.get('mode', 'standard'), tier)
        requirements.extend(n for n in planned['nodes'] if n.get('required_checks'))
    else:
        errors.append(('REVIEW_REQUIREMENTS_UNAVAILABLE', 'Select a supported workflow before release.'))
    dag = artifacts.get('workflow_dag') or {}
    requirements.extend(n for n in rows(dag, 'nodes') if n.get('required_checks'))
    for key in ('lead_decision', 'preflight'):
        requirements.extend(rows(artifacts.get(key), 'required_reviews'))
    reviews = rows(artifacts.get('review_artifact_manifest'), 'review_instances')
    seen = set()
    for node in requirements:
        node_id = node.get('id')
        checks = node.get('required_checks', [])
        refs = node.get('required_input_refs', [])
        key = (str(node_id), tuple(checks), tuple(refs), bool(node.get('independence_required')))
        if key in seen:
            continue
        seen.add(key)
        candidates = [r for r in reviews if node_id in r.get('covered_node_ids', [])
                      and review_binds(r, root, refs, checks)]
        if node.get('independence_required'):
            candidates = [r for r in candidates if r.get('independent_review_eligible') is True
                          and r.get('fixture_only') is False
                          and r.get('independence_class') in {'separate-model', 'external-tool', 'human'}]
        # Existing receipt validation separately verifies runtime, hashes and identity.
        if not candidates:
            errors.append(('REQUIRED_REVIEW_UNCOVERED', f'{node_id}: actual review must cover {checks} on {refs}.'))
    return errors


def final_coverage(artifacts: dict, root: Path) -> list[tuple[str, str]]:
    errors = []
    post = artifacts.get('post_write_validation') or {}
    if not isinstance(post, dict):
        return [('FINAL_REVIEW_REQUIRED', 'Post-write validation is required.')]
    for ref_key, sha_key, expected in (
        ('reviewed_final_ref', 'reviewed_final_sha256', 'final.md'),
        ('reviewed_ledger_ref', 'reviewed_ledger_sha256', 'claim_ledger.json'),
    ):
        if post.get(ref_key) != expected or not bound_file(root, post.get(ref_key), post.get(sha_key)):
            errors.append(('FINAL_REVIEW_STALE', f'Review the current {expected}; manifest regeneration is not a review.'))
    text = artifacts.get('final_text') or ''
    expected_blocks = final_blocks(str(text))
    coverage = rows(post, 'content_coverage')
    if [(r.get('block_id'), r.get('block_sha256')) for r in coverage] != [
            (r['block_id'], r['block_sha256']) for r in expected_blocks]:
        errors.append(('FINAL_COVERAGE_INCOMPLETE', 'Every final content block must be mapped in document order.'))
    claims = {r.get('claim_id'): r for r in rows(artifacts.get('claim_ledger'), 'claims')}
    for row in coverage:
        ids = row.get('claim_ids', [])
        category = row.get('classification')
        if not isinstance(ids, list) or any(c not in claims for c in ids):
            errors.append(('FINAL_COVERAGE_UNKNOWN_CLAIM', f"Unknown claim in {row.get('block_id')}."))
            continue
        if category == 'claim':
            if not ids or any(claims[c].get('audit_status') in {'block', 'blocked', 'excluded', 'fail'} for c in ids):
                errors.append(('FINAL_COVERAGE_CLAIM_BLOCKED', f"{row.get('block_id')} requires allowed ledger claims."))
        elif category not in {'heading', 'formatting', 'non-claim'} or ids or not str(row.get('reason', '')).strip():
            errors.append(('FINAL_COVERAGE_CLASSIFICATION_INVALID', 'Non-claim blocks need a reason and no claim IDs.'))
    reviews = rows(artifacts.get('review_artifact_manifest'), 'review_instances')
    review = next((r for r in reviews if r.get('instance_id') == post.get('coverage_review_instance_id')), None)
    if review is None or not review_binds(review, root, ['final.md', 'claim_ledger.json'], ['final.coverage', 'final.scope']):
        errors.append(('FINAL_COVERAGE_REVIEW_REQUIRED', 'A recorded reviewer must check coverage classification and claim scope on the final snapshot.'))
    return errors


def normalized_source(text: str) -> str:
    return unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n'))


def locator_matches(span: dict, extraction: dict, root: Path) -> bool:
    """Bind human-readable locators to intervals in the preserved extraction."""
    ref = extraction.get('locator_map_ref')
    if not bound_file(root, ref, extraction.get('locator_map_sha256')):
        return False
    try:
        mapping = json.loads(local_file(root, ref).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    if not isinstance(mapping, dict) or any(mapping.get(k) != extraction.get(k) for k in (
            'text_ref', 'text_sha256', 'original_snapshot_sha256', 'normalization',
            'offset_unit', 'extractor', 'extractor_version')):
        return False
    start, end = extraction.get('start'), extraction.get('end')
    if not isinstance(start, int) or not isinstance(end, int):
        return False
    return any(all(segment.get(k) == span.get(k) for k in (
                   'locator', 'section', 'paragraph_or_table', 'sentence_or_cell'))
               and type(segment.get('start')) is int and type(segment.get('end')) is int
               and 0 <= segment['start'] <= start < end <= segment['end']
               for segment in rows(mapping, 'segments'))


def source_spans(corpus: Any, root: Path, review_manifest: Any) -> list[tuple[str, str]]:
    errors = []
    reviews = rows(review_manifest, 'review_instances')
    all_spans = [(source, span) for source in rows(corpus, 'sources')
                 if source.get('inclusion_status') == 'included' for span in rows(source, 'evidence_spans')]
    valid = set()
    summaries = []
    for source, span in all_spans:
        sid = span.get('span_id')
        extraction = span.get('extraction')
        if not isinstance(extraction, dict):
            errors.append(('EVIDENCE_EXTRACTION_REQUIRED', f'{sid}: explicitly classify and verify the extraction; legacy spans are not inferred.'))
            continue
        kind = extraction.get('kind')
        if kind == 'summary':
            summaries.append((source, span, extraction))
            continue
        if kind == 'human-verified':
            reviewer = next((r for r in reviews if r.get('instance_id') == extraction.get('review_instance_id')
                             and r.get('actor_type') == 'human'), None)
            refs = ['source_corpus.json', str(span.get('source_snapshot_ref', ''))]
            if reviewer and review_binds(reviewer, root, refs, ['source.extraction']) and str(extraction.get('rationale', '')).strip():
                valid.add(sid)
            else:
                errors.append(('EVIDENCE_HUMAN_REVIEW_REQUIRED', f'{sid}: attributable human review of source and extraction is required.'))
            continue
        if kind != 'quotation':
            errors.append(('EVIDENCE_EXTRACTION_UNVERIFIED', f'{sid}: extraction has not been verified.'))
            continue
        ref = extraction.get('text_ref')
        if (extraction.get('normalization') != 'NFC-LF' or extraction.get('offset_unit') != 'unicode-codepoint'
                or not bound_file(root, ref, extraction.get('text_sha256'))
                or extraction.get('original_snapshot_sha256') != span.get('source_snapshot_sha256')
                or not bound_file(root, span.get('source_snapshot_ref'), span.get('source_snapshot_sha256'))):
            errors.append(('EVIDENCE_EXTRACTION_PROVENANCE_INVALID', f'{sid}: extraction text and original snapshot must be hash-bound.'))
            continue
        try:
            text = normalized_source(local_file(root, ref).read_text(encoding='utf-8'))
        except (OSError, UnicodeError):
            errors.append(('EVIDENCE_EXTRACTION_TEXT_INVALID', f'{sid}: preserve a UTF-8 extraction for binary sources.'))
            continue
        start, end = extraction.get('start'), extraction.get('end')
        if not locator_matches(span, extraction, root):
            errors.append(('EVIDENCE_LOCATOR_MISMATCH', f'{sid}: locator must match a hash-bound extraction interval.'))
            continue
        if (not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool)
                or not 0 <= start < end <= len(text)
                or text[start:end] != normalized_source(str(span.get('short_evidence_excerpt', '')))):
            errors.append(('EVIDENCE_EXCERPT_NOT_IN_SOURCE', f'{sid}: excerpt does not equal its declared text interval.'))
        elif not str(extraction.get('extractor', '')).strip() or not str(extraction.get('extractor_version', '')).strip():
            errors.append(('EVIDENCE_EXTRACTOR_REQUIRED', f'{sid}: record extractor and version, including identity extraction.'))
        else:
            valid.add(sid)
    owners = {span.get('span_id'): source.get('source_id') for source, span in all_spans}
    for source, span, extraction in summaries:
        supports = extraction.get('supporting_span_ids', [])
        reviewer = next((r for r in reviews if r.get('instance_id') == extraction.get('review_instance_id')), None)
        if (not isinstance(supports, list) or not supports or not set(supports) <= valid
                or any(owners.get(s) != source.get('source_id') for s in supports)
                or reviewer is None or not review_binds(reviewer, root, ['source_corpus.json'], ['source.summary'])):
            errors.append(('EVIDENCE_SUMMARY_SUPPORT_REQUIRED', f"{span.get('span_id')}: a summary needs verified source spans and a bounded summary review."))
    return errors
