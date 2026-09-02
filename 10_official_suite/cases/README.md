# Official SSE2 ↔ OpenPOWER cases

これはframework本体ではなく、独立したexample suiteです。1ケースはRubyのクラス1個に
近い単位として、1ファイルへまとめます。

現在は算術、乗算、飽和算術、平均/SAD、論理、比較、shift、pack、レーン操作を含む
146個のportable model case packが
あります。Native adapterの実装例は`_mm_add_pd`、`_mm_set1_pd`、
`_mm_shuffle_epi32`の3ケースです。

```text
10_official_suite/cases/
├── add-f32x4.py
├── add-f64x2.py
├── add-i32x4.py
└── ...
```

各ファイルの`CASE_YAML`はYAML 1.2 JSON schemaの安全な部分だけを受理します。anchor、alias、merge
key、明示tag、重複key、浮動小数点numberは拒否されます。成果物のhashはYAMLの見た目では
なく、JSON data modelへ変換した値から計算されます。

## Rubyっぽい小さな塊

YAMLの直後に残るのはcase ID、型、演算だけです。乱数、境界値、rounding、laneの
decode/encode、飽和、符号変換は共通部品へ畳みました。

```python
CASE_YAML = """
schema_version: 1
id: sse2.add.i32x4.default
# signatureや比較規則がここに続く
"""

from ioitf.casepack_families import binary_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.add.i32x4.default", "i32x4", "+", standard=8)
```

使える短い演算子は`+ - & | ^ ~& == > < sat+ sat- avg min max *lo *hi`です。
変換は`conversion_case`、並べ替えは`lanes_case`、比較は`float_compare_case`、
shuffleは`shuffle_case`という小さなfamilyへ渡します。bit単位の変換oracleやNaN、
即値、unaligned buffer処理も共通部品側にあり、case packを開いた瞬間は要点だけ見えます。

新しい命令が既存familyに入らない場合は、まず小さなfamilyを1個足します。巨大な
長いmodelをcase packへ戻さないことはテストでも確認しています。

generatorとportable fixtureは`cases/*.py`を自動発見するため、中央の`if case_id ==`
dispatchを変更する必要はありません。Intel/OpenPOWERのnative evidence adapterはCPUごとに
別コンパイルする安全境界なので、引き続き`adapters/`に置きます。

contractを読むときはPythonを実行せず、ASTからliteralな`CASE_YAML`だけを抜き出します。
modelが必要になったときだけ同じファイルを実行します。従来の`case.yaml + model.py`形式も
互換性のため読み込めます。

結果JSONの`development_fixture: true`は互換用の成果物区分で、「実CPUで採取した
native evidenceではない」という意味です。case packのファイル名とは別の話です。

## 新しいcaseを1コマンドで作る

よくあるinteger vectorの2項演算なら、suite rootからこれだけです。

```sh
./10_official_suite/new-case demo-add-i32x4 +
```

`cases/demo-add-i32x4.py`が1個だけ作られます。既存ファイルは上書きしません。
生成後はIntel/OpenPOWERの同名native symbolを追加して`ioitf check`を
実行します。使える演算子は`./10_official_suite/new-case --help`で確認できます。

Native側の単純wrapperも[`../shortcuts.h`](../shortcuts.h)で1行です。

```c
IOITF_BINARY(i32x4, i32x4, intel_add_i32x4, _mm_add_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, power_add_i32x4, vec_add(a, b))
```

複雑なshuffleや変換は普通のC関数のままなので、開いたときに重要なコードだけが縦に
大きく見えます。


OpenPOWER / VSXの中心部分だけを先に眺めたい場合は、隣の
[`../openpower/`](../openpower/)に短いCコード例があります。
