"""
Local File Operations Manager
Provides safe file creation, movement, renaming, deletion, and directory organization with security boundaries.
"""

import os
import shutil
import logging
from typing import Dict, Any, List, Optional
from core.security.permissions import permission_engine

logger = logging.getLogger("jarvis.automation.file_ops")


class FileOperationsManager:
    FORBIDDEN_ROOTS = [
        os.path.normpath("C:/Windows"),
        os.path.normpath("C:/Program Files"),
        os.path.normpath("C:/Program Files (x86)"),
    ]

    ORGANIZATION_MAP = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls", ".pptx", ".csv"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
        "Code": [".py", ".ts", ".js", ".json", ".html", ".css", ".cpp", ".c", ".rs"],
        "Installers": [".exe", ".msi", ".iso"]
    }

    @classmethod
    def _is_path_safe(cls, path: str) -> bool:
        """Ensures the target path is not inside a restricted Windows system directory."""
        abs_path = os.path.abspath(os.path.expanduser(path))
        for forbidden in cls.FORBIDDEN_ROOTS:
            if abs_path.lower().startswith(forbidden.lower()):
                logger.warning(f"BLOCKED ACCESS to restricted path: {abs_path}")
                return False
        return True

    @classmethod
    def create_directory(cls, dir_path: str) -> Dict[str, Any]:
        """Creates a directory in an authorized location (Level 2)."""
        if not cls._is_path_safe(dir_path):
            return {"success": False, "error": "Access to restricted system directory denied."}

        try:
            os.makedirs(dir_path, exist_ok=True)
            return {"success": True, "path": os.path.abspath(dir_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def move_file(cls, source_path: str, destination_path: str) -> Dict[str, Any]:
        """Moves a file from source to destination (Level 2)."""
        if not cls._is_path_safe(source_path) or not cls._is_path_safe(destination_path):
            return {"success": False, "error": "Access to restricted system directory denied."}

        try:
            dest_dir = os.path.dirname(os.path.abspath(destination_path))
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(source_path, destination_path)
            return {
                "success": True,
                "from": source_path,
                "to": destination_path
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def rename_file(cls, old_path: str, new_path: str) -> Dict[str, Any]:
        """Renames a file (Level 2)."""
        return cls.move_file(old_path, new_path)

    @classmethod
    def delete_file(cls, target_path: str, skip_permission: bool = False) -> Dict[str, Any]:
        """
        Permanently deletes a file or directory (Level 3: EXECUTE).
        Requires explicit permission challenge confirmation.
        """
        if not cls._is_path_safe(target_path):
            return {"success": False, "error": "Access to restricted system directory denied."}

        if not os.path.exists(target_path):
            return {"success": False, "error": f"Path '{target_path}' does not exist."}

        # Level 3 Permission Interceptor
        if not skip_permission:
            allowed, reason, challenge = permission_engine.evaluate_request(
                tool_name="file_ops.delete_file",
                permission_level=3,
                target_resource=target_path,
                arguments={"target_path": target_path}
            )
            if not allowed:
                return {
                    "success": False,
                    "awaiting_approval": True,
                    "challenge": challenge,
                    "message": reason
                }

        try:
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
            else:
                os.remove(target_path)
            return {"success": True, "deleted_path": target_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def organize_directory(cls, folder_path: str) -> Dict[str, Any]:
        """
        Organizes a folder (e.g. Downloads or Desktop) into categorized subfolders (Level 2).
        """
        if not cls._is_path_safe(folder_path):
            return {"success": False, "error": "Access to restricted system directory denied."}

        norm_folder = os.path.abspath(os.path.expanduser(folder_path))
        if not os.path.exists(norm_folder) or not os.path.isdir(norm_folder):
            return {"success": False, "error": f"Folder '{folder_path}' does not exist."}

        moved_files = []
        for item in os.listdir(norm_folder):
            item_path = os.path.join(norm_folder, item)
            if os.path.isdir(item_path):
                continue  # Skip existing folders

            _, ext = os.path.splitext(item)
            ext = ext.lower()

            target_subfolder = "Other"
            for category, extensions in cls.ORGANIZATION_MAP.items():
                if ext in extensions:
                    target_subfolder = category
                    break

            if target_subfolder != "Other":
                cat_dir = os.path.join(norm_folder, target_subfolder)
                os.makedirs(cat_dir, exist_ok=True)
                dest = os.path.join(cat_dir, item)
                try:
                    shutil.move(item_path, dest)
                    moved_files.append({"file": item, "category": target_subfolder})
                except Exception as e:
                    logger.warning(f"Could not move '{item}': {e}")

        return {
            "success": True,
            "organized_folder": norm_folder,
            "moved_count": len(moved_files),
            "details": moved_files
        }
