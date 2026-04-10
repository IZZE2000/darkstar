## 1. Move the file

- [x] 1.1 Move `data/regions.json` → `ml/regions.json`
- [x] 1.2 Remove the `!data/regions.json` exception from `.dockerignore`

## 2. Update Dockerfiles

- [x] 2.1 Update `Dockerfile`: change `COPY data/regions.json ./data/regions.json` → `COPY ml/regions.json ./ml/regions.json`
- [x] 2.2 Update `darkstar/Dockerfile`: same COPY line change
- [x] 2.3 Update `darkstar-dev/Dockerfile`: same COPY line change

## 3. Update code and tests

- [x] 3.1 Update `ml/weather.py` `load_regions_config` default path: `"data/regions.json"` → `"ml/regions.json"`
- [x] 3.2 Update `ml/weather.py` `get_regional_weather` default path: `"data/regions.json"` → `"ml/regions.json"`
- [x] 3.3 Update `tests/ml/test_regions_loader.py`: replace all 4 occurrences of `"data/regions.json"` → `"ml/regions.json"`

## 4. Update spec

- [x] 4.1 Update `openspec/specs/regional-weather-coordinates/spec.md`: replace all references to `data/regions.json` with `ml/regions.json`

## 5. Verify

- [x] 5.1 Confirm `data/regions.json` no longer exists in the repo
- [x] 5.2 Confirm no remaining references to `data/regions.json` in code or active specs (archived changes excluded)
- [x] 5.3 Run `tests/ml/test_regions_loader.py` and confirm all pass
