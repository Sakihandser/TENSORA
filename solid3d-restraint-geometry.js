'use strict';

const { validateRestraintGuides, restraintGeometryKey } = require('./src/core/solid3d-restraint-data.js');
const AXES = [0, 1, 2];

function dimension(guide) {
  if (guide.kind==='point') return 'Point';
  if (guide.kind==='volume') return 'Volume';
  return guide.kind === 'edge' || guide.kind === 'line' ? 'Curve' : 'Surface';
}

function toolGeometry(guide, index) {
  const prefix = 'bc' + index;
  const lines = [];
  const addPoint = (coordinates, offset) => {
    const tag = prefix + 'p' + offset;
    lines.push(tag+' = newp; Point('+tag+') = {'+coordinates.join(',')+'};');
    return tag;
  };
  if (guide.kind === 'point') {
    lines.push(prefix+'tool = '+addPoint(guide.at, 0)+';');
  } else if (guide.kind === 'line') {
    const a = addPoint(guide.start, 0), b = addPoint(guide.end, 1);
    lines.push(prefix+'tool = newl; Line('+prefix+'tool) = {'+a+','+b+'};');
  } else {
    const [u, v] = AXES.filter(axis => axis !== guide.axis);
    const vertices = [[0,0], [1,0], [1,1], [0,1]].map(([i,j], index) => {
      const coordinates = [...guide.min];
      if (i) coordinates[u] = guide.max[u];
      if (j) coordinates[v] = guide.max[v];
      return addPoint(coordinates, index);
    });
    const edges = vertices.map((vertex, index) => {
      const tag = prefix+'l'+index;
      lines.push(tag+' = newl; Line('+tag+') = {'+vertex+','+vertices[(index+1)%4]+'};');
      return tag;
    });
    lines.push(prefix+'loop = newll; Curve Loop('+prefix+'loop) = {'+edges.join(',')+'};');
    lines.push(prefix+'tool = news; Plane Surface('+prefix+'tool) = {'+prefix+'loop};');
  }
  return lines;
}

// A viewport hit lies on a tessellated triangle. If the exact face rejects
// that point, intersect a short probe along the triangle normal with the CAD
// face and use the closest crossing. Leave the original CAD surface intact.
function projectClickedPoint(guide,name) {
  const {normal,radius}=guide.projection;
  const start=guide.at.map((value,i)=>value-radius*normal[i]);
  const end=guide.at.map((value,i)=>value+radius*normal[i]);
  if (![...start,...end,radius*radius].every(Number.isFinite)) throw Error('几何边界条件数据无效。');
  const [x,y,z]=guide.at;
  return [
    'If (#'+name+'target[] == 0)',
    '  savedPoints[] = Point{:}; savedCurves[] = Curve{:}; savedSurfaces[] = Surface{:};',
    '  probeStart = newp; Point(probeStart) = {'+start.join(',')+'};',
    '  probeEnd = newp; Point(probeEnd) = {'+end.join(',')+'};',
    '  probe = newl; Line(probe) = {probeStart,probeEnd};',
    '  BooleanFragments{ Curve{probe}; Delete; }{ Surface{'+guide.entity+'}; }',
    '  newPoints[] = Point{:}; newPoints[] -= savedPoints[];',
    '  best = '+(radius*radius*(1-1e-6))+'; found = 0;',
    '  If (#newPoints[] > 0)',
    '    For k In {0:#newPoints[]-1}',
    '      xyz[] = Point{newPoints[k]};',
    '      delta = (xyz[0]-('+x+'))^2+(xyz[1]-('+y+'))^2+(xyz[2]-('+z+'))^2;',
    '      along = (xyz[0]-('+x+'))*('+normal[0]+')+(xyz[1]-('+y+'))*('+normal[1]+')+(xyz[2]-('+z+'))*('+normal[2]+');',
    '      If (delta < best && delta-along^2 < '+Math.max(1e-18,radius*radius*1e-12)+')',
    '        best = delta; found = 1; '+name+'pos[] = xyz[];',
    '      EndIf',
    '    EndFor',
    '  EndIf',
    '  newSurfaces[] = Surface{:}; newSurfaces[] -= savedSurfaces[];',
    '  newCurves[] = Curve{:}; newCurves[] -= savedCurves[];',
    '  Recursive Delete{ Surface{newSurfaces[]}; Curve{newCurves[]}; }',
    '  newPoints[] = Point{:}; newPoints[] -= savedPoints[];',
    '  Delete{ Point{newPoints[]}; }',
    '  If (found)',
    '    tool = newp; Point(tool) = {'+name+'pos[0],'+name+'pos[1],'+name+'pos[2]};',
    '    '+name+'target[] = BooleanIntersection{ Point{tool}; Delete; }{ Surface{'+guide.entity+'}; };',
    '  EndIf',
    'EndIf',
  ];
}

