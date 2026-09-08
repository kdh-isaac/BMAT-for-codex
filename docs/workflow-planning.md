# Workflow planning and installed validation

BMAT's runner creates a plan and editable artifacts. It does not automatically
execute the role prompts or establish that a review took place. The adapter
can run one explicitly supplied command and preserve its output.

| Request | Generated plan |
| --- | --- |
| quick + compact | Context, one inline specialist, final check; no formal tournament or independent-review claim |
| standard/plan + compact | Source and specialist stages retained; dedicated independent reviewer lanes omitted |
| deep, audit, run, or full tier | Complete command DAG and its required review lanes |

The CLI prints stage count, scaffold file count, and required review-lane count.
These are planning requirements, not completed calls or granted runtime budget.
Evidence, safety, and release gates still apply to actual claims in every mode.
Use audit/full for high-confidence or formal review work. For omics, quick is
conceptual only; use plan/run/audit for a substantive analysis workflow.

Idea discovery in quick/compact uses hypothesis-ideation. Other idea-discovery
plans select hypothesis-tournament and create an empty draft tournament file.
Drafts have no invented candidates, random seeds, scores, or ranking. Complete
the real tournament and set status to complete before release. Missing files
and drafts cannot satisfy the tournament release gate. Existing completed v2
tournaments without a status field continue to validate as completed artifacts.

The artifact registry and workflow planning policy are shared Python modules.
The bundle validator calls the same tournament checks as the standalone CLI.
Domain failure-mode availability records file presence; loaded stays false
until the executing agent actually reads the selected document.

From the installed plugin directory:

```bash
python -m pip install "jsonschema>=4.18,<5" "pytest>=8,<9"
python -B skills/biomedical-agent-teams/scripts/bmat_selftest.py --root . --release
python -B -m pytest -p no:cacheprovider skills/biomedical-agent-teams/tests -q
```

The default self-test is a dependency-free smoke. Its smoke_passed status is
separate from release_passed. An artifact release still requires running
bmat_validate.py --release on that artifact bundle, not just package fixtures.
Repository marketplace tests are maintained outside the installed test suite.

## Current 1.2.2 policy

See [the supervised release integrity contract](release-integrity-1.2.2.md).
Schema 2.0 remains readable; current release/Full validation requires the new
review, final-snapshot, and extraction bindings. Do not synthesize missing
verification records when migrating older bundles.
