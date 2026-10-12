# Build the real elevation grid for the Arizona world (the valley around KGEU and Luke).
#
#   .venv/bin/python tools/build_az_terrain.py [--refetch]
#
# Writes assets/world/az_dem.bin. Build time only: the live game never calls the tile
# server, it loads this file (precached by the service worker, tools/gen_sw.py).
#
# Source: Mapzen Terrarium tiles on AWS (SRTM, NASA; Copernicus DEM), zoom 11 (about
# 64 m a pixel here), height = R*256 + G + B/256 - 32768 m. Same URL, cache directory
# (tools/.osm-cache/terrarium, gitignored) and download helper as tools/build_region.py.
#
# Extent: 48 km west to 48 km east and 40 km north to 48 km south of the KGEU ARP
# (33.52683 N, 112.29517 W): the White Tanks, the Estrellas, South Mountain, Camelback, the
# Phoenix Mountains and the McDowells' west edge, and the valley floor. Each 120 m cell is
# the mean of the tile pixels whose centres fall in it (like the regions' grids).
#
# World frame: the Arizona frame of tools/build_map_data.py (bmd.world): metres, +X east,
# +Z south, origin at the start of KGEU runway 1 (the ARP is at ARP_X, ARP_Z).
#
# File layout (little endian):
#   header, 20 bytes: 'AZD1', W u16, H u16, x0 i32, z0 i32 (world metres of the north west
#     corner of cell 0), cell u16 (m), base i16 (decimetres MSL: 3264, KGEU's 1,071 ft)
#   W*H int16 heights, decimetres above base (signed: the Gila bottoms are under KGEU),
#     row major, row 0 the northern edge
#   the valley floor: FW u16, FH u16, fcell u16 (m), fx0 i32, fz0 i32, then FW*FH int16
#     decimetres above base. A smooth surface through the flat cells of the valley (slope
#     under 2.5 percent), interpolated under the mountains. The game takes the relief over
#     it, so the city, the freeways and the fields it builds at y=0 stay on the ground and
#     the ranges rise from the valley at their real heights and shapes.
import io, math, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_map_data as bmd
from build_region import download, tile_xy

OUT = os.path.join(bmd.ROOT, 'assets', 'world', 'az_dem.bin')
KGEU = bmd.KGEU
CELL = 120
WEST, EAST, NORTH, SOUTH = 48000, 48000, 40000, 48000
BASE_DM = 3264            # 326.4 m, 1,071 ft
Z = 11
FCELL = 1000              # the floor grid

