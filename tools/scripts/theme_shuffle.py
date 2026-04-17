#!/usr/bin/env python3
"""Randomize Windows Terminal cyberpunk theme with revert support."""

from __future__ import annotations

import argparse
import io
import json
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SETTINGS_PATH = Path(
    "C:/Users/ericp/AppData/Local/Packages"
    "/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json"
)
STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "theme_state.json"
OMP_ACTIVE = Path(__file__).resolve().parents[2] / "tools" / "themes" / "ohmyposh" / "active.omp.json"

THEMES: dict[str, dict] = {
    "cyberpunk": {
        "name": "Cyberpunk",
        "background": "#0D0221", "foreground": "#00F5FF",
        "cursorColor": "#FF2D78", "selectionBackground": "#1A0533",
        "black": "#0D0221", "brightBlack": "#2D0B4E",
        "blue": "#0066FF", "brightBlue": "#00AAFF",
        "cyan": "#00F5FF", "brightCyan": "#7DFDFE",
        "green": "#39FF14", "brightGreen": "#7CFF57",
        "purple": "#FF2D78", "brightPurple": "#FF6B9D",
        "red": "#FF2D78", "brightRed": "#FF6B9D",
        "white": "#C0C0FF", "brightWhite": "#FFFFFF",
        "yellow": "#FFD700", "brightYellow": "#FFE55C",
    },
    "ghost-shell": {
        "name": "Ghost Shell",
        "background": "#000000", "foreground": "#00FF41",
        "cursorColor": "#00FF41", "selectionBackground": "#003515",
        "black": "#000000", "brightBlack": "#0D200D",
        "blue": "#005C40", "brightBlue": "#00CC88",
        "cyan": "#00D97E", "brightCyan": "#66FFBB",
        "green": "#00B32C", "brightGreen": "#00FF41",
        "purple": "#007A3D", "brightPurple": "#00FFB3",
        "red": "#CC0000", "brightRed": "#FF3333",
        "white": "#88FF88", "brightWhite": "#CCFFCC",
        "yellow": "#B4FF00", "brightYellow": "#D4FF66",
    },
    "blade-runner": {
        "name": "Blade Runner",
        "background": "#0A0D1A", "foreground": "#FFB347",
        "cursorColor": "#FF6B00", "selectionBackground": "#1A1000",
        "black": "#0A0D1A", "brightBlack": "#1A2030",
        "blue": "#4488FF", "brightBlue": "#88AAFF",
        "cyan": "#00CCCC", "brightCyan": "#44EEEE",
        "green": "#44FF88", "brightGreen": "#88FFAA",
        "purple": "#CC44FF", "brightPurple": "#EE88FF",
        "red": "#FF4444", "brightRed": "#FF8888",
        "white": "#FFE8CC", "brightWhite": "#FFFFFF",
        "yellow": "#FFB347", "brightYellow": "#FFD088",
    },
    "synthwave": {
        "name": "Synthwave",
        "background": "#0D0D2B", "foreground": "#FF7EDB",
        "cursorColor": "#FC28A8", "selectionBackground": "#2D1B4E",
        "black": "#0D0D2B", "brightBlack": "#1D1D4E",
        "blue": "#2244DD", "brightBlue": "#4466FF",
        "cyan": "#36F9F6", "brightCyan": "#8AFCFA",
        "green": "#72F1B8", "brightGreen": "#A8F7D3",
        "purple": "#FC28A8", "brightPurple": "#FF7EDB",
        "red": "#FE4450", "brightRed": "#FF8890",
        "white": "#F4F4FF", "brightWhite": "#FFFFFF",
        "yellow": "#F97E72", "brightYellow": "#FBAD9A",
    },
    "deep-space": {
        "name": "Deep Space",
        "background": "#060918", "foreground": "#7EB8F7",
        "cursorColor": "#00D4FF", "selectionBackground": "#0D1F44",
        "black": "#060918", "brightBlack": "#0D1530",
        "blue": "#0055DD", "brightBlue": "#3388FF",
        "cyan": "#00D4FF", "brightCyan": "#66E8FF",
        "green": "#00FF88", "brightGreen": "#66FFB3",
        "purple": "#8844FF", "brightPurple": "#BB88FF",
        "red": "#FF4488", "brightRed": "#FF88BB",
        "white": "#C8E8FF", "brightWhite": "#FFFFFF",
        "yellow": "#FFD700", "brightYellow": "#FFE566",
    },
    "neon-tokyo": {
        "name": "Neon Tokyo",
        "background": "#12001A", "foreground": "#FF6AC1",
        "cursorColor": "#00FFA0", "selectionBackground": "#2A0033",
        "black": "#12001A", "brightBlack": "#2A0033",
        "blue": "#4466FF", "brightBlue": "#88AAFF",
        "cyan": "#00FFA0", "brightCyan": "#66FFD0",
        "green": "#00FFA0", "brightGreen": "#66FFD0",
        "purple": "#FF6AC1", "brightPurple": "#FF99DD",
        "red": "#FF2D78", "brightRed": "#FF6B9D",
        "white": "#FFE0F0", "brightWhite": "#FFFFFF",
        "yellow": "#FFEE00", "brightYellow": "#FFF566",
    },
    "outrun": {
        "name": "Outrun",
        "background": "#0D001A", "foreground": "#FF8800",
        "cursorColor": "#FF00FF", "selectionBackground": "#2A0040",
        "black": "#0D001A", "brightBlack": "#1A0030",
        "blue": "#3300CC", "brightBlue": "#6633FF",
        "cyan": "#00FFFF", "brightCyan": "#66FFFF",
        "green": "#00FF88", "brightGreen": "#66FFB3",
        "purple": "#FF00FF", "brightPurple": "#FF66FF",
        "red": "#FF2200", "brightRed": "#FF6655",
        "white": "#FFE8DD", "brightWhite": "#FFFFFF",
        "yellow": "#FF8800", "brightYellow": "#FFAA44",
    },
    "tron": {
        "name": "Tron",
        "background": "#000D1A", "foreground": "#00E5FF",
        "cursorColor": "#FFFFFF", "selectionBackground": "#001A33",
        "black": "#000D1A", "brightBlack": "#001A33",
        "blue": "#0033CC", "brightBlue": "#0066FF",
        "cyan": "#00E5FF", "brightCyan": "#66F2FF",
        "green": "#00FF88", "brightGreen": "#66FFB3",
        "purple": "#6600FF", "brightPurple": "#9944FF",
        "red": "#FF2200", "brightRed": "#FF6644",
        "white": "#C0EFFF", "brightWhite": "#FFFFFF",
        "yellow": "#FFD700", "brightYellow": "#FFE566",
    },
}

