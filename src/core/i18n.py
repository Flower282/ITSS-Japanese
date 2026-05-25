# src/core/i18n.py
"""
Internationalization (i18n) module for multi-language support.
"""

from typing import Dict, Optional
from nicegui import ui

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'vn': {
        # Common UI
        'dashboard_title': 'Bảng Điều Khiển',
        'dashboard_subtitle': 'Chào mừng đến với ứng dụng của chúng tôi',
        'language_label': 'Ngôn ngữ',
        'vietnamese': 'Tiếng Việt',
        'japanese': '日本語',

        # Navigation
        'home': 'Trang Chủ',
        'analysis': 'Phân Tích',
        'translate': 'Dịch Thuật',
        'culture': 'Văn Hóa',
        'profile': 'Hồ Sơ',
        'settings': 'Cài Đặt',

        # Nav menu items
        'nav_overview': 'Tổng quan',
        'nav_translate_conv': 'Dịch hội thoại',
        'nav_analysis_conv': 'Phân tích hội thoại',
        'nav_culture_explain': 'Giải thích văn hóa',

        # Layout sidebar
        'new_conversation': 'Hội thoại mới',
        'main_features': 'TÍNH NĂNG CHÍNH',
        'history': 'LỊCH SỬ',
        'logout': 'Đăng xuất',
        'logout_confirm': 'Bạn có chắc muốn đăng xuất?',
        'cancel': 'Hủy',

        # Dashboard
        'welcome': 'Chào mừng',
        'welcome_message': 'Chào mừng đến với ứng dụng của chúng tôi!',
        'description': 'Đây là một ứng dụng được xây dựng bằng NiceGUI với hỗ trợ đa ngôn ngữ.',
        'overview': 'Tổng quan',
        'overview_subtitle': 'Xem các phân tích mới và cải thiện kỹ năng giao tiếp của bạn',
        'total_conversations': 'Tổng số hội thoại',
        'ai_accuracy': 'Độ chính xác AI',
        'suggestions_to_review': 'Gợi ý cần xem',
        'interaction_time': 'Thời gian tương tác',
        'this_week': 'tuần này',
        'this_month': 'Trong tháng này',
        'need_review': 'Cần xem lại',
        'ai_analysis_title': 'Phân tích & Đề xuất AI',
        'view_full_report': 'Xem toàn bộ báo cáo',
        'lang_btn': 'Ngôn ngữ: Tiếng Việt',
        'conversations_week': '+3 tuần này',
        'accuracy_week': '+2% tuần này',
        'overuse_sorry_title': 'Lạm dụng từ xin lỗi',
        'overuse_sorry_desc': "Bạn có xu hướng nói 'Sumimasen' nhiều hơn mức cần thiết. Trong ngữ cảnh dự án hôm qua, bạn có thể dùng 'Arigatou gozaimasu'.",
        'view_details': 'Xem chi tiết',
        'confidence_down': '-15% tự tin',
        'improve_keigo_title': 'Cải thiện kính ngữ',
        'improve_keigo_desc': "Phân tích từ hội thoại với Tanaka-san cho thấy bạn dùng Keigo (kính ngữ) chính xác 92%. Rất tốt!",
        'view_report': 'Xem báo cáo',
        'accuracy_up': '+5% so với tuần trước',
        'comm_distance_title': 'Khoảng cách giao tiếp',
        'comm_distance_desc': "AI phát hiện cách nói chuyện của bạn với Yamada-san hơi quá trang trọng so với mối quan hệ hiện tại.",
        'learn_more': 'Tìm hiểu',
        'suggest_change': 'Gợi ý thay đổi',

        # Actions
        'save': 'Lưu',
        'delete': 'Xóa',
        'edit': 'Chỉnh Sửa',
        'add': 'Thêm',
        'back': 'Quay Lại',
        'next': 'Tiếp Theo',
        'previous': 'Trước Đó',
        'search': 'Tìm kiếm',

        # Messages
        'success': 'Thành công',
        'error': 'Lỗi',
        'warning': 'Cảnh báo',
        'loading': 'Đang tải...',
        'detecting_language': 'Đang phát hiện ngôn ngữ...',
        'search_placeholder': 'Tìm kiếm hội thoại, phân tích, văn hóa...',
        'user_subtitle': 'Người Việt Nam',

        # Form labels
        'name': 'Tên',
        'email': 'Email',
        'password': 'Mật Khẩu',
        'confirm_password': 'Xác Nhận Mật Khẩu',
        'submit': 'Gửi',

        # Page titles
        'profile_title': 'Hồ Sơ Cá Nhân',
        'profile_description': 'Quản lý hồ sơ người dùng của bạn.',
        'settings_title': 'Cài Đặt',
        'settings_description': 'Điều chỉnh cài đặt ứng dụng.',
        'analysis_title': 'Phân Tích',
        'analysis_description': 'Xem các phân tích chi tiết.',
        'translate_title': 'Dịch Thuật',
        'translate_description': 'Dịch nội dung giữa các ngôn ngữ.',
        'culture_title': 'Văn Hóa',
        'culture_description': 'Khám phá các hướng dẫn văn hóa.',

        # Translation page
        'new_conversation_title': 'Cuộc hội thoại mới',
        'online': 'Đang trực tuyến',
        'ai_supporting': 'AI Assistant đang hỗ trợ',
        'analyze': 'Phân tích',
        'archive': 'Lưu trữ',
        'conv_history_title': 'LỊCH SỬ HỘI THOẠI',
        'listen_label': 'NGHE',
        'you_label': 'BẠN NÓI',
        'what_other_says': 'ĐỐI PHƯƠNG NÓI GÌ?',
        'ai_analyze_btn': 'Phân tích AI',
        'translation_vn': 'BẢN DỊCH (TIẾNG VIỆT)',
        'real_meaning': 'Ý NGHĨA THỰC TẾ & SẮC THÁI',
        'suggested_replies_title': 'GỢI Ý CÁCH TRẢ LỜI (CLICK ĐỂ DÙNG)',
        'what_you_want_say': 'BẠN MUỐN NÓI GÌ?',
        'input_placeholder': 'Nhập ý bạn muốn nói bằng tiếng Việt...',
        'optimize_tone': 'TỐI ƯU TỔNG GIỌNG',
        'tone_polite': 'Lịch sự',
        'tone_shorter': 'Ngắn gọn hơn',
        'tone_soft': 'Mềm mỏng',
        'voice': 'Giọng nói',
        'translate_optimize': 'Dịch & Tối ưu',
        'save_conv': 'Đã lưu hội thoại hiện tại.',
        'analyzing_content': 'Đang phân tích nội dung.',
        'new_conv_created': 'Đã tạo hội thoại mới.',
        'added_to_history': 'Đã thêm câu trả lời vào lịch sử.',
        'empty_input_warn': 'Vui lòng nhập nội dung cần dịch.',
        'loaded_history': 'Đã tải lịch sử hội thoại.',

        # Analysis page
        'conversation_analysis': 'Phân tích hội thoại',
        'export_pdf': 'Xuất báo cáo PDF',
        'generating_pdf': 'Đang tạo báo cáo PDF...',
        'no_data_export': 'Chưa có dữ liệu phân tích để xuất PDF.',
        'no_data': 'Chưa có dữ liệu',
        'loading_data': 'Đang tải dữ liệu từ backend và phân tích AI...',
        'ai_overall_feedback_label': 'Nhận xét tổng quan từ AI',
        'perception_gaps_label': 'Điểm lệch nhận thức',
        'content_summary': 'Tóm tắt nội dung',
        'main_decisions': 'Quyết định chính',
        'action_items_label': 'Action items',
        'no_analysis_data_title': 'Chưa có phân tích hội thoại',
        'no_analysis_feedback': 'Chưa có dữ liệu phân tích trong database.',
        'duration_metric_title': 'THỜI LƯỢNG',
        'duration_metric_subtitle': 'Phút tương tác',
        'understanding_metric_title': 'ĐỘ HIỂU',
        'understanding_metric_subtitle': 'Truyền đạt chính xác',
        'sentiment_metric_title': 'CẢM XÚC CHUNG',
        'sentiment_metric_subtitle': 'Tích cực & Xây dựng',
        'no_gaps': 'Chưa phát hiện điểm lệch nhận thức nào.',
        'no_decisions': 'Chưa phát hiện quyết định chính nào trong hội thoại.',
        'no_action_items': 'Chưa có action items.',
        'ai_recommendation': 'KHUYẾN NGHỊ AI',
        'search_old_conv': 'Tìm hội thoại cũ trong database...',
        'search_results_label': 'Kết quả tìm kiếm',
        'results_count': 'kết quả',
        'no_conv_found': 'Không tìm thấy hội thoại phù hợp trong database.',
        'open_analysis': 'Mở phân tích',
        'found_label': 'Tìm thấy',
        'untitled_issue': 'Vấn đề chưa đặt tên',
        'vietnamese_perspective': 'Quan điểm Việt Nam',
        'japanese_perspective': 'Quan điểm Nhật Bản',
        'untitled_conversation': 'Cuộc hội thoại chưa đặt tên',
        'backend_analysis_not_found': 'Backend không tìm thấy dữ liệu phân tích.',
        'invalid_analysis_response': 'API không trả về dữ liệu phân tích hợp lệ.',
        'failed_analysis_load': 'Không tải được dữ liệu phân tích',

        # Culture page
        'culture_explain_title': 'Giải thích văn hóa',
        'culture_subtitle': 'Nâng cao sự thấu hiểu văn hóa Nhật Bản (日本の文化理解)',
        'ai_culture_assistant': 'Trợ lý Văn hóa AI',
        'ai_culture_insight': 'Qua phân tích lịch sử hội thoại, bạn có xu hướng sử dụng ngôn ngữ Nhật quá trang trọng so với mục đích thân thiện trong môi trường IT startup.',
        'view_roadmap': 'Xem lộ trình gợi ý',
        'comm_handbook': 'Cẩm nang giao tiếp',
        'real_situation_analysis': 'Phân tích tình huống thực tế',
        'update_from_conv': 'Cập nhật từ hội thoại của bạn',
        'showed_roadmap': 'Đã hiển thị lộ trình học tập.',
        'updated_from_conv': 'Đã cập nhật từ hội thoại gần nhất.',
        'switched_lang': 'Đã chuyển ngôn ngữ hiển thị.',
        'searching': 'Đang tìm',
    },
    'jp': {
        # Common UI
        'dashboard_title': 'ダッシュボード',
        'dashboard_subtitle': 'アプリケーションへようこそ',
        'language_label': '言語',
        'vietnamese': 'Tiếng Việt',
        'japanese': '日本語',

        # Navigation
        'home': 'ホーム',
        'analysis': '分析',
        'translate': '翻訳',
        'culture': '文化',
        'profile': 'プロフィール',
        'settings': '設定',

        # Nav menu items
        'nav_overview': '概要',
        'nav_translate_conv': '会話翻訳',
        'nav_analysis_conv': '会話分析',
        'nav_culture_explain': '文化説明',

        # Layout sidebar
        'new_conversation': '新しい会話',
        'main_features': 'メイン機能',
        'history': '履歴',
        'logout': 'ログアウト',
        'logout_confirm': 'ログアウトしてもよろしいですか？',
        'cancel': 'キャンセル',

        # Dashboard
        'welcome': 'ようこそ',
        'welcome_message': 'アプリケーションへようこそ！',
        'description': 'これはNiceGUIで構築された多言語サポート付きアプリケーションです。',
        'overview': '概要',
        'overview_subtitle': '最新の分析を確認し、コミュニケーションスキルを向上させましょう',
        'total_conversations': '総会話数',
        'ai_accuracy': 'AI精度',
        'suggestions_to_review': '確認すべき提案',
        'interaction_time': 'インタラクション時間',
        'this_week': '今週',
        'this_month': '今月',
        'need_review': '要確認',
        'ai_analysis_title': 'AI分析・提案',
        'view_full_report': 'レポート全体を見る',
        'lang_btn': '言語: 日本語',
        'conversations_week': '+3 今週',
        'accuracy_week': '+2% 今週',
        'overuse_sorry_title': '謝罪表現の過剰使用',
        'overuse_sorry_desc': "「すみません」を必要以上に使う傾向があります。昨日のプロジェクトの文脈では「ありがとうございます」の方が適切でした。",
        'view_details': '詳細を見る',
        'confidence_down': '-15% 自信',
        'improve_keigo_title': '敬語の改善',
        'improve_keigo_desc': "田中さんとの会話の分析から、敬語（丁寧語）を92%正確に使用していることがわかりました。素晴らしい！",
        'view_report': 'レポートを見る',
        'accuracy_up': '先週比+5%',
        'comm_distance_title': 'コミュニケーション距離',
        'comm_distance_desc': "AIが検出したところ、山田さんへの話し方が現在の関係性に対してやや丁寧すぎます。",
        'learn_more': '詳しく見る',
        'suggest_change': '変更を提案',

        # Actions
        'save': '保存',
        'delete': '削除',
        'edit': '編集',
        'add': '追加',
        'back': '戻る',
        'next': '次へ',
        'previous': '前へ',
        'search': '検索',

        # Messages
        'success': '成功',
        'error': 'エラー',
        'warning': '警告',
        'loading': '読み込み中...',
        'detecting_language': '言語を検出中...',
        'search_placeholder': '会話・分析・文化を検索...',
        'user_subtitle': 'ベトナム人ユーザー',

        # Form labels
        'name': '名前',
        'email': 'メール',
        'password': 'パスワード',
        'confirm_password': 'パスワードの確認',
        'submit': '送信',

        # Page titles
        'profile_title': 'プロフィール',
        'profile_description': 'ユーザープロフィールを管理してください。',
        'settings_title': '設定',
        'settings_description': 'アプリケーション設定を調整します。',
        'analysis_title': '分析',
        'analysis_description': '詳細な分析を表示してください。',
        'translate_title': '翻訳',
        'translate_description': '言語間でコンテンツを翻訳します。',
        'culture_title': '文化',
        'culture_description': '文化的なガイダンスを探索してください。',

        # Translation page
        'new_conversation_title': '新しい会話',
        'online': 'オンライン中',
        'ai_supporting': 'AIアシスタントがサポート中',
        'analyze': '分析',
        'archive': 'アーカイブ',
        'conv_history_title': '会話履歴',
        'listen_label': '聞く',
        'you_label': 'あなたの発言',
        'what_other_says': '相手は何と言っていますか？',
        'ai_analyze_btn': 'AI分析',
        'translation_vn': '翻訳（ベトナム語）',
        'real_meaning': '実際の意味とニュアンス',
        'suggested_replies_title': '返答の提案（クリックして使用）',
        'what_you_want_say': '何を言いたいですか？',
        'input_placeholder': 'ベトナム語で言いたいことを入力してください...',
        'optimize_tone': 'トーンの最適化',
        'tone_polite': '丁寧',
        'tone_shorter': 'より簡潔に',
        'tone_soft': '柔らかく',
        'voice': '音声',
        'translate_optimize': '翻訳・最適化',
        'save_conv': '現在の会話を保存しました。',
        'analyzing_content': 'コンテンツを分析中。',
        'new_conv_created': '新しい会話を作成しました。',
        'added_to_history': '返答を履歴に追加しました。',
        'empty_input_warn': '翻訳するコンテンツを入力してください。',
        'loaded_history': '会話履歴を読み込みました。',

        # Analysis page
        'conversation_analysis': '会話分析',
        'export_pdf': 'PDFレポートを出力',
        'generating_pdf': 'PDFレポートを生成中...',
        'no_data_export': '出力する分析データがありません。',
        'no_data': 'データなし',
        'loading_data': 'バックエンドからデータを読み込み・AI分析中...',
        'ai_overall_feedback_label': 'AIからの総合フィードバック',
        'perception_gaps_label': '認識のギャップ',
        'content_summary': 'コンテンツのまとめ',
        'main_decisions': '主な決定事項',
        'action_items_label': 'アクションアイテム',
        'no_analysis_data_title': '会話分析データがありません',
        'no_analysis_feedback': 'データベースに分析データがまだありません。',
        'duration_metric_title': '時間',
        'duration_metric_subtitle': 'やり取り時間（分）',
        'understanding_metric_title': '理解度',
        'understanding_metric_subtitle': '正確に伝わっている度合い',
        'sentiment_metric_title': '全体の感情',
        'sentiment_metric_subtitle': '前向きで建設的',
        'no_gaps': '認識のギャップは検出されませんでした。',
        'no_decisions': '会話内に主な決定事項は検出されませんでした。',
        'no_action_items': 'アクションアイテムはありません。',
        'ai_recommendation': 'AIの推奨',
        'search_old_conv': 'データベースで古い会話を検索...',
        'search_results_label': '検索結果',
        'results_count': '件',
        'no_conv_found': 'データベースに一致する会話が見つかりません。',
        'open_analysis': '分析を開く',
        'found_label': '見つかりました',
        'untitled_issue': '未設定の課題',
        'vietnamese_perspective': 'ベトナム側の視点',
        'japanese_perspective': '日本側の視点',
        'untitled_conversation': 'タイトル未設定の会話',
        'backend_analysis_not_found': 'バックエンドで分析データが見つかりませんでした。',
        'invalid_analysis_response': 'APIが有効な分析データを返しませんでした。',
        'failed_analysis_load': '分析データを読み込めませんでした',

        # Culture page
        'culture_explain_title': '文化説明',
        'culture_subtitle': '日本の文化理解を深めましょう',
        'new_badge': '新着',
        'recommended_lesson_btn': 'レッスン: 空気を読むスキル',
        'ai_culture_assistant': 'AI文化アシスタント',
        'ai_culture_insight': '会話履歴の分析から、ITスタートアップ環境での友好的なコミュニケーションに対して、日本語が過度に丁寧すぎる傾向があります。',
        'view_roadmap': '提案されたロードマップを見る',
        'comm_handbook': 'コミュニケーションハンドブック',
        'real_situation_analysis': '実際の状況分析',
        'update_from_conv': '最新の会話から更新',
        'opened_lesson': 'おすすめのレッスンを開きました。',
        'showed_roadmap': '学習ロードマップを表示しました。',
        'updated_from_conv': '最新の会話から更新しました。',
        'switched_lang': '表示言語を切り替えました。',
        'searching': '検索中',
    }
}

