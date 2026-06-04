import json
import os
import sys
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


TOOLS = [
    {
        "name": "list_assets",
        "description": "Return active financial assets available in the warehouse.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "as_of": {
                    "type": "string",
                    "description": "Optional ISO datetime for temporal lookup.",
                }
            },
        },
    },
    {
        "name": "get_asset_details",
        "description": "Return details for one financial asset.",
        "inputSchema": {
            "type": "object",
            "required": ["asset_id"],
            "properties": {
                "asset_id": {"type": "string"},
                "as_of": {"type": "string"},
            },
        },
    },
    {
        "name": "list_sources",
        "description": "Return financial data providers stored in the warehouse.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_time_series",
        "description": "Return time-series observations for an asset and data source.",
        "inputSchema": {
            "type": "object",
            "required": ["asset_id", "source_id"],
            "properties": {
                "asset_id": {"type": "string"},
                "source_id": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
        },
    },
    {
        "name": "summarize_series",
        "description": "Compute count/min/max/average for a numeric indicator.",
        "inputSchema": {
            "type": "object",
            "required": ["asset_id", "source_id"],
            "properties": {
                "asset_id": {"type": "string"},
                "source_id": {"type": "string"},
                "indicator": {"type": "string", "default": "close"},
            },
        },
    },
    {
        "name": "risk_signal",
        "description": "Compute a simple volatility-based risk signal.",
        "inputSchema": {
            "type": "object",
            "required": ["asset_id", "source_id"],
            "properties": {
                "asset_id": {"type": "string"},
                "source_id": {"type": "string"},
                "indicator": {"type": "string", "default": "close"},
            },
        },
    },
]


def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    query = f"?{urlencode(params or {})}" if params else ""
    request = Request(f"{API_BASE_URL}{path}{query}", headers={"Accept": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def call_tool(name: str, args: dict[str, Any]) -> Any:
    args = args or {}
    if name == "list_assets":
        params = {"as_of": args["as_of"]} if args.get("as_of") else None
        return api_get("/assets", params)
    if name == "get_asset_details":
        params = {"as_of": args["as_of"]} if args.get("as_of") else None
        return api_get(f"/assets/{args['asset_id']}", params)
    if name == "list_sources":
        return api_get("/sources")
    if name == "get_time_series":
        params = {
            key: value
            for key, value in {
                "start": args.get("start"),
                "end": args.get("end"),
                "limit": args.get("limit", 50),
            }.items()
            if value is not None
        }
        return api_get(f"/timeseries/{args['asset_id']}/{args['source_id']}", params)
    if name == "summarize_series":
        return api_get(
            "/analytics/summary",
            {
                "asset_id": args["asset_id"],
                "source_id": args["source_id"],
                "indicator": args.get("indicator", "close"),
            },
        )
    if name == "risk_signal":
        return api_get(
            "/analytics/risk",
            {
                "asset_id": args["asset_id"],
                "source_id": args["source_id"],
                "indicator": args.get("indicator", "close"),
            },
        )
    raise ValueError(f"Unknown tool: {name}")


def respond(message_id: Any, result: Any = None, error: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": message_id}
    if error:
        payload["error"] = error
    else:
        payload["result"] = result
    print(json.dumps(payload), flush=True)


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            method = message.get("method")
            message_id = message.get("id")

            if method == "initialize":
                respond(
                    message_id,
                    {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "acme-finance-dw", "version": "0.1.0"},
                    },
                )
            elif method == "tools/list":
                respond(message_id, {"tools": TOOLS})
            elif method == "tools/call":
                params = message.get("params", {})
                output = call_tool(params["name"], params.get("arguments", {}))
                respond(
                    message_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(output, indent=2, default=str),
                            }
                        ]
                    },
                )
            elif method == "notifications/initialized":
                continue
            else:
                respond(message_id, error={"code": -32601, "message": f"Unknown method: {method}"})
        except Exception as exc:
            respond(
                message.get("id") if "message" in locals() else None,
                error={"code": -32000, "message": str(exc)},
            )


if __name__ == "__main__":
    main()
