# Pirate Token Tracker

> **BETA:** This program is in beta. Any input or suggestions would be greatly appreciated!

A small Windows desktop tracker for recording Fortnite chest openings and games played. The always-on-top overlay shows your running counts and estimated odds for the Pirate Token and Gold Skin.

The tracker uses global hotkeys while it is running; it does not read Fortnite account data or automatically detect chest openings. The odds are cumulative estimates based on the per-chest chances configured in the program, not a guarantee of an item drop.

## Requirements

- Windows 10 or later
- Python 3.10 or later with Tkinter available (the standard python.org Windows installer includes it)

No third-party Python packages are required.

## Setup

1. Install Python 3 for Windows from [python.org](https://www.python.org/downloads/windows/). If the installer offers the option, enable **Add Python to PATH**.
2. Download or clone this repository.
3. Open PowerShell in the downloaded `Pirate Token Tracker` folder.
4. Confirm Python is available:

   ```powershell
   py -3 --version
   ```

5. Start the tracker:

   ```powershell
   py -3 .\pirateCalc.py --hotkey
   ```

The overlay should appear near the top-right of the screen and stay above other windows. If it is hidden by Fortnite, use **Windowed Fullscreen** or **Borderless** display mode instead of exclusive fullscreen.

## Hotkeys

- **Ctrl+Alt+C** — add one chest to the current game.
- **Ctrl+Alt+G** — finish the current game and save its chest count.

The tracker window can be minimized while you play; the hotkeys will continue to work. Keep the program running, because closing the overlay stops the tracker. Use the window's **-** button (minimize) to close it.

## Feedback

This project is in beta, so reports of bugs, ideas, and other suggestions are welcome. Please open a GitHub issue with steps to reproduce any problem when possible. Do not include API keys, passwords, or other sensitive information in an issue.
