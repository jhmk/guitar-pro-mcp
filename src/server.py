"""
Guitar Pro MCP Server v2.2
"""

import logging
from mcp.server.fastmcp import FastMCP
from .tools import setup_tools

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting Guitar Pro MCP Server v2.2...")
    
    mcp = FastMCP("Guitar Pro v2.2")
    setup_tools(mcp)
    
    logger.info("Server ready!")
    mcp.run()


if __name__ == "__main__":
    main()
