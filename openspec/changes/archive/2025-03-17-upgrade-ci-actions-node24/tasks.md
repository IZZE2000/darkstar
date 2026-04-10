## 1. Upgrade ci.yml actions

- [x] 1.1 Update `actions/checkout` from `@v4` to `@v6` (4 occurrences across both files, but start with ci.yml)
- [x] 1.2 Update `actions/setup-python` from `@v5` to `@v6` (3 occurrences in ci.yml)
- [x] 1.3 Update `actions/setup-node` from `@v4` to `@v6` (1 occurrence in ci.yml)

## 2. Upgrade build-addon.yml actions

- [x] 2.1 Update `actions/checkout` from `@v4` to `@v6` (3 occurrences in build-addon.yml)
- [x] 2.2 Update `actions/setup-python` from `@v5` to `@v6` (1 occurrence in build-addon.yml)
- [x] 2.3 Update `docker/login-action` from `@v3` to `@v4`
- [x] 2.4 Update `docker/setup-qemu-action` from `@v3` to `@v4`
- [x] 2.5 Update `docker/setup-buildx-action` from `@v3` to `@v4`
- [x] 2.6 Update `docker/build-push-action` from `@v6` to `@v7`
- [x] 2.7 Update `softprops/action-gh-release` from `@v1` to `@v2`

## 3. Verify

- [x] 3.1 Confirm `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true` is retained in both workflow files (needed for `pnpm/action-setup@v4`)
