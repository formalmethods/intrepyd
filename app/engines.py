"""
Implementation of REST API for engines
"""
from flask import Blueprint, request
from intrepyd.engine import Bmc, OptimizingBmc
from intrepyd.engine import EngineResult
from .contexts import contexts

er = Blueprint('engines', __name__)

@er.route('', methods=['GET'])
def list_engines():
    """
    List all the previously created engines
    """
    context = request.args.get('context')
    engines = contexts[context]['engines']
    return {'engines': [name for name in engines]}, 200

@er.route('/assumptions/create', methods=['POST'])
def create_assumption():
    """
    Creates an assumption
    """
    context = request.get_json()['context']
    net = request.get_json()['net']
    if context is None or net is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    ctx.mk_assumption(ctx.nets[net])
    return {'result': 'ok'}, 201

@er.route('/create', methods=['POST'])
def create_engine():
    """
    Creates an engine
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    assert ctx is not None
    eng = None
    if engine == 'bmc':
        eng = ctx.mk_bmc()
    elif engine == 'optimizing_bmc':
        eng = ctx.mk_optimizing_bmc()
    elif engine == 'backward_reach':
        eng = ctx.mk_backward_reach()
    elif engine == 'pdr':
        eng = ctx.mk_pdr()
    elif engine == 'portfolio':
        eng = ctx.mk_portfolio()
    else:
        return {'result': 'error: unknown engine {}'.format(engine)}, 400
    assert eng is not None
    name = 'e{}'.format(len(contexts[context]['engines']))
    contexts[context]['engines'][name] = eng
    return {'result': name}, 201

@er.route('/setcurrentdepth', methods=['PUT'])
def set_current_depth():
    """
    Sets the current depth for a BMC engine
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    depth = request.get_json()['depth']
    if context is None or engine is None or depth is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    assert ctx is not None
    assert eng is not None
    if not isinstance(eng, Bmc) and not isinstance(eng, OptimizingBmc):
        return {'result': 'error: cannot set depth on this engine'}, 400
    eng.set_current_depth(depth)
    return {'result': depth}, 200

@er.route('/setuseinduction', methods=['PUT'])
def set_use_induction():
    """
    Enable induction on a BMC engine
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    assert ctx is not None
    assert eng is not None
    if not isinstance(eng, Bmc) and not isinstance(eng, OptimizingBmc):
        return {'result': 'error: cannot set induction on this engine'}, 400
    eng.set_use_induction()
    return {'result': 'ok'}, 200

@er.route('/setallowtargetsatanydepth', methods=['PUT'])
def set_allow_targets_at_any_depth():
    """
    Allow BMC to reach targets at any depth, not just the last one
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    assert ctx is not None
    assert eng is not None
    if not isinstance(eng, Bmc) and not isinstance(eng, OptimizingBmc):
        return {'result': 'error: cannot set induction on this engine'}, 400
    eng.set_allow_targets_at_any_depth()
    return {'result': 'ok'}, 200

@er.route('/setuseattackpathaxioms', methods=['PUT'])
def set_use_attack_path_axioms():
    """
    Inserts specifically effective axioms for computing an Attack Path
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    source = request.get_json()['source']
    target = request.get_json()['target']
    if context is None or engine is None or source is None or target is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    sou = ctx.nets[source]
    tar = ctx.nets[target]
    assert ctx is not None
    assert eng is not None
    assert sou is not None
    assert tar is not None
    if not isinstance(eng, Bmc) and not isinstance(eng, OptimizingBmc):
        return {'result': 'error: cannot set attack path axioms on this engine'}, 400
    eng.set_use_attack_path_axioms(sou, tar)
    return {'result': 'ok'}, 200

@er.route('/addtarget', methods=['PUT'])
def add_target():
    """
    Adds a target to the engine
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    net = request.get_json()['net']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    net = ctx.nets[net]
    assert ctx is not None
    assert eng is not None
    assert net is not None
    eng.add_target(net)
    return {'result': 'ok'}, 200

@er.route('/reachtargets', methods=['PUT'])
def reach_targets():
    """
    Executes reachability for the specified targets
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    eng = contexts[context]['engines'][engine]
    assert eng is not None
    result = eng.reach_targets()
    res = 'unknown'
    if result == EngineResult.REACHABLE:
        res = 'reachable'
    if result == EngineResult.UNREACHABLE:
        res = 'unreachable'
    return {'result': res}, 200

@er.route('/watch', methods=['PUT'])
def add_watch():
    """
    Adds a net to the set of watches
    """
    context = request.get_json()['context']
    engine = request.get_json()['engine']
    net = request.get_json()['net']
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    net = ctx.nets[net]
    assert ctx is not None
    assert eng is not None
    assert net is not None
    eng.add_watch(net)
    return {'result': 'ok'}, 200

@er.route('/lastreachedtargets', methods=['GET'])
def last_reached_targets():
    """
    Gets the list of reached targets
    """
    context = request.args.get('context')
    engine = request.args.get('engine')
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    assert ctx is not None
    assert eng is not None
    result = [ctx.net2name[net] for net in eng.get_last_reached_targets()]
    return {'result': result}, 200

@er.route('/lasttrace', methods=['GET'])
def last_trace():
    """
    Gets the trace for the last reached target
    """
    context = request.args.get('context')
    engine = request.args.get('engine')
    if context is None or engine is None:
        return {'result': 'error'}, 400
    ctx = contexts[context]['context']
    eng = contexts[context]['engines'][engine]
    assert ctx is not None
    assert eng is not None
    name = 't{}'.format(len(contexts[context]['traces']))
    trace = eng.get_last_trace()
    contexts[context]['traces'][name] = trace
    return {'result': name}, 200
