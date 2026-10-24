"""libsbc (PipeWire'ın SBC eklentisinin bağlandığı /lib64/libsbc.so.1) için ctypes sarmalayıcı.

ffmpeg'in SBC encoder'ı kanal modu/alt-bant seçtirmediği için (ölçüldü: "XQ" isteğinde 4 alt-bant + joint + bp42
seçti) PipeWire'ın gerçek parametreleri ancak bu yolla birebir üretilebilir. Yapı: docs/research/upstream/sbc.h.
"""
from __future__ import annotations

import ctypes
import ctypes.util

import numpy as np

FREQ = {16000: 0x00, 32000: 0x01, 44100: 0x02, 48000: 0x03}
BLK = {4: 0x00, 8: 0x01, 12: 0x02, 16: 0x03}
MODE = {"mono": 0x00, "dual": 0x01, "stereo": 0x02, "joint": 0x03}
ALLOC = {"loudness": 0x00, "snr": 0x01}
SB = {4: 0x00, 8: 0x01}
SBC_LE = 0x00


class _Sbc(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_ulong), ("frequency", ctypes.c_uint8), ("blocks", ctypes.c_uint8),
                ("subbands", ctypes.c_uint8), ("mode", ctypes.c_uint8), ("allocation", ctypes.c_uint8),
                ("bitpool", ctypes.c_uint8), ("endian", ctypes.c_uint8),
                ("priv", ctypes.c_void_p), ("priv_alloc_base", ctypes.c_void_p)]


_lib = ctypes.CDLL(ctypes.util.find_library("sbc") or "libsbc.so.1")
_lib.sbc_init.argtypes = [ctypes.POINTER(_Sbc), ctypes.c_ulong]
_lib.sbc_init_msbc.argtypes = [ctypes.POINTER(_Sbc), ctypes.c_ulong]
_lib.sbc_encode.argtypes = [ctypes.POINTER(_Sbc), ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                            ctypes.c_size_t, ctypes.POINTER(ctypes.c_ssize_t)]
_lib.sbc_encode.restype = ctypes.c_ssize_t
_lib.sbc_decode.argtypes = [ctypes.POINTER(_Sbc), ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                            ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
_lib.sbc_decode.restype = ctypes.c_ssize_t
_lib.sbc_get_codesize.argtypes = [ctypes.POINTER(_Sbc)]
_lib.sbc_get_codesize.restype = ctypes.c_size_t
_lib.sbc_get_frame_length.argtypes = [ctypes.POINTER(_Sbc)]
_lib.sbc_get_frame_length.restype = ctypes.c_size_t
_lib.sbc_finish.argtypes = [ctypes.POINTER(_Sbc)]


class Codec:
    def __init__(self, rate=48000, mode="joint", bitpool=53, blocks=16, subbands=8, allocation="loudness",
                 msbc=False):
        self.s = _Sbc()
        if msbc:
            if _lib.sbc_init_msbc(ctypes.byref(self.s), 0) != 0:
                raise OSError("sbc_init_msbc başarısız")
        else:
            if _lib.sbc_init(ctypes.byref(self.s), 0) != 0:
                raise OSError("sbc_init başarısız")
            self.s.frequency, self.s.blocks, self.s.subbands = FREQ[rate], BLK[blocks], SB[subbands]
            self.s.mode, self.s.allocation, self.s.bitpool = MODE[mode], ALLOC[allocation], bitpool
        self.s.endian = SBC_LE
        self.channels = 1 if (msbc or mode == "mono") else 2

    def close(self):
        _lib.sbc_finish(ctypes.byref(self.s))

    @property
    def frame_length(self):
        return _lib.sbc_get_frame_length(ctypes.byref(self.s))

    @property
    def codesize(self):
        return _lib.sbc_get_codesize(ctypes.byref(self.s))

    def encode(self, pcm: np.ndarray) -> bytes:
        """pcm: int16, (n,) veya (n, ch) interleaved."""
        raw = np.ascontiguousarray(pcm, dtype="<i2").tobytes()
        cs, fl = self.codesize, self.frame_length
        out, buf, written = bytearray(), ctypes.create_string_buffer(fl + 16), ctypes.c_ssize_t(0)
        for off in range(0, len(raw) - cs + 1, cs):
            chunk = raw[off:off + cs]
            used = _lib.sbc_encode(ctypes.byref(self.s), chunk, cs, buf, len(buf), ctypes.byref(written))
            if used < 0:
                raise OSError(f"sbc_encode hata {used}")
            out += buf.raw[:written.value]
        return bytes(out)

    def decode(self, data: bytes) -> np.ndarray:
        cs = self.codesize
        pcm, obuf, written = bytearray(), ctypes.create_string_buffer(cs * 2), ctypes.c_size_t(0)
        off = 0
        while off < len(data):
            chunk = data[off:]
            used = _lib.sbc_decode(ctypes.byref(self.s), chunk, len(chunk), obuf, len(obuf), ctypes.byref(written))
            if used <= 0:
                break
            pcm += obuf.raw[:written.value]
            off += used
        a = np.frombuffer(bytes(pcm), dtype="<i2")
        return a.reshape(-1, self.channels) if self.channels == 2 else a
