## ADDED Requirements

### Requirement: Kepler result merge is index-aligned and crash-safe
After the Kepler solver runs, the pipeline merges `result_df` columns back into `final_df` using index-aligned pandas assignment. The merge SHALL NOT use positional `.values` assignment. If `len(result_df) != len(future_df)`, the pipeline SHALL log an error at `ERROR` level describing the mismatch (including both lengths) and continue with index-aligned assignment so that matching slots are correctly populated.

#### Scenario: Normal case — equal lengths
- **WHEN** Kepler returns the same number of slots as `future_df` has rows and timestamps align
- **THEN** all columns from `result_df` are written into `final_df` with correct values for every row
- **AND** no error is logged

#### Scenario: Length mismatch — no crash
- **WHEN** `result_df` has fewer rows than `final_df` (e.g., due to duplicate timestamps from malformed price input)
- **THEN** the pipeline SHALL NOT raise a `ValueError`
- **AND** the pipeline SHALL log an `ERROR` message containing both lengths
- **AND** matched rows in `final_df` SHALL receive correct `result_df` values
- **AND** unmatched rows SHALL retain the NaN values from the join

#### Scenario: No positional assignment in result merge loop
- **WHEN** the pipeline writes Kepler result columns into `final_df`
- **THEN** each assignment uses `final_df[col] = result_df[col]` (index-aligned Series assignment)
- **AND** `result_df[col].values` (positional numpy array assignment) is never used
