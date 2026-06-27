"""
Defines the four tasks the crew runs, in sequential order:

  research -> verification -> analysis -> report
"""

import os
from pathlib import Path

from crewai import Task

# Resolve output path relative to this file so it works regardless of cwd.
_PROJECT_ROOT = Path(__file__).parent
_OUTPUT_FILE = str(_PROJECT_ROOT / "output" / "report.md")


def build_tasks(researcher, verifier, analyst, writer):
    research_task = Task(
        description=(
            "Research the topic '{topic}' thoroughly using web search. Find at "
            "least 6-8 distinct, credible sources (news, official statistics, "
            "reputable publications, recent reports). For each finding, record: "
            "the claim/fact, the source name, and the source URL. Prioritize "
            "information from the last 1-2 years where relevant. Actively look "
            "for numeric data (statistics, percentages, market sizes, dates, "
            "counts, scores) since these will be turned into charts later."
        ),
        expected_output=(
            "A structured list of findings. Each finding includes the fact, the "
            "source name, the source URL, and a one-sentence credibility note. "
            "Followed by a separate sub-list of every numeric data point found, "
            "with enough context to plot it (what the number represents, its "
            "label, and its unit)."
        ),
        agent=researcher,
    )

    verification_task = Task(
        description=(
            "Review every finding produced by the research task on '{topic}'. "
            "For each one: confirm it with an independent search if you are not "
            "already confident it's accurate, check whether other sources agree "
            "or contradict it, and flag claims that could not be verified or that "
            "come from a low-credibility source. Do not delete unverifiable "
            "claims -- mark them clearly instead."
        ),
        expected_output=(
            "The same list of findings, each tagged as Verified, Partially "
            "Verified, or Unverified, with a short justification for the tag and "
            "any corrections needed. End with a short paragraph summarizing "
            "overall source quality for this topic."
        ),
        agent=verifier,
        context=[research_task],
    )

    analysis_task = Task(
        description=(
            "Using the verified findings about '{topic}', identify the most "
            "important numeric data points (at least 2, ideally 3-4) and use the "
            "Chart Generator tool to create one chart per data point -- choose "
            "bar, line, or pie depending on what fits best. Then write a short "
            "narrative analysis explaining what the data shows and why it matters."
        ),
        expected_output=(
            "A written analysis of the key statistics and trends for '{topic}', "
            "explicitly naming the exact saved filename returned by the Chart "
            "Generator tool for each chart you created (e.g. 'market_growth.png'), "
            "plus a narrative explanation of what each chart shows."
        ),
        agent=analyst,
        context=[verification_task],
    )

    report_task = Task(
        description=(
            "Write the final report on '{topic}' in clean Markdown. Combine the "
            "verified research, the verification notes, and the data analysis "
            "into one cohesive document with these sections, in this order: "
            "Executive Summary; Key Findings; Data & Statistics (embed each chart "
            "using standard Markdown image syntax, e.g. "
            "![Market Growth](charts/market_growth.png), using the exact "
            "filenames from the analysis task); Source Verification Notes; "
            "Conclusion and Outlook; Sources (a numbered list of every source URL "
            "used, with the source name). Do not wrap the whole document in a "
            "code block."
        ),
        expected_output=(
            "A complete Markdown report with the sections listed above, roughly "
            "800-1500 words, with charts embedded via Markdown image syntax and a "
            "numbered source list at the end."
        ),
        agent=writer,
        context=[research_task, verification_task, analysis_task],
        output_file=_OUTPUT_FILE,
    )

    return [research_task, verification_task, analysis_task, report_task]