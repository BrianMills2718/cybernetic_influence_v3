#!/usr/bin/env python3
"""Fail when the public page references an asset that does not load.

The public surface is mounted behind a path prefix (/waltzman), and its asset
references are relative. A browser resolving `assets/app.js` from the base
`/waltzman` drops the last segment and asks for `/assets/app.js`, which belongs
to a different service and returns 404 -- so the stylesheet and the entire
application script silently fail and the visitor gets an unstyled page with no
working navigation. From `/waltzman/` the same reference resolves correctly.

That difference is invisible to a health check that only asks whether the page
returned 200, and invisible to an API check, because both succeed while the
page is broken. It is only visible if something resolves the page's own asset
references the way a browser would. That is what this does.

Give it the exact URL that will be shared with a reader. Exit non-zero if any
referenced asset fails, naming the resolved URL that broke.
"""

from __future__ import annotations

import argparse
import re
import sys
from urllib.parse import urljoin

import httpx

REFERENCE = re.compile(r'(?:href|src)="([^"]+)"')
SKIP_PREFIXES = ("#", "data:", "mailto:", "javascript:")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="the exact URL a reader will open")
    args = parser.parse_args()

    with httpx.Client(follow_redirects=True, timeout=30) as client:
        page = client.get(args.url)
        if page.status_code != 200:
            print(f"the page itself returned {page.status_code}: {args.url}", file=sys.stderr)
            return 1

        references = [
            ref for ref in dict.fromkeys(REFERENCE.findall(page.text))
            if not ref.startswith(SKIP_PREFIXES)
        ]
        if not references:
            print("no asset references found in the page; is this the right URL?", file=sys.stderr)
            return 1

        broken = []
        for ref in references:
            resolved = urljoin(str(page.url), ref)
            try:
                status = client.get(resolved).status_code
            except httpx.HTTPError as error:
                broken.append((ref, resolved, str(error)))
                continue
            if status != 200:
                broken.append((ref, resolved, str(status)))
            print(f"  {status}  {ref}")

    if broken:
        print(f"\n{len(broken)} referenced asset(s) do not load from {args.url}:", file=sys.stderr)
        for ref, resolved, why in broken:
            print(f"  {ref}  ->  {resolved}  ({why})", file=sys.stderr)
        print(
            "\nIf these are relative references resolving above the mount point, the URL "
            "needs its trailing slash. Share the slash form.",
            file=sys.stderr,
        )
        return 1

    print(f"\nall {len(references)} referenced assets load from {args.url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
