# Specification - DX14: Config Soft Merge Improvement

## Background
Darkstar uses a `config.default.yaml` to define available settings and a user-provided `config.yaml` for local overrides. When new settings are added to the project, they must be "soft-merged" into the user's existing configuration.

## Problem
The current soft-merge implementation (likely using standard dictionary updates or simple YAML dumps) does not preserve the structural organization, comments, or positioning of keys relative to the default configuration. This leads to disorganized `config.yaml` files that are difficult for users to manage.

## Objectives
- **Preserve Structure**: New keys should be inserted into `config.yaml` at the same relative position they occupy in `config.default.yaml`.
- **Preserve Comments**: The merging process must respect and preserve existing comments in both files (where applicable) and ideally copy new comments from the default file for new keys.
- **Organization**: Maintain the grouping of settings (e.g., `battery`, `input_sensors`, `nordpool`) as defined in the source of truth.

## Technical Constraints
- Use `ruamel.yaml` (already in `requirements.txt`) which supports round-trip loading and comment preservation.
- Ensure 100% backward compatibility with existing `config.yaml` files.
- Must be robust against malformed or partially missing user configurations.

## Success Criteria
- New keys added to `config.default.yaml` appear in the user's `config.yaml` in the correct section and order.
- Existing user values are never overwritten by defaults.
- Formatting and comments in the user's file are preserved for existing keys.
