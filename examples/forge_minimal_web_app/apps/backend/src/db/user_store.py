# @forge:component
# id: user_store
# role: datastore
# description: Datastore area for user records.
# data_shapes:
#   - user_record
# responsibilities:
#   - Store registered users.
#   - Support lookup by email and user id.
#   - Enforce user data retention rules.

from dataclasses import dataclass


# @forge:type
# id: user_record
# type_kind: persistent_state
# entity: user
# shape:
#   user_id: string
#   email: string
#   display_name: string
#   password_hash: string
#   status: enum[active, disabled]
#   created_at: datetime
@dataclass
class UserRecord:
    user_id: str
    email: str
    display_name: str
    password_hash: str
    status: str
    created_at: str


# @forge:persistence
# entity: user
# storage_model: relational
# physical_store: notes_db
# table: users
# migrations_path: migrations
# access_patterns:
#   - find user by email
#   - find user by user_id
#   - create user record
# security: Password hashes must not be returned to frontend-facing components.
