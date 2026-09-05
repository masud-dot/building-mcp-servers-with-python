"""A version 1 server, as thousands were written.

Runs on mcp>=1.28,<2. Every line of this file is idiomatic for
that era and at least four of them do not survive the move.
"""

from mcp.server.fastmcp import Context, FastMCP
from pydantic import BaseModel

mcp = FastMCP("bookshop")

_stock = {"9780262033848": 3, "9781491950357": 0}


class Book(BaseModel):
    isbn: str
    copies: int


@mcp.tool()
def check_stock(isbn: str) -> Book:
    """How many copies of a book are in stock."""
    return Book(isbn=isbn, copies=_stock.get(isbn, 0))


@mcp.resource("stock://all")
def all_stock() -> str:
    """Every title and its count."""
    return "\n".join(f"{k}: {v}" for k, v in _stock.items())


@mcp.prompt()
def restock_review(isbn: str) -> str:
    """Ask whether a title needs restocking."""
    return f"Should we restock {isbn}?"


if __name__ == "__main__":
    mcp.run()
