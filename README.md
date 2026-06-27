# Multi-Agent Research & Report Generation System (CrewAI)

A four-agent CrewAI crew that researches any topic end-to-end and produces a
polished PDF report with embedded charts.

```
Research Agent --> Verification Agent --> Data Analyst Agent --> Report Writer Agent
 (web search)      (cross-checks &         (extracts stats,        (compiles everything
                     credibility)            builds charts)          into Markdown + PDF)
```

## What it does

Give it a topic -- e.g. `Artificial Intelligence in Healthcare`,
`Climate Change in India`, `Electric Vehicles Market Analysis`,
`Cricket World Cup 2027 Predictions` -- and it will:

1. **Search the web** for current, relevant information (Serper/Google).
2. **Collect** findings with their source name and URL.
3. **Verify sources**, flagging anything unverified or low-credibility.
4. **Summarize findings** and pull out the key statistics.
5. **Create charts** from those statistics (bar / line / pie, via matplotlib).
6. **Generate a final PDF report** (cover page, sections, embedded charts,
   numbered source list) at `output/report.pdf`, plus the raw Markdown at
   `output/report.md`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set SERPER_API_KEY, pick LLM_PROVIDER, and set the matching key
```

You need a free [Serper.dev](https://serper.dev) API key for web search no
matter which LLM provider you choose.

### Choosing an LLM provider

Set `LLM_PROVIDER` in `.env` to one of:

| Provider | Needs | Default model |
|---|---|---|
| `gemini` | `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey) | `gemini/gemini-2.0-flash` |
| `groq`   | `GROQ_API_KEY` from [Groq Console](https://console.groq.com/keys) | `groq/llama-3.3-70b-versatile` |
| `ollama` | A local [Ollama](https://ollama.ai) server running (`ollama pull llama3.1`) | `ollama/llama3.1` |

You can override the model via `MODEL_NAME` in `.env` if you want a different
size/version (e.g. `groq/llama-3.1-8b-instant` for a faster, cheaper run).

## Run it

```bash
python main.py "Artificial Intelligence in Healthcare"
```

or run it with no arguments and you'll be prompted for a topic.

Output appears in `output/`:
- `output/report.md` -- raw Markdown report
- `output/report.pdf` -- final formatted PDF
- `output/charts/*.png` -- the generated chart images

## Project structure

```
.
├── main.py              # entry point: runs the crew, then builds the PDF
├── config.py            # picks the LLM (gemini / groq / ollama) from .env
├── agents.py             # the 4 agents
├── tasks.py              # the 4 sequential tasks
├── tools/
│   └── chart_tool.py     # custom tool: data -> saved chart PNG
├── utils/
│   └── pdf_builder.py    # Markdown + charts -> polished PDF (no LLM calls)
├── requirements.txt
└── .env.example
```

## Customizing

- **Swap the search tool**: replace `SerperDevTool()` in `agents.py` with
  any other tool from `crewai_tools` (e.g. an alternative search API).
- **Add an agent**: e.g. a "Competitor Comparison Agent" -- define it in
  `agents.py`, add a matching `Task` with `context=[...]` pointing at
  whichever earlier tasks it needs, and append it to the list returned by
  `build_tasks()`.
- **Change chart style**: edit `tools/chart_tool.py`'s matplotlib calls
  (colors, figure size, chart types).
- **Smaller/cheaper/local model**: change `LLM_PROVIDER`/`MODEL_NAME` in
  `.env` -- no code changes needed.

## Known upstream bug (already patched in this project)

As of mid-2026, current CrewAI releases (1.14.4+) have a bug where an
internal prompt-caching helper stamps a `cache_breakpoint` field onto every
message regardless of LLM provider. Only the Anthropic adapter knows to
strip it -- Groq (and apparently Gemini/Ollama too) reject the request:

```
litellm.BadRequestError: GroqException - {"error": {"message":
"'messages.0': for 'role:system' the following must be satisfied
[('messages.0': property 'cache_breakpoint' is unsupported)]", ...}}
```

Tracked upstream at <https://github.com/crewAIInc/crewAI/issues/5886>.
`compat_patches.py` neutralizes the helper at startup (it's imported and
called at the top of `main.py`), so you shouldn't hit this. If a future
`pip install -r requirements.txt` pulls a crewai release that's already
fixed this, the patch just becomes a harmless no-op -- safe to delete
`compat_patches.py` and its two lines in `main.py` once you've confirmed
the upstream issue is closed.

## Notes on reliability

- This uses `Process.sequential` rather than a hierarchical "manager" crew,
  since sequential execution is more predictable across different model
  sizes (including smaller Groq/Ollama models).
- The PDF builder includes a fallback: if the Report Writer's Markdown
  doesn't reference a generated chart by its exact filename, that chart is
  still appended at the end of the PDF under "Additional Charts" so nothing
  generated gets silently dropped.
