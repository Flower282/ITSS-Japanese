import os
import re
import json
import httpx
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from src.models.analysis_models import AnalysisMessage, AnalysisLog, AnalysisConversation, LearningRoute
from src.core.config import settings
from src.core.i18n import _

def get_marked_messages(db: Session):
    """
    Fetch messages from the database where is_marked = 1.
    """
    return db.query(AnalysisMessage).filter(AnalysisMessage.is_marked == 1).all()

def generate_message_analysis_with_groq(db: Session, message_id: int, text: str, conversation_id: int) -> dict:
    """
    Call Groq to analyze a specific message, classify it into "GIAO TIẾP GIÁN TIẾP" or "QUẢN LÝ THỜI GIAN",
    save the category, intent analysis, and reply suggestions to the DB, and return the generated values.
    """
    api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: Missing GROQ_API_KEY")
        return {"category": "GIAO TIẾP GIÁN TIẾP", "intent_analysis": None, "reply_suggestion": None}

    prompt = f"""
Bạn là một trợ lý AI chuyên phân tích văn hóa và phong cách giao tiếp Việt Nam - Nhật Bản trong môi trường công việc IT.

Hãy phân tích câu thoại dưới đây của đối tác:
"{text}"

Nhiệm vụ của bạn:
1. Phân loại câu thoại (category): Phân loại câu thoại này vào MỘT TRONG HAI nhóm duy nhất:
   - "GIAO TIẾP GIÁN TIẾP" (Ví dụ: cách nói giảm nhẹ, do dự, lấp lửng, nói vòng vo, từ chối khéo léo như "để tôi suy nghĩ thêm", "hơi khó một chút").
   - "QUẢN LÝ THỜI GIAN" (Ví dụ: deadline, tiến độ, thời gian bàn giao, ưu tiên công việc, "càng sớm càng tốt", "xử lý ngay").
2. Phân tích ý định thực tế (INTENT_ANALYSIS): Giải thích rõ ý nghĩa thực sự đằng sau câu nói của đối tác (đặc biệt là nếu họ dùng cách nói gián tiếp, giảm nhẹ hoặc lịch sự quá mức của người Nhật).
3. Đề xuất gợi ý cách ứng phó khéo léo (REPLY_SUGGESTION): Đưa ra các câu trả lời gợi ý hoặc hành động tiếp theo cụ thể, lịch sự và phù hợp nhất cho phía Việt Nam.

Yêu cầu định dạng kết quả:
- Chỉ trả về duy nhất một chuỗi JSON hợp lệ. Không sử dụng markdown. Không có text thừa bên ngoài JSON.
- Trả về bằng ngôn ngữ tiếng Việt có dấu đầy đủ, UTF-8.

Cấu trúc JSON bắt buộc:
{{
  "category": "GIAO TIẾP GIÁN TIẾP" hoặc "QUẢN LÝ THỜI GIAN",
  "intent_analysis": "Ý nghĩa thực tế đằng sau câu nói...",
  "reply_suggestion": "Đề xuất cách phản hồi khéo léo..."
}}
"""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    "messages": [
                        {
                            "role": "system",
                            "content": "Bạn là AI chuyên phân tích ý nghĩa và sắc thái giao tiếp Việt Nam - Nhật Bản. Luôn trả lời JSON hợp lệ bằng tiếng Việt.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    "temperature": 0.2,
                },
            )
            
        if response.status_code >= 400:
            print(f"Groq API error: {response.text}")
            return {"category": "GIAO TIẾP GIÁN TIẾP", "intent_analysis": None, "reply_suggestion": None}
            
        content = response.json()["choices"][0]["message"]["content"].strip()
        
        # Clean markdown if present
        if content.startswith("```"):
            content = re.sub(r"^```json", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"^```", "", content).strip()
            content = re.sub(r"```$", "", content).strip()
            
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            category = parsed.get("category")
            intent = parsed.get("intent_analysis")
            reply = parsed.get("reply_suggestion")
            
            # Normalize category
            if category:
                category = category.strip().upper()
                if "THỜI GIAN" in category or "TIME" in category or "QUẢN LÝ THỜI GIAN" in category or "QUAN LY THOI GIAN" in category:
                    category = "QUẢN LÝ THỜI GIAN"
                else:
                    category = "GIAO TIẾP GIÁN TIẾP"
            else:
                category = "GIAO TIẾP GIÁN TIẾP"

            # Save CATEGORY to DB
            db_category = AnalysisLog(
                message_id=message_id,
                conversation_id=conversation_id,
                ai_task_type="CATEGORY",
                output_text=category,
                created_at=datetime.utcnow()
            )
            db.add(db_category)
            
            # Save INTENT_ANALYSIS to DB
            if intent:
                db_intent = AnalysisLog(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    ai_task_type="INTENT_ANALYSIS",
                    output_text=intent,
                    created_at=datetime.utcnow()
                )
                db.add(db_intent)
                
            # Save REPLY_SUGGESTION to DB
            if reply:
                reply_text = json.dumps(reply, ensure_ascii=False) if isinstance(reply, (list, dict)) else str(reply)
                db_reply = AnalysisLog(
                    message_id=message_id,
                    conversation_id=conversation_id,
                    ai_task_type="REPLY_SUGGESTION",
                    output_text=reply_text,
                    created_at=datetime.utcnow()
                )
                db.add(db_reply)
                
            db.commit()
            
            return {
                "category": category,
                "intent_analysis": intent,
                "reply_suggestion": reply
            }
    except Exception as e:
        print(f"Error calling Groq or saving: {e}")
        
    return {"category": "GIAO TIẾP GIÁN TIẾP", "intent_analysis": None, "reply_suggestion": None}

