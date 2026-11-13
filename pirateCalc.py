import argparse
import csv
import ctypes
import json
import math
import os
import queue
import threading
import tkinter as tk
from pathlib import Path


GAME_LOG_FILE = Path(__file__).with_name("game_log.csv")
ACTIVE_GAME_FILE = Path(__file__).with_name("active_game.json")
TOKEN_CHANCE_PER_CHEST = 1 / 137500
GOLD_SKIN_CHANCE_PER_CHEST = 1 / 1562500


def chanceOfFindingItem(chestsOpened, chancePerChest):
    return -math.expm1(chestsOpened * math.log1p(-chancePerChest)) * 100


def chanceOfFindingToken(chestsOpened):
    return chanceOfFindingItem(chestsOpened, TOKEN_CHANCE_PER_CHEST)


def chanceOfFindingGoldSkin(chestsOpened):
    return chanceOfFindingItem(chestsOpened, GOLD_SKIN_CHANCE_PER_CHEST)


def chestsToReachChance(targetChance, totalChests):
    targetChests = math.ceil(
        math.log1p(-targetChance) / math.log1p(-TOKEN_CHANCE_PER_CHEST)
    )
    return targetChests, max(0, targetChests - totalChests)


def gamesToReachChance(remainingChests, averageChests):
    if remainingChests == 0:
        return 0
    if averageChests == 0:
        return None
    return math.ceil(remainingChests / averageChests)


def oddsPrediction():
    baseChest = 25

    try:
        gamesPlayed = int(input("How many games have you played?: "))
    except ValueError:
        print("Please enter a valid number of games played.")
        return

    if gamesPlayed < 0:
        print("Please enter a valid number of games played.")
        return
    totalChests = baseChest * gamesPlayed
    tokenChance = chanceOfFindingToken(totalChests)
    goldChance = chanceOfFindingGoldSkin(totalChests)
    print(
        f"After playing {gamesPlayed} games, you have opened {totalChests} "
        f"chests, with a {tokenChance:.4f}% chance of getting the Pirate "
        f"Token and a {goldChance:.4f}% chance of getting the Gold Skin."
    )


def gameUpdate():
    try:
        matchChest = int(input("How many chests did you open in this match?: "))
    except ValueError:
        print("Please enter a valid number of chests opened.")
        return

    if matchChest < 0:
        print("Please enter a valid number of chests opened.")
        return

    games = readGames()

    gameNumber = max((game[0] for game in games), default=0) + 1
    hasLogContent = GAME_LOG_FILE.exists() and GAME_LOG_FILE.stat().st_size > 0
    with GAME_LOG_FILE.open("a", newline="", encoding="utf-8") as logFile:
        writer = csv.writer(logFile)
        if not hasLogContent:
            writer.writerow(["Game Number", "Chests"])
        writer.writerow([gameNumber, matchChest])

    games.append((gameNumber, matchChest))
    print(f"{'Game Number':<20}Chests")
    for number, chests in games:
        print(f"{number:<20}{chests}")

    totalChests = sum(chests for _, chests in games)
    averageChests = totalChests / len(games)
    print(f"Total chests opened: {totalChests}")
    print(f"Average chests per match: {averageChests:.2f}")
    tokenChance = chanceOfFindingToken(totalChests)
    goldChance = chanceOfFindingGoldSkin(totalChests)
    print(f"Current chance of finding the Pirate Token: {tokenChance:.4f}%")
    print(f"Current chance of finding the Gold Skin: {goldChance:.4f}%")

    for targetChance in (0.25, 0.50):
        targetPercent = targetChance * 100
        targetChests, remainingChests = chestsToReachChance(
            targetChance, totalChests
        )
        moreGames = gamesToReachChance(remainingChests, averageChests)
        if moreGames == 0:
            print(
                f"{targetPercent:.0f}% chance: approximately "
                f"{targetChests} total chests (target reached)."
            )
        elif moreGames is None:
            print(
                f"{targetPercent:.0f}% chance: approximately "
                f"{targetChests} total chests; cannot estimate games needed "
                "because your average chests per match is zero."
            )
        else:
            print(
                f"{targetPercent:.0f}% chance: approximately {targetChests} "
                f"total chests ({remainingChests} more), or {moreGames} "
                "more games at your average."
            )


