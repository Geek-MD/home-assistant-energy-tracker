# HACS Validation Issues - Fix Guide

This document provides step-by-step instructions to resolve the HACS validation failures for the Energy Tracker integration.

## Current Status

The repository is failing **2 out of 8** HACS validation checks:

### ❌ Failed Checks

1. **Repository Issues Not Enabled**
   - Error: "The repository does not have issues enabled"
   - [More info](https://hacs.xyz/docs/publish/include#check-repository)

2. **Repository Missing Valid Topics**
   - Error: "The repository has no valid topics"
   - [More info](https://hacs.xyz/docs/publish/include#check-repository)

### ✅ Passed Checks

- Validation information: ✓
- Validation archived: ✓
- Validation description: ✓
- Integration manifest: ✓
- HACS JSON: ✓
- Brands: ✓

## How to Fix

These are **GitHub repository configuration issues** that must be fixed in the GitHub web interface. They cannot be resolved through code changes.

### Fix 1: Enable Issues

1. Go to your repository on GitHub: https://github.com/Geek-MD/home-assistant-energy-tracker
2. Click on **Settings** (top navigation bar)
3. Scroll down to the **Features** section
4. Check the box next to **Issues**
5. Click **Save** if prompted

**Why this is required:** HACS needs the Issues feature enabled so users can report problems with the integration.

### Fix 2: Add Repository Topics

1. Go to your repository on GitHub: https://github.com/Geek-MD/home-assistant-energy-tracker
2. Click on the **About** section's settings gear icon (⚙️) on the right side
3. In the **Topics** field, add the following topics (comma or space separated):
   ```
   home-assistant
   hacs
   energy-tracker
   integration
   custom-component
   home-automation
   energy-monitoring
   ```
4. Click **Save changes**

**Why this is required:** Topics help users discover your integration and are required by HACS for proper categorization.

### Recommended Additional Topics

For better discoverability, consider also adding:
- `homeassistant-integration`
- `smart-home`
- `iot`
- `python`

## Verification

After making these changes:

1. Wait a few minutes for GitHub to update
2. Re-run the HACS validation check
3. Verify that all 8/8 checks pass

## Additional Information

- **HACS Documentation:** https://hacs.xyz/docs/publish/include
- **Current hacs.json configuration:** Already properly configured ✓
- **Current manifest.json configuration:** Already properly configured ✓
- **Integration version:** 1.1.0

## Notes

- These changes do not affect the code or functionality
- They are purely for HACS compliance and repository discoverability
- Once fixed, the integration will be properly validated for HACS submission
