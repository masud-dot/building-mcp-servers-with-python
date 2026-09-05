"""Run the server. The transport is chosen on the command line."""

from productivity import transport
from productivity.server import server


def main() -> None:
    transport.serve(server, transport.parse())


if __name__ == "__main__":
    main()
