# バグ探索用テスト

`test_adversarial_models.py` は、公式 case pack を読み込み、contract に適合する
入力を検証してから、モデルの結果を独立したビット列の期待値と比較します。
丸めモードの検証では、公式ケースを元に回帰期待値付きの検証用契約を明示的に作成します。
両 fixture が同じモデルを使うために見逃すバグを対象にしています。
期待値の計算には、対象モデルもホストの浮動小数点演算も使いません。

プロジェクトのルートで実行します。追加の Python 依存関係はありません。

```sh
.venv/bin/python -m unittest discover -s tests -p test_adversarial_models.py -v
```

## 拡張後の結果

arm64 Darwin / Python 3.14.7 で **171パターンの出力不一致**を再現しました。
初回の36件に、丸めモード未反映の135件が追加されています。
出力照合は1,516件、テストは出力検証17メソッドとoracle出典の整合性検証1メソッドです。
不一致件数はバグの個数ではありません。根本原因はNaNの符号・NaN payload選択・
丸めモード未反映の3系統で、最後の系統が5つの実装経路に現れています。

| 検出した差 | 不一致パターン | 契約の範囲 |
|---|---:|---|
| 無効演算のNaN符号 | 12 | 公式 nearest-even |
| NaN payload の選択 | 24 | 公式 nearest-even |
| 算術で指定した丸めが反映されない | 56 | 検証用の丸め拡張 |
| 平方根で指定した丸めが反映されない | 8 | 検証用の丸め拡張 |
| 浮動小数点→整数で指定した丸めが反映されない | 37 | 検証用の丸め拡張 |
| f64→f32で指定した丸めが反映されない | 16 | 検証用の丸め拡張 |
| 整数→浮動小数点で指定した丸めが反映されない | 18 | 検証用の丸め拡張 |

丸めを変えた場合の具体例：

| 操作・指定 | 入力 | SSE2期待値 | 現モデル |
|---|---|---|---|
| f32 add / toward_positive | `0x3f800000 + 0x33000000` | `0x3f800001` | `0x3f800000` |
| f32 sqrt / toward_positive | `0x40000000` (=2) | `0x3fb504f4` | `0x3fb504f3` |
| f32→i32 / toward_negative | `0x3fc00000` (=1.5) | `0x00000001` | `0x00000002` |
| f64→f32 / toward_positive | `0x3ff0000010000000` | `0x3f800001` | `0x3f800000` |
| i32→f32 / toward_positive | `0x01000001` (=16,777,217) | `0x4b800001` | `0x4b800000` |

原因箇所は `casepack_families.py` の `float_binary_case`、`sqrt_case`、
`conversion_case`、`scalar_conversion_case`、`float_to_scalar_case` の実行経路です。
入力の `environment.rounding` を使用せず、ホストの演算やnearest-even固定の補助関数を使います。
公式ケースの宣言はnearest-evenのまま変更していません。この135件は、対応モードを
拡張する際の再現ケースであり、公式nearest-evenで同じ差が出るという主張ではありません。

504組の丸め基準値は `tests/data/rounding-oracles.json` に保存しています。
Pythonモデルを一切呼ばない `tests/build_rounding_oracles.py` がSSE2 probeから取得しました。
4モードの正負、halfway、underflow、overflow、整数境界、scalar上位レーンを検証します。
nearest-evenと、丸めモードに影響されないcvttは対照ケースです。
同じ504組はstrict FPの `-O0` / `-O2` ビルドで再取得し、一致を確認しました。

さらに6種類のbitcastで全128ビットを1ビットずつ移動する768照合と、
3種類のunaligned storeでoffset 0〜15と未使用buffer・前後guardを確認する48照合も追加しました。
これら816照合では不一致は出ていません。

## 初回に確認したNaNの不一致

arm64 macOS の Python で、10テストメソッド中4つが失敗し、6つが成功しました。
失敗した subtest は36件で、原因は次の2種類です。実装の修正は含めていません。

| 入力例（f64） | SSE2の期待値 | 現在のarm64モデル |
|---|---|---|
| `+inf + -inf` / `inf - inf` / `0 * inf` | `0xfff8000000000000` | `0x7ff8000000000000` |
| `0x7ff8000000000042 + 0x7ff0000000000001` | `0x7ff8000000000042` | `0x7ff8000000000001` |

1. 無効演算で生成する NaN の符号が違います。add / sub / mul、f32 / f64、
   packed / scalar の12組で再現します。
2. 第一引数が quiet NaN、第二引数が signaling NaN のとき、第二引数の payload が
   残ります。add / sub / mul、f32 / f64、packed / scalar と第一引数の正負を
   組み合わせた24組で再現します。div と、NaN の順序を逆にした対照ケースは成功します。

原因箇所は `src/ioitf/casepack_families.py` の `float_binary_case.execute` です。
add / sub / mul はビット列を Python の float に変換してホストで演算します。
これらの公式 contract は入力を除外せず `bit_exact` を要求するため、NaN 同士でも
この差は不一致です。両側が同じモデルを実行する通常の fixture 比較では見逃します。