def loadActiveGameChests():
    if not ACTIVE_GAME_FILE.exists():
        return 0

    with ACTIVE_GAME_FILE.open("r", encoding="utf-8") as stateFile:
        state = json.load(stateFile)

    activeChests = state.get("activeGameChests")
    if (
        not isinstance(activeChests, int)
        or isinstance(activeChests, bool)
        or activeChests < 0
    ):
        raise ValueError(f"Invalid active game state in {ACTIVE_GAME_FILE}.")
    return activeChests


def saveActiveGameChests(activeChests):
    temporaryFile = ACTIVE_GAME_FILE.with_suffix(".json.tmp")
    with temporaryFile.open("w", encoding="utf-8") as stateFile:
        json.dump({"activeGameChests": activeChests}, stateFile)
    temporaryFile.replace(ACTIVE_GAME_FILE)


def readGames():
    if not GAME_LOG_FILE.exists() or GAME_LOG_FILE.stat().st_size == 0:
        return []

    with GAME_LOG_FILE.open("r", newline="", encoding="utf-8") as logFile:
        reader = csv.DictReader(logFile)
        if reader.fieldnames != ["Game Number", "Chests"]:
            raise ValueError(f"Unexpected CSV format in {GAME_LOG_FILE}.")
        return [
            (int(row["Game Number"]), int(row["Chests"]))
            for row in reader
        ]


def logCompletedGame(activeChests):
    games = readGames()
    gameNumber = max((game[0] for game in games), default=0) + 1
    hasLogContent = GAME_LOG_FILE.exists() and GAME_LOG_FILE.stat().st_size > 0
    with GAME_LOG_FILE.open("a", newline="", encoding="utf-8") as logFile:
        writer = csv.writer(logFile)
        if not hasLogContent:
            writer.writerow(["Game Number", "Chests"])
        writer.writerow([gameNumber, activeChests])
    return games + [(gameNumber, activeChests)]


def printTrackerSummary(games, activeChests):
    totalChests = sum(chests for _, chests in games) + activeChests
    print(
        f"Games completed: {len(games)} | "
        f"Chests opened (including current game): {totalChests}"
    )
    print(
        f"Pirate Token chance: {chanceOfFindingToken(totalChests):.6f}% | "
        f"Gold Skin chance: {chanceOfFindingGoldSkin(totalChests):.6f}%"
    )


