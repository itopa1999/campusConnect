from apps.users.models import ContactReport
from utils.base_result import BaseResultWithData
from django.utils import timezone

from utils.enums import IssueTypeEnum

class ReportCommand:
    @staticmethod
    def Add(request, validated_data):
        try:
            # Extract fields
            reporter_name = validated_data.get('reporter_name', '').strip()
            reporter_email = validated_data.get('reporter_email', '').strip()
            issue_type = validated_data.get('issue_type', '').strip()
            message = validated_data.get('message', '').strip()
            listing_identifier = validated_data.get('listing_identifier', '').strip()
            reported_user_email = validated_data.get('reported_user_email', '').strip()

            if not reporter_name:
                return BaseResultWithData(
                    message="Reporter name is required.",
                    data=None,
                    status_code=400
                )

            if not reporter_email:
                return BaseResultWithData(
                    message="Reporter email is required.",
                    data=None,
                    status_code=400
                )

            # is_valid, message = validate_ui_email(reporter_email)
            # if not is_valid:
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            allowed_types = [choice[0] for choice in IssueTypeEnum.choices()]
            if not issue_type or issue_type not in allowed_types:
                return BaseResultWithData(
                    message="Invalid or missing issue type.",
                    data=None,
                    status_code=400
                )

            if issue_type == IssueTypeEnum.REPORT_LISTING.value and not listing_identifier:
                return BaseResultWithData(
                    message="Listing URL or title is required when reporting a listing.",
                    data=None,
                    status_code=400
                )
            if issue_type == IssueTypeEnum.REPORT_USER.value and not reported_user_email:
                return BaseResultWithData(
                    message="Email of the reported user is required.",
                    data=None,
                    status_code=400
                )

            if not message:
                return BaseResultWithData(
                    message="Message cannot be empty.",
                    data=None,
                    status_code=400
                )

            report = ContactReport.objects.create(
                reporter_name=reporter_name,
                reporter_email=reporter_email,
                issue_type=issue_type,
                listing_identifier=listing_identifier,
                reported_user_email=reported_user_email,
                message=message,
                is_reviewed=False,
            )

            return BaseResultWithData(
                message="Thank you. Your report has been submitted. We will review it within 48 hours.",
                data={
                    "report_id": report.id,
                    "issue_type": issue_type,
                },
                status_code=201
            )
        except Exception as e:
            return BaseResultWithData(
                message=f"Unable to submit report: {str(e)}",
                data=None,
                status_code=500
            )