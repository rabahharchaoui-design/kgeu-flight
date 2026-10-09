# A stand-in for the pfs-scores Worker, for the ui1 checks and screenshots: the page points LB at a fake URL
# (localStorage kgeuLBUrl) and Playwright answers every call. MOCK.subs records the submissions; MOCK.gain sets the
# XP the fake server grants per run.
import json, random

FAKE = 'https://pfs-mock.test'
NAMES = ['HABOOB', 'SIDEWINDER7', 'MESQUITE', 'VIPERDUST', 'SAGUARO', 'MONSOON', 'GILA', 'COYOTE', 'JAVELINA', 'OCOTILLO',
         'PALOVERDE', 'SCORPION', 'RATTLER', 'ROADRUNNER', 'MIRAGE', 'MESA', 'CANYON', 'SONORAN', 'MOJAVE', 'TUMBLEWEED',
         'CHOLLA', 'YUCCA', 'BUTTE', 'ARROYO', 'DUNE', 'SIROCCO', 'SANDSTORM', 'VULTURE', 'CONDOR', 'CACTUS']
RANKS = ['Nugget', 'Wingman', 'Flight Lead', 'Instructor Pilot', 'Weapons School', 'Top Gun']
ACS = ['cessna', 'f16', 'c130', 'reaper', 'alpha', 'mq9b', 'archer', 'b737']


class Mock:
    def __init__(self, cs='ACEPILOT', xp=1650, rows=30, me_rank=24, gain=37, offline=False):
        self.cs, self.xp, self.nrows, self.me_rank, self.gain, self.offline = cs, xp, rows, me_rank, gain, offline
        self.subs, self.boards = [], []
        self.extra = {}

    def storage(self):
        s = {'kgeuLBUrl': FAKE}
        if self.cs:
            s['kgeuLB'] = json.dumps({'cs': self.cs, 'key': 'k' * 48, 'xp': self.xp, 'creator': False, 'renamed': 0, 'renameAt': 0, 'created': 1})
        return s

    def board(self, b, p):
        rnd = random.Random(b + p)
        n = self.nrows if p == 'all' else max(0, self.nrows // (3 if p == 'week' else 6))
        rows = []
        lower = b in ('arc:drop', 'mission:dash') or b.startswith('df:clear')
        for i in range(n):
            cs = self.cs if i + 1 == self.me_rank else NAMES[i % len(NAMES)] + ('' if i < len(NAMES) else str(i))
            sc = (12 + i * 7.5) if lower else max(1, 1400 - i * 37 - rnd.randint(0, 9))
            rows.append({'r': i + 1, 'cs': cs, 'score': sc, 'secs': 90 + i, 'ac': ACS[i % len(ACS)], 'mode': 'easy' if i % 3 == 1 else 'hard',
                         'xp': 16000 - i * 600, 'rank': RANKS[max(0, 5 - i // 5)], 'creator': i == 2, 'when': 1})
        me = None
        if self.cs and self.me_rank <= n:
            me = {'r': self.me_rank, 'cs': self.cs, 'score': rows[self.me_rank - 1]['score'], 'mode': 'hard', 'xp': self.xp, 'rank': 'Flight Lead', 'creator': False}
        return {'rows': rows, 'me': me, 'total': n * 4 + 3, 'ghost': None}

    async def install(self, ctx):
        async def h(route):
            if self.offline:
                await route.abort(); return
            req = route.request
            url = req.url[len(FAKE):]
            path = url.split('?')[0]
            body = {}
            if req.method == 'POST':
                try: body = json.loads(req.post_data or '{}')
                except Exception: body = {}
            if path == '/health': out = {'ok': True}
            elif path == '/me': out = {'cs': self.cs, 'xp': self.xp, 'creator': False, 'renamed': 0, 'renameAt': 0}
            elif path == '/fame': out = {'day': 0, 'daily': None, 'top': []}
            elif path == '/pool': out = {'tokens': ['pooltok%d' % i for i in range(int(body.get('n', 1)))]}
            elif path == '/token': out = {'token': 'tok-' + body.get('board', '')}
            elif path == '/board':
                q = dict(x.split('=', 1) for x in url.split('?', 1)[1].split('&'))
                from urllib.parse import unquote
                b = unquote(q.get('b', 'daily')); self.boards.append((b, q.get('p')))
                out = self.board(b, q.get('p', 'today'))
            elif path == '/submit' and self.extra.get('reject'):
                self.subs.append(body)
                await route.fulfill(status=400, content_type='application/json', body=json.dumps({'ok': False, 'reason': self.extra['reject']}), headers={'Access-Control-Allow-Origin': '*'}); return
            elif path == '/submit':
                self.subs.append(body)
                g = self.extra.get('gain', self.gain)
                ach = self.extra.get('ach', [])
                ax = sum(a['xp'] for a in ach)
                self.xp += g + ax
                out = {'ok': True, 'id': len(self.subs), 'board': body.get('board'), 'mode': body.get('mode'), 'score': body.get('score'), 'pb': True,
                       'best': body.get('score'), 'rank': 7, 'total': 40, 'top10': True, 'today': {'rank': 1, 'total': 3}, 'xp': self.xp, 'gain': g,
                       'rankName': 'Flight Lead'}
                if str(body.get('board', '')).startswith('df:') or body.get('df') is not None:
                    out['ach'] = ach; out['achXp'] = ax
                    out['df'] = {'kills': {'score': 3, 'rank': 4, 'total': 9, 'pb': False, 'best': 5, 'top10': True}, 'clear': None, 'guns': None}
            else: out = {}
            await route.fulfill(status=200, content_type='application/json', body=json.dumps(out), headers={'Access-Control-Allow-Origin': '*'})
        await ctx.route(FAKE + '/**', h)
