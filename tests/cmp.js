// Compare two benchmark runs: node tests/cmp.js baseline speedR
const fs=require('fs');
const A=JSON.parse(fs.readFileSync(__dirname+'/bench_'+process.argv[2]+'.json'));
const B=JSON.parse(fs.readFileSync(__dirname+'/bench_'+process.argv[3]+'.json'));
const TYS=['cessna','reaper','f16'];
for(const ty of TYS){
  console.log('== '+ty+'  hold '+A.hold[ty].t.toFixed(0)+' -> '+B.hold[ty].t.toFixed(0)+
    '  ('+(((B.hold[ty].t-A.hold[ty].t)/A.hold[ty].t*100).toFixed(0))+'%)');
  let line='   k: ';
  A.rand[ty].rows.forEach((r,k)=>{const b=B.rand[ty].rows[k];
    const d=(b.t-r.t)/r.t*100;
    line+=`${String(k).padStart(2)}:${r.t.toFixed(0).padStart(4)}->${b.t.toFixed(0).padStart(4)}(${d>0?'+':''}${d.toFixed(0)}%)${b.crash?'!':''} `;});
  console.log(line);
  console.log('   avg '+A.rand[ty].avg.toFixed(1)+' -> '+B.rand[ty].avg.toFixed(1)+
    '  ('+(((B.rand[ty].avg-A.rand[ty].avg)/A.rand[ty].avg*100).toFixed(1))+'%)  maxfpm '+B.rand[ty].maxFpm);
}
