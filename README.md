TODO: 

------TEST---------
1. All logic utilis and ever functions please app after apps

1. add refeerall 



Seconds	Time
60	1 minute
300	5 minutes
600	10 minutes
1800	30 minutes
3600	1 hour
7200	2 hours
21600	6 hours
43200	12 hours
86400	24 hours



<!-- Todo -->

Strong additions
Type	Purpose	Example
JOB	Part-time/student employment	"Part-time graphic designer needed"
EVENT	Promote a campus event	"Tech Meetup — Saturday"



class JobListing(BaseModel):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="job_details",
    )

    employment_type = models.CharField(
        max_length=50,
    )

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    application_deadline = models.DateField(
        null=True,
        blank=True,
    )

    requirements = models.TextField(
        blank=True,
        null=True,
    )

# working_hours
# experience_required
# remote
# company
# application_url


<!-- TODO -->
check the email template to have standard for all others
