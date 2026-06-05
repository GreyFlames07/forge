# @forge:component
# id: account_router
# role: interface
# description: Backend route group for registration and sign-in.
# interface:
#   kind: router
#   surface: /account
#   container_flows:
#     - register_user
#     - sign_in_user
#   input: ref[authenticated_http_request]
#   output: ref[http_response]
#   security: Must never log submitted passwords.
# data_shapes:
#   - register_user_request
#   - sign_in_request
#   - registration_success_response
#   - sign_in_success_response
# responsibilities:
#   - Accept account API requests.
#   - Convert HTTP requests into account commands.
#   - Return account API responses.

from dataclasses import dataclass


@dataclass
class AccountCommand:
    email: str
    password: str
    display_name: str | None = None


# @forge:type
# id: authenticated_http_request
# type_kind: payload
# shape:
#   headers: {string: string}
#   body: {string: string}
@dataclass
class AuthenticatedHttpRequest:
    headers: dict[str, str]
    body: dict[str, str]


# @forge:type
# id: http_response
# type_kind: response
# shape:
#   status_code: integer
#   body: {string: string}
@dataclass
class HttpResponse:
    status_code: int
    body: dict[str, str]


# @forge:operation
# id: handle_register_user
# input: ref[register_user_request]
# returns: ref[register_user_command]
# logic:
#   - Accept the registration request.
#   - Validate transport-level request shape.
#   - Convert the request into a registration command.
# participates_in:
#   - container_flow: register_user:2
#     local_flow: register_user_backend:1
#     passes: ref[register_user_command]
#     next: 2
def handle_register_user(request: dict[str, str]) -> AccountCommand:
    return AccountCommand(
        email=request["email"],
        password=request["password"],
        display_name=request["display_name"],
    )


# @forge:operation
# id: handle_sign_in_user
# input: ref[sign_in_request]
# returns: ref[sign_in_command]
# logic:
#   - Accept the sign-in request.
#   - Validate transport-level request shape.
#   - Convert the request into a sign-in command.
# participates_in:
#   - container_flow: sign_in_user:2
#     local_flow: sign_in_user_backend:1
#     passes: ref[sign_in_command]
#     next: 2
def handle_sign_in_user(request: dict[str, str]) -> AccountCommand:
    return AccountCommand(email=request["email"], password=request["password"])


# @forge:operation
# id: build_registration_response
# input: ref[user_record]
# returns: ref[registration_success_response]
# logic:
#   - Accept the stored user record.
#   - Remove password hash material.
#   - Build the frontend registration response.
# participates_in:
#   - container_flow: register_user:4
#     local_flow: register_user_backend:4
#     passes: ref[registration_success_response]
def build_registration_response(user: dict[str, str]) -> dict[str, str]:
    return {
        "user_id": user["user_id"],
        "display_name": user["display_name"],
        "message": "Registration complete.",
    }


# @forge:operation
# id: build_sign_in_response
# input: ref[session_record]
# returns: ref[sign_in_success_response]
# logic:
#   - Accept the stored session record.
#   - Build the frontend sign-in response.
#   - Include only approved session data.
# participates_in:
#   - container_flow: sign_in_user:2
#     local_flow: sign_in_user_backend:4
#     passes: ref[sign_in_success_response]
def build_sign_in_response(session: dict[str, str]) -> dict[str, str]:
    return {
        "session_token": session["session_token"],
        "user_id": session["user_id"],
        "display_name": "Team member",
    }
