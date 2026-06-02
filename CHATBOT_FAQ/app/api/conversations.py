import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from app.retrieval.retriever import retrieve_context
from app.retrieval.structured_lookup import (
	lookup_certificate_mapping,
	format_structured_certificate_answer,
)
from app.llm.client import generate_answer


router = APIRouter(prefix="/api", tags=["conversations"])


class CreateConversationRequest(BaseModel):
	title: Optional[str] = None


class ConversationResponse(BaseModel):
	id: str
	user_id: int
	title: str
	created_at: str
	updated_at: str


class CreateMessageRequest(BaseModel):
	content: str


class MessageResponse(BaseModel):
	id: str
	conversation_id: str
	role: str
	content: str
	created_at: str


class CreateMessageResponse(BaseModel):
	answer: str
	conversation_id: str


class UpdateTitleRequest(BaseModel):
	title: str


def _get_db_path() -> Path:
	base_dir = Path(__file__).resolve().parents[2]
	db_path = os.getenv("CHAT_DB_PATH", "data/indexes/chat_db.sqlite3")
	return (base_dir / db_path).resolve()


_schema_lock = threading.Lock()
_schema_initialized = False


def _get_conn() -> sqlite3.Connection:
	conn = sqlite3.connect(_get_db_path(), timeout=30)
	conn.row_factory = sqlite3.Row
	conn.execute("PRAGMA foreign_keys = ON;")
	conn.execute("PRAGMA busy_timeout = 30000;")
	_ensure_schema_once(conn)
	return conn


def _ensure_schema_once(conn: sqlite3.Connection) -> None:
	global _schema_initialized
	if _schema_initialized:
		return
	with _schema_lock:
		if _schema_initialized:
			return
		_ensure_schema(conn)
		_schema_initialized = True


