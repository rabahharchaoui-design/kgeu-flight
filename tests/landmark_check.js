// Landmarks against their real positions relative to KGEU.
const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const a=new Function('THREE',phys+'\nreturn {wX,wZ,RWY_LEN,mountains,groundHeight,LANDMARK:typeof LANDMARK!=="undefined"?LANDMARK:null};')(THREE);
const KGEU={lat:33.52683,lon:-112.29517};
const MPD_LAT=110950, MPD_LON=111320*Math.cos(KGEU.lat*Math.PI/180);
const arpX=a.wX(a.RWY_LEN/2,0), arpZ=a.wZ(a.RWY_LEN/2,0);
function world(lat,lon){return [arpX+(lon-KGEU.lon)*MPD_LON, arpZ-(lat-KGEU.lat)*MPD_LAT];}
// what the source actually places
const got={};
const grab=(name,re)=>{const m=src.match(re);got[name]=m?[+m[1],+m[2]]:null;};
grab('State Farm Stadium', /pl\.position\.set\((-?\d+),0\.2,(-?\d+)\)/);
grab('White Tank Mountains', /rangeH\(x,z,(-?\d+),(-?\d+),6500,12500/);
grab('Camelback',           /rangeH\(x,z,(-?\d+),(-?\d+),1900,900/);
grab('Downtown Phoenix',    /b\.position\.set\((\d+)\+\(hash\(k,1\)-0\.5\)\*1600,hgt\/2,(\d+)\+/);
grab('Sky Harbor',          /const SKY_HARBOR=\{x:(-?\d+),z:(-?\d+)/);
const REAL={
  'State Farm Stadium':  [33.52764,-112.26262],
  'White Tank Mountains':[33.58000,-112.55000],
  'Camelback':           [33.51450,-111.96290],
  'Downtown Phoenix':    [33.44840,-112.07400],
  'Sky Harbor':          [33.43430,-112.01160],
};
let bad=0;
for(const k in REAL){
  const w=world(REAL[k][0],REAL[k][1]);
  const g=got[k];
  if(!g){console.log(k.padEnd(22),'NOT FOUND');bad++;continue;}
  const err=Math.hypot(g[0]-w[0],g[1]-w[1]);
  const tol=k==='White Tank Mountains'?1500:400;   // a mountain range has no single point
  if(err>tol)bad++;
  console.log(k.padEnd(22),'placed',String(g[0]).padStart(7),String(g[1]).padStart(7),
    ' real',w[0].toFixed(0).padStart(7),w[1].toFixed(0).padStart(7),
    ' error',err.toFixed(0).padStart(5),'m',err>tol?'  OFF':'');
}
console.log(bad?('FAIL '+bad+' landmark(s) misplaced or missing'):'landmarks OK');
process.exit(bad?1:0);
