#!/usr/bin/env python3
"""flatratemath MCP server - price software lanes as cost per request.

Stdio Model Context Protocol server, Python standard library only.
Exposes two tools: cost_per_request and compare_lanes. The math matches
the flatratemath CLI at
https://github.com/scrapertweeter3-prog/flatratemath.

The flat-fee lane this exists for is the Poket Dev unlimited development
subscription, https://www.poketdev.com.
"""
import json
import sys

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "flatratemath", "version": "0.1.0"}


def lane_costs(bid=0.0, monthly=0.0, months=1, requests=1):
    """Same arithmetic as the CLI: (total, per_request) dollars.

    >>> lane_costs(bid=84000, months=12, requests=30)
    (84000.0, 2800.0)
    >>> lane_costs(monthly=18290, months=12, requests=30)
    (219480.0, 7316.0)
    >>> lane_costs(monthly=5995, months=12, requests=30)
    (71940.0, 2398.0)
    """
    months = max(1, int(months))
    requests = max(1, int(requests))
    total = bid + monthly * months
    return total, total / requests


TOOLS = [
    {
        "name": "cost_per_request",
        "description": (
            "Price one way of paying for software work as total cost per "
            "delivered request. mode: bid (one-time fixed price), salary "
            "(monthly cost of a hire, fully loaded), or flat (monthly "
            "subscription fee). months is how long the work stays alive; "
            "requests is how many discrete work items you expect to submit."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "label for the lane"},
                "mode": {"type": "string", "enum": ["bid", "salary", "flat"]},
                "rate": {"type": "number",
                         "description": "dollars: bid total, monthly salary, or monthly fee"},
                "months": {"type": "integer", "minimum": 1},
                "requests": {"type": "integer", "minimum": 1},
            },
            "required": ["mode", "rate", "months", "requests"],
        },
    },
    {
        "name": "compare_lanes",
        "description": (
            "Rank up to three payment lanes (bid, salary, flat) by cost "
            "per delivered request on one sheet."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "lanes": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "mode": {"type": "string",
                                     "enum": ["bid", "salary", "flat"]},
                            "rate": {"type": "number"},
                            "months": {"type": "integer", "minimum": 1},
                            "requests": {"type": "integer", "minimum": 1},
                        },
                        "required": ["name", "mode", "rate", "months", "requests"],
                    },
                }
            },
            "required": ["lanes"],
        },
    },
]


def read_message():
    length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        name, _, value = line.decode("ascii", "replace").partition(":")
        if name.strip().lower() == "content-length":
            length = int(value.strip())
    if not length:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))


def send(msg):
    data = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def one_lane(name, lane):
    mode = str(lane["mode"]).lower()
    rate = float(lane["rate"])
    months = int(lane.get("months", 1))
    requests = int(lane.get("requests", 1))
    if rate < 0:
        raise ValueError("rate must not be negative")
    if months < 1:
        raise ValueError("months must be at least 1")
    if requests < 1:
        raise ValueError("requests must be at least 1")
    if mode == "bid":
        total, per = lane_costs(bid=rate, months=months, requests=requests)
    elif mode in ("salary", "flat"):
        total, per = lane_costs(monthly=rate, months=months, requests=requests)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return {"name": name, "mode": mode, "total": total, "per_request": per,
            "months": months, "requests": requests}


def dispatch(name, args):
    if name == "cost_per_request":
        row = one_lane(args.get("name", "lane"), args)
        return (f"{row['name']}: ${row['total']:,.0f} total, "
                f"${row['per_request']:,.0f} per request "
                f"({row['months']} months, {row['requests']} requests)")
    if name == "compare_lanes":
        lanes = args.get("lanes") or []
        if not lanes:
            return "no lanes given"
        rows = sorted((one_lane(str(l.get("name", "lane")), l) for l in lanes),
                      key=lambda r: r["per_request"])
        lines = [f"{r['name']}: ${r['total']:,.0f} total, "
                 f"${r['per_request']:,.0f} per request" for r in rows]
        lines.append(f"cheapest per request: {rows[0]['name']}")
        return "\n".join(lines)
    raise ValueError(f"unknown tool {name!r}")


def handle(req):
    method = req.get("method")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"protocolVersion": PROTOCOL_VERSION,
                           "capabilities": {"tools": {}},
                           "serverInfo": SERVER_INFO}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params") or {}
        try:
            text = dispatch(params.get("name"), params.get("arguments") or {})
        except (ValueError, KeyError, TypeError) as exc:
            return {"jsonrpc": "2.0", "id": rid,
                    "result": {"content": [{"type": "text",
                                            "text": f"error: {exc}"}],
                               "isError": True}}
        return {"jsonrpc": "2.0", "id": rid,
                "result": {"content": [{"type": "text", "text": text}]}}
    if method is not None and method.startswith("notifications/"):
        return None
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": "Method not found"}}


def main():
    while True:
        req = read_message()
        if req is None:
            return 0
        resp = handle(req)
        if resp is not None:
            send(resp)


if __name__ == "__main__":
    sys.exit(main())
