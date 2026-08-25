#!/bin/bash
# Wrapper to launch GitHub MCP server with gh CLI token
export GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token)"
exec npx -y @modelcontextprotocol/server-github
