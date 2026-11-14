"""
Autonomous Goal Planner Engine
Decomposes complex human instructions into an acyclic directed graph of executable tool subtasks.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from core.planning.task import PlanDAG, SubTask, TaskStatus
from core.brain.tools import tool_registry
from core.providers.router import model_router

logger = logging.getLogger("jarvis.planning.planner")


class GoalPlanner:
    """Intelligently translates high-level user goals into structured PlanDAG instances."""

    PLANNER_PROMPT_TEMPLATE = """You are JARVIS's Chief Autonomous Planning Kernel.
Decompose the following user goal into a concise Directed Acyclic Graph (DAG) of discrete tool steps.

Goal: "{goal}"

Available Tools:
{tools_schema}

### Instructions:
1. Return ONLY a valid JSON object matching this schema:
{{
  "subtasks": [
    {{
      "id": "task_1",
      "description": "Short explanation of the step",
      "tool_name": "exact_tool_name_from_registry",
      "arguments": {{ "arg_name": "arg_value" }},
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "description": "Next step",
      "tool_name": "exact_tool_name_from_registry",
      "arguments": {{ ... }},
      "dependencies": ["task_1"]
    }}
  ]
}}
2. Maximum steps: 8.
3. Dependencies must reference prior task IDs.
4. Output strict JSON only. No markdown formatting, no conversational text.
"""

    async def create_plan(self, goal: str) -> PlanDAG:
        """
        Generates an executable PlanDAG from a natural language goal.
        Attempts LLM structured generation with fallback to heuristic goal templates.
        """
        logger.info(f"Generating autonomous execution plan for goal: '{goal}'")
        dag = PlanDAG(goal=goal)

        # 1. Attempt LLM decomposition
        try:
            tools_schemas = tool_registry.get_schemas()
            formatted_schemas = json.dumps([s["function"] for s in tools_schemas], indent=2)
            prompt = self.PLANNER_PROMPT_TEMPLATE.format(goal=goal, tools_schema=formatted_schemas)

            provider = model_router.get_provider()
            response = await provider.generate([
                {"role": "system", "content": "You are JARVIS Autonomous Planning Engine. Output raw JSON only."},
                {"role": "user", "content": prompt}
            ])

            content = response.content.strip()
            # Clean markdown code blocks if model wrapped JSON
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:].strip()

            parsed = json.loads(content)
            subtask_list = parsed.get("subtasks", [])

            for item in subtask_list:
                subtask = SubTask(
                    id=item.get("id", f"task_{len(dag.subtasks)+1}"),
                    description=item.get("description", "Execute planned step"),
                    tool_name=item.get("tool_name"),
                    arguments=item.get("arguments", {}),
                    dependencies=item.get("dependencies", [])
                )
                dag.add_subtask(subtask)

            # Validate graph integrity
            if dag.subtasks and not dag.has_cycles():
                logger.info(f"Successfully generated LLM plan with {len(dag.subtasks)} subtasks.")
                return dag
            else:
                logger.warning("LLM plan was empty or had cycles. Falling back to heuristic planner.")

        except Exception as e:
            logger.warning(f"LLM planning encountered exception: {e}. Activating heuristic planner.")

        # 2. Heuristic Goal Decomposition Fallback
        return self._generate_heuristic_plan(goal)

    def _generate_heuristic_plan(self, goal: str) -> PlanDAG:
        """Rule-based heuristic decomposition for common multi-step automation workflows."""
        dag = PlanDAG(goal=goal)
        goal_lower = goal.lower()

        if "exam" in goal_lower or "study" in goal_lower or "revision" in goal_lower:
            # Multi-step Exam Preparation Pipeline
            topic = goal_lower.replace("prepare my", "").replace("examination", "").replace("study", "").strip() or "Computer Networks"
            dag.add_subtask(SubTask(
                id="task_1",
                description=f"Search study materials and syllabus for {topic}",
                tool_name="web_search",
                arguments={"query": f"{topic} syllabus important topics exam notes", "max_results": 3},
                dependencies=[]
            ))
            dag.add_subtask(SubTask(
                id="task_2",
                description=f"Search local indexed documents for {topic}",
                tool_name="semantic_document_search",
                arguments={"query": topic, "limit": 3},
                dependencies=[]
            ))
            dag.add_subtask(SubTask(
                id="task_3",
                description=f"Synthesize comprehensive research and revision notes for {topic}",
                tool_name="conduct_research_report",
                arguments={"topic": topic, "max_sources": 3},
                dependencies=["task_1"]
            ))
        elif "download" in goal_lower or "organize" in goal_lower:
            # File Organization & Cleanup Pipeline
            dag.add_subtask(SubTask(
                id="task_1",
                description="Organize Downloads folder into categorized directories",
                tool_name="organize_directory",
                arguments={"folder_path": "Downloads"},
                dependencies=[]
            ))
            dag.add_subtask(SubTask(
                id="task_2",
                description="Identify duplicate files across workspace",
                tool_name="find_duplicate_files",
                arguments={},
                dependencies=["task_1"]
            ))
        else:
            # General Autonomous Multi-Step Research & Telemetry Pipeline
            dag.add_subtask(SubTask(
                id="task_1",
                description=f"Conduct web search on: {goal}",
                tool_name="web_search",
                arguments={"query": goal, "max_results": 3},
                dependencies=[]
            ))
            dag.add_subtask(SubTask(
                id="task_2",
                description="Fetch current system telemetry and hardware metrics",
                tool_name="get_system_telemetry",
                arguments={},
                dependencies=[]
            ))
            dag.add_subtask(SubTask(
                id="task_3",
                description=f"Compile synthesis report for {goal}",
                tool_name="conduct_research_report",
                arguments={"topic": goal, "max_sources": 2},
                dependencies=["task_1"]
            ))

        return dag


# Global planner singleton
goal_planner = GoalPlanner()
