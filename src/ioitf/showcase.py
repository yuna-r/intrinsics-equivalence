"""Self-contained, non-normative HTML showcase report."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, Mapping

from .canonical import JSONValue, atomic_write, dumps
from .cases import CaseDefinition
from .metrics import collect_verification_metrics


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


def _quality_section(quality: Mapping[str, JSONValue] | None) -> str:
    if quality is None:
        return '''<section class="panel oracle-report"><h2>独立したモデル検証：未実施</h2>
          <p>このレポートの一致率は両経路の比較結果です。同じ Python モデルを使う
          fixture 同士の一致だけでは、モデルの正しさは確認できません。
          <code>--quality --showcase-report</code> で独立した期待値との照合結果を表示できます。</p></section>'''
    gates = quality.get("gates", {})
    python = gates.get("python_coverage", {}) if isinstance(gates, dict) else {}
    classification = python.get("failure_classification", {})
    rows = python.get("model_output_mismatches", [])
    environment = python.get("execution_environment", {})
    scopes = python.get("model_findings_by_contract_scope", {})
    oracle_reference = python.get("model_oracle_reference") or {}
    family_labels = {
        "nan_indefinite_sign": "NaN の符号",
        "nan_payload_priority": "NaN payload の選択",
        "rounding_arithmetic": "丸めモード未反映：算術",
        "rounding_sqrt": "丸めモード未反映：平方根",
        "rounding_float_to_integer": "丸めモード未反映：浮動小数点 → 整数",
        "rounding_narrowing": "丸めモード未反映：f64 → f32",
        "rounding_integer_to_float": "丸めモード未反映：整数 → 浮動小数点",
    }
    family_rows = "".join(
        f'<div class="matrix-row"><span>{_text(family_labels.get(name, name))}</span><b>{_text(count)}</b></div>'
        for name, count in sorted(python.get("model_findings_by_family", {}).items())
    )
    findings = []
    for row in rows:
        record = row["input"]
        findings.append(f'''<details><summary>{_text(record["case_id"])} — {_text(record["input_id"])}</summary>
          <p>検証範囲：{_text(row.get("contract_scope", "未記録"))}。
          環境指定：{_text(dumps(record.get("environment", {})))}。</p>
          <p>入力</p><pre>{_text(dumps(record["operands"]))}</pre>
          <p>期待値（固定 SSE2 ビット列）</p><pre>{_text(dumps(row["expected"]))}</pre>
          <p>実測値（Python モデル）</p><pre>{_text(dumps(row["actual"]))}</pre>
          <small>{_text(row["test_id"])}</small></details>''')
    counts = "".join(
        f'<div class="matrix-row"><span>{label}</span><b>{_text(classification.get(key, "未集計"))}</b></div>'
        for key, label in (
            ("portable_model_output_mismatches", "モデル出力と期待値の不一致（入力パターン数）"),
            ("other_assertion_failures", "その他のテスト assertion 失敗"),
            ("test_execution_errors", "テスト実行エラー"),
        )
    )
    explanation = '''<p><strong>今回の不一致の対象は Python portable model の出力です。</strong>
      contract 検証とモデル実行が成功した後、比較エンジン <code>ioitf.compare</code> を
      通さず、出力のビット列を固定期待値と直接照合して検出しました。
      比較・集計処理の誤判定として検出されたものではありません。</p>
      <p>OpenPOWER 実機の不具合を示す結果ではありません。モデルはこのリポジトリに含まれる
      開発用実装です。この結果だけでフレームワーク全体にバグがないとは判断しません。</p>''' if rows else '''<p>モデル出力の不一致はこの実行では記録されていません。
      実施件数・その他の失敗・実行エラーも併せて確認してください。</p>'''
    gate_rows = "".join(
        f'<div class="matrix-row"><span>{_text(name)}</span><b>{_text(gate.get("status", "unknown"))}</b></div>'
        for name, gate in gates.items() if isinstance(gate, dict)
    )
    return f'''<section class="panel oracle-report" id="model-oracle">
      <div class="kicker">Independent model oracle / failure attribution</div>
      <h2>独立したモデル検証と失敗箇所</h2>
      {explanation}<div class="matrix">{counts}</div>
      <h3>検証範囲と不一致の内訳</h3>
      <p>公式 nearest-even 契約での不一致：{_text(scopes.get("official_nearest_even", "未集計"))}件。
      丸めモードを追加した検証用契約での不一致：{_text(scopes.get("validated_rounding_extension", "未集計"))}件。</p>
      <p>公式ケースの対応モードは変更していません。拡張契約にはSSE2の回帰期待値を登録し、
      contract 検証を通してから実行しています。拡張した契約自体もJSONの各不一致記録に保存しています。
      件数は不一致になった入力パターン数です。丸めの5経路は同じ原因の現れであり、別々の根本原因とは数えません。</p>
      <div class="matrix">{family_rows}</div>
      <p>モデル oracle テスト実施数：{_text(python.get("model_oracle_tests_run", "未集計"))} メソッド。
      独立した出力照合：{_text(python.get("model_oracle_checks_run", "未集計"))}件。
      実行環境：{_text(dumps(environment))}。</p>
      <p>期待値の出典：テスト内の固定ビット列と <code>tests/data/rounding-oracles.json</code> の
      SSE2実行結果{_text(oracle_reference.get("row_count", "未記録"))}組。
      取得環境：{_text(oracle_reference.get("execution_context", "未記録"))}。
      後者は4種類のMXCSR丸めモードで別プログラムから取得しています。
      NaN の期待値の事前確認手順と Rosetta での確認記録は <code>tests/BUG_HUNT.md</code> に記載しています。
      この quality 実行では probe を再実行していません。実機間の native evidence ではありません。</p>
      <div class="matrix">{gate_rows}</div>
      <details><summary>不一致の入力・期待値・実測値（{len(rows)}件）</summary>{"".join(findings)}</details>
      <p>機械可読の根拠：<code>quality/summary.json</code> の
      <code>gates.python_coverage</code>。入力ID、テストID、期待値、実測値、実行環境、
      検証に使ったソースの SHA-256 を保存しています。</p>
    </section>'''


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
    quality: Mapping[str, JSONValue] | None = None,
) -> str:
    """Render a portable report. All supplied text is escaped before insertion."""

    ordered_cases = tuple(cases)
    metrics = collect_verification_metrics(ordered_cases, summary)
    case_count = metrics.case_count
    record_count = metrics.trials
    matched = metrics.matched_inputs
    mismatched = metrics.mismatched_inputs
    not_comparable = metrics.not_comparable_inputs
    mismatch_atoms = metrics.mismatch_atoms
    outcome = str(summary["outcome"])
    rate_text = f"{metrics.match_rate:.2f}".rstrip("0").rstrip(".")
    vectors_each = metrics.vectors_per_case
    path_executions = metrics.implementation_path_evaluations
    lane_positions = metrics.lane_verdicts
    paired_bit_positions = metrics.bit_positions
    bit_exact_cases = sum(
        case.comparison["mode"] == "bit_exact" for case in ordered_cases
    )
    load_percent = max(0.0, min(100.0, vectors_each / 1000 * 100))
    load_text = f"{load_percent:.2f}".rstrip("0").rstrip(".")
    meter_value = min(vectors_each, 1000)
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
        "pass": "Every observed lane completed the equivalence comparison without divergence.",
        "mismatch": "At least one observed lane returned a divergent result.",
        "not_comparable": "One or more signals could not be compared safely.",
    }.get(outcome, "Verification sequence completed.")
    headline_outcome = outcome
    if quality is not None and quality.get("status") != "pass":
        status_class = "mismatch"
        status_title = "QUALITY CHECK FAILED"
        headline_outcome = "quality_failed"
        status_copy = f"Paired comparison: {outcome}. Independent quality checks failed; see failure attribution."
    quality_section = _quality_section(quality)
    evidence_label = "NATIVE EVIDENCE" if native_evidence else "DEVELOPMENT SIMULATION"
    evidence_copy = (
        "Results were captured from architecture-specific native runners."
        if native_evidence
        else "Portable development fixtures were used. This is not CPU-native evidence."
    )
    lane_metric_label = (
        "LANE VERDICTS" if outcome == "pass" else "MATRIX LANE POSITIONS"
    )
    output_metric_label = (
        "BIT-EXACT POSITIONS"
        if outcome == "pass" and case_count > 0 and bit_exact_cases == case_count
        else "PAIRED OUTPUT-BIT POSITIONS"
    )
    intel_path_copy = (
        "x86_64 // NATIVE RUNNER"
        if native_evidence
        else "SSE2 SEMANTICS // DEV FIXTURE"
    )
    power_path_copy = (
        "ppc64le // NATIVE RUNNER"
        if native_evidence
        else "VSX SEMANTICS // DEV FIXTURE"
    )
    observatory_label = (
        "CROSS-ARCHITECTURE OBSERVATORY"
        if native_evidence
        else "SEMANTIC EQUIVALENCE OBSERVATORY"
    )
    hero_copy = (
        "A deterministic signal crossed two native architectures. Every observable bit returned to the same coordinate."
        if native_evidence
        else "A deterministic signal crossed paired development fixtures. Every comparable bit returned to the same coordinate."
    )
    trial_label = (
        "DETERMINISTIC CROSS-ARCH TRIALS"
        if native_evidence
        else "DETERMINISTIC PAIRED-FIXTURE TRIALS"
    )
    path_activity_label = (
        "PATH EXECUTIONS" if native_evidence else "FIXTURE PATH EVALUATIONS"
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
    @keyframes load-rise {{
      from {{ opacity: .2; transform: scaleY(0); }}
      to {{ opacity: 1; transform: scaleY(1); }}
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
    .load-spectrum-section {{
      margin-top: 0;
      border: 1px solid var(--line);
      border-top: 0;
      background:
        linear-gradient(90deg, rgba(124,247,255,.05) 1px, transparent 1px),
        linear-gradient(rgba(124,247,255,.05) 1px, transparent 1px),
        linear-gradient(135deg, rgba(20,63,121,.72), rgba(67,42,132,.58) 58%, rgba(17,101,151,.5));
      background-size: 34px 34px, 34px 34px, auto;
    }}
    .load-spectrum-layout {{
      min-height: 740px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(300px, .42fr);
    }}
    .density-ledger {{ padding: clamp(34px, 6vw, 72px); background: linear-gradient(145deg, rgba(20,48,101,.28), rgba(70,40,132,.2)); }}
    .density-title {{ margin-top: 10px; max-width: 720px; }}
    .density-copy {{
      max-width: 680px;
      margin: 20px 0 38px;
      color: #c0d8e9;
      font: 15px/1.75 var(--display);
      letter-spacing: .025em;
    }}
    .density-evidence {{
      display: inline-block;
      margin-bottom: 16px;
      padding: 9px 11px;
      border: 1px solid var(--amber);
      color: var(--amber);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .18em;
      text-transform: uppercase;
    }}
    .load-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 11px; }}
    .load-cell {{
      --cell-accent: var(--cyan);
      position: relative;
      min-height: 132px;
      padding: 22px;
      border: 1px solid rgba(174,217,255,.24);
      border-top: 3px solid var(--cell-accent);
      background: linear-gradient(135deg, rgba(27,69,133,.72), rgba(48,37,105,.64));
      overflow: hidden;
    }}
    .load-cell::after {{
      content: attr(data-channel);
      position: absolute;
      top: 9px;
      right: 10px;
      color: rgba(124,247,255,.2);
      font-size: 8px;
      letter-spacing: .16em;
    }}
    .load-cell:nth-child(2) {{ --cell-accent: #70ffd1; background: linear-gradient(135deg, rgba(26,91,116,.72), rgba(35,58,123,.64)); }}
    .load-cell:nth-child(3) {{ --cell-accent: #a991ff; background: linear-gradient(135deg, rgba(52,57,137,.72), rgba(76,42,126,.64)); }}
    .load-cell:nth-child(4) {{ --cell-accent: #e7f66b; background: linear-gradient(135deg, rgba(64,88,119,.72), rgba(69,55,118,.64)); }}
    .load-cell:nth-child(5) {{ --cell-accent: #73a7ff; background: linear-gradient(135deg, rgba(37,75,142,.72), rgba(57,42,125,.64)); }}
    .load-cell:nth-child(6) {{ --cell-accent: #ff9d42; background: linear-gradient(135deg, rgba(78,77,118,.72), rgba(77,48,113,.64)); }}
    .load-cell.primary {{ grid-column: 1 / -1; min-height: 164px; background: linear-gradient(120deg, rgba(25,96,149,.82), rgba(57,51,145,.72), rgba(23,115,147,.7)); }}
    .load-cell strong {{
      display: block;
      margin-top: 14px;
      color: var(--text);
      font: 780 clamp(34px, 5vw, 62px)/.9 var(--display);
      letter-spacing: -.025em;
    }}
    .load-cell.primary strong {{ color: var(--ok); font-size: clamp(48px, 7vw, 86px); text-shadow: 0 0 30px rgba(115,255,210,.16); }}
    .load-cell span {{ color: var(--cyan); font-size: 8px; letter-spacing: .2em; text-transform: uppercase; }}
    .load-cell small {{ display: block; margin-top: 13px; color: #6f879a; font-size: 9px; line-height: 1.5; letter-spacing: .08em; text-transform: uppercase; }}
    .load-cell.divergence strong {{ color: var(--ok); }}
    .mismatch .load-cell.divergence strong {{ color: var(--red); text-shadow: 0 0 24px rgba(255,94,122,.22); }}
    .density-note {{
      margin: 24px 0 0;
      padding-left: 13px;
      border-left: 1px solid var(--amber);
      color: #a8c3d9;
      font-size: 9px;
      line-height: 1.65;
      letter-spacing: .09em;
      text-transform: uppercase;
    }}
    .load-chart-panel {{
      min-height: 740px;
      padding: 38px 28px 34px;
      display: flex;
      flex-direction: column;
      align-items: center;
      border-left: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(32,66,127,.8), rgba(60,42,126,.74));
    }}
    .load-chart-label {{ align-self: stretch; color: var(--amber); font-size: 8px; letter-spacing: .23em; text-align: center; text-transform: uppercase; }}
    .load-profile {{
      margin-top: 14px;
      padding: 6px 9px;
      border: 1px solid rgba(124,247,255,.28);
      color: var(--cyan);
      font-size: 8px;
      letter-spacing: .18em;
      text-transform: uppercase;
    }}
    .load-chart {{ --load-level: 0%; width: min(360px, 100%); margin: 30px auto 18px; }}
    .load-chart-frame {{ --plot-height: 470px; height: var(--plot-height); display: grid; grid-template-columns: 54px minmax(0, 1fr); }}
    .load-y-axis {{ position: relative; border-right: 2px solid rgba(237,250,255,.74); }}
    .load-axis-label {{
      position: absolute;
      right: 10px;
      bottom: var(--level);
      transform: translateY(50%);
      color: #c0d8e9;
      font-size: 9px;
      letter-spacing: .08em;
    }}
    .load-plot {{ position: relative; border-bottom: 2px solid rgba(237,250,255,.74); overflow: hidden; background: rgba(39,64,126,.3); }}
    .load-gridline {{ position: absolute; right: 0; bottom: var(--level); left: 0; border-top: 1px solid rgba(199,225,255,.22); }}
    .load-bar {{
      position: absolute;
      bottom: 0;
      left: 18%;
      width: 46%;
      height: var(--load-level);
      transform-origin: bottom;
      background: linear-gradient(to top, #58e9ff 0%, #70ffd1 38%, #e7f66b 70%, #ff9d42 100%);
      background-position: bottom;
      background-size: 100% var(--plot-height);
      box-shadow: 8px 0 0 rgba(124,247,255,.08);
      animation: load-rise .8s cubic-bezier(.2,.7,.2,1) both;
    }}
    .load-bar::after {{ content: ""; position: absolute; inset: 0; border: 1px solid rgba(237,250,255,.42); }}
    .load-marker {{ position: absolute; right: 0; bottom: var(--load-level); left: 0; border-top: 2px solid var(--text); box-shadow: 0 0 12px rgba(237,250,255,.28); }}
    .load-marker span {{ position: absolute; top: 8px; right: 0; padding: 5px 7px; border-left: 2px solid var(--text); background: rgba(45,56,123,.9); color: var(--text); font-size: 8px; letter-spacing: .12em; }}
    .load-x-label {{ margin-top: 13px; color: #c0d8e9; font-size: 9px; letter-spacing: .22em; text-align: center; }}
    .load-readout {{ text-align: center; }}
    .load-readout strong {{ display: block; color: var(--amber); font: 800 48px/.9 var(--display); text-shadow: 0 0 24px rgba(255,203,107,.16); }}
    .load-readout span {{ display: block; margin-top: 9px; color: #bdd4e6; font-size: 8px; letter-spacing: .2em; }}
    .load-baseline {{ margin-top: 14px; color: #a8c3d9; font-size: 8px; line-height: 1.55; letter-spacing: .12em; text-align: center; text-transform: uppercase; }}
    .load-spectrum-key {{ width: min(260px, 100%); height: 5px; margin-top: auto; background: linear-gradient(90deg, #58e9ff, #70ffd1, #e7f66b, #ff9d42); box-shadow: 0 0 12px rgba(112,255,209,.2); }}
    section {{ margin-top: 74px; }}
    section.load-spectrum-section {{ margin-top: 0; }}
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
      .load-spectrum-layout {{ grid-template-columns: 1fr; }}
      .load-chart-panel {{ min-height: 650px; border-top: 1px solid var(--line); border-left: 0; }}
      .split, .evidence {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 580px) {{
      .shell {{ width: min(100% - 20px, 1240px); padding-top: 10px; }}
      .chrome {{ align-items: flex-start; flex-direction: column; }}
      .hero {{ padding: 44px 20px; }}
      h1 {{ font-size: 49px; }}
      .metrics, .case-grid {{ grid-template-columns: 1fr; }}
      .density-ledger {{ padding: 42px 20px; }}
      .load-grid {{ grid-template-columns: 1fr; }}
      .load-cell.primary {{ grid-column: auto; }}
      .load-chart-panel {{ padding-right: 18px; padding-left: 18px; }}
      .load-chart-frame {{ --plot-height: 420px; grid-template-columns: 48px minmax(0, 1fr); }}
      .metric, .metric:nth-child(2) {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .metric:last-child {{ border-bottom: 0; }}
      .routes {{ grid-template-columns: 1fr; }}
      .route-beam {{ height: 46px; width: 1px; margin: 0 auto; }}
      .section-head, footer {{ align-items: flex-start; flex-direction: column; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; }}
    }}
    .oracle-report p {{ line-height: 1.8; overflow-wrap: anywhere; }}
    .oracle-report details {{ margin-top: 18px; }}
    .oracle-report summary {{ cursor: pointer; overflow-wrap: anywhere; }}
    .oracle-report pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font-size: 12px; }}
    .oracle-report small {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body class="{_text(status_class)}">
  <main class="shell">
    <div class="chrome">
      <div class="chrome-left"><span class="lights"><i></i><i></i><i></i></span> IOITF // {_text(observatory_label)}</div>
      <div>REPORT {_text(report_id)} // {_text(generated_text)}</div>
    </div>

    <header class="hero">
      <div>
        <div class="eyebrow">Operation Nightglass</div>
        <h1>Intrinsic <span>Equivalence</span></h1>
        <p class="lede">{_text(hero_copy)}</p>
        <div class="status-line">{_text(status_title)} // {_text(headline_outcome).upper()}</div>
      </div>
      <div class="core-wrap" aria-label="Equivalence coherence visualization">
        <div class="core">
          <div class="orbit one"></div><div class="orbit two"></div><div class="orbit three"></div>
          <div class="core-label"><strong>{_text(rate_text)}%</strong><span>PAIRED COMPARISON</span></div>
        </div>
      </div>
    </header>

    {quality_section}

    <div class="metrics">
      <div class="metric" data-code="A-01"><strong>{case_count}</strong><span>Intrinsic cases</span></div>
      <div class="metric" data-code="V-02"><strong>{record_count}</strong><span>Signals transmitted</span></div>
      <div class="metric" data-code="M-03"><strong>{matched}</strong><span>Signals aligned</span></div>
      <div class="metric" data-code="D-04"><strong>{mismatched + not_comparable}</strong><span>Anomalies observed</span></div>
    </div>

    <section class="load-spectrum-section" aria-labelledby="load-spectrum-title">
      <div class="load-spectrum-layout">
        <div class="density-ledger">
          <div class="kicker">Test load spectrum</div>
          <h2 class="density-title" id="load-spectrum-title">Verification density</h2>
          <p class="density-copy">A deterministic workload was evaluated across paired paths, then resolved at lane and bit-position granularity. These counts are derived from the canonical record stream and declared return-vector shapes.</p>
          <div class="density-evidence">{_text(evidence_label)}</div>
          <div class="load-grid">
            <div class="load-cell primary" data-channel="LOAD-01">
              <span>{_text(trial_label)}</span>
              <strong>{record_count:,}</strong>
              <small>Canonical input records presented to the paired equivalence comparison</small>
            </div>
            <div class="load-cell" data-channel="PATH-02">
              <span>{_text(path_activity_label)}</span>
              <strong>{path_executions:,}</strong>
              <small>Two implementation-path observations per deterministic trial</small>
            </div>
            <div class="load-cell" data-channel="LANE-03">
              <span>{_text(lane_metric_label)}</span>
              <strong>{lane_positions:,}</strong>
              <small>Declared return lanes multiplied by vectors per case</small>
            </div>
            <div class="load-cell" data-channel="BIT-04">
              <span>{_text(output_metric_label)}</span>
              <strong>{paired_bit_positions:,}</strong>
              <small>Observed output bits compared as paired positions at declared element width</small>
            </div>
            <div class="load-cell" data-channel="MODE-05">
              <span>Bit-exact contracts</span>
              <strong>{bit_exact_cases:,}</strong>
              <small>Cases whose comparison mode requires exact output representation</small>
            </div>
            <div class="load-cell divergence" data-channel="DIV-00">
              <span>Divergence atoms</span>
              <strong>{mismatch_atoms:,}</strong>
              <small>{not_comparable:,} non-comparable inputs reported independently</small>
            </div>
          </div>
          <p class="density-note">Workload counts do not expand the evidence boundary. The capture classification above identifies whether these observations came from native runners or development fixtures.</p>
        </div>
        <aside class="load-chart-panel" aria-label="Test load spectrum graph">
          <div class="load-chart-label">Standard load scale // 1,000 vectors per case</div>
          <div class="load-profile">Profile // {_text(str(profile).upper())}</div>
          <div class="load-chart" role="meter" aria-label="Verification density by vectors per case" aria-valuemin="0" aria-valuemax="1000" aria-valuenow="{meter_value}" aria-valuetext="{vectors_each:,} vectors per case; standard load scale {_text(load_text)} percent" style="--load-level:{_text(load_text)}%">
            <div class="load-chart-frame">
              <div class="load-y-axis" aria-hidden="true">
                <span class="load-axis-label" style="--level:100%">1000</span>
                <span class="load-axis-label" style="--level:75%">750</span>
                <span class="load-axis-label" style="--level:50%">500</span>
                <span class="load-axis-label" style="--level:25%">250</span>
                <span class="load-axis-label" style="--level:0%">0</span>
              </div>
              <div class="load-plot" aria-hidden="true">
                <i class="load-gridline" style="--level:100%"></i>
                <i class="load-gridline" style="--level:75%"></i>
                <i class="load-gridline" style="--level:50%"></i>
                <i class="load-gridline" style="--level:25%"></i>
                <i class="load-gridline" style="--level:0%"></i>
                <div class="load-bar"></div>
                <div class="load-marker"><span>ACTUAL // {vectors_each:,}</span></div>
              </div>
            </div>
            <div class="load-x-label">VECTORS / CASE</div>
          </div>
          <div class="load-readout"><strong>{vectors_each:,}</strong><span>ACTUAL VECTORS / CASE</span></div>
          <div class="load-baseline">Load density {_text(load_text)}% // 1,000 vectors per case = standard</div>
          <div class="load-spectrum-key" aria-hidden="true"></div>
          <div class="load-baseline">Cyan → green → yellow → orange load spectrum<br>Failure indication remains red</div>
        </aside>
      </div>
    </section>

    <section>
      <div class="section-head">
        <div><div class="kicker">Transmission topology</div><h2>Dual-path verification</h2></div>
        <div class="section-code">PROFILE {_text(str(profile).upper())}<br>SEED {_text(seed)}</div>
      </div>
      <div class="split">
        <div class="panel routes">
          <div class="route-node"><b>INTEL</b><small>{_text(intel_path_copy)}</small></div>
          <div class="route-beam"></div>
          <div class="route-node"><b>OPENPOWER</b><small>{_text(power_path_copy)}</small></div>
        </div>
        <div class="panel">
          <div class="panel-label">Integrity matrix</div>
          <div class="matrix">
            <div class="matrix-row"><span>Case contracts</span><b>LOCKED</b></div>
            <div class="matrix-row"><span>Vector stream</span><b>DETERMINISTIC</b></div>
            <div class="matrix-row"><span>Matched inputs</span><b>{matched:04d}</b></div>
            <div class="matrix-row"><span>Mismatch atoms</span><b>{mismatch_atoms:04d}</b></div>
            <div class="matrix-row"><span>Comparison outcome</span><b>{_text(outcome).upper()}</b></div>
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
    quality: Mapping[str, JSONValue] | None = None,
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
        quality=quality,
    )
    atomic_write(path, html.encode("utf-8"))
    return path
