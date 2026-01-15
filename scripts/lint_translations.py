#!/usr/bin/env python3
"""Translation Linter for Home Assistant Integration.

Validates translation files and their usage in the codebase.

Checks performed:
1. Missing translations: Keys that exist in strings.json but not in a language file
2. Extra keys: Keys that exist in a language file but not in strings.json
3. Missing translation_keys: Keys used in Python code but not defined in strings.json
4. Placeholder mismatches: Different placeholders across languages for the same key
5. Empty values: Translation values that are empty strings
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ANSI colors for terminal output
COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}


def log_error(msg: str) -> None:
    """Log an error message."""
    print(f"{COLORS['red']}✖ {msg}{COLORS['reset']}")


def log_warn(msg: str) -> None:
    """Log a warning message."""
    print(f"{COLORS['yellow']}⚠ {msg}{COLORS['reset']}")


def log_success(msg: str) -> None:
    """Log a success message."""
    print(f"{COLORS['green']}✓ {msg}{COLORS['reset']}")


def log_info(msg: str) -> None:
    """Log an info message."""
    print(f"{COLORS['cyan']}ℹ {msg}{COLORS['reset']}")


def log_header(msg: str) -> None:
    """Log a header message."""
    print(f"\n{COLORS['bold']}{COLORS['blue']}{msg}{COLORS['reset']}\n")


def flatten_json(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    """Flatten a nested JSON structure into dot-notation keys."""
    result: dict[str, str] = {}

    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict):
            result.update(flatten_json(value, full_key))
        elif isinstance(value, str):
            result[full_key] = value

    return result


def extract_placeholders(value: str) -> set[str]:
    """Extract placeholder names from a translation string.

    Placeholders are in the format {placeholder_name}.
    """
    return set(re.findall(r"\{([^}]+)\}", value))


def load_translation_file(file_path: Path) -> dict[str, str] | None:
    """Load and flatten a translation JSON file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return flatten_json(data)
    except json.JSONDecodeError as e:
        log_error(f"Invalid JSON in {file_path}: {e}")
        return None
    except OSError as e:
        log_error(f"Could not read {file_path}: {e}")
        return None


def extract_translation_keys_from_python(
    root_dir: Path,
) -> dict[str, list[dict[str, Any]]]:
    """Extract translation_key usages from Python files.

    Returns a dict mapping keys to their usage locations.
    """
    used_keys: dict[str, list[dict[str, Any]]] = {}

    # Pattern to match translation_key="..." or translation_key='...'
    pattern = re.compile(r'translation_key\s*=\s*["\']([^"\']+)["\']')

    py_files = list(root_dir.rglob("*.py"))

    for py_file in py_files:
        # Skip test files and pycache
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
        except OSError:
            continue

        for line_num, line in enumerate(content.split("\n"), start=1):
            for match in pattern.finditer(line):
                key = match.group(1)
                if key not in used_keys:
                    used_keys[key] = []
                used_keys[key].append(
                    {
                        "file": str(py_file),
                        "line": line_num,
                    }
                )

    return used_keys


