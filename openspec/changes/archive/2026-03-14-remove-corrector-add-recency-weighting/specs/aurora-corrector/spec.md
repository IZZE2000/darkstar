## REMOVED Requirements

### Requirement: Slot start type conversion
**Reason**: The entire AURORA corrector capability is being removed. The corrector layer (stats bias + ML error model) is architecturally coupled to the base model version, causing stale corrections after every base model retrain. The base model with recency weighting replaces the corrector's purpose.
**Migration**: No migration needed. Base model predictions are used directly as final values. The `final.load_kwh` and `final.pv_kwh` fields in the forecast API remain but now equal the base model output without any correction applied. Correction columns in the DB schema are preserved but unused.
