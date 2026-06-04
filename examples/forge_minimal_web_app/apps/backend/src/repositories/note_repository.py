# @forge:component
# id: note_repository
# role: persistence
# description: Persistence adapter for note records.
# data_shapes:
#   - pending_note_record
#   - active_notes_lookup
#   - archive_note_lookup
#   - note_record
#   - note_list_response
# responsibilities:
#   - Persist new note records.
#   - List active notes.
#   - Archive active notes.

from dataclasses import dataclass


# @forge:type
# id: pending_note_record
# type_kind: state
# entity: note
# shape:
#   title: string
#   body: string
#   status: enum[active]
@dataclass
class PendingNoteRecord:
    title: str
    body: str
    status: str


# @forge:type
# id: active_notes_lookup
# type_kind: query
# shape:
#   status: enum[active]
@dataclass
class ActiveNotesLookup:
    status: str


# @forge:type
# id: archive_note_lookup
# type_kind: query
# shape:
#   note_id: string
#   status: enum[active]
@dataclass
class ArchiveNoteLookup:
    note_id: str
    status: str


# @forge:operation
# id: save_created_note
# input: ref[pending_note_record]
# returns: ref[note_record]
# logic:
#   - Persist the pending note record.
#   - Return the stored note record.
# participates_in:
#   - container_flow: create_note
#     local_flow: create_note_backend
#     step: 3
#     passes: ref[note_record]
def save_created_note(record: PendingNoteRecord) -> dict[str, str]:
    return {
        "note_id": "note-1",
        "title": record.title,
        "body": record.body,
        "status": "active",
    }


# @forge:operation
# id: list_active_notes
# input: ref[active_notes_lookup]
# returns: ref[note_list_response]
# logic:
#   - Query active note records.
#   - Order notes by updated time.
#   - Return a note list response.
# participates_in:
#   - container_flow: list_notes
#     local_flow: list_notes_backend
#     step: 3
#     passes: ref[note_list_response]
def list_active_notes(_lookup: ActiveNotesLookup) -> dict[str, list[dict[str, str]]]:
    return {"notes": []}


# @forge:operation
# id: archive_active_note
# input: ref[archive_note_lookup]
# returns: ref[note_record]
# logic:
#   - Load the active note by id.
#   - Change status from active to archived.
#   - Return the updated note record.
# participates_in:
#   - container_flow: archive_note
#     local_flow: archive_note_backend
#     step: 3
#     passes: ref[note_record]
def archive_active_note(lookup: ArchiveNoteLookup) -> dict[str, str]:
    return {
        "note_id": lookup.note_id,
        "title": "Archived note",
        "body": "Archived body",
        "status": "archived",
    }
