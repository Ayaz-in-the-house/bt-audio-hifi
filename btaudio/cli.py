"""bta — Bluetooth audio hi-fi durum aracı.

  bta snapshot [label]        durum JSON'u state/snapshots/'a yaz
  bta diff [A] [B]            iki snapshot farkı (varsayılan: son iki); 'latest', '-2', dosya yolu
  bta status                  insan-okur özet
  bta check [--json]          kabul kontrolleri (exit 0 = hepsi geçti)
  bta install | uninstall     config drop-in'lerini kur/kaldır (yedekli) + PipeWire yeniden başlat
  bta codec <profil>          kart profilini değiştir (a2dp-sink | a2dp-sink-sbc_xq | a2dp-sink-sbc)
  bta link-test [sn] [--passive] [--label x]  paket/bitrate düşürme ölçümü → analysis/link-health/
  bta bench                   encoder benchmark (AAC/SBC/SBC-XQ/HFP) → analysis/encoder-benchmark-*.md
  bta bass-analyze [dosya…] [--target harman-ie-bass|flat] [--max-boost 12]  eşleştirme JSON → yanıt+EQ
  bta bass-apply [analiz.json]   EQ'yu smart filter-chain olarak kur (yalnız kulaklık) + EE preset'i üret
  bta bass-tune [--no-open]      CANLI bas ayarı: yerel sayfa (Zen'de açılır), müziğini dinlerken kaydırıcılar, Kaydet
  bta console [--no-open]        PROFESYONEL KONSOL: 10 bant EQ (grafikten sürükle) + ses uzayı + profiller
                  [--idle-timeout SN]   boşta kapanma (varsayılan 3600, 0 = hiç; servis 0 kullanır)
  bta service install|uninstall|status   otomatik modu arka plan servisi yap (systemd kullanıcı birimi, girişte başlar)
                    [--port N] [--allow-host AD]   uzaktan (tailnet) erişim: `tailscale serve` adı Host kapısından geçer
  bta model verify|fetch         yerel müzik türü sınıflayıcısı (YAMNet ONNX, sha256 kilitli; otomatik modlar için)
  bta bass-off                   bas EQ'sunu kaldır (filter-chain durur, dosyalar yedeklenir)
  bta btmon-report <x.btsnoop>   kullanıcının root ile aldığı radyo kaydını çözümle (+ yanındaki .rssi.txt)
  bta apply-pending              kurulu ama etkin olmayan config'leri (T-L24) yalnız ilgili servisi yeniden başlatarak etkinleştir
  bta abx [a] [b] [--clip f] [--start s] [--dur s] [--n 12] [--apply]   kör ABX dinleme testi (etkileşimli)
"""
from __future__ import annotations

import datetime as _dt
import glob
import json
import os
import shutil
import sys
import time

from . import collect, paths, state

SNAP_DIR = os.path.join(collect.REPO, "state", "snapshots")
BACKUP_DIR = paths.backups_root()  # C0: kullanıcı verisi (repo dışı); eski yedekler repo state/backups/ altında kalır
DECISION = os.path.join(collect.REPO, "decision.json")
SERVICES = ["pipewire.service", "pipewire-pulse.service", "wireplumber.service"]
ALL_SERVICES = SERVICES + ["filter-chain.service"]


def _decision():
    with open(DECISION) as f:
        return json.load(f)


