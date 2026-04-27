from fastmcp import FastMCP

# This is the single source of truth for the MCP server instance.
# All modules (tools, scheduler, supervisor) should import 'mcp' from here
# to use decorators like @mcp.tool() without circular dependencies.
mcp = FastMCP("Smart Task Hub")
