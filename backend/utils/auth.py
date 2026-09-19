from functools import wraps

from flask import jsonify, request, session

from backend.extensions import db
from backend.models.user import User


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None
        if not user or not user.is_active:
            session.clear()
            return jsonify(success=False, message="Authentication required"), 401
        request.current_user = user
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    allowed_roles = set(roles)

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if request.current_user.role not in allowed_roles:
                return jsonify(success=False, message="Insufficient permissions"), 403
            return view(*args, **kwargs)

        return wrapped_view

    return decorator
