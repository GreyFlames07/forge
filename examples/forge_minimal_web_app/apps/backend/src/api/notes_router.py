# @forge:component
# id: notes_router
# role: interface
# description: Backend route group for note operations.
# interface:
#   kind: router
#   surface: /notes
#   container_flows:
#     - create_note
#     - list_notes
#     - archive_note
#   input: ref[authenticated_http_request]
#   output: ref[http_response]
#   security: Requires a valid session token for all note routes.
# data_shapes:
#   - create_note_request
#   - list_notes_request
#   - archive_note_request
# responsibilities:
#   - Accept note API requests.
#   - Convert HTTP requests into note commands and queries.
#   - Return note API responses.

from dataclasses import dataclass


@dataclass
class NoteCommand:
    session_token: str
    title: str | None = None
    body: str | None = None
    note_id: str | None = None


# @forge:operation
# id: handle_create_note
# input: ref[create_note_request]
# returns: ref[create_note_command]
# logic:
#   - Accept the create note request.
#   - Validate transport-level request shape.
#   - Convert the request into a create note command.
# participates_in:
#   - container_flow: create_note:2
#     local_flow: create_note_backend:1
#     passes: ref[create_note_command]
#     next: 2
def handle_create_note(request: dict[str, str]) -> NoteCommand:
    return NoteCommand(
        session_token=request["session_token"],
        title=request["title"],
        body=request["body"],
    )


# @forge:operation
# id: handle_list_notes
# input: ref[list_notes_request]
# returns: ref[list_notes_query]
# logic:
#   - Accept the list notes request.
#   - Validate the session token field.
#   - Convert the request into an active notes query.
# participates_in:
#   - container_flow: list_notes:2
#     local_flow: list_notes_backend:1
#     passes: ref[list_notes_query]
#     next: 2
def handle_list_notes(request: dict[str, str]) -> NoteCommand:
    return NoteCommand(session_token=request["session_token"])


# @forge:operation
# id: handle_archive_note
# input: ref[archive_note_request]
# returns: ref[archive_note_command]
# logic:
#   - Accept the archive note request.
#   - Validate the session token and note id fields.
#   - Convert the request into an archive note command.
# participates_in:
#   - container_flow: archive_note:2
#     local_flow: archive_note_backend:1
#     passes: ref[archive_note_command]
#     next: 2
def handle_archive_note(request: dict[str, str]) -> NoteCommand:
    return NoteCommand(
        session_token=request["session_token"],
        note_id=request["note_id"],
    )


# @forge:operation
# id: build_note_detail_response
# input: ref[note_record]
# returns: ref[note_detail_response]
# logic:
#   - Accept a note record.
#   - Build a frontend note detail response.
# participates_in:
#   - container_flow: create_note:2
#     local_flow: create_note_backend:4
#     passes: ref[note_detail_response]
#     flow_logic:
#       - Return the newly created note to the frontend.
#   - container_flow: archive_note:2
#     local_flow: archive_note_backend:4
#     passes: ref[note_detail_response]
#     flow_logic:
#       - Return the archived note state to the frontend.
def build_note_detail_response(note: dict[str, str]) -> dict[str, dict[str, str]]:
    return {"note": note}


# @forge:operation
# id: build_list_notes_response
# input: ref[note_list_response]
# returns: ref[note_list_response]
# logic:
#   - Accept the active notes list.
#   - Return the list response unchanged.
# participates_in:
#   - container_flow: list_notes:2
#     local_flow: list_notes_backend:4
#     passes: ref[note_list_response]
def build_list_notes_response(response: dict[str, list[dict[str, str]]]) -> dict[str, list[dict[str, str]]]:
    return response
