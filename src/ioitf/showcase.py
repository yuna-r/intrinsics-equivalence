"""Self-contained, non-normative HTML showcase report."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import JSONValue, atomic_write
from .cases import CaseDefinition


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _shape(value: object) -> str:
    if not isinstance(value, dict):
        return "unknown"
    kind = str(value.get("type", "unknown"))
    element = str(value.get("element", ""))
    if kind == "vector":
        return f"{element} × {value.get('lanes', '?')}"
    if element:
        return f"{kind} / {element}"
    return kind


def _signature(case: CaseDefinition) -> str:
    signature = case.signature
    arguments = signature["arguments"]
    assert isinstance(arguments, list)
    argument_shapes = []
    for argument in arguments:
        assert isinstance(argument, dict)
        argument_shapes.append(f"{argument['name']}: {_shape(argument)}")
    return f"{' · '.join(argument_shapes)} → {_shape(signature['return'])}"


def _case_cards(cases: tuple[CaseDefinition, ...], vectors_each: int) -> str:
    cards: list[str] = []
    for index, case in enumerate(cases, start=1):
        description = case.data["description"]
        comparison = case.comparison["mode"]
        intel = case.data["intel"]
        openpower = case.data["openpower"]
        assert isinstance(intel, dict) and isinstance(openpower, dict)
        intel_isa = intel["required_isa"]
        power_isa = openpower["required_isa"]
        assert isinstance(intel_isa, list) and isinstance(power_isa, list)
        isa = " / ".join(str(item).upper() for item in intel_isa + power_isa)
        cards.append(
            f"""
            <article class="case-card" style="--delay:{index * 70}ms">
              <div class="case-index">CASE // {index:02d}</div>
              <h3>{_text(case.id)}</h3>
              <p>{_text(description)}</p>
              <div class="signature">{_text(_signature(case))}</div>
              <div class="case-meta">
                <span>{_text(comparison).upper()}</span>
                <span>{vectors_each} VECTORS</span>
                <span>{_text(isa)}</span>
              </div>
            </article>"""
        )
    return "".join(cards)


def render_showcase_html(
    *,
    cases: Iterable[CaseDefinition],
    summary: Mapping[str, JSONValue],
    profile: str,
    seed: str,
    vector_sha256: str,
    case_definitions_sha256: str,
    isa_contract_sha256: str,
    generated_at: datetime,
    native_evidence: bool,
) -> str:
    """Render a portable report. All supplied text is escaped before insertion."""

    ordered_cases = tuple(cases)
    case_count = len(ordered_cases)
    record_count = int(summary["record_count"])
    matched = int(summary["matched_inputs"])
    mismatched = int(summary["mismatched_inputs"])
    not_comparable = int(summary["not_comparable_inputs"])
    mismatch_atoms = int(summary["mismatch_atoms"])
    outcome = str(summary["outcome"])
    match_rate = 100.0 if record_count == 0 else matched * 100.0 / record_count
    rate_text = f"{match_rate:.2f}".rstrip("0").rstrip(".")
    vectors_each = record_count // case_count if case_count else 0
    generated_text = generated_at.strftime("%Y-%m-%d // %H:%M:%S UTC")
    report_id = case_definitions_sha256[:12].upper()
    status_class = {
        "pass": "pass",
        "mismatch": "mismatch",
        "not_comparable": "incomplete",
    }.get(outcome, "incomplete")
    status_title = {
        "pass": "COHERENCE CONFIRMED",
        "mismatch": "DIVERGENCE DETECTED",
        "not_comparable": "SIGNAL INCOMPLETE",
    }.get(outcome, outcome.upper())
    status_copy = {
        "pass": "Every observed lane returned through the equivalence gate without divergence.",
        "mismatch": "At least one observed lane crossed the gate with a divergent result.",
        "not_comparable": "One or more signals could not be compared safely.",
    }.get(outcome, "Verification sequence completed.")
    evidence_label = "NATIVE EVIDENCE" if native_evidence else "DEVELOPMENT SIMULATION"
    evidence_copy = (
        "Results were captured from architecture-specific native runners."
        if native_evidence
        else "Portable development fixtures were used. This is not CPU-native evidence."
    )
    cards = _case_cards(ordered_cases, vectors_each)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>IOITF // {_text(status_title)}</title>
  <style>
    :root {{
      --void: #03050b;
      --panel: rgba(9, 14, 28, .76);
      --panel-solid: #090e1c;
      --line: rgba(143, 244, 255, .18);
      --cyan: #7cf7ff;
      --blue: #6685ff;
      --violet: #bc7cff;
      --amber: #ffcb6b;
      --red: #ff5e7a;
      --text: #edfaff;
      --muted: #8296aa;
      --ok: #73ffd2;
      --display: "Arial Narrow", "Avenir Next Condensed", "Roboto Condensed", sans-serif;
      --mono: "SFMono-Regular", "Cascadia Code", "Roboto Mono", Consolas, monospace;
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--void); scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-width: 320px;
      color: var(--text);
      background:
        radial-gradient(circle at 80% 4%, rgba(102,133,255,.2), transparent 32rem),
        radial-gradient(circle at 8% 32%, rgba(188,124,255,.13), transparent 28rem),
        linear-gradient(145deg, #02040a 0%, #060b17 48%, #03050b 100%);
      font-family: var(--mono);
      overflow-x: hidden;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .32;
      background-image:
        linear-gradient(rgba(124,247,255,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,247,255,.035) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, black, transparent 88%);
    }}
    body::after {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .05;
      background: repeating-linear-gradient(0deg, transparent 0 3px, #fff 4px);
      animation: scan 12s linear infinite;
    }}
    @keyframes scan {{ to {{ transform: translateY(24px); }} }}
    @keyframes pulse {{ 50% {{ opacity: .35; transform: scale(.96); }} }}
    @keyframes orbit {{ to {{ transform: rotate(360deg); }} }}
    @keyframes reveal {{
      from {{ opacity: 0; transform: translateY(14px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .shell {{ width: min(1240px, calc(100% - 36px)); margin: 0 auto; padding: 28px 0 64px; }}
    .chrome {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding: 11px 15px;
      border: 1px solid var(--line);
      border-bottom-color: rgba(124,247,255,.42);
      background: rgba(4,8,16,.8);
      color: var(--muted);
      font-size: 10px;
      letter-spacing: .18em;
      text-transform: uppercase;
    }}
    .chrome-left {{ display: flex; align-items: center; gap: 12px; }}
    .lights {{ display: flex; gap: 6px; }}
    .lights i {{ width: 6px; height: 6px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 9px var(--cyan); }}
    .lights i:nth-child(2) {{ background: var(--violet); box-shadow: 0 0 9px var(--violet); }}
    .lights i:nth-child(3) {{ background: var(--amber); box-shadow: 0 0 9px var(--amber); }}
    .hero {{
      position: relative;
      min-height: 540px;
      display: grid;
      grid-template-columns: 1.18fr .82fr;
      align-items: center;
      gap: 32px;
      padding: clamp(44px, 7vw, 90px) clamp(22px, 6vw, 72px);
      border: 1px solid var(--line);
      border-top: 0;
      overflow: hidden;
      background: linear-gradient(120deg, rgba(5,9,19,.96), rgba(10,16,34,.68));
    }}
    .hero::before {{
      content: "IOITF / NIGHTGLASS / IOITF / NIGHTGLASS";
      position: absolute;
      right: -7rem;
      bottom: -1.4rem;
      color: rgba(124,247,255,.035);
      font: 900 72px/1 var(--display);
      letter-spacing: .06em;
      white-space: nowrap;
    }}
    .eyebrow {{ color: var(--cyan); font-size: 11px; letter-spacing: .28em; text-transform: uppercase; }}
    .eyebrow::before {{ content: ""; display: inline-block; width: 32px; height: 1px; margin-right: 12px; vertical-align: middle; background: var(--cyan); box-shadow: 0 0 9px var(--cyan); }}
    h1 {{ margin: 22px 0 16px; font: 800 clamp(48px, 8vw, 104px)/.84 var(--display); letter-spacing: -.045em; text-transform: uppercase; }}
    h1 span {{ display: block; color: transparent; -webkit-text-stroke: 1px rgba(237,250,255,.68); }}
    .lede {{ max-width: 650px; color: #b6c8d7; font: 400 clamp(15px, 1.7vw, 19px)/1.75 var(--display); letter-spacing: .035em; }}
    .status-line {{ display: flex; align-items: center; gap: 12px; margin-top: 34px; color: var(--ok); font-size: 12px; letter-spacing: .15em; }}
    .status-line::before {{ content: ""; width: 9px; height: 9px; border: 1px solid currentColor; border-radius: 50%; background: currentColor; box-shadow: 0 0 18px currentColor; animation: pulse 1.8s ease-in-out infinite; }}
    .mismatch .status-line {{ color: var(--red); }}
    .incomplete .status-line {{ color: var(--amber); }}
    .core-wrap {{ min-height: 360px; display: grid; place-items: center; }}
    .core {{ position: relative; width: min(330px, 72vw); aspect-ratio: 1; display: grid; place-items: center; }}
    .orbit {{ position: absolute; border: 1px solid rgba(124,247,255,.38); border-radius: 50%; box-shadow: inset 0 0 24px rgba(124,247,255,.06), 0 0 28px rgba(102,133,255,.07); }}
    .orbit::after {{ content: ""; position: absolute; top: -4px; left: 50%; width: 8px; height: 8px; border-radius: 50%; background: var(--cyan); box-shadow: 0 0 18px 3px var(--cyan); }}
    .orbit.one {{ inset: 2%; animation: orbit 13s linear infinite; }}
    .orbit.two {{ inset: 15%; border-style: dashed; animation: orbit 9s linear reverse infinite; }}
    .orbit.three {{ inset: 28%; border-color: rgba(188,124,255,.7); animation: orbit 6s linear infinite; }}
    .core-label {{ width: 36%; aspect-ratio: 1; display: grid; place-content: center; text-align: center; border: 1px solid var(--cyan); border-radius: 50%; background: #07101c; box-shadow: 0 0 45px rgba(124,247,255,.28), inset 0 0 30px rgba(124,247,255,.12); }}
    .core-label strong {{ font: 800 28px/1 var(--display); }}
    .core-label span {{ margin-top: 7px; color: var(--cyan); font-size: 7px; letter-spacing: .18em; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--line); border-top: 0; background: rgba(6,10,20,.8); }}
    .metric {{ position: relative; padding: 26px 28px; border-right: 1px solid var(--line); overflow: hidden; }}
    .metric:last-child {{ border-right: 0; }}
    .metric::after {{ content: attr(data-code); position: absolute; right: 9px; top: 8px; color: rgba(124,247,255,.16); font-size: 9px; }}
    .metric strong {{ display: block; font: 700 clamp(28px, 4vw, 46px)/1 var(--display); }}
    .metric span {{ display: block; margin-top: 9px; color: var(--muted); font-size: 9px; letter-spacing: .19em; text-transform: uppercase; }}
    section {{ margin-top: 74px; }}
    .section-head {{ display: flex; align-items: end; justify-content: space-between; gap: 22px; margin-bottom: 22px; }}
    .kicker {{ color: var(--violet); font-size: 9px; letter-spacing: .26em; text-transform: uppercase; }}
    h2 {{ margin: 8px 0 0; font: 750 clamp(28px, 5vw, 56px)/1 var(--display); letter-spacing: -.025em; text-transform: uppercase; }}
    .section-code {{ color: #53697d; font-size: 9px; letter-spacing: .16em; text-align: right; }}
    .split {{ display: grid; grid-template-columns: 1.15fr .85fr; gap: 18px; }}
    .panel {{ position: relative; padding: 28px; border: 1px solid var(--line); background: var(--panel); backdrop-filter: blur(14px); overflow: hidden; }}
    .panel::before {{ content: ""; position: absolute; left: 0; top: 0; width: 54px; height: 1px; background: var(--cyan); box-shadow: 0 0 12px var(--cyan); }}
    .panel-label {{ color: var(--cyan); font-size: 9px; letter-spacing: .2em; text-transform: uppercase; }}
    .routes {{ display: grid; grid-template-columns: 1fr 58px 1fr; align-items: center; gap: 8px; min-height: 190px; }}
    .route-node {{ padding: 20px; border: 1px solid rgba(124,247,255,.2); background: rgba(4,8,16,.58); }}
    .route-node b {{ display: block; margin-bottom: 8px; font: 700 22px/1 var(--display); }}
    .route-node small {{ color: var(--muted); font-size: 9px; letter-spacing: .12em; }}
    .route-beam {{ position: relative; height: 1px; background: linear-gradient(90deg, var(--blue), var(--cyan), var(--violet)); box-shadow: 0 0 10px var(--cyan); }}
    .route-beam::after {{ content: "≡"; position: absolute; left: 50%; top: 50%; transform: translate(-50%,-50%); width: 28px; height: 28px; display: grid; place-items: center; border: 1px solid var(--cyan); border-radius: 50%; background: #08101b; color: var(--cyan); }}
    .matrix {{ display: grid; gap: 11px; margin-top: 20px; }}
    .matrix-row {{ display: grid; grid-template-columns: 1fr auto; gap: 16px; padding-bottom: 11px; border-bottom: 1px solid rgba(124,247,255,.1); font-size: 11px; }}
    .matrix-row span {{ color: #9cb0c2; }}
    .matrix-row b {{ color: var(--ok); letter-spacing: .09em; }}
    .case-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .case-card {{ position: relative; min-height: 236px; padding: 26px; border: 1px solid var(--line); background: linear-gradient(145deg, rgba(12,19,37,.86), rgba(5,9,19,.88)); animation: reveal .6s both; animation-delay: var(--delay); overflow: hidden; }}
    .case-card::after {{ content: ""; position: absolute; width: 120px; height: 120px; right: -72px; bottom: -72px; border: 1px solid rgba(188,124,255,.35); transform: rotate(45deg); }}
    .case-index {{ color: var(--violet); font-size: 9px; letter-spacing: .2em; }}
    .case-card h3 {{ margin: 17px 0 10px; font: 700 clamp(18px, 2.4vw, 28px)/1.05 var(--display); letter-spacing: -.01em; overflow-wrap: anywhere; }}
    .case-card p {{ min-height: 42px; color: var(--muted); font: 14px/1.5 var(--display); }}
    .signature {{ margin-top: 20px; padding: 11px 13px; border-left: 2px solid var(--cyan); background: rgba(124,247,255,.045); color: #bed8e2; font-size: 10px; overflow-wrap: anywhere; }}
    .case-meta {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 15px; }}
    .case-meta span {{ padding: 5px 7px; border: 1px solid rgba(124,247,255,.18); color: #7892a7; font-size: 7px; letter-spacing: .11em; }}
    .evidence {{ display: grid; grid-template-columns: .72fr 1.28fr; gap: 18px; }}
    .evidence-state {{ display: flex; flex-direction: column; justify-content: space-between; min-height: 310px; }}
    .evidence-state strong {{ display: block; margin: 18px 0 10px; font: 750 34px/.95 var(--display); color: var(--amber); }}
    .evidence-state p {{ color: var(--muted); font: 14px/1.6 var(--display); }}
    .stamp {{ align-self: flex-start; padding: 8px 10px; border: 1px solid var(--amber); color: var(--amber); font-size: 8px; letter-spacing: .18em; transform: rotate(-1deg); }}
    .hashes {{ display: grid; gap: 18px; }}
    .hash {{ padding-bottom: 16px; border-bottom: 1px solid rgba(124,247,255,.1); }}
    .hash:last-child {{ border: 0; padding-bottom: 0; }}
    .hash span {{ display: block; margin-bottom: 8px; color: var(--cyan); font-size: 8px; letter-spacing: .16em; }}
    .hash code {{ display: block; color: #a9bac8; font-size: 10px; line-height: 1.6; word-break: break-all; }}
    footer {{ margin-top: 64px; padding: 22px 0; display: flex; justify-content: space-between; gap: 22px; border-top: 1px solid var(--line); color: #53697d; font-size: 8px; letter-spacing: .14em; text-transform: uppercase; }}
    @media (max-width: 820px) {{
      .hero {{ grid-template-columns: 1fr; min-height: auto; }}
      .core-wrap {{ min-height: 280px; }}
      .core {{ width: 260px; }}
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
      .metric:nth-child(2) {{ border-right: 0; }}
      .metric:nth-child(-n+2) {{ border-bottom: 1px solid var(--line); }}
      .split, .evidence {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 580px) {{
      .shell {{ width: min(100% - 20px, 1240px); padding-top: 10px; }}
      .chrome {{ align-items: flex-start; flex-direction: column; }}
      .hero {{ padding: 44px 20px; }}
      h1 {{ font-size: 49px; }}
      .metrics, .case-grid {{ grid-template-columns: 1fr; }}
      .metric, .metric:nth-child(2) {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .metric:last-child {{ border-bottom: 0; }}
      .routes {{ grid-template-columns: 1fr; }}
      .route-beam {{ height: 46px; width: 1px; margin: 0 auto; }}
      .section-head, footer {{ align-items: flex-start; flex-direction: column; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; }}
    }}
  </style>
</head>
<body class="{_text(status_class)}">
  <main class="shell">
    <div class="chrome">
      <div class="chrome-left"><span class="lights"><i></i><i></i><i></i></span> IOITF // CROSS-ARCHITECTURE OBSERVATORY</div>
      <div>REPORT {_text(report_id)} // {_text(generated_text)}</div>
    </div>

    <header class="hero">
      <div>
        <div class="eyebrow">Operation Nightglass</div>
        <h1>Intrinsic <span>Equivalence</span></h1>
        <p class="lede">A deterministic signal crossed two architectures. Every observable bit returned to the same coordinate.</p>
        <div class="status-line">{_text(status_title)} // {_text(outcome).upper()}</div>
      </div>
      <div class="core-wrap" aria-label="Equivalence coherence visualization">
        <div class="core">
          <div class="orbit one"></div><div class="orbit two"></div><div class="orbit three"></div>
          <div class="core-label"><strong>{_text(rate_text)}%</strong><span>COHERENCE</span></div>
        </div>
      </div>
    </header>

    <div class="metrics">
      <div class="metric" data-code="A-01"><strong>{case_count}</strong><span>Intrinsic cases</span></div>
      <div class="metric" data-code="V-02"><strong>{record_count}</strong><span>Signals transmitted</span></div>
      <div class="metric" data-code="M-03"><strong>{matched}</strong><span>Signals aligned</span></div>
      <div class="metric" data-code="D-04"><strong>{mismatched + not_comparable}</strong><span>Anomalies observed</span></div>
    </div>

    <section>
      <div class="section-head">
        <div><div class="kicker">Transmission topology</div><h2>Dual-path verification</h2></div>
        <div class="section-code">PROFILE {_text(profile).upper()}<br>SEED {_text(seed)}</div>
      </div>
      <div class="split">
        <div class="panel routes">
          <div class="route-node"><b>INTEL</b><small>x86_64 // SSE2 PATH</small></div>
          <div class="route-beam"></div>
          <div class="route-node"><b>OPENPOWER</b><small>ppc64le // VSX PATH</small></div>
        </div>
        <div class="panel">
          <div class="panel-label">Integrity matrix</div>
          <div class="matrix">
            <div class="matrix-row"><span>Case contracts</span><b>LOCKED</b></div>
            <div class="matrix-row"><span>Vector stream</span><b>DETERMINISTIC</b></div>
            <div class="matrix-row"><span>Matched inputs</span><b>{matched:04d}</b></div>
            <div class="matrix-row"><span>Mismatch atoms</span><b>{mismatch_atoms:04d}</b></div>
            <div class="matrix-row"><span>Gate outcome</span><b>{_text(outcome).upper()}</b></div>
          </div>
        </div>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="kicker">Active payloads</div><h2>Case constellation</h2></div>
        <div class="section-code">{case_count:02d} CONTRACTS<br>{vectors_each:03d} VECTORS / CASE</div>
      </div>
      <div class="case-grid">{cards}</div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="kicker">Evidence boundary</div><h2>Cryptographic trace</h2></div>
        <div class="section-code">SHA-256<br>FULL-LENGTH IDENTIFIERS</div>
      </div>
      <div class="evidence">
        <div class="panel evidence-state">
          <div>
            <div class="panel-label">Capture classification</div>
            <strong>{_text(evidence_label)}</strong>
            <p>{_text(evidence_copy)}</p>
          </div>
          <div class="stamp">NON-NORMATIVE SHOWCASE VIEW</div>
        </div>
        <div class="panel hashes">
          <div class="hash"><span>TEST VECTOR STREAM</span><code>{_text(vector_sha256)}</code></div>
          <div class="hash"><span>CASE DEFINITION CONTRACT</span><code>{_text(case_definitions_sha256)}</code></div>
          <div class="hash"><span>USED ISA CONTRACT</span><code>{_text(isa_contract_sha256)}</code></div>
        </div>
      </div>
    </section>

    <footer>
      <span>INTRINSICS-EQUIVALENCE // IOITF</span>
      <span>{_text(status_copy)}</span>
      <span>SOURCE OF TRUTH: CANONICAL JSON ARTIFACTS</span>
    </footer>
  </main>
</body>
</html>
"""


def write_showcase_report(
    output: str | Path,
    *,
    cases: Iterable[CaseDefinition],
    summary: Mapping[str, JSONValue],
    profile: str,
    seed: str,
    vector_sha256: str,
    case_definitions_sha256: str,
    isa_contract_sha256: str,
    generated_at: datetime,
    native_evidence: bool,
) -> Path:
    """Atomically write the optional presentation-only HTML report."""

    path = Path(output)
    html = render_showcase_html(
        cases=cases,
        summary=summary,
        profile=profile,
        seed=seed,
        vector_sha256=vector_sha256,
        case_definitions_sha256=case_definitions_sha256,
        isa_contract_sha256=isa_contract_sha256,
        generated_at=generated_at,
        native_evidence=native_evidence,
    )
    atomic_write(path, html.encode("utf-8"))
    return path