`expectedFailure` や skip で失敗を隠していません。全体の unittest discover にも
含まれるため、未修正の arm64 環境では全体テストも非0で終了します。
ホスト依存のバグなので、x86_64 の Python では同じ失敗数になるとは限りません。

## レポートへの反映

```sh
.venv/bin/python -m ioitf check --quality --showcase-report
```

`showcase.html` の「独立したモデル検証と失敗箇所」に、モデル出力の不一致、その他の
assertion 失敗、テスト実行エラーを分けて表示します。fixture 比較が PASS でも、
quality 検証に失敗した場合は冒頭を `QUALITY CHECK FAILED` と表示します。
今回の未修正環境ではコマンドは非0で終了しますが、レポートは生成されます。
`--quality` を付けなかったレポートでは、独立したモデル検証は「未実施」です。

出力不一致は、公式または明示した検証用 contract に適合した入力でモデル実行が成功した後、
`ioitf.compare` を通さず固定期待値と直接照合した出力の差です。
**比較・集計処理の誤判定ではなく、Python portable model の出力不一致**として分類します。
このモデルもリポジトリ内の開発用実装であり、OpenPOWER 実機のバグが見つかったという
意味ではありません。また、今回の結果だけでフレームワーク全体の無欠陥を主張しません。

機械可読の記録は `quality/summary.json` の `gates.python_coverage` にあります。

- `failure_classification`: モデル不一致・その他の assertion 失敗・実行エラーの件数。
- `model_output_mismatches`: 各入力、入力ID、テストID、期待値、実測値、照合方法。
- `execution_environment`: 実際に検証した OS、CPU アーキテクチャ、Python バージョン。
- `evidence_sources`: oracle テストとモデル等のソースの SHA-256。
- `model_findings_by_family` / `model_findings_by_contract_scope`: 原因別と契約範囲別の件数。
- `model_oracle_checks_run`: 実施した出力照合数（テストメソッド数とは別）。
- `model_oracle_reference`: SSE2記録数、取得環境、probeと生成スクリプトのSHA-256。

NaN oracle の出典はこの文書の SSE2 probe 確認記録です。
quality 検証時には probe を再実行せず、固定した期待値を使用します。

保存した丸め基準値を独立に再確認するには、上記probeをビルドした後に実行します。

```sh
.venv/bin/python tests/build_rounding_oracles.py \
  --probe /tmp/ioitf-probe-sse2-nan \
  --execution-context 'x86_64 under Rosetta on arm64 Darwin' --verify
```

`--verify` は保存済み504組と再取得した結果の一致を確認します。
基準値の更新が必要な場合だけ `--verify` を外します。ソース変更後に古いoracleを
無言で使わないよう、通常テストでも取得元ソースのSHA-256を確認しています。

端末の品質メトリクスも、`tests_run` を `passed` と表示していた表記を
`executed` に修正しました。これは表示の問題で、上記36件のモデル出力の差とは
別の問題です。実行数と成功数を混同しないための修正です。

## 追加した境界条件

- min / max：±0 の入力順序、NaN の入力順序、第二引数の signaling NaN をそのまま返すこと。
- scalar 演算：上位レーンの signaling NaN、負のゼロ、payload をビット単位で保持すること。
- f64 → f32：丸め中間点の直前・一致・直後。偶数丸め、ゼロへの underflow、
  subnormal / normal 境界、overflow、負数、未使用レーンのゼロ化。
- 可変シフト：幅以上の count、`2^32`、`2^32 + 1`、`2^63`、`2^64 - 1`、
  count の上位64ビットを無視すること。
- `_mm_madd_epi16`：`(-32768 * -32768) * 2` が `0x80000000` に wrap することと、
  隣接するレーン対が混ざらないこと。

## NaN の期待値を SSE2 で確認する

`native/probe_sse2_nan.c` は、実行時に渡した入力で SSE2 intrinsic を直接呼びます。
FP例外は mask、丸めは nearest-even、FTZ / DAZ は無効に設定します。
Python モデルには依存しません。

Apple Silicon + Rosetta の場合：

```sh
clang -arch x86_64 -std=c11 -O0 -msse2 -ffp-model=strict \
  tests/native/probe_sse2_nan.c -o /tmp/ioitf-probe-sse2-nan
```

x86_64 上の Clang では `-arch x86_64` を外します。

```sh
/tmp/ioitf-probe-sse2-nan f64 add 0x7ff0000000000000 0xfff0000000000000
# 0xfff8000000000000
/tmp/ioitf-probe-sse2-nan f64 add 0x7ff8000000000042 0x7ff0000000000001
# 0x7ff8000000000042
/tmp/ioitf-probe-sse2-nan f32 mul 0x00000000 0x7f800000
# 0xffc00000
```

今回の期待値確認は Rosetta 上の x86_64 バイナリ実行です。
Intel / OpenPOWER 実機間の native conformance evidence ではありません。
通常の Python テスト実行にコンパイラや Rosetta は不要です。
