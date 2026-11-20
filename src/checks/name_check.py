"""
Name consistency check across ID proof, salary slips, and bank statement.

The check combines normalized token similarity with a lightweight phonetic
signal. Common Indian spelling variants are treated as hard negatives, while
genuine low-similarity mismatches remain HIGH severity.
"""

import re
from typing import List, Tuple
from src.config import CONFIG
from src.models import ApplicantPacketData, MismatchFlag, EvidenceItem, SeverityLevel

try:
    from rapidfuzz import fuzz
except ImportError:
    class fuzz:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, " ".join(sorted(s1.lower().split())), " ".join(sorted(s2.lower().split()))).ratio() * 100

        @staticmethod
        def token_set_ratio(s1: str, s2: str) -> float:
            return fuzz.token_sort_ratio(s1, s2)


COMMON_VARIANTS = {
    "mohammed": "muhammad",
    "muhammed": "muhammad",
    "mohd": "muhammad",
    "muhammad": "muhammad",
    "khushi": "khusi",
    "khusi": "khusi",
    "shivani": "sivani",
    "sivani": "sivani",
    "vijay": "vijaya",
    "vijaya": "vijaya",
    "prasad": "prasada",
    "chandra": "chandar",
    "kumar": "kumar",
}


def normalize_token(token: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z]", "", token.lower())
    return COMMON_VARIANTS.get(cleaned, cleaned)


def normalize_name_string(name: str) -> str:
    if not name or name.strip().lower() == "not_found":
        return ""
    spaced = re.sub(r"\.", ". ", name)
    return " ".join(normalize_token(t) for t in spaced.split() if normalize_token(t))


def matches_initial(token_initial: str, token_full: str) -> bool:
    initial = re.sub(r"[^a-zA-Z]", "", token_initial.lower())
    full = re.sub(r"[^a-zA-Z]", "", token_full.lower())
    return len(initial) == 1 and bool(full) and initial == full[0]


def check_initial_expansion(tokens1: List[str], tokens2: List[str]) -> bool:
    if not tokens1 or not tokens2:
        return False
    for short_tokens, long_tokens in ((tokens1, tokens2), (tokens2, tokens1)):
        if not any(len(token) == 1 for token in short_tokens):
            continue
        short_words = [t for t in short_tokens if len(t) > 2]
        long_words = [t for t in long_tokens if len(t) > 2]
        if short_words and not set(short_words).intersection(long_words):
            continue
        used = set()
        matched = True
        for token in short_tokens:
            if len(token) == 1:
                match = next((i for i, candidate in enumerate(long_tokens) if i not in used and matches_initial(token, candidate)), None)
                if match is None:
                    matched = False
                    break
                used.add(match)
            elif token in long_tokens:
                used.add(long_tokens.index(token))
            else:
                matched = False
                break
        if matched:
            return True
    return False


def _phonetic_token(token: str) -> str:
    token = re.sub(r"[^a-z]", "", token.lower())
    if not token:
        return ""
    # Keep the first sound and consonant classes; this tolerates common vowel
    # omissions and transliteration differences without guessing a name.
    classes = {
        "b": "1", "f": "1", "p": "1", "v": "1",
        "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
        "d": "3", "t": "3",
        "l": "4",
        "m": "5", "n": "5",
        "r": "6",
    }
    encoded = token[0] + "".join(classes.get(ch, "") for ch in token[1:])
    return re.sub(r"(.)\1+", r"\1", encoded)[:6]


def phonetic_similarity(name1: str, name2: str) -> float:
    tokens1 = sorted(_phonetic_token(t) for t in normalize_name_string(name1).split())
    tokens2 = sorted(_phonetic_token(t) for t in normalize_name_string(name2).split())
    if not tokens1 or not tokens2:
        return 0.0
    if tokens1 == tokens2:
        return 100.0
    return fuzz.token_sort_ratio(" ".join(tokens1), " ".join(tokens2))


def are_names_equivalent(name1: str, name2: str, threshold: float) -> Tuple[bool, float, str]:
    if not name1 or not name2 or name1.strip().lower() == "not_found" or name2.strip().lower() == "not_found":
        return False, 0.0, "Missing name value"
    norm1 = normalize_name_string(name1)
    norm2 = normalize_name_string(name2)
    if norm1 == norm2:
        return True, 100.0, "Normalized match"
    tokens1, tokens2 = norm1.split(), norm2.split()
    if sorted(tokens1) == sorted(tokens2):
        return True, 100.0, "Surname/name order variation"
    if check_initial_expansion(tokens1, tokens2):
        return True, 95.0, "Initials versus full name"

    text_score = max(fuzz.token_sort_ratio(norm1, norm2), fuzz.token_set_ratio(norm1, norm2))
    phonetic_score = phonetic_similarity(name1, name2)
    phonetic_signal = (
        phonetic_score
        if text_score >= CONFIG.NAME_PHONETIC_MINIMUM_BASE_SIMILARITY
        and phonetic_score >= CONFIG.NAME_PHONETIC_SIMILARITY_THRESHOLD
        else 0.0
    )
    score = max(text_score, phonetic_signal)
    if score >= CONFIG.NAME_SIMILARITY_VERY_HIGH_THRESHOLD:
        return True, score, f"Very high similarity ({score:.1f}%)"
    if score >= threshold:
        return False, score, f"Medium similarity ({score:.1f}%)"
    return False, score, f"Low similarity ({score:.1f}%)"


