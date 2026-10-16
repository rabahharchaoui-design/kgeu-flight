# Fix2 item 2: which shader programs does AI traffic link in flight that the warm-up missed?
# One page load per case (844x390, the graphics_shots harness): wait for the precompile queue and the WARM steps,
# record __kgeu.progList(), start a free flight with traffic on, run the traffic with rendered frames, and print every
# NEW program (name, cacheKey) with a diff against the closest program that existed before, plus TFC.spawns.
#   timeout 110 .venv/bin/python -u tests/traffic_prog_probe.py --case az_f16 [--tier medium]
# cases: az_f16 (F-16 kgeu day, then night, force all types, clear and respawn, sunset), az_cessna (luke),
#        az_737 (phx), rjtt, lfpg, sbrj (F-16 then the airliner each)
import asyncio, os, sys, json
args = sys.argv[1:]
def opt(n, d):
    if n in args:
        i = args.index(n); v = args[i + 1]; del args[i:i + 2]; return v
    return d
CASE = opt('--case', 'az_f16')
CLOUDS = opt('--clouds', '')   # force a cloud preset (scattered, clear, monsoon) for the flights
BOOT_TOD = opt('--boot-tod', '')   # the time of day the page boots with (localStorage kgeuTOD)
EARLY = '--early' in args   # start the flight as soon as the precompile queue drains, the menu's WARM steps not yet run
os.environ['PFS_TIER'] = opt('--tier', 'medium')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright   # noqa: E402
import graphics_shots as G   # noqa: E402
K = G.K
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
REG = {'rjtt': 'rjtt', 'lfpg': 'lfpg', 'sbrj': 'sbrj'}.get(CASE)
PLAN = {'az_f16': [('f16', 'kgeu')], 'az_cessna': [('cessna', 'luke')], 'az_737': [('b737', 'phx')]}.get(CASE, [('f16', None), ('b737', None)])

# run traffic n updates of dt, a rendered frame every k
RUN = f"""([n,dt,k])=>{{const K={K};for(let i=0;i<n;i++){{K.TFC.update(dt);if(i%k===0)K.stepFrame(1/30);}}K.stepFrame(1/30);return K.tfcList().length;}}"""
FORCE_B = f"""const K={K},out=[];K.tfcClear();for(const t of Object.keys(K.TFC.pool)){{for(let j=0;j<K.TFC.pool[t].length;j++)out.push([t,K.tfcSpawn(t,{{force:true}})]);}}
  for(let i=0;i<4;i++)K.stepFrame(1/30);return out;"""
FORCE = "()=>{" + FORCE_B + "}"

# r128 WebGLPrograms parameterNames, in cache key order after the shader id (and any defines)
PN = ('precision isWebGL2 supportsVertexTextures outputEncoding instancing instancingColor map mapEncoding matcap matcapEncoding envMap envMapMode '
      'envMapEncoding envMapCubeUV lightMap lightMapEncoding aoMap emissiveMap emissiveMapEncoding bumpMap normalMap objectSpaceNormalMap '
      'tangentSpaceNormalMap clearcoatMap clearcoatRoughnessMap clearcoatNormalMap displacementMap specularMap roughnessMap metalnessMap gradientMap '
      'alphaMap combine vertexColors vertexAlphas vertexTangents vertexUvs uvsVertexOnly fog useFog fogExp2 flatShading sizeAttenuation '
      'logarithmicDepthBuffer skinning maxBones useVertexTexture morphTargets morphNormals premultipliedAlpha numDirLights numPointLights '
      'numSpotLights numHemiLights numRectAreaLights numDirLightShadows numPointLightShadows numSpotLightShadows shadowMapEnabled shadowMapType '
      'toneMapping physicallyCorrectLights alphaTest doubleSided flipSided numClippingPlanes numClipIntersection depthPacking dithering sheen '
      'transmissionMap rendererOutputEncoding gammaFactor customProgramCacheKey').split()
def diff(a, b):
    A, B = a.split(','), b.split(',')
    out = []
    for i in range(max(len(A), len(B))):
        x = A[i] if i < len(A) else '-'; y = B[i] if i < len(B) else '-'
        # names hold for a built-in material without defines (the shader id is entry 0)
        nm = PN[i - 1] if 0 < i <= len(PN) and len(A) == len(PN) + 1 else f'#{i}'
        if x != y: out.append(f'{nm} {y[:60]} -> {x[:60]}')
    return out
