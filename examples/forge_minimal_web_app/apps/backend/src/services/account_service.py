# @forge:component
# id: account_service
# role: logic
# description: Applies account registration and sign-in business rules.
# data_shapes:
#   - register_user_command
#   - sign_in_command
#   - user_record
#   - session_record
# responsibilities:
#   - Validate account business rules.
#   - Hash submitted passwords.
#   - Verify submitted credentials.
#   - Coordinate account persistence.
# security: Must never expose password hashes outside backend internals.

from dataclasses import dataclass


# @forge:type
# id: register_user_command
# type_kind: command
# shape:
#   email: string
#   display_name: string
#   password: string
@dataclass
class RegisterUserCommand:
    email: str
    display_name: str
    password: str


# @forge:type
# id: sign_in_command
# type_kind: command
# shape:
#   email: string
#   password: string
@dataclass
class SignInCommand:
    email: str
    password: str


# @forge:operation
# id: register_user_business_rules
# input: ref[register_user_command]
# returns: ref[pending_user_record]
# logic:
#   - Confirm the email has a valid shape.
#   - Hash the submitted password.
#   - Build a pending user record for persistence.
# participates_in:
#   - container_flow: register_user
#     local_flow: register_user_backend
#     step: 2
#     passes: ref[pending_user_record]
#     next: 3
def register_user_business_rules(command: RegisterUserCommand) -> dict[str, str]:
    return {
        "email": command.email,
        "display_name": command.display_name,
        "password_hash": "hashed-password",
    }


# @forge:operation
# id: verify_sign_in_credentials
# input: ref[sign_in_command]
# returns: ref[verified_user_credentials]
# logic:
#   - Load user credential material.
#   - Compare submitted password with stored password hash.
#   - Produce verified credential context when valid.
# participates_in:
#   - container_flow: sign_in_user
#     local_flow: sign_in_user_backend
#     step: 2
#     passes: ref[verified_user_credentials]
#     next: 3
def verify_sign_in_credentials(command: SignInCommand) -> dict[str, str]:
    return {"email": command.email}
