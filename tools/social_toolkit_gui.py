"""Unified Tkinter app for the Discord and Facebook tools."""

from __future__ import annotations

import sys
from pathlib import Path
from tkinter import ttk
from tkinterdnd2 import TkinterDnD

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.discord_interaction.discord_tab import DiscordTab
from tools.facebook_group_repost.facebook_tab import FacebookTab


class SocialToolkitGUI:
    def __init__(self) -> None:
        self.root = TkinterDnD.Tk()
        self.root.title("Social Toolkit")
        self.root.geometry("1100x900")
        self.root.minsize(900, 700)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        discord_tab = DiscordTab(notebook)
        notebook.add(discord_tab, text="Discord")

        self.facebook_tab = FacebookTab(notebook)
        notebook.add(self.facebook_tab, text="Facebook")
        notebook.select(self.facebook_tab)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self) -> None:
        self.facebook_tab.shutdown()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    SocialToolkitGUI().run()


if __name__ == "__main__":
    main()
