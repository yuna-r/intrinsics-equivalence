# intrinsics-equivalence

`IOITF-SPEC-001`（1.1.0-draft）を実装するための初期版です。現段階では、CPUに依存しないコーディネーター部分を先に完成させています。

実装済み:

- RFC 8785で必要になるUTF-16 code-unit順を含む、整数限定のcanonical JSON
- JSON安全整数、重複キー、非canonical JSON/JSONLの拒否
- 閉じたcase schema、ISA registry、used ISA contractの検証とSHA-256
- 決定的な入力生成、`input_id`、入力manifest
- 丸めwitnessの回帰ID昇格、同一入力のnearest-even対、およびIntel oracle検査
- 結果manifestとpreflight projectionの検証
- `bit_exact`、`ieee_value`、`ulp`、`abs_rel`、`classification`比較
- status、戻り値、バッファ、メモリ契約、FP例外の原子単位比較
- summary、JUnit、単一入力failure bundle
- C ABI v1ヘッダーと、ホストでビルドできるnative自己テスト

登録済みの最初のケースは `_mm_add_pd`、`_mm_set1_pd`、`_mm_shuffle_epi32`
です。3ケースともIntel、OpenPOWER、開発用portableの公開Cシンボルを持ちます。

制限:

- case definitionは現在JSONのみです。JSONはYAML 1.2 JSON schemaの部分集合なので、仕様上有効な形式です。
- Linux x86_64/ppc64leの実機runner、CPU feature detector、MXCSR/FPSCR/VSCR probe、共有ライブラリの動的ロード監査は未完成です。
- ppc64le adapterはソース実装までで、対応toolchainと実機によるビルド・実行確認は未実施です。
- `fixture-run`は比較器を自己テストするための純粋Python実装です。IntelまたはPOWERの実機証拠ではありません。出力は`development-fixture:` build IDを持ち、比較時にも明示的な許可が必要です。
- `replay` / `verify-replay`、traceability/coverage成果物、YAML frontendは次段階です。
- `observe_fp_exceptions: true`でIntrinsicごとに発生可能な例外classを網羅したかは、
  schema v1に能力宣言がないためケース作者の一次資料レビューも必要です。登録された
  regressionの型、入力ID、Intel期待値は機械検証します。現行3ケースはすべて例外観測を無効にしています。

## クイックスタート

Python 3.11以上が必要です。このmacOS環境では`/usr/bin/python3`が3.9系のため、
HomebrewのPython 3.14で仮想環境を作ります。

```sh
cd intrinsics-equivalence
/opt/homebrew/bin/python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

python -m unittest discover -s tests -v

python -m ioitf validate-cases \
  --cases cases \
  --isa-registry cases/isa-registry.json

python -m ioitf generate-vectors \
  --cases cases \
  --isa-registry cases/isa-registry.json \
  --output artifacts/vectors \
  --count-per-case 8
```

開発fixtureを使ったend-to-end確認:

```sh
python -m ioitf fixture-run \
  --cases cases --isa-registry cases/isa-registry.json \
  --input artifacts/vectors/test-vectors.manifest.json \
  --role intel --output artifacts/intel \
  --i-understand-this-is-not-native-evidence

python -m ioitf fixture-run \
  --cases cases --isa-registry cases/isa-registry.json \
  --input artifacts/vectors/test-vectors.manifest.json \
  --role openpower --output artifacts/openpower \
  --i-understand-this-is-not-native-evidence

python -m ioitf compare-results \
  --cases cases --isa-registry cases/isa-registry.json \
  --input artifacts/vectors/test-vectors.manifest.json \
  --intel artifacts/intel/intel-results.manifest.json \
  --openpower artifacts/openpower/power-results.manifest.json \
  --output artifacts/comparison \
  --allow-development-fixtures
```

別のOSでは、利用可能な3.11以上のPythonで同じ仮想環境を作ってください。
インストールせずに実行する場合は各コマンドへ`PYTHONPATH=src`を付けます。

## Native自己テスト

```sh
cmake -S . -B build/native -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
ctest --test-dir build/native --output-on-failure
```

arm64 macOSではportable adapterだけをビルドします。x86_64ではSSE2 adapter、
ppc64leではVSX adapterも対象になります。portable adapterの成功は、実機間の
Intrinsic等価性を証明しません。詳細は[NATIVE_STATUS.md](NATIVE_STATUS.md)を参照してください。

## 終了コード

- `0`: 全比較一致、または検証/生成成功
- `1`: 比較可能な結果の不一致
- `2`: 仕様、入力、case定義のエラー
- `3`: 必須ISA・能力がunsupported
- `4`: runner成果物または実行の異常
- `5`: Intel回帰oracleエラー

## 設計上の境界

`ioitf` Python packageは、入力と成果物をホスト間で交換する規範層です。`include/framework/case_abi.h`とnative codeは各ホスト内でrunnerとadapterを結ぶ層です。ネイティブvector型や構造体の生バイト列をホスト間形式に使用しません。
