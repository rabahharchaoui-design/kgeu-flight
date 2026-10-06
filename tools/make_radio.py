#!/usr/bin/env python3
"""Pre-record every ATC line with the macOS `say` command.

The cockpit voice (TCAS, c_* clips) is Daniel, Enhanced if installed, and is
played dry in the game.

Two Enhanced voices: Samantha for the controllers, Evan for the pilots. Female
tower against male pilot is the pairing that stays readable through a band
limited radio filter, where two male voices blur together.

Each clip is trimmed of leading and trailing silence so lines can be stitched
without gaps, then written as mono AAC at 64 kbps.

    python3 tools/make_radio.py            # write radio/*.m4a and radio/clips.json
    python3 tools/make_radio.py --check    # report what is missing, write nothing

Red Flag Dogfight (d_*): the cockpit warning voice d_c_* (Samantha, dry), the wingman Viper 2 d_w_* and the
AWACS controller Sentry d_a_* (DF_VOICES: the first installed voice of each list, both radio filtered).
"""
import json, os, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'radio')

TOWER_VOICE = 'Samantha (Enhanced)'
PILOT_VOICE = 'Evan (Enhanced)'
TOWER_RATE, PILOT_RATE = 200, 190          # controllers talk faster than pilots
# the cockpit voice (TCAS): calm male, played dry in the game, not through the radio
COCKPIT_VOICES = ('Daniel (Enhanced)', 'Daniel')
COCKPIT_RATE = 175
# Red Flag Dogfight (5.4): three more voices, the first one installed of each list. The cockpit warning voice
# (d_c_*) is calm and female and played dry, like a "Bitching Betty"; the wingman Viper 2 (d_w_*) and the AWACS
# controller Sentry (d_a_*) go through the radio filter, so they are a male and a female voice that are neither
# the tower (Samantha) nor the pilot (Evan).
DF_VOICES = {
    'dc': (('Samantha (Enhanced)', 'Samantha'), 180),
    'dw': (('Nathan (Enhanced)', 'Tom (Enhanced)', 'Tom', 'Alex', 'Reed (English (US))', 'Daniel'), 205),
    'da': (('Noelle (Enhanced)', 'Ava (Enhanced)', 'Allison (Enhanced)', 'Karen', 'Moira (English (Ireland))', 'Moira'), 195),
}

# ---- said by both sides: the pilot calls the facility, the tower calls the aircraft ----
BOTH = {
    'glendale_tower':   'Glendale Tower',
    'glendale_ground':  'Glendale Ground',
    'luke_tower':       'Luke Tower',
    'luke_ground':      'Luke Ground',
    'phoenix_approach': 'Phoenix Approach',
    'phoenix_tower':    'Phoenix Tower',
    'phoenix_ground':   'Phoenix Ground',
    # world regions (4.6b): the tower and ground of each region's airport
    'tokyo_tower':         'Tokyo Tower',
    'tokyo_ground':        'Haneda Ground',
    'degaulle_tower':      'de Gaulle Tower',
    'degaulle_ground':     'de Gaulle Ground',
    'santosdumont_tower':  'Santos Dumont Tower',
    'santosdumont_ground': 'Santos Dumont Ground',
    'cs_skyhawk':       'Skyhawk eight four zero one lima',
    'cs_skyhawk_s':     'Skyhawk zero one lima',
    'cs_viper':         'Viper one',
    'cs_reaper':        'Reaper eight four zero one lima',
    'cs_reaper_s':      'Reaper zero one lima',
    'cs_herky':         'Herky seven one',
    'cs_skyguardian':   'Sky Guardian one niner zero tango charlie',
    'cs_skyguardian_s': 'Sky Guardian zero tango charlie',
    'cs_pipistrel':     'Pipistrel five zero two alpha tango',
    'cs_pipistrel_s':   'Pipistrel two alpha tango',
    # planes2: the Archer
    'cs_archer':        'Archer eight one two eight papa',
    'cs_archer_s':      'Archer two eight papa',
    'cs_hawg':          'Hawg one',
    'cs_pocket737':     'Pocket seven three seven',
    'cs_pocket320':     'Pocket three two zero',
}

