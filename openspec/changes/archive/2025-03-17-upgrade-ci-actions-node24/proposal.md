## Why

GitHub Actions is deprecating Node.js 20 runtimes. Actions will be forced to run on Node.js 24 starting June 2, 2026. Our CI workflows use action versions that declare `node20`, producing deprecation warnings on every run. While the `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env var mitigates runtime behavior, bumping to native node24 action versions eliminates the warnings at the source and ensures long-term compatibility.

## What Changes

- Upgrade `actions/checkout` from `@v4` to `@v6`
- Upgrade `actions/setup-python` from `@v5` to `@v6`
- Upgrade `actions/setup-node` from `@v4` to `@v6`
- Upgrade `docker/login-action` from `@v3` to `@v4`
- Upgrade `docker/setup-buildx-action` from `@v3` to `@v4`
- Upgrade `docker/setup-qemu-action` from `@v3` to `@v4`
- Upgrade `docker/build-push-action` from `@v6` to `@v7`
- Upgrade `softprops/action-gh-release` from `@v1` to `@v2`
- Keep `pnpm/action-setup@v4` (no node24 version available yet)
- Keep `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` env var until `pnpm/action-setup` releases a node24 version

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — this is a CI infrastructure change with no spec-level behavior impact)

## Impact

- **Files**: `.github/workflows/ci.yml`, `.github/workflows/build-addon.yml`
- **Dependencies**: Requires GitHub-hosted runner v2.327.1+ (ubuntu-latest already satisfies this)
- **Risk**: Low. Major version bumps for these actions are typically runtime-only changes. The `softprops/action-gh-release` v1→v2 jump may have minor API differences worth verifying.
- **No application code changes** — only workflow YAML files are affected.
