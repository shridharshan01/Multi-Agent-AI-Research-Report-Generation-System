"""
Defines the four agents in the research crew:

  1. researcher  -- searches the web and collects raw findings
  2. verifier    -- cross-checks claims and source credibility
  3. analyst     -- pulls out key statistics and turns them into charts
  4. writer      -- compiles everything into the final Markdown report
"""

from crewai import Agent
from crewai_tools import SerperDevTool

from config import get_llm
from tools.chart_tool import ChartGeneratorTool  # requires tools/__init__.py

search_tool = SerperDevTool()
chart_tool = ChartGeneratorTool()


def build_agents():
    llm = get_llm()

    researcher = Agent(
        role="Senior Research Analyst",
        goal=(
            "Search the web and collect comprehensive, current, well-sourced "
            "information about {topic}."
        ),
        backstory=(
            "You are a meticulous research analyst who knows how to dig past the "
            "first page of search results. You always note where each piece of "
            "information came from (publication name and URL) so it can be checked "
            "later, and you actively look for concrete numbers and statistics, not "
            "just qualitative claims."
        ),
        tools=[search_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    verifier = Agent(
        role="Source Verification Specialist",
        goal=(
            "Cross-check the claims and sources gathered about {topic}, run extra "
            "searches where needed, and flag anything outdated, contradicted "
            "elsewhere, or sourced from a low-credibility outlet."
        ),
        backstory=(
            "You are a fact-checker with healthy skepticism. You distinguish "
            "between primary sources, reputable journalism, and low-quality or "
            "speculative content, and you always say clearly which claims you "
            "could not verify rather than guessing."
        ),
        tools=[search_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    analyst = Agent(
        role="Data Analyst",
        goal=(
            "Extract the key statistics and trends about {topic} from the verified "
            "research, and turn the most important ones into charts."
        ),
        backstory=(
            "You think in numbers. Given a pile of verified findings, you pull out "
            "the figures that matter most, decide whether a bar, line, or pie chart "
            "fits each one best, and use the Chart Generator tool to produce the "
            "actual images."
        ),
        tools=[chart_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    writer = Agent(
        role="Report Writer",
        goal=(
            "Turn the research, verification notes, and data analysis about "
            "{topic} into a single polished, well-structured report."
        ),
        backstory=(
            "You are an experienced analyst-writer who produces reports that "
            "people actually read: clear structure, no fluff, every claim "
            "traceable to a source, and charts placed where they add the most "
            "value."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )

    return researcher, verifier, analyst, writer