# ---- controller only ----
TOWER = {
    'rwy_1':   'runway one',              'rwy_19':  'runway one niner',
    'rwy_03l': 'runway zero three left',  'rwy_03r': 'runway zero three right',
    'rwy_21l': 'runway two one left',     'rwy_21r': 'runway two one right',
    'rwy_07l': 'runway zero seven left',  'rwy_25r': 'runway two five right',
    # world regions (4.6b): every runway end at Haneda, de Gaulle and Santos Dumont
    'rwy_34r': 'runway three four right', 'rwy_34l': 'runway three four left',
    'rwy_16r': 'runway one six right',    'rwy_16l': 'runway one six left',
    'rwy_04':  'runway zero four',        'rwy_22':  'runway two two',
    'rwy_05':  'runway zero five',        'rwy_23':  'runway two three',
    'rwy_26l': 'runway two six left',     'rwy_26r': 'runway two six right',
    'rwy_27l': 'runway two seven left',   'rwy_27r': 'runway two seven right',
    'rwy_08l': 'runway zero eight left',  'rwy_08r': 'runway zero eight right',
    'rwy_09l': 'runway zero niner left',  'rwy_09r': 'runway zero niner right',
    'rwy_20l': 'runway two zero left',    'rwy_20r': 'runway two zero right',
    'rwy_02l': 'runway zero two left',    'rwy_02r': 'runway zero two right',

    'cleared_to':     'cleared for takeoff.',
    'cleared_land':   'cleared to land.',
    'cleared_option': 'cleared for the option.',
    'cleared_tg':     'cleared touch and go.',
    'cleared_low':    'cleared low approach.',
    'taxi_alpha':     'taxi to the active via alpha.',
    'hold_short':     'hold short of the runway.',
    'lineup_wait':    'line up and wait.',
    'closed_traffic': 'make right closed traffic.',
    'wheels_down':    'check wheels down.',
    'nice_landing':   'nice landing. Turn left next taxiway, contact ground.',
    'go_around':      'go around, I say again, go around.',
    'report_initial': 'report initial.',
    'crash':          'Crash, crash, crash. Emergency vehicles are rolling.',
    'luke_security':  'you just landed at Luke Air Force Base. Hold position, security is on the way.',
    'haboob_luke':     'Attention all aircraft, Luke Tower, visibility one half mile in blowing dust, wind gusting five zero knots, use caution.',
    'haboob_glendale': 'Attention all aircraft, Glendale Tower, visibility one half mile in blowing dust, wind gusting five zero knots, use caution.',
    'haboob_phoenix':  'Attention all aircraft, Phoenix Tower, visibility one half mile in blowing dust, wind gusting five zero knots, use caution.',

    'wind':   'wind',
    'at':     'at',
    'traffic': 'traffic,',
    'oclock': "o'clock,",
    'mile':   'mile,',
    'miles':  'miles,',
    'same_alt': 'same altitude.',
    'above':  'above.',
    'below':  'below.',
    'hundred_feet':  'hundred feet',
    'thousand_feet': 'thousand feet',

    # traffic types, so a traffic call can name what it is
    'tfc_cessna': 'a Cessna.',
    'tfc_vipers': 'a flight of two F-sixteens.',
    'tfc_c17':    'a C-seventeen.',
    'tfc_reaper': 'an M Q nine.',
    'tfc_banner': 'a banner tow plane.',
    'tfc_airliner': 'an airliner.',
    'tfc_f16':      'an F-sixteen.',
    'tfc_heli':     'a helicopter.',

    'gila_range':  'Gila Range Control,',
    'cleared_hot': 'you are cleared hot. Range is clear, four targets.',
    'range_cold':  'range is cold.',
    'of_four':     'of four.',
    'good_hit':    'good hit, good hit, target destroyed.',
    'miss':        'miss,',
    'meters':      'meters.',
    'long':        'long.',
    'reset_again': 'reset and try again.',
    'dz_smoke':    'drop zone is marked. Head for the red smoke.',

    'n_0': 'zero',  'n_1': 'one',   'n_2': 'two',    'n_3': 'three',
    'n_4': 'four',  'n_5': 'five',  'n_6': 'six',    'n_7': 'seven',
    'n_8': 'eight', 'n_9': 'niner', 'n_10': 'one zero',
    'c_10': 'ten',  'c_11': 'eleven', 'c_12': 'twelve',
}

