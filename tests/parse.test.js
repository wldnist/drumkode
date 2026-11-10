var fs = require("fs"), assert = require("assert");
var src = fs.readFileSync(require("path").join(__dirname, "..", "src", "parse.js"), "utf8");
var STEPS = 16;
var LANES = ["kick","snare","rim","clap","tom","hat","open","ride","crash"].map(function(i){return {id:i};});
function copyPattern(p){ var o={}; LANES.forEach(function(l){ o[l.id]=Array.isArray(p[l.id])?p[l.id].map(function(v){var n=Number(v);return (n===2||n===3)?n:(n>0?1:0);}):new Array(16).fill(0); }); return o; }
function emptyPattern(){ return copyPattern({}); }
eval(src + "\nglobalThis.pj=parseJsonImport; globalThis.pm=midiToProject;");

// json: single pattern + per-bar patterns
var r = pj(JSON.stringify({ bpm: 92, sections: [
  { name: "verse", bars: 4, pattern: { kick: "x..x..x...x.....", HiHat: "x.x.x.x.x.x.x.x." } },
  { name: "chorus", patterns: [
      { kick: "x...............", crash: "x..............." },
      {},
      { ride: "x...x...x...x...", rim: "....x.......x..." } ] }
], arrangement: ["verse", "Chorus"] }));
assert.equal(r.errors.length, 0, JSON.stringify(r));
var S = r.project.sections;
assert.equal(S[0].bars, 4); assert.equal(S[0].patterns.length, 4);
assert.equal(S[0].patterns[3].hat[0], 1);
assert.equal(S[1].bars, 3);
assert.equal(S[1].patterns[0].crash[0], 1);
assert.equal(S[1].patterns[1].kick.some(Boolean), false);
assert.equal(S[1].patterns[2].rim[4], 1);
assert.equal(S[1].patterns[2].ride[8], 1);

// errors / warnings
r = pj('{"sections":[{"name":"a","patterns":[{"kick":"x..x"}]}]}');
assert(/bar 1 \/ kick: panjang 4/.test(r.errors[0]), JSON.stringify(r));
r = pj('{"sections":[{"name":"a","bars":8,"patterns":[{"kick":"x...............","cowbell":"x..............."},{"kick":"x...............","cowbell":"x..............."}]}]}');
assert.equal(r.errors.length, 0);
assert.equal(r.warnings.filter(function(w){return /bars/.test(w);}).length, 1);
assert.equal(r.warnings.filter(function(w){return /cowbell/.test(w);}).length, 1, JSON.stringify(r.warnings)); // sekali saja
r = pj('{"sections":[{"name":"a","pattern":{"xyz":"x..............."}}]}');
assert(/tidak ada lane yang dikenali/.test(r.errors[0]));
r = pj('{"sections":[{"name":"a","pattern":{}}]}');
assert.equal(r.errors.length, 0); // rest
r = pj('{"sections":[{"name":"a","pattern":{"kick":"x..............."}}],"arrangement":["nope"]}');
assert(/tidak ditemukan/.test(r.errors[0]));
r = pj("{bad"); assert(/tidak valid/.test(r.errors[0]));
r = pj('{"sections":[{"name":"a","pattern":{"kick":"x..............."}},{"name":"b"}]}');
assert(r.errors.length === 1);

