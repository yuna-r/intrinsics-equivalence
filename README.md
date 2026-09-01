# intrinsics-equivalence

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat&logo=python&logoColor=white)
![C](https://img.shields.io/badge/C-native-a8b9cc?style=flat&logo=c&logoColor=black)
![Status](https://img.shields.io/badge/status-early_development-f59e0b?style=flat)
[![MIT License](https://img.shields.io/badge/license-MIT-2ea44f?style=flat)](LICENSE)

**IntelとOpenPOWERに同じ問題を解かせて、答え合わせするツールです。**

同じ入力から結果の違いを見つけます。中ではかなり厳密に記録しますが、普段使う
コマンドは短くしてあります。

現在はadd、sub、mul、set1、shuffle、bitwise ANDの6ケースで遊べます。

> まだ開発初期です。ローカルの比較フローとportable adapterは動きますが、
> x86_64 / ppc64le実機runnerはこれからです。

Original concept: [@daisukeokaoss](https://github.com/daisukeokaoss)

## まずは動かす

```sh
git clone https://github.com/yuna-r/intrinsics-equivalence.git
cd intrinsics-equivalence

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

ioitf check
```

最後に`"status":"pass"`が出れば成功です。

```json
{"case_count":6,"record_count":48,"status":"pass"}
```

`ioitf check`ひとつで、caseの確認、入力生成、両側の実行、答え合わせまで進みます。
途中の記録は`.ioitf/checks/<timestamp>/`へ残ります。

> ここで動くのはローカル開発用fixtureです。CPU実機で一致した証拠ではありません。

## おまけ：SFレポート

ちょっと楽しいおまけとして、`--showcase-report`を付けると、いつもの成果物に
近未来SF風のHTMLレポートが加わります。

![Showcase report preview](assets/showcase-report-preview.svg)

```sh
ioitf check --showcase-report
```

実行結果の`showcase_report`が生成したファイルです。

```json
{"showcase_report":".ioitf/checks/.../showcase.html","status":"pass"}
```

外部画像やWebフォントを使わない1ファイル完結なので、そのままブラウザで開いたり
共有したりできます。

派手なのは見た目だけで、判定元はこれまでどおりcanonical JSON成果物です。

## ケースをひとつ増やす

似ているケースをコピーします。

```sh
cp -R examples/sse2/add-f64x2 examples/sse2/my-new-case
```

1ケースは、この小さな塊だけです。

```text
my-new-case/
├── case.yaml       # 名前、型、比較方法
└── development.py  # 入力と期待動作
```

2ファイルを直したら、いつものコマンドを実行します。

```sh
ioitf check
```

これでローカルのcase追加は完了です。中央の巨大なswitch文へcase IDを足す必要はありません。
実例は[`examples/sse2/`](examples/sse2/)にあります。

## 変更後の確認

普段はこの2つで大丈夫です。

```sh
ioitf check
python -m unittest discover -s tests -v
```

Native側を変更した場合だけ、Cのテストも実行します。

```sh
cmake -S . -B build/native -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
ctest --test-dir build/native --output-on-failure
```

## 必要になったら開くところ

ここから先は、いま必要な項目だけどうぞ。

<details>
<summary><strong>case.yamlとdevelopment.pyの書き方</strong></summary>

### `case.yaml`

case ID、引数、戻り値、必要ISA、比較方法を書きます。

```yaml
schema_version: 1
id: sse2.add.f64x2.default
description: two-lane IEEE 754 binary64 addition

intel:
  symbol: intel_mm_add_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_add_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f64, lanes: 2}

input_domain: {exclude: []}
comparison: {mode: bit_exact}
environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false
tags: []
```

### `development.py`

`candidates()`と`execute()`を同じファイルへ置きます。

```python
CASE_ID = "sse2.add.f64x2.default"
MINIMUM_COUNTS = {"standard": 10}

def candidates(case, *, seed_text):
    # 境界値や典型値を先にyieldし、その後に決定的なrandom入力を続ける
    yield {
        "environment": {"fp_mode": "ieee", "rounding": "nearest_even"},
        "generation": {"class": "structured"},
        "operands": {...},
    }

def execute(record):
    # development fixtureが使う、CPUに依存しない期待動作
    return {"return": {...}}
```

`ioitf`が隣り合う2ファイルを自動で見つけます。

### 浮動小数点は文字列にする

YAML自体は浮動小数点を扱えますが、このプロジェクトのcase定義では生の
浮動小数点numberを受け付けません。環境ごとの丸めや文字列化の違いを避け、
同じcaseから常に同じhashを作るためです。

```yaml
# NG: YAMLの浮動小数点number
abs_tolerance: 0.001

# OK: 正確に解釈できる10進文字列
abs_tolerance: "0.001"
rel_tolerance: "0"
```

具体的なf32/f64入力は`development.py`でIEEE 754の32/64-bit値として生成します。
`NaN`、無限大、`-0.0`もbit表現のまま扱えるため、値やNaN payloadを失いません。

YAMLではほかにanchor、alias、merge key、明示tag、重複keyも受け付けません。
JSON形式のcaseも読み込めます。

</details>

<details>
<summary><strong>実機で動くcaseへ育てる</strong></summary>

ローカル開発だけならcase packの2ファイルで動きます。実機検証へ進める場合は、
対象に応じて次を追加します。

- `adapters/intel/`: Intel Intrinsicを呼ぶ実装
- `adapters/openpower/`: OpenPOWER互換実装を呼ぶ実装
- `adapters/portable/`: ホストで確認できる補助実装
- `include/framework/example_cases.h`: 公開C symbol
- `tests/native/test_native.c`: ABIと代表入力のテスト

IntelとOpenPOWERのコードは、それぞれの対象CPU上で別々にビルド・実行します。
arm64 macOSではportable adapterのみ、Linux x86_64ではIntel adapter、ppc64leでは
OpenPOWER adapterも対象になります。

詳しくは[NATIVE_STATUS.md](NATIVE_STATUS.md)を参照してください。

</details>

<details>
<summary><strong>Framework側へテストを追加する</strong></summary>

変更した場所に近いファイルへ追加します。

- case schema、YAML、入力生成: `tests/test_cases_generator.py`
- project fileの読み込み: `tests/test_project.py`
- manifestとartifact検証: `tests/test_artifacts.py`
- 比較ルール: `tests/test_compare.py`
- CLIと一連の処理: `tests/test_end_to_end.py`
- failure bundleと再実行: `tests/test_replay.py`
- C ABIとadapter: `tests/native/test_native.c`

Python側は標準の`unittest`です。

```sh
python -m unittest discover -s tests -v
```

Native側:

```sh
cmake -S . -B build/native -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
ctest --test-dir build/native --output-on-failure
```

</details>

<details>
<summary><strong>中で何をしているのか</strong></summary>

```text
case pack ──> test vectors ──┬──> Intel result
                             └──> OpenPOWER result
                                      │
                                      ▼
                                   compare
                                      │
                         summary / JUnit / failure bundle
```

Frameworkとテストsuiteは分けてあります。

```text
intrinsics-equivalence/
├── src/ioitf/             # CLIとartifact処理
├── adapters/              # native / portable adapter
├── contracts/             # ISA registry
├── examples/sse2/         # example suite
├── tests/                 # framework自身のテスト
└── ioitf.toml             # 使用するsuiteの指定
```

特定のproject fileを使う場合:

```sh
ioitf check --project ../my-intrinsics/ioitf.toml
```

相対パスは、その`ioitf.toml`がある場所を基準に解決されます。

</details>

<details>
<summary><strong>工程をひとつずつ実行する</strong></summary>

```sh
ioitf validate-cases

ioitf generate-vectors \
  --output artifacts/vectors \
  --count-per-case 8

ioitf fixture-run \
  --input artifacts/vectors/test-vectors.manifest.json \
  --role intel --output artifacts/intel \
  --i-understand-this-is-not-native-evidence

ioitf fixture-run \
  --input artifacts/vectors/test-vectors.manifest.json \
  --role openpower --output artifacts/openpower \
  --i-understand-this-is-not-native-evidence

ioitf compare-results \
  --input artifacts/vectors/test-vectors.manifest.json \
  --intel artifacts/intel/intel-results.manifest.json \
  --openpower artifacts/openpower/power-results.manifest.json \
  --output artifacts/comparison \
  --allow-development-fixtures
```

インストールせずに試す場合は`PYTHONPATH=src python -m ioitf`を使えます。

</details>

<details>
<summary><strong>不一致を別のホストで再確認する</strong></summary>

不一致が見つかると、`<output>/failures/<input_id>/`へその入力だけのfailure bundleを
保存します。別ホストで取り直した結果は`verify-replay`で照合できます。

```sh
ioitf verify-replay \
  --failure artifacts/comparison/failures/$INPUT_ID/failure.json \
  --intel replay/intel/intel-results.manifest.json \
  --openpower replay/openpower/power-results.manifest.json
```

`--failure`には`failure.json`またはbundleディレクトリを指定できます。

Bundleは、ファイルのSHA-256、case contract、input ID、使用ISA、両方の基準結果、
不一致件数、最初の差分を検証します。bundle外へ出るpathやsymlinkも拒否します。

Development fixtureの成果物を使う場合は`--allow-development-fixtures`が必要です。
この指定を付けてもnative evidenceにはなりません。

</details>

<details>
<summary><strong>現在の制限と終了コード</strong></summary>

### 現在の制限

- Linux x86_64 / ppc64le実機runnerとCPU feature detectorは未完成です。
- MXCSR、FPSCR、VSCR probeと共有ライブラリの動的ロード監査は未完成です。
- ppc64le adapterは対応toolchainと実機での確認が残っています。
- 実機SUTを単一入力で動かすnative `ioitf replay`は未実装です。
- traceability / coverage artifactは未実装です。
- 現在のcase packはFP例外観測を無効にしています。

### 終了コード

- `0`: 一致、または検証・生成成功
- `1`: 比較結果の不一致
- `2`: case定義や入力のエラー
- `3`: 必要なISAや機能が利用できない
- `4`: runnerまたは成果物の異常
- `5`: Intel回帰oracleエラー

</details>

<details>
<summary><strong>インストールで詰まったとき</strong></summary>

Python 3.11以上が必要です。macOSの`/usr/bin/python3`が古い場合は、Homebrewなどで
入れたPythonから仮想環境を作成してください。

```sh
python3 --version
```

</details>

<details>
<summary><strong>仕様を読む</strong></summary>

- [まずはこちら: 読みやすい解説版](docs/doc/intel-openpower-intrinsics-equivalence-test-framework-spec-for-everyone.md)
- [IOITF specification](docs/doc/intel-openpower-intrinsics-equivalence-test-framework-spec.md)
- [Native implementation status](NATIVE_STATUS.md)

ホスト間ではcanonical JSON / JSONLだけを交換します。`__m128i`やOpenPOWERのvector型など、
CPU固有型の生バイト列は共通形式に使いません。

</details>
