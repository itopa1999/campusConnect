import re

def validate_ui_email(email: str) -> tuple[bool, str]:
  
    allowed_domains = ('@ui.edu.ng', '@stu.ui.edu.ng')
    
    if not email:
        return False, "Email address is required."
    
    if email.lower().endswith(allowed_domains):
        return True, ""
    else:
        return False, "Please use a valid @ui.edu.ng or @stu.ui.edu.ng email address."


def is_email_verified(user) -> bool:
    return user.email_verified

def is_fully_verified(user) -> bool:
    return (
        user.email_verified and 
        user.student_id_verified and 
        user.hall_verified
    )


def normalize_nigerian_phone(phone: str) -> str | None:
    """
    Convert any valid Nigerian phone number to the local 11-digit format starting with 0.
    Returns normalized string or None if invalid.
    
    Examples:
        +2348064160380 -> 08064160380
        08064160380    -> 08064160380
        2348064160380  -> 08064160380
        8064160380     -> 08064160380
        07012345678    -> 07012345678
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 11 and digits.startswith('0'):
        # Already local format
        return digits
    elif len(digits) == 13 and digits.startswith('234'):
        # Convert +234... to 0...
        return '0' + digits[3:]
    elif len(digits) == 10 and digits[0] != '0':
        # Assume missing leading zero, e.g., 8064160380
        return '0' + digits
    else:
        return None