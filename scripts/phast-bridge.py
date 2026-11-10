"""Mesh/BC and result adapter; all equilibrium and damage solves belong to PhAST."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'third_party/phast/upstream/src'))
import torch
from phast import FEMMesh, Material, BoundaryConditions, SolverConfig, StaggeredSolver


def emit(message):
    print('TENSORA_PROGRESS ' + json.dumps(message, allow_nan=False), flush=True)


def run(request_file):
    request = json.loads(Path(request_file).read_text(encoding='utf-8'))
    model, settings, cards = request['model'], request['settings'], request['materialSettings']
    torch.set_num_threads(2)
    dtype = torch.float64
    node_ids = [n['nodeNo'] for n in model['nodes']]
    index = {n: i for i, n in enumerate(node_ids)}
    nodes = torch.tensor([[n['x'], n['y']] for n in model['nodes']], dtype=dtype)
    elements = torch.tensor([[index[e[k]] for k in ('node1', 'node2', 'node3')] for e in model['elements']], dtype=torch.long)
    points=nodes[elements]
    signed=(points[:,1,0]-points[:,0,0])*(points[:,2,1]-points[:,0,1])-(points[:,1,1]-points[:,0,1])*(points[:,2,0]-points[:,0,0])
    clockwise=signed<0
    elements[clockwise]=elements[clockwise][:,[0,2,1]]
    mesh = FEMMesh.from_tensors(nodes, elements, device='cpu', dtype=dtype)
    first = model['elements'][0]
    card = cards[str(first.get('materialNo', 'legacy'))]
    # Consistent SI throughout: m, N, Pa, J/m². Do not use YAML's mm-unit conversion.
    material = Material(E=first['elasticModulus'], nu=first['poissonRatio'],
                        Gc=card['fractureEnergy'], l0=card['fractureLength'], rho=1.0,
                        eta_residual=1e-7, energy_split='amor', pf_model='AT2', plane_stress=False)
    bcs = BoundaryConditions(mesh.n_nodes, device='cpu', dtype=dtype)
    for component, key in enumerate(('fixUx', 'fixUy')):
        indices = [i for i, n in enumerate(model['nodes']) if n.get(key)]
        if indices:
            bcs.fix(torch.tensor(indices, dtype=torch.long), component)
    force = torch.tensor([[n.get('forceX', 0), n.get('forceY', 0)] for n in model['nodes']], dtype=dtype)
    if settings['fractureLoading'] == 'displacement':
        maximum = force.norm(dim=1).max().item()
        for i, n in enumerate(model['nodes']):
            for component, fix in enumerate(('fixUx', 'fixUy')):
                if force[i, component] != 0:
                    if n.get(fix):
                        raise ValueError('Prescribed fracture displacement conflicts with a fixed component.')
                    bcs.add(torch.tensor([i]), component,
                            settings['fractureDisplacement'] * force[i, component].item() / maximum)
    config = SolverConfig(solver_type='quasi_static', num_steps=settings['increments'],
                          backend='scipy', static_tol=1e-8, static_max_iter=50,
                          stagger_tol=1e-6, max_stagger=300, use_multigrid=False,
                          bounds_method='projected_cg', enable_damage=True)
    solver = StaggeredSolver(mesh, material, bcs, config)
    solver.install_diff_E_field(torch.tensor([e['elasticModulus'] for e in model['elements']], dtype=dtype))
    solver.diff_Gc_field = torch.tensor([cards[str(e.get('materialNo', 'legacy'))]['fractureEnergy'] for e in model['elements']], dtype=dtype)
    start = time.monotonic()
    frames, termination = [], None
    def snapshot(fraction):
        strain = solver.fem.compute_strain(solver.u)
        sx, sy, xy = solver.fem.compute_stress(solver.u, solver.d, strain=strain)
        ex, ey, gamma = strain
        # Out-of-plane Cauchy stress from the same upstream Amor plane-strain law.
        E = solver.fem.diff_E_field
        mu = E / (2 * (1 + material.nu))
        kappa = E / (3 * (1 - 2 * material.nu))
        trace = ex + ey
        g = material.degradation(solver.d[elements].mean(1))
        sz = g * (kappa * trace.clamp(min=0) - 2 * mu * trace / 3) + kappa * trace.clamp(max=0)
        stresses = torch.stack((sx, sy, sz, xy, torch.zeros_like(sx), torch.zeros_like(sx)), 1)
        strains = torch.stack((ex, ey, torch.zeros_like(ex), gamma/2, torch.zeros_like(ex), torch.zeros_like(ex)), 1)
        def project(values):
            accum = torch.zeros((mesh.n_nodes, values.shape[1]), dtype=dtype)
            weights = torch.zeros(mesh.n_nodes, dtype=dtype)
            for k in range(3):
                accum.index_add_(0, elements[:, k], values * mesh.areas[:, None])
                weights.index_add_(0, elements[:, k], mesh.areas)
            return accum / weights[:, None].clamp(min=1e-30)
        stress_nodes, strain_nodes = project(stresses), project(strains)
        if not all(torch.isfinite(v).all() for v in (solver.u, solver.d, stresses, strains)):
            raise RuntimeError('PhAST returned non-finite fields.')
        elemental = {}
        for j, e in enumerate(model['elements']):
            elemental[str(e['elementNo'])] = {'stress': stresses[j].tolist(), 'strain': strains[j].tolist(), 'damage': solver.d[elements[j]].mean().item()}
        reaction = solver.fem.internal_force(solver.u, solver.d)
        direction=force/force.norm(dim=1).max().clamp(min=1e-30)
        return {'time': fraction, 'reactionForce': (reaction*direction).sum().item(), 'displacement': {str(id): solver.u[i].tolist()+[0] for i,id in enumerate(node_ids)},
                'stress': {str(id): stress_nodes[i].tolist() for i,id in enumerate(node_ids)},
                'strain': {str(id): strain_nodes[i].tolist() for i,id in enumerate(node_ids)},
                'plasticStrain': {}, 'damage': {str(id): [solver.d[i].item()] for i,id in enumerate(node_ids)},
                'elementFields': elemental}
    frames.append(snapshot(0.0))
    with torch.no_grad():
        for step in range(1, settings['increments']+1):
            fraction = step/settings['increments']
            bcs.load_factor = fraction*settings['loadFactor']
            solver.f_ext = force * bcs.load_factor if settings['fractureLoading']=='forces' else torch.zeros_like(force)
            try:
                solver.step_full()
                frames.append(snapshot(fraction))
            except RuntimeError as error:
                termination = {'code': 'nonconvergence', 'message': 'PhAST: '+str(error), 'convergedFraction': frames[-1]['time']}
                break
            elapsed = (time.monotonic()-start)*1000
            emit({'phase':'solving', 'fraction':fraction, 'completedIncrements':step,
                  'elapsedMs':elapsed, 'estimatedRemainingMs':elapsed*(1-fraction)/fraction if step>=2 else None})
    if len(frames)<2:
        raise RuntimeError(termination['message'] if termination else 'No converged fracture increments.')
    result = {'ok':True,'completed':termination is None,'termination':termination,'solver':'PhAST 0.16.2',
              'fracture':True,'settings':settings,'materialSettings':cards,'model':model,'frames':frames,
              'damageScope':'AT2 phase-field damage with irreversible tensile-history evolution and stiffness degradation; small-strain Amor plane strain.'}
    Path(request_file).with_name('result.json').write_text(json.dumps(result,allow_nan=False),encoding='utf-8')


if __name__=='__main__':
    run(sys.argv[1])
