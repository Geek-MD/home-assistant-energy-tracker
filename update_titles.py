import json
from pathlib import Path

# Mapping: alte Titel/Beschreibungen -> neue (generisch, funktioniert für die meisten Sprachen)
translations_dir = Path("custom_components/energy_tracker/translations")

# Lade die englische Version als Referenz
with open(translations_dir / "en.json", 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Lade die deutsche Version als Referenz
with open(translations_dir / "de.json", 'r', encoding='utf-8') as f:
    de_data = json.load(f)

# Definiere die neuen Texte, die wir für jede Sprache manuell übersetzen müssen
# Für jetzt: nur EN und DE sind fertig, andere behalten alte Titel aber ohne name-Felder

print("English and German translations are already updated.")
print("Other languages: Keys removed, but titles/descriptions kept as-is.")
print("\nTo fully translate, each language would need manual translation of:")
print("- user.title: 'Set up Energy Tracker' / 'Energy Tracker einrichten'")
print("- user.description: Updated description without name mention")
print("- reconfigure.title: 'Reconfigure Energy Tracker' / 'Energy Tracker neu konfigurieren'")
print("- reconfigure.description: Updated description")