def _field_values_match(first, second) -> bool:
    return bool(first and second and first.is_found and second.is_found and str(first.value).strip().upper() == str(second.value).strip().upper())


def _identity_is_corroborated(packet: ApplicantPacketData, compared_field) -> bool:
    id_doc = packet.id_document
    if not _field_values_match(id_doc.date_of_birth, compared_field.date_of_birth if hasattr(compared_field, "date_of_birth") else None):
        return False
    id_number = id_doc.id_number
    comparable = getattr(compared_field, "id_number", None)
    return _field_values_match(id_number, comparable)


def _make_flag(packet, primary_name, primary_loc, other_name, other_field, title, flag_id) -> MismatchFlag:
    _, score, reason = are_names_equivalent(primary_name, other_name, CONFIG.NAME_SIMILARITY_WARNING_THRESHOLD)
    corroborated = _identity_is_corroborated(packet, other_field)
    if score >= CONFIG.NAME_SIMILARITY_VERY_HIGH_THRESHOLD:
        severity = None
    elif score >= CONFIG.NAME_SIMILARITY_WARNING_THRESHOLD or corroborated:
        severity = SeverityLevel.MEDIUM
    else:
        severity = SeverityLevel.HIGH
    if severity is None:
        raise ValueError("Very-high similarity must not create a mismatch flag")
    if hasattr(other_field, "applicant_name"):
        other_loc = other_field.applicant_name.location
    elif hasattr(other_field, "account_holder"):
        other_loc = other_field.account_holder.location
    else:
        other_loc = None
    return MismatchFlag(
        flag_id=flag_id,
        check_name="name_consistency",
        severity=severity,
        short_title=title,
        llm_explanation=(
            f"Name comparison: '{primary_name}' vs '{other_name}'. {reason}. "
            f"Evidence is cited from the ID and comparison document. "
            f"{'DOB and ID number also match, so severity is reduced. ' if corroborated else ''}"
        ),
        evidence=[
            EvidenceItem(document=packet.id_document.document_name, page=primary_loc.page if primary_loc else 1,
                         line=primary_loc.line if primary_loc else 1, field_name="applicant_name",
                         extracted_value=primary_name, raw_snippet=primary_loc.raw_text if primary_loc else ""),
            EvidenceItem(document=other_field.document_name, page=other_loc.page if other_loc else 1,
                         line=other_loc.line if other_loc else 1, field_name="applicant_name",
                         extracted_value=other_name, raw_snippet=other_loc.raw_text if other_loc else ""),
        ],
    )


def check_name_consistency(packet: ApplicantPacketData) -> List[MismatchFlag]:
    flags: List[MismatchFlag] = []
    id_name_field = packet.id_document.applicant_name
    if not id_name_field.is_found:
        return [MismatchFlag(
            flag_id="FLAG_NAME_ID_MISSING", check_name="name_consistency", severity=SeverityLevel.HIGH,
            short_title="Applicant Name Missing on ID Document",
            llm_explanation=f"Applicant name could not be extracted from ID document '{packet.id_document.document_name}'.",
            evidence=[EvidenceItem(document=packet.id_document.document_name, page=1, line=1,
                                    field_name="applicant_name", extracted_value="not_found")],
        )]

    primary_name = str(id_name_field.value)
    for idx, slip in enumerate(packet.salary_slips, start=1):
        if not slip.applicant_name.is_found:
            continue
        equivalent, _, _ = are_names_equivalent(primary_name, str(slip.applicant_name.value),
                                                 CONFIG.NAME_SIMILARITY_WARNING_THRESHOLD)
        if not equivalent:
            flags.append(_make_flag(packet, primary_name, id_name_field.location, str(slip.applicant_name.value),
                                    slip, f"Name Mismatch: ID Proof vs Salary Slip #{idx}",
                                    f"FLAG_NAME_MISMATCH_SLIP_{idx}"))

    bank_field = packet.bank_statement.account_holder
    if bank_field.is_found:
        equivalent, _, _ = are_names_equivalent(primary_name, str(bank_field.value),
                                                 CONFIG.NAME_SIMILARITY_WARNING_THRESHOLD)
        if not equivalent:
            flags.append(_make_flag(packet, primary_name, id_name_field.location, str(bank_field.value),
                                    packet.bank_statement, "Name Mismatch: ID Proof vs Bank Statement",
                                    "FLAG_NAME_MISMATCH_BANK"))
    return flags