# ============================================================================
# CONFIGURATION
# ============================================================================

VALID_LANGUAGES: list[str] = ['vn', 'jp']
DEFAULT_LANGUAGE: str = 'vn'
STORAGE_KEY_LANGUAGE: str = 'language'

# ============================================================================
# LOCALIZATION HELPER
# ============================================================================


def _(key: str, lang: str) -> str:
    """
    Localization helper: fetch translation for a key.

    Args:
        key: Translation key (e.g., 'dashboard_title')
        lang: Language code ('vn', 'jp', etc.)

    Returns:
        Translated string in the specified language.
        Returns the key itself if translation not found.
        Falls back to DEFAULT_LANGUAGE if lang not available.

    Example:
        title = _('dashboard_title', 'vn')  # Returns 'Bảng Điều Khiển'
        title = _('dashboard_title', 'jp')  # Returns 'ダッシュボード'
    """
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS.get(DEFAULT_LANGUAGE, {}))
    return lang_dict.get(key, key)


# ============================================================================
# STORAGE MANAGEMENT
# ============================================================================


def get_user_language() -> Optional[str]:
    """
    Retrieve user's saved language preference.

    Priority:
      1. NiceGUI client storage (set by language selector — explicit user choice)
      2. request.state.app_language (injected by LanguagePrefixMiddleware from
         the URL path BEFORE call_next — accurate for the current request)
      3. Cookie 'app_language' (persisted from previous requests)

    Returns:
        Saved language code (e.g., 'vn'), or None if not set.
    """
    try:
        request = ui.context.client.request
        storage = ui.context.client.storage
        user_storage = storage.get('user')

        # 1. NiceGUI client storage (explicit user choice via language selector)
        if user_storage:
            lang = user_storage.get(STORAGE_KEY_LANGUAGE)
            if lang and lang in VALID_LANGUAGES:
                return lang

        # 2. request.state injected by middleware (same-request, most accurate)
        if request and hasattr(request, 'state') and hasattr(request.state, 'app_language'):
            lang = request.state.app_language
            if lang and lang in VALID_LANGUAGES:
                return lang

        # 3. Cookie set by middleware on previous request (cross-request persistence)
        if request:
            cookie_lang = request.cookies.get('app_language')
            if cookie_lang and cookie_lang in VALID_LANGUAGES:
                return cookie_lang

        return None
    except (RuntimeError, AttributeError):
        return None