// midi
function vlq(n){ var b=[n&0x7f]; n>>=7; while(n){ b.unshift((n&0x7f)|0x80); n>>=7;} return b; }
var tp=480, bar=tp*4, sx=tp/4, ev=[];
function note(t,n,v){ ev.push([t,n,v===undefined?100:v]); }
function groove(b,k,s,h,extra){ k.forEach(function(x){note(b*bar+x*sx,36)}); s.forEach(function(x){note(b*bar+x*sx,38)}); h.forEach(function(x){note(b*bar+x*sx,42)}); (extra||[]).forEach(function(e){note(b*bar+e[0]*sx,e[1])}); }
var hh=[0,2,4,6,8,10,12,14];
groove(0,[0,10],[4,12],hh); groove(1,[0,10],[4,12],hh);
groove(2,[0,6],[4,12],hh,[[0,49],[14,45],[8,37],[3,51],[5,56]]); groove(3,[0,6],[4,12],hh);
ev.sort(function(a,b){return a[0]-b[0];});
var trk=[0,0xFF,0x51,3,0x09,0x27,0xC0, 0,0xFF,0x58,4,4,2,0x18,8], last=0;
ev.forEach(function(e){ trk=trk.concat(vlq(e[0]-last)); last=e[0]; trk=trk.concat([0x99,e[1],e[2]]); });
trk=trk.concat([0,0xFF,0x2F,0]);
var hdr=[0x4D,0x54,0x68,0x64,0,0,0,6,0,0,0,1,(tp>>8)&255,tp&255];
var th=[0x4D,0x54,0x72,0x6B,(trk.length>>>24)&255,(trk.length>>>16)&255,(trk.length>>>8)&255,trk.length&255];
var bytes=new Uint8Array(hdr.concat(th,trk));
r = pm(bytes.buffer, "my-song.mid");
assert.equal(r.errors.length, 0, JSON.stringify(r));
var P=r.project;
assert.equal(P.bpm, 100);
assert.deepEqual(P.sections.map(function(s){return s.bars;}), [2,1,1]);
assert.deepEqual(P.arr, [0,1,2]);
assert.equal(P.sections[1].patterns[0].crash[0], 1);
assert.equal(P.sections[1].patterns[0].tom[14], 1);
assert.equal(P.sections[1].patterns[0].rim[8], 1);
assert.equal(P.sections[1].patterns[0].ride[3], 1);
assert(r.warnings.some(function(w){return /1 note diabaikan/.test(w);}), JSON.stringify(r.warnings));
r = pm(new Uint8Array(20).buffer, "x.mid"); assert(r.errors.length===1);
console.log("PARSE TESTS OK");
// ---- velocity: json ----
r = pj('{"sections":[{"name":"v","pattern":{"snare":"....X..o....x..O","kick":[1,2,3,0,5,0,0,0,0,0,0,0,0,0,0,true]}}]}');
assert.equal(r.errors.length, 0, JSON.stringify(r));
var pv = r.project.sections[0].patterns[0];
assert.deepEqual(pv.snare.slice(4,8), [2,0,0,3]);
assert.equal(pv.snare[12], 1); assert.equal(pv.snare[15], 1);   // x dan O = normal
assert.deepEqual(pv.kick.slice(0,5), [1,2,3,0,1]); assert.equal(pv.kick[15], 1);
r = pj('{"sections":[{"name":"v","pattern":{"kick":"x..............z"}}]}');
assert(/x normal, X aksen, o ghost/.test(r.errors[0]), r.errors[0]);

// ---- velocity: midi ----
function buildMidi(events){
  var evs = events.slice().sort(function(a,b){return a[0]-b[0];}), tr=[0,0xFF,0x51,3,0x09,0x27,0xC0], lt=0;
  evs.forEach(function(e){ tr=tr.concat(vlq(e[0]-lt)); lt=e[0]; tr=tr.concat([0x99,e[1],e[2]]); });
  tr=tr.concat([0,0xFF,0x2F,0]);
  var h=[0x4D,0x54,0x68,0x64,0,0,0,6,0,0,0,1,(tp>>8)&255,tp&255];
  var th=[0x4D,0x54,0x72,0x6B,(tr.length>>>24)&255,(tr.length>>>16)&255,(tr.length>>>8)&255,tr.length&255];
  return new Uint8Array(h.concat(th,tr)).buffer;
}
r = pm(buildMidi([[0,36,120],[4*sx,38,90],[8*sx,42,40],[8*sx,42,115],[12*sx,38,50],[2*sx,42,51]]), "vel.mid");
assert.equal(r.errors.length, 0, JSON.stringify(r));
var bp = r.project.sections[0].patterns[0];
assert.equal(bp.kick[0], 2);        // 120 -> aksen
assert.equal(bp.snare[4], 1);       // 90 -> normal
assert.equal(bp.hat[8], 2);         // dua not di langkah sama: ambil yang paling keras
assert.equal(bp.snare[12], 3);      // 50 -> ghost
assert.equal(bp.hat[2], 1);         // 51 -> normal (batas ghost <= 50)
assert(!r.warnings.some(function(w){return /seragam/.test(w);}));
r = pm(buildMidi([[0,36,127],[4*sx,38,127],[8*sx,42,120]]), "flat.mid");
assert(r.warnings.some(function(w){return /seragam/.test(w);}), JSON.stringify(r.warnings));
assert.equal(r.project.sections[0].patterns[0].kick[0], 1);
assert.equal(r.project.sections[0].patterns[0].hat[8], 1);
console.log("VELOCITY TESTS OK");

