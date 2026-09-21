import os
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

def is_safe_image(file_obj):
    """
    Validates that an uploaded file is a safe, allowed image format
    and within maximum allowable size limits.
    """
    if not file_obj:
        return False
    if file_obj.size > MAX_UPLOAD_SIZE:
        return False
    _, ext = os.path.splitext(file_obj.name.lower())
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    return True
