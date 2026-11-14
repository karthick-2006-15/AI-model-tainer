"""
Tier 4: Personal Profile & Entity Knowledge Graph Engine
Maintains verified user facts, preferences, academic info, and project history with provenance and confidence scores.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from storage.db.connection import SessionLocal
from storage.db.models import MemoryEntity
from core.memory.semantic import semantic_memory

logger = logging.getLogger("jarvis.memory.profile")


class ProfileMemory:
    VALID_CATEGORIES = [
        "preference",
        "academic",
        "project",
        "work",
        "app",
        "decision",
        "task",
        "general"
    ]

    def add_or_update_fact(
        self,
        key_name: str,
        category: str,
        value_data: Any,
        confidence_score: float = 1.0,
        provenance: str = "user_explicit"
    ) -> Dict[str, Any]:
        """
        Adds or updates a structured memory entity.
        Automatically updates both SQLite and Semantic Vector memory.
        """
        cat = category.lower() if category.lower() in self.VALID_CATEGORIES else "general"
        val = value_data if isinstance(value_data, dict) else {"text": str(value_data)}

        with SessionLocal() as db:
            entity = (
                db.query(MemoryEntity)
                .filter(MemoryEntity.key_name == key_name)
                .first()
            )

            if entity:
                entity.value_data = val
                entity.category = cat
                entity.confidence_score = confidence_score
                entity.provenance = provenance
                entity.is_active = True
                db.commit()
                db.refresh(entity)
                fact_id = entity.id
                logger.info(f"Updated memory entity '{key_name}' [{cat}]")
            else:
                entity = MemoryEntity(
                    key_name=key_name,
                    category=cat,
                    value_data=val,
                    confidence_score=confidence_score,
                    provenance=provenance,
                    is_active=True
                )
                db.add(entity)
                db.commit()
                db.refresh(entity)
                fact_id = entity.id
                logger.info(f"Created new memory entity '{key_name}' [{cat}]")

            # Sync to Semantic Vector Store for semantic RAG
            text_repr = f"{key_name}: {val.get('text', str(val))}"
            semantic_memory.upsert_memory(
                memory_id=fact_id,
                text=text_repr,
                category=cat,
                metadata={"key_name": key_name, "provenance": provenance}
            )

            return {
                "id": entity.id,
                "key_name": entity.key_name,
                "category": entity.category,
                "value_data": entity.value_data,
                "confidence_score": entity.confidence_score,
                "provenance": entity.provenance
            }

    def get_fact(self, key_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific fact by key name."""
        with SessionLocal() as db:
            entity = (
                db.query(MemoryEntity)
                .filter(MemoryEntity.key_name == key_name, MemoryEntity.is_active == True)
                .first()
            )
            if not entity:
                return None
            return {
                "id": entity.id,
                "key_name": entity.key_name,
                "category": entity.category,
                "value_data": entity.value_data,
                "confidence_score": entity.confidence_score,
                "provenance": entity.provenance
            }

    def list_facts(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists active facts, optionally filtered by category."""
        with SessionLocal() as db:
            query = db.query(MemoryEntity).filter(MemoryEntity.is_active == True)
            if category:
                query = query.filter(MemoryEntity.category == category.lower())
            
            entities = query.order_by(MemoryEntity.category, MemoryEntity.key_name).all()
            return [
                {
                    "id": e.id,
                    "key_name": e.key_name,
                    "category": e.category,
                    "value_data": e.value_data,
                    "confidence_score": e.confidence_score,
                    "provenance": e.provenance,
                    "created_at": e.created_at.isoformat()
                }
                for e in entities
            ]

    def delete_fact(self, fact_id: str) -> bool:
        """Deletes (or deactivates) a fact from relational and vector memory."""
        with SessionLocal() as db:
            entity = db.query(MemoryEntity).filter(MemoryEntity.id == fact_id).first()
            if not entity:
                return False
            db.delete(entity)
            db.commit()

        # Remove from vector store
        semantic_memory.delete_memory(fact_id)
        logger.info(f"Deleted memory fact '{fact_id}'")
        return True

    def auto_extract_facts_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Heuristic extractor for user statements stating preferences, exams, or projects.
        Examples:
        - "My exam is on Tuesday" -> category: academic, key: exam_schedule
        - "My project is Autonomous Warehouse AI" -> category: project, key: primary_project
        - "I prefer VS Code" -> category: preference, key: preferred_editor
        """
        extracted = []
        cleaned = text.strip()

        # 1. Exam / Academic
        m = re.search(r"\b(?:my\s+)?exam\s+is\s+(?:on\s+)?([a-zA-Z0-9_\-\s]+)", cleaned, re.IGNORECASE)
        if m:
            fact = self.add_or_update_fact(
                key_name="upcoming_examination",
                category="academic",
                value_data={"text": f"Exam scheduled {m.group(1).strip()}"},
                confidence_score=1.0,
                provenance="user_explicit"
            )
            extracted.append(fact)

        # 2. Project
        m = re.search(r"\b(?:my\s+)?project\s+is\s+(?:called\s+)?([a-zA-Z0-9_\-\s]+)", cleaned, re.IGNORECASE)
        if m:
            fact = self.add_or_update_fact(
                key_name="active_project",
                category="project",
                value_data={"text": m.group(1).strip()},
                confidence_score=1.0,
                provenance="user_explicit"
            )
            extracted.append(fact)

        # 3. Preference
        m = re.search(r"\bi\s+prefer\s+([a-zA-Z0-9_\-\s]+)", cleaned, re.IGNORECASE)
        if m:
            item = m.group(1).strip()
            fact = self.add_or_update_fact(
                key_name=f"preferred_{item.replace(' ', '_').lower()}",
                category="preference",
                value_data={"text": item},
                confidence_score=1.0,
                provenance="user_explicit"
            )
            extracted.append(fact)

        return extracted


# Global singleton instance
profile_memory = ProfileMemory()
