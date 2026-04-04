import json
from pathlib import Path
from app.runtime_scraper import scrape_snapshot


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_subpatrol(records):
    c = 0
    for r in records or []:
        if str(r.get("mission", "")).strip().upper() == "SUBPATROL":
            c += 1
    return c


game = Path("C:/Matrix Games/War in the Pacific Admiral's Edition")
save = game / "SAVE"
compare_dir = save / "ALLIED_COMPARE"

legacy_taskforces = load_json(compare_dir / "taskforces.json") or []
legacy_threats = load_json(compare_dir / "threats.json") or {}

records, objects = scrape_snapshot(game, save, "ALLIED")
inproc_taskforces = records.get("taskforces", [])
inproc_threats = objects.get("threats", {})

print("LEGACY_JSON taskforces", len(legacy_taskforces))
print("LEGACY_JSON taskforces_subpatrol", count_subpatrol(legacy_taskforces))
print("LEGACY_JSON threats_sub", len(legacy_threats.get("sub_threat_areas", [])))
print("LEGACY_JSON threats_all", len(legacy_threats.get("threat_areas", [])))
print("LEGACY_JSON invasions", len(legacy_threats.get("invasion_threat_areas", [])))

print("INPROC taskforces", len(inproc_taskforces))
print("INPROC taskforces_subpatrol", count_subpatrol(inproc_taskforces))
print("INPROC threats_sub", len(inproc_threats.get("sub_threat_areas", [])))
print("INPROC threats_all", len(inproc_threats.get("threat_areas", [])))
print("INPROC invasions", len(inproc_threats.get("invasion_threat_areas", [])))

legacy_tf_ids = {int(r.get("record_id", -1)) for r in legacy_taskforces if isinstance(r, dict)}
inproc_tf_ids = {int(r.get("record_id", -1)) for r in inproc_taskforces if isinstance(r, dict)}
print("TASKFORCE_ID overlap", len(legacy_tf_ids & inproc_tf_ids))
print("TASKFORCE_ID legacy_only", len(legacy_tf_ids - inproc_tf_ids))
print("TASKFORCE_ID inproc_only", len(inproc_tf_ids - legacy_tf_ids))
