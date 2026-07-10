# Independent Review Policy (v2)

Use this policy whenever a BMAT workflow records review, validation, audit,
red-team, or independent-verification status. It governs process evidence; it
does not certify scientific truth or replace expert judgment, experimental
validation, statistics, IRB/IACUC review, or regulatory review.

## Non-negotiable rule

A role name, reviewer prompt, second pass, new task, or spawned subagent is not
proof of independence. Independence is established only by a complete,
hash-bound review receipt whose runtime metadata supports its declared
`independence_class`.

Treat `independence_class` as a derived classification, not a reviewer
self-attestation. The validator compares reviewer and authoring identity tuples,
sessions, actor type, context-sharing flag, fixture status, and receipt status
before accepting `independent_review_eligible`.

The canonical classes are:

| `independence_class` | meaning | `independent_review_eligible` | Full protocol use |
|---|---|---:|---|
| `same-model-self-review` | the authoring model reviews its own work in the authoring context | `false` | never |
| `same-model-separate-context` | the same model family/version reviews a bounded artifact snapshot in a separate context | `false` | supplementary only |
| `separate-model` | a different identified model reviews a bounded snapshot in a separate execution context | `true` | eligible with a valid receipt |
| `external-tool` | an identified external review/validation tool evaluates the bounded snapshot and returns review findings | `true` | eligible with a valid receipt |
| `human` | an identified human reviewer evaluates the bounded snapshot | `true` | eligible with a valid receipt |

`same-model-separate-context` may improve error detection, but correlated model
judgment remains a material limitation. Never relabel it as independent review.

## Required v2 receipt

Every review instance in `review_artifact_manifest.json` must satisfy
`contracts/review-artifact-manifest.schema.json` and record all of the
following:

- identity: `instance_id`, `agent_id`, `actor_type`, `provider`, `model`, and
  `model_version`;
- author identity: `authoring_provider`, `authoring_model`,
  `authoring_model_version`, `authoring_execution_session_id`, and
  `authoring_identity_available`;
- runtime identity: `execution_surface`, `execution_session_id`, and
  `spawn_event_id`;
- bounded input: `input_scope`, `input_artifact_refs`, and the
  `input_artifact_sha256` map;
- frozen instructions: `prompt_template_ref` and `prompt_template_sha256`;
- output: `output_artifact` and `output_sha256`;
- work performed: `checks_run`, `changed_claim_ids`, `ledger_handoff`, and
  `results_integration_rows`;
- independence: `independence_class`, `independent_review_eligible`, and
  `fixture_only`, and `authoring_context_shared`;
- timing and runtime evidence: `started_at`, `completed_at`,
  `runtime_receipt_ref`, and `runtime_receipt_sha256`;
- an explicit `limitations` statement.

The referenced runtime receipt must satisfy
`contracts/review-runtime-receipt.schema.json`. Its instance/run/plugin IDs,
actor and runtime identity, timing, fixture status, and authoring-context flag
must equal the manifest row. The authoring-identity tuple must also match. Only
a `status=success` receipt with
`runtime_metadata_available=true` can support an eligible class.

The runtime must not invent unavailable provider, model, version, session, or
spawn metadata, including authoring identity. Record the literal value
`unavailable`, classify the review as
non-independent, set `independent_review_eligible=false`, and downgrade the
workflow label with a structured reason. Use
`receipt_source=runtime-unavailable` and
`runtime_metadata_available=false` in the runtime receipt. A receipt with
unavailable model or session identity cannot claim `separate-model`.

## Hash and path controls

1. Every `input_artifact_refs` item must have exactly one same-key entry in the
   `input_artifact_sha256` map. Extra hash-map keys are invalid.
2. All referenced files must resolve inside the workflow bundle. Absolute
   paths, path traversal, symlink escape, and missing files are invalid.
3. SHA-256 values are lowercase 64-character hex digests of the exact file
   bytes. The validator recomputes them; a descriptive digest is not enough.