def get_marked_messages_with_analysis(db: Session) -> List[dict]:
    """
    Fetch all marked messages. If they don't have CATEGORY, INTENT_ANALYSIS or REPLY_SUGGESTION logs,
    dynamically generate them using Groq and save to DB, then return.
    """
    marked_msgs = get_marked_messages(db)
    results = []
    
    for msg in marked_msgs:
        if msg.message_id is None:
            continue
            
        # Try to fetch existing logs
        logs = db.query(AnalysisLog).filter(AnalysisLog.message_id == msg.message_id).all()
        
        category_log = next((l for l in logs if l.ai_task_type == "CATEGORY"), None)
        intent_log = next((l for l in logs if l.ai_task_type == "INTENT_ANALYSIS"), None)
        reply_log = next((l for l in logs if l.ai_task_type == "REPLY_SUGGESTION"), None)
        
        category_val = category_log.output_text if category_log else None
        intent_val = intent_log.output_text if intent_log else None
        reply_val = reply_log.output_text if reply_log else None
        
        # If any log is missing, trigger Groq dynamic generation!
        if not category_val or not intent_val or not reply_val:
            generated = generate_message_analysis_with_groq(
                db=db,
                message_id=msg.message_id,
                text=msg.text,
                conversation_id=msg.conversation_id
            )
            category_val = category_val or generated.get("category")
            intent_val = intent_val or generated.get("intent_analysis")
            reply_val = reply_val or generated.get("reply_suggestion")
            
        # Clean up JSON list if reply_val is stored as list JSON
        if reply_val:
            try:
                parsed = json.loads(reply_val)
                if isinstance(parsed, list):
                    reply_val = " / ".join(parsed)
            except Exception:
                pass

        if intent_val:
            try:
                parsed = json.loads(intent_val)
                if isinstance(parsed, list):
                    intent_val = " / ".join(parsed)
            except Exception:
                pass
                
        results.append({
            "phrase": msg.text,
            "category": category_val or "GIAO TIẾP GIÁN TIẾP",
            "meaning": intent_val,
            "response": reply_val
        })
        
    return results