function appendRestraintGeometry(script, guides) {
  validateRestraintGuides(guides);
  if (!guides.length) return script;
  // Whole faces, edges and volumes already have stable CAD tags when no
  // geometry needs to be split for a point, line or patch.
  if (guides.every(guide=>['face','edge','volume'].includes(guide.kind))) {
    const lines=[script,'Printf("TENSORA restraints") > "restraint-groups.txt";'];
    guides.forEach((guide,index)=>{
      if (guide.kind==='volume'&&guide.entity===0) return;
      lines.push(`measure = Mass ${dimension(guide)}{${guide.entity}};`);
      lines.push(`Printf("R %g %.17g", ${index}, measure) >> "restraint-groups.txt";`);
      lines.push(`Printf("M %g %g %.17g", ${index}, ${guide.entity}, measure) >> "restraint-groups.txt";`);
    });
    return lines.join('\n')+'\n';
  }
  const lines = [script, 'bcPointTools[] = {}; bcCurveTools[] = {}; bcSurfaceTools[] = {}; bcCurveRefs[] = {}; bcSurfaceRefs[] = {}; bcVolumeRefs[] = {};'];
  lines.push('bcVolumes[] = Volume{:};');
  guides.forEach((guide, index) => {
    const name = 'bc'+index, type = dimension(guide);
    if (guide.kind==='volume'&&guide.entity===0) return;
    if (guide.kind==='point'||guide.kind==='line'||guide.kind==='patch') {
      lines.push(...toolGeometry(guide, index));
      if(guide.kind==='point')lines.push(name+'pos[] = {'+guide.at.join(',')+'};');
      else lines.push(name+'bounds[] = BoundingBox '+type+'{'+name+'tool};');
      lines.push(name+'target[] = BooleanIntersection{ '+type+'{'+name+'tool}; Delete; }{ Surface{'+guide.entity+'}; };');
      if(guide.kind==='point'&&guide.projection)lines.push(...projectClickedPoint(guide,name));
      lines.push('bc'+type+'Tools[] += '+name+'target[];');
    } else {
      lines.push(name+'bounds[] = BoundingBox '+type+'{'+guide.entity+'};');
      lines.push(name+'target[] = {'+guide.entity+'};');
    }
    if (guide.kind==='point') return;
    lines.push(name+'ref[] = {};');
    lines.push('If (#'+name+'target[] > 0)');
    lines.push('  '+name+'ref[] = Duplicata{ '+type+'{'+name+'target[]}; };');
    lines.push('  bc'+type+'Refs[] += '+name+'ref[];');
    lines.push('EndIf');
  });
  lines.push('If (#bcPointTools[] + #bcCurveTools[] + #bcSurfaceTools[] > 0)');
  lines.push('  BooleanFragments{ Volume{bcVolumes[]}; Delete; }{ Point{bcPointTools[]}; Curve{bcCurveTools[]}; Surface{bcSurfaceTools[]}; Delete; }');
  lines.push('EndIf');
  lines.push('Geometry.OCCBooleanPreserveNumbering = 0;');
  lines.push('Printf("TENSORA restraints") > "restraint-groups.txt";');
  // Identify the resulting entities by exact OCC coverage of each retained reference.
  // The bounding box only reduces the number of boolean operations.
  guides.forEach((guide, index) => {
    const name = 'bc'+index, type = dimension(guide);
    if (guide.kind==='volume'&&guide.entity===0) return;
    const bounds = Array.from({length:6}, (_, i) => name+'bounds['+i+']'+(i<3?'-':'+')+'1e-6');
    if (guide.kind==='point') {
      const coordinates=Array.from({length:6},(_,i)=>name+'pos['+(i%3)+']'+(i<3?'-':'+')+'1e-6');
      lines.push('If (#'+name+'target[] > 0)');
      lines.push('  Printf("P %g %.17g %.17g %.17g", '+index+', '+name+'pos[0], '+name+'pos[1], '+name+'pos[2]) >> "restraint-groups.txt";');
      lines.push('  candidates[] = Point In BoundingBox{'+coordinates.join(',')+'};');
      lines.push('  If (#candidates[] > 0)');
      lines.push('    For j In {0:#candidates[]-1}');
      lines.push('      Printf("M %g %g 1", '+index+', candidates[j]) >> "restraint-groups.txt";');
      lines.push('    EndFor');
      lines.push('  EndIf');
      lines.push('EndIf');
      return;
    }
    lines.push('If (#'+name+'ref[] > 0)');
    lines.push('  expected = 0;');
    lines.push('  For j In {0:#'+name+'ref[]-1}');
    lines.push('    expected += Mass '+type+'{'+name+'ref[j]};');
    lines.push('  EndFor');
    lines.push('  Printf("R %g %.17g", '+index+', expected) >> "restraint-groups.txt";');
    lines.push('  candidates[] = '+type+' In BoundingBox{'+bounds.join(',')+'};');
    lines.push('  candidates[] -= bc'+type+'Refs[];');
    lines.push('  If (#candidates[] > 0)');
    lines.push('    For j In {0:#candidates[]-1}');
    lines.push('      trial[] = Duplicata{ '+type+'{candidates[j]}; };');
    lines.push('      remainder[] = BooleanDifference{ '+type+'{trial[]}; Delete; }{ '+type+'{'+name+'ref[]}; };');
    lines.push('      If (#remainder[] == 0)');
    lines.push('        measure = Mass '+type+'{candidates[j]};');
    lines.push('        Printf("M %g %g %.17g", '+index+', candidates[j], measure) >> "restraint-groups.txt";');
    lines.push('      Else');
    lines.push('        Recursive Delete{ '+type+'{remainder[]}; }');
    lines.push('      EndIf');
    lines.push('    EndFor');
    lines.push('  EndIf');
    lines.push('EndIf');
  });
  lines.push('Recursive Delete{ Curve{bcCurveRefs[]}; Surface{bcSurfaceRefs[]}; Volume{bcVolumeRefs[]}; }');
  return lines.join('\n')+'\n';
}