def main():
    refetch = '--refetch' in sys.argv
    from PIL import Image
    ax, az = bmd.ARP_X, bmd.ARP_Z
    x0, z0 = round(ax - WEST), round(az - NORTH)
    W, H = (WEST + EAST) // CELL, (NORTH + SOUTH) // CELL
    lat0, lon0 = KGEU
    lat_n = lat0 + (az - z0) / bmd.MPD_LAT; lat_s = lat0 + (az - (z0 + H * CELL)) / bmd.MPD_LAT
    lon_w = lon0 + (x0 - ax) / bmd.MPD_LON; lon_e = lon0 + (x0 + W * CELL - ax) / bmd.MPD_LON
    n = 2 ** Z
    tx0, ty0 = tile_xy(lat_n, lon_w, Z); tx1, ty1 = tile_xy(lat_s, lon_e, Z)
    s = [0.0] * (W * H); c = [0] * (W * H); count = 0
    for ty in range(int(ty0), int(ty1) + 1):
        rows = []
        for py in range(256):
            yy = (ty + (py + 0.5) / 256) / n
            lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy))))
            wx, wz = bmd.world(lat, lon0)
            rows.append(math.floor((wz - z0) / CELL))
        for tx in range(int(tx0), int(tx1) + 1):
            raw = download(f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{tx}/{ty}.png',
                           os.path.join(bmd.CACHE, 'terrarium', str(Z), str(tx), f'{ty}.png'), refetch)
            count += 1
            px = Image.open(io.BytesIO(raw)).convert('RGB').tobytes()
            cols = []
            for qx in range(256):
                lon = (tx + (qx + 0.5) / 256) / n * 360 - 180
                wx, wz = bmd.world(lat0, lon)
                cols.append(math.floor((wx - x0) / CELL))
            for py in range(256):
                j = rows[py]
                if not 0 <= j < H:
                    continue
                base = py * 768; rowo = j * W
                for qx in range(256):
                    i = cols[qx]
                    if 0 <= i < W:
                        o = base + qx * 3
                        s[rowo + i] += px[o] * 256 + px[o + 1] + px[o + 2] / 256 - 32768
                        c[rowo + i] += 1
    hole = sum(1 for v in c if not v)
    if hole:
        sys.exit(f'{hole} cells without a pixel')
    h = [s[k] / c[k] for k in range(W * H)]
    print(f'{count} z{Z} tiles, grid {W} x {H} at {CELL} m, origin {x0} {z0}')

    # ---- the valley floor ----
    # flat cells: slope under 2.5 percent over the neighbouring cells
    flat = bytearray(W * H)
    for j in range(1, H - 1):
        for i in range(1, W - 1):
            k = j * W + i
            gx = (h[k + 1] - h[k - 1]) / (2 * CELL); gz = (h[k + W] - h[k - W]) / (2 * CELL)
            if gx * gx + gz * gz < 0.025 ** 2:
                flat[k] = 1
    FW, FH = math.ceil(W * CELL / FCELL), math.ceil(H * CELL / FCELL)
    floor = None
    for it in range(4):
        # per floor cell: the mean of its flat cells (not more than 15 m over the last floor)
        sw = [0.0] * (FW * FH); sh = [0.0] * (FW * FH)
        for j in range(H):
            fj = min(FH - 1, (j * CELL + CELL // 2) // FCELL)
            for i in range(W):
                k = j * W + i
                if not flat[k]:
                    continue
                fi = min(FW - 1, (i * CELL + CELL // 2) // FCELL)
                if floor is not None and h[k] > fsample(floor, FW, FH, (i + 0.5) * CELL, (j + 0.5) * CELL) + 15:
                    continue
                sw[fj * FW + fi] += 1; sh[fj * FW + fi] += h[k]
        # normalised convolution, a Gaussian of 2.5 km, then 6 km where too few flat cells
        a = gauss(sh, FW, FH, 2.5); b = gauss(sw, FW, FH, 2.5)
        a2 = gauss(sh, FW, FH, 6.0); b2 = gauss(sw, FW, FH, 6.0)
        floor = []
        for k in range(FW * FH):
            t = min(1.0, b[k] / 20.0)
            f2 = a2[k] / b2[k] if b2[k] > 1e-6 else 0.0
            f1 = a[k] / b[k] if b[k] > 1e-6 else f2
            floor.append(f1 * t + f2 * (1 - t))
    # ---- write ----
    dm = lambda v: max(-32768, min(32767, round(v * 10) - BASE_DM))
    out = bytearray(b'AZD1') + struct.pack('<HHiiHh', W, H, x0, z0, CELL, BASE_DM)
    out += struct.pack(f'<{W*H}h', *[dm(v) for v in h])
    out += struct.pack('<HHHii', FW, FH, FCELL, x0, z0) + struct.pack(f'<{FW*FH}h', *[dm(v) for v in floor])
    open(OUT, 'wb').write(out)
    print(f'wrote {OUT}: {len(out)/1024:.0f} KB, floor grid {FW} x {FH} at {FCELL} m')

    # ---- sanity ----
    base = BASE_DM / 10
    def at(lat, lon):
        wx, wz = bmd.world(lat, lon)
        gx = min(W - 1.001, max(0, (wx - x0) / CELL - 0.5)); gz = min(H - 1.001, max(0, (wz - z0) / CELL - 0.5))
        i, j = int(gx), int(gz); fx, fz = gx - i, gz - j; k = j * W + i
        v = (h[k] * (1 - fx) + h[k + 1] * fx) * (1 - fz) + (h[k + W] * (1 - fx) + h[k + W + 1] * fx) * fz
        f = fsample(floor, FW, FH, wx - x0, wz - z0)
        return v, f
    def peak(lat, lon, r=2500):
        wx, wz = bmd.world(lat, lon); best = (-1e9, 0, 0)
        for j in range(max(0, int((wz - r - z0) / CELL)), min(H, int((wz + r - z0) / CELL) + 1)):
            for i in range(max(0, int((wx - r - x0) / CELL)), min(W, int((wx + r - x0) / CELL) + 1)):
                if h[j * W + i] > best[0]:
                    best = (h[j * W + i], x0 + (i + 0.5) * CELL, z0 + (j + 0.5) * CELL)
        return best
    print(f'min {min(h):.1f} m, max {max(h):.1f} m MSL; base {base} m')
    for name, lat, lon in [('KGEU', 33.52683, -112.29517), ('Luke', 33.5350, -112.3830), ('Sky Harbor', 33.4343, -112.0116)]:
        v, f = at(lat, lon)
        print(f'  {name:12s} {v:7.1f} m MSL, {v-base:+7.1f} m on KGEU, floor {f-base:+7.1f}, relief {v-f:+6.1f}')
    for name, lat, lon in [('White Tanks', 33.5880, -112.5730), ('Camelback', 33.5151, -111.9618),
                           ('South Mtn', 33.3460, -112.0610), ('Estrellas', 33.2740, -112.2400),
                           ('Piestewa', 33.5465, -112.0201), ('Hedgpeth', 33.6820, -112.1660)]:
        v, x, zz = peak(lat, lon)
        f = fsample(floor, FW, FH, x - x0, zz - z0)
        print(f'  {name:12s} top {v:7.1f} m MSL, {v-base:+7.1f} m on KGEU at x {x:.0f} z {zz:.0f}, relief {v-f:+6.1f}')

def fsample(F, FW, FH, lx, lz):
    gx = min(FW - 1.001, max(0, lx / FCELL - 0.5)); gz = min(FH - 1.001, max(0, lz / FCELL - 0.5))
    i, j = int(gx), int(gz); fx, fz = gx - i, gz - j; k = j * FW + i
    return (F[k] * (1 - fx) + F[k + 1] * fx) * (1 - fz) + (F[k + FW] * (1 - fx) + F[k + FW + 1] * fx) * fz

def gauss(a, W, H, sig):
    r = int(sig * 3)
    w = [math.exp(-0.5 * (d / sig) ** 2) for d in range(-r, r + 1)]
    t = [0.0] * (W * H); o = [0.0] * (W * H)
    for j in range(H):
        for i in range(W):
            v = 0.0
            for d in range(-r, r + 1):
                ii = i + d
                if 0 <= ii < W:
                    v += a[j * W + ii] * w[d + r]
            t[j * W + i] = v
    for j in range(H):
        for i in range(W):
            v = 0.0
            for d in range(-r, r + 1):
                jj = j + d
                if 0 <= jj < H:
                    v += t[jj * W + i] * w[d + r]
            o[j * W + i] = v
    return o

if __name__ == '__main__':
    main()
