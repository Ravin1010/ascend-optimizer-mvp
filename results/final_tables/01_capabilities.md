# Method selection capabilities

SYNTHETIC_EVALUATION_ONLY

| Feature | Highest Yield | Equal Weight | Legacy Linear | Policy-Aware Amount |
| --- | --- | --- | --- | --- |
| Decision sleeve | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Strategy gate | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Concentration | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Exact amount economics | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Fixed lifecycle costs | NOT_SUPPORTED | NOT_SUPPORTED | APPROXIMATED | SUPPORTED |
| Lp quote effects | NOT_SUPPORTED | NOT_SUPPORTED | APPROXIMATED | SUPPORTED |
| Admission evidence | APPROXIMATED | APPROXIMATED | APPROXIMATED | SUPPORTED |
| Range aware lp stress | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Legacy lp proxy | NOT_SUPPORTED | NOT_SUPPORTED | LEGACY_ONLY | NOT_SUPPORTED |
| Staking stress | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED | SUPPORTED |
| Exit time | NOT_SUPPORTED | NOT_SUPPORTED | LEGACY_ONLY | SUPPORTED |
| Cash deadline | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Idle | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| Amount specific feasibility | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |
| Selected point revalidation | NOT_SUPPORTED | NOT_SUPPORTED | NOT_SUPPORTED | SUPPORTED |

Selection-time capabilities from the accepted contract. Common post-selection diagnostics do not add selection capabilities. APPROXIMATED/LEGACY_ONLY semantics remain in data/final_evaluation_contract.md.
