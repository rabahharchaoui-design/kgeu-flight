# Shared region table for the build time world tools.
#
# Imported by tools/build_map_data.py (the 2D map, assets/map/<id>.bin) and
# tools/build_region.py (the 3D world data, assets/world/<id>.json). Neither the
# table nor those tools run in the live game: the game only loads their output.
#
# World frame for the new regions: metres, +X east, -Z north, origin at the
# airport reference point (ARP) from OurAirports airports.csv:
#   x = (lon - lon0) * 111320 * cos(lat0),  z = -(lat - lat0) * 110950
# (the same flat projection as the game's geoW).
#
# Phoenix keeps its historical frame (origin offset to the KGEU runway middle,
# extent X0..X1 / Z0..Z1) so assets/map/phx.bin stays byte identical.

PHX = {
    'id': 'phx', 'icao': 'KGEU', 'name': 'Glendale', 'city': 'Phoenix', 'country': 'USA',
    'origin': (33.52683, -112.29517),
    # map extent in world metres: the White Tanks to past Camelback
    'extent': (-34000, 38000, -28000, 30000),
}

REGIONS = {
    'rjtt': {
        'id': 'rjtt', 'icao': 'RJTT', 'name': 'Tokyo Haneda', 'city': 'Tokyo', 'country': 'JAPAN',
        'origin': (35.549678, 139.786958),    # OurAirports ARP
        'half': 32000, 'cell': 200, 'main': '34R',
        'tiles': 6,   # Overpass street tiles per side (Tokyo is dense)
        'landmarks': [
            {'id': 'tokyo_tower', 'name': 'Tokyo Tower', 'lat': 35.6586, 'lon': 139.7454, 'kind': 'tower', 'h': 333},
            {'id': 'skytree', 'name': 'Tokyo Skytree', 'lat': 35.7101, 'lon': 139.8107, 'kind': 'tower', 'h': 634},
            {'id': 'rainbow_n', 'name': 'Rainbow Bridge (Shibaura pylon)', 'lat': 35.6375, 'lon': 139.7602, 'kind': 'bridge_pylon', 'h': 126},
            {'id': 'rainbow_s', 'name': 'Rainbow Bridge (Daiba pylon)', 'lat': 35.6356, 'lon': 139.7661, 'kind': 'bridge_pylon', 'h': 126},
            {'id': 'shinjuku', 'name': 'Shinjuku skyline', 'lat': 35.6905, 'lon': 139.6930, 'kind': 'skyline', 'h': 243},
            {'id': 'fuji', 'name': 'Mount Fuji', 'lat': 35.3606, 'lon': 138.7274, 'kind': 'mountain', 'h': 3776},
            {'id': 'hnd_t1', 'name': 'Haneda Terminal 1', 'lat': 35.5490, 'lon': 139.7845, 'kind': 'terminal', 'h': 30},
            {'id': 'hnd_t2', 'name': 'Haneda Terminal 2', 'lat': 35.5507, 'lon': 139.7887, 'kind': 'terminal', 'h': 30},
            {'id': 'hnd_t3', 'name': 'Haneda Terminal 3', 'lat': 35.5446, 'lon': 139.7686, 'kind': 'terminal', 'h': 30},
        ],
    },
    'lfpg': {
        'id': 'lfpg', 'icao': 'LFPG', 'name': 'Paris Charles de Gaulle', 'city': 'Paris', 'country': 'FRANCE',
        'origin': (49.00896, 2.554117),
        'half': 32000, 'cell': 200, 'main': '26L',
        'landmarks': [
            {'id': 'eiffel', 'name': 'Eiffel Tower', 'lat': 48.8584, 'lon': 2.2945, 'kind': 'tower', 'h': 330},
            {'id': 'arc', 'name': 'Arc de Triomphe', 'lat': 48.8738, 'lon': 2.2950, 'kind': 'monument', 'h': 50},
            {'id': 'sacre_coeur', 'name': 'Sacré-Cœur', 'lat': 48.8867, 'lon': 2.3431, 'kind': 'church', 'h': 83},
            {'id': 'grande_arche', 'name': 'La Défense (Grande Arche)', 'lat': 48.8926, 'lon': 2.2360, 'kind': 'skyline', 'h': 110},
            {'id': 'notre_dame', 'name': 'Notre-Dame', 'lat': 48.8530, 'lon': 2.3499, 'kind': 'church', 'h': 96},
        ],
    },
    'sbrj': {
        'id': 'sbrj', 'icao': 'SBRJ', 'name': 'Rio Santos Dumont', 'city': 'Rio de Janeiro', 'country': 'BRAZIL',
        'origin': (-22.910397, -43.16282),
        'half': 24000, 'cell': 120,
        'main': '20L',   # 02R/20L is the longer (4341 ft vs 4134 ft in OurAirports); build_region checks
        'landmarks': [
            {'id': 'sugarloaf', 'name': 'Sugarloaf Mountain', 'lat': -22.9495, 'lon': -43.1562, 'kind': 'mountain', 'h': 396},
            {'id': 'urca', 'name': 'Morro da Urca', 'lat': -22.9508, 'lon': -43.1640, 'kind': 'mountain', 'h': 220},
            {'id': 'cable_base', 'name': 'Cable car base (Praia Vermelha)', 'lat': -22.9557, 'lon': -43.1669, 'kind': 'cable_car', 'h': 0},
            {'id': 'cristo', 'name': 'Christ the Redeemer', 'lat': -22.9519, 'lon': -43.2105, 'kind': 'statue', 'h': 38},
            {'id': 'copacabana', 'name': 'Copacabana beach', 'lat': -22.9711, 'lon': -43.1822, 'kind': 'beach', 'h': 0},
            {'id': 'niteroi_bridge', 'name': 'Rio-Niterói Bridge', 'lat': -22.8686, 'lon': -43.1830, 'kind': 'bridge', 'h': 72},
        ],
    },
}
for _r in REGIONS.values():
    for _l in _r['landmarks']:
        _l['src'] = 'manual'

def get(rid):
    return PHX if rid in (None, 'phx') else REGIONS[rid]