def _ensure_schema(conn: sqlite3.Connection) -> None:
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS conversations (
			id TEXT PRIMARY KEY,
			user_id INTEGER NOT NULL,
			title TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			updated_at TEXT NOT NULL DEFAULT (datetime('now'))
		);
		"""
	)
	conn.execute(
		"""
		CREATE TABLE IF NOT EXISTS messages (
			id TEXT PRIMARY KEY,
			conversation_id TEXT NOT NULL,
			role TEXT NOT NULL,
			content TEXT NOT NULL,
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
		);
		"""
	)


def _require_user_id(x_user_id: Optional[str]) -> int:
	if not x_user_id or not x_user_id.isdigit():
		raise HTTPException(status_code=400, detail="Missing or invalid X-User-Id header")
	return int(x_user_id)


def select_llm_contexts(question: str, contexts: list[str], sources: list[dict]):
	q = question.lower()
	pairs = list(zip(contexts, sources))

	if not pairs:
		return [], []

	# 1) Nhóm quy đổi chứng chỉ: ưu tiên đúng bảng chứng chỉ quốc tế
	if any(k in q for k in ["ielts", "toeic", "toefl", "hsk", "topik", "jlpt", "quy đổi"]):
		filtered = []
		for ctx, src in pairs:
			file_name = (src.get("file") or "").lower()
			ctx_lower = ctx.lower()
			score = 0

			if "ngoại ngữ quốc tế" in file_name:
				score += 100

			if "ielts" in q and "ielts" in ctx_lower:
				score += 120
			if "toeic" in q and "toeic" in ctx_lower:
				score += 120
			if "toefl" in q and "toefl" in ctx_lower:
				score += 120
			if "hsk" in q and "hsk" in ctx_lower:
				score += 120
			if "topik" in q and "topik" in ctx_lower:
				score += 120
			if "jlpt" in q and "jlpt" in ctx_lower:
				score += 120

			if "điểm quy đổi" in ctx_lower:
				score += 80
			if "loại chứng chỉ quốc tế" in ctx_lower:
				score += 60

			if "xếp lớp tiếng anh" in file_name:
				score -= 150

			if "điều kiện chứng chỉ được công nhận quy đổi" in ctx_lower:
				score -= 100

			filtered.append((score, ctx, src))

		filtered.sort(key=lambda x: x[0], reverse=True)

		if filtered:
			best_ctx = filtered[0][1]
			best_src = filtered[0][2]
			return [best_ctx], [best_src]

		return [pairs[0][0]], [pairs[0][1]]

	# 2) Nhóm thủ tục: ưu tiên hồ sơ, điều kiện, bước
	if any(k in q for k in ["nghỉ học", "thực tập", "khóa luận", "đăng ký", "chuyển ngành", "chuyển trường", "tốt nghiệp"]):
		scored = []
		for ctx, src in pairs:
			section = (ctx.splitlines()[0] if ctx else "").lower()
			score = 0

			if "hồ sơ" in ctx.lower():
				score += 50
			if "điều kiện" in ctx.lower():
				score += 40
			if "bước" in ctx.lower():
				score += 30
			if "hướng dẫn" in ctx.lower():
				score += 20
			if "mẫu đơn" in ctx.lower():
				score += 10
			if "hồ sơ" in section:
				score += 10
			if "điều kiện" in section:
				score += 10

			scored.append((score, ctx, src))

		scored.sort(key=lambda x: x[0], reverse=True)
		top = scored[:2]
		return [x[1] for x in top], [x[2] for x in top]

	# 3) Mặc định
	return contexts[:2], sources[:2]


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(req: CreateConversationRequest, x_user_id: Optional[str] = Header(default=None)):
	user_id = _require_user_id(x_user_id)
	conversation_id = str(uuid4())
	title = req.title or "Cuộc trò chuyện mới"

	with _get_conn() as conn:
		conn.execute(
			"""
			INSERT INTO conversations (id, user_id, title)
			VALUES (?, ?, ?)
			""",
			(conversation_id, user_id, title),
		)
		row = conn.execute(
			"SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?",
			(conversation_id,),
		).fetchone()

	return ConversationResponse(**dict(row))


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(x_user_id: Optional[str] = Header(default=None)):
	user_id = _require_user_id(x_user_id)

	with _get_conn() as conn:
		rows = conn.execute(
			"""
			SELECT id, user_id, title, created_at, updated_at
			FROM conversations
			WHERE user_id = ?
			ORDER BY updated_at DESC
			""",
			(user_id,),
		).fetchall()

	return [ConversationResponse(**dict(row)) for row in rows]


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, x_user_id: Optional[str] = Header(default=None)):
	user_id = _require_user_id(x_user_id)

	with _get_conn() as conn:
		row = conn.execute(
			"SELECT id FROM conversations WHERE id = ? AND user_id = ?",
			(conversation_id, user_id),
		).fetchone()
		if not row:
			raise HTTPException(status_code=404, detail="Conversation not found")

		conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


@router.post("/conversations/{conversation_id}/messages", response_model=CreateMessageResponse)
def create_message(
	conversation_id: str,
	req: CreateMessageRequest,
	x_user_id: Optional[str] = Header(default=None),
):
	user_id = _require_user_id(x_user_id)

	with _get_conn() as conn:
		conv = conn.execute(
			"SELECT id FROM conversations WHERE id = ? AND user_id = ?",
			(conversation_id, user_id),
		).fetchone()
		if not conv:
			raise HTTPException(status_code=404, detail="Conversation not found")

		user_message_id = str(uuid4())
		assistant_message_id = str(uuid4())

		conn.execute(
			"""
			INSERT INTO messages (id, conversation_id, role, content)
			VALUES (?, ?, ?, ?)
			""",
			(user_message_id, conversation_id, "user", req.content),
		)

		structured_result = lookup_certificate_mapping(req.content)
		if structured_result:
			answer = format_structured_certificate_answer(structured_result)
		else:
			docs = retrieve_context(req.content, k=5)
			sources = []
			contexts = []

			for doc in docs:
				source_item = {
					"file": doc.metadata.get("filename"),
					"source_file": doc.metadata.get("source_file"),
					"page": doc.metadata.get("page"),
					"category": doc.metadata.get("category"),
					"sub_category": doc.metadata.get("sub_category"),
					"id": doc.metadata.get("id"),
				}
				sources.append(source_item)
				contexts.append(doc.page_content)

			llm_contexts, llm_sources = select_llm_contexts(req.content, contexts, sources)
			answer = generate_answer(req.content, llm_contexts, llm_sources)

		conn.execute(
			"""
			INSERT INTO messages (id, conversation_id, role, content)
			VALUES (?, ?, ?, ?)
			""",
			(assistant_message_id, conversation_id, "assistant", answer),
		)
		conn.execute(
			"""
			UPDATE conversations
			SET updated_at = ?
			WHERE id = ?
			""",
			(datetime.utcnow().isoformat(timespec="seconds"), conversation_id),
		)

	return CreateMessageResponse(answer=answer, conversation_id=conversation_id)


@router.post("/messages", response_model=CreateMessageResponse)
def create_message_auto(req: CreateMessageRequest, x_user_id: Optional[str] = Header(default=None)):
	user_id = _require_user_id(x_user_id)
	conversation_id = str(uuid4())
	default_title = "Cuộc trò chuyện mới"

	with _get_conn() as conn:
		conn.execute(
			"""
			INSERT INTO conversations (id, user_id, title)
			VALUES (?, ?, ?)
			""",
			(conversation_id, user_id, default_title),
		)

		user_message_id = str(uuid4())
		assistant_message_id = str(uuid4())

		conn.execute(
			"""
			INSERT INTO messages (id, conversation_id, role, content)
			VALUES (?, ?, ?, ?)
			""",
			(user_message_id, conversation_id, "user", req.content),
		)

		structured_result = lookup_certificate_mapping(req.content)
		if structured_result:
			answer = format_structured_certificate_answer(structured_result)
		else:
			docs = retrieve_context(req.content, k=5)
			sources = []
			contexts = []

			for doc in docs:
				source_item = {
					"file": doc.metadata.get("filename"),
					"source_file": doc.metadata.get("source_file"),
					"page": doc.metadata.get("page"),
					"category": doc.metadata.get("category"),
					"sub_category": doc.metadata.get("sub_category"),
					"id": doc.metadata.get("id"),
				}
				sources.append(source_item)
				contexts.append(doc.page_content)

			llm_contexts, llm_sources = select_llm_contexts(req.content, contexts, sources)
			answer = generate_answer(req.content, llm_contexts, llm_sources)

		conn.execute(
			"""
			INSERT INTO messages (id, conversation_id, role, content)
			VALUES (?, ?, ?, ?)
			""",
			(assistant_message_id, conversation_id, "assistant", answer),
		)
		conn.execute(
			"""
			UPDATE conversations
			SET updated_at = ?
			WHERE id = ?
			""",
			(datetime.utcnow().isoformat(timespec="seconds"), conversation_id),
		)

	return CreateMessageResponse(answer=answer, conversation_id=conversation_id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(conversation_id: str, x_user_id: Optional[str] = Header(default=None)):
	user_id = _require_user_id(x_user_id)

	with _get_conn() as conn:
		conv = conn.execute(
			"SELECT id FROM conversations WHERE id = ? AND user_id = ?",
			(conversation_id, user_id),
		).fetchone()
		if not conv:
			raise HTTPException(status_code=404, detail="Conversation not found")

		rows = conn.execute(
			"""
			SELECT id, conversation_id, role, content, created_at
			FROM messages
			WHERE conversation_id = ?
			ORDER BY created_at ASC
			""",
			(conversation_id,),
		).fetchall()

	return [MessageResponse(**dict(row)) for row in rows]


@router.patch("/conversations/{conversation_id}/title", response_model=ConversationResponse)
def update_title(
	conversation_id: str,
	req: UpdateTitleRequest,
	x_user_id: Optional[str] = Header(default=None),
):
	user_id = _require_user_id(x_user_id)

	with _get_conn() as conn:
		row = conn.execute(
			"SELECT id FROM conversations WHERE id = ? AND user_id = ?",
			(conversation_id, user_id),
		).fetchone()
		if not row:
			raise HTTPException(status_code=404, detail="Conversation not found")

		conn.execute(
			"""
			UPDATE conversations
			SET title = ?, updated_at = ?
			WHERE id = ?
			""",
			(req.title, datetime.utcnow().isoformat(timespec="seconds"), conversation_id),
		)

		updated = conn.execute(
			"SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE id = ?",
			(conversation_id,),
		).fetchone()

	return ConversationResponse(**dict(updated))