def cmd_snapshot(args):
    label = (args[0] if args else "manual").replace("/", "-").replace(" ", "-")
    snap = collect.snapshot(label)
    os.makedirs(SNAP_DIR, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(SNAP_DIR, f"{ts}-{label}.json")
    with open(path, "w") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(path)
    return 0


def _resolve(ref):
    snaps = sorted(glob.glob(os.path.join(SNAP_DIR, "*.json")))
    if ref in (None, "latest"):
        return snaps[-1]
    if ref.lstrip("-").isdigit():
        return snaps[int(ref)]
    if os.path.exists(ref):
        return ref
    hits = [s for s in snaps if ref in os.path.basename(s)]
    if len(hits) != 1:
        raise SystemExit(f"snapshot çözülemedi: {ref!r} ({len(hits)} eşleşme)")
    return hits[0]


def cmd_diff(args):
    a = _resolve(args[0] if len(args) > 0 else "-2")
    b = _resolve(args[1] if len(args) > 1 else "latest")
    with open(a) as fa, open(b) as fb:
        d = state.diff(json.load(fa), json.load(fb))
    print(f"A: {os.path.basename(a)}\nB: {os.path.basename(b)}")
    for cat, sym in (("changed", "~"), ("added", "+"), ("removed", "-")):
        for k, v in d[cat].items():
            if cat == "changed":
                print(f"  {sym} {k}: {json.dumps(v[0], ensure_ascii=False)} → {json.dumps(v[1], ensure_ascii=False)}")
            else:
                print(f"  {sym} {k}: {json.dumps(v, ensure_ascii=False)}")
    n = sum(len(d[c]) for c in d)
    print(f"  ({n} fark)")
    return 0


def checks(snap=None):
    """(id, ok, detay) listesi — TEST-PLAN T-L01..T-L05, T-L20 ile aynı kimlikler."""
    s = snap or collect.snapshot("check")
    dec = _decision()
    out = []
    card, sink = s.get("card", {}), s.get("sink", {})
    out.append(("T-L01", str(card.get("active_profile", "")).startswith("a2dp-sink"),
                f"profil={card.get('active_profile')}"))
    out.append(("T-L02", sink.get("codec") == dec["codec"], f"codec={sink.get('codec')} karar={dec['codec']}"))
    out.append(("T-L03", sink.get("channels") == 2 and (sink.get("rate") or 0) >= 44100,
                f"{sink.get('channels')}ch {sink.get('rate')}Hz"))
    dp = s.get("wp_state", {}).get("default-profile", {}).get(collect.CARD)
    out.append(("T-L04", bool(dp) and dp.startswith("a2dp-sink"), f"default-profile={dp}"))
    a = s.get("wp_settings", {}).get("bluetooth.autoswitch-to-headset-profile", {})
    out.append(("T-L05", a.get("value") == "false" and a.get("saved") == "false", f"autoswitch={a}"))
    cfg = s.get("configs", {})
    bad = {k: v["status"] for k, v in cfg.items() if v.get("status") != "ok"} if "error" not in cfg else cfg
    out.append(("T-L20", not bad, f"config sapması={bad or 'yok'}"))
    mt = {rel: os.path.getmtime(os.path.join(collect.CONFIG_DST, rel))
          for rel, v in (cfg.items() if "error" not in cfg else []) if v.get("status") == "ok"}
    pend = pending_restarts(mt, service_start_times())
    out.append(("T-L24", not pend, f"etkin-değil (yeniden başlatma bekliyor)={pend or 'yok'}"))
    try:
        from . import console as _c
        tgt = _c.smart_target(open(os.path.join(collect.CONFIG_DST, CONSOLE_REL)).read())
    except OSError:
        tgt = None
    if tgt is not None:                              # U71: konsol kuruluysa hedefi bağlı kulaklık olmalı
        cur = collect.filter_target() if sink.get("present") else None
        out.append(("T-L25", not _c.target_stale("filter.smart.target = " + _c.target_spa(tgt), cur),
                    f"filtre hedefi={tgt} beklenen={cur}"))
    return out


def cmd_check(args):
    res = checks()
    if "--json" in args:
        print(json.dumps([{"id": i, "ok": ok, "detail": d} for i, ok, d in res], ensure_ascii=False))
    else:
        for i, ok, d in res:
            print(f"  {'PASS' if ok else 'FAIL'}  {i}  {d}")
    failed = [i for i, ok, _ in res if not ok]
    print(f"  == {len(res) - len(failed)}/{len(res)} geçti" + (f" · FAIL: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


def cmd_status(args):
    s = collect.snapshot("status")
    sk, t = s.get("sink", {}), s.get("bluez", {}).get("transports", {})
    print(f"cihaz   : {s['device'].get('name')} bağlı={s['device'].get('connected')} pil=%{s['device'].get('battery')}")
    print(f"profil  : {s['card'].get('active_profile')}")
    print(f"sink    : {sk.get('codec')} {sk.get('format')} {sk.get('channels')}ch {sk.get('rate')}Hz durum={sk.get('state')}")
    for k, v in t.items():
        print(f"transport {k}: {json.dumps({x: v.get(x) for x in ('codec', 'rates', 'channels', 'channel_modes', 'vbr', 'bitrate', 'min_bitpool', 'max_bitpool', 'pipewire_target_bitrate', 'pipewire_forced_bandwidth_hz', 'state') if x in v}, ensure_ascii=False)}")
    print(f"graf    : {s.get('graph_clock')}")
    for st in s.get("streams", []) if isinstance(s.get("streams"), list) else []:
        print(f"akış    : {st}")
    print(f"wifi    : {s.get('wifi')}  diğer BT: {s.get('other_bt_devices')}")
    print(f"EE      : {s.get('easyeffects')}")
    return 0


def services_for(paths):
    """Değişen config yollarına göre yeniden başlatılması GEREKEN en küçük servis kümesi.
    client.conf.d → servis yok (yeni başlayan native istemciler okur)."""
    svc = []
    if any(p.startswith("pipewire/pipewire.conf.d/") for p in paths):
        return list(SERVICES)
    if any(p.startswith("pipewire/pipewire-pulse.conf.d/") for p in paths):
        svc.append("pipewire-pulse.service")
    if any(p.startswith("wireplumber/") for p in paths):
        svc.append("wireplumber.service")
    if any(p.startswith("pipewire/filter-chain.conf.d/") for p in paths):
        svc.append("filter-chain.service")
    return svc


def pending_restarts(installed_mtimes: dict, service_started: dict) -> list:
    """Teslimat zinciri: kurulu drop-in, onu okuyan servisin son başlangıcından YENİYSE ayar henüz ETKİN DEĞİL."""
    out = []
    for rel, mt in sorted(installed_mtimes.items()):
        for svc in services_for([rel]):
            if mt > service_started.get(svc, 0):
                out.append((rel, svc))
    return out


def parse_systemd_us(value: str) -> float:
    """'Sun 2026-09-27 16:19:29.123456 UTC' → epoch (µs hassasiyet). Boş/n/a → 0."""
    try:
        d = _dt.datetime.strptime(value.strip(), "%a %Y-%m-%d %H:%M:%S.%f UTC")
    except ValueError:
        return 0.0
    return d.replace(tzinfo=_dt.timezone.utc).timestamp()


def service_start_times() -> dict:
    res = {}
    for svc in ALL_SERVICES:
        rc, out, _ = collect.run(["systemctl", "--user", "show", svc, "-p", "ActiveEnterTimestamp",
                                  "--timestamp=us+utc"])
        res[svc] = parse_systemd_us(out.strip().split("=", 1)[-1])
    return res


def _restart_services(services):
    if not services:
        return True
    if "filter-chain.service" in services:
        fc_files = [f for f in os.listdir(os.path.join(collect.CONFIG_DST, "pipewire", "filter-chain.conf.d"))
                    if f.startswith("60-bta-")] if os.path.isdir(
            os.path.join(collect.CONFIG_DST, "pipewire", "filter-chain.conf.d")) else []
        collect.run(["systemctl", "--user", "enable" if fc_files else "disable", "filter-chain.service"], timeout=15)
        if not fc_files:
            collect.run(["systemctl", "--user", "stop", "filter-chain.service"], timeout=15)
            services = [s for s in services if s != "filter-chain.service"]
            if not services:
                return True
    rc, out, err = collect.run(["systemctl", "--user", "restart", *services], timeout=30)
    if rc != 0:
        raise SystemExit(f"servis yeniden başlatma başarısız: {err}")
    if not ({"pipewire.service", "wireplumber.service"} & set(services)):
        return True
    # BT kartı WirePlumber'da yeniden kurulana kadar bekle
    for _ in range(30):
        time.sleep(1)
        c = collect._safe(collect.card)
        if c.get("present") and str(c.get("active_profile", "")).startswith("a2dp"):
            return True
    return False


def cmd_install(args):
    man = collect.configs()
    todo = {k: v for k, v in man.items() if v["status"] != "ok"}
    if not todo:
        print("config zaten kurulu (tüm sha'lar eşleşiyor) — değişiklik yok")
        return 0
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = os.path.join(BACKUP_DIR, f"install-{ts}")
    for rel, v in todo.items():
        dst = os.path.join(collect.CONFIG_DST, rel)
        if os.path.exists(dst):
            os.makedirs(os.path.dirname(os.path.join(bdir, rel)), exist_ok=True)
            shutil.copy2(dst, os.path.join(bdir, rel))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(v["src"], dst)
        print(f"  kuruldu: {dst.replace(collect.HOME, '~', 1)} ({v['status']})")
    if "--no-restart" not in args and not os.environ.get("BTA_NO_RESTART"):
        svc = services_for(list(todo))
        ok = _restart_services(svc)
        print(f"  yeniden başlatılan: {svc or 'yok (yeni istemciler okur)'}; BT kartı hazır: {ok}")
    final = collect.configs()
    return 0 if all(v["status"] == "ok" for v in final.values()) else 1


def cmd_uninstall(args):
    man = collect.configs()
    removed = []
    for rel, v in man.items():
        dst = os.path.join(collect.CONFIG_DST, rel)
        if v["status"] == "ok":
            os.remove(dst)
            removed.append(rel)
            print(f"  kaldırıldı: ~/.config/{rel}")
        elif v["status"] == "drift":
            print(f"  ATLANDI (elle değiştirilmiş, sha farklı): ~/.config/{rel}")
    if "--no-restart" not in args:
        svc = services_for(removed)
        print(f"  yeniden başlatılan: {svc or 'yok'}; hazır: {_restart_services(svc)}")
    return 0


def cmd_codec(args):
    if not args:
        raise SystemExit("kullanım: bta codec <a2dp-sink|a2dp-sink-sbc_xq|a2dp-sink-sbc>")
    rc, out, err = collect.run(["pactl", "set-card-profile", collect.CARD, args[0]])
    if rc != 0:
        raise SystemExit(f"pactl hata: {err}")
    time.sleep(2)
    return cmd_status([])


def cmd_link_test(args):
    from . import link
    secs = int(next((a for a in args if a.isdigit()), "30"))
    label = args[args.index("--label") + 1] if "--label" in args else "run"
    res = link.run_test(secs, passive="--passive" in args)
    out_dir = os.path.join(collect.REPO, "analysis", "link-health")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{label}.json")
    with open(path, "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(json.dumps({k: res.get(k) for k in ("verdict", "mode", "codec", "seconds", "reduce_events",
                                               "increase_events", "min_bitrate_seen")}, ensure_ascii=False))
    print(path)
    return 0 if res["verdict"] in ("CLEAN", "NO_DATA") else 3


