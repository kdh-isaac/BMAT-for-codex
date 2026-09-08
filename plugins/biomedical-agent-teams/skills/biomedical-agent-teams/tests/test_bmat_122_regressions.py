"""Negative controls for the 1.2.1 audit findings; no live tools or models."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import argparse
import unicodedata

import pytest
import jsonschema

import bmat_tournament_check
import bmat_validate
import bmat_release_integrity as integrity
import bmat_workflow_policy as policy
import bmat_run
from fixture_integrity import hashes, rebind
from test_bmat_tournament_v2 import valid_tournament

SKILL = Path(__file__).resolve().parents[1]


def write(path, payload):
    path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')


def release_codes(bundle):
    manifest = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts/bmat_bundle_manifest.py'),
                               '--bundle', str(bundle)], capture_output=True, text=True)
    assert manifest.returncode == 0, manifest.stderr
    result = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts/bmat_validate.py'),
                             '--bundle', str(bundle), '--release', '--json'], capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    return {row['code'] for row in json.loads(result.stdout) if row['level'] == 'ERROR'}


def fixture(tmp_path):
    dest = tmp_path / 'bundle'
    shutil.copytree(SKILL / 'tests/fixtures/valid_full_protocol_bundle', dest)
    return dest


def test_extra_final_sentence_invalidates_post_write_review(tmp_path):
    b = fixture(tmp_path)
    assert release_codes(b) == set()
    with (b / 'final.md').open('a', encoding='utf-8') as f:
        f.write('\nThis report contains twelve replicated validation experiments.\n')
    codes = release_codes(b)
    assert 'FINAL_REVIEW_STALE' in codes
    assert 'FINAL_COVERAGE_INCOMPLETE' in codes


def test_runtime_dag_rejects_self_cycle():
    data = {'run_state': {'alias': 'evidence-audit-team', 'mode': 'audit',
                         'stages': [{'id': 'S0', 'depends_on': ['S0']}]},
            'workflow_dag': {'alias': 'evidence-audit-team', 'mode': 'audit',
                             'nodes': [{'id': 'S0', 'agent': 'protocol-context-locker',
                                        'requires': ['S0'], 'outputs': [], 'blocking': True}]}}
    findings = []
    bmat_validate.validate_workflow_dag_policy(data, findings)
    assert 'WORKFLOW_DAG_CYCLE' in {f.code for f in findings}


def test_missing_contradiction_review_does_not_satisfy_full_dag(tmp_path):
    b = fixture(tmp_path)
    state = json.loads((b / 'run_state.json').read_text(encoding='utf-8'))
    dag = json.loads((SKILL / 'workflows/evidence-audit-team.json').read_text(encoding='utf-8'))
    dag.update(schema_version='2.0', workflow_run_id=state['run_id'],
               plugin_version=state['plugin_version'], created_at=state['created_at'])
    state['stages'] = [{'id': n['id'], 'required': True, 'status': 'pass',
                       'depends_on': n.get('requires', []), 'evidence': 'Synthetic negative control'}
                      for n in dag['nodes']]
    write(b / 'workflow_dag.json', dag)
    write(b / 'run_state.json', state)
    reviews = json.loads((b / 'review_artifact_manifest.json').read_text(encoding='utf-8'))
    for row in reviews['review_instances']:
        row['covered_node_ids'] = ['S3_citation_check']
        row['covered_check_ids'] = ['citation.identity']
    write(b / 'review_artifact_manifest.json', reviews)
    assert 'REQUIRED_REVIEW_UNCOVERED' in release_codes(b)


def test_tournament_recomputes_aggregate_and_disagreement():
    p = valid_tournament()
    p['aggregate_scores'][0]['evidence_strength'] = 0.01
    p['judge_disagreement'][0]['evidence_strength_dispersion'] = 0.9
    codes = {f.code for f in bmat_tournament_check.check(p)}
    assert 'TOURNAMENT_AGGREGATE_MISMATCH' in codes
    assert 'TOURNAMENT_DISAGREEMENT_MISMATCH' in codes


def test_tournament_rejects_wrong_presentation_order():
    p = valid_tournament()
    for row in p['judge_scores']:
        row['presentation_order'] = 1
    assert 'TOURNAMENT_PRESENTATION_ORDER_INVALID' in {f.code for f in bmat_tournament_check.check(p)}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def loaded(bundle):
    return {'run_state': read(bundle/'run_state.json'),
            'review_artifact_manifest': read(bundle/'review_artifact_manifest.json'),
            'post_write_validation': read(bundle/'post_write_validation.json'),
            'claim_ledger': read(bundle/'claim_ledger.json'),
            'source_corpus': read(bundle/'source_corpus.json'),
            'final_text': (bundle/'final.md').read_text(encoding='utf-8')}


@pytest.mark.parametrize('kind,expected', [
    ('cycle', 'WORKFLOW_DAG_CYCLE'), ('missing', 'WORKFLOW_DAG_DEPENDENCY_INVALID'),
    ('duplicate', 'WORKFLOW_DAG_DUPLICATE_NODE'), ('agent', 'WORKFLOW_DAG_UNKNOWN_AGENT')])
def test_graph_negative_controls(kind, expected):
    dag = {'nodes': [{'id':'a','agent':'known','requires':[]}, {'id':'b','agent':'known','requires':['a']}]}
    if kind == 'cycle': dag['nodes'][0]['requires'] = ['b']
    if kind == 'missing': dag['nodes'][1]['requires'] = ['missing']
    if kind == 'duplicate': dag['nodes'][1]['id'] = 'a'
    if kind == 'agent': dag['nodes'][1]['agent'] = 'invented'
    assert expected in {c for c,_ in policy.graph_errors(dag, {'known'})}


def test_graph_branch_merge_accepts_arbitrary_serialization():
    dag = {'nodes':[{'id':'d','requires':['b','c']}, {'id':'c','requires':['a']},
                    {'id':'a','requires':[]}, {'id':'b','requires':['a']}]}
    assert policy.graph_errors(dag) == []
    assert [n['id'] for n in policy.topological_nodes(dag)] == ['a','b','c','d']


def test_combined_review_covers_multiple_requirements_without_extra_instances(tmp_path):
    b = fixture(tmp_path)
    data = loaded(b)
    assert len(data['review_artifact_manifest']['review_instances']) == 1
    assert integrity.review_coverage(data,b,SKILL) == []
    assert release_codes(b) == set()
    data['workflow_dag'] = {'nodes': []}  # Removing local gates does not erase the canonical minimum.
    data['review_artifact_manifest']['review_instances'][0]['covered_check_ids'] = ['citation.identity']
    assert 'REQUIRED_REVIEW_UNCOVERED' in {c for c,_ in integrity.review_coverage(data,b,SKILL)}


def test_lead_can_add_review_requirements_to_inline_run(tmp_path):
    b = fixture(tmp_path); data = loaded(b)
    data['lead_decision'] = {'required_reviews':[{'id':'specific-review','required_checks':['specific.check'],
                          'required_input_refs':['claim_ledger.json'],'independence_required':False}]}
    assert integrity.review_coverage(data,b,SKILL)


@pytest.mark.parametrize('filename', ['final.md','claim_ledger.json'])
def test_snapshot_change_cannot_be_fixed_by_manifest_alone(tmp_path, filename):
    b = fixture(tmp_path)
    with (b/filename).open('a',encoding='utf-8') as f: f.write('\n')
    assert 'FINAL_REVIEW_STALE' in release_codes(b)


def test_reviewed_korean_paraphrase_blocks_and_table(tmp_path):
    b = fixture(tmp_path); before = hashes(b)
    text = 'Final workflow label: Full protocol followed\n\n# 연구 요약\n\n보존한 로컬 기록은 명시된 합성 사례의 제한된 주장을 뒷받침한다.\n\n| 판단 | 범위 |\n|---|---|\n| 지지 | 합성 사례에 한정 |\n'
    (b/'final.md').write_text(text,encoding='utf-8')
    post = read(b/'post_write_validation.json')
    post.update(wording_policy='reviewed-paraphrase', reviewed_final_sha256=integrity.digest((b/'final.md').read_bytes()))
    post['content_coverage'] = [dict(row, classification='heading' if i<2 else 'claim',
                                   claim_ids=[] if i<2 else ['CL-001'], reason='Synthetic reviewed Korean paraphrase')
                               for i,row in enumerate(integrity.final_blocks(text))]
    write(b/'post_write_validation.json',post); rebind(b,before)
    data=loaded(b); data['_bundle_dir']=str(b)
    assert integrity.final_coverage(data,b) == []
    assert release_codes(b) == set()
    post['content_coverage'][1]['claim_ids']=['unknown']
    data['post_write_validation']=post
    assert 'FINAL_COVERAGE_UNKNOWN_CLAIM' in {c for c,_ in integrity.final_coverage(data,b)}


@pytest.mark.parametrize('mutation,code', [
    ('excerpt','EVIDENCE_EXCERPT_NOT_IN_SOURCE'), ('locator','EVIDENCE_LOCATOR_MISMATCH'),
    ('offset','EVIDENCE_EXCERPT_NOT_IN_SOURCE'), ('legacy','EVIDENCE_EXTRACTION_REQUIRED')])
def test_source_mismatch_survives_other_hash_repairs(tmp_path, mutation, code):
    b=fixture(tmp_path); before=hashes(b); corpus=read(b/'source_corpus.json');span=corpus['sources'][0]['evidence_spans'][0]
    if mutation=='excerpt':
        span['short_evidence_excerpt']='X'+span['short_evidence_excerpt'][1:]
        span['evidence_text_sha256']=integrity.digest(span['short_evidence_excerpt'].encode())
    elif mutation=='locator':span['locator']='page 999'
    elif mutation=='offset':span['extraction']['start']+=1
    else:span.pop('extraction')
    write(b/'source_corpus.json',corpus);rebind(b,before)
    assert code in release_codes(b)


def test_source_unicode_and_line_normalization(tmp_path):
    b=fixture(tmp_path);corpus=read(b/'source_corpus.json');span=corpus['sources'][0]['evidence_spans'][0];e=span['extraction']
    raw=unicodedata.normalize('NFD','한글 근거\r\n둘째 줄')
    normalized=integrity.normalized_source(raw)
    (b/e['text_ref']).write_bytes(raw.encode('utf-8'))
    sha=integrity.digest(raw.encode('utf-8'))
    span.update(source_snapshot_sha256=sha,short_evidence_excerpt=normalized)
    e.update(text_sha256=sha,original_snapshot_sha256=sha,start=0,end=len(normalized))
    mapping=read(b/e['locator_map_ref']);mapping.update(text_sha256=sha,original_snapshot_sha256=sha)
    mapping['segments'][0].update(start=0,end=len(normalized))
    write(b/e['locator_map_ref'],mapping);e['locator_map_sha256']=integrity.digest((b/e['locator_map_ref']).read_bytes())
    assert integrity.source_spans(corpus,b,{}) == []
    span['short_evidence_excerpt']=normalized.replace(' ','  ')
    assert 'EVIDENCE_EXCERPT_NOT_IN_SOURCE' in {c for c,_ in integrity.source_spans(corpus,b,{})}


def test_summary_and_human_routes_require_attributable_review(tmp_path):
    b=fixture(tmp_path);corpus=read(b/'source_corpus.json');spans=corpus['sources'][0]['evidence_spans']; original=spans[0]
    summary=copy.deepcopy(original);summary.update(span_id='summary',short_evidence_excerpt='A bounded summary.')
    summary['extraction']={'kind':'summary','supporting_span_ids':[original['span_id']], 'review_instance_id':'human'}
    spans.append(summary);write(b/'source_corpus.json',corpus)
    refs=['source_corpus.json',original['source_snapshot_ref']]
    review={'instance_id':'human','actor_type':'human','covered_check_ids':['source.summary','source.extraction'],
            'checks_run':['source.summary','source.extraction'],'input_artifact_refs':refs,
            'input_artifact_sha256':{ref:integrity.digest((b/ref).read_bytes()) for ref in refs}}
    manifest={'review_instances':[review]}
    assert integrity.source_spans(corpus,b,manifest)==[]
    assert 'EVIDENCE_SUMMARY_SUPPORT_REQUIRED' in {c for c,_ in integrity.source_spans(corpus,b,{})}
    original['extraction']={'kind':'human-verified','review_instance_id':'human','rationale':'Synthetic human inspection of source and extraction.'}
    write(b/'source_corpus.json',corpus);review['input_artifact_sha256']['source_corpus.json']=integrity.digest((b/'source_corpus.json').read_bytes())
    assert integrity.source_spans(corpus,b,manifest)==[]
    review['actor_type']='model'
    assert 'EVIDENCE_HUMAN_REVIEW_REQUIRED' in {c for c,_ in integrity.source_spans(corpus,b,manifest)}


def qualitative_tournament():
    p=valid_tournament();p['aggregation']={'method':'qualitative'};p['ranking_model']='qualitative';p.pop('elo_input')
    for k in ('judge_scores','aggregate_scores','judge_disagreement','model_based_ranking'):p[k]=[]
    for row in p['final_ranking']:row.pop('rating',None)
    p['order_sensitivity_check']={'performed':False,'alternate_seed':None,'rank_stability':None,'limitations':'Comparison not performed.'}
    return p


def test_qualitative_tournament_needs_no_scores_or_second_run():
    p=qualitative_tournament()
    p['candidate_order_randomization'].update(method='manually recorded blinded order',seed=None)
    jsonschema.Draft202012Validator(read(SKILL/'contracts/hypothesis-tournament.schema.json')).validate(p)
    assert bmat_tournament_check.check(p)==[]
    p['order_sensitivity_check']['rank_stability']=1
    assert 'TOURNAMENT_STABILITY_UNVERIFIED' in {f.code for f in bmat_tournament_check.check(p)}


def test_qualitative_alternate_comparison_binds_actual_output(tmp_path):
    p=qualitative_tournament();s=p['order_sensitivity_check']
    s.update(performed=True,alternate_order=['blind-17','blind-42'],alternate_ranking=['H-001','H-002'],review_artifact_ref='review.json')
    write(tmp_path/'review.json',{'primary_order':p['candidate_order_randomization']['randomized_order'],
          'primary_ranking':p['qualitative_ranking'],'alternate_order':s['alternate_order'],
          'alternate_ranking':s['alternate_ranking'],'rationale':'Synthetic qualitative comparison.'})
    s['review_artifact_sha256']=integrity.digest((tmp_path/'review.json').read_bytes())
    assert bmat_tournament_check.check(p,bundle=tmp_path)==[]
    (tmp_path/'review.json').write_text('{}',encoding='utf-8')
    assert 'TOURNAMENT_ALTERNATE_EVIDENCE_REQUIRED' in {f.code for f in bmat_tournament_check.check(p,bundle=tmp_path)}


@pytest.mark.parametrize('mutation,code', [('order','TOURNAMENT_ALTERNATE_ORDER_INVALID'),
    ('scores','TOURNAMENT_STABILITY_MISMATCH'),('elo','TOURNAMENT_ELO_RATING_MISMATCH'),
    ('rank','TOURNAMENT_RANKING_OVERRIDE_REASON_REQUIRED')])
def test_tournament_numeric_negative_controls(mutation,code):
    p=valid_tournament()
    if mutation=='order':p['order_sensitivity_check']['alternate_order']=p['candidate_order_randomization']['randomized_order']
    elif mutation=='scores':
        for r in p['order_sensitivity_check']['alternate_judge_scores']:
            for axis in __import__('bmat_tournament_math').AXES:r[axis]=0.0 if r['blinded_candidate_id']=='blind-17' else 1.0
    elif mutation=='elo':p['elo_input']['k_factor']=64
    else:p['final_ranking'][0]['rank'],p['final_ranking'][1]['rank']=2,1
    assert code in {f.code for f in bmat_tournament_check.check(p)}


def test_tournament_weighted_means_and_researcher_override():
    import bmat_tournament_math as maths
    p=valid_tournament();p['aggregation']={'method':'weighted-mean','axis_weights':dict.fromkeys(maths.AXES,1),'judge_weights':{'judge-a':1,'judge-b':2}}
    assert bmat_tournament_check.check(p)==[]
    p['final_ranking'][0]['rank'],p['final_ranking'][1]['rank']=2,1
    p['ranking_override_reason']='Researcher prioritizes the feasible assay within the current resource constraint.'
    assert bmat_tournament_check.check(p)==[]


@pytest.mark.parametrize('mode', ['plan','audit','run'])
def test_omics_modes_and_preexecution_gate(tmp_path,mode):
    args=argparse.Namespace(alias='omics-analysis-team',mode=mode,tier='full',track='tenx-gex',question='Synthetic routing',
            out=tmp_path,domain_pack='generic-biomedical',dry_run=True,validate=False,export='none',force=False)
    p=bmat_run.bmat_init_bundle.build_payloads(args.alias,mode,args.question,tmp_path);bmat_run.enrich_payloads(p,args)
    dag=p['workflow_dag.json'];node=next(n for n in dag['nodes'] if n['id']=='S2_execute')
    if mode!='run':
        assert node['phase']!='execute' and 'analysis_artifacts' not in node['outputs']
    else:
        assert node['agent']=='tenx-singlecell-specialist' and 'S1_smoke' in node['requires']
        state=p['run_state.json']
        for s in state['stages']:s['status']='pass'
        next(s for s in state['stages'] if s['id']=='S1_smoke')['status']='block'
        findings=[];bmat_validate.validate_workflow_dag_policy({'run_state':state,'workflow_dag':dag},findings)
        assert 'OMICS_PREEXECUTION_GATE_REQUIRED' in {f.code for f in findings}


def test_track_option_rejected_for_nonomics_alias():
    with pytest.raises(SystemExit):
        bmat_run.selected_omics_track(argparse.Namespace(alias='evidence-audit-team',track='bulk-rnaseq'))


def test_legacy_v2_parses_without_inferred_verification(tmp_path):
    b=fixture(tmp_path);data=loaded(b)
    corpus=data['source_corpus'];corpus['sources'][0]['evidence_spans'][0].pop('extraction')
    post=data['post_write_validation']
    for key in ('reviewed_final_ref','reviewed_final_sha256','reviewed_ledger_ref','reviewed_ledger_sha256',
                'coverage_review_instance_id','wording_policy','content_coverage'):
        post.pop(key,None)
    for payload,name in ((corpus,'source-corpus'),(post,'post-write-validation')):
        jsonschema.Draft202012Validator(read(SKILL/f'contracts/{name}.schema.json')).validate(payload)
    assert 'EVIDENCE_EXTRACTION_REQUIRED' in {c for c,_ in integrity.source_spans(corpus,b,{})}
    assert 'FINAL_REVIEW_STALE' in {c for c,_ in integrity.final_coverage(data,b)}
