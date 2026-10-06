"""Refresh the checked-in frontend assets. Run only when upgrading dependencies."""
from pathlib import Path
from urllib.request import urlretrieve

DESTINATION = Path(__file__).resolve().parent.parent / "static" / "vendor"
ASSETS = {
    "bootstrap.min.css": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css",
    "bootstrap.bundle.min.js": "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js",
    "BOOTSTRAP-LICENSE.txt": "https://raw.githubusercontent.com/twbs/bootstrap/v5.3.8/LICENSE",
    "DM-Sans.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz,wght%5D.ttf",
    "DM-Sans-OFL.txt": "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/OFL.txt",
}
if __name__ == "__main__":
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for name, url in ASSETS.items():
        urlretrieve(url, DESTINATION / name)
        print(f"Downloaded {name}")