def check_missing_translations(
    strings: dict[str, str],
    translations: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Check for keys missing in translation files.

    Returns a list of errors with key and missing languages.
    """
    errors: list[dict[str, Any]] = []

    for key in strings:
        missing_langs = []
        for lang, trans in translations.items():
            if key not in trans:
                missing_langs.append(lang)

        if missing_langs:
            errors.append(
                {
                    "key": key,
                    "missing_langs": missing_langs,
                }
            )

    return errors


def check_extra_keys(
    strings: dict[str, str],
    translations: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Check for keys in translations that don't exist in strings.json.

    Returns a list of warnings with key and languages where it appears.
    """
    warnings: list[dict[str, Any]] = []
    extra_keys: dict[str, list[str]] = {}

    for lang, trans in translations.items():
        for key in trans:
            if key not in strings:
                if key not in extra_keys:
                    extra_keys[key] = []
                extra_keys[key].append(lang)

    for key, langs in extra_keys.items():
        warnings.append(
            {
                "key": key,
                "languages": langs,
            }
        )

    return warnings


def check_missing_keys_in_code(
    used_keys: dict[str, list[dict[str, Any]]],
    strings: dict[str, str],
) -> list[dict[str, Any]]:
    """Check for translation_keys used in code but not defined in strings.json.

    Returns a list of errors with key and usage locations.
    """
    errors: list[dict[str, Any]] = []

    # Build set of keys from strings.json
    # translation_key can reference exceptions or issues
    defined_keys = set()
    for key in strings:
        # Extract the key part (e.g., "exceptions.timeout.message" -> "timeout")
        # or "issues.auth_error_invalid_token.title" -> "auth_error_invalid_token"
        parts = key.split(".")
        if len(parts) >= 2:
            defined_keys.add(parts[1])

    for key, locations in used_keys.items():
        if key not in defined_keys:
            errors.append(
                {
                    "key": key,
                    "locations": locations,
                }
            )

    return errors


def check_placeholder_consistency(
    strings: dict[str, str],
    translations: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Check for placeholder inconsistencies across languages.

    Returns a list of errors with key and placeholder differences.
    """
    errors: list[dict[str, Any]] = []

    for key, base_value in strings.items():
        base_placeholders = extract_placeholders(base_value)

        inconsistencies: dict[str, set[str]] = {}

        for lang, trans in translations.items():
            if key in trans:
                lang_placeholders = extract_placeholders(trans[key])
                if lang_placeholders != base_placeholders:
                    inconsistencies[lang] = lang_placeholders

        if inconsistencies:
            errors.append(
                {
                    "key": key,
                    "base_placeholders": base_placeholders,
                    "inconsistencies": inconsistencies,
                }
            )

    return errors


def check_empty_values(
    strings: dict[str, str],
    translations: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Check for empty translation values.

    Returns a list of warnings with key and languages with empty values.
    """
    warnings: list[dict[str, Any]] = []

    # Check strings.json
    for key, value in strings.items():
        if not value.strip():
            warnings.append(
                {
                    "key": key,
                    "languages": ["strings.json"],
                }
            )

    # Check translation files
    for lang, trans in translations.items():
        for key, value in trans.items():
            if not value.strip():
                # Check if already reported
                existing = next((w for w in warnings if w["key"] == key), None)
                if existing:
                    existing["languages"].append(lang)
                else:
                    warnings.append(
                        {
                            "key": key,
                            "languages": [lang],
                        }
                    )

    return warnings


def main() -> int:
    """Main entry point."""
    log_header("🌐 Home Assistant Translation Linter")

    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    component_dir = project_root / "custom_components" / "energy_tracker"
    strings_file = component_dir / "strings.json"
    translations_dir = component_dir / "translations"

    # Load strings.json (reference file)
    log_info("Loading strings.json...")
    strings = load_translation_file(strings_file)
    if strings is None:
        log_error("Failed to load strings.json")
        return 1

    log_info(f"Found {len(strings)} keys in strings.json")

    # Load all translation files
    log_info("Loading translation files...")
    translations: dict[str, dict[str, str]] = {}

    if translations_dir.exists():
        for trans_file in translations_dir.glob("*.json"):
            lang = trans_file.stem
            trans = load_translation_file(trans_file)
            if trans is not None:
                translations[lang] = trans

    log_info(
        f"Found {len(translations)} translation files: {', '.join(sorted(translations.keys()))}"
    )

    # Extract translation_key usages from Python code
    log_info("Scanning Python files for translation_key usage...")
    used_keys = extract_translation_keys_from_python(component_dir)
    log_info(f"Found {len(used_keys)} unique translation_keys in Python files")

    has_errors = False
    has_warnings = False

    # Check 1: Missing translations
    log_header("📋 Check 1: Missing translations across languages")
    missing_translations = check_missing_translations(strings, translations)

    if not missing_translations:
        log_success("All keys are translated in all languages!")
    else:
        has_errors = True
        log_error(
            f"Found {len(missing_translations)} keys with missing translations:\n"
        )

        for error in missing_translations[:20]:
            print(f"  {COLORS['red']}{error['key']}{COLORS['reset']}")
            print(
                f"    Missing in: {COLORS['yellow']}{', '.join(error['missing_langs'])}{COLORS['reset']}\n"
            )

        if len(missing_translations) > 20:
            print(f"  ... and {len(missing_translations) - 20} more")

    # Check 2: Extra keys in translations
    log_header("📋 Check 2: Extra keys in translation files")
    extra_keys = check_extra_keys(strings, translations)

    if not extra_keys:
        log_success("No extra keys found in translation files!")
    else:
        has_warnings = True
        log_warn(f"Found {len(extra_keys)} extra keys in translation files:\n")

        for warning in extra_keys[:20]:
            print(f"  {COLORS['yellow']}{warning['key']}{COLORS['reset']}")
            print(
                f"    Found in: {COLORS['cyan']}{', '.join(warning['languages'])}{COLORS['reset']}\n"
            )

        if len(extra_keys) > 20:
            print(f"  ... and {len(extra_keys) - 20} more")

    # Check 3: Missing translation_keys in strings.json
    log_header("📋 Check 3: Translation keys used in code but not defined")
    missing_in_strings = check_missing_keys_in_code(used_keys, strings)

    if not missing_in_strings:
        log_success("All translation_keys used in code are defined in strings.json!")
    else:
        has_errors = True
        log_error(f"Found {len(missing_in_strings)} translation_keys not defined:\n")

        for error in missing_in_strings:
            print(f"  {COLORS['red']}{error['key']}{COLORS['reset']}")
            for loc in error["locations"][:3]:
                print(
                    f"    {COLORS['cyan']}{loc['file']}:{loc['line']}{COLORS['reset']}"
                )
            if len(error["locations"]) > 3:
                print(f"    ... and {len(error['locations']) - 3} more locations")
            print()

    # Check 4: Placeholder consistency
    log_header("📋 Check 4: Placeholder consistency across languages")
    placeholder_errors = check_placeholder_consistency(strings, translations)

    if not placeholder_errors:
        log_success("All languages have consistent placeholders!")
    else:
        has_errors = True
        log_error(
            f"Found {len(placeholder_errors)} keys with inconsistent placeholders:\n"
        )

        for error in placeholder_errors:
            print(f"  {COLORS['red']}{error['key']}{COLORS['reset']}")
            base_ph = error["base_placeholders"]
            print(
                f"    strings.json: {COLORS['green']}{{{', '.join(sorted(base_ph)) or 'none'}}}{COLORS['reset']}"
            )

            for lang, ph in error["inconsistencies"].items():
                print(
                    f"    {lang}: {COLORS['yellow']}{{{', '.join(sorted(ph)) or 'none'}}}{COLORS['reset']}"
                )
            print()

    # Check 5: Empty values
    log_header("📋 Check 5: Empty translation values")
    empty_values = check_empty_values(strings, translations)

    if not empty_values:
        log_success("No empty translation values found!")
    else:
        has_warnings = True
        log_warn(f"Found {len(empty_values)} keys with empty values:\n")

        for warning in empty_values[:20]:
            print(f"  {COLORS['yellow']}{warning['key']}{COLORS['reset']}")
            print(
                f"    Empty in: {COLORS['cyan']}{', '.join(warning['languages'])}{COLORS['reset']}\n"
            )

        if len(empty_values) > 20:
            print(f"  ... and {len(empty_values) - 20} more")

    # Summary
    log_header("📊 Summary")

    if has_errors:
        log_error("Translation validation failed! Please fix the errors above.")
        return 1
    if has_warnings:
        log_warn("Translation validation passed with warnings.")
        return 0

    log_success("Translation validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
