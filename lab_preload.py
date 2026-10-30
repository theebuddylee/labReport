"""API-to-widget state helpers. No requests, storage, scoring, or unit conversion."""
import hashlib
import json
import math
import re
from copy import deepcopy
from lab_reference import reference_from_api

CBC_LOINC = {
    '770-8': ('Neutrophils', '%'), '751-8': ('Neutrophils', 'absolute'),
    '736-9': ('Lymphocytes', '%'), '731-0': ('Lymphocytes', 'absolute'),
    '5905-5': ('Monocytes', '%'), '742-7': ('Monocytes', 'absolute'),
    '713-8': ('Eosinophils', '%'), '711-2': ('Eosinophils', 'absolute'),
    '706-2': ('Basophils', '%'), '704-7': ('Basophils', 'absolute'),
}

def code_text(value):
    if isinstance(value, str): return value
    if isinstance(value, list): return ' '.join(code_text(v) for v in value)
    if isinstance(value, dict):
        return ' '.join(str(value.get(k) or '') for k in ('text', 'display', 'name', 'code')) + ' ' + code_text(value.get('coding', []))
    return ''

def reporting_lab(value):
    text = code_text(value).strip().casefold()
    if 'labcorp' in text.replace(' ', '') or 'laboratory corporation' in text: return 'LabCorp'
    if 'quest' in text: return 'Quest'
    return ''


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def finite_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_api_batches(lab_data):
    """Keep collection time/specimen boundaries; never pick a newest result."""
    batches = {}
    data = lab_data.get('data', {}) if isinstance(lab_data, dict) else {}
    entries = data.get('entry', []) if isinstance(data, dict) else []
    if not isinstance(entries, list):
        return []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        resource = entry.get('resource', {})
        if not isinstance(resource, dict):
            continue
        observations = [c for c in (resource.get('component') or []) if isinstance(c, dict)]
        if 'valueQuantity' in resource:
            observations.append(resource)
        for observation in observations:
            when = observation.get('effectiveDateTime') or resource.get('effectiveDateTime')
            period = observation.get('effectivePeriod') or resource.get('effectivePeriod')
            # An interval is not a single collection timestamp. Keep it distinct.
            date = when or (json.dumps(period, sort_keys=True) if period else '')
            specimen = resource.get('specimen', {}).get('reference', '')
            lab = reporting_lab(observation.get('performer') or resource.get('performer'))
            cohort = (date, specimen, lab) if date else ('undated', index, lab)
            key = fingerprint(cohort)
            batch = batches.setdefault(key, {'id': key, 'collection': date,
                                             'label': (date or f'Collection date unavailable (entry {index + 1})') + (f' ({lab})' if lab else ''),
                                             'rows': []})
            quantity = observation.get('valueQuantity') or {}
            batch['rows'].append({'marker': observation.get('code', {}).get('text', 'Unknown'),
                                  'value': quantity.get('value'), 'unit': quantity.get('unit'),
                                  'code': quantity.get('code'), 'comparator': quantity.get('comparator'),
                                  'status': observation.get('status', resource.get('status', '')),
                                  'coding': observation.get('code', {}).get('coding', []),
                                  'reference_range': observation.get('referenceRange'),
                                  'method': code_text(observation.get('method') or resource.get('method')),
                                  'lab_source': lab})
    # Include an ordinal so two specimens on the same date are distinguishable.
    result = sorted(batches.values(), key=lambda b: (b['collection'], b['id']))
    for batch in result:
        batch['rows'].sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
    for index, batch in enumerate(result):
        batch['label'] = f"Result set {index + 1}: {batch['label']}"
    return result


def canonical_unit(unit):
    # Typography and explicit identical-scale count display aliases only.
    # Never casefold units globally: milli/mega prefixes are case-sensitive.
    unit = ''.join(str(unit or '').split()).replace('μ', 'u').replace('µ', 'u')
    if '/' in unit:
        numerator, denominator = unit.rsplit('/', 1)
        if denominator in ('dl', 'ml', 'ul', 'l'):
            unit = numerator + '/' + denominator[:-1] + 'L'
    return {
        'x10E3/uL': '10*3/uL',
        'x10E3cells/uL': '10*3/uL',
        'x10E6/uL': '10*6/uL',
        'millioncells/uL': '10*6/uL',
    }.get(unit, unit)


