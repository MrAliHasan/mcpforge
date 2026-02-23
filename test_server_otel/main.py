"""
MCP-Maker Server
Source: sqlite

This is your main server file. It is safe to edit!
`mcp-maker init` will NOT overwrite this file if it already exists.

You can add your own custom tools here, and they will be served alongside
the auto-generated tools from `_autogen_main`.

Run with: mcp-maker serve --file main.py
Or directly: python main.py
"""

from _autogen_main import mcp

# ─── Add Custom Tools Here ───
#
# @mcp.tool()
# def my_custom_tool(name: str) -> str:
#     """A custom tool that does something cool."""
#     return f"Hello, {name}!"
#
# ─── End Custom Tools ───

if __name__ == "__main__":
    mcp.run()