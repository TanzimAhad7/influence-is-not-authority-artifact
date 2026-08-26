# P0b-3-ACT shadow sensitivity pre-analysis freeze

- input SHA-256: `bc8c17c257b00a12295c54384c9ce7bc3490f8d6c1f1d3b89aee36641253746a`
- denominators: `{'benign': 37, 'attack': 587}`
- endpoint: `shadow_any_flag` / `COMPLETION_PLUS_TOOL_CALL`
- known pre-split overall shadow activation from frozen P0b-3: `538/624`
- benign/attack shadow outcomes were not aggregated in this freeze stage
- zero model calls; report regardless of shape; no CI/p-value/tuning
- freeze JSON SHA-256: `87d3e83efdd6637a9f57931beeb309acb24c7936eecadd59a47cb54321349968`
