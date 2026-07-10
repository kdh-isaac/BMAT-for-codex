# Migrating BMAT bundles from v1 to v2

BMAT v1.2.0 release validation requires v2 release artifacts. The migration
tool performs a conservative structural conversion into a new directory. It
does not edit the source bundle and does not overwrite an existing destination
by default.

## Safe migration

From a clean repository checkout:

```bash
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_migrate_bundle.py --source path/to/bundle-v1 --out path/to/bundle-v2
```

PowerShell uses the same arguments on one line:

```powershell
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_migrate_bundle.py --source .\bundle-v1 --out .\bundle-v2
```

Keep the emitted migration report and re-verification list with the migrated
bundle. Compare the source and output before adding new evidence. If the output
path already exists, choose another path; do not use migration as an in-place
rewrite.

## Conservative mapping rules

| v1 condition | v2 migration result |
| --- | --- |
| Missing source verification | `not-checked`/`unknown` state, release-ineligible, added to the re-verification list |
| Offline or synthetic fixture | Remains `fixture_only=true`, `identifier_status=not-checked`, and `release_eligible=false` |
| Missing reviewer runtime identity | Recorded as unavailable and non-independent; never inferred from an agent name or spawn description |
| Missing file or output digest | Left unresolved and listed for regeneration; no digest is invented |
| Missing artifact identity | Populated only when it can be derived from the source bundle without contradicting it; otherwise reported as unresolved |
| Legacy free-text skip reason | Preserved for context and mapped to a structured reason only when the mapping is unambiguous |
| Legacy claim support | Preserved as non-release context until a source-owned evidence span and seven-axis scope assessment are supplied |

The converter never synthesizes a live lookup, human review, model identity,
claim entailment decision, successful tool receipt, or scientific validation.
Migration success means that the structural conversion completed, not that the
result is release-ready.

## Re-verification workflow

1. Review the migration report and every item in the re-verification list.
2. Resolve source identities through an eligible live tool, attributable human
   review, or hash-bound local snapshot. Keep fixtures release-ineligible.
3. Add source-owned evidence spans and rebuild claim-support rows, including
   all seven scope axes and bounded final wording.
4. Re-run any independent review against frozen v2 input artifacts. Preserve
   author/reviewer runtime identities and input, prompt, output, and receipt
   hashes.
5. Regenerate `bundle_manifest.json` only after all release artifacts are
   final:

   ```bash
   python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_bundle_manifest.py --bundle path/to/bundle-v2
   ```

6. Run non-release validation first, then the release gate:

   ```bash
   python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_validate.py --bundle path/to/bundle-v2
   python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_validate.py --bundle path/to/bundle-v2 --release
   ```

Any post-review change to a reviewed input invalidates the old hashes. Repeat
the affected review and regenerate the bundle manifest instead of editing hash
values by hand.

## Compatibility boundary

Non-release tooling may inspect legacy artifacts to explain migration work, but
v1 artifacts cannot satisfy the v1.2.0 release gate. Preserve the original v1
bundle as the audit source and treat the migrated v2 directory as a new derived
artifact.
