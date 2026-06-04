# @forge:component
# id: session_store
# role: datastore
# description: Datastore area for authenticated sessions.
# data_shapes:
#   - session_record
# responsibilities:
#   - Store active sessions.
#   - Support session lookup by token.
#   - Support session revocation.

from dataclasses import dataclass


# @forge:type
# id: session_record
# type_kind: persistent_state
# entity: session
# shape:
#   session_id: string
#   session_token: string
#   user_id: string
#   created_at: datetime
#   expires_at: datetime
@dataclass
class SessionRecord:
    session_id: str
    session_token: str
    user_id: str
    created_at: str
    expires_at: str


# @forge:persistence
# entity: session
# storage_model: relational
# physical_store: notes_db
# table: sessions
# migrations_path: migrations
# access_patterns:
#   - find session by session_token
#   - create session record
#   - revoke session by session_id
# security: Session tokens must be stored and compared securely.