4. `prompt_template_sha256`, `output_sha256`, and
   `runtime_receipt_sha256` must match their referenced files.
5. Write the reviewed output and runtime receipt first, compute their hashes,
   then write the manifest. Do not point `output_artifact` or
   `runtime_receipt_ref` at the manifest or handoff receipt that contains its
   own hash; self-referential hashes are invalid.
6. If an input, prompt, output, or runtime receipt changes, the old review
   receipt is stale and cannot support release.

## Class-specific controls

### Same-model classes

- `same-model-self-review` requires `actor_type=model` and
  `authoring_context_shared=true`.
- `same-model-separate-context` requires `actor_type=model` and
  `authoring_context_shared=false`.
- When identity is available, both same-model classes require exact equality of
  reviewer and authoring provider/model/version. Separate-context additionally
  requires a different execution session.
- Both classes require receipts and hashes for auditability, but both set
  `independent_review_eligible=false`.

### Separate model

- Require `actor_type=model`, a distinct identified provider/model/version,
  a distinct execution session, a real spawn event, and
  `authoring_context_shared=false`.
- Require `authoring_identity_available=true`; the reviewer
  provider/model/version tuple must differ from the recorded authoring tuple.
- “Different agent name” or “spawned subagent” does not establish a different
  model. Compare the runtime receipt with the authoring runtime identity.
- If the authoring model identity is unavailable, separate-model independence
  cannot be proven; downgrade rather than infer it.

### External tool

- Require `actor_type=external-tool`, identified provider/tool version,
  successful execution metadata, and a preserved runtime output receipt.
- A source resolver, database lookup, schema validator, or tool call that only
  retrieves evidence is not automatically an independent scientific review.
  It may prove source identity or process conformance, but it earns the
  `external-tool` review class only when the tool actually evaluates the
  declared review checks against the bounded input snapshot.
- Tool success and scientific support are separate findings. Preserve tool
  limitations and negative results.

### Human

- Require `actor_type=human`, a stable non-secret reviewer identifier and
  role, the reviewed input snapshot, a signed or otherwise attributable review
  artifact, and the hash-bound runtime/human-review receipt.
- Do not place unnecessary PII in public artifacts. A local pseudonymous actor
  ID is sufficient when policy requires de-identification.

## Full protocol gate

`Full protocol followed` requires at least one complete review instance whose:

- class is `separate-model`, `external-tool`, or `human`;
- `independent_review_eligible` is `true`;
- `fixture_only` is `false`;
- schema, runtime metadata, local paths, and all hashes validate;
- input artifacts match the current workflow run and plugin version;
- output records non-empty checks and a ledger handoff; and
- changed claims are represented in `results_integration.json` before final
  synthesis.

No number of self reviews or same-model separate-context passes can be combined
to satisfy this gate. If an eligible surface is unavailable, use a structured
skip/downgrade reason and a lower `run_state.final_label`; free-text rationale
alone is not a gate input.

## Review conduct

1. Freeze review criteria and prompt template before the review starts.
2. Give the reviewer only the declared, hash-bound input scope needed for its
   lane; do not silently share private or patent-sensitive context.
3. Compare final prose with claim-ledger IDs and `allowed_final_wording`.
4. Do not add evidence during review without first updating source corpus,
   source verification, evidence spans, and claim support.
5. Preserve contradictions, negative evidence, rejected recommendations,
   skipped checks, and limitations through integration.
6. Every `changed_claim_ids` item must have a matching results-integration row.
7. Report process-gate status, source-identity verification, claim-entailment
   review, independent-review status, and scientific-truth certification as
   separate concepts.

## FM10 handling

When reviewer/writer self-ratification (FM10) is detected, do not repair the
label with prose. Run an eligible receipt-backed review if available, or set
`independent_review_eligible=false`, preserve the limitation, and downgrade or
block high-confidence release as required by the workflow policy.
