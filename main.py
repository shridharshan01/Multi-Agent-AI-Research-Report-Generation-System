"""
Entry point. Usage:

    python main.py "Artificial Intelligence in Healthcare"

or just run `python main.py` and you'll be prompted for a topic.
"""

import os
import sys
from pathlib import Path

# ── Always resolve paths relative to this file, not the caller's cwd ─────────
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv

load_dotenv()

from compat_patches import apply_compat_patches

apply_compat_patches()

from crewai import Crew, Process

from agents import build_agents
from tasks import build_tasks
from utils.pdf_builder import build_pdf

OUTPUT_DIR = "output"
CHARTS_DIR = os.path.join(OUTPUT_DIR, "charts")


def run(topic: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CHARTS_DIR, exist_ok=True)

    researcher, verifier, analyst, writer = build_agents()
    tasks = build_tasks(researcher, verifier, analyst, writer)

    crew = Crew(
        agents=[researcher, verifier, analyst, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(inputs={"topic": topic})

    report_path = os.path.join(OUTPUT_DIR, "report.md")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report_markdown = f.read()
    else:
        # Fallback in case output_file didn't get written for some reason.
        report_markdown = str(result)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_markdown)

    chart_paths = sorted(str(p) for p in Path(CHARTS_DIR).glob("*.png"))

    pdf_path = os.path.join(OUTPUT_DIR, "report.pdf")
    build_pdf(
        topic=topic,
        markdown_text=report_markdown,
        chart_paths=chart_paths,
        output_path=pdf_path,
    )

    print(f"\nDone.\n  Markdown report: {report_path}\n  PDF report:      {pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        topic_arg = " ".join(sys.argv[1:])
    else:
        topic_arg = input("Enter a research topic: ").strip()

    if not topic_arg:
        print("No topic provided.")
        sys.exit(1)

    run(topic_arg)