from apps.users.models import ContactReport
from utils.Tasks.backgroundTask import background_task_send_report_recieved_email
from utils.base_result import BaseResultWithData
from utils.enums import IssueTypeEnum
from utils.log_helpers import OperationLogger


class ReportCommand:
    @staticmethod
    def Add(request, validated_data) -> BaseResultWithData:
        op = OperationLogger("ReportCommand.Add",
                             reporter_email=validated_data.get('reporter_email'),
                             issue_type=validated_data.get('issue_type'))
        op.start()
        try:
            issue_type = validated_data.get('issue_type')
            message = validated_data.get('message', '').strip()
            listing_identifier = validated_data.get('listing_identifier', '').strip()
            reported_user_identifer = validated_data.get('reported_user_identifer', '').strip()
            reporter_name = validated_data.get('reporter_name', '').strip()
            reporter_email = validated_data.get('reporter_email', '').strip()

            # ─── Validation ────────────────────────────────────────────
            if not issue_type or issue_type not in [c[0] for c in IssueTypeEnum.choices()]:
                op.fail(f"Invalid issue type: {issue_type}")
                return BaseResultWithData(message="Invalid or missing issue type.", status_code=400)

            if issue_type == IssueTypeEnum.REPORT_LISTING.value and not listing_identifier:
                op.fail("Missing listing identifier")
                return BaseResultWithData(message="Listing identifier is required for listing reports.", status_code=400)

            if issue_type == IssueTypeEnum.REPORT_USER.value and not reported_user_identifer:
                op.fail("Missing reported user identifier")
                return BaseResultWithData(message="User identifier is required for user reports.", status_code=400)

            if not message:
                op.fail("Message is empty")
                return BaseResultWithData(message="Message cannot be empty.", status_code=400)

            # ─── Determine reporter ────────────────────────────────────
            reporter = None
            if request.user and request.user.is_authenticated:
                reporter = request.user
            elif not reporter_name or not reporter_email:
                op.fail("Anonymous reporter requires name and email")
                return BaseResultWithData(message="Reporter name and email are required for anonymous reports.", status_code=400)

            # ─── Create report ─────────────────────────────────────────
            report = ContactReport.objects.create(
                reporter=reporter,
                reporter_name=reporter_name if not reporter else '',
                reporter_email=reporter_email if not reporter else '',
                issue_type=issue_type,
                listing_identifier=listing_identifier,
                reported_user_identifer=reported_user_identifer,
                message=message,
                is_reviewed=False,
            )

            # ─── Queue notification (optional) ────────────────────────
            try:
                background_task_send_report_recieved_email.delay(
                    reporter_email or (reporter.email if reporter else ''),
                    reporter_name or (reporter.get_full_name() or reporter.username if reporter else 'Anonymous'),
                    issue_type
                )
            except Exception as e:
                op.fail(f"Error queuing email: {str(e)}")
            else:
                op.success("Report submitted successfully")

            return BaseResultWithData(
                message="Thank you. Your report has been submitted. We will review it within 48 hours.",
                data={"report_id": report.id, "issue_type": issue_type},
                status_code=201
            )

        except Exception as e:
            op.fail("Unable to submit report", exc=e)
            return BaseResultWithData(
                message=f"Unable to submit report: {str(e)}",
                status_code=500
            )