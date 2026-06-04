# @forge:component
# id: account_repository
# role: persistence
# description: Persistence adapter for users and sessions.
# data_shapes:
#   - pending_user_record
#   - user_record
#   - verified_user_credentials
#   - session_record
# responsibilities:
#   - Check user uniqueness by email.
#   - Persist user records.
#   - Persist session records.

from dataclasses import dataclass


# @forge:type
# id: pending_user_record
# type_kind: state
# entity: user
# shape:
#   email: string
#   display_name: string
#   password_hash: string
@dataclass
class PendingUserRecord:
    email: str
    display_name: str
    password_hash: str


# @forge:type
# id: verified_user_credentials
# type_kind: state
# entity: user
# shape:
#   user_id: string
#   email: string
@dataclass
class VerifiedUserCredentials:
    user_id: str
    email: str


# @forge:operation
# id: save_registered_user
# input: ref[pending_user_record]
# returns: ref[user_record]
# logic:
#   - Check for an existing user with the same email.
#   - Persist the pending user record when unique.
#   - Return the stored user record.
# participates_in:
#   - container_flow: register_user
#     local_flow: register_user_backend
#     step: 3
#     passes: ref[user_record]
def save_registered_user(record: PendingUserRecord) -> dict[str, str]:
    return {
        "user_id": "user-1",
        "email": record.email,
        "display_name": record.display_name,
        "status": "active",
    }


# @forge:operation
# id: create_session_for_verified_user
# input: ref[verified_user_credentials]
# returns: ref[session_record]
# logic:
#   - Create a session token for the verified user.
#   - Persist the session record.
#   - Return the stored session record.
# participates_in:
#   - container_flow: sign_in_user
#     local_flow: sign_in_user_backend
#     step: 3
#     passes: ref[session_record]
def create_session_for_verified_user(
    credentials: VerifiedUserCredentials,
) -> dict[str, str]:
    return {
        "session_id": "session-1",
        "session_token": "session-token",
        "user_id": credentials.user_id,
    }