# ---- pilot only ----
PILOT = {
    'rb_cleared_to':   'Cleared for takeoff,',
    'rb_cleared_land': 'Cleared to land,',
    'rb_wilco':        'Wilco,',
    'rb_roger':        'Roger,',
    'rb_traffic':      'Looking for the traffic,',
    'load_away':       'load away, one bundle.',
    'rifle':           'Rifle,',
    # C-130 jump calls on the intercom
    'j_1min':          'One minute.',
    'j_10s':           'Ten seconds.',
    'j_green':         'Green light, green light.',
}

# ---- background chatter, recorded whole because these lines never change ----
CHATTER_TOWER = {
    'ch_t1': 'Viper two one flight, runway three left, break at the numbers, wind zero five zero at six.',
    'ch_t2': 'Reach four eight two, Phoenix altimeter two niner eight three.',
    'ch_t3': 'Cessna three one golf, runway one, cleared touch and go.',
    'ch_t4': 'Hunter one one, block six thousand to seven thousand approved, report exiting.',
    'ch_t5': 'Viper two one, runway three left, cleared low approach.',
    'ch_t6': 'Bolt one one, report initial, runway three left.',
    'ch_t7': 'Cessna seven three eight golf echo, runway one, taxi via alpha.',
    'ch_t8': 'Reach four eight two, direct Luke approved, maintain eight thousand.',
    'ch_t9': 'Viper two one flight, check wheels down. Runway three left, cleared to land.',
    # world regions (4.6b): generic callsigns only, never a real airline
    'ch_jp_t1': 'Skyline two two, Tokyo Tower, runway three four left, continue approach.',
    'ch_jp_t2': 'Pacific seven, Haneda Ground, runway zero five, taxi via charlie.',
    'ch_jp_t3': 'Orient four one, runway zero five, cleared for takeoff.',
    'ch_fr_t1': 'Atlantic three one zero, de Gaulle Tower, runway two seven right, cleared to land.',
    'ch_fr_t2': 'Riviera five two, de Gaulle Ground, push and start approved, facing east.',
    'ch_fr_t3': 'Lumiere nine eight, runway two six left, line up and wait.',
    'ch_br_t1': 'Carioca one five, Santos Dumont Tower, runway two zero left, cleared to land.',
    'ch_br_t2': 'Sugarloaf eight, Santos Dumont Ground, runway two zero right, taxi via alpha.',
    'ch_br_t3': 'Guanabara three, runway two zero right, cleared for takeoff, right turn out over the bay.',
}
CHATTER_PILOT = {
    'ch_p1': 'Luke tower, viper two one, flight of two, initial, runway three left.',
    'ch_p2': 'Phoenix approach, reach four eight two, level eight thousand.',
    'ch_p3': 'Glendale tower, Cessna five two three one golf, right downwind runway one, touch and go.',
    'ch_p4': 'Viper two one flight, push button five.',
    'ch_p5': 'Two.',
    'ch_p6': 'Phoenix approach, hunter one one, M Q nine, request block six thousand to seven thousand.',
    'ch_p7': 'Viper two one, low approach, gear down.',
    'ch_p8': 'Luke tower, bolt one one, five miles south, with kilo.',
    'ch_p9': 'Runway one via alpha, three eight golf echo.',
    'ch_p10': 'Viper two two, bingo.',
    'ch_p11': 'Copy. Viper two one flight, knock it off. Rejoin, R T B.',
    'ch_p12': 'Cleared to land, viper two one.',
    # world regions (4.6b)
    'ch_jp_p1': 'Tokyo Tower, Skyline two two, ten miles south, runway three four left.',
    'ch_jp_p2': 'Haneda Ground, Pacific seven, at the gate, request taxi.',
    'ch_jp_p3': 'Tokyo Tower, Orient four one, ready runway zero five.',
    'ch_fr_p1': 'de Gaulle Tower, Atlantic three one zero, established runway two seven right.',
    'ch_fr_p2': 'de Gaulle Ground, Riviera five two, request push and start.',
    'ch_fr_p3': 'de Gaulle Tower, Lumiere nine eight, ready runway two six left.',
    'ch_br_p1': 'Santos Dumont Tower, Carioca one five, over the bridge, runway two zero left.',
    'ch_br_p2': 'Santos Dumont Ground, Sugarloaf eight, request taxi.',
    'ch_br_p3': 'Santos Dumont Tower, Guanabara three, ready runway two zero right.',
}

