// @forge:component
// id: note_card
// role: interface
// parent_component: notes_screen
// description: Nested card for displaying and archiving a single note.
// interface:
//   kind: subsurface
//   surface: notes.note-card
//   actor: team_member
//   container_flows:
//     - archive_note
// data_shapes:
//   - archive_note_ui_command
// responsibilities:
//   - Display note summary state.
//   - Start the archive note flow for one note.

import type { ArchiveNoteRequest, ArchiveNoteUiCommand } from "./notes_screen";

// @forge:operation
// id: archive_note_from_card
// input: ref[archive_note_ui_command]
// returns: ref[archive_note_request]
// logic:
//   - Confirm the archive action for the selected note.
//   - Build an archive request with session context.
//   - Submit the request to the notes API.
// participates_in:
//   - container_flow: archive_note:1
//     local_flow: archive_note_frontend:1
//     passes: ref[archive_note_request]
export function archiveNoteFromCard(
  command: ArchiveNoteUiCommand,
): ArchiveNoteRequest {
  return {
    sessionToken: command.sessionToken,
    noteId: command.noteId,
  };
}

// @forge:operation
// id: render_archived_note
// input: ref[note_detail_response] or ref[note_error_response]
// returns: ref[note_detail_response]
// logic:
//   - Accept the archive-note result.
//   - Mark the card as archived when archiving succeeds.
//   - Show an archive error when the backend rejects the request.
// participates_in:
//   - container_flow: archive_note:3
//     local_flow: archive_note_frontend:2
//     passes: ref[note_detail_response]
export function renderArchivedNote(response: unknown): unknown {
  return response;
}
