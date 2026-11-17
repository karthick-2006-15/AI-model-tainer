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

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        device_id: Optional[str] = None,
        raise_on_denied: bool = False
    ) -> Dict[str, Any]:
        """Executes a registered tool with central security interception, permission evaluation, and exception handling."""
        from core.security.permissions import permission_engine

        # 1. Central Kill-Switch: Verify Emergency Stop Status
        if permission_engine.is_emergency_stopped():
            err_msg = "Operation blocked: Global Emergency Stop is active."
            logger.warning(f"Tool execution for '{tool_name}' blocked: Emergency Stop is active.")
            if raise_on_denied:
                raise PermissionError(err_msg)
            return {
                "success": False,
                "error": err_msg,
                "tool_name": tool_name,
                "emergency_stopped": True,
                "permission_denied": True
            }

        metadata = self.get_tool(tool_name)
        if not metadata:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry."
            }

        # 2. Central Security Interceptor: Evaluate Permission Level & Challenges
        target_resource = str(
            arguments.get("target_resource")
            or arguments.get("file_path")
            or arguments.get("path")
            or arguments.get("url")
            or arguments.get("app_name")
            or arguments.get("app_name_or_id")
            or arguments.get("app_name_or_process")
            or arguments.get("command")
            or arguments.get("recipient")
            or tool_name
        )

        allowed, reason, challenge = permission_engine.evaluate_request(
            tool_name=tool_name,
            permission_level=metadata.permission_level,
            target_resource=target_resource,
            arguments=arguments,
            device_id=device_id
        )

        if not allowed:
            err_msg = reason or "Operation not permitted by policy."
            logger.warning(f"Tool '{tool_name}' blocked by permission engine: {err_msg}")
            if raise_on_denied:
                raise PermissionError(err_msg)
            return {
                "success": False,
                "error": err_msg,
                "tool_name": tool_name,
                "permission_level": metadata.permission_level,
                "permission_denied": True,
                "challenge": challenge
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


@jarvis_tool(name="spotify.play", description="Search and play a song, artist, album, or playlist on the Spotify desktop application.", permission_level=1)
def tool_spotify_play(query: str = "") -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.play_track(query)


@jarvis_tool(name="spotify.pause", description="Pause music playback on Spotify.", permission_level=1)
def tool_spotify_pause() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.pause_playback()


@jarvis_tool(name="spotify.resume", description="Resume music playback on Spotify.", permission_level=1)
def tool_spotify_resume() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.resume_playback()


@jarvis_tool(name="spotify.next", description="Skip to the next track on Spotify.", permission_level=1)
def tool_spotify_next() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.next_track()


@jarvis_tool(name="spotify.previous", description="Return to the previous track on Spotify.", permission_level=1)
def tool_spotify_previous() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.previous_track()


@jarvis_tool(name="spotify.get_current_track", description="Get currently playing track title, artist, album, and duration on Spotify.", permission_level=1)
def tool_spotify_get_current_track() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.get_current_track()


@jarvis_tool(name="spotify.get_playback_state", description="Get complete Spotify playback state (is_playing, is_paused, volume, active device, track).", permission_level=1)
def tool_spotify_get_playback_state() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.get_playback_state()


@jarvis_tool(name="spotify.set_volume", description="Set Spotify audio volume level (0 to 100).", permission_level=1)
def tool_spotify_set_volume(level: int = 50) -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.set_volume(level)


@jarvis_tool(name="spotify.open", description="Open or focus the Windows Spotify desktop application.", permission_level=1)
def tool_spotify_open() -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    return spotify_controller.open_spotify()


@jarvis_tool(name="spotify.search", description="Search songs, artists, albums, or playlists on Spotify.", permission_level=1)
def tool_spotify_search(query: str, search_type: str = "track") -> Dict[str, Any]:
    from modules.media.spotify_controller import spotify_controller
    if search_type == "artist":
        return spotify_controller.search_artist(query)
    elif search_type == "album":
        return spotify_controller.search_album(query)
    elif search_type == "playlist":
        return spotify_controller.search_playlist(query)
    return spotify_controller.search_track(query)



@jarvis_tool(name="analyze_daily_productivity", description="Compute personal daily developer productivity score, flow analysis, and objective fulfillment report.", permission_level=1)
def tool_analyze_daily_productivity() -> Dict[str, Any]:
    from modules.integrations.productivity import productivity_analyzer
    return productivity_analyzer.analyze_daily_productivity()


@jarvis_tool(name="trigger_emergency_stop", description="Immediately halt all automated mouse, keyboard, tool, and external operations.", permission_level=1)
def tool_trigger_emergency_stop(reason: str = "User initiated emergency abort") -> Dict[str, Any]:
    from core.security.permissions import permission_engine
    return permission_engine.trigger_emergency_stop(reason=reason)


@jarvis_tool(name="reset_emergency_stop", description="Clear emergency stop state and restore normal operations.", permission_level=2)
def tool_reset_emergency_stop() -> Dict[str, Any]:
    from core.security.permissions import permission_engine
    return permission_engine.reset_emergency_stop()


# =====================================================================
# JARVIS-7: Autonomous Computer Use, Browser & WhatsApp Tool Registry
# =====================================================================

# 1. Computer Control Tools
@jarvis_tool(name="computer.capture_screen", description="Capture a screenshot of the primary display or region.", permission_level=1)
def tool_computer_capture_screen() -> Dict[str, Any]:
    from modules.computer_use.screen import screen_intelligence
    return screen_intelligence.capture_screen()


@jarvis_tool(name="computer.inspect_active_window", description="Identify the active application, window title, process name, and bounds.", permission_level=1)
def tool_computer_inspect_active_window() -> Dict[str, Any]:
    from modules.computer_use.screen import screen_intelligence
    return screen_intelligence.get_active_window()


@jarvis_tool(name="computer.get_active_window", description="Detect the currently active foreground window, application type, and boundaries.", permission_level=1)
def tool_computer_get_active_window() -> Dict[str, Any]:
    from modules.computer_use.screen import screen_intelligence
    return screen_intelligence.get_active_window()


@jarvis_tool(name="computer.inspect_ui", description="Inspect the Windows UI Automation accessibility tree to locate interactive buttons, inputs, and tabs.", permission_level=1)
def tool_computer_inspect_ui() -> Dict[str, Any]:
    from modules.computer_use.native_uia import native_uia
    return native_uia.inspect_active_window()


@jarvis_tool(name="computer.find_element", description="Find an on-screen element or control by name, label, or control type.", permission_level=1)
def tool_computer_find_element(name: str, control_type: str = "") -> Dict[str, Any]:
    from modules.computer_use.native_uia import native_uia
    return native_uia.find_element_info(name=name, control_type=control_type or None)


@jarvis_tool(name="computer.click", description="Universal click tool: clicks at coordinates (x, y) or by accessible element name.", permission_level=2)
def tool_computer_click(x: int = -1, y: int = -1, element_name: str = "", button: str = "left", clicks: int = 1) -> Dict[str, Any]:
    from modules.computer_use.mouse_kb import mouse_kb
    from modules.computer_use.loop import observation_loop
    if element_name:
        return observation_loop.click_interactive_element(element_name=element_name)
    if x >= 0 and y >= 0:
        return mouse_kb.click(x=x, y=y, button=button, clicks=clicks)
    return {"success": False, "error": "Must provide either (x, y) coordinates or element_name."}


@jarvis_tool(name="computer.click_element", description="Click an on-screen element by its accessible name or visual label.", permission_level=2)
def tool_computer_click_element(element_name: str, control_type: str = "") -> Dict[str, Any]:
    from modules.computer_use.loop import observation_loop
    return observation_loop.click_interactive_element(element_name=element_name, control_type=control_type or None)


@jarvis_tool(name="computer.type", description="Type text into the focused or target field (alias for computer.type_text).", permission_level=2)
def tool_computer_type(text: str) -> Dict[str, Any]:
    from modules.computer_use.mouse_kb import mouse_kb
    return mouse_kb.type_text(text=text)


@jarvis_tool(name="computer.type_text", description="Type text into the currently focused or targeted input field.", permission_level=2)
def tool_computer_type_text(text: str) -> Dict[str, Any]:
    from modules.computer_use.mouse_kb import mouse_kb
    return mouse_kb.type_text(text=text)


@jarvis_tool(name="computer.press_key", description="Press a keyboard key (e.g. enter, tab, esc, backspace).", permission_level=2)
def tool_computer_press_key(key_name: str) -> Dict[str, Any]:
    from modules.computer_use.mouse_kb import mouse_kb
    return mouse_kb.press_key(key_name=key_name)


@jarvis_tool(name="computer.scroll", description="Scroll vertically on the active window (up or down).", permission_level=2)
def tool_computer_scroll(direction: str = "down", clicks: int = 4) -> Dict[str, Any]:
    from modules.computer_use.mouse_kb import mouse_kb
    return mouse_kb.scroll(clicks=clicks, direction=direction)


@jarvis_tool(name="computer.search_app", description="Search indexed Windows applications across Win32, UWP, Store, and system utilities.", permission_level=1)
def tool_computer_search_app(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.search_app(query=query, limit=limit)


@jarvis_tool(name="computer.list_installed_apps", description="List all applications discovered and indexed on the Windows system, optionally filtered by category.", permission_level=1)
def tool_computer_list_installed_apps(category: str = "", limit: int = 50) -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.list_installed_apps(category=category or None, limit=limit)


@jarvis_tool(name="computer.find_app_by_description", description="Find installed applications matching a functional description (e.g. 'application I use for Python', 'my music player').", permission_level=1)
def tool_computer_find_app_by_description(description: str, limit: int = 5) -> List[Dict[str, Any]]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.find_app_by_description(description=description, limit=limit)


@jarvis_tool(name="computer.get_running_apps", description="List all currently running desktop applications that have open visible GUI windows.", permission_level=1)
def tool_computer_get_running_apps() -> List[Dict[str, Any]]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.get_running_apps()


@jarvis_tool(name="computer.open_app", description="Universal application launcher: discovers, launches, and verifies Win32, UWP, Store, system utilities, and folders.", permission_level=2)
def tool_computer_open_app(app_name_or_id: str = "", app_name: str = "") -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    query = app_name_or_id or app_name
    return universal_app_manager.open_app(app_name_or_query=query)


@jarvis_tool(name="computer.open_application", description="Launch or bring a Windows application to the foreground (alias for computer.open_app).", permission_level=2)
def tool_computer_open_application(app_name: str = "", app_name_or_id: str = "") -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    query = app_name or app_name_or_id
    return universal_app_manager.open_app(app_name_or_query=query)


@jarvis_tool(name="open_application", description="Launch an authorized application or website by name.", permission_level=2)
def tool_open_application(app_name: str = "", app_name_or_id: str = "") -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    query = app_name or app_name_or_id
    return universal_app_manager.open_app(app_name_or_query=query)


@jarvis_tool(name="computer.close_app", description="Gracefully closes an active application, warning if unsaved changes exist.", permission_level=2)
def tool_computer_close_app(app_name_or_process: str, force: bool = False) -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.close_app(app_name_or_process=app_name_or_process, force=force)


@jarvis_tool(name="computer.restart_app", description="Restarts an application by closing it and re-launching with verification.", permission_level=2)
def tool_computer_restart_app(app_name_or_process: str) -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    return universal_app_manager.restart_app(app_name_or_process=app_name_or_process)


@jarvis_tool(name="computer.switch_app", description="Brings an open application window to the foreground by matching its title or process name.", permission_level=2)
def tool_computer_switch_app(app_name_or_window: str) -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    success = universal_app_manager.switch_app(app_name_or_window=app_name_or_window)
    return {"success": success, "target": app_name_or_window, "focused": success}


@jarvis_tool(name="computer.switch_window", description="Bring a window to the foreground by matching its title (alias for computer.switch_app).", permission_level=2)
def tool_computer_switch_window(window_title: str) -> Dict[str, Any]:
    from modules.computer_use.app_manager import universal_app_manager
    success = universal_app_manager.switch_app(app_name_or_window=window_title)
    return {"success": success, "window_title": window_title, "focused": success}


@jarvis_tool(name="computer.verify_action", description="Compare before and after screenshots to verify that an action caused a visible UI change.", permission_level=1)
def tool_computer_verify_action(before_image_path: str, after_image_path: str) -> Dict[str, Any]:
    from modules.computer_use.screen import screen_intelligence
    return screen_intelligence.compare_visual_states(before_image_path, after_image_path)


# 2. Universal Browser Automation (Playwright)
@jarvis_tool(name="browser.open", description="Open a URL in the Playwright browser controller (supports Chrome, Edge, Chromium).", permission_level=1)
def tool_browser_open(url: str) -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.open(url=url)


@jarvis_tool(name="browser.inspect", description="Inspect DOM elements, headings, inputs, buttons, and links of the active browser page.", permission_level=1)
def tool_browser_inspect(selector: str = "") -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.inspect(selector=selector or None)


@jarvis_tool(name="browser.search", description="Execute a search query on Google, YouTube, or DuckDuckGo via browser.", permission_level=1)
def tool_browser_search(query: str, engine: str = "google") -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.search(query=query, engine=engine)


@jarvis_tool(name="browser.click", description="Click an element on the active browser page by CSS selector, text, or accessibility label.", permission_level=2)
def tool_browser_click(selector_or_text: str) -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.click(selector_or_text=selector_or_text)


@jarvis_tool(name="browser.fill", description="Fill text into an input field or textarea on the active webpage.", permission_level=2)
def tool_browser_fill(selector_or_name: str, value: str) -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.fill(selector_or_name=selector_or_name, value=value)


@jarvis_tool(name="browser.extract_text", description="Extract clean readable text or markdown content from the active webpage or selector.", permission_level=1)
def tool_browser_extract_text(selector: str = "") -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.extract_text(selector=selector or None)


@jarvis_tool(name="browser.get_tabs", description="List all open tabs in the browser context with titles and URLs.", permission_level=1)
def tool_browser_get_tabs() -> List[Dict[str, Any]]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.get_tabs()


@jarvis_tool(name="browser.screenshot", description="Capture a high-resolution screenshot of the active browser page.", permission_level=1)
def tool_browser_screenshot(full_page: bool = False) -> Dict[str, Any]:
    from modules.computer_use.browser_playwright import playwright_controller
    return playwright_controller.screenshot(full_page=full_page)


@jarvis_tool(name="browser.get_active_tab", description="Detect the currently open browser window and active web tab.", permission_level=1)
def tool_browser_get_active_tab() -> Dict[str, Any]:
    from modules.computer_use.browser import browser_automation
    return browser_automation.get_active_tab()


@jarvis_tool(name="browser.inspect_page", description="Inspect the DOM structure, interactive forms, inputs, and links on a webpage.", permission_level=1)
async def tool_browser_inspect_page(url: str) -> Dict[str, Any]:
    from modules.computer_use.browser import browser_automation
    return await browser_automation.inspect_page(url=url)


@jarvis_tool(name="browser.extract_questions", description="Extract all visible question prompts, choices, and input fields from a webpage HTML.", permission_level=1)
def tool_browser_extract_questions(html_content: str) -> List[Dict[str, Any]]:
    from modules.computer_use.worksheet import worksheet_engine
    return worksheet_engine.extract_questions_from_html(html_content=html_content)


@jarvis_tool(name="browser.fill_field", description="Fill a specific input field on an active webpage.", permission_level=2)
def tool_browser_fill_field(field_name: str, value: str) -> Dict[str, Any]:
    from modules.computer_use.browser import browser_automation
    return browser_automation.fill_field(field_name=field_name, value=value)


@jarvis_tool(name="browser.click_element", description="Click a button or link on an active webpage.", permission_level=2)
def tool_browser_click_element(text_or_name: str) -> Dict[str, Any]:
    from modules.computer_use.browser import browser_automation
    return browser_automation.click_element(text_or_name=text_or_name)


# 2b. Universal Page Intelligence Tools
@jarvis_tool(name="page.analyze", description="Deep semantic analysis of the active webpage or URL: structure, word count, forms, buttons, tables.", permission_level=1)
def tool_page_analyze(url: str = "") -> Dict[str, Any]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.analyze_page(url=url or None)


@jarvis_tool(name="page.find_element", description="Find elements on a webpage matching a query (text, ID, aria label) with bounds.", permission_level=1)
def tool_page_find_element(query: str) -> Dict[str, Any]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.find_element(query=query)


@jarvis_tool(name="page.extract_questions", description="Extract worksheet or form questions, types, and options from active webpage.", permission_level=1)
def tool_page_extract_questions(url: str = "") -> List[Dict[str, Any]]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.extract_questions(url=url or None)


@jarvis_tool(name="page.extract_tables", description="Extract data tables on active webpage into structured JSON headers and rows.", permission_level=1)
def tool_page_extract_tables(table_index: int = 0) -> Dict[str, Any]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.extract_tables(table_index=table_index)


@jarvis_tool(name="page.fill_form", description="Populate form fields on active page using key-value mappings.", permission_level=2)
def tool_page_fill_form(form_data: Dict[str, Any]) -> Dict[str, Any]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.fill_form(form_data=form_data)


@jarvis_tool(name="page.verify_form", description="Verify form completion and check that no required fields are missing before submission.", permission_level=1)
def tool_page_verify_form() -> Dict[str, Any]:
    from modules.computer_use.page_intelligence import page_intelligence
    return page_intelligence.verify_form()


# 2c. YouTube Automation Tools
@jarvis_tool(name="youtube.search", description="Search YouTube for videos and extract top results with titles, creators, and links.", permission_level=1)
def tool_youtube_search(query: str) -> Dict[str, Any]:
    from modules.computer_use.youtube import youtube_automation
    return youtube_automation.search(query=query)


@jarvis_tool(name="youtube.play_video", description="Play a video from search results by index (e.g. 1 for first video, 3 for third) or URL.", permission_level=2)
def tool_youtube_play_video(result_index: int = 1, video_url: str = "") -> Dict[str, Any]:
    from modules.computer_use.youtube import youtube_automation
    return youtube_automation.play_video(result_index=result_index, video_url=video_url or None)


@jarvis_tool(name="youtube.control_playback", description="Control YouTube video playback: play, pause, toggle, mute, unmute, volume_up, volume_down, fullscreen.", permission_level=2)
def tool_youtube_control_playback(action: str = "pause") -> Dict[str, Any]:
    from modules.computer_use.youtube import youtube_automation
    return youtube_automation.control_playback(action=action)


# 3. WhatsApp Automation Tools
@jarvis_tool(name="whatsapp.find_contact", description="Resolve a contact relation (father, mom, boss) or name using profile facts and heuristics.", permission_level=1)
def tool_whatsapp_find_contact(contact_query: str) -> Dict[str, Any]:
    from modules.computer_use.whatsapp import whatsapp_automation
    return whatsapp_automation.resolve_contact(contact_query=contact_query)


@jarvis_tool(name="whatsapp.open_conversation", description="Open WhatsApp and navigate to the specified contact conversation.", permission_level=2)
def tool_whatsapp_open_conversation(contact_name: str) -> Dict[str, Any]:
    from modules.computer_use.whatsapp import whatsapp_automation
    return whatsapp_automation.open_conversation(contact_name=contact_name)


@jarvis_tool(name="whatsapp.prepare_message", description="Draft a WhatsApp message and create a Level 3 authorization challenge for user confirmation.", permission_level=2)
def tool_whatsapp_prepare_message(recipient: str, message: str) -> Dict[str, Any]:
    from modules.computer_use.whatsapp import whatsapp_automation
    return whatsapp_automation.prepare_message(recipient=recipient, message_text=message)


@jarvis_tool(name="whatsapp.send_message", description="Send an authorized WhatsApp message. Strictly requires explicit user confirmation.", permission_level=3)
def tool_whatsapp_send_message(recipient: str, message: str) -> Dict[str, Any]:
    from modules.computer_use.whatsapp import whatsapp_automation
    return whatsapp_automation.send_message(recipient=recipient, message_text=message)


@jarvis_tool(name="whatsapp.verify_message", description="Verify that a sent message appears in the active chat conversation window.", permission_level=1)
def tool_whatsapp_verify_message(message: str) -> Dict[str, Any]:
    from modules.computer_use.whatsapp import whatsapp_automation
    return whatsapp_automation.verify_message(message_text=message)


# 4. Worksheet & Form Automation Tools
@jarvis_tool(name="worksheet.extract_questions", description="Extract visible questions, options, and input types from an online worksheet or form.", permission_level=1)
def tool_worksheet_extract_questions(html_content: str) -> List[Dict[str, Any]]:
    from modules.computer_use.worksheet import worksheet_engine
    return worksheet_engine.extract_questions_from_html(html_content=html_content)


@jarvis_tool(name="worksheet.research_answers", description="Research factual answers for extracted worksheet questions using Internet Intelligence.", permission_level=1)
async def tool_worksheet_research_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from modules.computer_use.worksheet import worksheet_engine
    return await worksheet_engine.research_answers(questions=questions)


@jarvis_tool(name="worksheet.fill_answers", description="Populate researched answers into the corresponding worksheet form fields.", permission_level=2)
def tool_worksheet_fill_answers(answered_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    from modules.computer_use.worksheet import worksheet_engine
    return worksheet_engine.fill_answers(answered_questions=answered_questions)


@jarvis_tool(name="worksheet.review_answers", description="Review all filled fields and compile a structured summary before submission.", permission_level=1)
def tool_worksheet_review_answers(answered_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    from modules.computer_use.worksheet import worksheet_engine
    return worksheet_engine.review_answers(answered_questions=answered_questions)


@jarvis_tool(name="worksheet.submit", description="Submit a completed worksheet. Strictly requires explicit user confirmation.", permission_level=3)
def tool_worksheet_submit() -> Dict[str, Any]:
    from modules.computer_use.worksheet import worksheet_engine
    return worksheet_engine.submit_worksheet()


# 5. Multi-Application Orchestration & Office Intelligence Tools
@jarvis_tool(name="orchestration.run_multi_app_workflow", description="Execute an autonomous end-to-end multi-app workflow (research web, generate Word report, create PowerPoint presentation, verify files, and view).", permission_level=2)
async def tool_run_multi_app_workflow(topic: str) -> Dict[str, Any]:
    from modules.orchestration.multi_app import multi_app_orchestrator
    return await multi_app_orchestrator.execute_research_report_presentation_workflow(topic=topic)


@jarvis_tool(name="office.create_presentation", description="Create a professional PowerPoint presentation (.pptx) with slides, titles, and bullet points.", permission_level=2)
def tool_office_create_presentation(topic: str, slides: List[Dict[str, Any]]) -> Dict[str, Any]:
    from modules.files.office_generator import office_generator
    return office_generator.create_presentation(topic=topic, slides_data=slides)


@jarvis_tool(name="office.create_document", description="Create a structured Word document (.docx) executive report with sections and citations.", permission_level=2)
def tool_office_create_document(title: str, summary: str, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    from modules.files.office_generator import office_generator
    return office_generator.create_word_report(title=title, executive_summary=summary, sections=sections)


@jarvis_tool(name="office.verify_file", description="Verify file integrity, valid binary headers, and execution openability.", permission_level=1)
def tool_office_verify_file(file_path: str) -> Dict[str, Any]:
    from modules.files.office_generator import office_generator
    return office_generator.verify_file_integrity_and_openable(file_path=file_path)


# 6. Intelligent File Management Tools
@jarvis_tool(name="files.recursive_search", description="Recursively search files across workspace directories by name and extensions.", permission_level=1)
def tool_files_recursive_search(query: str, root_dir: str = "") -> List[Dict[str, Any]]:
    from modules.files.manager import intelligent_file_manager
    return intelligent_file_manager.search_files_recursive(query=query, root_dir=root_dir or None)


@jarvis_tool(name="files.preview_organization", description="Generate a preview of folder organization without moving any files.", permission_level=1)
def tool_files_preview_organization(folder_path: str) -> Dict[str, Any]:
    from modules.files.manager import intelligent_file_manager
    return intelligent_file_manager.organize_folder_with_preview(folder_path=folder_path, execute=False)


@jarvis_tool(name="files.extract_metadata", description="Extract detailed file metadata, size, timestamps, word/page counts, and SHA-256 hash.", permission_level=1)
def tool_files_extract_metadata(file_path: str) -> Dict[str, Any]:
    from modules.files.manager import intelligent_file_manager
    return intelligent_file_manager.extract_metadata(file_path=file_path)


@jarvis_tool(name="files.summarize_document", description="Parse and summarize a document (PDF, Word, PPTX, or text file).", permission_level=1)
def tool_files_summarize_document(file_path: str) -> Dict[str, Any]:
    from modules.files.manager import intelligent_file_manager
    return intelligent_file_manager.summarize_document(file_path=file_path)


@jarvis_tool(name="files.convert", description="Convert files between formats (e.g. Markdown or text to DOCX).", permission_level=2)
def tool_files_convert(source_path: str, target_format: str) -> Dict[str, Any]:
    from modules.files.manager import intelligent_file_manager
    return intelligent_file_manager.convert_file(source_path=source_path, target_format=target_format)


# 7. Windows Intelligence Diagnostics Tools
@jarvis_tool(name="system.get_network_status", description="Inspect active network interfaces, IP addresses, data rates, and internet connectivity.", permission_level=1)
def tool_system_get_network_status() -> Dict[str, Any]:
    from modules.automation.windows_intel import windows_intelligence
    return windows_intelligence.get_network_status()


@jarvis_tool(name="system.get_startup_apps", description="List applications configured to start automatically on Windows boot.", permission_level=1)
def tool_system_get_startup_apps() -> List[Dict[str, Any]]:
    from modules.automation.windows_intel import windows_intelligence
    return windows_intelligence.get_startup_applications()


@jarvis_tool(name="system.analyze_storage", description="Analyze storage consumption and categorize largest file types in directory.", permission_level=1)
def tool_system_analyze_storage(folder_path: str = "") -> Dict[str, Any]:
    from modules.automation.windows_intel import windows_intelligence
    return windows_intelligence.analyze_storage(target_folder=folder_path or None)


@jarvis_tool(name="system.troubleshoot", description="Run automated system diagnostics on CPU, RAM, disk, network, and crash dumps.", permission_level=1)
def tool_system_troubleshoot() -> Dict[str, Any]:
    from modules.automation.windows_intel import windows_intelligence
    return windows_intelligence.run_basic_troubleshooting()


# 8. Productivity & Task Scheduling Tools
@jarvis_tool(name="productivity.create_task", description="Create a prioritized task with optional deadline and tags.", permission_level=2)
def tool_productivity_create_task(title: str, priority: str = "medium", deadline: str = "") -> Dict[str, Any]:
    from modules.scheduler.productivity import productivity_manager
    task = productivity_manager.create_task(title=title, priority=priority, deadline_str=deadline or None)
    return task.model_dump()


@jarvis_tool(name="productivity.list_tasks", description="List active and completed tasks with deadlines and priorities.", permission_level=1)
def tool_productivity_list_tasks(include_completed: bool = False) -> List[Dict[str, Any]]:
    from modules.scheduler.productivity import productivity_manager
    return productivity_manager.list_tasks(include_completed=include_completed)


@jarvis_tool(name="productivity.schedule_reminder", description="Schedule a reminder from natural voice instruction.", permission_level=2)
def tool_productivity_schedule_reminder(command: str) -> Dict[str, Any]:
    from modules.scheduler.productivity import productivity_manager
    return productivity_manager.schedule_voice_reminder(voice_command=command)


# 9. Avatar & Virtual AI Face Tools
@jarvis_tool(name="avatar.set_state", description="Change avatar animation state (idle, listening, thinking, speaking, happy, confused, error, warning, sleeping, success).", permission_level=1)
def tool_avatar_set_state(state: str, message: str = "") -> Dict[str, Any]:
    from modules.avatar.avatar_engine import avatar_engine
    avatar_engine.set_state(state, message or None)
    return avatar_engine.get_state()


@jarvis_tool(name="avatar.set_expression", description="Trigger a transient facial expression on the avatar face (happy, confused, alert, wink).", permission_level=1)
def tool_avatar_set_expression(expression: str, duration: float = 3.0) -> Dict[str, Any]:
    from modules.avatar.avatar_engine import avatar_engine
    avatar_engine.trigger_expression(expression, duration)
    return avatar_engine.get_state()


@jarvis_tool(name="avatar.set_theme", description="Set avatar visual theme (classic_cyan, arc_gold, quantum_violet, matrix_emerald).", permission_level=1)
def tool_avatar_set_theme(theme: str) -> Dict[str, Any]:
    from modules.avatar.avatar_engine import avatar_engine
    avatar_engine.update_settings({"theme": theme})
    return avatar_engine.get_settings()


@jarvis_tool(name="avatar.get_status", description="Get the visual status, eye metrics, and current animation state of the avatar face.", permission_level=1)
def tool_avatar_get_status() -> Dict[str, Any]:
    from modules.avatar.avatar_engine import avatar_engine
    return avatar_engine.get_state()



