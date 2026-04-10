## Context

GitHub Actions is transitioning from Node.js 20 to Node.js 24 as the runtime for JavaScript-based actions. Our two workflow files (`.github/workflows/ci.yml` and `.github/workflows/build-addon.yml`) use 9 distinct third-party actions, most of which currently declare `node20` in their metadata. Commit `adcac97` added `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` as a stopgap, which forces node24 execution but doesn't eliminate the deprecation annotations.

## Goals / Non-Goals

**Goals:**
- Eliminate all Node.js 20 deprecation warnings from CI runs
- Pin all actions to their latest stable major versions with native node24 support
- Maintain identical CI behavior (lint, test, build, release)

**Non-Goals:**
- Upgrading the frontend Node.js version (`node-version: '20'` in lint job) — separate concern
- Removing `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` — still needed for `pnpm/action-setup@v4`
- Changing CI workflow structure or adding new jobs

## Decisions

### 1. Bump all actions to latest major version (not pin to exact patch)

Use `@v6` style tags, not `@v6.0.2`. Major version tags float to the latest patch, which is the convention for GitHub Actions and ensures automatic security fixes.

**Alternative considered**: Pinning to exact SHA — more secure but high maintenance burden for a small project.

### 2. Keep `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` env var

`pnpm/action-setup@v4` has no node24 release yet. The env var ensures it runs on node24 despite declaring node20. Remove it once pnpm releases a node24 version.

### 3. Upgrade `softprops/action-gh-release` from v1 to v2

v1 is unmaintained. v2 is a major version jump but our usage (body_path, draft, prerelease) is straightforward and should be compatible. Verify after upgrade that release creation still works on a tag push.

## Risks / Trade-offs

- **`softprops/action-gh-release` v1→v2 API changes** → Mitigation: Our usage is basic (body_path, draft, prerelease flags). Review v2 changelog before merging. Test with a tag push to verify.
- **`docker/build-push-action` v6→v7 breaking changes** → Mitigation: Our usage is standard (context, file, platforms, push, tags, cache-from). Low risk but verify build output.
- **Runner version requirement** → All node24 actions require runner v2.327.1+. `ubuntu-latest` already exceeds this. Only a risk if we ever use self-hosted runners.
