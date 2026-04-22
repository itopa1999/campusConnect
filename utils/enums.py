from enum import Enum

class GroupNames(Enum):
    ADMIN = "Admin"
    CUSTOMER = "Customer"
    
    @classmethod
    def values(cls):
        """Return all enum values as a list"""
        return [group.value for group in cls]
    
