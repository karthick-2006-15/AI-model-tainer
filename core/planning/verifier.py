"""
Result Verifier & Execution Validation Engine
Evaluates action outcomes against expected schemas, detects recoverable failures, and triggers retries.
"""

import logging
from typing import Dict, Any, Tuple
from core.planning.task import SubTask, TaskStatus

logger = logging.getLogger("jarvis.planning.verifier")


class ResultVerifier:
    """Validates execution results and handles dynamic failure recovery."""

    @staticmethod
    def verify_subtask_outcome(subtask: SubTask, raw_result: Any) -> Tuple[bool, str]:
        """
        Validates if a subtask succeeded according to its tool signature and return payload.
        Returns: (is_success, failure_or_success_reason)
        """
        if raw_result is None:
            return False, "Tool returned null/empty execution output."

        # Case 1: Result is a dict with explicit success flag
        if isinstance(raw_result, dict):
            if "success" in raw_result and not raw_result["success"]:
                err_msg = raw_result.get("error", "Tool explicitly reported failure status.")
                return False, f"Tool execution failed: {err_msg}"
            
            # Check for error keys
            if "error" in raw_result and raw_result["error"]:
                return False, f"Tool error occurred: {raw_result['error']}"

            inner_res = raw_result.get("result")
            if isinstance(inner_res, str):
                err_lower = inner_res.lower()
                if err_lower.startswith("error:") or "failed to launch" in err_lower or "does not exist" in err_lower or "not found" in err_lower:
                    return False, inner_res

        # Case 2: String result containing error markers
        if isinstance(raw_result, str):
            err_lower = raw_result.lower()
            if err_lower.startswith("error:") or "failed to launch" in err_lower or "does not exist" in err_lower or "not found" in err_lower:
                return False, raw_result

        # Valid success
        return True, "Subtask outcome verified successfully."

    @staticmethod
    def evaluate_retry_or_abort(subtask: SubTask, error_message: str) -> bool:
        """
        Determines whether the subtask should be retried or transitioned to FAILED.
        Returns True if a retry should be scheduled, False if attempts are exhausted.
        """
        subtask.retry_count += 1
        subtask.error = error_message

        if subtask.retry_count < subtask.max_retries:
            logger.warning(
                f"Subtask '{subtask.id}' failed on attempt {subtask.retry_count}/{subtask.max_retries}: {error_message}. Scheduling retry."
            )
            subtask.status = TaskStatus.PENDING
            return True
        else:
            logger.error(
                f"Subtask '{subtask.id}' exceeded maximum retry attempts ({subtask.max_retries}). Marking FAILED."
            )
            subtask.status = TaskStatus.FAILED
            return False


# Global verifier singleton
result_verifier = ResultVerifier()
