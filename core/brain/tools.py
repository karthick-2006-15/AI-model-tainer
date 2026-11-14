"""
Dynamic Tool Discovery & Execution Registry
Provides the @jarvis_tool decorator and automatic JSON Schema generation for LLMs.
"""

import inspect
import functools
import json
import os
import subprocess
import logging
from typing import Callable, Dict, Any, List, Optional
from modules.automation.system import SystemMonitor

logger = logging.getLogger("jarvis.brain.tools")


class ToolMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        permission_level: int,
        parameters_schema: Dict[str, Any],
        func: Callable
    ):
        self.name = name
        self.description = description
        self.permission_level = permission_level
        self.parameters_schema = parameters_schema
        self.func = func

    def to_openai_schema(self) -> Dict[str, Any]:
        """Converts to standard OpenAI/Ollama function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema
            }
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permission_level: int = 1
    ):
        """Decorator to register a function as a JARVIS tool."""
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = description or (func.__doc__ or "").strip()

            # Inspect function parameters to construct JSON schema
            sig = inspect.signature(func)
            properties: Dict[str, Any] = {}
            required: List[str] = []

            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue

                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list or getattr(param.annotation, "__origin__", None) == list:
                    param_type = "array"

                properties[param_name] = {
                    "type": param_type,
                    "description": f"Argument for {param_name}"
                }

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            parameters_schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }

            metadata = ToolMetadata(
                name=tool_name,
                description=tool_desc,
                permission_level=permission_level,
                parameters_schema=parameters_schema,
                func=func
            )
            self._tools[tool_name] = metadata

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_tool(self, name: str) -> Optional[ToolMetadata]:
        return self._tools.get(name)

    def get_all_tools(self) -> List[ToolMetadata]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a registered tool with exception handling and structured output."""
        metadata = self.get_tool(tool_name)
        if not metadata:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry."
            }

        try:
            func = metadata.func
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)

            return {
                "success": True,
                "result": result,
                "tool_name": tool_name
            }
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }


# Global tool registry
tool_registry = ToolRegistry()
jarvis_tool = tool_registry.register


# =====================================================================
# Built-in Core OS & Utility Tools
# =====================================================================

@jarvis_tool(name="get_system_telemetry", description="Get live CPU, RAM, disk, and battery hardware metrics.", permission_level=1)
def tool_get_system_telemetry() -> Dict[str, Any]:
    return SystemMonitor.get_hardware_metrics()


@jarvis_tool(name="search_workspace_files", description="Search for files by keyword or extension in the active workspace.", permission_level=1)
def tool_search_workspace_files(keyword: str, extension: str = "") -> List[str]:
    matches = []
    root_dir = os.getcwd()
    for root, _, files in os.walk(root_dir):
        if any(ign in root for ign in [".git", "node_modules", ".venv", "__pycache__"]):
            continue
        for file in files:
            if keyword.lower() in file.lower():
                if not extension or file.endswith(extension):
                    matches.append(os.path.relpath(os.path.join(root, file), root_dir))
            if len(matches) >= 20:
                break
    return matches


@jarvis_tool(name="read_file_content", description="Read the contents of a local file in the workspace.", permission_level=1)
def tool_read_file_content(file_path: str, max_lines: int = 100) -> str:
    norm_path = os.path.normpath(file_path)
    if not os.path.exists(norm_path):
        return f"File '{file_path}' does not exist."
    try:
        with open(norm_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline() for _ in range(max_lines)]
            return "".join(lines)
    except Exception as e:
        return f"Could not read file: {e}"


@jarvis_tool(name="open_application", description="Launch an authorized application or website by name.", permission_level=2)
def tool_open_application(app_name: str) -> str:
    from modules.automation.apps import ApplicationManager
    res = ApplicationManager.launch(app_name)
    if res.get("success"):
        return res.get("message", f"Application '{app_name}' launched successfully.")
    return f"Failed to launch '{app_name}': {res.get('error', 'unknown error')}"


@jarvis_tool(name="execute_shell_command", description="Run an approved PowerShell or terminal command.", permission_level=3)
def tool_execute_shell_command(command: str) -> Dict[str, Any]:
    from modules.automation.shell import shell_sandbox
    return shell_sandbox.execute_command(command)


@jarvis_tool(name="organize_directory", description="Sort and organize cluttered files in a folder into categorized subfolders.", permission_level=2)
def tool_organize_directory(folder_path: str) -> Dict[str, Any]:
    from modules.automation.file_ops import FileOperationsManager
    return FileOperationsManager.organize_directory(folder_path)


@jarvis_tool(name="create_folder", description="Create a new directory in an authorized location.", permission_level=2)
def tool_create_folder(folder_path: str) -> Dict[str, Any]:
    from modules.automation.file_ops import FileOperationsManager
    return FileOperationsManager.create_directory(folder_path)


@jarvis_tool(name="take_desktop_screenshot", description="Capture a screenshot of the primary Windows screen.", permission_level=1)
def tool_take_desktop_screenshot(output_path: str = "screenshot.png") -> Dict[str, Any]:
    from modules.automation.gui import gui_controller
    return gui_controller.take_screenshot(output_path)


@jarvis_tool(name="semantic_document_search", description="Search document contents and find relevant passages using semantic similarity.", permission_level=1)
def tool_semantic_document_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    from modules.files.search import file_search_engine
    return file_search_engine.search_documents(query=query, limit=limit)