# ---- cockpit voice, c_*: TCAS callouts (Hard) and plain English versions (Easy) ----
COCKPIT = {
    'tcas_traffic':     'Traffic, traffic.',
    'tcas_climb':       'Climb, climb.',
    'tcas_descend':     'Descend, descend.',
    'tcas_climb_now':   'Increase climb, increase climb.',
    'tcas_descend_now': 'Increase descent, increase descent.',
    'tcas_clear':       'Clear of conflict.',
    'tcas_e_traffic':   'Plane nearby!',
    'tcas_e_climb':     'Plane nearby! Climb now!',
    'tcas_e_descend':   'Plane nearby! Descend now!',
    'tcas_e_clear':     'All clear.',
}

# ---- Red Flag Dogfight (5.4): cockpit warnings d_c_*, the wingman d_w_*, the AWACS controller d_a_* ----
DF_COCKPIT = {
    'launch':   'Missile launch.',
    'pullup':   'Pull up.',
    'bingo':    'Bingo.',
    'warning':  'Warning.',
    'flares':   'Flares.',
    'altitude': 'Altitude.',
}
DF_NUMW = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
DF_WING = dict({
    'fox2':       'Fox two!',
    'guns':       'Guns, guns, guns!',
    'tally1':     'Tally one!',
    'tally2':     'Tally two!',
    'goodkill':   'Good kill!',
    'break_r':    'Break right!',
    'break_l':    'Break left!',
    'winchester': 'Winchester.',
    'niceflares': 'Nice flares!',
    'six':        "He's on your six!",
    'kio':        'Knock it off, knock it off.',
}, **{f'splash_{n}': f'Splash {DF_NUMW[n]}!' for n in range(1, 11)})
# a picture call is stitched: sentry, count, bearing, miles number, miles, angels, angels number
DF_AWACS = dict({
    'bandit':   'Bandit, bandit.',
    'sentry':   'Sentry,',
    'g1':       'single bandit,',
    'g2':       'two bandits,',
    'g3':       'three bandits,',
    'g4':       'four bandits,',
    'miles':    'miles,',
    'angels':   'angels',
    'clean':    'Picture clean.',
    'fightson': "Fight's on.",
    'deck':     'Hard deck, hard deck.',
    'hot':      'Range is hot.',
    'rtr':      'Return to the range.',
    's30':      'Thirty seconds.',
    'kio':      'Knock it off. Good work, Viper.',
}, **{'b_' + k: w + ',' for k, w in (('n', 'north'), ('ne', 'northeast'), ('e', 'east'), ('se', 'southeast'),
                                       ('s', 'south'), ('sw', 'southwest'), ('w', 'west'), ('nw', 'northwest'))},
   **{f'num_{n}': w for n, w in ((5, 'five'), (10, 'ten'), (11, 'eleven'), (12, 'twelve'), (13, 'thirteen'), (14, 'fourteen'),
                                 (15, 'fifteen'), (16, 'sixteen'), (17, 'seventeen'), (18, 'eighteen'), (19, 'nineteen'), (20, 'twenty'))})


def installed(names, voices):
    for v in names:
        if any(line.startswith(v + ' ') or line.startswith(v + '\t') for line in voices.splitlines()):
            return v
    return None


_VOICES = None
def voice_list():
    global _VOICES
    if _VOICES is None:
        _VOICES = subprocess.run(['say', '-v', '?'], capture_output=True, text=True).stdout
    return _VOICES


def cockpit_voice(voices=None):
    if voices is None:
        voices = subprocess.run(['say', '-v', '?'], capture_output=True, text=True).stdout
    for v in COCKPIT_VOICES:
        if any(line.startswith(v + ' ') or line.startswith(v + '\t') for line in voices.splitlines()):
            return v
    return None


