"""A2DP codec capability/configuration byte çözücüleri.

Kaynak otoritesi: PipeWire 1.6.8 `spa/plugins/bluez5/a2dp-codec-caps.h` (little-endian bitfield düzeni) ve
`a2dp-codec-aac.c` — kopyaları `docs/research/upstream/` altında, SHA256SUMS ile.
"""
from __future__ import annotations

import math

A2DP_CODEC_SBC = 0x00
A2DP_CODEC_MPEG24 = 0x02
A2DP_CODEC_VENDOR = 0xFF

# ── AAC ──────────────────────────────────────────────────────────────────────
_AAC_OBJECT_TYPES = [
    (0x80, "MPEG-2 AAC LC"),
    (0x40, "MPEG-4 AAC LC"),
    (0x20, "MPEG-4 AAC LTP"),
    (0x10, "MPEG-4 AAC SCA"),
    (0x02, "MPEG-4 AAC ELD"),
]
# 12-bit frekans alanı: freq1<<4 | freq2
_AAC_FREQS = [
    (0x800, 8000), (0x400, 11025), (0x200, 12000), (0x100, 16000),
    (0x080, 22050), (0x040, 24000), (0x020, 32000), (0x010, 44100),
    (0x008, 48000), (0x004, 64000), (0x002, 88200), (0x001, 96000),
]
_AAC_CHANNELS = [(0x08, 1), (0x04, 2), (0x02, 6), (0x01, 8)]

DEFAULT_AAC_BITRATE = 320000   # a2dp-codec-aac.c:21
MIN_AAC_BITRATE = 64000        # a2dp-codec-aac.c:22
AAC_FORCED_BANDWIDTH = 19293   # a2dp-codec-aac.c:402
RTP_HEADER_SIZE = 12


def decode_aac(raw: bytes) -> dict:
    if len(raw) != 6:
        raise ValueError(f"AAC capability 6 bayt olmalı, {len(raw)} geldi")
    obj, f1, b2, b3, b4, b5 = raw
    freq = (f1 << 4) | (b2 >> 4)
    return {
        "codec": "AAC",
        "object_types": [n for bit, n in _AAC_OBJECT_TYPES if obj & bit],
        "rates": [r for bit, r in _AAC_FREQS if freq & bit],
        "channels": sorted(c for bit, c in _AAC_CHANNELS if (b2 & 0x0F) & bit),
        "vbr": bool(b3 & 0x80),
        "bitrate": ((b3 & 0x7F) << 16) | (b4 << 8) | b5,
        "raw": raw.hex(" "),
    }


def encode_aac_bitrate(bitrate: int, vbr: bool) -> bytes:
    """AAC_SET_BITRATE makrosunun eşdeğeri (vbr biti bitrate1'in üst bitinde)."""
    return bytes([((bitrate >> 16) & 0x7F) | (0x80 if vbr else 0), (bitrate >> 8) & 0xFF, bitrate & 0xFF])


def pipewire_effective_aac_bitrate(conf_bitrate: int) -> int:
    """get_valid_aac_bitrate(): bilinmeyen/sahte (<64k) → 320k; aksi hâlde min(conf, 320k)."""
    if conf_bitrate < MIN_AAC_BITRATE:
        return DEFAULT_AAC_BITRATE
    return min(conf_bitrate, DEFAULT_AAC_BITRATE)


def pipewire_aac_max_bitrate(mtu: int, rate: int) -> int:
    """Fragmentation yok → her AAC çerçevesi (mtu - RTP başlığı) içine sığmalı (a2dp-codec-aac.c:382)."""
    return ((mtu - RTP_HEADER_SIZE) * 8 * rate) // 1024


def pipewire_aac_forced_bandwidth(vbr: bool, cur_bitrate: int):
    """a2dp-codec-aac.c:400 — yalnız vbr=0 ve >110 kbps CBR'de 19293 Hz zorlanır; aksi hâlde FDK otomatik."""
    if not vbr and cur_bitrate > 110000:
        return AAC_FORCED_BANDWIDTH
    return None


# ── SBC ──────────────────────────────────────────────────────────────────────
_SBC_FREQS = [(0x8, 16000), (0x4, 32000), (0x2, 44100), (0x1, 48000)]
_SBC_MODES = [(0x8, "mono"), (0x4, "dual"), (0x2, "stereo"), (0x1, "joint")]
_SBC_BLOCKS = [(0x8, 4), (0x4, 8), (0x2, 12), (0x1, 16)]
_SBC_SUBBANDS = [(0x2, 4), (0x1, 8)]
_SBC_ALLOC = [(0x2, "snr"), (0x1, "loudness")]


def decode_sbc(raw: bytes) -> dict:
    if len(raw) != 4:
        raise ValueError(f"SBC capability 4 bayt olmalı, {len(raw)} geldi")
    b0, b1, mn, mx = raw
    return {
        "codec": "SBC",
        "rates": [r for bit, r in _SBC_FREQS if (b0 >> 4) & bit],
        "channel_modes": [m for bit, m in _SBC_MODES if (b0 & 0x0F) & bit],
        "block_lengths": [b for bit, b in _SBC_BLOCKS if (b1 >> 4) & bit],
        "subbands": [s for bit, s in _SBC_SUBBANDS if ((b1 >> 2) & 0x3) & bit],
        "allocation": [a for bit, a in _SBC_ALLOC if (b1 & 0x3) & bit],
        "min_bitpool": mn,
        "max_bitpool": mx,
        "raw": raw.hex(" "),
    }


def sbc_frame_length(mode: str, subbands: int, blocks: int, bitpool: int) -> int:
    """A2DP spec SBC çerçeve uzunluğu (bayt)."""
    ch = 1 if mode == "mono" else 2
    base = 4 + (4 * subbands * ch) // 8
    if mode in ("mono", "dual"):
        return base + math.ceil(blocks * ch * bitpool / 8)
    if mode == "stereo":
        return base + math.ceil(blocks * bitpool / 8)
    if mode == "joint":
        return base + math.ceil((subbands + blocks * bitpool) / 8)
    raise ValueError(f"bilinmeyen SBC kanal modu: {mode}")


def sbc_bitrate(mode: str, rate: int, subbands: int, blocks: int, bitpool: int) -> int:
    return 8 * sbc_frame_length(mode, subbands, blocks, bitpool) * rate // (subbands * blocks)


# ── dispatch ─────────────────────────────────────────────────────────────────
def decode(codec_id: int, raw: bytes) -> dict:
    if codec_id == A2DP_CODEC_SBC:
        return decode_sbc(raw)
    if codec_id == A2DP_CODEC_MPEG24:
        return decode_aac(raw)
    return {"codec": "vendor" if codec_id == A2DP_CODEC_VENDOR else f"id-{codec_id}", "raw": raw.hex(" ")}
