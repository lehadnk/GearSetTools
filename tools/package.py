"""Build a clean, installable CurseForge ZIP using an explicit file list."""
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
toc = root / "GearSetTools.toc"
version = re.search(r"^## Version:\s*(\S+)", toc.read_text(encoding="utf-8"), re.M).group(1)
files = ["GearSetTools.toc", "GearSetTools.lua", "SetCache.lua", "SetCompare.lua", "README.md", "CHANGELOG.md",
         "comparison.png", "bank.png", "bags.png"]
if (root / "LICENSE").exists():
    files.append("LICENSE")
output = root / "dist" / f"GearSetTools-{version}.zip"
output.parent.mkdir(exist_ok=True)
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for name in files:
        archive.write(root / name, f"GearSetTools/{name}")
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == {f"GearSetTools/{name}" for name in files}
print(output)
print(f"Validated {len(files)} files; version {version}; no settings, logs, or development files included.")
