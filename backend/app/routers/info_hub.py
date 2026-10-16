"""Info Hub: everyone signed in can read and search; HR and Admin create, edit, hide and delete entries."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..core import Email, Name, WebUrl
from ..db import DB
from ..deps import CurrentUser, InfoEditor
from ..repositories import info_hub

router = APIRouter(prefix="/api/info-hub", tags=["info-hub"])


@router.get("")
def list_entries(search: str = Query(default="", max_length=200), include_inactive: bool = False,
                 user=CurrentUser, conn=DB):
    if include_inactive and user["role"] not in ("ADMIN", "HR"):
        raise HTTPException(403, "Only HR and admins can see hidden entries")
    return info_hub.search(conn, search.strip(), include_inactive)


class EntryIn(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    title: Name
    body_md: str = Field(min_length=1, max_length=10000)
    contact_email: Email | None = None
    link_url: WebUrl | None = None
    display_order: int = Field(default=0, ge=0, le=10000)
    is_active: bool = True


@router.post("", status_code=201)
def create_entry(body: EntryIn, user=InfoEditor, conn=DB):
    return info_hub.create(conn, body.model_dump(), user["id"])


@router.put("/{entry_id}")
def update_entry(entry_id: UUID, body: EntryIn, user=InfoEditor, conn=DB):
    row = info_hub.update(conn, entry_id, body.model_dump(), user["id"])
    if not row:
        raise HTTPException(404, "Entry not found")
    return row


@router.delete("/{entry_id}", status_code=204)
def delete_entry(entry_id: UUID, _=InfoEditor, conn=DB):
    if not info_hub.delete(conn, entry_id):
        raise HTTPException(404, "Entry not found")
