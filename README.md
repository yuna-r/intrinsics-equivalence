# intrinsics-equivalence

![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab?style=flat&logo=python&logoColor=white)
![C](https://img.shields.io/badge/C-native-a8b9cc?style=flat&logo=c&logoColor=black)
![Status](https://img.shields.io/badge/status-early_development-f59e0b?style=flat)
[![MIT License](https://img.shields.io/badge/license-MIT-2ea44f?style=flat)](LICENSE)

Intel IntrinsicsとOpenPOWER側の互換実装へ同じ入力を渡し、結果の違いを見つけるための
テストツールです。成果物は厳密に扱いつつ、普段の確認は短いコマンドで済むようにしています。

現在のexample suiteは`_mm_add_pd`、`_mm_set1_pd`、`_mm_shuffle_epi32`を収録しています。

> **Status:** まだ開発初期です。ローカルの比較フローとportable adapterは動きますが、
> x86_64 / ppc64le実機runnerは未完成です。

Original concept: [@daisukeokaoss](https://github.com/daisukeokaoss)

## Quick start

Python 3.11以上を使います。

```sh
git clone https://github.com/yuna-r/intrinsics-equivalence.git
cd intrinsics-equivalence

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

ioitf check
```

成功すると、次のような結果が返ります。

```json
{"artifacts":".ioitf/checks/...","case_count":3,"development_fixture":true,"native_evidence":false,"record_count":24,"status":"pass"}
```

`ioitf check`は、case定義の検証、入力生成、Intel/OpenPOWER用development fixtureの実行、
結果比較までをまとめて行います。成果物は`.ioitf/checks/<timestamp>/`に残ります。

ここで使うfixtureはローカル確認用です。`native_evidence: false`が示すとおり、
Intel/POWER実機で動作した証拠にはなりません。

macOSの`/usr/bin/python3`が古い場合は、Homebrewなどで入れたPython 3.11以上を
仮想環境の作成に使ってください。

## 仕組み

```text
case pack ──> test vectors ──┬──> Intel result
                             └──> OpenPOWER result
                                      │
                                      ▼
                                   compare
                                      │
                         summary / JUnit / failure bundle
```

frameworkとテストsuiteは分けてあります。

```text
intrinsics-equivalence/
├── src/ioitf/             # CLIとartifact処理
├── adapters/              # native / portable adapter
├── contracts/             # ISA registry
├── examples/sse2/         # example suite
├── tests/                 # framework自身のテスト
└── ioitf.toml             # 使用するsuiteの指定
```

## テストケースを追加する

似ている既存ケースをコピーするのが一番早いです。

```sh
cp -R examples/sse2/add-f64x2 examples/sse2/my-new-case
```

1ケースは1つのcase packとしてまとまっています。

```text
examples/sse2/my-new-case/
├── case.yaml
└── development.py
```

### 1. `case.yaml`を書く

ここにはcase ID、引数、戻り値、必要ISA、比較方法を書きます。

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

YAMLとJSONの両方を読めます。YAMLではanchor、alias、merge key、明示tag、重複key、
浮動小数点numberを受け付けません。

### 2. `development.py`へ入力と期待動作を書く

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

`ioitf`が`case.yaml`の隣にあるファイルを自動で見つけます。中央のgeneratorやfixtureへ
case IDの分岐を追加する必要はありません。実例は
[`examples/sse2/README.md`](examples/sse2/README.md)と各case packを参照してください。

### 3. 確認する

```sh
ioitf check
```

特定のproject fileを使う場合:

```sh
ioitf check --project ../my-intrinsics/ioitf.toml
```

project file内の相対パスは、その`ioitf.toml`がある場所を基準に解決されます。

### 4. Native対応を加える場合

development checkだけならcase packの2ファイルで動きます。実機で検証するケースへ進める場合は、
次も追加します。

- `adapters/intel/`: Intel Intrinsicを呼ぶ実装
- `adapters/openpower/`: OpenPOWER互換実装を呼ぶ実装
- `adapters/portable/`: ホストで確認できる補助実装
- `include/framework/example_cases.h`: 公開C symbol
- `tests/native/test_native.c`: ABIと代表入力のテスト

IntelとOpenPOWERのコードは、それぞれの対象CPU上で別々にビルド・実行します。

## Framework側のテストを追加する

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

ケースを追加したときは、最低でも次の3種類が通ることを確認します。

```sh
ioitf check
python -m unittest discover -s tests -v
cmake --build build/native --parallel
ctest --test-dir build/native --output-on-failure
```

arm64 macOSではportable adapterのみ、Linux x86_64ではIntel adapter、ppc64leでは
OpenPOWER adapterも対象になります。詳しくは[NATIVE_STATUS.md](NATIVE_STATUS.md)を参照してください。

<details>
<summary>個別コマンドとfailure bundle</summary>

### 個別コマンド

工程を分けて確認したい場合も、同じ`ioitf.toml`が使われます。

```sh
ioitf validate-cases

ioitf generate-vectors \
  --output artifacts/vectors \
  --count-per-case 8
```

生成したvectorをdevelopment fixtureへ渡す例:

```sh
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

### 不一致を再確認する

不一致が見つかると、`<output>/failures/<input_id>/`へその入力だけのfailure bundleを
保存します。別ホストで取り直した結果は`verify-replay`で照合できます。

```sh
ioitf verify-replay \
  --failure artifacts/comparison/failures/$INPUT_ID/failure.json \
  --intel replay/intel/intel-results.manifest.json \
  --openpower replay/openpower/power-results.manifest.json
```

`--failure`には`failure.json`またはbundleディレクトリを指定できます。相対パスは
bundleディレクトリを基準に解決されます。

#### Failure bundleで検証するもの

- canonical JSON / JSONLと閉じたschema
- bundle内ファイルのSHA-256と相互参照
- case contract、input ID、used ISA contract
- Intel / OpenPOWER両方の基準結果
- 保存された不一致件数と最初の差分
- bundle外へ出るpathやsymlinkの拒否

development fixtureの成果物を使う場合は`--allow-development-fixtures`が必要です。
この指定を付けてもnative evidenceにはなりません。

</details>

## 現在の制限

- Linux x86_64 / ppc64le実機runnerとCPU feature detectorは未完成です。
- MXCSR、FPSCR、VSCR probeと共有ライブラリの動的ロード監査は未完成です。
- ppc64le adapterは対応toolchainと実機での確認が残っています。
- 実機SUTを単一入力で動かすnative `ioitf replay`は未実装です。
- traceability / coverage artifactは未実装です。
- 現在の3ケースはFP例外観測を無効にしています。

## 終了コード

- `0`: 一致、または検証・生成成功
- `1`: 比較結果の不一致
- `2`: case定義や入力のエラー
- `3`: 必要なISAや機能が利用できない
- `4`: runnerまたは成果物の異常
- `5`: Intel回帰oracleエラー

## 仕様と設計メモ

- [IOITF specification](docs/doc/intel-openpower-intrinsics-equivalence-test-framework-spec.md)
- [読みやすい解説版](docs/doc/intel-openpower-intrinsics-equivalence-test-framework-spec-for-everyone.md)
- [Native implementation status](NATIVE_STATUS.md)

ホスト間ではcanonical JSON / JSONLだけを交換します。`__m128i`やOpenPOWERのvector型など、
CPU固有型の生バイト列は共通形式に使いません。
