"""WITPAE Theater Staff — main application entry point.

Launch with:
    python src/witpae_theater_staff/main.py
or via the provided run_gui.bat launcher on Windows.
"""

import tkinter as tk
from tkinter import ttk


def main() -> None:
    """Create and run the WITPAE Theater Staff GUI application."""
    root = tk.Tk()
    root.title("WITPAE Theater Staff")
    root.geometry("800x600")
    root.resizable(True, True)

    # ── Root grid weights ────────────────────────────────────────────────────
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # ── Main frame ───────────────────────────────────────────────────────────
    main_frame = ttk.Frame(root, padding=20)
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(2, weight=1)

    # ── Title label ──────────────────────────────────────────────────────────
    title_label = ttk.Label(
        main_frame,
        text="WITPAE Theater Staff",
        font=("Arial", 28, "bold"),
        anchor=tk.CENTER,
    )
    title_label.grid(row=0, column=0, pady=(20, 5), sticky=(tk.W, tk.E))

    # ── Subtitle label ───────────────────────────────────────────────────────
    subtitle_label = ttk.Label(
        main_frame,
        text="War in the Pacific Admiral's Edition — Theater Staff Tool",
        font=("Arial", 13),
        anchor=tk.CENTER,
    )
    subtitle_label.grid(row=1, column=0, pady=(0, 20), sticky=(tk.W, tk.E))

    # ── Placeholder canvas (future hex-map area) ─────────────────────────────
    canvas = tk.Canvas(main_frame, background="#1a3a1a", relief=tk.SUNKEN, bd=2)
    canvas.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
    canvas.bind(
        "<Configure>",
        lambda event: _draw_placeholder(canvas, event.width, event.height),
    )

    # ── Status bar ───────────────────────────────────────────────────────────
    status_bar = ttk.Label(
        main_frame,
        text="Ready",
        relief=tk.SUNKEN,
        anchor=tk.W,
        padding=(4, 2),
    )
    status_bar.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    root.mainloop()


def _draw_placeholder(canvas: tk.Canvas, width: int, height: int) -> None:
    """Draw a placeholder message on the map canvas."""
    canvas.delete("all")
    cx, cy = width // 2, height // 2
    canvas.create_text(
        cx,
        cy,
        text="[ Map / Hex-Grid Area — Coming Soon ]",
        fill="#4caf50",
        font=("Courier New", 14),
        anchor=tk.CENTER,
    )


if __name__ == "__main__":
    main()
