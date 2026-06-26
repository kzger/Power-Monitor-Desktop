from __future__ import annotations

from dataclasses import dataclass
import threading
import tkinter as tk
from tkinter import ttk

from app.config import APP_NAME, AppConfig, load_config_from_env, save_config
from app.power_reader import LibreHardwareMonitorReader, PowerSummary
from app.startup_task import is_startup_task_installed, set_startup_task_enabled


@dataclass(frozen=True)
class OverlaySettings:
    transparent_color: str
    text_fill: str
    text_outline: str
    text_shadow: str
    text_colors: tuple[tuple[str, str], ...]
    default_font_size: int
    min_font_size: int
    max_font_size: int
    always_on_top: bool


@dataclass(frozen=True)
class PanelSettings:
    geometry: str
    min_width: int
    min_height: int


def overlay_settings() -> OverlaySettings:
    return OverlaySettings(
        transparent_color="#010203",
        text_fill="#ffffff",
        text_outline="#000000",
        text_shadow="#111827",
        text_colors=(
            ("White", "#ffffff"),
            ("Amber", "#facc15"),
            ("Cyan", "#22d3ee"),
            ("Lime", "#a3e635"),
            ("Pink", "#f472b6"),
        ),
        default_font_size=42,
        min_font_size=18,
        max_font_size=120,
        always_on_top=True,
    )


def panel_settings() -> PanelSettings:
    return PanelSettings(
        geometry="400x480",
        min_width=340,
        min_height=450,
    )


def clamp_font_size(font_size: int, settings: OverlaySettings) -> int:
    return max(settings.min_font_size, min(settings.max_font_size, font_size))


def overlay_window_size(text: str, font_size: int) -> tuple[int, int]:
    width = max(160, int(len(text) * font_size * 0.62) + 46)
    height = max(64, int(font_size * 1.25) + 23)
    return width, height


