"""Allows `python -m aria.mcp` as an alternative to the `aria-mcp` console script."""

from aria.mcp.server import main

if __name__ == "__main__":
    main()
