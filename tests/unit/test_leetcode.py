"""
Unit tests for LeetCode Practice Engine and Bot Challenge Detection
"""

import pytest
from modules.computer_use.leetcode import leetcode_engine, CURATED_LEETCODE_PROBLEMS
from modules.computer_use.browser_playwright import playwright_controller


def test_leetcode_problem_catalog():
    assert len(CURATED_LEETCODE_PROBLEMS) >= 5
    assert "two-sum" in CURATED_LEETCODE_PROBLEMS
    assert "valid-parentheses" in CURATED_LEETCODE_PROBLEMS


def test_leetcode_search_and_filtering():
    # 1. Search by title
    results = leetcode_engine.search_problems(query="two sum")
    assert len(results) >= 1
    assert results[0]["slug"] == "two-sum"

    # 2. Search by difficulty
    easy_problems = leetcode_engine.search_problems(difficulty="Easy")
    assert len(easy_problems) >= 3
    assert all(p["difficulty"] == "Easy" for p in easy_problems)

    medium_problems = leetcode_engine.search_problems(difficulty="Medium")
    assert any(p["difficulty"] == "Medium" for p in medium_problems)


def test_leetcode_problem_details_and_test_cases():
    # Details lookup
    details = leetcode_engine.get_problem_details("two-sum")
    assert details is not None
    assert details["title"] == "Two Sum"
    assert "starter_code" in details
    assert len(details["examples"]) >= 2

    # Test cases extraction
    test_cases = leetcode_engine.extract_test_cases("two-sum")
    assert len(test_cases) >= 3
    assert test_cases[0]["expected"] == [0, 1]


def test_bot_challenge_detection_structure():
    # Detect bot challenges returns structured payload without throwing
    res = playwright_controller.detect_bot_challenges()
    assert isinstance(res, dict)
    assert "detected" in res
    assert isinstance(res["detected"], bool)
    if res["detected"]:
        assert "action_required" in res
        assert res["action_required"] == "USER_MANUAL_VERIFICATION"