def cmd_bench(args):
    from . import bench
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tmp = os.path.join(collect.REPO, "analysis", "tmp", f"bench-{stamp}")
    brahms = os.path.join(collect.REPO, "analysis", "tmp", "brahms1-48k-45s.wav")
    sig = bench.make_signals(tmp, brahms=brahms)
    res = bench.run(sig, tmp)
    out = os.path.join(collect.REPO, "analysis")
    bench.save(res, out, stamp)
    md = bench.to_markdown(res)
    with open(os.path.join(out, f"encoder-benchmark-{stamp}.md"), "w") as f:
        f.write(f"# Encoder benchmark {stamp}\n\n" + (bench.__doc__ or "") + "\n" + md + "\n")
    print(md)
    return 0


def _opt(args, name, default):
    return args[args.index(name) + 1] if name in args else default


def cmd_abx(args):
    from . import abx
    pos = [a for a in args if not a.startswith("--") and a not in
           {_opt(args, k, None) for k in ("--clip", "--start", "--dur", "--n")}]
    a, b = (pos + ["aac", "sbc"])[:2]
    clip = _opt(args, "--clip", os.path.join(collect.REPO, "analysis", "tmp", "brahms1-48k-45s.wav"))
    res = abx.run(a, b, clip=clip, n=int(_opt(args, "--n", 12)), start=float(_opt(args, "--start", 2)),
                  dur=float(_opt(args, "--dur", 8)), apply="--apply" in args,
                  out_dir=os.path.join(collect.REPO, "analysis", "abx"))
    print(f"\nSONUÇ: {res['correct']}/{res['n']} doğru · p={res['p_value']} · "
          f"{'FARK DUYULUYOR' if res['distinguishable'] else 'fark istatistiksel olarak duyulmuyor'}"
          f" · tercih={res['preference']}")
    if "--apply" in args and res["preference"]:
        dec = _decision()
        dec.update({"codec": res["preference"], "profile": abx.PROFILES[res["preference"]],
                    "decided_at": res["at"], "status": "ABX ile kullanıcı kararı",
                    "evidence": f"analysis/abx/ ({res['correct']}/{res['n']}, p={res['p_value']})"})
        with open(DECISION, "w") as f:
            json.dump(dec, f, indent=2, ensure_ascii=False)
        print(f"karar yazıldı: {DECISION} → {res['preference']}")
    return 0


