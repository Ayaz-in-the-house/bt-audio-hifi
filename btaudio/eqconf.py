"""F5/F8 — EQ tasarımını çalışır config'e çevirir.

1) BİRİNCİL: PipeWire filter-chain + WirePlumber 0.5 "smart filter". Yalnız hedef sink'e (bu kulaklık) giden
   akışlara uygulanır; hoparlör/Dock etkilenmez. Ek süreç: PipeWire'ın kendi filter-chain.service'i.
   bq_peaking = RBJ cookbook (PipeWire audioconvert/biquad.c:223) → btaudio.loudness.eq_response_db ile birebir.
2) İSTEĞE BAĞLI: EasyEffects 8 preset'i (aynı bantlar) — GUI ile deneme yapmak için; otomatik başlatılmaz.
"""
from __future__ import annotations


def _target_spa(target) -> str:
    from .console import target_spa          # tek kaynak (U72): str → node.name, dict → kimlik eşleşmesi
    return target_spa(target)

HEADER = """# bt-audio-hifi (PRD-BTA01 F8) — ÜRETİLMİŞ DOSYA, elle düzenleme: `bta bass-apply` yeniden yazar.
# Kaynak tasarım: {source}
# Hedef: {target} · preamp {preamp_db} dB (kırpılma koruması: toplam güçlendirmenin tepe değeri kadar)
"""


def render_filter_chain(design: dict, target_sink: str, source: str = "-") -> str:
    bands = design["bands"]
    mult = 10 ** (design["preamp_db"] / 20)
    nodes = [
        "                    {\n"
        "                        type  = builtin\n"
        "                        name  = preamp\n"
        "                        label = linear\n"
        f'                        control = {{ "Mult" = {mult:.6f} "Add" = 0.0 }}\n'
        "                    }"
    ]
    for i, b in enumerate(bands, 1):
        if b["type"] != "Bell":
            raise ValueError(f"yalnız Bell (bq_peaking) desteklenir: {b}")
        nodes.append(
            "                    {\n"
            "                        type  = builtin\n"
            f"                        name  = eq_band_{i}\n"
            "                        label = bq_peaking\n"
            f'                        control = {{ "Freq" = {float(b["frequency"]):.1f} "Q" = {float(b["q"]):.1f} '
            f'"Gain" = {float(b["gain"]):.1f} }}\n'
            "                    }")
    chain = ["preamp"] + [f"eq_band_{i}" for i in range(1, len(bands) + 1)]
    links = [f'                    {{ output = "{a}:Out" input = "{b}:In" }}' for a, b in zip(chain, chain[1:])]
    return HEADER.format(source=source, target=design.get("target"), preamp_db=design["preamp_db"]) + f"""
context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "BT kulaklık bas EQ (bta)"
            media.name       = "BT kulaklık bas EQ (bta)"
            filter.graph = {{
                nodes = [
{chr(10).join(nodes)}
                ]
                links = [
{chr(10).join(links)}
                ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "effect_input.bta_bass_eq"
                media.class = Audio/Sink
                filter.smart = true
                filter.smart.name = "bta-bass-eq"
                filter.smart.target = {_target_spa(target_sink)}
            }}
            playback.props = {{
                node.name    = "effect_output.bta_bass_eq"
                node.passive = true
            }}
        }}
    }}
]
"""


def render_ee_preset(design: dict) -> dict:
    band = {f"band{i}": {"type": "Bell", "mode": "RLC (BT)", "slope": "x1", "solo": False, "mute": False,
                         "gain": b["gain"], "frequency": b["frequency"], "q": b["q"], "width": 4.0}
            for i, b in enumerate(design["bands"])}
    return {"output": {
        "blocklist": [],
        "plugins_order": ["equalizer#0", "limiter#0"],
        "equalizer#0": {"bypass": False, "input-gain": design["preamp_db"], "output-gain": 0.0, "mode": "IIR",
                        "split-channels": False, "num-bands": len(design["bands"]), "left": band, "right": band},
        "limiter#0": {"bypass": False, "input-gain": 0.0, "output-gain": 0.0, "threshold": -1.0,
                      "attack": 5.0, "release": 5.0, "lookahead": 5.0},
    }}
