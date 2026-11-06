"""Allow running ostensible with python -m ostensible."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
