from pathlib import Path
from app.runtime_scraper import scrape_snapshot

game = Path("C:/Matrix Games/War in the Pacific Admiral's Edition")
save = game / "SAVE"
records, objects = scrape_snapshot(game, save, "ALLIED")
print("taskforces", len(records.get("taskforces", [])))
print("sub_threats", len(objects.get("threats", {}).get("sub_threat_areas", [])))
