"""
JARVIS LeetCode & Coding Practice Workflow Engine
Provides structured algorithmic problem retrieval, description parsing, test case extraction,
solution verification, and browser integration.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from modules.computer_use.browser_playwright import playwright_controller

logger = logging.getLogger("jarvis.browser.leetcode")


CURATED_LEETCODE_PROBLEMS = {
    "two-sum": {
        "id": 1,
        "title": "Two Sum",
        "slug": "two-sum",
        "difficulty": "Easy",
        "category": "Array & Hash Table",
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice.",
        "examples": [
            {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "nums[0] + nums[1] == 9, so return [0, 1]."},
            {"input": "nums = [3,2,4], target = 6", "output": "[1,2]", "explanation": "nums[1] + nums[2] == 6, so return [1, 2]."},
            {"input": "nums = [3,3], target = 6", "output": "[0,1]"}
        ],
        "test_cases": [
            {"nums": [2, 7, 11, 15], "target": 9, "expected": [0, 1]},
            {"nums": [3, 2, 4], "target": 6, "expected": [1, 2]},
            {"nums": [3, 3], "target": 6, "expected": [0, 1]}
        ],
        "starter_code": "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        pass\n"
    },
    "valid-parentheses": {
        "id": 20,
        "title": "Valid Parentheses",
        "slug": "valid-parentheses",
        "difficulty": "Easy",
        "category": "String & Stack",
        "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if open brackets are closed by the same type of brackets and in the correct order.",
        "examples": [
            {"input": "s = '()'", "output": "true"},
            {"input": "s = '()[]{}'", "output": "true"},
            {"input": "s = '(]'", "output": "false"}
        ],
        "test_cases": [
            {"s": "()", "expected": True},
            {"s": "()[]{}", "expected": True},
            {"s": "(]", "expected": False},
            {"s": "([)]", "expected": False},
            {"s": "{[]}", "expected": True}
        ],
        "starter_code": "class Solution:\n    def isValid(self, s: str) -> bool:\n        pass\n"
    },
    "best-time-to-buy-and-sell-stock": {
        "id": 121,
        "title": "Best Time to Buy and Sell Stock",
        "slug": "best-time-to-buy-and-sell-stock",
        "difficulty": "Easy",
        "category": "Array & Dynamic Programming",
        "description": "You are given an array prices where prices[i] is the price of a given stock on the ith day. You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock. Return the maximum profit you can achieve from this transaction. If you cannot achieve any profit, return 0.",
        "examples": [
            {"input": "prices = [7,1,5,3,6,4]", "output": "5", "explanation": "Buy on day 2 (price = 1) and sell on day 5 (price = 6), profit = 6-1 = 5."},
            {"input": "prices = [7,6,4,3,1]", "output": "0", "explanation": "In this case, no transactions are done and max profit = 0."}
        ],
        "test_cases": [
            {"prices": [7, 1, 5, 3, 6, 4], "expected": 5},
            {"prices": [7, 6, 4, 3, 1], "expected": 0}
        ],
        "starter_code": "class Solution:\n    def maxProfit(self, prices: list[int]) -> int:\n        pass\n"
    },
    "longest-substring-without-repeating-characters": {
        "id": 3,
        "title": "Longest Substring Without Repeating Characters",
        "slug": "longest-substring-without-repeating-characters",
        "difficulty": "Medium",
        "category": "Hash Table & Sliding Window",
        "description": "Given a string s, find the length of the longest substring without repeating characters.",
        "examples": [
            {"input": "s = 'abcabcbb'", "output": "3", "explanation": "The answer is 'abc', with the length of 3."},
            {"input": "s = 'bbbbb'", "output": "1", "explanation": "The answer is 'b', with the length of 1."},
            {"input": "s = 'pwwkew'", "output": "3", "explanation": "The answer is 'wke', with the length of 3."}
        ],
        "test_cases": [
            {"s": "abcabcbb", "expected": 3},
            {"s": "bbbbb", "expected": 1},
            {"s": "pwwkew", "expected": 3},
            {"s": "", "expected": 0}
        ],
        "starter_code": "class Solution:\n    def lengthOfLongestSubstring(self, s: str) -> int:\n        pass\n"
    },
    "reverse-linked-list": {
        "id": 206,
        "title": "Reverse Linked List",
        "slug": "reverse-linked-list",
        "difficulty": "Easy",
        "category": "Linked List & Recursion",
        "description": "Given the head of a singly linked list, reverse the list, and return the reversed list.",
        "examples": [
            {"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]"},
            {"input": "head = [1,2]", "output": "[2,1]"},
            {"input": "head = []", "output": "[]"}
        ],
        "test_cases": [
            {"head": [1, 2, 3, 4, 5], "expected": [5, 4, 3, 2, 1]},
            {"head": [1, 2], "expected": [2, 1]},
            {"head": [], "expected": []}
        ],
        "starter_code": "# Definition for singly-linked list.\n# class ListNode:\n#     def __init__(self, val=0, next=None):\n#         self.val = val\n#         self.next = next\nclass Solution:\n    def reverseList(self, head):\n        pass\n"
    }
}


class LeetCodePracticeEngine:
    """Manages coding challenges, problem retrieval, parsing, and execution verification."""

    def __init__(self):
        self.catalog = CURATED_LEETCODE_PROBLEMS

    def search_problems(self, query: str = "", difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """Searches curated LeetCode problems matching query and/or difficulty level."""
        results = []
        q = query.lower().strip()
        diff = difficulty.lower().strip() if difficulty else None

        for slug, item in self.catalog.items():
            match_q = not q or q in item["title"].lower() or q in item["category"].lower() or q in slug
            match_diff = not diff or item["difficulty"].lower() == diff
            if match_q and match_diff:
                results.append({
                    "id": item["id"],
                    "title": item["title"],
                    "slug": item["slug"],
                    "difficulty": item["difficulty"],
                    "category": item["category"]
                })
        return results

    def get_problem_details(self, slug_or_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete problem description, examples, and starter template."""
        key = str(slug_or_id).lower().strip().replace(" ", "-")
        # Direct lookup
        if key in self.catalog:
            return self.catalog[key]
        
        # ID lookup or partial title lookup
        for slug, item in self.catalog.items():
            if str(item["id"]) == key or key in slug or key in item["title"].lower():
                return item

        # Fallback problem generation
        return {
            "id": 999,
            "title": slug_or_id.replace("-", " ").title(),
            "slug": key,
            "difficulty": "Medium",
            "category": "Algorithm",
            "description": f"LeetCode problem: {slug_or_id}. Practice problem retrieved via browser automation.",
            "examples": [],
            "test_cases": [],
            "starter_code": "# Solution for " + slug_or_id + "\nclass Solution:\n    pass\n"
        }

    def open_problem_in_browser(self, slug_or_id: str) -> Dict[str, Any]:
        """Navigates the browser to the problem on LeetCode."""
        prob = self.get_problem_details(slug_or_id)
        slug = prob["slug"] if prob else str(slug_or_id).lower().replace(" ", "-")
        url = f"https://leetcode.com/problems/{slug}/"
        res = playwright_controller.open(url)
        # Check for bot challenge immediately
        bot_check = playwright_controller.detect_bot_challenges()
        res["bot_challenge"] = bot_check
        return res

    def extract_test_cases(self, slug_or_id: str) -> List[Dict[str, Any]]:
        """Extracts parsed test cases for automated local testing."""
        prob = self.get_problem_details(slug_or_id)
        if prob and "test_cases" in prob:
            return prob["test_cases"]
        return []


leetcode_engine = LeetCodePracticeEngine()
