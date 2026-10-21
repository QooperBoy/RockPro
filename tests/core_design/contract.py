"""ROC-43 proposed offline boundary. This file implements no case planner."""
import importlib
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = json.loads(Path(__file__).with_name('cases.json').read_text(encoding='utf-8'))


def plan(requirement, spec, manifest=None, **scenario):
    """Later core code must expose plan_case(request), without CAD side effects.

    Request: spec, manifest, scenario. Response: observation (see oracle.py), or
    status=blocked with stable diagnostic codes and no executable changes.
    The requirement is diagnostic context, never an instruction to fake a result.
    """
    try:
        module = importlib.import_module('rockpro_cad.core_case')
    except ModuleNotFoundError as exc:
        if exc.name not in ('rockpro_cad.core_case', 'rockpro_cad'):
            raise
        raise NotImplementedError(
            f'{requirement}: missing pure production rockpro_cad.core_case.plan_case; '
            'implement this rule before GREEN (no CAD execution in ROC-43)') from None
    planner = getattr(module, 'plan_case', None)
    if not callable(planner):
        raise NotImplementedError(f'{requirement}: production plan_case(request) is not implemented')
    recipe = json.loads(Path(__file__).with_name('synthetic_template.json').read_text(encoding='utf-8'))
    request = copy.deepcopy({'spec': spec, 'manifest': FIXTURES['manifest'] if manifest is None else manifest,
                             'template_recipe': recipe, 'scenario': scenario})
    before = json.dumps(request, sort_keys=True, allow_nan=True)
    result = planner(request)
    assert json.dumps(request, sort_keys=True, allow_nan=True) == before, requirement + ': planner mutated input request'
    return result
