"""
Custom CrewAI tool that lets an agent turn labeled numeric data into a
saved chart image (bar, line, or pie) using matplotlib.
"""

import os
from pathlib import Path
from typing import List, Type

import matplotlib

matplotlib.use("Agg")  # headless backend, no display needed
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

from crewai.tools import BaseTool

# Resolve relative to the project root (parent of the tools/ package),
# so the chart directory is always output/charts/ regardless of cwd.
_PROJECT_ROOT = Path(__file__).parent.parent
CHARTS_DIR = str(_PROJECT_ROOT / "output" / "charts")


class ChartGeneratorInput(BaseModel):
    """Input schema for the Chart Generator tool."""

    title: str = Field(
        ..., description="Title of the chart. Also used to build the saved filename."
    )
    chart_type: str = Field(
        ..., description="Type of chart to draw. One of: 'bar', 'line', 'pie'."
    )
    labels: List[str] = Field(
        ..., description="Category labels for the x-axis (or pie slice names)."
    )
    values: List[float] = Field(
        ..., description="Numeric values matching each label, in the same order."
    )
    x_label: str = Field(
        default="", description="Optional x-axis label (ignored for pie charts)."
    )
    y_label: str = Field(
        default="", description="Optional y-axis label (ignored for pie charts)."
    )


class ChartGeneratorTool(BaseTool):
    name: str = "Chart Generator"
    description: str = (
        "Turns labeled numeric data into a bar, line, or pie chart and saves it as a "
        "PNG file under output/charts/. Use this for any statistic or trend worth "
        "visualizing. The tool returns the exact saved filename -- reuse that exact "
        "filename later when referencing the chart in the written report."
    )
    args_schema: Type[BaseModel] = ChartGeneratorInput

    def _run(
        self,
        title: str,
        chart_type: str,
        labels: List[str],
        values: List[float],
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        if len(labels) != len(values):
            return "Error: 'labels' and 'values' must contain the same number of items."
        if not labels:
            return "Error: 'labels' and 'values' cannot be empty."

        os.makedirs(CHARTS_DIR, exist_ok=True)

        safe_name = (
            "".join(c if c.isalnum() or c in (" ", "_", "-") else "" for c in title)
            .strip()
            .replace(" ", "_")
            .lower()
        )
        filename = f"{safe_name or 'chart'}.png"
        filepath = os.path.join(CHARTS_DIR, filename)

        fig, ax = plt.subplots(figsize=(6, 4))
        chart_type_clean = chart_type.lower().strip()

        try:
            if chart_type_clean == "bar":
                ax.bar(labels, values, color="#3B6FD6")
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                plt.xticks(rotation=30, ha="right")
            elif chart_type_clean == "line":
                ax.plot(labels, values, marker="o", color="#3B6FD6")
                ax.set_xlabel(x_label)
                ax.set_ylabel(y_label)
                plt.xticks(rotation=30, ha="right")
            elif chart_type_clean == "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%")
            else:
                plt.close(fig)
                return (
                    f"Error: unsupported chart_type '{chart_type}'. "
                    "Use 'bar', 'line', or 'pie'."
                )

            ax.set_title(title)
            fig.tight_layout()
            fig.savefig(filepath, dpi=150)
        finally:
            plt.close(fig)

        return f"Chart saved as {filename} (full path: {filepath})"