def cmd_bass_analyze(args):
    import glob as _g
    from . import bass
    files = [a for a in args if a.endswith(".json")] or sorted(
        _g.glob(os.path.expanduser("~/Downloads/bta-loudness-*.json")), key=os.path.getmtime)[-4:]
    if not files:
        raise SystemExit("eşleştirme dosyası yok: ~/Downloads/bta-loudness-*.json (tools/loudness-match.html)")
    a = bass.analyze(files, target=_opt(args, "--target", "harman-ie-bass"),
                     max_boost_db=float(_opt(args, "--max-boost", 12)))
    out_dir = os.path.join(collect.REPO, "analysis", "bass")
    os.makedirs(out_dir, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for f in files:                                   # ham ölçümü repoya kopyala (kanıt kalıcı olsun)
        shutil.copy2(f, os.path.join(out_dir, os.path.basename(f)))
    path = os.path.join(out_dir, f"{stamp}-analysis.json")
    with open(path, "w") as f:
        json.dump(a, f, indent=2, ensure_ascii=False)
    fr = [k for k in next(iter(a["runs"].values()))["response_db"]]
    print("frekans  " + "  ".join(f"{x:>6}" for x in fr))
    for fit, r in a["runs"].items():
        print(f"{fit[:8]:<8} " + "  ".join(f"{r['response_db'][x]:>6.1f}" for x in fr) + "   (dB, 1 kHz'e göre)")
    if a["seal_gain_db"]:
        print("sızdırm. " + "  ".join(f"{a['seal_gain_db'][x]:>+6.1f}" for x in fr))
    print("phon±5   " + "  ".join(f"{a['phon_sensitivity_db'][x]:>6.1f}" for x in fr) + "   (belirsizlik)")
    print("KARAR:", a["verdict"])
    print("EQ:", ", ".join(f"{b['frequency']}Hz {b['gain']:+.1f}dB Q{b['q']}" for b in a["design"]["bands"]),
          f"· preamp {a['design']['preamp_db']} dB")
    print(path)
    return 0


def cmd_bass_apply(args):
    import glob as _g
    from . import eqconf
    src = next((a for a in args if a.endswith(".json")), None) or sorted(
        _g.glob(os.path.join(collect.REPO, "analysis", "bass", "*-analysis.json")))[-1]
    a = json.load(open(src))
    sink = collect.filter_target()                    # U72: MAC'siz hedef
    rel = "pipewire/filter-chain.conf.d/60-bta-bass-eq.conf"
    os.makedirs(os.path.dirname(os.path.join(paths.generated_dir(), rel)), exist_ok=True)
    with open(os.path.join(paths.generated_dir(), rel), "w") as f:
        f.write(eqconf.render_filter_chain(a["design"], sink, source=os.path.relpath(src, collect.REPO)))
    ee_dir = os.path.join(collect.REPO, "config-optional", "easyeffects")
    os.makedirs(ee_dir, exist_ok=True)
    with open(os.path.join(ee_dir, "bta-bass.json"), "w") as f:
        json.dump(eqconf.render_ee_preset(a["design"]), f, indent=2)
    print(f"üretildi: {paths.generated_dir()}/{rel} + config-optional/easyeffects/bta-bass.json")
    return cmd_install([])


BASS_REL = "pipewire/filter-chain.conf.d/60-bta-bass-eq.conf"


def _write_bass_config(st, source):
    from . import eqconf
    dst_src = os.path.join(paths.generated_dir(), BASS_REL)
    os.makedirs(os.path.dirname(dst_src), exist_ok=True)
    with open(dst_src, "w") as f:
        f.write(eqconf.render_filter_chain(st, collect.filter_target(), source=source))
    ee_dir = os.path.join(collect.REPO, "config-optional", "easyeffects")
    os.makedirs(ee_dir, exist_ok=True)
    with open(os.path.join(ee_dir, "bta-bass.json"), "w") as f:
        json.dump(eqconf.render_ee_preset(st), f, indent=2)


def _latest_tuned():
    import glob as _g
    files = sorted(_g.glob(os.path.join(collect.REPO, "analysis", "bass", "*-tuned.json")))
    return (json.load(open(files[-1])), files[-1]) if files else (None, None)


def cmd_bass_tune(args):
    from . import tuner, tunerserver
    st, src = _latest_tuned()
    gains = {b["id"]: b["gain"] for b in st["bands"]} if st else dict(tuner.PRESETS["notr"])
    if collect.configs().get(BASS_REL, {}).get("status") != "ok":
        _write_bass_config(tuner.state(gains), source=os.path.relpath(src, collect.REPO) if src else "neutral")
        cmd_install([])                                   # yalnız filter-chain.service (enable + restart)

    def on_save(state):
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(collect.REPO, "analysis", "bass", f"{stamp}-tuned.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        _write_bass_config(state, source=os.path.relpath(path, collect.REPO))
        cmd_install([])                                   # dosya ↔ servis tutarlı (T-L24), kısa kesinti
        summ = ", ".join(f"{b['label']} {b['gain']:+.1f} dB" for b in state["bands"])
        return {"file": os.path.relpath(path, collect.REPO), "summary": summ}

    sess = tunerserver.Session(tunerserver.PwApplier(), on_save, initial=gains)
    sess.applier.apply(tuner.state(gains))                # canlı değer = başlangıç değeri (doğrulama)
    httpd, url, stop, _ = tunerserver.serve(sess, port=int(_opt(args, "--port", 0)))
    print(url, flush=True)
    if "--no-open" not in args:
        _open_url(url)
    stop.wait()
    print("bass-tune kapandı; kaydedilen:", sess.saved)
    return 0


CONSOLE_REL = "pipewire/filter-chain.conf.d/60-bta-console.conf"


def _open_url(url):
    """Taşınabilir (C5.2): $BTA_BROWSER komutu → bu makinedeki Zen → sistem varsayılan tarayıcısı. Ajan kabuğunda
    grafik ortam değişkenleri olmayabilir → kullanıcı oturumunun ortamı `systemctl --user show-environment`'tan alınır."""
    import shlex
    import subprocess as _sp
    import webbrowser
    env = dict(os.environ)
    rc, out, _ = collect.run(["systemctl", "--user", "show-environment"])
    env.update(dict(l.split("=", 1) for l in out.splitlines() if "=" in l and l.split("=", 1)[0] in
                    ("WAYLAND_DISPLAY", "DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR")))
    custom = os.environ.get("BTA_BROWSER")
    zen = os.path.expanduser("~/.local/opt/zen/zen")
    cmd = shlex.split(custom) + [url] if custom else ([zen, "--new-tab", url] if os.path.exists(zen) else None)
    if cmd:
        _sp.run(cmd, env=env, timeout=20, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
    else:
        os.environ.update({k: v for k, v in env.items() if k not in os.environ})
        webbrowser.open_new_tab(url)


def _latest_console_state():
    import glob as _g
    files = sorted(_g.glob(os.path.join(paths.console_states_dir(), "*-committed.json")))
    return json.load(open(files[-1])) if files else None


def _migrate_bass_state():
    """Eski 3-bant bas ayarını (bass-tune) konsol bantlarına taşı — ses aynı kalsın."""
    from . import console
    st = console.default_state()
    old, _ = _latest_tuned()
    if old:
        for i, b in enumerate(old["bands"]):
            st["bands"][i] = {"type": "bell", "freq": float(b["frequency"]), "gain": float(b["gain"]),
                              "q": float(b["q"]), "enabled": abs(float(b["gain"])) > 0}
    return console.sanitize(st)


def _install_console(state, source):
    from . import console
    if collect.filter_target() is None:              # U72: kulaklık hiç tanınmadı/bağlı değil → hedefsiz filtre KURMA
        print("  kurulum atlandı: kulaklık tanınmadı (bağla, sonra yeniden dene)", file=sys.stderr)
        return
    path = os.path.join(paths.generated_dir(), CONSOLE_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(console.render_graph_ab(collect.filter_target(), state, source=source))   # D2 A/B graf · U72 MAC'siz hedef
    old = os.path.join(paths.generated_dir(), BASS_REL)
    if os.path.exists(old):                          # iki smart filter üst üste binmesin
        bdir = os.path.join(BACKUP_DIR, f"console-migrate-{_dt.datetime.now():%Y%m%d-%H%M%S}")
        os.makedirs(bdir, exist_ok=True)
        shutil.copy2(old, bdir)
        os.remove(old)
        inst = os.path.join(collect.CONFIG_DST, BASS_REL)
        if os.path.exists(inst):
            shutil.copy2(inst, os.path.join(bdir, "installed-" + os.path.basename(inst)))
            os.remove(inst)
    cmd_install([])


def commit_console_state(st):
    """'Açılışta kullan': durum geçmişi (XDG) + üretilmiş config + kurulum. Repo'ya YAZMAZ (C0, T-L37/U49)."""
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(paths.console_states_dir(), f"{stamp}-committed.json")
    with open(path, "w") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)
    _install_console(st, os.path.basename(path))
    on = [b for b in st["bands"] if b["enabled"]]
    return {"file": path,
            "summary": f"{len(on)} bant, crossfeed {'açık' if st['crossfeed']['enabled'] else 'kapalı'}, genişlik {st['width']}"}


SERVICE_PORT = 8766
SERVICE_UNIT = "bta-console.service"


def _port_owner(port):
    """127.0.0.1:<port>'u DİNLEYEN sürecin {pid, uid, cmd} bilgisi (/proc/net/tcp → soket inode → /proc/<pid>/fd).
    Başka kullanıcının süreci okunamaz → None (güvenilmez sayılır)."""
    want = f"0100007F:{port:04X}"
    inodes = set()
    for tbl in ("/proc/net/tcp",):
        try:
            for line in open(tbl).read().splitlines()[1:]:
                f = line.split()
                if f[1] == want and f[3] == "0A":           # LISTEN
                    inodes.add(f[9])
        except OSError:
            pass
    if not inodes:
        return None
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                if os.readlink(f"/proc/{pid}/fd/{fd}") in {f"socket:[{i}]" for i in inodes}:
                    cmd = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
                    return {"pid": int(pid), "uid": os.stat(f"/proc/{pid}").st_uid,
                            "cmd": [c.decode(errors="replace") for c in cmd if c]}
        except OSError:
            continue
    return None


def _owner_is_bta(port, lookup=None):
    """Güvenlik (port gaspı): portu dinleyen süreç BİZİM kullanıcımızın `bta console` süreci mi?"""
    info = (lookup or _port_owner)(port)
    if not info or info.get("uid") != os.getuid():
        return False
    cmd = info.get("cmd") or []
    return any(os.path.basename(c) == "bta" for c in cmd) and "console" in cmd


def _existing_console(port, owner_ok=None):
    """U75: portta çalışan bir bta konsolu varsa adresini döndür (yeni motor açılmaz); yoksa/başka sunucuysa None.
    Yalnız JSON biçimine güvenilmez: dinleyen süreç bizim `bta console` sürecimiz olmalı (port gaspına karşı)."""
    import urllib.request
    url = f"http://127.0.0.1:{port}/"
    if not (owner_ok or _owner_is_bta)(port):
        return None
    try:
        with urllib.request.urlopen(url + "api/state", timeout=1.5) as r:
            d = json.loads(r.read() or b"{}")
        return url if isinstance(d.get("state"), dict) and "bands" in d["state"] else None
    except (OSError, ValueError):
        return None


def cmd_console(args):
    from . import console, consoleserver
    port_arg = _opt(args, "--port", None)
    probe = int(port_arg) if port_arg else SERVICE_PORT
    if probe and _existing_console(probe):           # U75: tek motor — ikinci süreç aynı düğüme yazmaz
        url = f"http://127.0.0.1:{probe}/"
        print(f"konsol zaten çalışıyor: {url}", flush=True)
        if "--no-open" not in args:
            _open_url(url)
        return 0
    mig = paths.migrate(collect.REPO)                     # C0: eski repo-içi kullanıcı verisini KOPYALA (idempotent)
    if mig["copied"]:
        print("taşındı (kopya):", *mig["copied"], sep="\n  ")
    state = _latest_console_state() or _migrate_bass_state()
    init = _opt(args, "--initial", None)                 # sürüm geçişinde canlı sesi koru (sunucu yeniden başlatma)
    if init:
        state = console.sanitize(json.load(open(init)))
    if collect.configs().get(CONSOLE_REL, {}).get("status") != "ok":
        _install_console(state, "console-init")

    on_commit = commit_console_state

    from . import analyzer as _an
    from . import crossfade as _xf
    if "A/B tıksız geçiş" not in open(os.path.join(collect.CONFIG_DST, CONSOLE_REL)).read():
        _install_console(state, "d2-ab-graph")          # tek seferlik geçiş: A/B grafına (kısa ses kesintisi)
    elif "limiter_stereo" not in open(os.path.join(collect.CONFIG_DST, CONSOLE_REL)).read():
        _install_console(state, "u77-limiter")          # tek seferlik geçiş: ses yükseltici + sınırlayıcı (kısa ses kesintisi)
    if collect._safe(collect.sink).get("present") and console.target_stale(
            open(os.path.join(collect.CONFIG_DST, CONSOLE_REL)).read(), collect.filter_target()):
        _install_console(state, "u72-retarget")         # U71/U72: eski MAC'li ya da adı değişmiş hedef → kimlik hedefine göç
    applier = _xf.Crossfader(_xf.PwCliSession(consoleserver.NODE), fade_s=0.04, active=_xf.detect_active(consoleserver.NODE))
    applier.settle()                                  # önceki süreç yarı geçişte öldüyse karışımı etkin zincire sabitle (U68)
    dev = collect._safe(collect.device)
    snk = collect._safe(collect.sink)
    device = {"name": dev.get("alias") or dev.get("name") or "Bluetooth kulaklık", "codec": snk.get("codec"),
              "rate": snk.get("rate"), "profile": snk.get("profile")}
    an = _an.Analyzer(_an.console_taps())
    from . import tones
    sess = consoleserver.Session(applier, on_commit, initial=state, analyzer=an, device=device,
                                 tone_player=tones.player(snk["name"]) if snk.get("present") else None,
                                 idle_timeout_s=int(_opt(args, "--idle-timeout", 3600)))
    if init:                                          # "açılışta" = kurulu olan durum, canlı aktarılan değil
        sess.default_json = json.dumps(console.sanitize(_latest_console_state() or console.default_state()), sort_keys=True)
    an.on_activity = lambda: setattr(sess, "last", time.time())   # izlenen analizör = etkinlik (boşta kapanma yok)
    sess._apply()                                     # canlı değer = başlangıç durumu (A/B geçişle)
    applier.apply_payload(console.loud_payload(console.load_loud_db()))   # U78: kurulu conf eski değeri taşıyabilir
    keep = _opt(args, "--profile", None)                 # sürüm geçişinde aktif çalışma kopyasını da koru
    if keep and sess.store.exists(keep):
        sess.load_profile(keep)
    from . import autoengine, classifier
    try:
        clf = classifier.YamnetClassifier()           # model yoksa available=False → yalnız öznitelik katmanı
    except Exception as e:                            # sınıflayıcı asla konsolu düşürmez
        clf = None
        print(f"sınıflayıcı yüklenemedi: {e}", file=sys.stderr)
    eng = autoengine.AutoEngine(sess, an, classifier=clf, state_path=paths.auto_state_path())
    _wire_abx(sess, eng)
    allow = [h for h in (_opt(args, "--allow-host", "") or "").split(",") if h]   # tailnet adı (tailscale serve → 127.0.0.1)
    try:                                              # varsayılan: servis portu (tek adres); doluysa rastgele port
        httpd, url, stop = consoleserver.serve(sess, port=probe, allow_hosts=allow)
    except OSError:
        if port_arg:
            raise
        httpd, url, stop = consoleserver.serve(sess, port=0, allow_hosts=allow)
    print(url, flush=True)
    if "--no-open" not in args:
        _open_url(url)
    stop.wait()
    eng.close(clear=True)                          # otomasyon ayarları diske, abonelik bırakılır, ADL katmanı kalkar
    if hasattr(applier, "wait_idle"):
        applier.wait_idle(3)                       # katmanın kalkışı (A/B geçiş) bitsin, sonra çık
    applier.close()                                # kalıcı pw-cli oturumu `quit` ile kapanır (E23: EOF'ta dönüyordu)
    an.close()                                     # yakalama alt süreçleri sunucuyla birlikte kapanır
    return 0


def _wire_abx(sess, eng):
    """PRD-BTA05 E1: konsoldaki kör test — gerçek codec değiştirici (pactl profil), çalar (pw-play → kulaklık, EQ yolu
    aynı), kaydedici (EQ ÖNCESİ dokunuş: effect_input monitörü, codec'ten önce dijital)."""
    import subprocess
    from . import abx, abxsession, analyzer, procs

    class _Play:
        def __init__(self, wav):
            snk = collect._safe(collect.sink)
            self.p = procs.spawn(["pw-play", "--target", snk.get("name", ""), wav],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def wait(self, timeout=None):
            return self.p.wait(timeout=timeout)

        def stop(self):
            if self.p.poll() is None:
                self.p.terminate()

    def record(path, seconds):
        node = analyzer._unique("abxclip")
        r = procs.spawn(["pw-record", "-P", f'{{ node.name = "{node}" node.autoconnect = false node.passive = true }}',
                         "--format", "f32", "--rate", "48000", "--channels", "2", path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            analyzer._link(analyzer.console_taps()["pre"]["ports"], node)
            time.sleep(seconds + 0.6)
        finally:
            r.terminate()
            r.wait(timeout=5)

    def on_apply(d):
        dec = _decision()
        ev = d["evidence"]
        dec.update({"codec": d["codec"], "profile": abx.PROFILES[d["codec"]], "decided_at": ev["at"],
                    "status": "konsol kör testiyle kullanıcı kararı",
                    "evidence": f"{ev['correct']}/{ev['n']} doğru, p={ev['p_value']}"})
        with open(DECISION, "w") as f:
            json.dump(dec, f, indent=2, ensure_ascii=False)
            f.write("\n")

    def env():
        others = [s.get("app") for s in collect.streams_to_sink() if s.get("state") == "running" and s.get("app") != "pw-play"]
        return {"other_audio": others}

    state_root = os.path.join(os.path.dirname(paths.auto_state_path()), "abx")
    sess.abx = abxsession.AbxSession(switcher=abx._set_codec, player=_Play,
                                     current_codec=lambda: collect._safe(collect.sink).get("codec"),
                                     results_dir=os.path.join(state_root, "results"), automation=eng, on_apply=on_apply)
    sess.abx_recorder = record if collect._safe(collect.sink).get("present") else None
    brahms = os.path.join(collect.REPO, "analysis", "tmp", "brahms1-48k-45s.wav")
    sess.abx_default_clip = (lambda: abx.excerpt(brahms, 2.0, 12.0)) if os.path.exists(brahms) else None
    sess.abx_env = env


def cmd_model(args):
    """bta model verify|fetch — yerel sınıflayıcı (YAMNet ONNX, Apache-2.0). İndirilen dosya models.lock.json
    sha256'sıyla doğrulanmadan kabul edilmez; uymazsa silinir."""
    from . import classifier
    sub = args[0] if args else "verify"
    if sub == "fetch":
        try:
            res = classifier.fetch()
        except Exception as e:
            print(f"indirme reddedildi: {e}")
            return 1
    elif sub == "verify":
        res = classifier.verify()
    else:
        print("kullanım: bta model verify|fetch")
        return 2
    print(f"konum: {classifier.model_dir()}")
    for fn, st in res.items():
        print(f"  {fn}: {st}")
    return 0 if all(v == "ok" for v in res.values()) else 1


def cmd_bass_off(args):
    rel = "pipewire/filter-chain.conf.d/60-bta-bass-eq.conf"
    for base in (collect.CONFIG_SRC, paths.generated_dir(), collect.CONFIG_DST):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            bdir = os.path.join(BACKUP_DIR, f"bass-off-{_dt.datetime.now():%Y%m%d-%H%M%S}")
            os.makedirs(bdir, exist_ok=True)
            shutil.copy2(p, os.path.join(bdir, os.path.basename(p) + (".installed" if base == collect.CONFIG_DST else ".src")))
            os.remove(p)
    _restart_services(["filter-chain.service"])
    print(f"bas EQ kaldırıldı (yedek: {BACKUP_DIR}/bass-off-*)")
    return 0


def cmd_btmon_report(args):
    from . import btmon
    path = args[0]
    lines = btmon.read_btsnoop(path)
    h = btmon.dominant_handle(lines)
    rep = {"file": path, "audio_handle": h, "trace": btmon.parse_trace(lines, audio_handle=h)}
    rs = path.replace(".btsnoop", ".rssi.txt")
    if os.path.exists(rs):
        rep["rssi"] = btmon.parse_rssi(open(rs).read().splitlines())
    with open(path.replace(".btsnoop", ".report.json"), "w") as f:
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


def cmd_apply_pending(args):
    cfg = collect.configs()
    mt = {rel: os.path.getmtime(os.path.join(collect.CONFIG_DST, rel)) for rel, v in cfg.items() if v["status"] == "ok"}
    pend = pending_restarts(mt, service_start_times())
    svc = sorted({s for _, s in pend})
    if not svc:
        print("bekleyen yok")
        return 0
    playing = [s["app"] for s in collect.streams_to_sink() if s.get("state") == "running"]
    if playing and "--force" not in args:
        print(f"ŞU AN ÇALAN VAR: {playing} → yeniden başlatma bir anlık kesinti yapar. Durdurup tekrar dene "
              "veya --force ekle.")
        return 4
    print(f"yeniden başlatılıyor: {svc}")
    _restart_services(svc)
    return cmd_check([])


def render_service_unit(bta_path):
    """U76: otomatik mod arka plan servisi (systemd kullanıcı birimi). Tarayıcı açmaz, boşta kapanmaz."""
    return f"""# bt-audio-hifi (PRD-BTA06 G1) — ÜRETİLMİŞ DOSYA: `bta service install` yazar, elle düzenleme.
[Unit]
Description=bt-audio-hifi konsolu (otomatik mod + canli EQ, 127.0.0.1:{SERVICE_PORT})
After=pipewire.service wireplumber.service filter-chain.service
Wants=pipewire.service wireplumber.service filter-chain.service

[Service]
Type=simple
ExecStart={bta_path} console --no-open --port {SERVICE_PORT} --idle-timeout 0
Restart=on-failure
RestartSec=10
Nice=5
MemoryMax=400M

[Install]
WantedBy=default.target
"""


def _unit_path():
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"), "systemd", "user", SERVICE_UNIT)


def cmd_service(args):
    import subprocess as _sp
    act = args[0] if args else "status"
    sc = ["systemctl", "--user"]
    if act == "install":
        url = _existing_console(SERVICE_PORT)
        if url and _sp.run(sc + ["is-active", "--quiet", SERVICE_UNIT]).returncode != 0:
            import urllib.request                     # elle açılmış konsol portu tutuyor → nazikçe kapat (servis devralır)
            req = urllib.request.Request(url + "api/quit", data=b"{}", method="POST",
                                         headers={"Content-Type": "application/json", "Origin": url.rstrip("/")})
            urllib.request.urlopen(req, timeout=5).read()
            for _ in range(40):
                if not _existing_console(SERVICE_PORT):
                    break
                time.sleep(0.25)
        path = _unit_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bta = os.path.realpath(os.path.join(collect.REPO, "bin", "bta"))
        with open(path, "w") as f:
            f.write(render_service_unit(bta))
        _sp.run(sc + ["daemon-reload"], check=True)
        _sp.run(sc + ["enable", "--now", SERVICE_UNIT], check=True)
        print(f"kuruldu: {path}")
    elif act == "uninstall":
        _sp.run(sc + ["disable", "--now", SERVICE_UNIT])
        if os.path.exists(_unit_path()):
            os.remove(_unit_path())
        _sp.run(sc + ["daemon-reload"])
        print("kaldırıldı")
    elif act != "status":
        print("kullanım: bta service install|uninstall|status", file=sys.stderr)
        return 2
    r = _sp.run(sc + ["is-active", SERVICE_UNIT], capture_output=True, text=True)
    url = _existing_console(SERVICE_PORT)
    print(f"servis: {r.stdout.strip() or 'yok'} · konsol: {url or 'cevap yok'}")
    return 0 if act != "status" or url else 1


COMMANDS = {"service": cmd_service, "console": cmd_console, "model": cmd_model, "bass-tune": cmd_bass_tune, "apply-pending": cmd_apply_pending, "btmon-report": cmd_btmon_report, "bass-analyze": cmd_bass_analyze, "bass-apply": cmd_bass_apply, "bass-off": cmd_bass_off, "abx": cmd_abx, "bench": cmd_bench, "link-test": cmd_link_test, "snapshot": cmd_snapshot, "diff": cmd_diff, "status": cmd_status, "check": cmd_check,
            "install": cmd_install, "uninstall": cmd_uninstall, "codec": cmd_codec}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    return COMMANDS[argv[0]](argv[1:])
