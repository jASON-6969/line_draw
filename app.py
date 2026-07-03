from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


DEFAULT_MAX_X = 10.0
DEFAULT_MAX_Y = 10.0
DEFAULT_DEGREE = 5
MIN_POINTS = 2
MAX_DEGREE = 12
MAX_TAN_ABS = 20.0


BasisTerm = tuple[str, int | None]


class PolynomialDrawApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Line Draw Polynomial Fitter")
        self.root.minsize(720, 520)
        self.root.resizable(True, True)

        self.points: list[tuple[float, float]] = []
        self.drawing = False
        self.picking_start_point = False

        self.max_x_var = tk.StringVar(value=str(DEFAULT_MAX_X))
        self.max_y_var = tk.StringVar(value=str(DEFAULT_MAX_Y))
        self.use_start_point_var = tk.BooleanVar(value=False)
        self.start_x_var = tk.StringVar(value="0")
        self.start_y_var = tk.StringVar(value="0")
        self.use_sin_var = tk.BooleanVar(value=False)
        self.use_cos_var = tk.BooleanVar(value=False)
        self.use_tan_var = tk.BooleanVar(value=False)
        self.degree_var = tk.IntVar(value=DEFAULT_DEGREE)
        self.equation_var = tk.StringVar(value="y = ")
        self.status_var = tk.StringVar(value="Hold left mouse button and drag inside the graph.")

        self._build_layout()
        self._connect_plot_events()
        self.apply_axis_limits()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.root, padding=(10, 10, 10, 6))
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(7, weight=1)

        ttk.Label(controls, text="Max X").grid(row=0, column=0, padx=(0, 4))
        ttk.Entry(controls, width=8, textvariable=self.max_x_var).grid(row=0, column=1, padx=(0, 12))

        ttk.Label(controls, text="Max Y").grid(row=0, column=2, padx=(0, 4))
        ttk.Entry(controls, width=8, textvariable=self.max_y_var).grid(row=0, column=3, padx=(0, 12))

        ttk.Button(controls, text="Apply Size", command=self.apply_axis_limits).grid(
            row=0, column=4, padx=(0, 16)
        )

        ttk.Label(controls, text="Degree").grid(row=0, column=5, padx=(0, 4))
        self.degree_spinbox = ttk.Spinbox(
            controls,
            from_=1,
            to=MAX_DEGREE,
            width=5,
            textvariable=self.degree_var,
            command=self.refit_if_possible,
        )
        self.degree_spinbox.grid(row=0, column=6, padx=(0, 8))

        self.degree_slider = ttk.Scale(
            controls,
            from_=1,
            to=MAX_DEGREE,
            orient="horizontal",
            variable=self.degree_var,
            command=self._on_degree_slider,
        )
        self.degree_slider.grid(row=0, column=7, sticky="ew", padx=(0, 16))

        ttk.Button(controls, text="Clear", command=self.clear).grid(row=0, column=8)

        ttk.Checkbutton(
            controls,
            text="Use Start Point",
            variable=self.use_start_point_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(controls, text="Start X").grid(row=1, column=2, padx=(0, 4), pady=(8, 0))
        ttk.Entry(controls, width=8, textvariable=self.start_x_var).grid(row=1, column=3, padx=(0, 12), pady=(8, 0))

        ttk.Label(controls, text="Start Y").grid(row=1, column=4, padx=(0, 4), pady=(8, 0))
        ttk.Entry(controls, width=8, textvariable=self.start_y_var).grid(row=1, column=5, padx=(0, 12), pady=(8, 0))
        ttk.Button(controls, text="Pick Start", command=self.begin_pick_start_point).grid(
            row=1, column=6, padx=(0, 12), pady=(8, 0)
        )
        ttk.Checkbutton(controls, text="sin", variable=self.use_sin_var, command=self.refit_if_possible).grid(
            row=1, column=7, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(controls, text="cos", variable=self.use_cos_var, command=self.refit_if_possible).grid(
            row=1, column=8, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(controls, text="tan", variable=self.use_tan_var, command=self.refit_if_possible).grid(
            row=1, column=9, sticky="w", pady=(8, 0)
        )

        plot_area = ttk.Frame(self.root, padding=(10, 0, 10, 0))
        plot_area.grid(row=1, column=0, sticky="nsew")
        plot_area.columnconfigure(0, weight=1)
        plot_area.rowconfigure(0, weight=1)

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_xlabel("x")
        self.ax.set_ylabel("y")
        self.ax.grid(True, alpha=0.25)

        self.raw_line = self.ax.plot([], [], "b.", markersize=4, label="drawn points")[0]
        self.fit_line = self.ax.plot([], [], "r-", linewidth=2, label="fit")[0]
        self.ax.legend(loc="upper right")

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(plot_area)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame, pack_toolbar=False)
        toolbar.grid(row=0, column=0, sticky="w")

        output = ttk.Frame(self.root, padding=(10, 8, 10, 10))
        output.grid(row=2, column=0, sticky="ew")
        output.columnconfigure(1, weight=1)

        ttk.Label(output, text="Function").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(output, textvariable=self.equation_var, state="readonly").grid(row=0, column=1, sticky="ew")
        ttk.Label(output, textvariable=self.status_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _connect_plot_events(self) -> None:
        self.canvas.mpl_connect("button_press_event", self.on_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_move)
        self.canvas.mpl_connect("button_release_event", self.on_release)

    def apply_axis_limits(self) -> None:
        max_x = self._parse_positive_float(self.max_x_var.get(), "Max X")
        max_y = self._parse_positive_float(self.max_y_var.get(), "Max Y")
        if max_x is None or max_y is None:
            return

        self.ax.set_xlim(-max_x, max_x)
        self.ax.set_ylim(-max_y, max_y)
        self.canvas.draw_idle()
        self.status_var.set(f"Graph size set to x: {-max_x:g}..{max_x:g}, y: {-max_y:g}..{max_y:g}.")

    def on_press(self, event: object) -> None:
        if not self._is_valid_draw_event(event):
            return

        if self.picking_start_point:
            self.set_start_point_from_event(event)
            return

        first_point = self._get_start_point()
        if first_point is None:
            return
        if not self.use_start_point_var.get():
            first_point = (float(event.xdata), float(event.ydata))  # type: ignore[attr-defined]

        self.drawing = True
        self.points = [first_point]
        if first_point != (float(event.xdata), float(event.ydata)):  # type: ignore[attr-defined]
            self.points.append((float(event.xdata), float(event.ydata)))  # type: ignore[attr-defined]
        self.fit_line.set_data([], [])
        self.equation_var.set("y = ")
        self.status_var.set("Drawing...")
        self._refresh_raw_points()

    def on_move(self, event: object) -> None:
        if not self.drawing or not self._is_valid_draw_event(event):
            return

        self.points.append((float(event.xdata), float(event.ydata)))  # type: ignore[attr-defined]
        self._refresh_raw_points()

    def on_release(self, event: object) -> None:
        if not self.drawing:
            return

        self.drawing = False
        if self._is_valid_draw_event(event):
            self.points.append((float(event.xdata), float(event.ydata)))  # type: ignore[attr-defined]
            self._refresh_raw_points()

        self.fit_and_report()

    def fit_and_report(self) -> None:
        if len(self.points) < MIN_POINTS:
            self.status_var.set("Not enough points. Draw a longer line.")
            return

        degree = self._current_degree()
        x_unique, y_avg = self._sorted_unique_points()
        effective_degree = min(degree, len(x_unique) - 1)
        if effective_degree < 1:
            self.status_var.set("Need at least two different x values.")
            return

        fit = self.fit_curve(x_unique, y_avg, effective_degree)
        if fit is None:
            self.status_var.set("Not enough stable points for the selected function terms.")
            return
        coefficients, terms, fit_x, fit_y = fit

        x_fit = np.linspace(float(fit_x.min()), float(fit_x.max()), 300)
        y_fit = self.evaluate_terms(x_fit, coefficients, terms)
        self.fit_line.set_data(x_fit, y_fit)

        equation = f"y = {self.format_equation(coefficients, terms)}"
        self.equation_var.set(equation)
        print("Fitted function:")
        print(equation)

        if effective_degree != degree:
            self.status_var.set(f"Only {len(x_unique)} unique x values; degree reduced to {effective_degree}.")
        elif fit_x.size != x_unique.size:
            self.status_var.set("Fit complete. Some tan-unstable points were skipped.")
        else:
            self.status_var.set("Fit complete.")

        self.canvas.draw_idle()

    def refit_if_possible(self) -> None:
        self._normalize_degree_var()
        if len(self.points) >= MIN_POINTS:
            self.fit_and_report()

    def clear(self) -> None:
        self.points = []
        self.drawing = False
        self.raw_line.set_data([], [])
        self.fit_line.set_data([], [])
        self.equation_var.set("y = ")
        self.status_var.set("Cleared. Hold left mouse button and draw again.")
        self.canvas.draw_idle()

    def begin_pick_start_point(self) -> None:
        self.picking_start_point = True
        self.status_var.set("Click one point in the graph to use as the start point.")

    def set_start_point_from_event(self, event: object) -> None:
        start_x = float(event.xdata)  # type: ignore[attr-defined]
        start_y = float(event.ydata)  # type: ignore[attr-defined]
        self.start_x_var.set(f"{start_x:.6g}")
        self.start_y_var.set(f"{start_y:.6g}")
        self.use_start_point_var.set(True)
        self.picking_start_point = False
        self.status_var.set(f"Start point set to ({start_x:.6g}, {start_y:.6g}).")
        self.canvas.draw_idle()

    def _on_degree_slider(self, _value: str) -> None:
        self._normalize_degree_var()
        self.refit_if_possible()

    def _current_degree(self) -> int:
        self._normalize_degree_var()
        return self.degree_var.get()

    def _normalize_degree_var(self) -> None:
        try:
            degree = int(float(self.degree_var.get()))
        except (tk.TclError, ValueError):
            degree = DEFAULT_DEGREE
        self.degree_var.set(max(1, min(MAX_DEGREE, degree)))

    def _refresh_raw_points(self) -> None:
        if not self.points:
            self.raw_line.set_data([], [])
        else:
            xs, ys = zip(*self.points)
            self.raw_line.set_data(xs, ys)
        self.canvas.draw_idle()

    def _sorted_unique_points(self) -> tuple[np.ndarray, np.ndarray]:
        pts = np.array(self.points, dtype=float)
        order = np.argsort(pts[:, 0])
        x = pts[order, 0]
        y = pts[order, 1]

        rounded_x = np.round(x, decimals=5)
        x_unique, inverse = np.unique(rounded_x, return_inverse=True)
        y_sum = np.zeros_like(x_unique, dtype=float)
        counts = np.zeros_like(x_unique, dtype=float)

        np.add.at(y_sum, inverse, y)
        np.add.at(counts, inverse, 1)

        return x_unique, y_sum / counts

    def fit_curve(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        degree: int,
    ) -> tuple[np.ndarray, list[BasisTerm], np.ndarray, np.ndarray] | None:
        terms = self.build_terms(degree)
        design = self.build_design_matrix(x_values, terms)
        valid_rows = np.all(np.isfinite(design), axis=1)

        if self.use_tan_var.get():
            tan_columns = [index for index, term in enumerate(terms) if term[0] == "tan"]
            for column in tan_columns:
                valid_rows &= np.abs(design[:, column]) <= MAX_TAN_ABS

        fit_x = x_values[valid_rows]
        fit_y = y_values[valid_rows]
        fit_design = design[valid_rows]

        if fit_x.size < len(terms):
            return None

        coefficients, *_ = np.linalg.lstsq(fit_design, fit_y, rcond=None)
        return coefficients, terms, fit_x, fit_y

    def build_terms(self, degree: int) -> list[BasisTerm]:
        terms: list[BasisTerm] = [("poly", power) for power in range(degree, -1, -1)]
        if self.use_sin_var.get():
            terms.append(("sin", None))
        if self.use_cos_var.get():
            terms.append(("cos", None))
        if self.use_tan_var.get():
            terms.append(("tan", None))
        return terms

    def build_design_matrix(self, x_values: np.ndarray, terms: list[BasisTerm]) -> np.ndarray:
        columns: list[np.ndarray] = []
        for kind, power in terms:
            if kind == "poly":
                if power is None:
                    raise ValueError("Polynomial term requires a power.")
                columns.append(np.power(x_values, power))
            elif kind == "sin":
                columns.append(np.sin(x_values))
            elif kind == "cos":
                columns.append(np.cos(x_values))
            elif kind == "tan":
                columns.append(np.tan(x_values))
            else:
                raise ValueError(f"Unknown basis term: {kind}")
        return np.column_stack(columns)

    def evaluate_terms(self, x_values: np.ndarray, coefficients: np.ndarray, terms: list[BasisTerm]) -> np.ndarray:
        design = self.build_design_matrix(x_values, terms)
        y_values = design @ coefficients
        return np.where(np.isfinite(y_values), y_values, np.nan)

    def _get_start_point(self) -> tuple[float, float] | None:
        if not self.use_start_point_var.get():
            return (0.0, 0.0)

        start_x = self._parse_float(self.start_x_var.get(), "Start X")
        start_y = self._parse_float(self.start_y_var.get(), "Start Y")
        if start_x is None or start_y is None:
            return None
        return start_x, start_y

    def _is_valid_draw_event(self, event: object) -> bool:
        if getattr(event, "inaxes", None) != self.ax:
            return False
        if getattr(event, "xdata", None) is None or getattr(event, "ydata", None) is None:
            return False
        if getattr(event, "button", 1) not in (None, 1):
            return False
        return True

    @staticmethod
    def _parse_positive_float(value: str, label: str, show_error: bool = True) -> float | None:
        try:
            parsed = float(value)
        except ValueError:
            if show_error:
                messagebox.showerror("Invalid value", f"{label} must be a number.")
            return None

        if parsed <= 0:
            if show_error:
                messagebox.showerror("Invalid value", f"{label} must be greater than 0.")
            return None
        return parsed

    @staticmethod
    def _parse_float(value: str, label: str, show_error: bool = True) -> float | None:
        try:
            return float(value)
        except ValueError:
            if show_error:
                messagebox.showerror("Invalid value", f"{label} must be a number.")
            return None

    @staticmethod
    def format_equation(coefficients: np.ndarray, terms: list[BasisTerm]) -> str:
        formatted_terms: list[str] = []

        for coefficient, basis_term in zip(coefficients, terms, strict=True):
            if abs(coefficient) < 1e-8:
                continue

            abs_coeff = abs(float(coefficient))
            sign = "-" if coefficient < 0 else "+"
            coeff_text = f"{abs_coeff:.4g}"
            kind, power = basis_term

            if kind == "poly":
                if power == 0:
                    term = coeff_text
                elif power == 1:
                    term = f"{coeff_text}x"
                else:
                    term = f"{coeff_text}x^{power}"
            elif kind in {"sin", "cos", "tan"}:
                term = f"{coeff_text}{kind}(x)"
            else:
                raise ValueError(f"Unknown basis term: {kind}")

            if not formatted_terms:
                formatted_terms.append(f"-{term}" if sign == "-" else term)
            else:
                formatted_terms.append(f" {sign} {term}")

        return "".join(formatted_terms) if formatted_terms else "0"


def main() -> None:
    root = tk.Tk()
    PolynomialDrawApp(root)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
