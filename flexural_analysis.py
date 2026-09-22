"""
flexural_analysis.py
====================
Pure-math engine for Stress-Strain analysis of 3-point Flexural bend test data.
No GUI, no Qt, no hardware dependencies — safe to unit-test standalone.

Inputs  : Load array (N), Displacement array (mm), Span Length (mm), Width (mm), Height (mm)
Outputs : AnalysisResult dataclass containing all key material properties.

Algorithm summary
-----------------
1. Convert raw Load/Displacement → Stress (MPa) / Strain (mm/mm) using flexural formulas.
2. Detect and strip the initial "toe" region (grip seating noise).
3. Find the linear elastic region using a rolling-window R² scan.
4. Compute Flexural Modulus via linear regression over that window.
5. Find Break point (peak stress) — for brittle ceramics, fracture occurs at peak stress.

Note: This engine is designed for brittle materials (ceramics, glass) that fracture
immediately at peak stress. There is no separate yield point or UTS plateau.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    """All key material properties derived from one flexural test."""

    # Raw converted arrays
    stress: List[float] = field(default_factory=list)   # MPa
    strain: List[float] = field(default_factory=list)   # dimensionless

    # Elastic region used for modulus fit (indices into stress/strain)
    elastic_start_idx: int = 0
    elastic_end_idx: int = 0

    # Key properties
    youngs_modulus: Optional[float] = None      # MPa (Flexural Modulus)

    break_stress: Optional[float] = None        # MPa  (peak stress at fracture)
    break_strain: Optional[float] = None        # mm/mm (strain at peak stress)

    # Fit line for plotting: two (strain, stress) points
    modulus_line: Optional[Tuple[List[float], List[float]]] = None

    # Warnings or notes from the engine
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Main engine class
# ---------------------------------------------------------------------------

class FlexuralAnalysisEngine:
    """
    Stateless analysis engine for 3-point flexural tests on brittle materials.

    Parameters
    ----------
    toe_strain_threshold : float
        Strain below which data is considered "toe" (grip seating) and excluded
        from modulus fitting. Default 0.001 (0.1 %).
    elastic_window_size : int
        Number of consecutive points used in the rolling R² scan to locate the
        linear elastic region.
    min_r2 : float
        Minimum R² required to consider a window "linear".
    """

    def __init__(
        self,
        toe_strain_threshold: float = 0.001,
        elastic_window_size: int = 20,
        min_r2: float = 0.995,
    ):
        self.toe_strain_threshold = toe_strain_threshold
        self.elastic_window_size = elastic_window_size
        self.min_r2 = min_r2

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(
        self,
        load: List[float],
        displacement: List[float],
        span_length_mm: float,
        width_mm: float,
        height_mm: float,
        manual_elastic_range: Optional[Tuple[float, float]] = None,
    ) -> AnalysisResult:
        """
        Run the full flexural analysis pipeline.
        """
        result = AnalysisResult()

        # ---- 0. Basic validation ----------------------------------------
        if len(load) != len(displacement):
            result.warnings.append("Load and displacement arrays have different lengths — truncating.")
            n = min(len(load), len(displacement))
            load = load[:n]
            displacement = displacement[:n]

        if len(load) < 10:
            result.warnings.append("Fewer than 10 data points — results unreliable.")

        if len(load) == 0:
            result.warnings.append("No data points provided.")
            return result

        if span_length_mm <= 0 or width_mm <= 0 or height_mm <= 0:
            result.warnings.append("Sample dimensions must be positive.")
            return result

        # ---- Auto-detect Negative Direction Test ------------------------
        if min(load) < 0 and abs(min(load)) > max(load):
            load = [-x for x in load]
            displacement = [-x for x in displacement]
            result.warnings.append("Test recorded with negative values: Data inverted for analysis.")

        # ---- 1. Convert to Stress / Strain (Flexural) -------------------
        load_np = np.array(load, dtype=float)
        disp_np = np.array(displacement, dtype=float)

        stress = (3.0 * load_np * span_length_mm) / (2.0 * width_mm * (height_mm ** 2))
        strain = (6.0 * disp_np * height_mm) / (span_length_mm ** 2)

        result.stress = stress.tolist()
        result.strain = strain.tolist()

        # ---- 2. Break point = Peak stress --------------------------------
        # For brittle ceramics, fracture occurs at peak stress.
        # The strain at peak stress is the true break strain — any displacement
        # recorded after this point is the loading rod travelling into the
        # broken sample (phantom displacement).
        peak_idx = int(np.argmax(stress))
        result.break_stress = float(stress[peak_idx])
        result.break_strain = float(strain[peak_idx])

        # Guard: if peak stress is zero or negative, something is wrong
        if result.break_stress <= 0:
            result.warnings.append("Peak stress is zero or negative — check load data.")
            return result

        # ---- 3. Locate elastic region -----------------------------------
        if manual_elastic_range is not None:
            e_start, e_end = manual_elastic_range
            # Validate: start must be less than end
            if e_start >= e_end:
                result.warnings.append(
                    "Manual elastic range start must be less than end — auto-detection used instead."
                )
                elastic_indices = self._auto_detect_elastic(strain, stress)
            else:
                mask = (strain >= e_start) & (strain <= e_end)
                elastic_indices = np.where(mask)[0]
                if len(elastic_indices) < 5:
                    result.warnings.append(
                        "Manual elastic range contains fewer than 5 points — auto-detection used instead."
                    )
                    elastic_indices = self._auto_detect_elastic(strain, stress)
        else:
            elastic_indices = self._auto_detect_elastic(strain, stress)

        if len(elastic_indices) < 3:
            result.warnings.append("Could not detect a reliable linear elastic region.")
            return result

        result.elastic_start_idx = int(elastic_indices[0])
        result.elastic_end_idx   = int(elastic_indices[-1])

        e_strain = strain[elastic_indices]
        e_stress = stress[elastic_indices]

        # ---- 4. Modulus via linear regression ---------------------------
        slope, intercept, r_value, _, _ = stats.linregress(e_strain, e_stress)
        if r_value ** 2 < 0.98:
            result.warnings.append(
                f"Elastic region R² = {r_value**2:.4f} — modulus fit may be unreliable."
            )
        result.youngs_modulus = float(slope)

        # Build modulus line for plotting
        elastic_strain_range = float(strain[result.elastic_end_idx]) - float(strain[result.elastic_start_idx])
        # Extend the line a bit past the elastic region for visual clarity
        plot_end_strain = float(strain[result.elastic_end_idx]) + elastic_strain_range
        plot_strain = [float(strain[result.elastic_start_idx]), plot_end_strain]
        plot_stress = [slope * s + intercept for s in plot_strain]
        result.modulus_line = (plot_strain, plot_stress)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _auto_detect_elastic(self, strain: np.ndarray, stress: np.ndarray) -> np.ndarray:
        """
        Automatically detect the linear elastic region using a rolling-window
        slope consistency scan. Only searches up to the peak stress index to
        avoid including the post-fracture phantom displacement region.
        """
        peak_idx = int(np.argmax(stress))
        sw = max(5, len(strain) // 100)

        start = int(np.searchsorted(strain, self.toe_strain_threshold))
        start = max(start, sw)

        scan_limit = min(peak_idx, len(strain) - sw)
        if scan_limit <= start:
            return np.arange(0, min(10, len(strain)))

        slopes = np.zeros(len(strain))
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for i in range(start, scan_limit):
                x_win = strain[i: i + sw]
                y_win = stress[i: i + sw]
                if np.ptp(x_win) == 0:
                    slopes[i] = 0.0
                else:
                    sl, _, _, _, _ = stats.linregress(x_win, y_win)
                    slopes[i] = sl if not np.isnan(sl) else 0.0

        peak_slope_idx = int(np.argmax(slopes[start:scan_limit])) + start
        peak_slope = slopes[peak_slope_idx]

        if peak_slope <= 0:
            w = self.elastic_window_size
            return np.arange(start, min(start + w, len(strain)))

        tolerance = 0.70
        elastic_end = peak_slope_idx
        for i in range(peak_slope_idx, min(scan_limit, len(strain) - sw)):
            if slopes[i] > 0 and slopes[i] >= tolerance * peak_slope:
                elastic_end = i
            else:
                break

        elastic_end = min(elastic_end + sw, len(strain) - 1)
        return np.arange(start, elastic_end + 1)