def set_user_language(lang: str) -> None:
    """
    Save user's language preference to persistent storage.

    Args:
        lang: Language code to save ('vn', 'jp', etc.)

    Note:
        Only saves if lang is in VALID_LANGUAGES.
        Silently fails if called outside of a UI context.
    """
    if lang not in VALID_LANGUAGES:
        return

    try:
        storage = ui.context.client.storage
        user_storage = storage.get('user')
        if user_storage is None:
            storage['user'] = {}
            user_storage = storage['user']

        user_storage[STORAGE_KEY_LANGUAGE] = lang
    except RuntimeError:
        pass


def is_valid_language(lang: str) -> bool:
    """Check if a language code is valid."""
    return lang in VALID_LANGUAGES


# ============================================================================
# LANGUAGE SWITCHING
# ============================================================================


def switch_language(new_lang: str, current_path: str = '/') -> None:
    """
    Switch to a new language and redirect, preserving the current subpath.

    Args:
        new_lang: Target language code ('vn', 'jp', etc.)
        current_path: Current page subpath to preserve (default: '/')

    Example:
        switch_language('jp', '/dashboard')  # Redirects to /jp/dashboard
    """
    if not is_valid_language(new_lang):
        return

    set_user_language(new_lang)
    ui.navigate.to(f'/{new_lang}{current_path}')


