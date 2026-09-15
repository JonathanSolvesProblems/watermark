import json, sys, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

URL = "https://knowledge.appstore-mcp.ring.amazon.dev/mcp"

def call(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    return d["result"]["content"][0]["text"]

mode = sys.argv[1]
arg = sys.argv[2]
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 12000
if mode == "search":
    out = json.loads(call("ring___search_docs", {"query": arg}))
    for r in out.get("results", []):
        print("=== ", r["metadata"].get("source"), "score", r.get("score"))
        print(r["content"][:limit])
        print()
else:
    print(call("ring___get_doc", {"uri": arg})[:limit])
