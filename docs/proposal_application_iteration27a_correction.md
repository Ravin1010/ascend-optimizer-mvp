# Iteration 27A — Narrow correction audit

Status: **CORRECTION_APPLIED**. Iteration 28 was not started.

- Parent commit: `2758a109d5450a0c6a71b565b8f94c89ae9306e6`.
- Existing Google Doc: [Proposal Initial Draft](https://docs.google.com/document/d/1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4/edit).
- Revision before: `AHj4eMRaDTOhigia0rZbAocOaGpxRiB8YNfZpGEQiIS-noNUmBd88bV5gB8j5B0JOfW91RR_IBh8YIw15NirukKOz6HqhwOtWgvedF26uWs`.
- Revision after, confirmed by fresh native read: `AHj4eMRLHvuKZIPWMc1POIqMkzGuh7z5K92XCNry0jJMta677zDwdC091BvsHdTh7X_59UN26slRRfFH7Wc_fgnrEHpPWzpurFPtKVkSz48`.
- This supersedes the retained stale-artwork caveat in the original 27A application audit; that original audit remains historical.

## Exactly four corrections

1. **Figure 4.1 artwork:** terminal label changed from “On-chain Execution” to “Current-Request Advisory Result”. Other workflow labels and diagram topology retained.
2. **Figure 5.1 artwork:** “LIVE integration boundary” becomes “Source-level integration boundary”; “live a0G route” becomes “Intended a0G route”; the external-path note now states “External SourceCore/a0G runtime unresolved.” The artwork title/header/footer are qualified as source-level/intended architecture, runtime unresolved and Ascend gate CLOSED. Boxes, paths and technical relationships retained.
3. **Figure 5.3 artwork:** title becomes “Ascend a0G Source-Level Deposit and Withdrawal Architecture”. Live integration labels become source-level; vault headers become source-level architecture. External-path note and summary explicitly retain unresolved runtime registration and Ascend CLOSED. The existing wrap, external share issuance, withdrawal request, epoch/queue/funding, claim W0G, unwrap and native-0G return path is preserved. External Ascend accounting still determines shares, without a fixed 1:1 issuance assumption.
4. **Section 8.6 future-work wording only:** opening conclusion text and heading retained. Final replacement wording:

> Future work may include qualified observational economics and freshness evidence, direct W0G input, ETH/BTC and broader multi-asset input normalization, whole-portfolio optimization, direct standalone Symbiotic allocation, and any future public/live execution or deployment. None of these are current implemented capabilities, and public deployment is not a required capstone milestone.

## In-place image replacement

The connector's local-image sidecar supports inline insertion, but rejected a native replaceImage upload before any mutation. Each affected image was therefore deleted as a single inline object and its replacement inserted at exactly the same document index, in its existing paragraph. Required revision controls guarded each successful write.

| Figure | Original object | Replacement object | Result dimensions (pt) | Image SHA-256 |
| --- | --- | --- | --- | --- |
| 4.1 | kix.uflv6d4360hl | kix.sii7msp3vgle | 240.027386 × 320.773926 | 64f92d9d3c6f67b99f7cbc22580942357bac2d92e7247be42e911d2b1dab9bcd |
| 5.1 | kix.abmcih9qxosl | kix.jzz8vmfvtzkg | 416 × 312 | 2a91538e7d2a8c5ff616e6746bcbd9f1f7cad20f9a78018fa3990b6ad471dfcb |
| 5.3 | kix.i46legk2tp7c | kix.c94s1hmwzvbd | 416 × 312 | 9f84d954a749d266de39339208154c47a671563adce786d0e5292b2f7388c578 |

The source diagrams were used as image-edit references, with only the specified stale wording/architectural qualifications changed. Figure 4.1 retains its original height; width is about 5.3% narrower because Docs preserves the replacement image's aspect ratio rather than the original cropped image's width. It remains centered in the original paragraph. Figures 5.1 and 5.3 retain exact dimensions. No redesign, unrelated figure deletion or caption change occurred. Visual review confirms the specified stale in-image phrases are absent.

## Protected-content verification

- Full native document text before/after is exactly equal after applying only the Section 8.6 future-work substitution. Thus Section 1.0, front matter, Sections 2–7, Sections 8.0–8.5, Section 5.5, all accepted captions and the empty TOC placeholder remain text-for-text unchanged.
- Section 1.0 heading-to-next-section SHA-256 remains `18f83624a62184e2cc32316e89de8f3f70a8d1a4d9fbea28880a01c1a12478a0`.
- Native paragraph/style comparison passed outside the amended 8.6 paragraph, allowing only the three replacement inline-object identities and index shifts.
- All **18 native tables** are structurally/textually identical after removing shifted indexes. Frozen numerical results and the five-strategy category/gate mapping are unchanged.
- All **18 unrelated inline images** retain their object metadata, ignoring expiring content retrieval URLs. Total image count remains **21**.
- All **230 previously tracked repository files** compared byte-for-byte with the parent before adding this audit: unchanged. This includes code, tests, frontend, Solidity, strategy metadata, runtime configuration, canonical evidence, all assumptions and frozen Iteration 23/24 artifacts.
- Native structure/repository verification: **694 checks passed**, plus the full-text substitution comparison and exact Objectives hash check.
- First four strategies remain INTEGRATED_ALLOCATABLE / CONDITIONAL; Ascend remains INTEGRATED_GATED / CLOSED. No production behavior or evidence changes.

## Checks actually run

- `python -m pytest -q tests/test_application_contract.py -k production_fail_closed_all_profiles`: **3 passed, 61 deselected**. Conservative, Balanced and Aggressive remain 100% idle.
- `python tools/run_final_evaluation.py --check`: **49 scenarios / 196 rows**, byte-for-byte replay passed.
- `python tools/generate_final_results.py --check`: **7 tables / 8 figures / 34 files**, exact replay passed.
- `python tools/audit_deployment_history.py --check`: audit provenance, pinned history and frozen-file checks passed.
- `python tools/deployment_preflight.py`: five strategies, intended chain 16661, unresolved runtime bindings, NOT_DEPLOYED, public deployment not required.
- `git diff --check`: passed.
- No GitHub CI/status-check claim is made. Full Python, frontend and Hardhat suites were not run for this documentation-only correction.

## PDF verification and remaining caveats

The corrected live Google Doc was exported to PDF: **52 pages**, SHA-256 `b5b52c0e8879ae6fa828be4e0e299a5be3be33da3e52a9fa978b84236093356b`. Rendered pages **20 (Figure 4.1), 24 (Figure 5.1), 27 (Figure 5.3), and 44 (Section 8.6)** were visually inspected. Images preserve their aspect ratios and original placement/page flow; captions remain attached and unchanged. No clipping, overflow, distortion or broken caption was observed. Geometry scan of all 52 pages found **0 out-of-page text/image blocks**.

The empty TOC placeholder remains untouched, as explicitly required; a native TOC remains a final-submission/editor task. The original audit's illustrative reward-price corroboration caveat remains outside this correction. Dense inherited artwork retains its existing compact presentation. The PDF and replacement image bytes were used for review and embedded in the existing Doc; no frozen result/image files were replaced in the repository.

**This correction changes only three proposal artworks and Section 8.6 future-work wording. Optimizer behavior, code, data, evidence, deployment state, dashboard, frozen numerical results and canonical strategy taxonomy/gates remain unchanged. Iteration 28 was not started.**