PALETTE_NOTES = {
    "cyberpunk":    "electric cyan on deep purple",
    "ghost-shell":  "phosphor green rain — matrix greens + teal + lime",
    "blade-runner": "amber gold on dark navy",
    "synthwave":    "magenta/pink on dark indigo",
    "deep-space":   "ice blue on near-black",
    "neon-tokyo":   "hot pink on deep violet",
    "outrun":       "neon orange on void purple",
    "tron":         "electric blue on black",
}

# OMP prompt segment colors per theme — (os-badge, path, git, exectime, prompt-char)
OMP_COLORS: dict[str, dict] = {
    "cyberpunk":    {"os": "#FF2D78", "path": "#00F5FF", "git": "#39FF14", "time": "#FFD700", "prompt": "#FF2D78"},
    "ghost-shell":  {"os": "#00FF41", "path": "#00B32C", "git": "#B4FF00", "time": "#00D97E", "prompt": "#00FF41"},
    "blade-runner": {"os": "#FF6B00", "path": "#FFB347", "git": "#00CCCC", "time": "#CC44FF", "prompt": "#FF6B00"},
    "synthwave":    {"os": "#FC28A8", "path": "#FF7EDB", "git": "#36F9F6", "time": "#72F1B8", "prompt": "#FC28A8"},
    "deep-space":   {"os": "#00D4FF", "path": "#7EB8F7", "git": "#00FF88", "time": "#8844FF", "prompt": "#00D4FF"},
    "neon-tokyo":   {"os": "#FF6AC1", "path": "#00FFA0", "git": "#FFEE00", "time": "#4466FF", "prompt": "#FF6AC1"},
    "outrun":       {"os": "#FF00FF", "path": "#FF8800", "git": "#00FFFF", "time": "#00FF88", "prompt": "#FF00FF"},
    "tron":         {"os": "#00E5FF", "path": "#0066FF", "git": "#00FF88", "time": "#6600FF", "prompt": "#00E5FF"},
}


def _load_state() -> dict:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"current": "cyberpunk", "previous": None}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _luminance(hex_color: str) -> float:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _fg_for(bg: str) -> str:
    return "#000000" if _luminance(bg) >= 0.35 else "#FFFFFF"


