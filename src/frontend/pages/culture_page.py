from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlencode

from nicegui import ui

from src.core.i18n import _, get_user_language, nav, validate_language_or_default
from src.frontend.api_client import api_get
from src.frontend.components.components import (
    action_button,
    insight_list,
    page_title_block,
    scenario_panel,
    sync_action_bar,
)
from src.frontend.layouts.layout import base_layout
from src.frontend.services.conversation_service import (
    load_conversation_history,
    load_translate_context,
)   
from src.frontend.ui_state import UiState
from src.db.session import get_db_context
from src.repositories.cultural_assistant_repo import (
    get_marked_messages_with_analysis,
    get_culture_assistant_insight,
    get_user_learning_roadmap,
)


FALLBACK_DETAILS = {
    "vn": {
        "Kính ngữ (Keigo)": """
### 1. Tổng quan về Kính ngữ (Keigo - 敬語)
Kính ngữ là hệ thống ngôn ngữ phân cấp đặc trưng trong tiếng Nhật, được sử dụng để thể hiện sự tôn trọng, lịch sự và duy trì khoảng cách xã hội phù hợp giữa những người tham gia giao tiếp. Việc sử dụng kính ngữ phụ thuộc vào tuổi tác, chức vụ, mức độ thân thiết và mối quan hệ "trong - ngoài" (Uchi - Soto).

---

### 2. Phân loại Kính ngữ
Kính ngữ trong tiếng Nhật được chia làm 3 nhóm chính:

#### 1. Lịch sự ngữ (Teineigo - 丁寧語)
- **Đặc điểm:** Là hình thức lịch sự cơ bản nhất, dùng hàng ngày với đồng nghiệp, người mới quen hoặc trong cuộc sống công cộng.
- **Dấu hiệu nhận biết:** Thêm đuôi `です (desu)` sau danh từ/tính từ hoặc `ます (masu)` sau động từ.
- **Ví dụ:** 
  - 行きます (Ikimasu - Đi)
  - 美しいです (Utsukushii desu - Đẹp)

#### 2. Tôn kính ngữ (Sonkeigo - 尊敬語)
- **Đặc điểm:** Dùng để **nâng cao** hành động, trạng thái của đối phương (khách hàng, cấp trên, đối tác) lên nhằm thể hiện sự tôn kính sâu sắc.
- **Quy tắc chuyển đổi:**
  - Thêm tiền tố `お` hoặc `ご` kết hợp với động từ thể liên dụng.
  - Sử dụng các động từ tôn kính đặc biệt (Ví dụ: `irassharu` thay cho `iru`/`kuru`/`iku`).
- **Ví dụ:**
  - 社長が**お帰りになります** (Giám đốc đi về)
  - どちらから**いらっしゃいました**か (Anh/chị đến từ đâu ạ?)

#### 3. Khiêm nhường ngữ (Kenjougo - 謙譲語)
- **Đặc điểm:** Dùng để **hạ thấp** hành động của bản thân hoặc người thuộc nhóm của mình (Uchi) nhằm gián tiếp tôn vinh đối phương lên.
- **Quy tắc chuyển đổi:**
  - Thêm tiền tố `お` hoặc `ご` + động từ + `します`.
  - Sử dụng các động từ khiêm nhường đặc biệt (Ví dụ: `伺います` thay cho `行く`/`nghe`).
- **Ví dụ:**
  - 資料を**お持ちいたします** (Tôi xin phép cầm tài liệu)
  - 明日, オフィスへ**伺います** (Ngày mai tôi sẽ ghé qua văn phòng)

---

### 3. Lưu ý khi dùng Keigo trong môi trường IT Startup
> [!IMPORTANT]
> - **Tránh quá trang trọng:** Trong môi trường startup trẻ trung, năng động, việc lạm dụng Sonkeigo/Kenjougo mức độ cao có thể tạo khoảng cách và làm chậm nhịp độ làm việc.
> - **Tập trung vào sự rõ ràng:** Lịch sự cơ bản `đều dùng desu / masu` kết hợp thái độ cầu thị thường là lựa chọn tối ưu nhất.
""",
        "Phong cách phản hồi": """
### 1. Ý thức duy trì sự hài hòa (Wa - 和)
Trong văn hóa công sở Nhật Bản, sự hòa thuận và nhất trí trong tập thể được đặt lên hàng đầu. Phong cách phản hồi công việc của người Nhật tập trung vào việc bảo vệ thể diện (Mentsu) cho đối phương và tránh gây ra xung đột trực tiếp.

---

### 2. Các quy tắc giao tiếp quan trọng

#### 1. Tránh nói từ chối trực tiếp (Tránh từ "Không")
- Người Nhật cực kỳ hạn chế dùng từ `いいえ (Iie - Không)` vì nó mang cảm giác thô lỗ và cự tuyệt.
- Thay vào đó, họ sẽ dùng các diễn đạt giảm nhẹ, gián tiếp như:
  - **ちょっと難しいです (Chotto muzukashii desu):** Thực tế nghĩa là "Không thể làm được".
  - **検討します (Kentou shimasu) / 考えさせてください (Kangaesete kudasai):** "Để tôi suy nghĩ thêm", thường là một cách từ chối lịch sự.
- **Bài học:** Khi đối tác nói những câu này, hãy chuẩn bị các phương án thay thế thay vì tiếp tục chờ đợi vô ích.

#### 2. Lắng nghe và đồng tình trước khi góp ý (Aizuchi)
- Trong các cuộc họp, hãy liên tục sử dụng các từ đệm biểu thị sự chú ý lắng nghe như `はい (Hai)`, `なるほど (Naruhodo)`, `そうですね (Sou desu ne)`.
- Khi muốn phản biện, hãy áp dụng công thức **"Yes, but..."**: Đồng tình với nỗ lực hoặc ý kiến của họ trước, sau đó mới nhẹ nhàng đưa ra góc nhìn cá nhân bằng từ nối `しかし (Shikashi)` hoặc `ただ (Tada)`.

#### 3. Ý nghĩa thực tế của thời hạn "Càng sớm càng tốt" (Narubeku Hayaku)
- Trong môi trường làm việc Nhật Bản, `なるべく早く (Narubeku hayaku)` hoặc `được thời hạn càng sớm càng tốt` thường không phải là "khi nào rảnh thì làm".
- Nó thực chất mang ý nghĩa **"Ngay lập tức / Ưu tiên tối đa"**. Hãy bắt tay vào làm ngay hoặc chủ động báo cáo khoảng thời gian cụ thể bạn sẽ hoàn thành.

---

### 3. Lời khuyên thực chiến từ AI
> [!TIP]
> Hãy luôn chủ động cập nhật tiến độ công việc (báo cáo trung gian) để tạo sự tin tưởng tuyệt đối với quản lý người Nhật, thay vì chỉ báo cáo khi đã hoàn thành 100% công việc.
""",
        "Văn hóa cảm ơn và xin lỗi": """
### 1. Sức mạnh của lòng biết ơn và sự nhận trách nhiệm
Người Nhật thường xuyên sử dụng lời cảm ơn và xin lỗi không chỉ để biểu thị lòng biết ơn hay nhận sai lầm, mà sâu xa hơn là để bôi trơn các mối quan hệ, giảm bớt căng thẳng và giữ gìn sự hòa hợp chung.

---

### 2. Hướng dẫn sử dụng chi tiết

#### 1. Cảm ơn ngay cả với những sự trợ giúp nhỏ nhất
- Việc nói `ありがとうございます (Arigatou gozaimasu)` với đồng nghiệp hỗ trợ mình (như pha trà, chuẩn bị tài liệu, fix giúp 1 bug nhỏ) được coi là phép lịch sự tối thiểu.
- Việc ghi nhận công sức của người khác giúp tạo ra một môi trường làm việc tích cực và gắn kết.

#### 2. Triết lý xin lỗi đặc trưng
- Đối với người Nhật, lời xin lỗi `すみません (Sumimasen)` hoặc `申し訳ありません (Moushiwake arimasen)` nhiều khi không đồng nghĩa với việc nhận lỗi hoàn toàn về mình.
- Nó thể hiện:
  - **Sự đồng cảm:** "Tôi xin lỗi vì sự cố này đã gây phiền toái/làm mất thời gian của anh/chị".
  - **Sự chu đáo:** Quan tâm đến cảm xúc và khó khăn của người đối diện.
- **Lưu ý cực kỳ quan trọng:** Khi có sự cố, hãy ưu tiên xin lỗi trước để làm dịu bầu không khí, sau đó cùng tập trung phân tích nguyên nhân và đưa ra giải pháp giải quyết triệt để.

#### 3. Cách lựa chọn cụm từ phổ biến
- **ありがとうございます (Arigatou gozaimasu):** Dùng để cảm ơn lịch sự.
- **すみません (Sumimasen):** Dùng cho các lỗi nhỏ, xin lỗi xã giao, hoặc khi làm phiền ai đó (giống như "Excuse me").
- **申し訳ありません (Moushiwake arimasen):** Lời xin lỗi trang trọng, chân thành nhất khi phạm sai lầm nghiêm trọng trong công việc ảnh hưởng đến dự án/khách hàng.

---

### 3. Lời khuyên từ AI
> [!WARNING]
> Tránh lạm dụng từ "Sumimasen" để thay thế cho lời cảm ơn. Nếu đồng nghiệp hỗ trợ bạn nhiệt tình, hãy ưu tiên nói "Arigatou gozaimasu" để họ cảm thấy công sức của mình được trân trọng xứng đáng!
"""
    },
    "jp": {
        "敬語（けいご）": """
### 1. 敬語（けいご）の概要
敬語は日本語特有の階層的な言語システムであり、話し手が聞き手や話題の人物に対して敬意を表すために用いられます。年齢、職務上の地位、親密度、そして「ウチ・ソト」の関係性に基づいて適切に使い分ける必要があります。

---

### 2. 敬語の3大分類

#### 1. 丁寧語（ていねいご）
- **特徴:** 最も基本的な敬語表現であり、同僚や初対面の人、あるいは公の場で日常的に使用されます。
- **表現パターン:** 名詞や形容詞の後に「です」を、動詞の後に「ます」を付けます。
- **例:** 
  - 行きます
  - 美しいです

#### 2. 尊敬語（そんけいご）
- **特徴:** 聞き手や話題の人物（顧客、上司、取引先）の行為や状態を**高めて**表現することで、深い敬意を示します。
- **表現パターン:** 
  - 「お（ご）〜なる」の形をとる。
  - 特別な尊敬動詞を使用する（例：「いる/来る/行く」→「いらっしゃる」）。
- **例:**
  - 社長が**お帰りになります**。
  - どちらから**いらっしゃいました**か。

#### 3. 謙譲語（けんじょうご）
- **特徴:** 話し手自身や身内（ウチ）の行為を**低めて**表現することで、相対的に相手を高く位置づけ、敬意を示します。
- **表現パターン:** 
  - 「お（ご）〜する」の形をとる。
  - 特別な謙譲動詞を使用する（例：「行く/聞く」→「伺う」）。
- **例:**
  - 資料を**お持ちいたします**。
  - 明日、オフィスへ**伺います**。

---

### 3. ITスタートアップでの敬語使用の注意点
> [!IMPORTANT]
> - **過度な敬語の回避:** 若くダイナミックなスタートアップ環境では、過度に丁寧な二重敬語や最高度の敬語は距離感を生み、コミュニケーションのスピードを低下させることがあります。
> - **明確さを重視:** 基本的な「です・ます」調をベースに、前向きでフラットなコミュニケーションを心がけるのが最適です。
""",
        "返答スタイル": """
### 1. 調和（和）を重んじる返答スタイル
日本のビジネス文化では、組織内の調和と合意形成（根回し）が重視されます。相手の面目（メンツ）を保ち、直接的な衝突を避けるための対話スタイルが一般的です。

---

### 2. 重要なコミュニケーションのルール

#### 1. 直接的な否定を避ける（「いいえ」を言わない）
- 日本人は「いいえ」と直接拒絶することを好まず、相手に配慮した間接的な表現を好みます。
- 代表的なクッション言葉や間接表現：
  - **ちょっと難しいです:** 実際には「できません」という意味です。
  - **検討します / 考えさせてください:** 丁寧な断り文句として使われることが多々あります。
- **教訓:** パートナーがこれらの表現を使った場合、単に待つのではなく、別の代替案を用意しアプローチを切り替えましょう。

#### 2. 反論の前にまず同調する（相槌）
- 会話中には常に「はい」「なるほど」「そうですね」といった相槌を打ち、聞いている姿勢を示します。
- 異なる意見を述べたい時は、まず相手の労力や意見を受け入れ（Yes）、その後に「しかし」「ただ」を用いて柔らかく自身の見解を述べます（Yes-But法）。

#### 3. 「なるべく早く」というデッドラインの真意
- 日本の仕事環境における「なるべく早く」や「できるだけ早く」は、「手が空いた時で良い」という意味ではありません。
- 実際には**「最優先で・今すぐに」**処理してほしいという強い意図があります。すぐに作業に着手するか、具体的な完了予定時刻を速やかに報告しましょう。

---

### 3. 実践的なAIのアドバイス
> [!TIP]
> 進捗が100%になるのを待ってから報告するのではなく、進捗が30%や50%の段階で中間報告（ホウレンソウ - 報告・連絡・相談）を行うことで、日本人マネージャーとの信頼関係が劇的に向上します。
""",
        "感謝とお詫びの文化": """
### 1. 感謝と謝罪による調和の維持
日本人は感謝やお詫びの言葉を頻繁に口にします。これは単にお礼を言ったり非を認めたりするだけでなく、関係性を円滑にし、不必要な摩擦を避けてコミュニティの「調和」を維持するための重要なマナーです。

---

### 2. 具体的なガイドライン

#### 1. 小さな支援に対しても感謝を示す
- 資料を用意してくれた、バグの特定を手伝ってくれたなど、どんなに小さなサポートに対しても「ありがとうございます」と声に出して伝えるのが基本です。
- 他者の貢献をオープンに認めることで、ポジティブなチーム環境が築かれます。

#### 2. 日本特有のお詫びの哲学
- ビジネスシーンでの「すみません」や「申し訳ありません」は、必ずしも自分が100%悪いと認めているわけではありません。
- 以下の意味も含まれています：
  - **共感の表明:** 「このトラブルによってお手間をとらせてしまい申し訳ありません」
  - **配慮の表明:** 相手の状況や心情に寄り添う姿勢。
- **最優先事項:** 問題が発生した際は、理由を言い訳する trước khi 謝るのではなく、まず状況に対してお詫びをし、その後迅速に原因調査と対策の議論に移行しましょう。

#### 3. 状況に応じた表現の使い分け
- **ありがとうございます:** 丁寧な感謝の表現。
- **すみません:** 軽いお詫び、クッション言葉、注意を引く際（Excuse me）に使用。
- **申し訳ありません:** 重大なミスを犯した際や、顧客・社外に対して誠心誠意お詫びする際の最もフォーマルな表現。

---

### 3. AIからのアドバイス
> [!WARNING]
> 感謝の代わりに「すみません」を使いすぎるのを避けましょう。同僚が親身になって助けてくれた際は、ぜひ「ありがとうございます！」と伝えることで、相手への敬意と感謝がよりストレートに伝わります。
"""
    }
}