def resolve_api_marker(row, manual_map, catalog):
    name = row['marker']; lower = name.casefold()
    unit = canonical_unit(row.get('unit') or row.get('code'))
    identity = None
    for coding in row.get('coding', []):
        if 'loinc.org' in str(coding.get('system', '')) and coding.get('code') in CBC_LOINC:
            identity = CBC_LOINC[coding['code']]
            break
    families = [('neut', 'Neutrophils'), ('lymph', 'Lymphocytes'), ('monocyt', 'Monocytes'),
                ('eos', 'Eosinophils'), ('baso', 'Basophils')]
    if identity:
        family, kind = identity
        return family + (' (%)' if kind == '%' else ' (Absolute)')
    family = next((family for token, family in families if token in lower), None)
    if any(term in lower for term in ('band', 'immature', 'blasts', 'metamyelo', 'promyelo')):
        return manual_map.get(name, name)
    if family and family + ' (%)' in catalog:
        return family + (' (%)' if unit == '%' else ' (Absolute)')
    method = (lower + ' ' + str(row.get('method', '')).casefold())
    if 'testosterone' in lower and 'free' in lower and not any(term in lower for term in ('bioavailable', 'weakly bound')):
        options = [('direct', 'Free Testosterone (Direct assay)'),
                   ('dialysis', 'Free Testosterone (Equilibrium dialysis)'),
                   ('ultrafiltration', 'Free Testosterone (Equilibrium ultrafiltration)'),
                   ('calculated', 'Free Testosterone (Calculated)')]
        identified = [target for token, target in options if token in method or (token == 'calculated' and re.search(r'\bcalc\b', method))]
        if len(identified) == 1 and identified[0] in catalog: return identified[0]
        generic = f'Free Testosterone (Reported assay, {unit})'
        if generic in catalog: return generic
    if 'testosterone' in lower and (re.search(r'\b(?:lc/?ms(?:[-/]ms)?|ms)\b', method) or 'mass spectrometry' in method):
        target = 'Total Testosterone (LC/MS) [uncapped]'
        if target in catalog: return target
    if lower.strip() == 'ggt' or 'glutamyl transferase' in lower or 'glutamyl transpeptidase' in lower:
        if 'Glutamyl Transferase (GGT)' in catalog: return 'Glutamyl Transferase (GGT)'
    return manual_map.get(name, name)

def units_match(marker, units, expected):
    units = [canonical_unit(u) for u in units if u]
    expected = canonical_unit(expected)
    if marker == 'Estimated Glomerular Filtration Rate (eGFR)':
        # User verified this API's truncated label denotes the same indexed unit.
        # Scope the alias to eGFR; do not accept unindexed mL/min or convert values.
        indexed = {'mL/min/1.73', 'mL/min/1.73m\u00b2'}
        return bool(units) and expected in indexed and all(u in indexed for u in units)
    if marker == 'Glutamyl Transferase (GGT)':
        activity = {'U/L', 'IU/L', '[IU]/L'}
        return bool(units) and expected in activity and all(u in activity for u in units)
    if marker == 'BUN/Creatinine Ratio':
        ratios = {'', '1', 'ratio', ':1(Ratio)', ':1Ratio', '{ratio}'}
        return expected in ratios and all(u in ratios for u in units)
    return bool(units) and bool(expected) and all(u == expected for u in units)

