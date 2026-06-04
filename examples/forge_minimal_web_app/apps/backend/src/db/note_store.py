# @forge:component
# id: note_store
# role: datastore
# description: Datastore area for note records.
# data_shapes:
#   - note_record
# responsibilities:
#   - Store notes.
#   - Support active note listing.
#   - Support note archive lifecycle transition.

from dataclasses import dataclass


# @forge:type
# id: note_record
# type_kind: persistent_state
# entity: note
# shape:
#   note_id: string
#   title: string
#   body: string
#   status: enum[active, archived]
#   created_by_user_id: string
#   created_at: datetime
#   updated_at: datetime
@dataclass
class NoteRecord:
    note_id: str
    title: str
    body: str
    status: str
    created_by_user_id: str
    created_at: str
    updated_at: str


# @forge:persistence
# entity: note
# storage_model: relational
# physical_store: notes_db
# table: notes
# migrations_path: migrations
# access_patterns:
#   - create note record
#   - list active notes
#   - archive note by note_id
# lifecycle:
#   states:
#     - active
#     - archived
#   transitions:
#     - from: active
#       to: archived
#       condition: Team member archives the note.
# security: Notes are readable only by authenticated team members.
