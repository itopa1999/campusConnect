from http import HTTPStatus
from datetime import datetime, timezone
import uuid


class BaseResult:
    def __init__(
        self,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        message="An error occurred; please try again later",
        request_id=None,
    ):
        self.status_code = status_code
        self.message = message
        self.request_id = request_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)

    @property
    def is_success(self):
        """Returns True if status_code is in 2xx range"""
        return str(self.status_code).startswith("2")

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "status_code": self.status_code,
            "message": self.message,
            "is_success": self.is_success,
        }


class BaseResultWithData(BaseResult):
    def __init__(
        self,
        data=None,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        message="An error occurred; please try again later",
        request_id=None,
    ):
        super().__init__(status_code, message, request_id)
        self.data = data

    def to_dict(self):
        base = super().to_dict()
        base["data"] = self.data
        return base