def manifest():
    """id -> (voice tag, text). Tower clips are t_*, pilot clips p_*, cockpit c_*."""
    m = {}
    for k, v in BOTH.items():
        m['t_' + k] = ('t', v)
        m['p_' + k] = ('p', v)
    for k, v in TOWER.items():          m['t_' + k] = ('t', v)
    for k, v in CHATTER_TOWER.items():  m['t_' + k] = ('t', v)
    for k, v in PILOT.items():          m['p_' + k] = ('p', v)
    for k, v in CHATTER_PILOT.items():  m['p_' + k] = ('p', v)
    for k, v in COCKPIT.items():        m['c_' + k] = ('c', v)
    for k, v in DF_COCKPIT.items():     m['d_c_' + k] = ('dc', v)
    for k, v in DF_WING.items():        m['d_w_' + k] = ('dw', v)
    for k, v in DF_AWACS.items():       m['d_a_' + k] = ('da', v)
    return m


TRIM = ('silenceremove=start_periods=1:start_silence=0.02:start_threshold=-50dB:detection=peak,'
        'areverse,'
        'silenceremove=start_periods=1:start_silence=0.02:start_threshold=-50dB:detection=peak,'
        'areverse')


def render(cid, voice, text, tmp):
    aiff = os.path.join(tmp, cid + '.aiff')
    m4a = os.path.join(OUT, cid + '.m4a')
    if voice == 'c':
        v, rate = cockpit_voice(), COCKPIT_RATE
    elif voice in DF_VOICES:
        v, rate = installed(DF_VOICES[voice][0], voice_list()), DF_VOICES[voice][1]
    else:
        v, rate = (TOWER_VOICE, TOWER_RATE) if voice == 't' else (PILOT_VOICE, PILOT_RATE)
    subprocess.run(['say', '-v', v, '-r', str(rate), '-o', aiff, text], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', aiff, '-af', TRIM,
                    '-ac', '1', '-c:a', 'aac', '-b:a', '64k', m4a], check=True)
    os.remove(aiff)
    return os.path.getsize(m4a)


def main():
    m = manifest()
    check = '--check' in sys.argv
    if check:
        missing = [c for c in m if not os.path.exists(os.path.join(OUT, c + '.m4a'))]
        print(f'{len(m)} clips in the manifest, {len(missing)} missing')
        for c in missing[:20]:
            print('  missing', c)
        return 1 if missing else 0

    for tool in ('say', 'ffmpeg'):
        if not shutil.which(tool):
            print(f'{tool} not found', file=sys.stderr)
            return 2
    voices = subprocess.run(['say', '-v', '?'], capture_output=True, text=True).stdout
    for v in (TOWER_VOICE, PILOT_VOICE):
        if v not in voices:
            print(f'voice not installed: {v}', file=sys.stderr)
            return 2
    if not cockpit_voice(voices):
        print(f'voice not installed: {COCKPIT_VOICES[0]} or {COCKPIT_VOICES[1]}', file=sys.stderr)
        return 2

    for tag, (names, _) in DF_VOICES.items():
        if not installed(names, voices):
            print(f'no dogfight voice installed for {tag}: tried {", ".join(names)}', file=sys.stderr)
            return 2

    os.makedirs(OUT, exist_ok=True)
    tmp = os.path.join(OUT, '.tmp')
    os.makedirs(tmp, exist_ok=True)
    total = 0
    force = '--force' in sys.argv
    made = 0
    for i, (cid, (voice, text)) in enumerate(sorted(m.items()), 1):
        path = os.path.join(OUT, cid + '.m4a')
        if force or not os.path.exists(path):
            render(cid, voice, text, tmp)
            made += 1
        total += os.path.getsize(path)
        if i % 20 == 0:
            print(f'  {i}/{len(m)}')
    print(f'{made} clip(s) rendered')
    os.rmdir(tmp)

    json.dump(sorted(m.keys()), open(os.path.join(OUT, 'clips.json'), 'w'), indent=0)
    print(f'{len(m)} clips, {total/1024:.0f} KB total, average {total/len(m)/1024:.1f} KB')
    print(f'tower voice {TOWER_VOICE}, pilot voice {PILOT_VOICE}, cockpit voice {cockpit_voice(voices)}')
    df = [c for c in m if c.startswith('d_')]
    dsz = sum(os.path.getsize(os.path.join(OUT, c + '.m4a')) for c in df)
    print(f'dogfight: {len(df)} clips, {dsz/1024:.0f} KB; cockpit {installed(DF_VOICES["dc"][0], voices)}, '
          f'wingman {installed(DF_VOICES["dw"][0], voices)}, AWACS {installed(DF_VOICES["da"][0], voices)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
