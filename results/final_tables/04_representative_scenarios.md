# Representative frozen scenario results

SYNTHETIC_EVALUATION_ONLY

| Scenario ID | Method | Selected allocation | Idle | Common net profit USD | LP absolute stress | Deadline state | Constraint / rejection diagnostic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FIXED_100 | Highest Yield | Native 60.0% | 40.0% | -$13.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_100 | Equal Weight | Native 60.0% | 40.0% | -$13.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_100 | Legacy Linear | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| FIXED_100 | Policy-Aware Amount | None (idle) | 100.0% | $0.00 | 0.0% | NOT_REQUESTED | Idle selected; exclusions below are diagnostics, not isolated causes; Candidate exclusion: lp_absolute_stress |
| FIXED_1000 | Highest Yield | Native 60.0% | 40.0% | $95.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_1000 | Equal Weight | Native 60.0% | 40.0% | $95.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_1000 | Legacy Linear | Native 60.0% | 40.0% | $95.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_1000 | Policy-Aware Amount | Native 60.0% | 40.0% | $95.00 | 0.0% | NOT_REQUESTED | concentration; Candidate exclusion: lp_absolute_stress |
| FIXED_ZERO_CONTROL | Highest Yield | Native 60.0% | 40.0% | $12.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_ZERO_CONTROL | Equal Weight | Native 60.0% | 40.0% | $12.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_ZERO_CONTROL | Legacy Linear | Native 60.0% | 40.0% | $12.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| FIXED_ZERO_CONTROL | Policy-Aware Amount | Native 60.0% | 40.0% | $12.00 | 0.0% | NOT_REQUESTED | concentration; Candidate exclusion: lp_absolute_stress |
| QUOTE_CURVE | Highest Yield | Jaine 60.0% | 40.0% | $56.80 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| QUOTE_CURVE | Equal Weight | Jaine 60.0% | 40.0% | $56.80 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| QUOTE_CURVE | Legacy Linear | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced; JAINE_LP_0G_USDC:slippage_exceeds_profile_limit; OKU_LP_0G_USDC:slippage_exceeds_profile_limit |
| QUOTE_CURVE | Policy-Aware Amount | Jaine 10.0% | 90.0% | $13.30 | 1.6% | NOT_REQUESTED | No selected boundary |
| QUOTE_CONSTANT_CONTROL | Highest Yield | Jaine 60.0% | 40.0% | $114.40 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| QUOTE_CONSTANT_CONTROL | Equal Weight | Jaine 60.0% | 40.0% | $114.40 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| QUOTE_CONSTANT_CONTROL | Legacy Linear | Jaine 60.0% | 40.0% | $114.40 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| QUOTE_CONSTANT_CONTROL | Policy-Aware Amount | Jaine 60.0% | 40.0% | $114.40 | 9.8% | NOT_REQUESTED | concentration; Candidate exclusion: lp_absolute_stress |
| LP_PROGRESSION_CONSERVATIVE | Highest Yield | Jaine 40.0% | 60.0% | $73.96 | 6.5% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_CONSERVATIVE | Equal Weight | Jaine 40.0% | 60.0% | $73.96 | 6.5% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_CONSERVATIVE | Legacy Linear | Jaine 31.5% | 68.5% | $57.19 | 5.1% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_CONSERVATIVE | Policy-Aware Amount | Jaine 30.0% | 70.0% | $54.34 | 4.9% | NOT_REQUESTED | Candidate exclusion: lp_absolute_stress; Candidate exclusion: staking_stress |
| LP_PROGRESSION_BALANCED | Highest Yield | Jaine 60.0% | 40.0% | $112.96 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_BALANCED | Equal Weight | Jaine 60.0% | 40.0% | $112.96 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_BALANCED | Legacy Linear | Jaine 60.0% | 40.0% | $112.96 | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_BALANCED | Policy-Aware Amount | Jaine 60.0% | 40.0% | $112.96 | 9.8% | NOT_REQUESTED | concentration; Candidate exclusion: lp_absolute_stress |
| LP_PROGRESSION_AGGRESSIVE | Highest Yield | Jaine 80.0% | 20.0% | $151.64 | 13.0% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_AGGRESSIVE | Equal Weight | Jaine 80.0% | 20.0% | $151.64 | 13.0% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_AGGRESSIVE | Legacy Linear | Jaine 80.0% | 20.0% | $151.64 | 13.0% | NOT_SUPPORTED | Final policy not enforced |
| LP_PROGRESSION_AGGRESSIVE | Policy-Aware Amount | Jaine 80.0% | 20.0% | $151.64 | 13.0% | NOT_REQUESTED | concentration |
| DEADLINE_STAKING_1 | Highest Yield | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_1 | Equal Weight | Native 25.0%, Gimo 25.0%, Jaine 25.0%, Oku 25.0% | 0.0% | $10.29 | 7.1% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_1 | Legacy Linear | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_1 | Policy-Aware Amount | None (idle) | 100.0% | $0.00 | 0.0% | COMPATIBLE_MODELLED | Idle selected; exclusions below are diagnostics, not isolated causes; Candidate exclusion: cash_deadline; Candidate exclusion: lp_absolute_stress |
| DEADLINE_STAKING_8 | Highest Yield | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_8 | Equal Weight | Native 25.0%, Gimo 25.0%, Jaine 25.0%, Oku 25.0% | 0.0% | $10.29 | 7.1% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_8 | Legacy Linear | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_8 | Policy-Aware Amount | Native 60.0% | 40.0% | $28.15 | 0.0% | COMPATIBLE_MODELLED | concentration; Candidate exclusion: cash_deadline; Candidate exclusion: lp_absolute_stress |
| DEADLINE_STAKING_15 | Highest Yield | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_15 | Equal Weight | Native 25.0%, Gimo 25.0%, Jaine 25.0%, Oku 25.0% | 0.0% | $10.29 | 7.1% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_15 | Legacy Linear | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| DEADLINE_STAKING_15 | Policy-Aware Amount | Native 60.0%, Gimo 40.0% | 0.0% | $43.54 | 0.0% | COMPATIBLE_MODELLED | concentration; staking_stress; Candidate exclusion: lp_absolute_stress |
| NEGATIVE | Highest Yield | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| NEGATIVE | Equal Weight | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| NEGATIVE | Legacy Linear | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| NEGATIVE | Policy-Aware Amount | None (idle) | 100.0% | $0.00 | 0.0% | NOT_REQUESTED | Idle selected; exclusions below are diagnostics, not isolated causes; Candidate exclusion: lp_absolute_stress |
| MISSING_COST | Highest Yield | Jaine 60.0% | 40.0% | NOT_ASSESSED (LIMITED) | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| MISSING_COST | Equal Weight | Jaine 60.0% | 40.0% | NOT_ASSESSED (LIMITED) | 9.8% | NOT_SUPPORTED | Final policy not enforced |
| MISSING_COST | Legacy Linear | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced; JAINE_LP_0G_USDC:optimizer_eligible=False; JAINE_LP_0G_USDC:MISSING_COST:entry_gas |
| MISSING_COST | Policy-Aware Amount | None (idle) | 100.0% | $0.00 | 0.0% | NOT_REQUESTED | Idle selected; exclusions below are diagnostics, not isolated causes; JAINE_LP_0G_USDC:ECONOMICS_UNAVAILABLE: MISSING_COST:entry_gas |
| ASCEND_ATTRACTIVE | Highest Yield | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Ascend gate CLOSED; Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| ASCEND_ATTRACTIVE | Equal Weight | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Ascend gate CLOSED; Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| ASCEND_ATTRACTIVE | Legacy Linear | None (idle) | 100.0% | $0.00 | 0.0% | NOT_SUPPORTED | Ascend gate CLOSED; Idle selected; exclusions below are diagnostics, not isolated causes; Final policy not enforced |
| ASCEND_ATTRACTIVE | Policy-Aware Amount | None (idle) | 100.0% | $0.00 | 0.0% | NOT_REQUESTED | Ascend gate CLOSED; Idle selected; exclusions below are diagnostics, not isolated causes; Candidate exclusion: lp_absolute_stress |
| TIE | Highest Yield | Gimo 60.0%, Jaine 40.0% | 0.0% | $100.00 | 6.5% | NOT_SUPPORTED | Final policy not enforced |
| TIE | Equal Weight | Native 25.0%, Gimo 25.0%, Jaine 25.0%, Oku 25.0% | 0.0% | $100.00 | 7.1% | NOT_SUPPORTED | Final policy not enforced |
| TIE | Legacy Linear | Native 40.0%, Gimo 60.0% | 0.0% | $100.00 | 0.0% | NOT_SUPPORTED | Final policy not enforced |
| TIE | Policy-Aware Amount | Native 60.0%, Gimo 40.0% | 0.0% | $100.00 | 0.0% | NOT_REQUESTED | concentration; staking_stress; Candidate exclusion: lp_absolute_stress |

Common profit is an exact-allocation post-selection rescore. LP stress for baselines/legacy is posthoc, not enforced final risk. Unsupported deadline checks are not passes. Raw row identity: (scenario ID, method ID).