def redirect_to_default_language(subpath: str = '/dashboard') -> None:
    """Redirect to the default language with specified subpath."""
    ui.navigate.to(f'/{DEFAULT_LANGUAGE}{subpath}')


def nav(path: str, lang: str) -> str:
    """Build a language-prefixed navigation URL.

    Use this instead of bare paths in ui.navigate.to() so that the
    current language is preserved across page transitions.

    Args:
        path: Page path starting with '/', e.g. '/translate', '/analysis/5'
        lang: Current language code, e.g. 'jp' or 'vn'

    Returns:
        '/{lang}{path}', e.g. '/jp/translate'

    Example:
        ui.navigate.to(nav('/translate', lang))   # -> '/jp/translate'
        ui.navigate.to(nav('/analysis/3', lang))  # -> '/jp/analysis/3'
    """
    return f'/{lang}{path}'


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def get_language_display_name(lang: str, current_lang: str) -> str:
    """Get the display name of a language in the current language."""
    key = 'vietnamese' if lang == 'vn' else 'japanese'
    return _(key, current_lang)


def get_language_options(current_lang: str) -> Dict[str, str]:
    """Get language selector options for the UI dropdown."""
    return {
        lang: get_language_display_name(lang, current_lang)
        for lang in VALID_LANGUAGES
    }


def validate_language_or_default(lang: Optional[str]) -> str:
    """Validate a language code and return default if invalid."""
    if lang and is_valid_language(lang):
        return lang
    return DEFAULT_LANGUAGE
