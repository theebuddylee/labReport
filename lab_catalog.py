"""Marker catalog with protected original Optimal ranges and scoped new-marker targets."""
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
    """Preserve existing targets verbatim; only genuinely new fields use lab targets."""
    from lab_preload import units_match
    result = deepcopy(base)
    for group, markers in result.items():
        for name, info in markers.items():
            info.setdefault('optimal_origin', 'legacy')
            info.setdefault('optimal_units', info.get('units', ''))
            info.setdefault('clinical_units', info.get('units', ''))
            info.setdefault('legacy_marker', name)
            info.setdefault('optimal_identity_confirmed', True)
            info.setdefault('optimal_units_compatible', True)
            info.setdefault('clinical_units_compatible', True)
            info.setdefault('target_policy', 'Original Optimal range retained')

        def profile(name, unit, panel, description, source=None):
            if source and source in markers:
                info = deepcopy(markers[source])
                info.update(legacy_marker=markers[source].get('legacy_marker', source), optimal_origin=markers[source].get('optimal_origin', 'legacy'),
                            optimal_units=markers[source].get('optimal_units', markers[source].get('units', '')),
                            target_policy=markers[source].get('target_policy', 'Original Optimal range retained'))
                if source != name:
                    markers[source]['selectable'] = False
            else:
                info = {'clinical_range':'Not supplied','optimal_range':'Not supplied',
                        'optimal_origin':'new','optimal_units':unit,
                        'requires_report_reference':True,
                        'target_policy':'Reported lab interval as temporary Optimal range'}
            info.setdefault('clinical_units', unit)
            info.setdefault('legacy_marker', name)
            info.setdefault('optimal_identity_confirmed', True)
            info.update(units=unit, panel=panel, description=description, selectable=True)
            info['optimal_units_compatible'] = units_match(name, [info.get('optimal_units')], unit)
            info['clinical_units_compatible'] = units_match(name, [info.get('clinical_units', unit)], unit)
            return info

        for family, definition in CBC_FAMILIES.items():
            source = family if family in markers else None
            absolute_name = family + ' (Absolute)'
            # A second build retains the alias's original source and exact target.
            if source is None and absolute_name in markers:
                source = absolute_name
            markers[absolute_name] = profile(absolute_name, 'x10E3 cells/\u00b5L',
                'CBC w/ Differential and Platelet',
                definition + ' This is an absolute count per unit volume, separate from its percentage.', source)
            name = family + ' (%)'
            if name not in markers:
                markers[name] = profile(name, '%', 'CBC w/ Differential and Platelet',
                    definition + ' This is the percentage of total white blood cells. Percentages and absolute counts are separate results.')
                markers[name].update(clinical_range='Not established', optimal_range='Not established',
                                     reference_sources=[CBC_SOURCE])

        direct_source = next((n for n in ('Free Testosterone (LabCorp EIA)',
                             'Free Testosterone (Lab Corp)', 'Free Testosterone') if n in markers), None)
        quest_source = 'Free Testosterone (Quest LC/MS-MS or Calculated)'
        ultra_source = 'Free Testosterone (Equilibrium Ultrafiltration) [uncapped]'
        sources = {'Free Testosterone (Direct assay)':direct_source,
                   'Free Testosterone (Equilibrium dialysis)':quest_source,
                   'Free Testosterone (Calculated)':quest_source,
                   'Free Testosterone (Equilibrium ultrafiltration)':ultra_source}
        for name in list(markers):
            if name.lower().startswith('free testosterone') and name not in FREE_PROFILES:
                markers[name]['selectable'] = False
        for name, (unit, method, definition) in FREE_PROFILES.items():
            source = sources.get(name)
            source = source if source in markers else None
            if method == 'equilibrium ultrafiltration' and source:
                unit = markers[source].get('units', unit)
            # An unspecified existing assay is not evidence of a genuinely new one.
            unresolved = 'Reported assay,' in name
            info = profile(name, unit, 'Hormone, Gonadotropin & Neurosteroid Panel',
                'Free testosterone is the unbound fraction of circulating testosterone. ' + definition, source)
            info.update(assay_method=method, reference_sources=[DIRECT_SOURCE,
                'https://testdirectory.questdiagnostics.com/test/test-detail/36170/testosterone-free-dialysis-and-total-ms'])
            if unresolved:
                info.update(optimal_origin='unresolved', optimal_identity_confirmed=False,
                    optimal_range='Not established - assay identity unresolved',
                    target_policy='Assay identity unresolved; no Optimal range guessed')
            markers[name] = info

        if 'Total Testosterone' in markers and 'Total Testosterone (LC/MS) [uncapped]' not in markers:
            markers['Total Testosterone (LC/MS) [uncapped]'] = profile(
                'Total Testosterone (LC/MS) [uncapped]', 'ng/dL',
                'Hormone, Gonadotropin & Neurosteroid Panel',
                'Total testosterone measured by mass spectrometry. Use this assay separately from generic total testosterone.')

        name = 'Glutamyl Transferase (GGT)'
        source = name if name in markers else None
        markers[name] = profile(name, 'U/L', 'Thyroid, Growth Factors & Glucose',
            'GGT is an enzyme associated with liver and bile-duct tissues, reported as activity per volume. The reported lab interval and original Optimal target retain their own units; incompatible units are not converted or scored.', source)
        markers[name]['reference_sources'] = GGT_SOURCES
        ratio = markers.setdefault('BUN/Creatinine Ratio', profile('BUN/Creatinine Ratio', 'ratio',
            'Metabolic Panel', 'Dimensionless ratio of blood urea nitrogen to creatinine.'))
        ratio.update(allow_missing_unit=True,
            description='The dimensionless ratio of blood urea nitrogen to creatinine. A missing API unit is accepted only for this marker; the numerical value is unchanged.')
    return result
