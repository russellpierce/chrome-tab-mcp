#!/usr/bin/env python3
"""
Test script to verify FastAPI server and OpenAPI spec generation
"""

import json
import sys

print("Testing FastAPI server setup...")

try:
    # Import the FastAPI app
    from chrome_tab_http_server import app
    print("✓ FastAPI app imported successfully")

    # Get the OpenAPI schema
    openapi_schema = app.openapi()
    print("✓ OpenAPI schema generated")

    # Verify basic structure
    assert "openapi" in openapi_schema, "Missing 'openapi' field"
    assert openapi_schema["openapi"].startswith("3."), f"Wrong OpenAPI version: {openapi_schema['openapi']}"
    print(f"✓ OpenAPI version: {openapi_schema['openapi']}")

    assert "info" in openapi_schema, "Missing 'info' field"
    assert openapi_schema["info"]["title"] == "Chrome Tab Reader API"
    print(f"✓ API title: {openapi_schema['info']['title']}")

    assert "paths" in openapi_schema, "Missing 'paths' field"
    paths = openapi_schema["paths"]
    print(f"✓ Found {len(paths)} paths")

    # Check for expected endpoints
    expected_endpoints = [
        "/api/extract",
        "/api/navigate_and_extract",
        "/api/current_tab",
        "/api/health"
    ]

    for endpoint in expected_endpoints:
        if endpoint in paths:
            methods = list(paths[endpoint].keys())
            print(f"  ✓ {endpoint} ({', '.join(m.upper() for m in methods)})")
        else:
            print(f"  ✗ Missing endpoint: {endpoint}")
            sys.exit(1)

    # Check for security schemes
    assert "components" in openapi_schema, "Missing 'components' field"
    assert "securitySchemes" in openapi_schema["components"], "Missing 'securitySchemes'"
    assert "HTTPBearer" in openapi_schema["components"]["securitySchemes"], "Missing HTTPBearer scheme"
    print("✓ HTTPBearer security scheme defined")

    # Check for tags (optional at root level, defined per endpoint)
    if "tags" in openapi_schema:
        tag_names = [tag["name"] for tag in openapi_schema["tags"]]
        print(f"✓ Tags defined: {', '.join(tag_names)}")
    else:
        # Collect tags from endpoints
        endpoint_tags = set()
        for path_data in paths.values():
            for operation in path_data.values():
                if isinstance(operation, dict) and "tags" in operation:
                    endpoint_tags.update(operation["tags"])
        if endpoint_tags:
            print(f"✓ Endpoint tags found: {', '.join(sorted(endpoint_tags))}")

    # Pretty print a sample endpoint
    print("\n" + "="*60)
    print("Sample endpoint - POST /api/extract:")
    print("="*60)
    extract_endpoint = paths.get("/api/extract", {}).get("post", {})

    # Show request body
    if "requestBody" in extract_endpoint:
        print("\nRequest Body:")
        request_schema = extract_endpoint["requestBody"]["content"]["application/json"]["schema"]
        print(json.dumps(request_schema, indent=2))

    # Show response
    if "responses" in extract_endpoint and "200" in extract_endpoint["responses"]:
        print("\n200 Response:")
        response_schema = extract_endpoint["responses"]["200"]["content"]["application/json"]["schema"]
        print(json.dumps(response_schema, indent=2))

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    print(f"\nFull OpenAPI spec has {len(json.dumps(openapi_schema))} characters")
    print("\nTo view the interactive docs, start the server with:")
    print("  python chrome_tab_http_server.py")
    print("\nThen visit:")
    print("  http://localhost:8888/docs (Swagger UI)")
    print("  http://localhost:8888/redoc (ReDoc)")
    print("  http://localhost:8888/openapi.json (Raw OpenAPI spec)")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
