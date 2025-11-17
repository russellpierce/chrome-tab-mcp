#!/usr/bin/env python3
"""
Test script to verify OpenAPI spec generation
"""

import json
import sys

# Test import and spec generation
print("Testing OpenAPI spec generation...")

try:
    # Import the module
    import chrome_tab_http_server
    print("✓ Module imported successfully")

    # Check if apispec is available
    if not chrome_tab_http_server.APISPEC_AVAILABLE:
        print("✗ apispec not available")
        sys.exit(1)
    print("✓ apispec is available")

    # Generate the spec
    spec = chrome_tab_http_server.build_openapi_spec()
    print("✓ OpenAPI spec generated")

    # Verify basic structure
    assert "openapi" in spec, "Missing 'openapi' field"
    assert spec["openapi"] == "3.0.3", f"Wrong OpenAPI version: {spec['openapi']}"
    print(f"✓ OpenAPI version: {spec['openapi']}")

    assert "info" in spec, "Missing 'info' field"
    assert "title" in spec["info"], "Missing 'title' in info"
    assert spec["info"]["title"] == "Chrome Tab Reader API"
    print(f"✓ API title: {spec['info']['title']}")

    assert "paths" in spec, "Missing 'paths' field"
    paths = spec["paths"]
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
            print(f"  ✓ {endpoint}")
        else:
            print(f"  ✗ Missing endpoint: {endpoint}")
            sys.exit(1)

    # Check for security schemes
    assert "components" in spec, "Missing 'components' field"
    assert "securitySchemes" in spec["components"], "Missing 'securitySchemes'"
    assert "BearerAuth" in spec["components"]["securitySchemes"], "Missing BearerAuth scheme"
    print("✓ BearerAuth security scheme defined")

    # Pretty print a sample
    print("\n" + "="*60)
    print("Sample endpoint - /api/health:")
    print("="*60)
    health_endpoint = paths.get("/api/health", {})
    print(json.dumps(health_endpoint, indent=2))

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    print(f"\nFull spec has {len(json.dumps(spec))} characters")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