def parse_markdown_content(file_path: str = "content.md") -> dict[str, str]:
    """Parse sections from content.md by header.
    Looks for lines starting with '#' or '##' and grabs subsequent text.
    """
    import os
    sections = {}
    if not os.path.exists(file_path):
        return sections
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        current_header = None
        current_lines = []
        
        for line in lines:
            if line.startswith("#") and not line.startswith("##"):
                if current_header:
                    sections[current_header] = "".join(current_lines).strip()
                current_header = line.lstrip("#").strip()
                current_lines = []
            else:
                if current_header is not None:
                    current_lines.append(line)
                    
        if current_header and current_lines:
            sections[current_header] = "".join(current_lines).strip()
    except Exception as e:
        print(f"Error parsing markdown: {e}")
        
    return sections


def get_detail_content(title: str, lang: str) -> str:
    """Gets detail content for a specific handbook section from content.md or fallback."""
    parsed_sections = parse_markdown_content()
    
    # Try exact match first
    if title in parsed_sections:
        return parsed_sections[title]
    
    # Try normalized match (case-insensitive, strip parentheses/punctuation)
    def normalize(s: str) -> str:
        import re
        s = s.lower()
        s = re.sub(r'\(.*?\)', '', s)
        s = re.sub(r'[^\w\s\u00C0-\u1EF9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '', s)
        return s.strip()
        
    norm_title = normalize(title)
    for sect_title, sect_content in parsed_sections.items():
        if normalize(sect_title) == norm_title or norm_title in normalize(sect_title) or normalize(sect_title) in norm_title:
            return sect_content
            
    # 2. Fallback to our hardcoded detailed explanations
    fallback_lang = FALLBACK_DETAILS.get(lang, FALLBACK_DETAILS["vn"])
    if title in fallback_lang:
        return fallback_lang[title]
        
    # Match in fallback keys using normalization
    for key, val in fallback_lang.items():
        if normalize(key) == norm_title or norm_title in normalize(key) or normalize(key) in norm_title:
            return val
            
    return "Không tìm thấy nội dung chi tiết cho mục này." if lang == "vn" else "この項目の詳細内容は見つかりませんでした。"


@ui.page("/culture")
def culture_page() -> None:
    layout_state = UiState()

    stored_lang = get_user_language()
    lang = validate_language_or_default(stored_lang)

    page_state: dict[str, Any] = {
        "handbook_items": [],
        "scenarios": [],
        "culture_insight": "",
        "history_items": [],
        "loading": True,
    }

    roadmap_loading = True
    roadmap_text = ""

    selected_handbook_item = {
        "title": "",
        "description": "",
        "icon": "🙇",
        "details_markdown": ""
    }

    @ui.refreshable
    def render_roadmap_content() -> None:
        nonlocal roadmap_loading, roadmap_text
        if roadmap_loading:
            with ui.column().classes("w-full items-center justify-center py-16 gap-4"):
                ui.spinner(size="xl", color="primary", thickness=4)
                ui.label("Đang phân tích hội thoại và lập lộ trình học tập...").classes("text-slate-500 text-sm animate-pulse font-medium")
        else:
            if not roadmap_text:
                ui.label("Không thể tạo lộ trình học tập lúc này.").classes("text-rose-500 py-6 text-center w-full font-medium")
                return

            with ui.column().classes("w-full gap-4 max-h-[450px] overflow-y-auto pr-2"):
                ui.markdown(roadmap_text).classes(
                    "text-sm text-slate-700 leading-relaxed markdown-body "
                    "prose prose-slate max-w-full"
                )

    with ui.dialog().classes("rounded-2xl") as roadmap_dialog, ui.card().classes(
        "w-[650px] max-w-full p-6 rounded-2xl border border-slate-100 shadow-2xl bg-white overflow-hidden"
    ):
        with ui.row().classes("w-full items-center justify-between mb-4 border-b border-slate-100 pb-2"):
            with ui.row().classes("items-center gap-2.5"):
                icon_box = ui.element("div").classes(
                    "h-10 w-10 rounded-xl bg-blue-50 text-blue-600 "
                    "flex items-center justify-center flex-shrink-0"
                )
                with icon_box:
                    ui.icon("auto_awesome", color="primary").classes("text-xl")
                ui.label("Lộ trình Học tập Gợi ý (User #4)").classes("text-base font-bold text-slate-800")
            ui.button(icon="close", on_click=roadmap_dialog.close).props('flat round').classes(
                "text-slate-400 hover:text-slate-600"
            )
        
        render_roadmap_content()

    with ui.dialog().classes("rounded-2xl") as handbook_dialog, ui.card().classes(
        "w-[700px] h-[650px] max-w-full p-6 rounded-2xl border border-slate-100 shadow-2xl bg-white overflow-hidden flex flex-col"
    ):
        @ui.refreshable
        def render_handbook_dialog_content() -> None:
            nonlocal selected_handbook_item
            title = selected_handbook_item.get("title", "")
            description = selected_handbook_item.get("description", "")
            icon = selected_handbook_item.get("icon", "🙇")
            details_markdown = selected_handbook_item.get("details_markdown", "")

            with ui.row().classes("w-full items-center justify-between mb-4 border-b border-slate-100 pb-2"):
                with ui.row().classes("items-center gap-2.5"):
                    icon_box = ui.element("div").classes(
                        "h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 "
                        "flex items-center justify-center flex-shrink-0 text-xl font-bold"
                    )
                    with icon_box:
                        if len(icon) == 1 or icon in ["🙇", "💬", "🙏"]:
                            ui.label(icon).classes("text-xl")
                        else:
                            ui.icon(icon).classes("text-xl text-emerald-600")
                    ui.label(title).classes("text-base font-bold text-slate-800")
                ui.button(icon="close", on_click=handbook_dialog.close).props('flat round').classes(
                    "text-slate-400 hover:text-slate-600"
                )

            with ui.column().classes("w-full gap-4 flex-1 overflow-y-auto pr-2"):
                if description:
                    with ui.row().classes("w-full gap-3 bg-slate-50 border-l-4 border-emerald-500 p-4 rounded-r-2xl"):
                        ui.label(description).classes(
                            "text-sm text-slate-600 leading-relaxed font-medium italic"
                        )

                if details_markdown:
                    ui.markdown(details_markdown).classes(
                        "text-sm text-slate-700 leading-relaxed markdown-body "
                        "prose prose-slate max-w-full"
                    )
        
        render_handbook_dialog_content()

    def handle_handbook_click(item: dict) -> None:
        nonlocal selected_handbook_item
        title = item.get("title", "")
        description = item.get("description", "")
        icon = item.get("icon", "🙇")
        
        details_markdown = get_detail_content(title, lang)
        
        selected_handbook_item = {
            "title": title,
            "description": description,
            "icon": icon,
            "details_markdown": details_markdown
        }
        
        render_handbook_dialog_content.refresh()
        handbook_dialog.open()

    def handle_new_conversation() -> None:
        ui.navigate.to("/translate")

    async def handle_roadmap() -> None:
        nonlocal roadmap_loading, roadmap_text
        roadmap_dialog.open()
        roadmap_loading = True
        render_roadmap_content.refresh()
        
        def fetch():
            with get_db_context() as db:
                return get_user_learning_roadmap(db, user_id=4)
                
        try:
            roadmap_text = await asyncio.to_thread(fetch)
        except Exception as e:
            print(f"Error fetching roadmap: {e}")
            roadmap_text = "Không thể tải được lộ trình học tập do lỗi hệ thống."
            
        roadmap_loading = False
        render_roadmap_content.refresh()

    async def load_culture_data() -> None:
        page_state["loading"] = True
        shell.refresh()
        try:
            page_state["history_items"] = await load_conversation_history()
            
            def fetch_db():
                with get_db_context() as db:
                    scenarios_data = get_marked_messages_with_analysis(db)
                    insight_text = get_culture_assistant_insight(db, lang)
                    return scenarios_data, insight_text

            marked_scenarios_data, ai_insight_text = await asyncio.to_thread(fetch_db)
            
            if lang == 'jp':
                handbook_items = [
                    {
                        "title": "敬語（けいご）",
                        "description": "年上や上司への敬意を示す階層的な言語システム。",
                        "icon": "🙇",
                        "tags": [
                            "です・ます（基本的な丁寧さ）",
                            "尊敬語（相手を高める）",
                            "謙譲語（自分を下げる）",
                        ],
                        "link_label": "続きを読む",
                        "link_href": "#",
                    },
                    {
                        "title": "返答スタイル",
                        "description": "ビジネスのやり取りで返答のペースを尊重し、面目を保つ。",
                        "icon": "💬",
                        "tags": ["直接的な言い方を避ける", "提案する前に聞く"],
                        "link_label": "続きを読む",
                        "link_href": nav("/analysis", lang),
                    },
                    {
                        "title": "感謝とお詫びの文化",
                        "description": "日本人はコミュニケーションの調和を保つために、頻繁に感謝とお詫びの言葉を使います。",
                        "icon": "🙏",
                        "tags": [
                            "小さな親切に対しても感謝する",
                            "お詫びは必ずしも全面的に非を認めるだけでなく、相手への気遣いを示す",
                            "よく使われる表現：ありがとうございます、すみません、申し訳ありません",
                            "感情を強く表現することよりも丁寧さが重んじられる",
                        ],
                        "link_label": "続きを読む",
                        "link_href": "#",
                    }
                ]
                scenarios = []
                num_scenarios = max(2, len(marked_scenarios_data))
                for i in range(num_scenarios):
                    idx = i + 1
                    has_data = i < len(marked_scenarios_data)
                    
                    phrase_val = marked_scenarios_data[i]["phrase"] if has_data else None
                    meaning_val = marked_scenarios_data[i]["meaning"] if has_data else None
                    response_val = marked_scenarios_data[i]["response"] if has_data else None
                    category_val = marked_scenarios_data[i]["category"] if has_data else None

                    if has_data and category_val == "QUẢN LÝ THỜI GIAN":
                        category = "時間管理"
                        accent_classes = "border-rose-100 bg-rose-50/60"
                    elif has_data and category_val == "GIAO TIẾP GIÁN TIẾP":
                        category = "間接的なコミュニケーション"
                        accent_classes = "border-amber-100 bg-amber-50/70"
                    else:
                        if idx == 1:
                            category = "間接的なコミュニケーション"
                            accent_classes = "border-amber-100 bg-amber-50/70"
                        else:
                            category = "時間管理"
                            accent_classes = "border-rose-100 bg-rose-50/60"

                    phrase = phrase_val
                    if not phrase:
                        if idx == 1:
                            phrase = '相手が言いました: "ちょっと考えさせてください"'
                        else:
                            phrase = '"なるべく早く" というデッドラインが設定された'

                    meaning = meaning_val
                    if not meaning:
                        if idx == 1:
                            meaning = "これは多くの場合、時間が必要なのではなく、丁寧な断り方です。"
                        else:
                            meaning = "日本の仕事文化では、これは通常「今すぐ」、最優先事項を意味します。"
                            
                    response = response_val
                    if not response:
                        if idx == 1:
                            response = "代替案を準備するか、現在の懸念事項について穏やかに尋ねる。"
                        else:
                            response = "すぐに取り掛かるか、具体的な完了時間を報告する。"

                    scenarios.append({
                        "index": idx,
                        "category": category,
                        "phrase": phrase,
                        "meaning": meaning,
                        "response": response,
                        "accent_classes": accent_classes,
                    })
            else:
                handbook_items = [
                    {
                        "title": "Kính ngữ (Keigo)",
                        "description": "Hệ thống ngôn ngữ phân cấp, thể hiện sự tôn trọng với người lớn tuổi, cấp trên.",
                        "icon": "🙇",
                        "tags": [
                            "てす・ます (Lịch sự cơ bản)",
                            "尊敬語 (Tôn kính ngữ)",
                            "謙譲語 (Khiêm nhường ngữ)",
                        ],
                        "link_label": "Đọc tiếp",
                        "link_href": "#",
                    },
                    {
                        "title": "Phong cách phản hồi",
                        "description": "Tôn trọng nhịp độ phản hồi và giữ thể diện trong trao đổi công việc.",
                        "icon": "💬",
                        "tags": ["Tránh nói thẳng", "Lắng nghe trước khi góp ý"],
                        "link_label": "Đọc tiếp",
                        "link_href": "#",
                    },
                    {
                        "title": "Văn hóa cảm ơn và xin lỗi",
                        "description": "Người Nhật thường xuyên sử dụng lời cảm ơn và xin lỗi để duy trì sự hài hòa trong giao tiếp.",
                        "icon": "🙏",
                        "tags": [
                            "Thường xuyên cảm ơn và xin lỗi.",
                            "ありがとうございます, すみません.",
                            "Duy trì sự tôn trọng."
                        ],
                        "link_label": "Đọc tiếp",
                        "link_href": "#",
                    },
                ]
                scenarios = []
                num_scenarios = max(2, len(marked_scenarios_data))
                for i in range(num_scenarios):
                    idx = i + 1
                    has_data = i < len(marked_scenarios_data)
                    
                    phrase_val = marked_scenarios_data[i]["phrase"] if has_data else None
                    meaning_val = marked_scenarios_data[i]["meaning"] if has_data else None
                    response_val = marked_scenarios_data[i]["response"] if has_data else None
                    category_val = marked_scenarios_data[i]["category"] if has_data else None

                    if has_data and category_val == "QUẢN LÝ THỜI GIAN":
                        category = "QUẢN LÝ THỜI GIAN"
                        accent_classes = "border-rose-100 bg-rose-50/60"
                    elif has_data and category_val == "GIAO TIẾP GIÁN TIẾP":
                        category = "GIAO TIẾP GIÁN TIẾP"
                        accent_classes = "border-amber-100 bg-amber-50/70"
                    else:
                        if idx == 1:
                            category = "GIAO TIẾP GIÁN TIẾP"
                            accent_classes = "border-amber-100 bg-amber-50/70"
                        else:
                            category = "QUẢN LÝ THỜI GIAN"
                            accent_classes = "border-rose-100 bg-rose-50/60"

                    phrase = phrase_val
                    if not phrase:
                        if idx == 1:
                            phrase = 'Đối tác nói: "Chotto kangaesete kudasai" (Để tôi suy nghĩ một chút)'
                        else:
                            phrase = 'Deadline được đưa ra "narubeku hayaku" (Càng sớm càng tốt)'

                    meaning = meaning_val
                    if not meaning:
                        if idx == 1:
                            meaning = "Đây thường là cách từ chối lịch sự, không phải thực sự cần thêm thời gian suy nghĩ."
                        else:
                            meaning = "Trong văn hóa làm việc Nhật, đây thường có nghĩa là NGAY LẬP TỨC, ưu tiên cao nhất."
                            
                    response = response_val
                    if not response:
                        if idx == 1:
                            response = "Nên chuẩn bị phương án thay thế hoặc nhẹ nhàng hỏi về các vướng mắc hiện tại."
                        else:
                            response = "Cần bắt tay vào làm ngay hoặc báo cáo thời gian hoàn thành cụ thể."

                    scenarios.append({
                        "index": idx,
                        "category": category,
                        "phrase": phrase,
                        "meaning": meaning,
                        "response": response,
                        "accent_classes": accent_classes,
                    })

            page_state["culture_insight"] = ai_insight_text or _('ai_culture_insight', lang)
            page_state["handbook_items"] = handbook_items
            page_state["scenarios"] = scenarios[::-1]
        except Exception as exc:
            print(f"Error loading culture data: {exc}")
            page_state["culture_insight"] = _('ai_culture_insight', lang)
            page_state["handbook_items"] = []
            page_state["scenarios"] = []
        page_state["loading"] = False
        shell.refresh()

    async def handle_sync() -> None:
        await load_culture_data()
        ui.notify(_('updated_from_conv', lang), type="positive")

    def handle_search(value: str) -> None:
        if value:
            ui.notify(f"{_('searching', lang)}: {value}", type="info")

    def handle_locale_click() -> None:
        ui.notify(_('switched_lang', lang), type="info")

    @ui.refreshable
    def shell() -> None:
        with base_layout(
            active_nav="/culture",
            ui_state=layout_state,
            history_items=page_state.get("history_items", []),
            on_history_select=lambda cid: ui.navigate.to(nav(f"/translate/{cid}", lang)),
            on_new_conversation=handle_new_conversation,
            on_search=handle_search,
            on_locale_click=handle_locale_click,
        ):
            if page_state["loading"]:
                with ui.row().classes("w-full justify-center py-20"):
                    ui.spinner(size="lg")
                return

            with ui.row().classes("w-full items-center justify-between"):
                with ui.row().classes("items-center gap-3"):
                    icon_box = ui.element("div").classes(
                        "h-10 w-10 rounded-full bg-amber-100 text-amber-600 "
                        "flex items-center justify-center"
                    )
                    with icon_box:
                        ui.icon("public")
                    page_title_block(
                        title=_('culture_explain_title', lang),
                        subtitle=_('culture_subtitle', lang),
                    )

            with ui.row().classes("w-full items-start gap-6"):
                with ui.column().classes("w-full max-w-[360px] gap-4"):
                    with ui.element("div").classes(
                        "w-full rounded-2xl border border-blue-100 bg-blue-50/60 p-4 shadow-sm"
                    ):
                        with ui.row().classes("items-center gap-3"):
                            icon_box = ui.element("div").classes(
                                "h-9 w-9 rounded-xl bg-white text-blue-600 "
                                "flex items-center justify-center"
                            )
                            with icon_box:
                                ui.icon("psychology")
                            ui.label(_('ai_culture_assistant', lang)).classes(
                                "text-sm font-semibold text-slate-800"
                            )
                        with ui.element("div").classes("max-h-[110px] overflow-y-auto mt-2 pr-1"):
                            ui.label(page_state["culture_insight"]).classes(
                                "text-sm text-slate-600"
                            )
                        action_button(
                            label=_("view_roadmap", lang),
                            icon="map",
                            variant="secondary",
                            on_click=handle_roadmap,
                            extra_classes="mt-4 bg-white",
                        )

                    with ui.column().classes("gap-3"):
                        ui.label(_("comm_handbook", lang)).classes(
                            "text-sm font-semibold text-slate-700"
                        )
                        insight_list(
                            items=page_state["handbook_items"],
                            max_height="300px",
                            on_link_click=handle_handbook_click,
                        )

                with ui.column().classes("flex-1 gap-4"):
                    scenario_panel(
                        title=_("real_situation_analysis", lang),
                        scenarios=page_state["scenarios"],
                        max_height="520px",
                        header_action=lambda: sync_action_bar(
                            label=_("update_from_conv", lang),
                            icon="sync",
                            on_click=handle_sync,
                            variant="secondary",
                        ),
                    )

    shell()
    ui.timer(0.1, load_culture_data, once=True)
