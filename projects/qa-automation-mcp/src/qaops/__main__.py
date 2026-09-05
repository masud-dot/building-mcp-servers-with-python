"""Run the server. Chapter 25 adds the other transports."""

from qaops.server import server


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
