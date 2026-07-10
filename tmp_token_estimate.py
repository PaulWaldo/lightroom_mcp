"""
One-off script to estimate the token cost of the Lightroom MCP server's
tool definitions (name + description + JSON parameter schema) as they
would be transmitted to an LLM client at session start.

Uses FastMCP's own tool registry (get_tools) to obtain the exact
name/description/inputSchema that the MCP protocol serializes, then
tokenizes the resulting JSON with tiktoken (cl100k_base, a reasonable
stand-in encoding for modern LLM tokenizers).
"""
import asyncio
import json

import tiktoken

from mcp_server.main import main_server


async def main():
    tools = await main_server.get_tools()

    enc = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0
    total_chars = 0
    per_tool = []

    for name, tool in tools.items():
        # Build the JSON structure approximating what MCP sends over the wire
        mcp_tool = tool.to_mcp_tool(name=name)
        payload = {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "inputSchema": mcp_tool.inputSchema,
        }
        text = json.dumps(payload, ensure_ascii=False)
        n_chars = len(text)
        n_tokens = len(enc.encode(text))
        total_chars += n_chars
        total_tokens += n_tokens
        per_tool.append((name, n_chars, n_tokens))

    print(f"Total tools: {len(tools)}")
    print(f"Total characters: {total_chars:,}")
    print(f"Total tokens (cl100k_base): {total_tokens:,}")
    print(f"Avg chars/token: {total_chars/total_tokens:.2f}")
    print()

    per_tool.sort(key=lambda x: -x[2])
    print("Top 15 most expensive tools (by tokens):")
    for name, c, t in per_tool[:15]:
        print(f"  {t:6,} tok  {c:6,} chars  {name}")

    print()
    print("Bottom 5 cheapest tools:")
    for name, c, t in per_tool[-5:]:
        print(f"  {t:6,} tok  {c:6,} chars  {name}")

    # Breakdown by prefix/category
    from collections import defaultdict
    cat_tokens = defaultdict(int)
    cat_count = defaultdict(int)
    for name, c, t in per_tool:
        prefix = name.split("_")[0]
        cat_tokens[prefix] += t
        cat_count[prefix] += 1

    print()
    print("Breakdown by category prefix:")
    for prefix, tok in sorted(cat_tokens.items(), key=lambda x: -x[1]):
        print(f"  {prefix:12s} {cat_count[prefix]:4d} tools  {tok:6,} tokens")


if __name__ == "__main__":
    asyncio.run(main())
