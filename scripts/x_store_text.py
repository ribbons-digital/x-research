#!/usr/bin/env python3
"""Compatibility wrapper for pasted-text x-research route."""

from x_research import main


if __name__ == '__main__':
    main(default_route='text', force_store=True)
