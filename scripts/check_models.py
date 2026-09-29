from __future__ import annotations

import json
import urllib.request

URL = "https://api.xn--e1aikcel5c5a.online/v1/models"


def main() -> None:
    with urllib.request.urlopen(URL, timeout=15) as response:
        payload = json.load(response)
    ids = [item["id"] for item in payload.get("data", []) if item.get("id")]
    print("\n".join(ids))


if __name__ == "__main__":
    main()