def prepare_api_import(batch, manual_map, available_markers):
    available_markers = deepcopy(available_markers)
    values, issues, candidates = {}, [], {}
    if not batch:
        return values, issues, available_markers
    if not batch['collection']:
        issues.append('Collection date is unavailable for this result set. Verify the source before using it.')
    for row in batch['rows']:
        name = row['marker']
        marker = resolve_api_marker(row, manual_map, available_markers)
        if marker not in available_markers:
            issues.append(f'{name}: no exact existing marker mapping in the selected group; not preloaded.')
            continue
        value = finite_number(row['value'])
        info = available_markers[marker]
        result_unit = row.get('unit') or row.get('code')
        if marker.startswith('Free Testosterone (') and canonical_unit(result_unit) in ('pg/mL', 'ng/dL'):
            info['units'] = result_unit
        if marker == 'Glutamyl Transferase (GGT)' and canonical_unit(result_unit) in ('U/L','IU/L','[IU]/L'):
            info['units'] = result_unit
        expected = info.get('units')
        units = [row[k] for k in ['unit', 'code'] if row.get(k)]
        reason = None
        status = str(row['status'] or '').strip().casefold()
        if status and status not in ('final', 'amended', 'corrected'):
            reason = f"result status is {row['status']}"
        elif row['comparator']:
            reason = 'a qualified result is not an exact number'
        elif value is None:
            reason = 'no finite numeric value'
        elif not units_match(marker, units, expected):
            reason = f"unit is missing or differs from the selected group's {available_markers[marker].get('units', 'unit')}"
        reference = reference_from_api(row, lambda unit: units_match(marker, [unit], expected))
        reference.update(optimal_range=reference['clinical_range'], units=expected,
                         lab_source=row.get('lab_source') or 'Not identified in API',
                         source_marker=name, source_method=row.get('method') or info.get('assay_method', 'Not specified'),
                         reference_source='Interval attached to API result',
                         assumed_ratio_unit=marker == 'BUN/Creatinine Ratio' and not units)
        candidates.setdefault(marker, []).append((value, reason, reference))
    for marker, rows in candidates.items():
        reasons = {reason for _, reason, _ in rows if reason}
        distinct = {value for value, _, _ in rows}
        if reasons or len(distinct) != 1:
            detail = '; '.join(sorted(reasons)) if reasons else 'multiple conflicting values in this result set'
            issues.append(f'{marker}: {detail}; not preloaded. Review the source and enter it manually if appropriate.')
        else:
            values[marker] = rows[0][0]
            definitions = {fingerprint(reference): reference for _, _, reference in rows}
            if len(definitions) == 1:
                available_markers[marker].update(rows[0][2])
            else:
                available_markers[marker].update(clinical_range='Multiple result definitions — review required',
                                               optimal_range='Multiple result definitions — review required',
                                               reference_bounds=None,
                                               reference_note='Repeated results have differing source definitions; not scored.')
    return values, issues, available_markers

def prepare_api_values(batch, manual_map, available_markers):
    values, issues, _ = prepare_api_import(batch, manual_map, available_markers)
    return values, issues


def clear_patient_state(state, patient_id, member_name):
    """Called before widgets are instantiated when the selected patient changes."""
    if state.get('_lab_patient_id', object()) == patient_id:
        return False
    for key in list(state):
        if str(key).startswith(('lab_panel:', 'lab_value:')) or key in (
            'api_markers_dict', 'api_batches', 'api_payload_fingerprint', 'api_batch_choice',
            '_lab_form_signature', 'lab_manual_values', 'extracted_markers_dict'):
            del state[key]
    state['_lab_patient_id'] = patient_id
    state['member_name_input'] = member_name
    return True


def accept_api_payload(state, lab_data):
    batches = parse_api_batches(lab_data)
    digest = fingerprint(batches)
    if state.get('api_payload_fingerprint') == digest:
        return False
    state['api_batches'] = batches
    state['api_payload_fingerprint'] = digest
    state['api_markers_dict'] = {}
    # A changed payload needs a deliberate date choice when there is ambiguity.
    state['api_batch_choice'] = batches[0]['id'] if len(batches) == 1 else None
    return True


def sync_form_state(state, signature, available_markers, values):
    """Apply an import once, before constructing widgets; reruns keep coach edits."""
    if state.get('_lab_form_signature') == signature:
        return False
    valid = {m: finite_number(v) for m, v in values.items() if m in available_markers}
    valid = {m: v for m, v in valid.items() if v is not None}
    for key in list(state):
        if str(key).startswith(('lab_panel:', 'lab_value:')):
            del state[key]
    panels = {}
    group = signature[1]
    for marker, info in available_markers.items():
        panels.setdefault(info.get('panel', 'Other'), [])
        if marker in valid:
            panels[info.get('panel', 'Other')].append(marker)
    for panel, markers in panels.items():
        state[f'lab_panel:{group}:{panel}'] = sorted(markers)
    state['lab_manual_values'] = valid.copy()
    state['_lab_form_signature'] = signature
    return True


def remember_result(state, marker, widget_key):
    state.setdefault('lab_manual_values', {})[marker] = state[widget_key]