def get_culture_assistant_insight(db: Session, lang: str, force_refresh: bool = False) -> str:
    """
    Get dynamic AI Culture Assistant insight based on the Vietnamese user's messages.
    If cached in ai_log with ai_task_type = 'CULTURAL_INSIGHT', return it (unless force_refresh is True).
    """
    # 1. Check for recent conversation to get a valid conversation_id
    latest_conv = db.query(AnalysisConversation).order_by(AnalysisConversation.created_at.desc()).first()
    if not latest_conv:
        # Fallback to hardcoded string if no conversations exist
        return _('ai_culture_insight', lang)
        
    conv_id = latest_conv.conversation_id
    
    # 2. Check if already cached in DB (ai_log)
    if not force_refresh:
        cached_log = db.query(AnalysisLog).filter(
            AnalysisLog.ai_task_type == "CULTURAL_INSIGHT"
        ).order_by(AnalysisLog.created_at.desc()).first()
        if cached_log and cached_log.output_text:
            return cached_log.output_text

    # 3. Fetch all messages written by the Vietnamese user (user_id is not null)
    # Filter non-deleted messages
    messages = db.query(AnalysisMessage).filter(
        AnalysisMessage.user_id != None,
        AnalysisMessage.is_deleted == False
    ).order_by(AnalysisMessage.created_at.asc()).all()

    if not messages:
        # Fallback if no messages yet
        return _('ai_culture_insight', lang)

    # 4. Clean and format the messages for the prompt
    formatted_list = []
    for msg in messages:
        text = msg.text
        # Clean JSON strings if any
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = parsed.get("text") or parsed.get("translation") or text
        except Exception:
            pass
        formatted_list.append(f"- {text}")

    formatted_messages = "\n".join(formatted_list[-30:]) # Use latest 30 messages to avoid prompt overflow

    # 5. Formulate prompt depending on language
    api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: Missing GROQ_API_KEY for dynamic insight generation.")
        return _('ai_culture_insight', lang)

    system_prompt = (
        "Bạn là chuyên gia tư vấn văn hóa và phong cách giao tiếp Việt - Nhật trong môi trường IT startup."
    )
    prompt = f"""
Dưới đây là lịch sử các tin nhắn tiếng Nhật/phát ngôn của lập trình viên người Việt trong công việc:
{formatted_messages}

Nhiệm vụ của bạn:
1. Phân tích các tin nhắn trên và phát hiện xu hướng sử dụng tiếng Nhật hoặc phong cách giao tiếp CHƯA TỐT, chưa tự nhiên hoặc chưa thực sự phù hợp với văn hóa làm việc Nhật Bản (ví dụ: lạm dụng kính ngữ quá mức gây xa cách, lạm dụng từ xin lỗi 'Sumimasen', dịch thô từ tiếng Việt nghe không tự nhiên, nói nước đôi hoặc không cam kết thời gian rõ ràng, v.v.).
2. Viết một đoạn nhận xét/lời khuyên ngắn gọn bằng tiếng Việt (khoảng 2-3 câu) giúp lập trình viên này nhận ra điểm hạn chế đó để cải thiện bản thân tốt hơn.

Yêu cầu:
- Trả về duy nhất đoạn nhận xét trực tiếp bằng tiếng Việt có dấu.
- Không thêm tiêu đề, không có markdown bọc bên ngoài, không có lời dẫn dắt hay ký tự đặc biệt thừa thãi nào.
"""

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    "temperature": 0.3,
                },
            )
            
        if response.status_code >= 400:
            print(f"Groq API error when generating cultural insight: {response.text}")
            return _('ai_culture_insight', lang)
            
        content = response.json()["choices"][0]["message"]["content"].strip()
        
        # Save cache to db
        db_log = AnalysisLog(
            conversation_id=conv_id,
            ai_task_type="CULTURAL_INSIGHT",
            output_text=content,
            created_at=datetime.utcnow()
        )
        db.add(db_log)
        db.commit()
        
        return content
    except Exception as e:
        print(f"Error generating dynamic cultural insight: {e}")
        return _('ai_culture_insight', lang)


