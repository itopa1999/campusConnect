import uuid
from http import HTTPStatus

from common.throttling.utils import format_duration
from drf_standardized_errors.formatter import (
    ExceptionFormatter as BaseExceptionFormatter,
)
from drf_standardized_errors.types import ErrorResponse

from utils.base_result import BaseResult
from utils.log_helpers import OperationLogger


class ExceptionFormatter(BaseExceptionFormatter):
    """
    Custom DRF Standardized Errors formatter.

    Features:
    - Standardized BaseResult response format
    - Safe generic messages for 5xx errors
    - Proper handling of throttling (429)
    - Reduced noise in logs for expected client errors
    """

    def format_error_response(
        self,
        error_response: ErrorResponse,
    ):
        error = (
            error_response.errors[0]
            if error_response.errors
            else None
        )

        status_code = self._determine_status_code(
            error_response=error_response,
            error=error,
        )

        message = (
            str(getattr(error, "detail", "An unexpected error occurred."))
            if error
            else "An unexpected error occurred."
        )

        self._log_error(
            status_code=status_code,
            message=message,
        )

        # Handle 500+
        if status_code >= 500:
            return BaseResult(
                status_code=500,
                message=(
                    "An unexpected error occurred on the server. "
                    "Please try again later."
                ),
                request_id=str(uuid.uuid4()),
            ).to_dict()

        # Handle throttling
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = self._extract_retry_after(message)

            response = BaseResult(
            status_code=429,
            message=(
                f"Too many requests. Please try again in "
                f"{format_duration(retry_after)}."
                if retry_after
                else "Too many requests. Please try again later."
            ),
            request_id=str(uuid.uuid4()),
        ).to_dict()

            response["retry_after"] = retry_after

            return response

        # Handle all other 4xx errors
        if error and getattr(error, "attr", None):
            message = f"{error.attr}: {error.detail}"

        return BaseResult(
            status_code=status_code,
            message=message,
            request_id=str(uuid.uuid4()),
        ).to_dict()

    def _determine_status_code(
        self,
        error_response: ErrorResponse,
        error,
    ) -> int:
        """
        Determine HTTP status code from DRF Standardized Errors.
        """

        if error:
            code = getattr(error, "code", None)

            if code == "throttled":
                return HTTPStatus.TOO_MANY_REQUESTS

            if code == "not_authenticated":
                return HTTPStatus.UNAUTHORIZED

            if code == "permission_denied":
                return HTTPStatus.FORBIDDEN

            if code == "not_found":
                return HTTPStatus.NOT_FOUND

            if error_response.type.value == "client_error":
                return HTTPStatus.BAD_REQUEST

        return HTTPStatus.INTERNAL_SERVER_ERROR

    def _extract_retry_after(
        self,
        message: str,
    ):
        """
        Extract retry seconds from:
        'Request was throttled. Expected available in 59 seconds.'
        """

        try:
            import re

            match = re.search(
                r"(\d+)\s+seconds?",
                message,
            )

            if match:
                return int(match.group(1))

        except Exception:
            pass

        return None

    def _log_error(
        self,
        *,
        status_code: int,
        message: str,
    ):
        """
        Log only server errors as ERROR.
        Client errors are expected behaviour.
        """

        op = OperationLogger(
            "ExceptionFormatter",
            status_code=status_code,
        )

        if status_code >= 500:
            op.fail(
                f"API Error [{status_code}]: {message}",
                exc=None,
            )