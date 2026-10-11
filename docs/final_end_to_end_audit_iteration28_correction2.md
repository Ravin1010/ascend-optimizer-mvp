# Iteration 28 — Section 8.0 wording correction audit

Date: 11 October 2026. Scope: proposal wording correction and this audit record only. Iteration 29 was not started.

## Parent and document revisions

- Repository: `Ravin1010/ascend-optimizer-mvp`, branch `main`.
- Parent SHA: `ede77d4d0165d0fb076463ee964c8bbe3e6cdf90`.
- Working tree was clean before the edit. The earlier Iteration 28 audits remain unchanged historical records.
- Existing Google document: [Proposal Initial Draft](https://docs.google.com/document/d/1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4).
- Revision before: `AHj4eMTuZTiqc2rS9d-KQDYuuHaeXhhCB9DZb7hSngAc98fQ4wVGX-t4yzhNCxVQy0S-ErWE5XB6pk3DoTLUuit2sKhJ8ecD4rgRD7lIauA`.
- Revision after: `AHj4eMS1IUyMt5eReN9DfndPNWT17NNkEB6dvBHaOdfaSqOj16C449FS0w8neYhnnQa-fw28hElcZCm013o9ySmdBMOnYrmTPv3Zl9E89Eg`.

## Exact authorized change

Section 8.0 — Differentiation of Ascend/0G contained this sentence:

> Controlled synthetic evaluation demonstrates where exact candidate costs and quotes alter selected allocations relative to simpler approaches, while typed feasibility and abstention expose the limitations of available evidence.

It was replaced with the approved sentence:

> Controlled synthetic evaluation demonstrates how exact candidate economics and explicit feasibility constraints affect recommendations relative to simpler approaches, while typed feasibility and abstention expose the limitations of available evidence.

A revision-required native Google Docs `replaceAllText` request replaced exactly one occurrence. The document was edited in place; no replacement document was created. No other proposal text was intentionally changed.

This removes the stale allocation-selection implication: the corrected quote-control pair selects Jaine 60% / idle 40% in both cases and demonstrates different assessed quote loss and profit, not a changed allocation. The fixed-cost controlled allocation sensitivity remains supported.

## Protected-content verification

- Read the current live document before writing and confirmed the exact stated revision and one unique stale sentence in Section 8.0. Read the document again after writing.
- Compared all **1,342 native paragraph texts**, including the existing TOC entries. Exactly one paragraph changed, solely by the approved sentence substitution. All other paragraph texts and all paragraph styles are identical.
- The stale sentence is absent; the approved replacement appears exactly once. Reviewed the quote/allocation wording: Section 6.5, Table 6.7 and Figure 6.4 continue to state the same-weight economic sensitivity, with no remaining controlled quote-pair allocation-change claim.
- Section 1.0 Objectives is text-identical. Its heading-to-next-section UTF-8 SHA-256 remains `18f83624a62184e2cc32316e89de8f3f70a8d1a4d9fbea28880a01c1a12478a0`.
- Section 6.5 and Table 6.7 are unchanged. Figure 6.4 and all other inline image identities and image metadata are unchanged, excluding regenerated authenticated `contentUri` download references. All **18 native tables** and **21 inline images** remain present.
- Sections 1–7, Sections 8.1–8.6 and Appendix A remain unchanged. The surrounding Section 8.0 wording is unchanged.
- Corrected numerical claims remain unchanged: mean +$46.32, disagreements 27/49 and 39/49, common-rescore sign counts 19/7/23. No result table, figure, value or caption was edited.

## PDF and TOC validation

- Exported the final live document to PDF after native readback.
- Final page count: **53**.
- Final PDF SHA-256: `770bd0b658f8a30b3aad1446136aaf16e127556e0e55630657e10fde1a51285d`.
- Compared layout-preserving extracted PDF text page-by-page against the previously verified Iteration 28 correction export. Only **page 44** differs. All other pages, including the TOC, Objectives, corrected Section 6 results, Section 8.6 and the complete Appendix, have identical extracted text.
- Visually inspected rendered pages **2–3** (native TOC), **44** (Section 8.0), **45** (Section 8.6), **46** (Appendix start) and **53** (Appendix end). The replacement is readable and fits within the existing page. No new clipping, overlap, broken captions or blank pages were observed. Inherited compact Appendix wrapping is unchanged.
- Pagination is unchanged: Section 8.0 remains page 44, Section 8.6 page 45, Appendix A page 46. TOC text/page references remain identical to the previously verified 61/61 reference baseline. **No TOC refresh was necessary or performed.**

## Repository and behavior boundary

The only repository change is this new audit file. No source, tests, optimizer, API, frontend, dashboard, Solidity, canonical metadata/evidence/runtime configuration, evaluation input, result output or generated result package was changed. Existing audit documents were not rewritten.

The five-strategy universe, Ascend `INTEGRATED_GATED / CLOSED`, corrected F1/F2 semantics, production fail-closed baseline and deployment boundary therefore remain as accepted at the parent commit. The parent audit's validated Conservative/Balanced/Aggressive 100%-idle production behavior is preserved; no technical suite or production replay was rerun for this wording-only change. Public deployment remains not required/planned.

Checks actually performed: revision-aware single-occurrence replacement; complete native paragraph/style comparison; protected Objectives digest; native table/image preservation; bounded quote-claim review; page-by-page PDF text comparison; PDF hash/page count; visual inspection; repository status and staged-path review; `git diff --check`.

No GitHub CI success is asserted. Actual statuses/check runs/workflows are queried after publication and reported separately.

**Iteration 28 correction-to-correction completed. Iteration 29 was not started.**