class PowerMonitorApp:
    def __init__(
        self,
        root: tk.Tk,
        reader: LibreHardwareMonitorReader,
        config: AppConfig,
    ) -> None:
        self.root = root
        self.reader = reader
        self.config = config
        self.settings = overlay_settings()
        self.panel_settings = panel_settings()
        self._after_id: str | None = None
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._display_mode = config.display_mode
        self._startup_task_busy = False
        self._closed = False

        self.total_var = tk.StringVar(value="-- W")
        self.cpu_var = tk.StringVar(value="-- W")
        self.gpu_var = tk.StringVar(value="-- W")
        self.other_var = tk.StringVar(value="-- W")
        self.sensor_count_var = tk.StringVar(value="Sensors: --")
        self.status_var = tk.StringVar(value="Starting...")
        self.baseline_var = tk.DoubleVar(value=config.baseline_watts)
        self.font_size_var = tk.IntVar(
            value=clamp_font_size(config.watt_font_size, self.settings)
        )
        self.text_color_name_var = tk.StringVar(
            value=self._valid_text_color_name(config.text_color_name)
        )
        self.always_on_top_var = tk.BooleanVar(value=config.always_on_top)
        self.startup_enabled_var = tk.BooleanVar(value=False)

        self._configure_window()
        self._configure_styles()
        self._build_overlay()
        self._build_panel()
        self._bind_interactions()
        self.root.after(100, self._check_startup_task_async)
        self._apply_display_mode(config.display_mode, save=False)
        self._schedule_refresh(initial=True)

    def _configure_window(self) -> None:
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.configure(background=self.settings.transparent_color)
        self.root.attributes("-topmost", self.always_on_top_var.get())
        try:
            self.root.attributes("-transparentcolor", self.settings.transparent_color)
        except tk.TclError:
            # Windows supports transparentcolor; this keeps other platforms usable.
            pass

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f6f8fb")
        style.configure("Panel.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#ffffff", foreground="#344054")
        style.configure("Total.TLabel", background="#ffffff", foreground="#111827")
        style.configure("Metric.TLabel", background="#ffffff", foreground="#1f2937")
        style.configure("Muted.TLabel", background="#ffffff", foreground="#667085")
        style.configure("Status.TLabel", background="#ffffff", foreground="#9a3412")
        style.configure("App.TCheckbutton", background="#ffffff", foreground="#1f2937")
        style.configure("App.TButton", padding=(10, 5))

    def _build_overlay(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            background=self.settings.transparent_color,
            highlightthickness=0,
            borderwidth=0,
        )

    def _build_panel(self) -> None:
        self.panel_frame = ttk.Frame(self.root, padding=12, style="App.TFrame")
        panel = ttk.Frame(self.panel_frame, padding=14, style="Panel.TFrame")
        panel.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(
            panel,
            text="TOTAL POWER",
            anchor="center",
            style="Title.TLabel",
            font=("Segoe UI", 9, "bold"),
        )
        title.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.panel_total_label = ttk.Label(
            panel,
            textvariable=self.total_var,
            anchor="center",
            style="Total.TLabel",
            font=("Segoe UI", 30, "bold"),
        )
        self.panel_total_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 12))

        self._add_value_row(panel, 2, "CPU", self.cpu_var)
        self._add_value_row(panel, 3, "GPU", self.gpu_var)
        self._add_value_row(panel, 4, "Other / baseline", self.other_var)

        ttk.Label(panel, text="Baseline W", style="Muted.TLabel").grid(
            row=5,
            column=0,
            sticky="w",
            pady=(12, 0),
        )
        baseline = ttk.Spinbox(
            panel,
            from_=0,
            to=500,
            increment=1,
            textvariable=self.baseline_var,
            width=8,
            command=self._baseline_changed,
        )
        baseline.grid(row=5, column=1, sticky="e", pady=(12, 0))
        baseline.bind("<Return>", lambda _event: self._baseline_changed())
        baseline.bind("<FocusOut>", lambda _event: self._baseline_changed())

        ttk.Label(panel, text="Watt font size", style="Muted.TLabel").grid(
            row=6,
            column=0,
            sticky="w",
            pady=(8, 0),
        )
        font_size = ttk.Spinbox(
            panel,
            from_=self.settings.min_font_size,
            to=self.settings.max_font_size,
            increment=4,
            textvariable=self.font_size_var,
            width=8,
            command=self._apply_font_size_from_control,
        )
        font_size.grid(row=6, column=1, sticky="e", pady=(8, 0))
        font_size.bind("<Return>", lambda _event: self._apply_font_size_from_control())
        font_size.bind("<FocusOut>", lambda _event: self._apply_font_size_from_control())

        ttk.Label(panel, text="Watt text color", style="Muted.TLabel").grid(
            row=7,
            column=0,
            sticky="w",
            pady=(8, 0),
        )
        text_color = ttk.Combobox(
            panel,
            textvariable=self.text_color_name_var,
            values=tuple(name for name, _color in self.settings.text_colors),
            state="readonly",
            width=8,
        )
        text_color.grid(row=7, column=1, sticky="e", pady=(8, 0))
        text_color.bind("<<ComboboxSelected>>", lambda _event: self._apply_text_color())

        always_on_top = ttk.Checkbutton(
            panel,
            text="Always on top",
            variable=self.always_on_top_var,
            command=self._apply_always_on_top,
            style="App.TCheckbutton",
        )
        always_on_top.grid(row=8, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.startup_task_checkbutton = ttk.Checkbutton(
            panel,
            text="Start at Windows logon",
            variable=self.startup_enabled_var,
            command=self._apply_startup_task,
            style="App.TCheckbutton",
        )
        self.startup_task_checkbutton.grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 0),
        )

        overlay_button = ttk.Button(
            panel,
            text="Overlay view",
            command=self.toggle_display_mode,
            style="App.TButton",
        )
        overlay_button.grid(row=10, column=0, sticky="w", pady=(10, 0))

        exit_button = ttk.Button(panel, text="Exit", command=self.close, style="App.TButton")
        exit_button.grid(row=10, column=1, sticky="e", pady=(10, 0))

        ttk.Label(panel, textvariable=self.sensor_count_var, style="Muted.TLabel").grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )
        ttk.Label(
            panel,
            textvariable=self.status_var,
            style="Status.TLabel",
            wraplength=320,
        ).grid(row=12, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        self.panel_frame.columnconfigure(0, weight=1)
        self.panel_frame.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

    def _add_value_row(
        self,
        parent: ttk.Frame,
        row: int,
        label_text: str,
        value_var: tk.StringVar,
    ) -> None:
        ttk.Label(parent, text=label_text, style="Muted.TLabel").grid(
            row=row,
            column=0,
            sticky="w",
            pady=3,
        )
        ttk.Label(
            parent,
            textvariable=value_var,
            anchor="e",
            style="Metric.TLabel",
            font=("Segoe UI", 10, "bold"),
        ).grid(row=row, column=1, sticky="e", pady=3)

    def _bind_interactions(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Double-Button-1>", self._on_double_click)
        self.root.bind("<plus>", lambda _event: self.adjust_font_size(4))
        self.root.bind("<KP_Add>", lambda _event: self.adjust_font_size(4))
        self.root.bind("<minus>", lambda _event: self.adjust_font_size(-4))
        self.root.bind("<KP_Subtract>", lambda _event: self.adjust_font_size(-4))
        self.root.bind("<Escape>", lambda _event: self.close())
        self.root.bind("<Button-3>", self._show_context_menu)
        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._drag_window)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-3>", self._show_context_menu)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

        self.menu = tk.Menu(self.root, tearoff=False)
        self.menu.add_command(label="Show full menu", command=self.toggle_display_mode)
        self.menu.add_separator()
        self.menu.add_command(
            label="Increase watt size",
            command=lambda: self.adjust_font_size(4),
        )
        self.menu.add_command(
            label="Decrease watt size",
            command=lambda: self.adjust_font_size(-4),
        )
        self.menu.add_command(label="Reset watt size", command=self.reset_font_size)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.close)

    def _apply_display_mode(self, mode: str, save: bool = True) -> None:
        self._display_mode = mode if mode in {"overlay", "panel"} else "overlay"
        if self._display_mode == "overlay":
            self.panel_frame.pack_forget()
            self.canvas.pack(fill="both", expand=True)
            self.root.overrideredirect(True)
            self.root.configure(background=self.settings.transparent_color)
            try:
                self.root.attributes("-transparentcolor", self.settings.transparent_color)
            except tk.TclError:
                pass
            self._apply_always_on_top(save=False)
            self._redraw_wattage()
        else:
            self.canvas.pack_forget()
            try:
                self.root.attributes("-transparentcolor", "")
            except tk.TclError:
                pass
            self.root.overrideredirect(False)
            self.root.configure(background="#f6f8fb")
            self.panel_frame.pack(fill="both", expand=True)
            self.root.geometry(self.panel_settings.geometry)
            self.root.minsize(self.panel_settings.min_width, self.panel_settings.min_height)
            self._apply_always_on_top(save=False)
            self._update_panel_font()
            self.root.update_idletasks()
        if save:
            self._save_current_config()

    def toggle_display_mode(self) -> None:
        next_mode = "panel" if self._display_mode == "overlay" else "overlay"
        self._apply_display_mode(next_mode)

    def _on_double_click(self, _event: tk.Event) -> str:
        self.toggle_display_mode()
        return "break"

    def _apply_always_on_top(self, save: bool = True) -> None:
        self.root.attributes("-topmost", self.always_on_top_var.get())
        if save:
            self._save_current_config()

    def _schedule_refresh(self, initial: bool = False) -> None:
        self.refresh_now()
        self._after_id = self.root.after(
            self.config.update_interval_ms,
            self._schedule_refresh,
        )

    def refresh_now(self) -> None:
        summary = self.reader.read_summary(self._baseline_value())
        self._render_summary(summary)

    def _baseline_changed(self) -> None:
        self.refresh_now()
        self._save_current_config()

    def _baseline_value(self) -> float:
        try:
            return max(0.0, float(self.baseline_var.get()))
        except (tk.TclError, ValueError):
            return self.config.baseline_watts

    def _render_summary(self, summary: PowerSummary) -> None:
        self.total_var.set(_format_watts(summary.total_watts))
        self.cpu_var.set(_format_watts(summary.cpu_watts))
        self.gpu_var.set(_format_watts(summary.gpu_watts))
        self.other_var.set(_format_watts(summary.other_watts))
        self.sensor_count_var.set(f"Sensors: {summary.sensor_count}")
        self.status_var.set(summary.error or "OK")
        if self._display_mode == "overlay":
            self._redraw_wattage()
        else:
            self._update_panel_font()

    def adjust_font_size(self, delta: int) -> None:
        next_size = clamp_font_size(
            self.font_size_var.get() + delta,
            self.settings,
        )
        self.font_size_var.set(next_size)
        if self._display_mode == "overlay":
            self._redraw_wattage()
        else:
            self._update_panel_font()
        self._save_current_config()

    def reset_font_size(self) -> None:
        self.font_size_var.set(self.settings.default_font_size)
        if self._display_mode == "overlay":
            self._redraw_wattage()
        else:
            self._update_panel_font()
        self._save_current_config()

    def _apply_font_size_from_control(self) -> None:
        try:
            requested_size = int(float(self.font_size_var.get()))
        except (tk.TclError, ValueError):
            requested_size = self.settings.default_font_size
        self.font_size_var.set(clamp_font_size(requested_size, self.settings))
        if self._display_mode == "overlay":
            self._redraw_wattage()
        else:
            self._update_panel_font()
        self._save_current_config()

    def _apply_text_color(self) -> None:
        if self._display_mode == "overlay":
            self._redraw_wattage()
        self._save_current_config()

    def _update_panel_font(self) -> None:
        panel_size = min(40, max(24, self.font_size_var.get()))
        if hasattr(self, "panel_total_label"):
            self.panel_total_label.configure(font=("Segoe UI", panel_size, "bold"))

    def _redraw_wattage(self) -> None:
        if self._display_mode != "overlay":
            return
        text = self.total_var.get()
        font_size = self.font_size_var.get()
        width, height = overlay_window_size(text, font_size)

        self.root.geometry(f"{width}x{height}")
        self.canvas.configure(width=width, height=height)
        self.canvas.delete("all")

        x = width // 2
        y = height // 2
        font = ("Segoe UI", font_size, "bold")

        # Draw a heavy outline so the white number remains readable anywhere.
        for offset_x, offset_y in _outline_offsets(font_size):
            self.canvas.create_text(
                x + offset_x,
                y + offset_y,
                text=text,
                fill=self.settings.text_outline,
                font=font,
            )

        self.canvas.create_text(
            x + 3,
            y + 3,
            text=text,
            fill=self.settings.text_shadow,
            font=font,
        )
        self.canvas.create_text(
            x,
            y,
            text=text,
            fill=self._selected_text_color(),
            font=font,
        )

    def _selected_text_color(self) -> str:
        color_by_name = dict(self.settings.text_colors)
        return color_by_name.get(self.text_color_name_var.get(), self.settings.text_fill)

    def _valid_text_color_name(self, color_name: str) -> str:
        valid_names = {name for name, _color in self.settings.text_colors}
        return color_name if color_name in valid_names else "White"

    def _sync_startup_task_state(self) -> None:
        try:
            self.startup_enabled_var.set(is_startup_task_installed())
        except Exception as exc:
            self.startup_enabled_var.set(False)
            self.status_var.set(f"Could not check startup task: {exc}")

    def _check_startup_task_async(self) -> None:
        def worker() -> None:
            error: Exception | None = None
            enabled = False
            try:
                enabled = is_startup_task_installed()
            except Exception as exc:
                error = exc
            self._run_on_ui_thread(
                lambda: self._finish_startup_task_check(enabled, error)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_startup_task_check(
        self,
        enabled: bool,
        error: Exception | None,
    ) -> None:
        if self._startup_task_busy:
            return
        if error is not None:
            self.status_var.set(f"Could not check startup task: {error}")
            return
        self.startup_enabled_var.set(enabled)

    def _apply_startup_task(self) -> None:
        if self._startup_task_busy:
            return

        requested = self.startup_enabled_var.get()
        self._set_startup_task_busy(True)
        action = "Enabling" if requested else "Disabling"
        self.status_var.set(f"{action} startup task...")

        def worker() -> None:
            error: Exception | None = None
            enabled = False
            try:
                set_startup_task_enabled(requested)
                enabled = is_startup_task_installed()
            except Exception as exc:
                error = exc
                try:
                    enabled = is_startup_task_installed()
                except Exception:
                    enabled = not requested
            self._run_on_ui_thread(
                lambda: self._finish_startup_task_change(enabled, error)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _finish_startup_task_change(
        self,
        enabled: bool,
        error: Exception | None,
    ) -> None:
        self._set_startup_task_busy(False)
        self.startup_enabled_var.set(enabled)
        if error is not None:
            self.status_var.set(f"Startup task change failed: {error}")
            return
        state = "enabled" if enabled else "disabled"
        self.status_var.set(f"Startup task {state}.")

    def _set_startup_task_busy(self, busy: bool) -> None:
        self._startup_task_busy = busy
        if hasattr(self, "startup_task_checkbutton"):
            self.startup_task_checkbutton.configure(
                state="disabled" if busy else "normal"
            )

    def _run_on_ui_thread(self, callback) -> None:
        if self._closed:
            return
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def _save_current_config(self) -> None:
        config = AppConfig(
            baseline_watts=self._baseline_value(),
            update_interval_ms=self.config.update_interval_ms,
            always_on_top=self.always_on_top_var.get(),
            display_mode=self._display_mode,
            watt_font_size=self.font_size_var.get(),
            text_color_name=self.text_color_name_var.get(),
        )
        try:
            save_config(config)
            self.config = config
        except Exception as exc:
            self.status_var.set(f"Could not save settings: {exc}")

    def _start_drag(self, event: tk.Event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _drag_window(self, event: tk.Event) -> None:
        x = self.root.winfo_pointerx() - self._drag_start_x
        y = self.root.winfo_pointery() - self._drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        delta = 4 if event.delta > 0 else -4
        self.adjust_font_size(delta)

    def _show_context_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)

    def close(self) -> None:
        self._closed = True
        self._save_current_config()
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.reader.close()
        self.root.destroy()


def _outline_offsets(font_size: int) -> tuple[tuple[int, int], ...]:
    radius = max(2, round(font_size / 18))
    offsets: list[tuple[int, int]] = []
    for x in range(-radius, radius + 1):
        for y in range(-radius, radius + 1):
            if x == 0 and y == 0:
                continue
            if abs(x) in (radius, radius - 1) or abs(y) in (radius, radius - 1):
                offsets.append((x, y))
    return tuple(offsets)


def _format_watts(value: float) -> str:
    return f"{value:.1f} W"


def main() -> None:
    config = load_config_from_env()
    reader = LibreHardwareMonitorReader()
    root = tk.Tk()
    PowerMonitorApp(root, reader, config)
    root.mainloop()


if __name__ == "__main__":
    main()
