from apps.users.models import ContactReport
from utils.Tasks.emailService import background_task_send_report_recieved_email
from utils.base_result import BaseResultWithData
from utils.enums import IssueTypeEnum
from utils.log_helpers import OperationLogger

class ReportCommand:
    @staticmethod
    def Add(request, validated_data)-> BaseResultWithData:
        reporter_name = validated_data.get('reporter_name', '').strip()
        reporter_email = validated_data.get('reporter_email', '').strip()
        issue_type = validated_data.get('issue_type', '').strip()
        message = validated_data.get('message', '').strip()
        listing_identifier = validated_data.get('listing_identifier', '').strip()
        reported_user_email = validated_data.get('reported_user_email', '').strip()
        op = OperationLogger("ReportCommand.Add", reporter_email=reporter_email, issue_type=issue_type)
        op.start()
        try:
            if not reporter_name:
                op.fail("[ReportCommand.Add] Reporter name is required")
                return BaseResultWithData(
                    message="Reporter name is required.",
                    data=None,
                    status_code=400
                )

            if not reporter_email:
                op.fail("[ReportCommand.Add] Reporter email is required")
                return BaseResultWithData(
                    message="Reporter email is required.",
                    data=None,
                    status_code=400
                )

            # is_valid, message = validate_ui_email(reporter_email)
            # if not is_valid:
            #     op.fail(f"[ReportCommand.Add] Invalid reporter email: {reporter_email}")
            #     return BaseResultWithData(
            #         message=message,
            #         data=None,
            #         status_code=400
            #     )
            allowed_types = [choice[0] for choice in IssueTypeEnum.choices()]
            if not issue_type or issue_type not in allowed_types:
                op.fail(f"[ReportCommand.Add] Invalid issue type: {issue_type}")
                return BaseResultWithData(
                    message="Invalid or missing issue type.",
                    data=None,
                    status_code=400
                )

            if issue_type == IssueTypeEnum.REPORT_LISTING.value and not listing_identifier:
                op.fail("[ReportCommand.Add] Missing listing identifier for listing report")
                return BaseResultWithData(
                    message="Listing URL or title is required when reporting a listing.",
                    data=None,
                    status_code=400
                )
            if issue_type == IssueTypeEnum.REPORT_USER.value and not reported_user_email:
                op.fail("[ReportCommand.Add] Missing reported user email for user report")
                return BaseResultWithData(
                    message="Email of the reported user is required.",
                    data=None,
                    status_code=400
                )

            if not message:
                op.fail("[ReportCommand.Add] Report message cannot be empty")
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
            try:
                background_task_send_report_recieved_email.delay(reporter_email, reporter_name, issue_type)
            except Exception as e:
                op.fail(f"Error queuing report received email: {str(e)}")
            else:
                op.success("Report submitted successfully")
            return BaseResultWithData(
                message="Thank you. Your report has been submitted. We will review it within 48 hours.",
                data={
                    "report_id": report.id,
                    "issue_type": issue_type,
                },
                status_code=201
            )
        except Exception as e:
            op.fail("Unable to submit report", exc=e)
            return BaseResultWithData(
                message=f"Unable to submit report: {str(e)}",
                data=None,
                status_code=500
            )