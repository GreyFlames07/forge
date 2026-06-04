// @forge:component
// id: notes_screen
// role: interface
// description: Screen for listing and creating notes.
// interface:
//   kind: screen
//   surface: /notes
//   actor: team_member
//   container_flows:
//     - create_note
//     - list_notes
//     - archive_note
// data_shapes:
//   - note_editor_state
//   - list_notes_view_request
//   - create_note_request
// responsibilities:
//   - Render active notes.
//   - Collect new note input.
//   - Start note list and create flows.

// @forge:type
// id: note_editor_state
// type_kind: ui_state
// shape:
//   session_token: string
//   title: string
//   body: string
//   status: enum[idle, submitting, rejected, complete]
export type NoteEditorState = {
  sessionToken: string;
  title: string;
  body: string;
  status: "idle" | "submitting" | "rejected" | "complete";
};

// @forge:type
// id: create_note_request
// type_kind: command
// shape:
//   session_token: string
//   title: string
//   body: string
export type CreateNoteRequest = {
  sessionToken: string;
  title: string;
  body: string;
};

// @forge:type
// id: list_notes_view_request
// type_kind: query
// shape:
//   session_token: string
export type ListNotesViewRequest = {
  sessionToken: string;
};

// @forge:type
// id: list_notes_request
// type_kind: query
// shape:
//   session_token: string
export type ListNotesRequest = {
  sessionToken: string;
};

// @forge:type
// id: archive_note_ui_command
// type_kind: command
// shape:
//   session_token: string
//   note_id: string
export type ArchiveNoteUiCommand = {
  sessionToken: string;
  noteId: string;
};

// @forge:type
// id: archive_note_request
// type_kind: command
// shape:
//   session_token: string
//   note_id: string
export type ArchiveNoteRequest = {
  sessionToken: string;
  noteId: string;
};

// @forge:type
// id: note_detail_response
// type_kind: response
// shape:
//   note: ref[note_record]
export type NoteDetailResponse = {
  note: unknown;
};

// @forge:type
// id: note_list_response
// type_kind: response
// shape:
//   notes: "[ref[note_record]]"
export type NoteListResponse = {
  notes: unknown[];
};

// @forge:type
// id: note_error_response
// type_kind: error
// shape:
//   message: string
//   note_id?: string
export type NoteErrorResponse = {
  message: string;
  noteId?: string;
};

// @forge:operation
// id: submit_create_note_form
// input: ref[note_editor_state]
// returns: ref[create_note_request]
// logic:
//   - Validate note title and body.
//   - Build a create note request with session context.
//   - Submit the request to the notes API.
// participates_in:
//   - container_flow: create_note
//     local_flow: create_note_frontend
//     step: 1
//     passes: ref[create_note_request]
export function submitCreateNoteForm(
  state: NoteEditorState,
): CreateNoteRequest {
  return {
    sessionToken: state.sessionToken,
    title: state.title,
    body: state.body,
  };
}

// @forge:operation
// id: request_active_notes
// input: ref[list_notes_view_request]
// returns: ref[list_notes_request]
// logic:
//   - Read the current session token.
//   - Build an active notes query.
//   - Submit the query to the notes API.
// participates_in:
//   - container_flow: list_notes
//     local_flow: list_notes_frontend
//     step: 1
//     passes: ref[list_notes_request]
export function requestActiveNotes(
  request: ListNotesViewRequest,
): ListNotesRequest {
  return { sessionToken: request.sessionToken };
}

// @forge:operation
// id: render_created_note
// input: ref[note_detail_response]
// returns: ref[note_editor_state]
// logic:
//   - Accept the created note response.
//   - Clear the note editor fields.
//   - Mark the note editor complete.
// participates_in:
//   - container_flow: create_note
//     local_flow: create_note_frontend
//     step: 2
//     passes: ref[note_editor_state]
export function renderCreatedNote(
  state: NoteEditorState,
  _response: NoteDetailResponse,
): NoteEditorState {
  return {
    ...state,
    title: "",
    body: "",
    status: "complete",
  };
}

// @forge:operation
// id: render_note_list
// input: ref[note_list_response]
// returns: ref[note_list_response]
// logic:
//   - Accept the active notes response.
//   - Render active notes in updated order.
//   - Preserve the current session context.
// participates_in:
//   - container_flow: list_notes
//     local_flow: list_notes_frontend
//     step: 2
//     passes: ref[note_list_response]
export function renderNoteList(response: NoteListResponse): NoteListResponse {
  return response;
}