def get_user_learning_roadmap(db: Session, user_id: int = 4, force_refresh: bool = False) -> str:
    """
    Fetch or generate a personalized markdown learning roadmap specifically for a user (defaults to user_id=4).
    Saves and caches the generated roadmap in the `learning_route` table.
    """
    # 1. Check if already cached in DB table `learning_route`
    if not force_refresh:
        cached_route = db.query(LearningRoute).filter(
            LearningRoute.user_id == user_id
        ).order_by(LearningRoute.created_at.desc()).first()
        
        if cached_route and cached_route.route_text:
            return cached_route.route_text

    # 2. Fetch all messages written by this user
    messages = db.query(AnalysisMessage).filter(
        AnalysisMessage.user_id == user_id,
        AnalysisMessage.is_deleted == False
    ).order_by(AnalysisMessage.created_at.asc()).all()

    formatted_list = []
    for msg in messages:
        text = msg.text
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                text = parsed.get("text") or parsed.get("translation") or text
        except Exception:
            pass
        formatted_list.append(f"- {text}")

    formatted_messages = "\n".join(formatted_list[-30:]) # Use latest 30 messages

    # Default fallback if no messages are found
    if not messages:
        fallback_text = (
            "### Lộ trình học tập giao tiếp tiếng Nhật\n\n"
            "Chưa có đủ lịch sử tin nhắn của bạn để phân tích cá nhân hóa. Dưới đây là khuyến nghị chung:\n\n"
            "1. **Tập trung vào phản hồi tự nhiên**: Luyện tập sử dụng kính ngữ cơ bản thay vì dịch thô từ tiếng Việt.\n"
            "2. **Làm rõ cam kết công việc**: Hạn chế nói do dự 'sẽ cố gắng' mà dùng các mốc thời gian cụ thể.\n"
            "3. **Tự nhiên hóa câu văn**: Học các cụm từ bản xứ chuyên biệt cho IT startup."
        )
        return fallback_text

    # 3. Formulate the Groq prompt
    api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: Missing GROQ_API_KEY for dynamic roadmap generation.")
        return "### Lộ trình học tập cá nhân hóa\n\nKhông có API key của Groq để khởi tạo lộ trình lúc này."

    system_prompt = (
        "Bạn là chuyên gia tư vấn văn hóa và phong cách giao tiếp Việt - Nhật trong môi trường công nghệ IT startup."
    )
    prompt = f"""
Dưới đây là danh sách các tin nhắn/phát ngôn tiếng Nhật của lập trình viên Việt Nam có ID {user_id}:
{formatted_messages}

Hãy phân tích phong cách viết và các điểm chưa tốt của họ (ví dụ: dùng sai kính ngữ, lạm dụng từ xin lỗi, diễn đạt thiếu cam kết, dịch thô cứng, v.v.).
Dựa trên phân tích đó, hãy soạn thảo một **LỘ TRÌNH HỌC TẬP GIAO TIẾP CÁ NHÂN HÓA** chi tiết bằng **tiếng Việt**, định dạng **Markdown** sạch sẽ và trực quan.

Lộ trình cần bao gồm:
1. **Phân tích tổng quan**: Nhận xét ngắn gọn về xu hướng sử dụng tiếng Nhật hiện tại của họ qua tin nhắn.
2. **Kế hoạch cải thiện chi tiết gồm 3 bước hành động cụ thể**:
   - **Bước 1**: Tập trung khắc phục điểm yếu lớn nhất (kèm giải thích hành động luyện tập và ví dụ đối sánh thực hành cụ thể).
   - **Bước 2**: Tự nhiên hóa biểu đạt (kèm hành động và ví dụ).
   - **Bước 3**: Chuyên nghiệp hóa phong cách giao tiếp IT (kèm hành động và ví dụ).

Yêu cầu định dạng:
- Trả về nội dung trực tiếp bằng tiếng Việt chuẩn Markdown.
- Không bọc trong code block (không dùng ```markdown), không thêm tiêu đề hay lời dẫn dắt thừa thãi nào ngoài nội dung lộ trình.
"""

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json={
                    "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    "temperature": 0.3,
                },
            )
            
        if response.status_code >= 400:
            print(f"Groq API error when generating roadmap: {response.text}")
            return "### Lộ trình học tập cá nhân hóa\n\nGặp lỗi khi kết nối API Groq để phân tích lộ trình."
            
        content = response.json()["choices"][0]["message"]["content"].strip()
        
        # Clean markdown wrappers if returned
        if content.startswith("```"):
            content = re.sub(r"^```markdown", "", content, flags=re.IGNORECASE).strip()
            content = re.sub(r"^```", "", content).strip()
            content = re.sub(r"```$", "", content).strip()
            
        # 4. Save cache to `learning_route` table
        db_route = LearningRoute(
            user_id=user_id,
            route_text=content,
            created_at=datetime.utcnow()
        )
        db.add(db_route)
        db.commit()
        
        return content
    except Exception as e:
        print(f"Error generating dynamic learning roadmap: {e}")
        return "### Lộ trình học tập cá nhân hóa\n\nGặp sự cố hệ thống khi tạo lộ trình."


# Unused/broken models in database schema:
# from src.models.analysis_models import CulturalAssistant, RealSituationAnalysis
# def get_cultural_assistant_recommendations(db: Session, user_id: int):
#     return db.query(CulturalAssistant).filter(CulturalAssistant.user_id == user_id).all()
# def get_real_situation_analysis(db: Session, user_id: int):
#     return db.query(RealSituationAnalysis).filter(RealSituationAnalysis.user_id == user_id).all()