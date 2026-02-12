"""
Memoria conversacional en RAM pura.
100% Python estándar, sin dependencias de LangChain.
"""

from collections import deque
from typing import List, Dict, Any, Optional
from datetime import datetime


class RAMConversationMemory:
    """
    Memoria conversacional en RAM.
    Almacena mensajes en memoria volátil.
    No persiste en disco ni base de datos.
    """
    
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages * 2
        self.messages = deque(maxlen=self.max_messages)
        self.session_id = None
        self.created_at = datetime.now()
        self.last_accessed = datetime.now()
    
    def add_user_message(self, content: str) -> None:
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_accessed = datetime.now()
    
    def add_ai_message(self, content: str) -> None:
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_accessed = datetime.now()
    
    def get_messages(self) -> List[Dict[str, str]]:
        self.last_accessed = datetime.now()
        return list(self.messages)
    
    def get_recent_messages(self, n: int = 5) -> List[Dict[str, str]]:
        self.last_accessed = datetime.now()
        return list(self.messages)[-n*2:] if len(self.messages) > n*2 else list(self.messages)
    
    def get_context_string(self, n: int = 5) -> str:
        recent = self.get_recent_messages(n)
        lines = []
        for msg in recent:
            prefix = "Usuario:" if msg["role"] == "user" else "Asistente:"
            lines.append(f"{prefix} {msg['content']}")
        return "\n".join(lines)
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.messages),
            "user_messages": sum(1 for m in self.messages if m["role"] == "user"),
            "assistant_messages": sum(1 for m in self.messages if m["role"] == "assistant"),
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "session_id": self.session_id
        }
    
    def clear(self) -> None:
        self.messages.clear()
        self.last_accessed = datetime.now()
    
    def set_session_id(self, session_id: str) -> None:
        self.session_id = session_id
    
    def __len__(self) -> int:
        return len(self.messages)


class SessionMemoryManager:
    """Gestor de memorias por sesión"""
    
    def __init__(self, max_sessions: int = 100, messages_per_session: int = 20):
        self.sessions: Dict[str, RAMConversationMemory] = {}
        self.max_sessions = max_sessions
        self.messages_per_session = messages_per_session
    
    def get_or_create_memory(self, session_id: str) -> RAMConversationMemory:
        if session_id not in self.sessions:
            if len(self.sessions) >= self.max_sessions:
                self._cleanup_oldest()
            
            memory = RAMConversationMemory(max_messages=self.messages_per_session)
            memory.set_session_id(session_id)
            self.sessions[session_id] = memory
        
        return self.sessions[session_id]
    
    def get_memory(self, session_id: str) -> Optional[RAMConversationMemory]:
        return self.sessions.get(session_id)
    
    def delete_memory(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def _cleanup_oldest(self) -> None:
        if not self.sessions:
            return
        oldest_id = min(self.sessions.keys(), 
                       key=lambda sid: self.sessions[sid].last_accessed)
        del self.sessions[oldest_id]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "total_messages": sum(len(m) for m in self.sessions.values())
        }