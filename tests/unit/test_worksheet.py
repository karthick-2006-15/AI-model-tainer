"""
Unit tests for Online Worksheet & Form Automation Engine
"""

import pytest
from modules.computer_use.worksheet import worksheet_engine
from core.security.permissions import permission_engine

SAMPLE_WORKSHEET_HTML = """
<!DOCTYPE html>
<html>
<head><title>Math & Science Assessment</title></head>
<body>
    <form id="quiz">
        <div>
            <label for="q1">Question 1: What is the capital of France?</label>
            <input type="text" id="q1" name="capital_france">
        </div>
        <div>
            <label>Question 2: What is the boiling point of water in Celsius?</label>
            <input type="number" id="q2" name="boiling_point">
        </div>
        <div>
            <p>Question 3: Which planet is known as the Red Planet?</p>
            <label><input type="radio" name="planet" value="Mars"> Mars</label>
            <label><input type="radio" name="planet" value="Venus"> Venus</label>
            <label><input type="radio" name="planet" value="Jupiter"> Jupiter</label>
        </div>
        <button type="submit" id="submit_btn">Submit form</button>
    </form>
</body>
</html>
"""


def test_worksheet_question_extraction():
    questions = worksheet_engine.extract_questions_from_html(SAMPLE_WORKSHEET_HTML)
    assert len(questions) >= 3

    # Check first question
    q1 = questions[0]
    assert "France" in q1["prompt"]
    assert q1["question_type"] == "text"

    # Check numeric question
    q2 = questions[1]
    assert "boiling point" in q2["prompt"].lower()
    assert q2["question_type"] == "numeric"

    # Check radio question
    q3 = questions[2]
    assert "Red Planet" in q3["prompt"]
    assert q3["question_type"] == "multiple_choice"
    assert "Mars" in q3["options"]


@pytest.mark.asyncio
async def test_worksheet_research_and_review():
    questions = worksheet_engine.extract_questions_from_html(SAMPLE_WORKSHEET_HTML)
    researched = await worksheet_engine.research_answers(questions)
    assert len(researched) == len(questions)
    assert all("answer" in r for r in researched)

    review = worksheet_engine.review_answers(researched)
    assert review["success"] is True
    assert review["total"] == len(questions)
    assert "summary" in review


def test_worksheet_submit_permission_guard():
    # Attempting to submit without confirmation triggers Level 3 challenge
    res = worksheet_engine.submit_worksheet(skip_permission_check=False)
    assert res["success"] is False
    assert res["awaiting_authorization"] is True
    assert "challenge" in res
