import re

FAQ_KNOWLEDGE_BASE = [
    {
        'id': 'submission_steps',
        'keywords': ['submit', 'submission', 'steps', 'how to apply', 'new application', 'process', 'procedure'],
        'title': 'SmartFlow Application Submission Process',
        'answer': """Use these SmartFlow portal steps:
1. **Complete Profile**: Enter institution and campus information.
2. **Declare Programmes & Faculty**: Add the records requested by the portal.
3. **Upload Documents**: Review the applicable checklist and upload supporting records.
4. **Submit Application**: Review the portal's checks and submit for officer scrutiny. A tracking number is generated.""",
        'source': 'AICTE SmartFlow workflow guidance; not a regulatory source',
        'recommended_action': 'Go to New Application (/applications/new/) to initiate your submission.'
    },
    {
        'id': 'required_documents',
        'keywords': ['documents', 'required documents', 'certificates', 'upload', 'mandatory', 'noc', 'land deed', 'fire safety'],
        'title': 'Supporting Document Checklist',
        'answer': """Document categories shown in the portal are workflow categories, not a definitive statement of current AICTE requirements. Check the application's configured, source-verified rules and any officer clarification. When no verified rule is configured, the item requires manual review.""",
        'source': 'AICTE SmartFlow portal guidance; verify current requirements with AICTE',
        'recommended_action': 'Check the Documents tab on your application page to upload or view verification status.'
    },
    {
        'id': 'status_meanings',
        'keywords': ['status', 'draft', 'in scrutiny', 'deficiency', 'flagged', 'meaning', 'workflow', 'approved', 'rejected'],
        'title': 'SmartFlow Workflow Status Definitions',
        'answer': """These are SmartFlow workflow statuses:
- **DRAFT**: Application created by institution; editable; not yet received by AICTE.
- **SUBMITTED**: Formally submitted by institution; locked from ordinary editing; awaiting scrutiny assignment.
- **IN_SCRUTINY**: Assigned to a Scrutiny Officer; documents and regulatory norms are actively under review.
- **DEFICIENCY_FLAGGED**: Reviewer flagged missing records or non-compliance; application returned to institution for clarification and document re-upload.
- **APPROVED**: The application was approved within the SmartFlow workflow.
- **REJECTED**: The application was rejected within the SmartFlow workflow.""",
        'source': 'AICTE SmartFlow workflow definitions; not a statutory decision',
        'recommended_action': 'Check your Dashboard for real-time status updates.'
    },
    {
        'id': 'respond_deficiency',
        'keywords': ['deficiency', 'respond', 'clarification', 'flagged', 'fix deficiency', 'replace document', 'resubmit'],
        'title': 'How to Respond to Flagged Deficiencies',
        'answer': """When your application is in 'DEFICIENCY_FLAGGED' status:
1. Open your application detail page and review the **Scrutiny Officer Deficiency Notes**.
2. If document defects were flagged, click **Replace Document** next to the deficient file. This increments the document to Version 2.
3. If profile data needed corrections, update your Institution, Faculty, or Course records.
4. In the **Deficiency Response** section, enter a comprehensive explanation detailing the actions taken.
5. Click **Submit Clarification Response**. The application returns to 'IN_SCRUTINY' for officer re-evaluation.""",
        'source': 'AICTE SmartFlow workflow guidance',
        'recommended_action': 'Navigate to your flagged application to submit clarifications and replacements.'
    },
    {
        'id': 'contact_officer',
        'keywords': ['contact', 'officer', 'regional office', 'phone', 'email', 'grievance', 'helpdesk', 'support'],
        'title': 'Contacting the Scrutiny Officer & Regional Offices',
        'answer': """For application-specific clarification, use the officer and regional office details displayed in your portal, if available. For official contact information, consult the current AICTE website. This help desk does not provide or verify external email addresses.""",
        'source': 'AICTE SmartFlow support guidance; external contacts are not verified here',
        'recommended_action': 'Open your application to view any assigned officer, or consult AICTE official contact information.'
    },
]


def search_faq(query_text):
    """
    Rule-based fuzzy search matching user query keywords against SmartFlow FAQ items.
    Returns matched item or standard advisory response.
    """
    query_clean = query_text.lower().strip()
    if not query_clean:
        return None

    best_match = None
    highest_score = 0

    for item in FAQ_KNOWLEDGE_BASE:
        score = 0
        for kw in item['keywords']:
            if kw in query_clean:
                score += len(kw.split()) * 3
            elif any(w in query_clean for w in kw.split()):
                score += 1

        if score > highest_score:
            highest_score = score
            best_match = item

    if highest_score > 0 and best_match:
        return {
            'found': True,
            'title': best_match['title'],
            'answer': best_match['answer'],
            'source': best_match['source'],
            'recommended_action': best_match['recommended_action'],
            'disclaimer': 'SmartFlow guidance only; confirm current requirements with AICTE or your authorized scrutiny officer.'
        }

    return {
        'found': False,
        'title': 'General AICTE SmartFlow Guidance',
        'answer': f"We could not locate an exact match for '{query_text}'. Common topics include: portal submission steps, supporting document checklist, workflow status, or responding to deficiencies.",
        'source': 'AICTE SmartFlow help center',
        'recommended_action': 'Select one of the suggested quick questions or contact your Regional Office directly.',
        'disclaimer': 'SmartFlow guidance only; confirm current requirements with AICTE or your authorized scrutiny officer.'
    }