# who holds a program: the scene objects whose material's current program has that cache key
OWNERS = f"""(keys)=>{{const R={K}.R3(),r=R.renderer,out={{}};const want=new Set(keys);
  R.scene.traverse(o=>{{const M=o.material?(Array.isArray(o.material)?o.material:[o.material]):[];
    for(const m of M){{const p=r.properties.get(m),pr=p&&p.currentProgram;if(!pr||!want.has(pr.cacheKey))continue;
      const a=out[pr.cacheKey]=out[pr.cacheKey]||[];let n=o,path=[];while(n&&path.length<4){{path.push(n.name||n.type);n=n.parent;}}
      const nm=path.join('<')+' '+m.type+(m.name?' '+m.name:'')+' fog:'+m.fog+' vis:'+o.visible;
      if(a.length<4&&a.indexOf(nm)<0)a.push(nm);}}}});
  return keys.map(k=>out[k]?out[k].join(' | '):'gone');}}"""

async def main():
    url = G.serve(ROOT)
    init = G.INIT + (f"localStorage.setItem('kgeuRegion','{REG}');" if REG else '') + (f"localStorage.setItem('kgeuTOD','{BOOT_TOD}');" if BOOT_TOD else '')
    async with async_playwright() as p:
        b = await G.launch(p)
        ctx = await b.new_context(viewport={'width': 844, 'height': 390}, is_mobile=True, has_touch=True, device_scale_factor=2)
        await ctx.add_init_script(init)
        pg = await ctx.new_page(); errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.route('**/three.min.js', lambda r: r.fulfill(body=G.THREE, content_type='application/javascript'))
        await pg.route('**/fonts.g*/**', lambda r: r.abort())
        await pg.goto(url); await pg.wait_for_function(f'()=>{K}', timeout=30000)
        if REG: await pg.wait_for_function(f"()=>{K}.WORLD.ready||{K}.WORLD.err", timeout=30000)
        if EARLY:
            await pg.wait_for_function(f"()=>{K}.boot().pre.done", timeout=90000, polling=50)
            print('  early start: WARM step', await pg.evaluate(f"()=>{K}.warmTimes().ms.length"), 'of', await pg.evaluate(f"()=>{K}.warmTimes().n"))
        else:
            await pg.wait_for_function(f"()=>{K}.boot().pre.done&&{K}.warm()&&{K}.warmTimes().total>0", timeout=90000, polling=250)
        seen = await pg.evaluate(f"()=>{K}.progList()")
        print(f'{CASE}: {len(seen)} programs after the warm-up', flush=True)
        async def report(label, now):
            old = {q['cacheKey'] for q in seen}
            new = [q for q in now if q['cacheKey'] not in old]
            own = await pg.evaluate(OWNERS, [q['cacheKey'] for q in new]) if new else []
            print(f'  {label}: {len(new)} new', flush=True)
            for q, o in zip(new, own):
                best = min(seen, key=lambda s: (s['name'] != q['name'], len(diff(q['cacheKey'], s['cacheKey']))))
                print(f"    NEW id {q['id']} {q['name']} used {q['usedTimes']}\n      key {q['cacheKey'][:300]}")
                print(f"      closest id {best['id']} {best['name']}: " + '; '.join(diff(q['cacheKey'], best['cacheKey'])[:8]))
                print(f"      used by: {o}")
            seen.extend(new)
        async def step(label, js, a=None):
            r = await pg.evaluate(js, a) if a is not None else await pg.evaluate(js)
            await report(label, await pg.evaluate(f"()=>{K}.progList()")); return r
        for t, base in PLAN:
            await pg.evaluate(f"()=>{{const K={K};K.setSkill('pilot');K.setTOD('day');}}")
            js = f"()=>{{const K={K};K.TFC.auto=true;" + (f"K.setClouds('{CLOUDS}');" if CLOUDS else '') + f"K.pick('{t}');" + (f"K.pickBase('{base}');" if base else '') + "K.start('runway');K.stepFrame(1/30);}"
            await step(f'{t} start', js)
            n = await step(f'{t} day 20 s', RUN, [40, 0.5, 4])
            sp = await pg.evaluate(f"()=>{K}.TFC.spawns.map(s=>s.type+':'+s.state+(s.forced?'*':''))")
            print(f'    alive {n}, spawns {sp}')
            await step('night', f"()=>{{{K}.setTOD('night');{K}.stepFrame(1/30);}}")
            await step('night 20 s', RUN, [40, 0.5, 4])
            r = await step('force all types', FORCE)
            print('    forced', [x for x in r if x[1] is None] or 'all')
            await step('clear + respawn', "()=>{" + FORCE_B + "}")
            await step('sunset', f"()=>{{{K}.setTOD('sunset');{K}.stepFrame(1/30);}}")
            await step('sunset 20 s', RUN, [40, 0.5, 4])
            await step('day force', f"()=>{{{K}.setTOD('day');" + FORCE_B + "}")
        print('page errors:', errs[:5])
        await b.close()

asyncio.run(main())
