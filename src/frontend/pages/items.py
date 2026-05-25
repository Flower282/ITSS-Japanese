from fastapi import HTTPException
from nicegui import ui

from src.frontend.api_client import api_delete, api_get, api_post_json, api_put_json
from src.frontend.components import notifications
from src.frontend.layouts.default import dashboard_frame
from src.models import ItemCreate, ItemUpdate


@ui.page("/items")
def items_page():
    """Items page backed by REST API /api/v1/items."""
    with dashboard_frame(title="My Items"):
        items_grid = ui.grid().classes(
            "w-full gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
        )

        with ui.dialog() as dialog, ui.card().classes("min-w-[600px]"):
            ui.label("Create New Item").classes("text-h6")
            title_input = ui.input("Title").classes("w-full")
            desc_input = ui.textarea("Description").classes("w-full")
            ui.button(
                "Create",
                on_click=lambda: create_item(
                    title_input, desc_input, dialog, items_grid
                ),
            ).classes("w-full")

        ui.button("Create Item", on_click=dialog.open, icon="add").props(
            "color=primary"
        )
        ui.timer(0.1, lambda: load_items(items_grid), once=True)


async def load_items(grid: ui.grid):
    try:
        items = await api_get("/api/v1/items/")
        if not isinstance(items, list):
            items = []

        grid.clear()
        with grid:
            for item in items:
                with ui.card().classes("p-0"):
                    ui.image(f"https://picsum.photos/600/400?random={item['id']}")
                    with ui.column().classes("p-4 w-full"):
                        ui.label(item.get("title", "")).classes(
                            "text-xl font-semibold"
                        )
                        ui.separator().classes("w-full my-1")
                        ui.label(item.get("description") or "").classes(
                            "text-sm line-clamp-3"
                        )

                        with ui.row().classes("w-full justify-end mt-4 gap-2"):
                            with (
                                ui.dialog() as modify_dialog,
                                ui.card().classes("min-w-[600px]"),
                            ):
                                ui.label("Modify Item").classes("text-h6")
                                modify_title = ui.input(
                                    "Title", value=item.get("title", "")
                                ).classes("w-full")
                                modify_desc = ui.textarea(
                                    "Description", value=item.get("description") or ""
                                ).classes("w-full")
                                ui.button(
                                    "Save",
                                    on_click=lambda i=item,
                                    t=modify_title,
                                    d=modify_desc: update_item(
                                        i["id"], t, d, modify_dialog, grid
                                    ),
                                ).classes("w-full")

                            ui.button(icon="edit", on_click=modify_dialog.open).props(
                                "flat dense"
                            )

                            with ui.dialog() as confirm_dialog, ui.card():
                                ui.label(
                                    f"Are you sure you want to delete '{item.get('title')}'?"
                                )
                                with ui.row().classes("w-full justify-end"):
                                    ui.button(
                                        "Cancel",
                                        on_click=confirm_dialog.close,
                                        color="gray-100",
                                    )
                                    ui.button(
                                        "Yes",
                                        on_click=lambda item_id=item[
                                            "id"
                                        ]: delete_item(item_id, grid),
                                        color="red",
                                    )

                            ui.button(
                                icon="delete", on_click=confirm_dialog.open
                            ).props("flat dense color=red")
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception as e:
        notifications.show_error(f"An unexpected error occurred: {e}")


async def create_item(
    title_input: ui.input, desc_input: ui.textarea, dialog: ui.dialog, grid: ui.grid
):
    try:
        item_in = ItemCreate(
            title=title_input.value, description=desc_input.value or None
        )
        await api_post_json(
            "/api/v1/item/",
            item_in.model_dump(exclude_unset=True),
        )
        notifications.show_success("Item created successfully!")
        dialog.close()
        await load_items(grid)
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception as e:
        notifications.show_error(f"An unexpected error occurred: {e}")


async def update_item(
    item_id: int,
    title_input: ui.input,
    desc_input: ui.textarea,
    dialog: ui.dialog,
    grid: ui.grid,
):
    try:
        item_in = ItemUpdate(
            title=title_input.value, description=desc_input.value or None
        )
        await api_put_json(
            f"/api/v1/item/{item_id}",
            item_in.model_dump(exclude_unset=True),
        )
        notifications.show_success("Item updated successfully.")
        dialog.close()
        await load_items(grid)
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception as e:
        notifications.show_error(f"An unexpected error occurred: {e}")


async def delete_item(item_id: int, grid: ui.grid):
    try:
        await api_delete(f"/api/v1/item/{item_id}")
        notifications.show_success("Item deleted successfully.")
        await load_items(grid)
    except HTTPException as e:
        notifications.show_error(e.detail)
    except Exception as e:
        notifications.show_error(f"An unexpected error occurred: {e}")
