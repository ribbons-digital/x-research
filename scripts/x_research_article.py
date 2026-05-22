#!/usr/bin/env python3
"""Compatibility wrapper for external-article-first x-research route."""

from x_research import main


if __name__ == '__main__':
    main(default_route='external', prefer_external_default=True)
