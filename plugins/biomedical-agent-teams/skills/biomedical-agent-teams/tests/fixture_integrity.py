"""Hash utilities for explicitly synthetic test fixtures, never research runs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def hashes(bundle):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(bundle).rglob('*')
            if p.is_file() and p.name != 'bundle_manifest.json'}


def rebind(bundle, before):
    changes = {old: hashlib.sha256(p.read_bytes()).hexdigest() for p, old in before.items()
               if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != old}
    for _ in range(30):
        follow = {}
        for p in Path(bundle).rglob('*.json'):
            if p.name == 'bundle_manifest.json':
                continue
            data = p.read_bytes()
            text = data.decode('utf-8')
            updated = text
            for old, new in changes.items():
                updated = updated.replace(old, new)
            if text != updated:
                p.write_bytes(updated.encode('utf-8'))
                follow[hashlib.sha256(data).hexdigest()] = hashlib.sha256(p.read_bytes()).hexdigest()
        if not follow:
            break
        changes = follow
    else:
        raise AssertionError('Synthetic fixture contains a hash dependency cycle')


def write(path, data):
    Path(path).write_bytes((json.dumps(data, indent=2) + '\n').encode('utf-8'))


def cover_workflow(bundle, dag):
    """Declare explicitly synthetic combined review scope for a mutated test DAG."""
    old = hashes(bundle)
    path = bundle / 'review_artifact_manifest.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    nodes = [n for n in dag['nodes'] if n.get('required_checks')]
    for review in data['review_instances']:
        review['covered_node_ids'] = [n['id'] for n in nodes]
        review['covered_check_ids'] = sorted({c for n in nodes for c in n['required_checks']})
        review['checks_run'] = sorted(set(review['checks_run'] + review['covered_check_ids']))
        for ref in {ref for n in nodes for ref in n.get('required_input_refs', [])}:
            if ref not in review['input_artifact_refs']:
                review['input_artifact_refs'].append(ref)
            review['input_artifact_sha256'][ref] = hashlib.sha256((bundle/ref).read_bytes()).hexdigest()
    write(path, data)
    rebind(bundle, old)