@jarvis_tool(name="find_duplicate_files", description="Identify duplicate files across indexed directories using SHA-256 hashes.", permission_level=1)
def tool_find_duplicate_files() -> List[Dict[str, Any]]:
    from modules.files.indexer import file_indexer
    return file_indexer.find_duplicate_files()


@jarvis_tool(name="parse_and_summarize_file", description="Extract text, structure, and summary from a local PDF, Word, Excel, or code document.", permission_level=1)
def tool_parse_and_summarize_file(file_path: str) -> Dict[str, Any]:
    from modules.files.parsers import DocumentParser
    return DocumentParser.parse_file(file_path)


@jarvis_tool(name="web_search", description="Conduct a privacy-preserving search on the web for real-time information.", permission_level=1)
async def tool_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    from modules.research.search import web_search_client
    return await web_search_client.search(query=query, max_results=max_results)


@jarvis_tool(name="scrape_web_page", description="Fetch, clean, and extract readable text content from a web page URL.", permission_level=1)
async def tool_scrape_web_page(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    from modules.research.scraper import web_scraper
    return await web_scraper.scrape_url(url=url, max_chars=max_chars)


@jarvis_tool(name="conduct_research_report", description="Autonomously research a topic across multiple web sources and generate a factual synthesis report with citations.", permission_level=1)
async def tool_conduct_research_report(topic: str, max_sources: int = 3) -> Dict[str, Any]:
    from modules.research.synthesizer import research_synthesizer
    return await research_synthesizer.conduct_research(topic=topic, max_sources=max_sources)


@jarvis_tool(name="create_goal_plan", description="Decompose a complex multi-step objective into a directed execution plan graph.", permission_level=1)
async def tool_create_goal_plan(goal: str) -> Dict[str, Any]:
    from core.planning.planner import goal_planner
    dag = await goal_planner.create_plan(goal)
    return dag.model_dump()


@jarvis_tool(name="execute_goal_plan", description="Execute an autonomous multi-step plan for a user goal and verify all results.", permission_level=2)
async def tool_execute_goal_plan(goal: str) -> Dict[str, Any]:
    from core.planning.planner import goal_planner
    from core.planning.executor import dag_executor
    dag = await goal_planner.create_plan(goal)
    completed = await dag_executor.execute_plan(dag)
    return completed.model_dump()


@jarvis_tool(name="explain_screen", description="Capture the desktop screen and explain visible errors, active windows, or user interface state.", permission_level=1)
async def tool_explain_screen(focus_area: str = "Full Screen") -> Dict[str, Any]:
    from modules.vision.analyzer import vision_engine
    return await vision_engine.explain_screen(focus_area=focus_area)


@jarvis_tool(name="analyze_image_file", description="Analyze a technical image, flowchart, or diagram from a file path.", permission_level=1)
async def tool_analyze_image_file(image_path: str, query: str = "Explain this image") -> Dict[str, Any]:
    from modules.vision.analyzer import vision_engine
    return await vision_engine.analyze_image_file(image_path=image_path, query=query)


@jarvis_tool(name="get_daily_briefing", description="Generate a proactive executive morning briefing with hardware health, active objectives, and speech output.", permission_level=1)
def tool_get_daily_briefing() -> Dict[str, Any]:
    from modules.scheduler.briefing import daily_briefing_generator
    return daily_briefing_generator.generate_briefing()


@jarvis_tool(name="schedule_periodic_task", description="Schedule a periodic background job for proactive monitoring, health checks, or briefings.", permission_level=2)
def tool_schedule_periodic_task(name: str, interval_seconds: int, action_type: str = "briefing") -> Dict[str, Any]:
    from modules.scheduler.engine import scheduler_engine
    job = scheduler_engine.add_job(name=name, interval_seconds=interval_seconds, action_type=action_type)
    return job.model_dump()


@jarvis_tool(name="open_vscode_project", description="Open a specific workspace folder or project path in Visual Studio Code.", permission_level=2)
async def tool_open_vscode_project(project_path: str = ".") -> Dict[str, Any]:
    from modules.integrations.vscode import vscode_integration
    return await vscode_integration.execute("open_workspace", {"path": project_path})


@jarvis_tool(name="inspect_git_status", description="Inspect the active Git repository branch, working tree changes, and recent commits.", permission_level=1)
async def tool_inspect_git_status(path: str = ".") -> Dict[str, Any]:
    from modules.integrations.github import github_integration
    return await github_integration.execute("repo_summary", {"path": path})


@jarvis_tool(name="control_spotify_media", description="Control media playback on Spotify or system (play_pause, next, previous, volume_up, volume_down, mute, search_play).", permission_level=1)
async def tool_control_spotify_media(action: str = "play_pause", query: str = "") -> Dict[str, Any]:
    from modules.integrations.spotify import spotify_integration
    return await spotify_integration.execute(action, {"query": query})


@jarvis_tool(name="analyze_daily_productivity", description="Compute personal daily developer productivity score, flow analysis, and objective fulfillment report.", permission_level=1)
def tool_analyze_daily_productivity() -> Dict[str, Any]:
    from modules.integrations.productivity import productivity_analyzer
    return productivity_analyzer.analyze_daily_productivity()

