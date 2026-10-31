"""Regression contract for the pre-preload Optimal targets. No network or patients."""
import json,sys,unittest
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lab_catalog import build_lab_catalog
from lab_preload import prepare_api_import,parse_api_batches
from lab_reference import assess_result,score_lab_results,parse_interval
BASE=json.loads((Path(__file__).parent/'fixtures/optimal_ranges_before_preload.json').read_text(encoding='utf-8'))['catalog']

def observation(name,value,unit,low=0,high=1000):
    return {'code':{'text':name},'valueQuantity':{'value':value,'unit':unit},
            'referenceRange':{'low':{'value':low,'unit':unit},'high':{'value':high,'unit':unit}}}
def batch(*rows):
    return parse_api_batches({'data':{'entry':[{'resource':{'status':'final','effectiveDateTime':'2026-10-01','component':list(rows)}}]}})[0]

class OriginalOptimalContract(unittest.TestCase):
    def setUp(self):self.catalog=build_lab_catalog(BASE)
    def test_every_legacy_target_in_all_three_groups_is_verbatim(self):
        self.assertEqual({g:len(v) for g,v in BASE.items()},{'Men':82,'Women':81,'Post Menopausal Women':83})
        for group,markers in BASE.items():
            for name,old in markers.items():
                with self.subTest(group=group,marker=name):
                    self.assertEqual(self.catalog[group][name]['optimal_range'],old['optimal_range'])
                    self.assertEqual(self.catalog[group][name]['optimal_units'],old['units'])
                    self.assertEqual(self.catalog[group][name]['optimal_origin'],'legacy')
    def test_api_intervals_cannot_overwrite_any_original_target(self):
        for group,markers in BASE.items():
            rows=[observation(n,1,self.catalog[group][n]['units'],0,99999) for n in markers]
            _,_,updated=prepare_api_import(batch(*rows),{},self.catalog[group])
            for name,old in markers.items():
                with self.subTest(group=group,marker=name):self.assertEqual(updated[name]['optimal_range'],old['optimal_range'])
    def test_all_absolute_count_renames_inherit_exact_old_targets(self):
        for group in BASE:
            for name in ('Neutrophils','Lymphocytes','Monocytes','Eosinophils','Basophils'):
                alias=self.catalog[group][name+' (Absolute)']
                self.assertEqual(alias['optimal_range'],BASE[group][name]['optimal_range'])
                self.assertEqual(alias['legacy_marker'],name)
                self.assertEqual(alias['optimal_origin'],'legacy')
    def test_assay_aliases_and_existing_mass_spec_variants_keep_group_specific_targets(self):
        for group,old in BASE.items():
            direct=next(n for n in ('Free Testosterone (LabCorp EIA)','Free Testosterone (Lab Corp)','Free Testosterone') if n in old)
            aliases={'Free Testosterone (Direct assay)':direct,
                     'Free Testosterone (Calculated)':'Free Testosterone (Quest LC/MS-MS or Calculated)',
                     'Free Testosterone (Equilibrium dialysis)':'Free Testosterone (Quest LC/MS-MS or Calculated)',
                     'Free Testosterone (Equilibrium ultrafiltration)':'Free Testosterone (Equilibrium Ultrafiltration) [uncapped]'}
            for name,source in aliases.items():
                self.assertEqual(self.catalog[group][name]['optimal_range'],old[source]['optimal_range'])
                self.assertEqual(self.catalog[group][name]['optimal_units'],old[source]['units'])
                self.assertEqual(self.catalog[group][name]['optimal_origin'],'legacy')
            self.assertEqual(self.catalog[group]['Total Testosterone (LC/MS) [uncapped]']['optimal_range'],old['Total Testosterone (LC/MS) [uncapped]']['optimal_range'])
    def test_only_new_percentage_fields_receive_reported_interval_as_target(self):
        for group in BASE:
            for name in ('Neutrophils','Lymphocytes','Monocytes','Eosinophils','Basophils'):
                key=name+' (%)'
                values,issues,updated=prepare_api_import(batch(observation(key,20,'%',10,30)),{},self.catalog[group])
                self.assertEqual(values[key],20);self.assertFalse(issues)
                self.assertEqual(updated[key]['optimal_origin'],'new')
                self.assertEqual(updated[key]['optimal_range'],'10 - 30')
                self.assertEqual(assess_result(20,updated[key])['points'],1)
                blank=observation(key,20,'%');blank.pop('referenceRange')
                _,_,unknown=prepare_api_import(batch(blank),{},self.catalog[group])
                self.assertIsNone(assess_result(20,unknown[key])['points'])
    def test_unknown_existing_assay_is_unscored_instead_of_being_called_new(self):
        values,_,updated=prepare_api_import(batch(observation('Free Testosterone',20,'pg/mL',10,40)),{},self.catalog['Men'])
        key='Free Testosterone (Reported assay, pg/mL)'
        self.assertIn(key,values)
        self.assertEqual(updated[key]['optimal_origin'],'unresolved')
        self.assertNotEqual(updated[key]['optimal_range'],'10 - 40')
        self.assertIsNone(assess_result(20,updated[key])['points'])
    def test_incompatible_old_direct_and_ggt_units_are_preserved_but_not_scored(self):
        for group in ('Men','Women'):
            values,issues,updated=prepare_api_import(batch(observation('Free Testosterone(Direct)',7.8,'pg/mL',6.8,21.5),observation('GGT',13,'IU/L',0,65)),{},self.catalog[group])
            self.assertFalse(issues);self.assertEqual(len(values),2)
            for key in values:
                self.assertFalse(updated[key]['optimal_units_compatible'])
                self.assertIsNone(assess_result(values[key],updated[key])['points'])
                self.assertEqual(updated[key]['optimal_origin'],'legacy')
    def test_compatible_ggt_retains_original_postmenopausal_target(self):
        values,issues,updated=prepare_api_import(batch(observation('GGT',25,'IU/L',0,60)),{},self.catalog['Post Menopausal Women'])
        key='Glutamyl Transferase (GGT)'
        self.assertEqual(updated[key]['optimal_range'],'9.0 - 20.0')
        self.assertEqual(assess_result(values[key],updated[key])['points'],.75)
    def test_original_weighted_scoring_and_unscored_denominator(self):
        info={'optimal_range':'70 - 95','clinical_range':'65 - 100','units':'mg/dL'}
        catalog={key:deepcopy(info) for key in ['A','B','C']}
        catalog['D']={'optimal_origin':'new','optimal_range':'Not established','reference_bounds':None}
        values={'A':90,'B':98,'C':120,'D':20}
        metrics=score_lab_results(list(values),values,catalog)
        self.assertEqual([assess_result(values[k],catalog[k])['points'] for k in ['A','B','C']],[1,.75,0])
        self.assertEqual((metrics['optimal'],metrics['clinical'],metrics['outside'],metrics['unscored'],metrics['scored']),(1,1,1,1,3))
        self.assertAlmostEqual(metrics['score_percent'],100*1.75/3)
    def test_original_text_is_retained_even_when_parser_supports_to_or_inequalities(self):
        key='Mean Platelet Volume (MPV)'
        self.assertEqual(self.catalog['Post Menopausal Women'][key]['optimal_range'],'7.0 to 9.0')
        self.assertEqual(parse_interval('7.0 to 9.0')['low'],7)
        self.assertEqual(assess_result(90,{'optimal_range':'>80','clinical_range':'>60'})['points'],1)
        self.assertEqual(assess_result(70,{'optimal_range':'>80','clinical_range':'>60'})['points'],.75)
    def test_repeated_definitions_cannot_replace_original_optimal_target(self):
        values,issues,updated=prepare_api_import(batch(observation('Glucose',90,'mg/dL',60,100),observation('Glucose',90,'mg/dL',70,110)),{},self.catalog['Men'])
        self.assertIn('Glucose',values)
        self.assertEqual(updated['Glucose']['optimal_range'],BASE['Men']['Glucose']['optimal_range'])
    def test_catalog_is_idempotent_and_does_not_mutate_baseline(self):
        before=deepcopy(BASE)
        self.assertEqual(build_lab_catalog(self.catalog),self.catalog)
        self.assertEqual(BASE,before)

if __name__=='__main__':unittest.main(verbosity=2)
