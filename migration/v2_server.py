"""The same server, migrated to mcp 2.x.

Line for line the same shape. Every change is mechanical, and
the diff against v1_server.py is the whole of this chapter's
first half.
"""

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

server = MCPServer(name="bookshop")

_stock = {"9780262033848": 3, "9781491950357": 0}


class Book(BaseModel):
    isbn: str
    copies: int


@server.tool()
def check_stock(isbn: str) -> Book:
    """How many copies of a book are in stock."""
    return Book(isbn=isbn, copies=_stock.get(isbn, 0))


@server.resource("stock://all")
def all_stock() -> str:
    """Every title and its count."""
    return "\n".join(f"{k}: {v}" for k, v in _stock.items())


@server.prompt()
def restock_review(isbn: str) -> str:
    """Ask whether a title needs restocking."""
    return f"Should we restock {isbn}?"


if __name__ == "__main__":
    server.run(transport="stdio")
