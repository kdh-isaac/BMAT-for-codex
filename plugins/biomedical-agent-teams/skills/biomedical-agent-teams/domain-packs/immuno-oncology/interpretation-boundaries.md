# Immuno-Oncology Interpretation Boundaries

Use this pack to keep immuno-oncology and cell-therapy omics claims at the
right evidence ceiling. These rules are boundary conditions for claim ledgers,
source-corpus notes, omics manifests, and final wording.

## TME and Bulk-Proxy Boundaries

- Treat bulk tumor expression, deconvolution scores, and TME signatures as
  cohort-level association unless cell-type-resolved evidence supports a
  cellular mechanism.
- Do not convert immune-infiltration, checkpoint, cytotoxicity, exhaustion, or
  interferon signatures into tumor-intrinsic, T-cell-intrinsic, or CAR-T-
  intrinsic mechanisms without perturbation or product-level evidence.
- For survival or prognosis claims, record cohort source/version, endpoint,
  event/censor definition, grouping rule, covariates, event counts, and
  multiplicity handling before writing a high-confidence conclusion.
- For deconvolution outputs, name the proxy method and state whether it can
  distinguish tumor, immune, stromal, and treatment-product compartments.

## Single-Cell and Spatial Boundaries

- Require donor/sample-aware statistics for cross-patient or cross-treatment
  comparisons. Cell-level tests may describe patterns but must not become
  biological replicate evidence.
- Require ambient RNA, doublet, sample mapping, and annotation-validation notes
  before using marker genes to assign mechanism or prognosis.
- Keep ligand-receptor, trajectory, spatial-neighborhood, and cell-state results
  exploratory unless supported by perturbation, longitudinal, or independent
  validation evidence.

## CAR-T and Adoptive-Cell Therapy Boundaries

- Separate product-level phenotype, tumor-context association, patient outcome
  association, and manufacturing-process claims.
- Do not infer CAR-T product manufacturing, expansion, persistence, exhaustion,
  or killing mechanisms from tumor-biopsy TME association alone.
- For product-level claims, require the product source, assay timing, donor or
  patient unit, transduction/manufacturing context, and direct functional or
  molecular measurement.
- For clinical actionability, require clinician-reviewed context and do not
  present exploratory public-omics associations as treatment guidance.
