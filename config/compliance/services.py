import math
from django.utils import timezone
from .models import ComplianceRule, ComplianceResult


def seed_default_compliance_rules():
    """Compatibility helper; regulatory rules require a verified administrator source."""
    return []

class ComplianceEngine:
    """
    Evaluates application data against active, source-verified rules and manual review.
    """

    @staticmethod
    def _active_rule(parameter_name, application):
        rules = ComplianceRule.objects.filter(
            parameter_name=parameter_name,
            is_active=True,
            is_source_verified=True,
            effective_date__lte=timezone.localdate(),
        )
        categories = set()
        if application.institution_id:
            institution = application.institution
            course_model = institution.courses.model
            categories = {
                label.casefold()
                for _code, label in course_model.PROGRAMME_CHOICES
            }
            categories.update(
                code.casefold()
                for code in institution.courses.values_list('programme', flat=True)
            )

        applicable_rules = []
        for rule in rules:
            category = rule.programme_category.strip().casefold()
            if not category or category == 'all':
                applicable_rules.append((0, rule))
            elif category in categories:
                applicable_rules.append((1, rule))

        if not applicable_rules:
            return None
        return max(
            applicable_rules,
            key=lambda item: (item[0], item[1].effective_date, item[1].pk),
        )[1]

    @classmethod
    def evaluate_application(cls, application):
        """Runs all applicable active compliance rules for an application."""
        # Clear existing cached results for clean refresh
        application.compliance_results.all().delete()

        inst = application.institution
        results = []

        missing_fields = []
        for field_name, field_value in (
            ('Institution name', application.institution_name),
            ('Academic year', application.academic_year),
        ):
            if not field_value or not field_value.strip():
                missing_fields.append(field_name)
        if application.total_intake <= 0:
            missing_fields.append('Total proposed student intake')
        if application.total_faculty <= 0:
            missing_fields.append('Total teaching faculty')

        if inst:
            for field_name, field_value in (
                ('Institution profile name', inst.name),
                ('State', inst.state),
                ('District', inst.district),
            ):
                if not field_value or not field_value.strip():
                    missing_fields.append(field_name)
        else:
            results.append(cls._manual_review_result(
                application,
                'Institution Profile Linkage',
                'ADMINISTRATIVE',
                'No institution profile is linked to this application; verify the institution details manually.'
            ))

        results.append(ComplianceResult.objects.create(
            application=application,
            check_name='Required Application & Profile Fields',
            category='ADMINISTRATIVE',
            status='FAIL' if missing_fields else 'PASS',
            explanation=(
                f"Missing required information: {', '.join(missing_fields)}."
                if missing_fields else 'Required application and linked profile fields are present.'
            ),
            evidence_field=(
                f"Missing: {', '.join(missing_fields)}" if missing_fields
                else 'Application and institution profile fields checked'
            ),
            suggested_action='Complete the missing application or institution profile fields before submission.'
            if missing_fields else '',
        ))

        # 1. Faculty-to-Student Ratio Check
        rule_sfr = cls._active_rule('student_faculty_ratio', application)
        if not rule_sfr:
            results.append(cls._manual_review_result(
                application,
                'Student-to-Faculty Ratio (SFR)',
                'FACULTY',
                'No active regulatory threshold found in system config. Manual officer evaluation required.'
            ))
        else:
            intake = application.total_intake
            faculty = application.total_faculty

            if inst and inst.faculty_members.exists():
                faculty = inst.faculty_members.count()
            if inst and inst.total_proposed_intake > 0:
                intake = inst.total_proposed_intake

            if faculty == 0:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_sfr,
                    check_name='Student-to-Faculty Ratio (SFR)',
                    category='FACULTY',
                    status='FAIL',
                    explanation='No faculty members are declared, so the configured student-to-faculty check cannot pass.',
                    evidence_field=f'Declared Faculty: 0, Total Student Intake: {intake}',
                    suggested_action='Appoint and submit credentials for qualified teaching faculty as per cadre ratio.',
                    regulatory_reference=rule_sfr.regulatory_reference
                ))
            else:
                ratio = intake / faculty
                threshold = rule_sfr.threshold_value  # 20.0
                if ratio <= threshold:
                    results.append(ComplianceResult.objects.create(
                        application=application,
                        rule=rule_sfr,
                        check_name='Student-to-Faculty Ratio (SFR)',
                        category='FACULTY',
                        status='PASS',
                        explanation=f'Student-to-Faculty ratio is 1:{ratio:.1f}, within the configured maximum of 1:{threshold:.0f}.',
                        evidence_field=f'{faculty} faculty for {intake} student intake (1:{ratio:.1f})',
                        suggested_action='Maintain cadre ratio across all academic departments.',
                        regulatory_reference=rule_sfr.regulatory_reference
                    ))
                else:
                    results.append(ComplianceResult.objects.create(
                        application=application,
                        rule=rule_sfr,
                        check_name='Student-to-Faculty Ratio (SFR)',
                        category='FACULTY',
                        status='FAIL',
                        explanation=f'Student-to-Faculty ratio is 1:{ratio:.1f}, exceeding the allowable limit of 1:{threshold:.0f}.',
                        evidence_field=f'{faculty} faculty for {intake} student intake (1:{ratio:.1f})',
                        suggested_action=f'Appoint at least {int(intake / threshold) - faculty + 1} additional regular faculty members.',
                        regulatory_reference=rule_sfr.regulatory_reference
                    ))

        # 2. Land Requirement Check
        rule_land = cls._active_rule('min_land_acres', application)
        if not rule_land or not inst:
            results.append(cls._manual_review_result(
                application,
                'Land Area Verification',
                'LAND_BUILDING',
                'Institution profile land data requires scrutiny officer manual inspection.'
            ))
        else:
            land_acres = inst.land_area_acres
            if land_acres >= rule_land.threshold_value:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_land,
                    check_name='Land Area Verification',
                    category='LAND_BUILDING',
                    status='PASS',
                    explanation=f'Possesses {land_acres} acres of contiguous land, meeting the configured threshold of {rule_land.threshold_value} acres.',
                    evidence_field=f'Land Area: {land_acres} acres, Ownership: {inst.get_land_ownership_type_display()}',
                    suggested_action='Ensure land title deed and revenue boundary sketch remain clear of encumbrances.',
                    regulatory_reference=rule_land.regulatory_reference
                ))
            else:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_land,
                    check_name='Land Area Verification',
                    category='LAND_BUILDING',
                    status='FAIL',
                    explanation=f'Possesses {land_acres} acres, which is below the minimum required {rule_land.threshold_value} acres.',
                    evidence_field=f'Land Area: {land_acres} acres',
                    suggested_action=f'Procure and register required contiguous land to reach at least {rule_land.threshold_value} acres.',
                    regulatory_reference=rule_land.regulatory_reference
                ))

        # 3. Built-Up Area Check
        rule_builtup = cls._active_rule('min_builtup_sqm', application)
        if not rule_builtup or not inst:
            results.append(cls._manual_review_result(
                application,
                'Instructional Built-up Area',
                'LAND_BUILDING',
                'Built-up area requires architect completion drawing verification.'
            ))
        else:
            sqm = inst.built_up_area_sqm
            if sqm >= rule_builtup.threshold_value:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_builtup,
                    check_name='Instructional Built-up Area',
                    category='LAND_BUILDING',
                    status='PASS',
                    explanation=f'Declared built-up area of {sqm:.0f} sq.m complies with minimum threshold of {rule_builtup.threshold_value:.0f} sq.m.',
                    evidence_field=f'Built-up Area: {sqm:.0f} sq.m',
                    suggested_action='Verify barrier-free access and fire exits across all floors.',
                    regulatory_reference=rule_builtup.regulatory_reference
                ))
            else:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_builtup,
                    check_name='Instructional Built-up Area',
                    category='LAND_BUILDING',
                    status='WARNING',
                    explanation=f'Declared built-up area ({sqm:.0f} sq.m) is less than the recommended {rule_builtup.threshold_value:.0f} sq.m.',
                    evidence_field=f'Built-up Area: {sqm:.0f} sq.m',
                    suggested_action='Upload approved expansion plan or local authority building sanction.',
                    regulatory_reference=rule_builtup.regulatory_reference
                ))

        # 4. Mandatory Regulatory Documentation Check
        rule_docs = cls._active_rule('mandatory_doc_count', application)
        mandatory_types = [
            ('LAND_DEED', 'Land Title & Ownership Deed'),
            ('BUILDING_PLAN', 'Approved Building Plan & Occupancy Certificate'),
            ('FIRE_SAFETY', 'Fire Safety Certificate (NOC)'),
            ('AFFILIATION_NOC', 'State Govt / Affiliating University NOC'),
            ('FACULTY_RECORDS', 'Faculty List & Form 16'),
            ('LAB_INVENTORY', 'Laboratory Equipment Inventory'),
        ]

        uploaded_types = set(application.documents.filter(
            verification_status='VERIFIED'
        ).values_list('document_type', flat=True))
        missing_docs = [name for doc_type, name in mandatory_types if doc_type not in uploaded_types]
        verified_required_count = len(mandatory_types) - len(missing_docs)
        required_doc_count = math.ceil(rule_docs.threshold_value) if rule_docs else 0

        if not rule_docs:
            results.append(cls._manual_review_result(
                application,
                'Mandatory Regulatory Documentation',
                'DOCUMENTATION',
                (
                    f"Missing or unverified document categories: {', '.join(missing_docs)}. "
                    if missing_docs else ''
                ) + 'No active documentation rule is configured; confirm requirements during manual scrutiny.'
            ))
        elif verified_required_count >= required_doc_count:
            results.append(ComplianceResult.objects.create(
                application=application,
                rule=rule_docs,
                check_name='Mandatory Regulatory Documentation',
                category='DOCUMENTATION',
                status='PASS',
                explanation=(
                    f'{verified_required_count} configured document categories have been verified; '
                    f'the configured minimum is {required_doc_count}.'
                ),
                evidence_field=f'{verified_required_count} verified categories',
                suggested_action='Proceed to scrutiny officer verification.',
                regulatory_reference=rule_docs.regulatory_reference
            ))
        else:
            results.append(ComplianceResult.objects.create(
                application=application,
                rule=rule_docs,
                check_name='Mandatory Regulatory Documentation',
                category='DOCUMENTATION',
                status='FAIL' if rule_docs.is_mandatory else 'WARNING',
                explanation=(
                    f'{verified_required_count} verified categories; configured minimum is '
                    f'{required_doc_count}. Missing or unverified: {", ".join(missing_docs)}.'
                ),
                evidence_field=f'Missing or unverified: {", ".join(missing_docs)}',
                suggested_action='Upload missing documents and request officer verification.',
                regulatory_reference=rule_docs.regulatory_reference
            ))

        # 5. Document Expiry Check
        expired_docs = []
        today = timezone.now().date()
        for doc in application.documents.filter(expiry_date__isnull=False):
            if doc.expiry_date < today:
                expired_docs.append(f"{doc.title} (expired on {doc.expiry_date})")

        rule_validity = cls._active_rule('fire_safety_active', application)
        fire_safety_docs = application.documents.filter(
            document_type='FIRE_SAFETY',
            verification_status='VERIFIED',
        )
        fire_safety_docs_without_expiry = fire_safety_docs.filter(
            expiry_date__isnull=True
        ).exists()
        expired_fire_safety_docs = [
            f"{doc.title} (expired on {doc.expiry_date})"
            for doc in fire_safety_docs.filter(expiry_date__lt=today)
        ]
        if not rule_validity:
            results.append(cls._manual_review_result(
                application,
                'Certificate Expiry & Statutory Validity',
                'ADMINISTRATIVE',
                (
                    f"Expired document dates were found: {', '.join(expired_docs)}. "
                    if expired_docs else ''
                ) + 'No active, source-verified validity rule is configured; confirm applicability during scrutiny.'
            ))
        elif not fire_safety_docs.exists() or fire_safety_docs_without_expiry:
            results.append(cls._manual_review_result(
                application,
                'Certificate Expiry & Statutory Validity',
                'ADMINISTRATIVE',
                'A verified fire safety certificate with an expiry date is unavailable; officer review is required.'
            ))
        elif expired_fire_safety_docs:
            results.append(ComplianceResult.objects.create(
                application=application,
                rule=rule_validity,
                check_name='Certificate Expiry & Statutory Validity',
                category='ADMINISTRATIVE',
                status='FAIL',
                explanation=f'The following verified fire safety certificates have expired: {", ".join(expired_fire_safety_docs)}.',
                evidence_field=f'{len(expired_fire_safety_docs)} expired fire safety certificates',
                suggested_action='Obtain renewed NOC certificates from competent authorities and upload replacements.',
                regulatory_reference=rule_validity.regulatory_reference
            ))
        else:
            results.append(ComplianceResult.objects.create(
                application=application,
                rule=rule_validity,
                check_name='Certificate Expiry & Statutory Validity',
                category='ADMINISTRATIVE',
                status='PASS',
                explanation='All submitted certificates with declared expiry dates are currently valid.',
                evidence_field='Zero expired certificates detected',
                suggested_action='Keep track of upcoming renewals before start of academic session.',
                regulatory_reference=rule_validity.regulatory_reference
            ))

        # 6. Library & Laboratory Norms
        rule_lib = cls._active_rule('min_library_volumes', application)
        if not inst or not rule_lib:
            results.append(cls._manual_review_result(
                application,
                'Library Resources',
                'ACADEMIC',
                'Library data or an active configured threshold is unavailable; officer review is required.'
            ))
        else:
            lib_vols = inst.library_volumes
            if lib_vols >= rule_lib.threshold_value:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_lib,
                    check_name='Library Volumes & Resources',
                    category='ACADEMIC',
                    status='PASS',
                    explanation=f'Library possesses {lib_vols} volumes, meeting the configured minimum of {rule_lib.threshold_value:.0f} volumes.',
                    evidence_field=f'Titles: {inst.library_titles}, Volumes: {lib_vols}',
                    suggested_action='Ensure digital library e-journal access subscriptions are up to date.',
                    regulatory_reference=rule_lib.regulatory_reference
                ))
            else:
                results.append(ComplianceResult.objects.create(
                    application=application,
                    rule=rule_lib,
                    check_name='Library Volumes & Resources',
                    category='ACADEMIC',
                    status='WARNING',
                    explanation=f'Library volume count ({lib_vols}) is below the configured threshold of {rule_lib.threshold_value:.0f}.',
                    evidence_field=f'Volumes: {lib_vols}',
                    suggested_action='Acquire additional required textbook volumes and technical subscriptions.',
                    regulatory_reference=rule_lib.regulatory_reference
                ))

        rule_labs = cls._active_rule('min_laboratories', application)
        if not rule_labs or not inst:
            results.append(cls._manual_review_result(
                application,
                'Laboratory Infrastructure',
                'ACADEMIC',
                'Laboratory data or an active configured threshold is unavailable; officer review is required.'
            ))
        else:
            meets_lab_threshold = inst.total_laboratories >= rule_labs.threshold_value
            results.append(ComplianceResult.objects.create(
                application=application,
                rule=rule_labs,
                check_name='Laboratory Infrastructure',
                category='ACADEMIC',
                status='PASS' if meets_lab_threshold else 'WARNING',
                explanation=(
                    f'Declared laboratory count ({inst.total_laboratories}) meets the configured threshold '
                    f'of {rule_labs.threshold_value:.0f}.'
                    if meets_lab_threshold else
                    f'Declared laboratory count ({inst.total_laboratories}) is below the configured threshold '
                    f'of {rule_labs.threshold_value:.0f}.'
                ),
                evidence_field=f'Declared laboratories: {inst.total_laboratories}',
                suggested_action='Verify laboratory availability and equipment records during scrutiny.',
                regulatory_reference=rule_labs.regulatory_reference,
            ))

        return results

    @classmethod
    def _manual_review_result(cls, application, check_name, category, explanation):
        return ComplianceResult.objects.create(
            application=application,
            check_name=check_name,
            category=category,
            status='MANUAL_REVIEW_REQUIRED',
            explanation=explanation,
            evidence_field='Pending manual review',
            suggested_action='A qualified reviewer must verify this item against the currently applicable requirements.',
            regulatory_reference=''
        )
