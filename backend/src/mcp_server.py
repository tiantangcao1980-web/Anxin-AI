"""
AI Legal Agent MCP Server
-------------------------
This server exposes AI Legal Agent capabilities via the Model Context Protocol (MCP).
It allows other AI agents (like Claude Desktop) to interact with the legal system.
"""

import asyncio
import os
import sys
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

from src.core.database import async_session_maker, init_db
from src.services.case_service import CaseService
from src.services.knowledge_service import KnowledgeService
from src.core.config import settings

# Create an MCP server
mcp = FastMCP("AI Legal Agent")

# Helper to get DB session
async def get_session():
    async with async_session_maker() as session:
        yield session

# Helper to execute service calls with DB session
async def with_service(service_class, callback):
    async with async_session_maker() as session:
        service = service_class(session)
        return await callback(service)

# --- Resources ---

@mcp.resource("legal://cases/list")
async def list_cases_resource() -> str:
    """List recent legal cases as a resource."""
    async def _list(service: CaseService):
        cases, _ = await service.list_cases(page_size=10)
        return "\n".join([f"- [{c.case_number}] {c.title} ({c.status.value})" for c in cases])
    
    return await with_service(CaseService, _list)

@mcp.resource("legal://knowledge/stats")
async def knowledge_stats_resource() -> str:
    """Get knowledge base statistics."""
    async def _stats(service: KnowledgeService):
        kbs, _ = await service.list_knowledge_bases()
        stats = []
        for kb in kbs:
            stats.append(f"- {kb.name}: {kb.doc_count} docs (Type: {kb.knowledge_type.value})")
        return "\n".join(stats) if stats else "No knowledge bases found."

    return await with_service(KnowledgeService, _stats)

# --- Tools ---

@mcp.tool()
async def search_knowledge_base(query: str, kb_id: Optional[str] = None) -> str:
    """
    Search the legal knowledge base for relevant information.
    
    Args:
        query: The search query (e.g., "contract breach penalties")
        kb_id: Optional ID of specific knowledge base to search
    """
    async def _search(service: KnowledgeService):
        results = await service.semantic_search_simple(query, kb_id=kb_id, top_k=5)
        formatted_results = []
        for res in results:
            formatted_results.append(
                f"--- Document: {res.get('title', 'Untitled')} ---\n"
                f"Content: {res.get('content', '')[:500]}...\n"
                f"Source: {res.get('source', 'Unknown')}\n"
            )
        return "\n".join(formatted_results) if formatted_results else "No matching documents found."

    return await with_service(KnowledgeService, _search)

@mcp.tool()
async def analyze_legal_case(case_id: str) -> str:
    """
    Trigger AI analysis for a specific legal case.
    
    Args:
        case_id: The UUID of the case to analyze
    """
    async def _analyze(service: CaseService):
        # Use default admin ID for system-triggered analysis
        admin_id = "00000000-0000-0000-0000-000000000001"
        result = await service.analyze_case(case_id, user_id=admin_id)
        final_result = result.get("final_result", {})
        
        # Format the output
        output = [f"Analysis for Case {case_id}:"]
        if isinstance(final_result, dict):
            for k, v in final_result.items():
                output.append(f"\n## {k}\n{v}")
        else:
            output.append(str(final_result))
            
        return "\n".join(output)

    return await with_service(CaseService, _analyze)

@mcp.tool()
async def get_case_details(case_id: str) -> str:
    """
    Get detailed information about a specific legal case.
    
    Args:
        case_id: The UUID of the case
    """
    async def _get(service: CaseService):
        case = await service.get_case(case_id)
        if not case:
            return f"Case {case_id} not found."
        
        details = [
            f"Case Number: {case.case_number}",
            f"Title: {case.title}",
            f"Type: {case.case_type.value}",
            f"Status: {case.status.value}",
            f"Priority: {case.priority.value}",
            f"Description: {case.description or 'N/A'}",
            f"Created At: {case.created_at}",
            f"Deadline: {case.deadline or 'None'}",
        ]
        
        if case.ai_analysis:
            details.append("\n--- AI Analysis Summary ---")
            # Extract summary if available, or just existence
            details.append("AI Analysis is available.")
            
        return "\n".join(details)

    return await with_service(CaseService, _get)

@mcp.tool()
async def list_pending_cases() -> str:
    """List all pending legal cases that require attention."""
    async def _list(service: CaseService):
        cases, _ = await service.list_cases(status="pending", page_size=20)
        if not cases:
            return "No pending cases found."
        
        lines = ["Pending Cases:"]
        for c in cases:
            lines.append(f"- ID: {c.id} | {c.case_number}: {c.title} (Priority: {c.priority.value})")
        return "\n".join(lines)

    return await with_service(CaseService, _list)

if __name__ == "__main__":
    # Ensure we are in the right directory for imports to work if running directly
    # But usually assume python path is set correctly
    
    # Run the server
    mcp.run()
