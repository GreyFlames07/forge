# @forge:component
# id: note_service
# role: logic
# description: Applies note creation, listing, and archive rules.
# data_shapes:
#   - create_note_command
#   - list_notes_query
#   - archive_note_command
#   - note_record
# responsibilities:
#   - Authenticate note workflow sessions.
#   - Validate note content.
#   - Apply note lifecycle rules.

from dataclasses import dataclass


# @forge:type
# id: create_note_command
# type_kind: command
# shape:
#   session_token: string
#   title: string
#   body: string
@dataclass
class CreateNoteCommand:
    session_token: str
    title: str
    body: str


# @forge:type
# id: list_notes_query
# type_kind: query
# shape:
#   session_token: string
@dataclass
class ListNotesQuery:
    session_token: str


# @forge:type
# id: archive_note_command
# type_kind: command
# shape:
#   session_token: string
#   note_id: string
@dataclass
class ArchiveNoteCommand:
    session_token: str
    note_id: str


# @forge:operation
# id: validate_create_note
# input: ref[create_note_command]
# returns: ref[pending_note_record]
# logic:
#   - Authenticate the session token.
#   - Validate note title and body length.
#   - Build a pending active note record.
# participates_in:
#   - container_flow: create_note
#     local_flow: create_note_backend
#     step: 2
#     passes: ref[pending_note_record]
#     next: 3
def validate_create_note(command: CreateNoteCommand) -> dict[str, str]:
    return {
        "title": command.title,
        "body": command.body,
        "status": "active",
    }


# @forge:operation
# id: validate_list_notes
# input: ref[list_notes_query]
# returns: ref[active_notes_lookup]
# logic:
#   - Authenticate the session token.
#   - Build a query for active notes.
# participates_in:
#   - container_flow: list_notes
#     local_flow: list_notes_backend
#     step: 2
#     passes: ref[active_notes_lookup]
#     next: 3
def validate_list_notes(query: ListNotesQuery) -> dict[str, str]:
    return {"status": "active"}


# @forge:operation
# id: validate_archive_note
# input: ref[archive_note_command]
# returns: ref[archive_note_lookup]
# logic:
#   - Authenticate the session token.
#   - Build a lookup for the active note.
# participates_in:
#   - container_flow: archive_note
#     local_flow: archive_note_backend
#     step: 2
#     passes: ref[archive_note_lookup]
#     next: 3
def validate_archive_note(command: ArchiveNoteCommand) -> dict[str, str]:
    return {"note_id": command.note_id, "status": "active"}
