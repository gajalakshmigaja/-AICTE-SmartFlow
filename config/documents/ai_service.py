import re
import os
from datetime import datetime
from django.utils import timezone
from .models import ApplicationDocument, AIDocumentAnalysis

# Graceful import of PyMuPDF
try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz
        PYMUPDF_AVAILABLE = True
    except ImportError:
        fitz = None
        PYMUPDF_AVAILABLE = False


def extract_text_from_file(file_path):
    """
    Extracts text from PDF or text file using PyMuPDF if available,
    with safe fallback to plain text parsing.
    """
    if not os.path.exists(file_path):
        return ""

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf' and PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(file_path)
            pages_text = []
            for i in range(min(len(doc), 10)):  # analyze first 10 pages
                pages_text.append(doc[i].get_text())
            doc.close()
            return "\n".join(pages_text)
        except Exception as e:
            return f"[PyMuPDF extraction note: {str(e)}]"

    # Fallback for plain text or if PyMuPDF not available
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read(20000)
    except Exception:
        return ""


def analyze_document_content(document):
    """
    Analyzes an uploaded ApplicationDocument against application data.
    Returns or updates an AIDocumentAnalysis instance.
    """
    app = document.application
    file_path = document.file.path if hasattr(document.file, 'path') else None

    extracted_text = ""
    if file_path and os.path.exists(file_path):
        extracted_text = extract_text_from_file(file_path)

    findings = []
    detected_dates = []
    detected_keywords = []
    confidence_points = 50  # base baseline

    # 1. Regex search for dates (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, or Month DD, YYYY)
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b',
        r'\b\d{4}-\d{2}-\d{2}\b'
    ]
    for pattern in date_patterns:
        matches = re.findall(pattern, extracted_text, re.IGNORECASE)
        for m in matches:
            if m not in detected_dates:
                detected_dates.append(m)

    # 2. Check for keywords based on document_type
    type_keywords = {
        'LAND_DEED': ['land', 'survey', 'deed', 'khasra', 'acres', 'hectares', 'ownership', 'registration', 'patta'],
        'BUILDING_PLAN': ['building', 'occupancy', 'completion', 'structural', 'built-up', 'sqm', 'sq.ft', 'architect'],
        'FIRE_SAFETY': ['fire', 'safety', 'noc', 'extinguisher', 'validity', 'rescue', 'hazard', 'combustion'],
        'AFFILIATION_NOC': ['affiliation', 'university', 'government', 'sanction', 'noc', 'approval', 'resolution'],
        'FACULTY_RECORDS': ['faculty', 'professor', 'salary', 'form 16', 'epf', 'joining', 'qualification', 'ph.d'],
        'LAB_INVENTORY': ['laboratory', 'equipment', 'computer', 'software', 'machinery', 'make', 'model', 'calibration'],
        'LIBRARY_REGISTER': ['library', 'books', 'volumes', 'titles', 'journals', 'subscription', 'delnet', 'ieee'],
        'BARRIER_FREE_CERT': ['barrier-free', 'ramp', 'lift', 'disabled', 'differently-abled', 'wheelchair', 'accessible'],
        'ENDOWMENT_FUND': ['fdr', 'endowment', 'deposit', 'bank', 'audit', 'balance sheet', 'corpus fund'],
    }

    expected_keywords = type_keywords.get(document.document_type, ['aicte', 'institution', 'approval'])
    matched_keywords = []
    for kw in expected_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', extracted_text, re.IGNORECASE):
            matched_keywords.append(kw)

    detected_keywords = matched_keywords

    if matched_keywords:
        confidence_points += min(len(matched_keywords) * 7, 30)
        findings.append({
            'category': 'Keyword Verification',
            'severity': 'INFO',
            'message': f"Matched {len(matched_keywords)} relevant regulatory keywords: {', '.join(matched_keywords[:6])}."
        })
    else:
        findings.append({
            'category': 'Keyword Verification',
            'severity': 'WARNING',
            'message': f"Expected keywords for {document.get_document_type_display()} were not distinctly detected. Scrutiny officer manual review advised."
        })

    # 3. Check for Institution Name alignment
    inst_name_words = [w for w in app.institution_name.split() if len(w) > 3]
    name_matches = 0
    for word in inst_name_words:
        if re.search(r'\b' + re.escape(word) + r'\b', extracted_text, re.IGNORECASE):
            name_matches += 1

    status = 'PASS'
    if inst_name_words:
        match_ratio = name_matches / len(inst_name_words)
        if match_ratio >= 0.5:
            confidence_points += 15
            findings.append({
                'category': 'Institution Match',
                'severity': 'PASS',
                'message': f"Document references institution naming pattern matching '{app.institution_name}'."
            })
        elif match_ratio > 0:
            findings.append({
                'category': 'Institution Match',
                'severity': 'WARNING',
                'message': f"Partial match found for institution name ({name_matches}/{len(inst_name_words)} terms matched). Verify that the legal title matches."
            })
            status = 'MANUAL_REVIEW_REQUIRED'
        else:
            findings.append({
                'category': 'Institution Match',
                'severity': 'WARNING',
                'message': f"Institution name '{app.institution_name}' was not detected in extracted text. Could be a scanned image or differing legal entity name."
            })
            status = 'MANUAL_REVIEW_REQUIRED'

    # 4. Expiry Date check if applicable (e.g. Fire Safety)
    if document.expiry_date:
        if document.expiry_date < timezone.now().date():
            status = 'MISMATCH_DETECTED'
            confidence_points -= 20
            findings.append({
                'category': 'Certificate Validity',
                'severity': 'FAIL',
                'message': f"The recorded certificate expiry date ({document.expiry_date.strftime('%d-%b-%Y')}) has lapsed. Active certificate required."
            })
        else:
            findings.append({
                'category': 'Certificate Validity',
                'severity': 'PASS',
                'message': f"Certificate validity is active through {document.expiry_date.strftime('%d-%b-%Y')}."
            })

    confidence_score = max(0.1, min(0.98, confidence_points / 100.0))

    # Create or update analysis record
    analysis, created = AIDocumentAnalysis.objects.get_or_create(
        document=document,
        defaults={
            'extracted_text_preview': extracted_text[:1500] if extracted_text else "No text extracted (scanned image or empty).",
            'detected_institution_name': app.institution_name if name_matches > 0 else "",
            'detected_dates': detected_dates[:10],
            'detected_keywords': detected_keywords,
            'confidence_score': round(confidence_score, 2),
            'findings': findings,
            'status': status,
        }
    )

    if not created:
        analysis.extracted_text_preview = extracted_text[:1500] if extracted_text else "No text extracted."
        analysis.detected_dates = detected_dates[:10]
        analysis.detected_keywords = detected_keywords
        analysis.confidence_score = round(confidence_score, 2)
        analysis.findings = findings
        analysis.status = status
        analysis.analysed_at = timezone.now()
        analysis.save()

    return analysis
