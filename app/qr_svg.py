from __future__ import annotations

# Compact pure-Python ISO/IEC 18004 QR Code SVG generator (Versions 1..4, ECC Level L, Byte Mode)
# Zero external dependencies required.

_VERSION_SPECS: dict[int, tuple[int, int, int]] = {
    # version: (size, total_data_codewords, ec_codewords)
    1: (21, 19, 7),
    2: (25, 34, 10),
    3: (29, 55, 15),
    4: (33, 80, 20),
}

_ALIGNMENT_POS: dict[int, list[int]] = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
}


def _gf_mul(a: int, b: int) -> int:
    res = 0
    for _ in range(8):
        if b & 1:
            res ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= 0x11D
        b >>= 1
    return res


def _rs_generator_poly(degree: int) -> list[int]:
    poly = [1]
    root = 1
    for _ in range(degree):
        next_poly = [0] * (len(poly) + 1)
        for i, c in enumerate(poly):
            next_poly[i] ^= c
            next_poly[i + 1] ^= _gf_mul(c, root)
        poly = next_poly
        root = _gf_mul(root, 2)
    return poly


def _rs_encode(data: list[int], ec_len: int) -> list[int]:
    gen = _rs_generator_poly(ec_len)
    reg = [0] * ec_len
    for byte in data:
        factor = byte ^ reg[0]
        reg = reg[1:] + [0]
        for i in range(ec_len):
            reg[i] ^= _gf_mul(gen[i + 1], factor)
    return reg


def _encode_bytes_to_codewords(payload: bytes) -> tuple[int, list[int]]:
    n = len(payload)
    for ver, (size, data_cw, ec_cw) in _VERSION_SPECS.items():
        if n + 2 <= data_cw:
            break
    else:
        payload = payload[:78]
        n = len(payload)
        ver, (size, data_cw, ec_cw) = 4, _VERSION_SPECS[4]

    bits: list[int] = [0, 1, 0, 0]  # Byte mode (0100)
    for i in range(7, -1, -1):
        bits.append((n >> i) & 1)
    for b in payload:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    max_bits = data_cw * 8
    for _ in range(min(4, max_bits - len(bits))):
        bits.append(0)
    while len(bits) % 8 != 0:
        bits.append(0)

    codewords = []
    for i in range(0, len(bits), 8):
        val = 0
        for bit in bits[i : i + 8]:
            val = (val << 1) | bit
        codewords.append(val)

    pad_bytes = [0xEC, 0x11]
    idx = 0
    while len(codewords) < data_cw:
        codewords.append(pad_bytes[idx % 2])
        idx += 1

    ec = _rs_encode(codewords, ec_cw)
    return ver, codewords + ec


def _place_finder(grid: list[list[int | None]], reserved: list[list[bool]], r: int, c: int) -> None:
    size = len(grid)
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            rr, cc = r + dr, c + dc
            if 0 <= rr < size and 0 <= cc < size:
                if 0 <= dr <= 6 and 0 <= dc <= 6:
                    if dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                        grid[rr][cc] = 1
                    else:
                        grid[rr][cc] = 0
                else:
                    grid[rr][cc] = 0
                reserved[rr][cc] = True


def _place_alignment(grid: list[list[int | None]], reserved: list[list[bool]], r: int, c: int) -> None:
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            rr, cc = r + dr, c + dc
            if reserved[rr][cc]:
                return
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            rr, cc = r + dr, c + dc
            val = 1 if (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)) else 0
            grid[rr][cc] = val
            reserved[rr][cc] = True


def _format_bits(ecc_bits: int, mask: int) -> int:
    data = ((ecc_bits & 0x3) << 3) | (mask & 0x7)
    rem = data << 10
    for i in range(14, 9, -1):
        if (rem >> i) & 1:
            rem ^= 0x537 << (i - 10)
    return ((data << 10) | rem) ^ 0x5412


def generate_qr_matrix(text: str, border: int = 4) -> list[list[int]]:
    """Return a 2D list of 0/1 modules (1 = dark, 0 = light) with quiet zone `border`."""
    ver, all_cw = _encode_bytes_to_codewords(text.encode("utf-8"))
    size = _VERSION_SPECS[ver][0]
    grid: list[list[int | None]] = [[None] * size for _ in range(size)]
    reserved: list[list[bool]] = [[False] * size for _ in range(size)]

    _place_finder(grid, reserved, 0, 0)
    _place_finder(grid, reserved, 0, size - 7)
    _place_finder(grid, reserved, size - 7, 0)

    centers = _ALIGNMENT_POS[ver]
    for r in centers:
        for c in centers:
            if not ((r == 6 and c == 6) or (r == 6 and c == size - 7) or (r == size - 7 and c == 6)):
                _place_alignment(grid, reserved, r, c)

    for i in range(8, size - 8):
        if not reserved[6][i]:
            grid[6][i] = 1 if i % 2 == 0 else 0
            reserved[6][i] = True
        if not reserved[i][6]:
            grid[i][6] = 1 if i % 2 == 0 else 0
            reserved[i][6] = True

    # Reserve format info modules and dark module
    for i in range(9):
        if i < size:
            reserved[8][i] = True
            reserved[i][8] = True
    for i in range(8):
        reserved[8][size - 1 - i] = True
        reserved[size - 1 - i][8] = True
    grid[size - 8][8] = 1
    reserved[size - 8][8] = True

    bit_stream: list[int] = []
    for cw in all_cw:
        for i in range(7, -1, -1):
            bit_stream.append((cw >> i) & 1)

    bit_idx = 0
    upward = True
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        row_iter = range(size - 1, -1, -1) if upward else range(size)
        for r in row_iter:
            for dc in (0, -1):
                c = col + dc
                if not reserved[r][c]:
                    b = bit_stream[bit_idx] if bit_idx < len(bit_stream) else 0
                    bit_idx += 1
                    # Apply Mask 0: (r + c) % 2 == 0
                    if (r + c) % 2 == 0:
                        b ^= 1
                    grid[r][c] = b
        upward = not upward
        col -= 2

    # Write Format Information (Level L = 01, Mask = 000)
    fmt = _format_bits(0b01, 0)
    fmt_bits = [(fmt >> (14 - i)) & 1 for i in range(15)]

    coords_tl = [
        (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
        (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
    ]
    for idx, (r, c) in enumerate(coords_tl):
        grid[r][c] = fmt_bits[idx]

    for idx in range(7):
        grid[size - 1 - idx][8] = fmt_bits[idx]
    for idx in range(7, 15):
        grid[8][size - 15 + idx] = fmt_bits[idx]

    total = size + border * 2
    out = [[0] * total for _ in range(total)]
    for r in range(size):
        for c in range(size):
            if grid[r][c] == 1:
                out[r + border][c + border] = 1
    return out


def generate_qr_svg(text: str, border: int = 4) -> str:
    """Return an inline SVG string containing a valid scannable QR code for `text`."""
    mat = generate_qr_matrix(text, border=border)
    total = len(mat)
    rects: list[str] = []
    for r in range(total):
        for c in range(total):
            if mat[r][c] == 1:
                rects.append(f"M{c},{r}h1v1h-1z")
    path_d = "".join(rects)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'shape-rendering="crispEdges" width="220" height="220">'
        f'<rect width="{total}" height="{total}" fill="#ffffff" rx="2"/>'
        f'<path d="{path_d}" fill="#0f172a"/></svg>'
    )
