#!/usr/bin/env python3
import sys
import tkinter as tk
from gui import GoGUI


def main():
    root = tk.Tk()
    try:
        app = GoGUI(root)
    except Exception as e:
        print(f"Error initializing GUI: {e}", file=sys.stderr)
        sys.exit(1)
    root.mainloop()


if __name__ == '__main__':
    main()
