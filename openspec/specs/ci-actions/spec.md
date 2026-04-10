## Purpose

Defines requirements for GitHub Actions CI/CD workflows to ensure compatibility with latest runner versions and eliminate deprecation warnings.

## Requirements

### Requirement: CI actions use node24-native versions

All GitHub Actions in `.github/workflows/ci.yml` and `.github/workflows/build-addon.yml` SHALL use the latest major version that natively declares node24, except where no node24 version is available.

#### Scenario: All actions at target versions
- **WHEN** the workflow files are inspected
- **THEN** the following action versions SHALL be present:
  - `actions/checkout@v6`
  - `actions/setup-python@v6`
  - `actions/setup-node@v6`
  - `docker/login-action@v4`
  - `docker/setup-buildx-action@v4`
  - `docker/setup-qemu-action@v4`
  - `docker/build-push-action@v7`
  - `softprops/action-gh-release@v2`
  - `pnpm/action-setup@v4` (unchanged — no node24 version available)

#### Scenario: Force flag retained for holdout actions
- **WHEN** `pnpm/action-setup` has no node24-native version
- **THEN** `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` SHALL remain in the workflow env block

#### Scenario: No deprecation warnings from upgraded actions
- **WHEN** a CI workflow runs after the upgrade
- **THEN** no Node.js 20 deprecation annotations SHALL appear for actions that were upgraded to node24-native versions
