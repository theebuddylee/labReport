"""Reference-interval parsing and scoring, independent of provider or UI."""
import math
import re

def reference_label(raw):
    if isinstance(raw, list):
        return reference_label(raw[0]) if len(raw) == 1 else 'Multiple intervals — review required'
    if isinstance(raw, dict):
        if raw.get('text'): return str(raw['text'])
        low, high = (raw.get('low') or {}).get('value'), (raw.get('high') or {}).get('value')
        if low is not None and high is not None: return f'{low} - {high}'
        if low is not None: return f'>= {low}'
        if high is not None: return f'<= {high}'
    return 'Not supplied'

def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None

def parse_interval(text):
    text = str(text or '').strip().replace('−', '-').replace('–', '-').replace(chr(8212), '-')
    text = re.sub(r'\s+to\s+', ' - ', text, flags=re.IGNORECASE)
    number = r'([-+]?(?:\d+(?:\.\d*)?|\.\d+))'
    match = re.fullmatch(r'\s*' + number + r'\s*-\s*' + number + r'\s*', text)
    if match:
        low, high = map(float, match.groups())
        return {'low': low, 'high': high, 'low_inclusive': True, 'high_inclusive': True} if low <= high else None
    match = re.fullmatch(r'\s*(<=|>=|<|>|≤|≥)\s*' + number + r'\s*', text)
    if match:
        operator, boundary = match.groups(); boundary = float(boundary)
        return {'low': boundary if operator in ('>', '>=', '≥') else None,
                'high': boundary if operator in ('<', '<=', '≤') else None,
                'low_inclusive': operator in ('>=', '≥'), 'high_inclusive': operator in ('<=', '≤')}
    return None

def reference_from_api(row, compatible_unit):
    raw = row.get('reference_range')
    if isinstance(raw, list):
        if len(raw) != 1:
            return {'clinical_range': 'Multiple reference intervals — review required', 'reference_bounds': None,
                    'reference_note': 'No population-specific interval was selected automatically.'}
        raw = raw[0]
    if not isinstance(raw, dict):
        return {'clinical_range': 'Not supplied', 'reference_bounds': None,
                'reference_note': 'The API did not supply a laboratory reference interval.'}
    for boundary in ('low', 'high'):
        part = raw.get(boundary) or {}
        unit = part.get('unit') or part.get('code')
        if unit and not compatible_unit(unit):
            return {'clinical_range': 'Reference-unit mismatch — review required', 'reference_bounds': None,
                    'reference_note': 'The laboratory interval unit differs from the result unit; clinical comparison is withheld.'}
    text = str(raw.get('text') or '').strip()
    low, high = numeric((raw.get('low') or {}).get('value')), numeric((raw.get('high') or {}).get('value'))
    bounds = parse_interval(text)
    if low is not None or high is not None:
        structured = {'low': low, 'high': high, 'low_inclusive': True, 'high_inclusive': True}
        if bounds:
            # Conflicting structured/text intervals are not guessed.
            if any(bounds[k] != structured[k] for k in ('low', 'high')):
                return {'clinical_range': 'Conflicting reference intervals — review required', 'reference_bounds': None,
                        'reference_note': 'The API text and numeric laboratory interval differ; clinical comparison is withheld.'}
            structured.update(low_inclusive=bounds['low_inclusive'], high_inclusive=bounds['high_inclusive'])
        bounds = structured if low is None or high is None or low <= high else None
        if not text:
            text = f'{low:g} - {high:g}' if low is not None and high is not None else (f'>= {low:g}' if low is not None else f'<= {high:g}')
    text = text or 'Not established'
    return {'clinical_range': text, 'reference_bounds': bounds,
            'reference_note': 'Reported laboratory reference interval.' if bounds else 'No established numeric laboratory reference interval.'}

def classify_result(value, info):
    value = numeric(value)
    if value is None:
        return None
    if not info.get('clinical_units_compatible', True):
        return None
    if info.get('requires_report_reference') and 'reference_bounds' not in info:
        return None
    bounds = info.get('reference_bounds') if 'reference_bounds' in info else parse_interval(info.get('clinical_range'))
    if not bounds:
        return None
    low, high = bounds['low'], bounds['high']
    if low is not None and (value < low or (value == low and not bounds.get('low_inclusive', True))):
        return False
    if high is not None and (value > high or (value == high and not bounds.get('high_inclusive', True))):
        return False
    return True

def in_interval(value, bounds):
    if not bounds:
        return None
    low, high = bounds['low'], bounds['high']
    if low is not None and (value < low or (value == low and not bounds.get('low_inclusive', True))):
        return False
    if high is not None and (value > high or (value == high and not bounds.get('high_inclusive', True))):
        return False
    return True


def assess_result(value, info):
    """One assessment shared by UI, PDF, analytics and weighted Optimal scoring."""
    value = numeric(value)
    clinical = classify_result(value, info)
    reason = None
    if value is None:
        reason = 'No finite numeric result.'
    elif not info.get('optimal_identity_confirmed', True):
        reason = 'Assay identity is unresolved; no existing Optimal target was guessed.'
    elif not info.get('optimal_units_compatible', True):
        reason = f"Original Optimal target uses {info.get('optimal_units', 'unspecified units')}; result uses {info.get('units', 'unspecified units')}. No conversion or scoring applied."
    bounds = info.get('optimal_reference_bounds') if info.get('optimal_origin') == 'new' else parse_interval(info.get('optimal_range'))
    optimal = in_interval(value, bounds) if value is not None else None
    if reason is None and optimal is None:
        reason = 'No established numeric Optimal target.'
    if reason is None and optimal is False and clinical is None:
        reason = 'The result is outside the Optimal target but its clinical interval is unavailable or ambiguous.'
    if reason:
        return {'category':'unscored','points':None,'optimal':None,'clinical':clinical,'reason':reason}
    category = 'optimal' if optimal else ('clinical' if clinical else 'outside')
    return {'category':category,'points':{'optimal':1.0,'clinical':0.75,'outside':0.0}[category],
            'optimal':optimal,'clinical':clinical,'reason':None}


def score_lab_results(markers, values, catalog):
    assessments = [assess_result(values.get(marker), catalog[marker]) for marker in markers]
    counts = {key:sum(a['category'] == key for a in assessments) for key in ('optimal','clinical','outside','unscored')}
    scored = len(assessments) - counts['unscored']
    return {'total':len(assessments), 'within':counts['optimal'] + counts['clinical'],
            **counts, 'scored':scored,
            'score_percent':100 * sum(a['points'] or 0 for a in assessments) / scored if scored else None}