def runHotkeyTracker():
    if os.name != "nt":
        raise OSError("Global hotkeys are currently supported only on Windows.")

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    registerHotKey = user32.RegisterHotKey
    registerHotKey.argtypes = [
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    registerHotKey.restype = ctypes.c_int
    unregisterHotKey = user32.UnregisterHotKey
    unregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
    unregisterHotKey.restype = ctypes.c_int

    class Point(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    class Message(ctypes.Structure):
        _fields_ = [
            ("hwnd", ctypes.c_void_p),
            ("message", ctypes.c_uint),
            ("wParam", ctypes.c_size_t),
            ("lParam", ctypes.c_ssize_t),
            ("time", ctypes.c_uint),
            ("point", Point),
            ("lPrivate", ctypes.c_uint),
        ]

    getMessage = user32.GetMessageW
    getMessage.argtypes = [
        ctypes.POINTER(Message),
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    getMessage.restype = ctypes.c_int
    postThreadMessage = user32.PostThreadMessageW
    postThreadMessage.argtypes = [
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.c_size_t,
        ctypes.c_ssize_t,
    ]
    postThreadMessage.restype = ctypes.c_int
    getCurrentThreadId = kernel32.GetCurrentThreadId
    getCurrentThreadId.restype = ctypes.c_uint

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_NOREPEAT = 0x4000
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    CHEST_HOTKEY_ID = 1
    GAME_HOTKEY_ID = 2
    modifiers = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    activeChests = loadActiveGameChests()
    games = readGames()

    hotkeyEvents = queue.Queue()
    startup = threading.Event()
    hotkeyThreadId = []
    startupErrors = []
    listenerRunning = [False]

    def listenForHotkeys():
        chestRegistered = False
        gameRegistered = False
        try:
            if not registerHotKey(None, CHEST_HOTKEY_ID, modifiers, ord("C")):
                raise ctypes.WinError(ctypes.get_last_error())
            chestRegistered = True
            if not registerHotKey(None, GAME_HOTKEY_ID, modifiers, ord("G")):
                raise ctypes.WinError(ctypes.get_last_error())
            gameRegistered = True
            hotkeyThreadId.append(getCurrentThreadId())
            listenerRunning[0] = True
            startup.set()

            message = Message()
            while True:
                result = getMessage(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
                if message.message == WM_HOTKEY:
                    hotkeyEvents.put(("hotkey", message.wParam))
        except OSError as error:
            if startup.is_set():
                hotkeyEvents.put(("error", error))
            else:
                startupErrors.append(error)
                startup.set()
        finally:
            listenerRunning[0] = False
            if chestRegistered:
                unregisterHotKey(None, CHEST_HOTKEY_ID)
            if gameRegistered:
                unregisterHotKey(None, GAME_HOTKEY_ID)

    hotkeyThread = threading.Thread(target=listenForHotkeys, daemon=True)
    hotkeyThread.start()
    if not startup.wait(timeout=5):
        raise TimeoutError("Timed out while registering the global hotkeys.")
    if startupErrors:
        raise startupErrors[0]

    root = tk.Tk()
    root.title("Fortnite Loot Tracker")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.94)
    root.configure(bg="#17212b")

    title = tk.Label(
        root,
        text="FORTNITE LOOT TRACKER",
        bg="#17212b",
        fg="#8fb9ff",
        font=("Segoe UI", 10, "bold"),
        padx=18,
        pady=12,
    )
    title.pack(anchor="w")

    gamesLabel = tk.Label(
        root, bg="#17212b", fg="white", font=("Segoe UI", 13, "bold")
    )
    gamesLabel.pack(anchor="w", padx=18, pady=(0, 3))
    chestsLabel = tk.Label(
        root, bg="#17212b", fg="white", font=("Segoe UI", 13, "bold")
    )
    chestsLabel.pack(anchor="w", padx=18, pady=3)
    currentGameLabel = tk.Label(
        root, bg="#17212b", fg="#c7d0da", font=("Segoe UI", 10)
    )
    currentGameLabel.pack(anchor="w", padx=18, pady=(0, 8))
    statusLabel = tk.Label(
        root, bg="#17212b", fg="#ffb3a7", font=("Segoe UI", 9)
    )
    statusLabel.pack(anchor="w", padx=18)
    oddsLabel = tk.Label(
        root, bg="#17212b", fg="#c7d0da", font=("Segoe UI", 9)
    )
    oddsLabel.pack(anchor="w", padx=18, pady=(0, 12))
    instructions = tk.Label(
        root,
        text="Ctrl+Alt+C: chest    Ctrl+Alt+G: finish game",
        bg="#17212b",
        fg="#8fb9ff",
        font=("Segoe UI", 9),
        padx=18,
        pady=8,
    )
    instructions.pack(anchor="w")

    def updateOverlay():
        totalChests = sum(chests for _, chests in games) + activeChests
        gamesLabel.config(text=f"Games played: {len(games)}")
        chestsLabel.config(text=f"Chests opened: {totalChests}")
        currentGameLabel.config(text=f"Current game: {activeChests} chests")
        oddsLabel.config(
            text=(
                f"Pirate Token: {chanceOfFindingToken(totalChests):.6f}%"
                f"    Gold Skin: {chanceOfFindingGoldSkin(totalChests):.6f}%"
            )
        )

    def processHotkeyEvents():
        nonlocal activeChests, games
        while True:
            try:
                eventType, value = hotkeyEvents.get_nowait()
            except queue.Empty:
                break

            if eventType == "error":
                statusLabel.config(text=f"Hotkey listener stopped: {value}")
            elif value == CHEST_HOTKEY_ID:
                activeChests += 1
                saveActiveGameChests(activeChests)
            elif value == GAME_HOTKEY_ID:
                games = logCompletedGame(activeChests)
                activeChests = 0
                saveActiveGameChests(activeChests)
            updateOverlay()

        root.after(100, processHotkeyEvents)

    def closeOverlay():
        if listenerRunning[0] and not postThreadMessage(
            hotkeyThreadId[0], WM_QUIT, 0, 0
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        root.destroy()

    updateOverlay()
    root.update_idletasks()
    x = max(0, root.winfo_screenwidth() - root.winfo_width() - 24)
    root.geometry(f"+{x}+40")
    root.protocol("WM_DELETE_WINDOW", closeOverlay)
    root.after(100, processHotkeyEvents)
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Track Fortnite chests and odds.")
    parser.add_argument(
        "--hotkey",
        action="store_true",
        help="run the Windows global-hotkey tracker and always-on-top overlay",
    )
    arguments = parser.parse_args()
    if arguments.hotkey:
        runHotkeyTracker()
    else:
        gameUpdate()