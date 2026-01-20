# Contributing

## Release Process

### HACS Release

1. Update `version` in `custom_components/energy_tracker/manifest.json`
2. Commit and push changes
3. Create and push tag:
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```
4. GitHub Action creates release automatically
5. HACS detects new release within hours

### Core Sync

1. Create and push core tag:
   ```bash
   git tag core-v1.2.3
   git push origin core-v1.2.3
   ```
2. GitHub Action syncs to `energy-tracker/core` fork
3. Manually create PR from fork to `home-assistant/core`

## Tag Conventions

| Tag | Target | Creates GitHub Release |
|-----|--------|------------------------|
| `v*` | HACS | ✅ Yes |
| `core-v*` | Core Fork | ❌ No |
