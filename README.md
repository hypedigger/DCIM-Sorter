# 📸 DCIM Sorter

**Import photos & videos from SD cards and phones, automatically sorted by shooting day.**

Point it at your camera card, USB stick or MTP phone: every photo and video is copied into a clean `Root\YYYY\to_sort\MM\DD` tree based on its **EXIF date** (file date as fallback) — ready to cull.

![DCIM Sorter](docs/screenshot.png)

## Features

- **Sources**: SD cards / USB drives (DCIM), and **phones plugged in MTP mode** (through the Windows Shell — no driver, no phone app needed).
- **EXIF-based day sorting** via [exiftool](https://exiftool.org/) (the app offers to download it on first run).
- **Priority subfolders** — files whose path matches your configured folder names (e.g. `_Priority`) are routed to their own tree.
- **Date filters** — import everything, or only after a given date.
- **Parallel copy** with per-file progress, duplicate-safe naming.
- **Delete after copy** (optional, off by default) — clearly confirmed before anything is removed from the source.
- Animated, themeable UI (cyberpunk / premium / sakura…), remembers your settings.

## Installation

Requires **Windows** and **Python 3.12+**.

```bash
git clone https://github.com/hypedigger/DCIM-Sorter.git
cd DCIM-Sorter
pip install -r requirements.txt
python photo_organiser.py
```

Optional — Start Menu shortcut (also generates the icon):

```bash
python install_start_menu.py
```

## Usage

1. Plug in your card or phone — the app scans for DCIM sources in the background.
2. Pick the source and your photo library root.
3. Choose the date range, check **Delete after copy** only if you want the source cleaned.
4. Start — files land in `Root\YYYY\to_sort\MM\DD`.

Settings (library root, priority folder names, exiftool path, theme) live in the standard Windows registry for the app and never in this repository.

## Notes

- exiftool is © Phil Harvey, distributed under the Perl Artistic License — downloaded from the official site, never bundled here.
- UI is currently in French; contributions welcome.

## Support

If DCIM Sorter tamed your photo imports:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/hypedigger)

## License

[MIT](LICENSE)
