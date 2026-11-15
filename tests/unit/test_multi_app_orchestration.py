"""
Comprehensive Unit & Integration Tests for JARVIS-8 Multi-Application Intelligence
Tests Autonomous Multi-App Orchestrator, PowerPoint & Word Generation,
File Intelligence & Preview Organization, Windows Intelligence Diagnostics,
and Natural Voice Productivity Reminders.
"""

import pytest
import os
import tempfile
from modules.files.office_generator import office_generator
from modules.files.manager import intelligent_file_manager
from modules.automation.windows_intel import windows_intelligence
from modules.scheduler.productivity import productivity_manager
from modules.orchestration.multi_app import multi_app_orchestrator
from core.brain.intent import intent_classifier, IntentCategory
from core.brain.tools import tool_registry


def test_office_generator_presentation_creation():
    """Verifies PowerPoint (.pptx) creation with slides and styling."""
    topic = "Autonomous Warehouse Robots"
    slides = [
        {"title": "Introduction to AMR", "bullet_points": ["SLAM Navigation", "Obstacle Avoidance"]},
        {"title": "Fleet Management", "bullet_points": ["Cloud Dispatch", "Battery Optimization"]}
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "test_presentation.pptx")
        res = office_generator.create_presentation(topic=topic, slides_data=slides, output_path=out_path)
        assert res["success"] is True
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000  # Valid non-empty PPTX
        assert res["slides_count"] >= 3  # Title slide + 2 content slides


def test_office_generator_word_report_creation():
    """Verifies Word (.docx) report generation with executive summary and sections."""
    title = "Autonomous Systems Industry Analysis"
    summary = "Executive summary of autonomous mobile robots."
    sections = [
        {"heading": "Market Growth", "content": "AMR adoption increased 35% year-over-year.", "bullets": ["AGV vs AMR", "Sensory arrays"]}
    ]
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = os.path.join(tmp_dir, "test_report.docx")
        res = office_generator.create_word_report(
            title=title,
            executive_summary=summary,
            sections=sections,
            sources=[{"title": "Robotics Journal", "url": "https://example.com/robotics"}],
            output_path=out_path
        )
        assert res["success"] is True
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 1000


def test_office_file_integrity_verification():
    """Verifies binary header detection (PK zip magic bytes for DOCX/PPTX)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "sample.docx")
        office_generator.create_word_report("Test Document", "Summary text", [], output_path=test_file)

        v_res = office_generator.verify_file_integrity_and_openable(test_file)
        assert v_res["success"] is True
        assert v_res["integrity_verified"] is True
        assert v_res["format"] == "docx"

        # Verify non-existent file handling
        bad_res = office_generator.verify_file_integrity_and_openable("non_existent_file.pptx")
        assert bad_res["success"] is False


def test_intelligent_file_manager_metadata_and_integrity():
    """Verifies metadata extraction, SHA-256 calculation, and integrity checks."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dummy_file = os.path.join(tmp_dir, "sample.txt")
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("JARVIS multi-application intelligence test file.")

        meta = intelligent_file_manager.extract_metadata(dummy_file)
        assert meta["success"] is True
        assert meta["size_bytes"] > 0
        assert len(meta["sha256"]) == 64  # SHA-256 length

        v_res = intelligent_file_manager.verify_file_integrity(dummy_file, expected_hash=meta["sha256"])
        assert v_res["success"] is True
        assert v_res["hash_matched"] is True


def test_intelligent_file_manager_preview_organization():
    """Verifies that folder organization preview mode does NOT move files until executed."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        f1 = os.path.join(tmp_dir, "document.pdf")
        f2 = os.path.join(tmp_dir, "picture.png")
        open(f1, "w").close()
        open(f2, "w").close()

        # Preview mode
        prev = intelligent_file_manager.organize_folder_with_preview(tmp_dir, execute=False)
        assert prev["success"] is True
        assert prev["preview_mode"] is True
        assert prev["total_files_to_move"] == 2
        # Files should still be in original root
        assert os.path.exists(f1)
        assert os.path.exists(f2)


def test_intelligent_file_manager_conversion():
    """Verifies file format conversion from Markdown to DOCX."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        md_file = os.path.join(tmp_dir, "notes.md")
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# Autonomous Robotics\n\nRobots perform automated material movement.")

        conv_res = intelligent_file_manager.convert_file(md_file, target_format="docx")
        assert conv_res["success"] is True
        assert conv_res["file_path"].endswith(".docx")
        assert os.path.exists(conv_res["file_path"])


