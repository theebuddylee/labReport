"""Marker catalog corrections. API-attached intervals take precedence at import."""
from copy import deepcopy

CBC_FAMILIES = {
    'Neutrophils': 'Neutrophils are white blood cells involved mainly in the response to bacterial infections and inflammation.',
    'Lymphocytes': 'Lymphocytes include T cells, B cells and natural killer cells that support immune recognition and defense.',
    'Monocytes': 'Monocytes are white blood cells that help remove damaged material and can develop into tissue macrophages.',
    'Eosinophils': 'Eosinophils participate in responses to parasites and in allergic and other inflammatory processes.',
    'Basophils': 'Basophils are a small white-blood-cell population involved in allergic and inflammatory signaling.',
}
CBC_SOURCE = 'https://www.labcorp.com/tests/005009/complete-blood-count-cbc-with-differential-reflex-to-peripheral-smear-review'
DIRECT_SOURCE = 'https://www.labcorp.com/tests/144980'
GGT_SOURCES = ['https://www.labcorp.com/tests/001958/y-glutamyl-transferase-ggt',
               'https://testdirectory.questdiagnostics.com/test/test-detail/482/gamma-glutamyl-transferase-ggt']
FREE_PROFILES = {
    'Free Testosterone (Direct assay)': ('pg/mL', 'direct', 'Direct analog assay. Its reference interval must not be substituted with a dialysis or calculated free-testosterone interval.'),
    'Free Testosterone (Equilibrium dialysis)': ('pg/mL', 'equilibrium dialysis', 'Free testosterone measured using equilibrium dialysis. Use the interval attached to this result, which can differ by laboratory, method, age and sex.'),
    'Free Testosterone (Calculated)': ('pg/mL', 'calculated', 'Free testosterone estimated by a calculation. Use the reporting laboratory\'s method-specific interval.'),
    'Free Testosterone (Equilibrium ultrafiltration)': ('ng/dL', 'equilibrium ultrafiltration', 'Free testosterone assessed using equilibrium ultrafiltration. The result\'s own units and reference interval are required.'),
    'Free Testosterone (Reported assay, pg/mL)': ('pg/mL', 'not specified', 'The API does not identify a specific free-testosterone method. The result is retained with its reported units and interval; no direct/dialysis/calculated method is inferred from units.'),
    'Free Testosterone (Reported assay, ng/dL)': ('ng/dL', 'not specified', 'The API does not identify a specific free-testosterone method. Use only the interval attached to this result; no conversion or method inference is applied.'),
}

def build_lab_catalog(base):
    result = deepcopy(base)
    for group, markers in result.items():
        # Interim user policy: catalog clinical intervals are the temporary target;
        # imported results replace these with their own laboratory intervals.
        for info in markers.values():
            info['optimal_range'] = info.get('clinical_range', 'Not supplied')
            info['target_policy'] = 'laboratory reference interval (temporary target)'
        for family, definition in CBC_FAMILIES.items():
            previous = markers.pop(family, markers.get(family + ' (Absolute)', {}))
            absolute = deepcopy(previous)
            if '%' in str(previous.get('units', '')):
                absolute['clinical_range'] = 'Not supplied'
            absolute.update(description=definition + ' This field is an absolute cell count per unit volume, not a percentage.',
                            units='x10E3 cells/µL', panel='CBC w/ Differential and Platelet',
                            requires_report_reference=True, reference_sources=[CBC_SOURCE], clinical_range='Not supplied')
            absolute['optimal_range'] = absolute.get('clinical_range', 'Not supplied')
            markers[family + ' (Absolute)'] = absolute
            markers[family + ' (%)'] = {
                'description': definition + ' This field is the percentage of total white blood cells. Percentages and absolute counts are separate results; changes in other white-cell populations can affect a percentage.',
                'units': '%', 'panel': 'CBC w/ Differential and Platelet',
                'clinical_range': 'Not established', 'optimal_range': 'Not established',
                'requires_report_reference': True, 'reference_sources': [CBC_SOURCE],
                'target_policy': 'reported laboratory interval; unscored if not established',
            }
        for name in list(markers):
            if name.lower().startswith('free testosterone'):
                del markers[name]
        for name, (unit, method, definition) in FREE_PROFILES.items():
            markers[name] = {
                'description': 'Free testosterone is the unbound fraction of circulating testosterone. ' + definition,
                'units': unit, 'assay_method': method,
                'clinical_range': 'Not supplied', 'optimal_range': 'Not supplied',
                'requires_report_reference': True, 'panel': 'Hormone, Gonadotropin & Neurosteroid Panel',
                'reference_sources': [DIRECT_SOURCE, 'https://testdirectory.questdiagnostics.com/test/test-detail/36170/testosterone-free-dialysis-and-total-ms'],
                'target_policy': 'reported laboratory interval; no universal assay interval',
            }
        if 'Total Testosterone' in markers:
            markers['Total Testosterone (LC/MS) [uncapped]'] = {
                **deepcopy(markers.get('Total Testosterone (LC/MS) [uncapped]',
                            {'units':'ng/dL','clinical_range':'Not supplied','optimal_range':'Not supplied',
                             'panel':'Hormone, Gonadotropin & Neurosteroid Panel'})),
                'description': 'Total testosterone measured using a mass-spectrometry assay. Use the reporting laboratory\'s attached reference interval; do not substitute an immunoassay interval.',
                'requires_report_reference': True,
            }
        ggt_names = [n for n in markers if 'ggt' in n.lower() or 'glutamyl transferase' in n.lower()]
        for name in ggt_names:
            del markers[name]
        markers['Glutamyl Transferase (GGT)'] = {
            'description': 'GGT is an enzyme associated with liver and bile-duct tissues. It is reported as enzyme activity per volume. Use the reporting laboratory\'s age-, sex- and method-appropriate reference interval; U/L and IU/L are supported activity labels for this marker.',
            'units': 'U/L', 'clinical_range': 'Not supplied', 'optimal_range': 'Not supplied',
            'requires_report_reference': True, 'panel': 'Thyroid, Growth Factors & Glucose',
            'reference_sources': GGT_SOURCES, 'target_policy': 'reported laboratory interval',
        }
        ratio = markers.setdefault('BUN/Creatinine Ratio', {'clinical_range':'Not supplied', 'optimal_range':'Not supplied', 'panel':'Metabolic Panel'})
        if ratio:
            ratio.update(units='ratio', allow_missing_unit=True,
                         description='The ratio of blood urea nitrogen to creatinine. This is a dimensionless ratio. An absent API unit is accepted only for this explicitly identified marker; the numerical result is unchanged.')
        if 'Immature Granulocytes' in markers:
            markers['Immature Granulocytes']['description'] = 'Immature granulocytes are developing white blood cells. This field is their percentage of white blood cells; it is separate from the absolute immature-granulocyte count. Use the reported laboratory interval, and do not score a result when no numeric interval is established.'
        if 'Immature Granulocytes (Absolute)' in markers:
            markers['Immature Granulocytes (Absolute)']['description'] = 'The absolute number of immature granulocytes per unit volume of blood. This result is separate from the percentage and uses its own reported laboratory reference interval.'
        for info in markers.values():
            info.setdefault('target_policy', 'laboratory reference interval (temporary target)')
    return result
