"""Web search is a server-side Claude tool: Anthropic runs the search and
returns results as content blocks in the same response — no client-side
execution code needed here, unlike remember/run_python."""

WEB_SEARCH_TOOL = {
    "type": "web_search_20260209",
    "name": "web_search",
}
