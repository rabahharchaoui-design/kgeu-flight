// Pocket Flight Sim service worker (phone3 item 8): the game opens and flies in airplane mode after one
// online visit. Registered by index.html as sw.js?v=<APP_VER>, so every shipped version installs a new
// worker with its own cache (pfs-<ver>), takes over at once and drops the older caches. The page's own
// version.json check still reloads a stale page once.
//   index.html (navigations), version.json, the playlist: network first, revalidating, the cache when offline
//   everything else of the game (radio clips, region data, icons): cache first, precached on install
//   music tracks: cached as they are played (pfs-music, kept across versions)
//   three.js and the fonts (other origins): cache first (pfs-ext, kept across versions)
//   the leaderboard Worker: never touched (runs queue in the page while offline)
const VER=new URL(self.location).searchParams.get('v')||'dev';
const CORE='pfs-'+VER,MUSIC='pfs-music',EXT='pfs-ext';
const THREE_URL='https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
// PRECACHE-START
const PRE=["./","index.html","manifest.json","assets/music/playlist.json","icons/apple-touch-icon.png","icons/favicon-32.png","icons/icon-1024.png","icons/icon-192.png","icons/icon-512.png","icons/share-card.png","assets/map/lfpg.bin?v=1","assets/map/phx.bin?v=1","assets/map/rjtt.bin?v=1","assets/map/sbrj.bin?v=1","assets/world/lfpg.json?v=1","assets/world/rjtt.json?v=1","assets/world/sbrj.json?v=1","radio/c_tcas_clear.m4a","radio/c_tcas_climb.m4a","radio/c_tcas_climb_now.m4a","radio/c_tcas_descend.m4a","radio/c_tcas_descend_now.m4a","radio/c_tcas_e_clear.m4a","radio/c_tcas_e_climb.m4a","radio/c_tcas_e_descend.m4a","radio/c_tcas_e_traffic.m4a","radio/c_tcas_traffic.m4a","radio/d_a_angels.m4a","radio/d_a_b_e.m4a","radio/d_a_b_n.m4a","radio/d_a_b_ne.m4a","radio/d_a_b_nw.m4a","radio/d_a_b_s.m4a","radio/d_a_b_se.m4a","radio/d_a_b_sw.m4a","radio/d_a_b_w.m4a","radio/d_a_bandit.m4a","radio/d_a_clean.m4a","radio/d_a_deck.m4a","radio/d_a_fightson.m4a","radio/d_a_g1.m4a","radio/d_a_g2.m4a","radio/d_a_g3.m4a","radio/d_a_g4.m4a","radio/d_a_hot.m4a","radio/d_a_kio.m4a","radio/d_a_miles.m4a","radio/d_a_num_10.m4a","radio/d_a_num_11.m4a","radio/d_a_num_12.m4a","radio/d_a_num_13.m4a","radio/d_a_num_14.m4a","radio/d_a_num_15.m4a","radio/d_a_num_16.m4a","radio/d_a_num_17.m4a","radio/d_a_num_18.m4a","radio/d_a_num_19.m4a","radio/d_a_num_20.m4a","radio/d_a_num_5.m4a","radio/d_a_rtr.m4a","radio/d_a_s30.m4a","radio/d_a_sentry.m4a","radio/d_c_altitude.m4a","radio/d_c_bingo.m4a","radio/d_c_flares.m4a","radio/d_c_launch.m4a","radio/d_c_pullup.m4a","radio/d_c_warning.m4a","radio/d_w_break_l.m4a","radio/d_w_break_r.m4a","radio/d_w_fox2.m4a","radio/d_w_goodkill.m4a","radio/d_w_guns.m4a","radio/d_w_kio.m4a","radio/d_w_niceflares.m4a","radio/d_w_six.m4a","radio/d_w_splash_1.m4a","radio/d_w_splash_10.m4a","radio/d_w_splash_2.m4a","radio/d_w_splash_3.m4a","radio/d_w_splash_4.m4a","radio/d_w_splash_5.m4a","radio/d_w_splash_6.m4a","radio/d_w_splash_7.m4a","radio/d_w_splash_8.m4a","radio/d_w_splash_9.m4a","radio/d_w_tally1.m4a","radio/d_w_tally2.m4a","radio/d_w_winchester.m4a","radio/p_ch_br_p1.m4a","radio/p_ch_br_p2.m4a","radio/p_ch_br_p3.m4a","radio/p_ch_fr_p1.m4a","radio/p_ch_fr_p2.m4a","radio/p_ch_fr_p3.m4a","radio/p_ch_jp_p1.m4a","radio/p_ch_jp_p2.m4a","radio/p_ch_jp_p3.m4a","radio/p_ch_p1.m4a","radio/p_ch_p10.m4a","radio/p_ch_p11.m4a","radio/p_ch_p12.m4a","radio/p_ch_p2.m4a","radio/p_ch_p3.m4a","radio/p_ch_p4.m4a","radio/p_ch_p5.m4a","radio/p_ch_p6.m4a","radio/p_ch_p7.m4a","radio/p_ch_p8.m4a","radio/p_ch_p9.m4a","radio/p_cs_archer.m4a","radio/p_cs_archer_s.m4a","radio/p_cs_hawg.m4a","radio/p_cs_herky.m4a","radio/p_cs_pipistrel.m4a","radio/p_cs_pipistrel_s.m4a","radio/p_cs_pocket320.m4a","radio/p_cs_pocket737.m4a","radio/p_cs_pocket747.m4a","radio/p_cs_reaper.m4a","radio/p_cs_reaper_s.m4a","radio/p_cs_skyguardian.m4a","radio/p_cs_skyguardian_s.m4a","radio/p_cs_skyhawk.m4a","radio/p_cs_skyhawk_s.m4a","radio/p_cs_viper.m4a","radio/p_degaulle_ground.m4a","radio/p_degaulle_tower.m4a","radio/p_glendale_ground.m4a","radio/p_glendale_tower.m4a","radio/p_hold_closed.m4a","radio/p_j_10s.m4a","radio/p_j_1min.m4a","radio/p_j_green.m4a","radio/p_load_away.m4a","radio/p_luke_ground.m4a","radio/p_luke_tower.m4a","radio/p_phoenix_approach.m4a","radio/p_phoenix_ground.m4a","radio/p_phoenix_tower.m4a","radio/p_rb_cleared_land.m4a","radio/p_rb_cleared_option.m4a","radio/p_rb_cleared_tg.m4a","radio/p_rb_cleared_to.m4a","radio/p_rb_roger.m4a","radio/p_rb_traffic.m4a","radio/p_rb_wilco.m4a","radio/p_rifle.m4a","radio/p_santosdumont_ground.m4a","radio/p_santosdumont_tower.m4a","radio/p_tokyo_ground.m4a","radio/p_tokyo_tower.m4a","radio/t_above.m4a","radio/t_at.m4a","radio/t_below.m4a","radio/t_c_10.m4a","radio/t_c_11.m4a","radio/t_c_12.m4a","radio/t_ch_br_t1.m4a","radio/t_ch_br_t2.m4a","radio/t_ch_br_t3.m4a","radio/t_ch_fr_t1.m4a","radio/t_ch_fr_t2.m4a","radio/t_ch_fr_t3.m4a","radio/t_ch_jp_t1.m4a","radio/t_ch_jp_t2.m4a","radio/t_ch_jp_t3.m4a","radio/t_ch_t1.m4a","radio/t_ch_t2.m4a","radio/t_ch_t3.m4a","radio/t_ch_t4.m4a","radio/t_ch_t5.m4a","radio/t_ch_t6.m4a","radio/t_ch_t7.m4a","radio/t_ch_t8.m4a","radio/t_ch_t9.m4a","radio/t_cleared_hot.m4a","radio/t_cleared_land.m4a","radio/t_cleared_low.m4a","radio/t_cleared_option.m4a","radio/t_cleared_tg.m4a","radio/t_cleared_to.m4a","radio/t_closed_traffic.m4a","radio/t_crash.m4a","radio/t_cs_archer.m4a","radio/t_cs_archer_s.m4a","radio/t_cs_hawg.m4a","radio/t_cs_herky.m4a","radio/t_cs_pipistrel.m4a","radio/t_cs_pipistrel_s.m4a","radio/t_cs_pocket320.m4a","radio/t_cs_pocket737.m4a","radio/t_cs_pocket747.m4a","radio/t_cs_reaper.m4a","radio/t_cs_reaper_s.m4a","radio/t_cs_skyguardian.m4a","radio/t_cs_skyguardian_s.m4a","radio/t_cs_skyhawk.m4a","radio/t_cs_skyhawk_s.m4a","radio/t_cs_viper.m4a","radio/t_degaulle_ground.m4a","radio/t_degaulle_tower.m4a","radio/t_dz_smoke.m4a","radio/t_gila_range.m4a","radio/t_glendale_ground.m4a","radio/t_glendale_tower.m4a","radio/t_go_around.m4a","radio/t_good_hit.m4a","radio/t_haboob_glendale.m4a","radio/t_haboob_luke.m4a","radio/t_haboob_phoenix.m4a","radio/t_hold_short.m4a","radio/t_hundred_feet.m4a","radio/t_lineup_wait.m4a","radio/t_long.m4a","radio/t_luke_ground.m4a","radio/t_luke_security.m4a","radio/t_luke_tower.m4a","radio/t_meters.m4a","radio/t_mile.m4a","radio/t_miles.m4a","radio/t_miss.m4a","radio/t_n_0.m4a","radio/t_n_1.m4a","radio/t_n_10.m4a","radio/t_n_2.m4a","radio/t_n_3.m4a","radio/t_n_4.m4a","radio/t_n_5.m4a","radio/t_n_6.m4a","radio/t_n_7.m4a","radio/t_n_8.m4a","radio/t_n_9.m4a","radio/t_nice_landing.m4a","radio/t_oclock.m4a","radio/t_of_four.m4a","radio/t_phoenix_approach.m4a","radio/t_phoenix_ground.m4a","radio/t_phoenix_tower.m4a","radio/t_range_cold.m4a","radio/t_report_initial.m4a","radio/t_reset_again.m4a","radio/t_rwy_02l.m4a","radio/t_rwy_02r.m4a","radio/t_rwy_03l.m4a","radio/t_rwy_03r.m4a","radio/t_rwy_04.m4a","radio/t_rwy_05.m4a","radio/t_rwy_07l.m4a","radio/t_rwy_08l.m4a","radio/t_rwy_08r.m4a","radio/t_rwy_09l.m4a","radio/t_rwy_09r.m4a","radio/t_rwy_1.m4a","radio/t_rwy_16l.m4a","radio/t_rwy_16r.m4a","radio/t_rwy_19.m4a","radio/t_rwy_20l.m4a","radio/t_rwy_20r.m4a","radio/t_rwy_21l.m4a","radio/t_rwy_21r.m4a","radio/t_rwy_22.m4a","radio/t_rwy_23.m4a","radio/t_rwy_25r.m4a","radio/t_rwy_26l.m4a","radio/t_rwy_26r.m4a","radio/t_rwy_27l.m4a","radio/t_rwy_27r.m4a","radio/t_rwy_34l.m4a","radio/t_rwy_34r.m4a","radio/t_same_alt.m4a","radio/t_santosdumont_ground.m4a","radio/t_santosdumont_tower.m4a","radio/t_taxi_alpha.m4a","radio/t_tfc_airliner.m4a","radio/t_tfc_banner.m4a","radio/t_tfc_c17.m4a","radio/t_tfc_cessna.m4a","radio/t_tfc_f16.m4a","radio/t_tfc_heli.m4a","radio/t_tfc_reaper.m4a","radio/t_tfc_vipers.m4a","radio/t_thousand_feet.m4a","radio/t_tokyo_ground.m4a","radio/t_tokyo_tower.m4a","radio/t_traffic.m4a","radio/t_wheels_down.m4a","radio/t_wind.m4a"];
// PRECACHE-END
self.addEventListener('install',e=>{
  e.waitUntil((async()=>{
    const c=await caches.open(CORE);
    // the page and three.js must be there; the rest is best effort (a clip that fails comes on its first use)
    await c.addAll(['./','index.html'].map(u=>new Request(u,{cache:'reload'})));
    try{const ext=await caches.open(EXT);if(!(await ext.match(THREE_URL)))await ext.add(new Request(THREE_URL,{mode:'cors'}));}catch(err){}
    await Promise.all(PRE.map(u=>c.match(u).then(h=>h||c.add(new Request(u,{cache:'reload'}))).catch(()=>{})));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate',e=>{
  e.waitUntil((async()=>{
    for(const k of await caches.keys())if(k.startsWith('pfs-')&&k!==CORE&&k!==MUSIC&&k!==EXT)await caches.delete(k);
    await self.clients.claim();
  })());
});
async function networkFirst(req,key,opt){
  const c=await caches.open(CORE);
  try{const r=await fetch(req,opt);if(r&&r.ok)c.put(key||req,r.clone()).catch(()=>{});return r;}
  catch(err){const h=await c.match(key||req,{ignoreSearch:true});if(h)return h;throw err;}
}
async function cacheFirst(req,name){
  const c=await caches.open(name),h=await c.match(req);if(h)return h;
  const r=await fetch(req);if(r&&(r.ok||r.type==='opaque'))c.put(req,r.clone()).catch(()=>{});return r;
}
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const u=new URL(req.url);
  if(u.origin===self.location.origin){
    const path=u.pathname.slice(new URL(self.registration.scope).pathname.length);
    if(req.mode==='navigate'||path===''||path==='index.html'){e.respondWith(networkFirst(req,'index.html',{cache:'no-cache'}));return;}
    if(path==='version.json'){e.respondWith(networkFirst(req,'version.json',{cache:'no-store'}));return;}
    if(path==='assets/music/playlist.json'){e.respondWith(networkFirst(req,'assets/music/playlist.json',{cache:'no-cache'}));return;}
    if(path==='sw.js')return;
    if(path.startsWith('assets/music/')){e.respondWith(cacheFirst(req,MUSIC));return;}
    e.respondWith(cacheFirst(req,CORE));return;
  }
  if(u.hostname==='cdnjs.cloudflare.com'||u.hostname==='fonts.googleapis.com'||u.hostname==='fonts.gstatic.com'){e.respondWith(cacheFirst(req,EXT));return;}
  // anything else (the leaderboard Worker): the network, as if there were no worker
});
