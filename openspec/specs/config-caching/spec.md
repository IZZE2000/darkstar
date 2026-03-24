# Config Caching

## Purpose

Configuration caching with file modification time detection to reduce unnecessary disk I/O.

## Requirements

### Requirement: Config YAML is cached with file-mtime detection
The executor SHALL cache the parsed config and inverter profile in memory. Before each tick, the executor SHALL check the file modification timestamp of `config.yaml` and the active profile YAML. The config SHALL only be re-parsed from disk when the mtime has changed since the last read.

#### Scenario: Config file unchanged between ticks
- **WHEN** the executor starts a new tick
- **AND** `config.yaml` has not been modified since the last tick
- **THEN** the executor uses the cached config without reading from disk
- **AND** no YAML parsing occurs

#### Scenario: Config file modified between ticks
- **WHEN** the executor starts a new tick
- **AND** `config.yaml` has been modified since the last tick (mtime changed)
- **THEN** the executor re-reads and re-parses the config from disk
- **AND** the cached config is updated with the new values

#### Scenario: Profile YAML cached independently
- **WHEN** the executor starts a new tick
- **AND** the inverter profile YAML file has not been modified since the last read
- **THEN** the cached profile is reused without disk I/O or YAML parsing

#### Scenario: Profile switches when config changes profile name
- **WHEN** the user changes `inverter_profile` in config.yaml from `fronius` to `deye`
- **AND** the executor detects the config mtime change
- **THEN** the executor re-parses the config, detects the profile name change
- **AND** loads and caches the new profile YAML

#### Scenario: First tick after startup
- **WHEN** the executor starts for the first time
- **THEN** the config and profile are read from disk and cached
- **AND** subsequent ticks use the cache until a file changes
