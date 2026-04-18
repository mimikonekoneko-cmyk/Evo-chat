import re
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, List
from sqlalchemy.orm import Session
from app.models import User, LongTermMemory, ChatMessage

MEMORY_TAG_PATTERN = re.compile(r'#memory\s+(.+)')
MAX_CONTEXT_LENGTH = 1000  # プロンプトに流す記憶や履歴の最大文字数を制限

def sanitize_prompt_input(text: str) -> str:
    """プロンプトインジェクションを防ぐため、入力テキストをサニタイズする"""
    # 制御文字、不要な改行、特殊なマークダウン文字などを制限的に除去
    text = text.replace('{', '(').replace('}', ')')
    text = text.replace('\n', ' ').strip()
    return text[:MAX_CONTEXT_LENGTH]

def handle_long_term_memory(db_session: Session, user: User, user_message: str) -> Tuple[str, bool]:
    """
    ユーザーメッセージから #memory タグを検出し、長期記憶としてDBに保存する。
    メッセージからはタグと内容を除去して返す。

    Args:
        db_session: SQLAlchemyのセッション。
        user: 対象のUserオブジェクト。
        user_message: ユーザーからの生のメッセージ。

    Returns:
        タプル (cleaned_message, memory_added)。
        cleaned_message: タグが除去されサニタイズされたメッセージ。
        memory_added: 記憶が追加されたかどうかを示すブール値。
    """
    match = MEMORY_TAG_PATTERN.search(user_message)
    if match:
        memory_content = sanitize_prompt_input(match.group(1)) # サニタイズ
        new_memory = LongTermMemory(user_id=user.id, content=memory_content)
        db_session.add(new_memory)
        
        # メッセージから #memory タグ全体を削除
        cleaned_message = MEMORY_TAG_PATTERN.sub('', user_message).strip()
        return sanitize_prompt_input(cleaned_message), True
    
    return sanitize_prompt_input(user_message), False

def get_context(user: User) -> Dict[str, Any]:
    """
    AIの応答生成に必要なコンテキスト（長期記憶、時間情報、会話履歴）を整形して返す。
    """
    # 1. 長期記憶の取得と整形
    memories = user.long_term_memories
    if memories:
        # DBから取得した記憶もサニタイズ
        formatted_memories = "Memories:\n" + "\n".join(f"- {sanitize_prompt_input(mem.content)}" for mem in memories)
    else:
        formatted_memories = "No long-term memories yet."

    # 2. 時間情報の取得と整形
    now = datetime.now(timezone.utc)
    time_context_parts = [f"Current date and time is {now.strftime('%Y-%m-%d %H:%M')}."]
    formatted_time_context = " ".join(time_context_parts)

    # 3. 会話履歴の取得と整形 (直近10件など)
    recent_messages = ChatMessage.query.filter_by(user_id=user.id).order_by(ChatMessage.id.desc()).limit(10).all()
    recent_messages.reverse() # 時系列順に戻す
    
    chat_history = [
        {'role': msg.role if msg.role == 'user' else 'model', 'parts': [sanitize_prompt_input(msg.content)]}
        for msg in recent_messages
    ]

    return {
        "long_term_memories": formatted_memories,
        "time_context": formatted_time_context,
        "chat_history": chat_history,
        "long_term_memories": formatted_memories,
        "time_context": formatted_time_context,
        "chat_history": chat_history
    }