def test_windows_intelligence_diagnostics():
    """Verifies telemetry, network status, startup apps, and troubleshooting diagnostics."""
    # 1. Network Status
    net = windows_intelligence.get_network_status()
    assert "internet_connected" in net
    assert "bytes_sent_mb" in net
    assert "active_interfaces" in net

    # 2. Startup Applications
    start_apps = windows_intelligence.get_startup_applications()
    assert isinstance(start_apps, list)

    # 3. Basic Troubleshooting
    diag = windows_intelligence.run_basic_troubleshooting()
    assert "healthy" in diag
    assert "metrics_summary" in diag


def test_productivity_task_creation_and_voice_reminder():
    """Verifies task prioritization, natural voice reminders, and progress tracking."""
    # 1. Direct Task Creation
    task = productivity_manager.create_task("Review Robotics Presentation", priority="high", deadline_str="Tomorrow 9 AM")
    assert task.title == "Review Robotics Presentation"
    assert task.priority == "high"

    # 2. Natural Voice Reminder
    rem_res = productivity_manager.schedule_voice_reminder("Jarvis, remind me to submit my assignment tomorrow at 9 AM")
    assert rem_res["success"] is True
    assert "assignment" in rem_res["reminder"].lower()

    # 3. Progress Report
    report = productivity_manager.get_progress_report()
    assert report["total_tasks"] >= 2
    assert report["active_tasks_count"] >= 2

    # 4. Mark Completed
    ok = productivity_manager.complete_task(task.id)
    assert ok is True


@pytest.mark.asyncio
async def test_multi_app_orchestrator_autonomous_workflow():
    """
    Verifies end-to-end execution of the multi-application workflow:
    Research -> Word Report (.docx) -> PowerPoint (.pptx) -> File Verification -> Memory Sync.
    """
    topic = "Autonomous Warehouse Robots"
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = await multi_app_orchestrator.execute_research_report_presentation_workflow(
            topic=topic,
            output_dir=tmp_dir,
            open_files_when_done=False  # Do not pop up PowerPoint GUI during automated test
        )
        assert res["success"] is True
        assert "report_docx" in res
        assert "presentation_pptx" in res
        assert os.path.exists(res["report_docx"])
        assert os.path.exists(res["presentation_pptx"])
        assert res["integrity_verified"] is True
        assert res["slides_count"] >= 3


def test_brain_intent_multi_app_routing():
    """Verifies that natural voice commands route to multi-app orchestrator and productivity tools."""
    # 1. Multi-App Workflow Command
    int_wf = intent_classifier.classify("Research autonomous warehouse robots, prepare a report and create a presentation")
    assert int_wf.category == IntentCategory.COMPLEX_TASK
    assert int_wf.target_tool == "orchestration.run_multi_app_workflow"
    assert "autonomous warehouse robots" in int_wf.extracted_params["topic"].lower()

    # 2. Voice Reminder Command
    int_rem = intent_classifier.classify("Jarvis, remind me to submit my assignment tomorrow at 9 AM")
    assert int_rem.category == IntentCategory.SYSTEM_CONTROL
    assert int_rem.target_tool == "productivity.schedule_reminder"


@pytest.mark.asyncio
async def test_tool_registry_multi_app_tools():
    """Verifies that all new tools are registered in the Brain Tool Registry."""
    schemas = tool_registry.get_schemas()
    names = [s["function"]["name"] for s in schemas]

    required_tools = [
        "orchestration.run_multi_app_workflow",
        "office.create_presentation",
        "office.create_document",
        "office.verify_file",
        "files.recursive_search",
        "files.preview_organization",
        "files.extract_metadata",
        "files.summarize_document",
        "system.get_network_status",
        "system.get_startup_apps",
        "system.troubleshoot",
        "productivity.create_task",
        "productivity.list_tasks",
        "productivity.schedule_reminder"
    ]
    for t in required_tools:
        assert t in names, f"Tool '{t}' missing from tool_registry"

    # Test direct execution of read tools
    res_net = await tool_registry.execute("system.get_network_status", {})
    assert res_net["success"] is True

    res_diag = await tool_registry.execute("system.troubleshoot", {})
    assert res_diag["success"] is True
