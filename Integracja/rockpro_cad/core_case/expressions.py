"""Small, inert, bounded recipe language. No Python source is evaluated."""
import math
from .contracts import ValidationError

OPS = frozenset(('add', 'sub', 'mul', 'div', 'min', 'max', 'at', 'eq',
                 'select', 'axis_index', 'permute_dimensions'))
SELECTORS = frozenset(('resized_dimension', 'approved_group_edge_offset', 'presentation_gap'))
MAX_DEPTH = 48
MAX_NODES = 100000


def fail(code, message, path='$.template_recipe'):
    raise ValidationError(code, path, message)


def finite(value):
    if type(value) not in (int, float):
        fail('RECIPE_INVALID_NUMBER', 'A finite number is required; bool is not numeric')
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        fail('RECIPE_INVALID_NUMBER', 'Recipe arithmetic must remain finite')
    return value


def bounded_json(value):
    """Check total size as well as depth before the public contract copies input."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            fail('RECIPE_LIMIT', 'Input depth or node budget exceeded', '$')
        if isinstance(item, dict):
            if any(not isinstance(k, str) for k in item):
                fail('INVALID_JSON_DATA', 'Only string JSON keys are supported', '$')
            pending.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            pending.extend((v, depth + 1) for v in item)
        elif item is None or type(item) in (str, bool):
            continue
        elif type(item) in (int, float):
            # Contract validators provide the more precise input dimension code.
            continue
        else:
            fail('INVALID_JSON_DATA', 'Only JSON data is supported', '$')


class Interpreter:
    def __init__(self, spec, scenario, parameters):
        self.values = {'spec.layout.' + k: v for k, v in spec['layout'].items()}
        self.values['spec.display_gap'] = spec['display_gap']
        self.values.update({'scenario.' + k: scenario[k]
                            for k in ('edge_offset', 'inner_offset') if k in scenario})
        self.scenario, self.parameters = scenario, parameters
        self.group_ids = set()
        self.steps = 0

    def validate(self, expr, references=None, depth=0):
        """Validate inactive branches too; references are ordered, never recursive."""
        if depth > MAX_DEPTH:
            fail('RECIPE_LIMIT', 'Expression depth exceeded')
        refs = self.values if references is None else references
        if type(expr) in (int, float):
            finite(expr)
        elif expr is None or type(expr) in (str, bool):
            return
        elif isinstance(expr, list):
            for item in expr:
                self.validate(item, refs, depth + 1)
        elif isinstance(expr, dict):
            if 'ref' in expr:
                if set(expr) != {'ref'} or not isinstance(expr['ref'], str) or expr['ref'] not in refs:
                    fail('RECIPE_REFERENCE_INVALID', 'Unknown, cyclic, or forward recipe reference')
            elif 'op' in expr:
                op, args = expr['op'], expr.get('args')
                if set(expr) != {'op', 'args'} or not isinstance(op, str) or op not in OPS:
                    fail('RECIPE_OPERATION_UNSUPPORTED', 'Unknown recipe operation')
                if not isinstance(args, list):
                    fail('RECIPE_ARITY_INVALID', 'Operation requires an argument list')
                arities = {'sub': 2, 'div': 2, 'at': 2, 'eq': 2, 'select': 3,
                           'axis_index': 1, 'permute_dimensions': 2}
                if (op in arities and len(args) != arities[op]) or not args:
                    fail('RECIPE_ARITY_INVALID', 'Incorrect operation arity')
                for item in args:
                    self.validate(item, refs, depth + 1)
            elif 'input_selector' in expr:
                selector = expr['input_selector']
                fields = {'resized_dimension': {'input_selector', 'axis', 'default'},
                          'approved_group_edge_offset': {'input_selector', 'group_id', 'default'},
                          'presentation_gap': {'input_selector', 'default'}}
                if not isinstance(selector, str) or selector not in SELECTORS or set(expr) != fields[selector]:
                    fail('RECIPE_SELECTOR_INVALID', 'Unknown or malformed input selector')
                if selector == 'resized_dimension' and (type(expr['axis']) is not int or expr['axis'] not in (0, 1, 2)):
                    fail('RECIPE_SELECTOR_INVALID', 'Resize selector requires axis 0, 1, or 2')
                if selector == 'approved_group_edge_offset' and not isinstance(expr['group_id'], str):
                    fail('RECIPE_SELECTOR_INVALID', 'Offset selector requires a group identifier')
                if selector == 'approved_group_edge_offset' and expr['group_id'] not in self.group_ids:
                    fail('RECIPE_SELECTOR_INVALID', 'Offset selector refers to an unknown group')
                self.validate(expr['default'], refs, depth + 1)
            else:
                for item in expr.values():
                    self.validate(item, refs, depth + 1)
        else:
            fail('RECIPE_EXPRESSION_INVALID', 'Unsupported expression data')

    def evaluate(self, expr, depth=0):
        self.steps += 1
        if depth > MAX_DEPTH or self.steps > MAX_NODES:
            fail('RECIPE_LIMIT', 'Expression evaluation budget exceeded')
        if type(expr) in (int, float):
            return finite(expr)
        if expr is None or type(expr) in (str, bool):
            return expr
        if isinstance(expr, list):
            return [self.evaluate(v, depth + 1) for v in expr]
        if 'ref' in expr:
            return self.values[expr['ref']]
        if 'input_selector' in expr:
            selector = expr['input_selector']
            if selector == 'resized_dimension' and 'target_plywood_external' in self.scenario:
                return self.scenario['target_plywood_external'][expr['axis']]
            if selector == 'approved_group_edge_offset':
                override = self.parameters.get(expr['group_id'], {})
                if 'edge_offset' in override:
                    return override['edge_offset']
            if selector == 'presentation_gap' and 'display_gap' in self.scenario:
                return self.scenario['display_gap']
            return self.evaluate(expr['default'], depth + 1)
        if 'op' not in expr:
            return {k: self.evaluate(v, depth + 1) for k, v in expr.items()}
        op, raw = expr['op'], expr['args']
        if op == 'select':
            condition = self.evaluate(raw[0], depth + 1)
            if type(condition) is not bool:
                fail('RECIPE_TYPE_INVALID', 'select requires a boolean condition')
            return self.evaluate(raw[1 if condition else 2], depth + 1)
        args = [self.evaluate(v, depth + 1) for v in raw]
        if op == 'eq':
            return type(args[0]) is type(args[1]) and args[0] == args[1]
        if op == 'axis_index':
            if args[0] not in ('X', 'Y', 'Z'):
                fail('RECIPE_TYPE_INVALID', 'Invalid axis')
            return 'XYZ'.index(args[0])
        if op == 'permute_dimensions':
            dims, axes = args
            if not isinstance(dims, list) or len(dims) != 3 or not isinstance(axes, str) or sorted(axes) != list('XYZ'):
                fail('RECIPE_TYPE_INVALID', 'Invalid dimension permutation')
            return [finite(dims['XYZ'.index(axis)]) for axis in axes]
        if op == 'at':
            vector, index = args
            if not isinstance(vector, list) or type(index) is not int or not 0 <= index < len(vector):
                fail('RECIPE_TYPE_INVALID', 'Invalid bounded vector index')
            return vector[index]
        values = [finite(v) for v in args]
        if op == 'add':
            result = sum(values)
        elif op == 'mul':
            result = math.prod(values)
        elif op == 'sub':
            result = values[0] - values[1]
        elif op == 'div':
            if values[1] == 0:
                fail('RECIPE_DIVISION_BY_ZERO', 'Recipe divisor cannot be zero')
            result = values[0] / values[1]
        elif op == 'min':
            result = min(values)
        elif op == 'max':
            result = max(values)
        else:
            fail('RECIPE_OPERATION_UNSUPPORTED', 'Unknown recipe operation')
        return finite(result)
