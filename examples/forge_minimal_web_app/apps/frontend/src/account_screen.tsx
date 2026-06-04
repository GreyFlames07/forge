// @forge:component
// id: account_screen
// role: interface
// description: Screen for registration and sign-in entry points.
// interface:
//   kind: screen
//   surface: /account
//   actor: visitor
//   container_flows:
//     - register_user
//     - sign_in_user
// data_shapes:
//   - registration_form_state
//   - sign_in_form_state
//   - register_user_request
//   - sign_in_request
// responsibilities:
//   - Render registration and sign-in forms.
//   - Validate account access input.
//   - Start registration and sign-in flows.

// @forge:type
// id: registration_form_state
// type_kind: ui_state
// shape:
//   email: string
//   display_name: string
//   password: string
//   status: enum[idle, submitting, rejected, complete]
export type RegistrationFormState = {
  email: string;
  displayName: string;
  password: string;
  status: "idle" | "submitting" | "rejected" | "complete";
};

// @forge:type
// id: sign_in_form_state
// type_kind: ui_state
// shape:
//   email: string
//   password: string
//   status: enum[idle, submitting, rejected, complete]
export type SignInFormState = {
  email: string;
  password: string;
  status: "idle" | "submitting" | "rejected" | "complete";
};

// @forge:type
// id: register_user_request
// type_kind: command
// shape:
//   email: string
//   display_name: string
//   password: string
export type RegisterUserRequest = {
  email: string;
  displayName: string;
  password: string;
};

// @forge:type
// id: sign_in_request
// type_kind: command
// shape:
//   email: string
//   password: string
export type SignInRequest = {
  email: string;
  password: string;
};

// @forge:type
// id: registration_success_response
// type_kind: response
// shape:
//   user_id: string
//   display_name: string
//   message: string
export type RegistrationSuccessResponse = {
  userId: string;
  displayName: string;
  message: string;
};

// @forge:type
// id: registration_error_response
// type_kind: error
// shape:
//   message: string
//   field_errors?: {string: string}
export type RegistrationErrorResponse = {
  message: string;
  fieldErrors?: Record<string, string>;
};

// @forge:type
// id: sign_in_success_response
// type_kind: response
// shape:
//   session_token: string
//   user_id: string
//   display_name: string
export type SignInSuccessResponse = {
  sessionToken: string;
  userId: string;
  displayName: string;
};

// @forge:type
// id: sign_in_error_response
// type_kind: error
// shape:
//   message: string
export type SignInErrorResponse = {
  message: string;
};

// @forge:operation
// id: submit_registration_form
// input: ref[registration_form_state]
// returns: ref[register_user_request]
// logic:
//   - Validate email, display name, and password fields.
//   - Map form state into a backend registration request.
//   - Submit the request to the account API.
// participates_in:
//   - container_flow: register_user
//     local_flow: register_user_frontend
//     step: 1
//     passes: ref[register_user_request]
export function submitRegistrationForm(
  state: RegistrationFormState,
): RegisterUserRequest {
  return {
    email: state.email,
    displayName: state.displayName,
    password: state.password,
  };
}

// @forge:operation
// id: submit_sign_in_form
// input: ref[sign_in_form_state]
// returns: ref[sign_in_request]
// logic:
//   - Validate email and password fields.
//   - Map form state into a backend sign-in request.
//   - Submit the request to the account API.
// participates_in:
//   - container_flow: sign_in_user
//     local_flow: sign_in_user_frontend
//     step: 1
//     passes: ref[sign_in_request]
export function submitSignInForm(state: SignInFormState): SignInRequest {
  return {
    email: state.email,
    password: state.password,
  };
}

// @forge:operation
// id: render_registration_result
// input: ref[registration_success_response]
// returns: ref[registration_form_state]
// logic:
//   - Accept the registration response from the backend.
//   - Mark the registration form complete.
//   - Show the registration success message.
// participates_in:
//   - container_flow: register_user
//     local_flow: register_user_frontend
//     step: 2
//     passes: ref[registration_form_state]
export function renderRegistrationResult(
  _response: RegistrationSuccessResponse,
): RegistrationFormState {
  return {
    email: "",
    displayName: "",
    password: "",
    status: "complete",
  };
}

// @forge:operation
// id: render_sign_in_result
// input: ref[sign_in_success_response]
// returns: ref[sign_in_form_state]
// logic:
//   - Accept the sign-in response from the backend.
//   - Store approved session context.
//   - Mark the sign-in form complete.
// participates_in:
//   - container_flow: sign_in_user
//     local_flow: sign_in_user_frontend
//     step: 2
//     passes: ref[sign_in_form_state]
export function renderSignInResult(_response: SignInSuccessResponse): SignInFormState {
  return {
    email: "",
    password: "",
    status: "complete",
  };
}