function bindRestraintGroups(mesh, guides, report) {
  const reports = guides.map(() => ({expected:0, entities:[]}));
  for (const row of report.trim().split(/\r?\n/).slice(1)) {
    const [kind, index, value, measure, z] = row.trim().split(/\s+/);
    if (kind === 'R') reports[index].expected = Number(value);
    if (kind === 'M') reports[index].entities.push({id:value, measure:Number(measure)});
    if (kind === 'P') reports[index].point=[value,measure,z].map(Number);
  }
  const surfaces = new Map(mesh.surfaces.map(face => [face.id, face.triangles]));
  const edges = new Map(mesh.edges.map(edge => [edge.id, edge.segments]));
  const vertices = new Map(mesh.vertices.map(vertex=>[vertex.id,vertex.node]));
  const volumes = new Set(mesh.volumes.map(volume=>volume.id));
  const boundary = new Set();
  if (guides.some(guide=>guide.kind==='point')) {
    for (const face of mesh.surfaces) for (const triangle of face.triangles) {
      for (const node of triangle) boundary.add(node);
    }
  }
  return guides.map((guide, index) => {
    const group={id:guide.id,geometry:restraintGeometryKey(guide),nodes:[]};
    if (guide.kind==='volume'&&guide.entity===0) return {...group,volumes:null};
    const {expected, entities, point} = reports[index];
    const error=()=>Error('第 '+(index+1)+' 项几何边界条件无法绑定，请检查所选对象和坐标。');
    if (guide.kind==='point') {
      if(!point?.every(Number.isFinite))throw error();
      const tolerance=1e-9+16*Number.EPSILON*Math.max(...point.map(Math.abs));
      const ids=new Set(entities.map(entity=>vertices.get(entity.id)).filter(node=>
        boundary.has(node)&&mesh.nodes[node].every((value,axis)=>Math.abs(value-point[axis])<=tolerance)));
      if (ids.size!==1) throw error();
      return {...group,nodes:[...ids]};
    }
    const type=dimension(guide);
    const source = type==='Curve'?edges:surfaces;
    const ids = new Set();
    const matched=[];
    let covered = 0;
    for (const {id, measure} of entities) {
      if (type==='Volume') {
        if (volumes.has(id)) {covered+=measure;matched.push(id);}
        continue;
      }
      const elements = source.get(id);
      if (!elements?.length) continue;
      covered += measure;
      matched.push(id);
      for (const element of elements) for (const node of element) ids.add(node);
    }
    if (!(expected > 0) || !Number.isFinite(expected) || !Number.isFinite(covered) ||
        Math.abs(covered/expected - 1) > 1e-6 || !matched.length) {
      throw error();
    }
    if (type==='Volume') return {...group,volumes:matched};
    return {...group,nodes:[...ids],entities:matched};
  });
}

module.exports = { appendRestraintGeometry, bindRestraintGroups };
