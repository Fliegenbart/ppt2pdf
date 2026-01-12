"""
Contrast Checker - WCAG color contrast analysis.
"""
import re
from typing import Optional, Tuple
from dataclasses import dataclass

from api.models import (
    AccessibilityIssue, AccessibilityIssueType, AccessibilitySeverity
)


@dataclass
class ContrastResult:
    """Result of a contrast check."""
    ratio: float
    passes_aa_normal: bool
    passes_aa_large: bool
    passes_aaa_normal: bool
    passes_aaa_large: bool
    foreground: str
    background: str


class ContrastChecker:
    """Checks color contrast according to WCAG guidelines."""

    # WCAG 2.1 contrast ratio requirements
    AA_NORMAL_TEXT = 4.5
    AA_LARGE_TEXT = 3.0
    AAA_NORMAL_TEXT = 7.0
    AAA_LARGE_TEXT = 4.5

    # Large text is 18pt or 14pt bold
    LARGE_TEXT_SIZE = 18
    LARGE_TEXT_BOLD_SIZE = 14

    def __init__(self):
        pass

    def check_contrast(
        self,
        foreground: str,
        background: str,
    ) -> ContrastResult:
        """Check contrast ratio between two colors."""
        fg_luminance = self._relative_luminance(foreground)
        bg_luminance = self._relative_luminance(background)

        # Calculate contrast ratio
        lighter = max(fg_luminance, bg_luminance)
        darker = min(fg_luminance, bg_luminance)
        ratio = (lighter + 0.05) / (darker + 0.05)

        return ContrastResult(
            ratio=round(ratio, 2),
            passes_aa_normal=ratio >= self.AA_NORMAL_TEXT,
            passes_aa_large=ratio >= self.AA_LARGE_TEXT,
            passes_aaa_normal=ratio >= self.AAA_NORMAL_TEXT,
            passes_aaa_large=ratio >= self.AAA_LARGE_TEXT,
            foreground=foreground,
            background=background,
        )

    def check_element_contrast(
        self,
        foreground: Optional[str],
        background: Optional[str],
        font_size: Optional[float],
        is_bold: bool,
        slide_number: int,
        element_id: str,
    ) -> Optional[AccessibilityIssue]:
        """Check contrast for a specific element and return issue if failing."""
        if not foreground or not background:
            return None

        # Default colors if not specified
        foreground = foreground or "#000000"
        background = background or "#FFFFFF"

        result = self.check_contrast(foreground, background)

        # Determine if this is large text
        is_large = False
        if font_size:
            if font_size >= self.LARGE_TEXT_SIZE:
                is_large = True
            elif font_size >= self.LARGE_TEXT_BOLD_SIZE and is_bold:
                is_large = True

        # Check against appropriate threshold
        required_ratio = self.AA_LARGE_TEXT if is_large else self.AA_NORMAL_TEXT
        passes = result.ratio >= required_ratio

        if not passes:
            return AccessibilityIssue(
                issue_type=AccessibilityIssueType.LOW_CONTRAST,
                severity=AccessibilitySeverity.ERROR,
                slide_number=slide_number,
                element_id=element_id,
                message=f"Insufficient color contrast ratio: {result.ratio}:1 (required: {required_ratio}:1)",
                suggestion=f"Increase contrast between text ({foreground}) and background ({background})",
                details={
                    "ratio": result.ratio,
                    "required": required_ratio,
                    "foreground": foreground,
                    "background": background,
                    "is_large_text": is_large,
                }
            )

        return None

    def _relative_luminance(self, color: str) -> float:
        """Calculate relative luminance of a color."""
        r, g, b = self._hex_to_rgb(color)

        # Convert to sRGB
        r_srgb = r / 255
        g_srgb = g / 255
        b_srgb = b / 255

        # Apply gamma correction
        r_lin = self._linearize(r_srgb)
        g_lin = self._linearize(g_srgb)
        b_lin = self._linearize(b_srgb)

        # Calculate luminance
        return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin

    def _linearize(self, value: float) -> float:
        """Apply gamma correction to linearize sRGB value."""
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')

        # Handle short hex (#RGB)
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)

        # Parse RGB values
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)
        except (ValueError, IndexError):
            return (0, 0, 0)  # Default to black

    def suggest_improved_color(
        self,
        foreground: str,
        background: str,
        target_ratio: float = 4.5,
    ) -> str:
        """Suggest an improved foreground color that meets contrast requirements."""
        fg_r, fg_g, fg_b = self._hex_to_rgb(foreground)
        bg_luminance = self._relative_luminance(background)

        # Determine if we need to lighten or darken
        fg_luminance = self._relative_luminance(foreground)

        # Try darkening first (usually more readable)
        if bg_luminance > 0.5:
            # Light background - darken foreground
            for factor in range(100):
                new_r = max(0, fg_r - factor * 2)
                new_g = max(0, fg_g - factor * 2)
                new_b = max(0, fg_b - factor * 2)
                new_color = f"#{new_r:02x}{new_g:02x}{new_b:02x}"
                result = self.check_contrast(new_color, background)
                if result.ratio >= target_ratio:
                    return new_color
        else:
            # Dark background - lighten foreground
            for factor in range(100):
                new_r = min(255, fg_r + factor * 2)
                new_g = min(255, fg_g + factor * 2)
                new_b = min(255, fg_b + factor * 2)
                new_color = f"#{new_r:02x}{new_g:02x}{new_b:02x}"
                result = self.check_contrast(new_color, background)
                if result.ratio >= target_ratio:
                    return new_color

        # Fallback to black or white
        black_result = self.check_contrast("#000000", background)
        white_result = self.check_contrast("#FFFFFF", background)
        return "#000000" if black_result.ratio > white_result.ratio else "#FFFFFF"


def analyze_presentation_contrast(presentation, checker: Optional[ContrastChecker] = None) -> list[AccessibilityIssue]:
    """Analyze all text elements in a presentation for contrast issues."""
    if checker is None:
        checker = ContrastChecker()

    issues = []

    for slide in presentation.slides:
        background = slide.background_color or "#FFFFFF"

        for element in slide.elements:
            if element.paragraphs:
                for para in element.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            issue = checker.check_element_contrast(
                                foreground=run.style.color,
                                background=run.style.background_color or background,
                                font_size=run.style.font_size,
                                is_bold=run.style.bold,
                                slide_number=slide.slide_number,
                                element_id=element.id,
                            )
                            if issue:
                                issues.append(issue)

    return issues