def _build_omp_theme(key: str) -> dict:
    c = OMP_COLORS[key]
    name = THEMES[key]["name"]
    return {
        "$schema": "https://raw.githubusercontent.com/JanDeDobbeleer/oh-my-posh/main/themes/schema.json",
        "version": 2,
        "final_space": True,
        "console_title_template": "{{ .Shell }} :: {{ .Folder }} [" + name + "]",
        "blocks": [
            {
                "type": "prompt",
                "alignment": "left",
                "segments": [
                    {
                        "type": "os",
                        "style": "diamond",
                        "leading_diamond": "\ue0b6",
                        "trailing_diamond": "\ue0b0",
                        "foreground": _fg_for(c["os"]),
                        "background": c["os"],
                        "template": " \ue62a ",
                    },
                    {
                        "type": "path",
                        "style": "powerline",
                        "powerline_symbol": "\ue0b0",
                        "foreground": _fg_for(c["path"]),
                        "background": c["path"],
                        "properties": {"style": "folder"},
                        "template": " \uf07c {{ .Path }} ",
                    },
                    {
                        "type": "git",
                        "style": "powerline",
                        "powerline_symbol": "\ue0b0",
                        "foreground": _fg_for(c["git"]),
                        "background": c["git"],
                        "properties": {"fetch_status": True},
                        "template": " \ue725 {{ .HEAD }}{{ if .Working.Changed }} \uf044 {{ .Working.String }}{{ end }}{{ if .Staging.Changed }} \uf046 {{ .Staging.String }}{{ end }} ",
                    },
                    {
                        "type": "executiontime",
                        "style": "diamond",
                        "leading_diamond": "\ue0b0",
                        "trailing_diamond": "\ue0b4",
                        "foreground": _fg_for(c["time"]),
                        "background": c["time"],
                        "properties": {"threshold": 500, "style": "austin"},
                        "template": " \uf252 {{ .FormattedMs }} ",
                    },
                ],
            },
            {
                "type": "prompt",
                "alignment": "left",
                "newline": True,
                "segments": [
                    {
                        "type": "exit",
                        "style": "plain",
                        "foreground": c["prompt"],
                        "foreground_templates": [
                            "{{ if gt .Code 0 }}" + c["os"] + "{{ end }}"
                        ],
                        "template": "{{ if gt .Code 0 }}\u2717{{ else }}\u276f{{ end }} ",
                    }
                ],
            },
        ],
    }


def _write_omp_theme(key: str) -> None:
    try:
        theme = _build_omp_theme(key)
        OMP_ACTIVE.parent.mkdir(parents=True, exist_ok=True)
        OMP_ACTIVE.write_text(json.dumps(theme, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"  (OMP write skipped: {e})", file=sys.stderr)


def _apply_theme(key: str) -> str:
    theme = THEMES[key]
    if not SETTINGS_PATH.is_file():
        print(f"ERROR: Windows Terminal settings not found at {SETTINGS_PATH}", file=sys.stderr)
        sys.exit(1)

    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))

    # Replace or add the scheme entry
    schemes = [s for s in settings.get("schemes", []) if s.get("name") != theme["name"]]
    schemes.append(theme)
    settings["schemes"] = schemes

    # Apply to profile defaults
    if "profiles" not in settings:
        settings["profiles"] = {}
    if "defaults" not in settings["profiles"]:
        settings["profiles"]["defaults"] = {}
    settings["profiles"]["defaults"]["colorScheme"] = theme["name"]

    SETTINGS_PATH.write_text(
        json.dumps(settings, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    _write_omp_theme(key)
    return theme["name"]


def _key_for_name(name: str) -> str | None:
    for k, v in THEMES.items():
        if v["name"].lower() == name.lower() or k == name.lower():
            return k
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Shuffle Windows Terminal cyberpunk theme")
    parser.add_argument("--revert", action="store_true", help="Restore previous theme")
    parser.add_argument("--list", action="store_true", help="List available themes")
    parser.add_argument("--theme", metavar="KEY", help="Apply a specific theme by key")
    args = parser.parse_args()

    state = _load_state()

    if args.list:
        print("Available themes:\n")
        for k, v in THEMES.items():
            marker = " ◄ active" if k == state.get("current") else ""
            prev_marker = " ◄ previous" if k == state.get("previous") else ""
            note = PALETTE_NOTES.get(k, "")
            print(f"  {k:<18}  {v['name']:<16}  {note}{marker}{prev_marker}")
        return

    if args.revert:
        prev = state.get("previous")
        if not prev or prev not in THEMES:
            print("No previous theme recorded -- nothing to revert to.")
            return
        applied = _apply_theme(prev)
        old_current = state["current"]
        state["previous"] = old_current
        state["current"] = prev
        _save_state(state)
        print(f"Reverted  {THEMES[old_current]['name']} -> {applied}")
        print(f"Undo available: /theme-shuffle --revert")
        return

    if args.theme:
        chosen = _key_for_name(args.theme)
        if not chosen:
            print(f"Unknown theme: {args.theme!r}")
            print("Run /theme-shuffle --list to see available keys.")
            sys.exit(1)
    else:
        current = state.get("current", "cyberpunk")
        pool = [k for k in THEMES if k != current]
        chosen = random.choice(pool)

    old = state.get("current", "cyberpunk")
    applied = _apply_theme(chosen)
    state["previous"] = old
    state["current"] = chosen
    _save_state(state)

    note = PALETTE_NOTES.get(chosen, "")
    print(f"Theme     {THEMES[old]['name']} -> {applied}  ({note})")
    print(f"Revert    /theme-shuffle --revert")
    print(f"All       /theme-shuffle --list")


if __name__ == "__main__":
    main()
