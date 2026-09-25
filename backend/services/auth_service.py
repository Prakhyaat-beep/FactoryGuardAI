"""Small session-authentication helpers for FactoryGuard."""

import re
from functools import wraps

from flask import jsonify, session
from werkzeug.security import check_password_hash, generate_password_hash


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class AuthenticationValidationError(ValueError):
    """Raised when login or registration input is invalid."""


def validate_registration(payload):
    if not isinstance(payload, dict):
        raise AuthenticationValidationError("Request body must be a JSON object.")
    username = str(payload.get("username", "")).strip()
    password = payload.get("password")
    if not USERNAME_PATTERN.fullmatch(username):
        raise AuthenticationValidationError("Username must be 3-50 characters using letters, numbers, dots, hyphens, or underscores.")
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        raise AuthenticationValidationError("Password must be between 8 and 128 characters.")
    return username, password


def validate_login(payload):
    return validate_registration(payload)


def create_user(repository, username, password):
    """The initial account is Admin; later self-registered accounts are Maintenance users."""
    role = "Admin" if repository.count() == 0 else "Maintenance"
    user_id = repository.create(username, generate_password_hash(password), role)
    return {"id": user_id, "username": username, "role": role}


def authenticate_user(repository, username, password):
    user = repository.get_by_username(username)
    if user is None or not check_password_hash(user["password_hash"], password):
        return None
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication is required."}), 401
        return view(*args, **kwargs)
    return wrapped
