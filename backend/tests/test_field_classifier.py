from app.services.browser_automation.field_classifier import (
    ApplicantProfile,
    DetectedField,
    FieldCategory,
    PauseReason,
    build_fill_plan,
    classify_field,
    page_has_auth_signal,
    page_has_captcha_signal,
)

PROFILE = ApplicantProfile(
    full_name="Jane Doe",
    email="jane@example.com",
    phone="555-1234",
    linkedin_url="https://linkedin.com/in/janedoe",
    portfolio_url="https://janedoe.dev",
    resume_file_path="/tmp/resume.pdf",
    cover_letter_text="Dear hiring team...",
)


def test_classify_email_field():
    field = DetectedField(label="Email Address", input_type="email")
    assert classify_field(field) == FieldCategory.EMAIL


def test_classify_phone_field():
    field = DetectedField(label="Mobile Phone", input_type="tel")
    assert classify_field(field) == FieldCategory.PHONE


def test_classify_first_name_before_generic_name():
    field = DetectedField(label="First Name", input_type="text")
    assert classify_field(field) == FieldCategory.FIRST_NAME


def test_classify_bare_name_falls_back_to_full_name():
    field = DetectedField(label="Name", input_type="text")
    assert classify_field(field) == FieldCategory.FULL_NAME


def test_classify_linkedin_field():
    field = DetectedField(label="LinkedIn Profile URL", input_type="text", name="linkedin_url")
    assert classify_field(field) == FieldCategory.LINKEDIN_URL


def test_classify_unrecognized_field_is_unknown():
    field = DetectedField(label="What's your favorite color?", input_type="text")
    assert classify_field(field) == FieldCategory.UNKNOWN


def test_password_field_always_unknown_for_direct_classification():
    # Password fields are handled as an auth pause signal at the plan
    # level, never filled - classify_field itself just returns UNKNOWN.
    field = DetectedField(label="Password", input_type="password")
    assert classify_field(field) == FieldCategory.UNKNOWN


def test_page_auth_signal_detection():
    assert page_has_auth_signal("Please sign in to continue") is True
    assert page_has_auth_signal("Tell us about your experience") is False


def test_page_captcha_signal_detection():
    assert page_has_captcha_signal('<div class="g-recaptcha"></div>') is True
    assert page_has_captcha_signal("<p>Normal application form</p>") is False


def test_fill_plan_fills_known_fields():
    fields = [
        DetectedField(label="Full Name", input_type="text", required=True),
        DetectedField(label="Email", input_type="email", required=True),
        DetectedField(label="Phone Number", input_type="tel", required=False),
    ]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason is None
    filled_labels = {f.label for f, _ in plan.fills}
    assert filled_labels == {"Full Name", "Email", "Phone Number"}


def test_fill_plan_pauses_on_password_field():
    fields = [
        DetectedField(label="Email", input_type="email"),
        DetectedField(label="Password", input_type="password"),
    ]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason == PauseReason.AUTH
    # Only the email fill (before the password field) should be queued.
    assert len(plan.fills) == 1


def test_fill_plan_pauses_on_required_unknown_field():
    fields = [
        DetectedField(label="Email", input_type="email", required=True),
        DetectedField(
            label="Describe a challenge you overcame", input_type="textarea", required=True
        ),
    ]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason == PauseReason.UNKNOWN_REQUIRED_FIELD
    assert "challenge" in plan.pause_detail.lower()


def test_fill_plan_skips_non_required_unknown_field_without_pausing():
    fields = [
        DetectedField(label="Email", input_type="email", required=True),
        DetectedField(label="How did you hear about us?", input_type="text", required=False),
    ]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason is None
    assert len(plan.fills) == 1  # only email; the optional unknown field is skipped


def test_fill_plan_pauses_on_resume_upload_without_a_resume_file():
    no_resume_profile = ApplicantProfile(full_name="Jane Doe", email="jane@example.com")
    fields = [DetectedField(label="Upload your resume", input_type="file", required=True)]

    plan = build_fill_plan(fields, no_resume_profile)

    assert plan.pause_reason == PauseReason.UNKNOWN_REQUIRED_FIELD
    assert "resume" in plan.pause_detail.lower()


def test_fill_plan_fills_resume_upload_when_available():
    fields = [DetectedField(label="Upload your resume", input_type="file", required=True)]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason is None
    assert plan.fills[0][1] == "/tmp/resume.pdf"


def test_fill_plan_never_fills_password_fields_even_if_labeled_confusingly():
    """Safety-critical: even if a password field happened to match a known
    keyword pattern in its label, the password input_type check must win."""
    fields = [DetectedField(label="Confirm your name/password", input_type="password")]
    plan = build_fill_plan(fields, PROFILE)

    assert plan.pause_reason == PauseReason.AUTH
    assert len(plan.fills) == 0
