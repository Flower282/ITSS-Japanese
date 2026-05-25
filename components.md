# Shared UI Components Architecture

Below is a reusable component plan based on the recurring UI patterns in id1.md, id2.md, id3.md, and id4.md.

## Component Name: AppTopBar
### Design Features
Global top bar with logo, search input, language selector, and primary action (new conversation). Consistent spacing and alignment across pages.
### Proposed Props/Parameters
- logo_src: str
- on_logo_click: Callable
- search_placeholder: str
- search_history: list[str] | None
- on_search: Callable
- language_options: list[str]
- active_language: str
- on_language_change: Callable
- primary_action_label: str
- on_primary_action: Callable
### Reference Files
- id1.md
- id2.md
- id3.md
- id4.md

## Component Name: SideNavMenu
### Design Features
Left navigation with active state, section labels, and quick access items. Handles main menu variants (overview, translate, analysis, culture).
### Proposed Props/Parameters
- items: list[dict] (label, route, icon, active)
- on_navigate: Callable
- footer_actions: list[dict] (label, icon, on_click)
### Reference Files
- id1.md
- id2.md
- id3.md
- id4.md

## Component Name: HistoryListPanel
### Design Features
Scrollable list of conversation partners or sessions with click-to-load behavior.
### Proposed Props/Parameters
- title: str | None
- items: list[dict] (id, label, subtitle, status)
- on_select: Callable
- selected_id: str | int | None
### Reference Files
- id1.md
- id2.md
- id3.md

## Component Name: PageTitleBlock
### Design Features
Large page title with optional subtitle/status indicator.
### Proposed Props/Parameters
- title: str
- subtitle: str | None
- status: str | None
- status_color: str | None
### Reference Files
- id1.md
- id2.md
- id3.md
- id4.md

## Component Name: StatsCardsRow
### Design Features
Row of KPI cards (e.g., total conversations, AI accuracy) with icons and values.
### Proposed Props/Parameters
- cards: list[dict] (label, value, icon, trend, accent_color)
- layout: str (e.g., "grid", "row")
### Reference Files
- id1.md

## Component Name: ActionButton
### Design Features
Primary/secondary buttons with consistent size, color, and hover behavior (save, analyze, translate).
### Proposed Props/Parameters
- label: str
- icon: str | None
- variant: str (primary/secondary/ghost)
- on_click: Callable
- disabled: bool = False
### Reference Files
- id2.md
- id3.md
- id4.md

## Component Name: ConversationHistoryView
### Design Features
Scrollable conversation log with role-based styling (speaker vs. user).
### Proposed Props/Parameters
- messages: list[dict] (role, text, timestamp)
- max_height: str | None
- on_load_more: Callable | None
### Reference Files
- id2.md
- id3.md

## Component Name: AnalysisPanel
### Design Features
Card-like blocks for AI analysis, nuance explanation, and intent summary.
### Proposed Props/Parameters
- title: str
- content: str | list[str]
- tags: list[str] | None
- actions: list[dict] | None
### Reference Files
- id2.md
- id3.md
- id4.md

## Component Name: RecommendationChips
### Design Features
Tag chips for tone optimization (polite, short, soft) with multi-select support.
### Proposed Props/Parameters
- options: list[str]
- selected: list[str]
- on_change: Callable
### Reference Files
- id2.md
- id3.md

## Component Name: InputComposer
### Design Features
Large textarea-like input for user reply drafting.
### Proposed Props/Parameters
- value: str
- placeholder: str
- on_submit: Callable
- on_change: Callable
### Reference Files
- id2.md
- id3.md

## Component Name: InsightList
### Design Features
List of AI suggestions or cultural guidance with optional "read more" links.
### Proposed Props/Parameters
- items: list[dict] (title, description, link)
- max_height: str | None
### Reference Files
- id1.md
- id4.md

## Component Name: ScenarioPanel
### Design Features
Scrollable scenarios/case studies with structured blocks and emphasis.
### Proposed Props/Parameters
- scenarios: list[dict] (title, situation, response)
- max_height: str | None
### Reference Files
- id4.md

## Component Name: SyncActionBar
### Design Features
Small action row for sync/update operations tied to the current context.
### Proposed Props/Parameters
- label: str
- icon: str | None
- on_click: Callable
- helper_text: str | None
### Reference Files
- id4.md
