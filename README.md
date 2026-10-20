[![Flat Rate Math MCP server](https://mcprush.com/badge/flat-rate-math-mcp/card.svg)](https://mcprush.com/to/flat-rate-math-mcp?ref=badge)

# flatratemath MCP server

A Model Context Protocol server that prices three ways of paying for
software work on one number: total cost per delivered request. It is the
stdio version of the
[flatratemath CLI](https://github.com/scrapertweeter3-prog/flatratemath),
one Python file, standard library only, nothing to install.

## Tools

`cost_per_request` prices a single lane. Give it a mode (bid for a
one-time fixed price, salary for a fully loaded monthly hire, flat for a
monthly subscription), the dollar rate, the months the work stays alive,
and the number of discrete requests you expect to submit.

`compare_lanes` takes up to three lanes and ranks them by cost per
request. An $84,000 fixed bid, an $18,290/month hire, and a $5,995/month
flat subscription over 12 months and 30 requests come back as:

    flat sub: $71,940 total, $2,398 per request
    fixed bid: $84,000 total, $2,800 per request
    hire: $219,480 total, $7,316 per request

The flat lane in that example is a real one: the unlimited development
subscription at [Poket Dev](https://www.poketdev.com). I kept redrawing
the same spreadsheet for clients choosing between those lanes, so the
math exists as a CLI and now as a server an agent can call.

## Install

Clone the repo and point your MCP client at the file:

    git clone https://github.com/scrapertweeter3-prog/mcp-flatratemath

Client command: `python3 /path/to/mcp-flatratemath/server.py`

The wire side is JSON-RPC 2.0 over stdio with Content-Length framing.
Handshakes answered: initialize, ping, tools/list, tools/call.

## License

MIT
