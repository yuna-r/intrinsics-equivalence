# Official SSE2 ↔ OpenPOWER cases

これはframework本体ではなく、独立したexample suiteです。1ケースはRubyのクラス1個に
近い単位として、1ディレクトリへまとめます。

現在は算術、乗算、飽和算術、平均/SAD、論理、比較、shift、pack、レーン操作を含む
146個のdevelopment case packが
あります。Native adapterの実装例は`_mm_add_pd`、`_mm_set1_pd`、
`_mm_shuffle_epi32`の3ケースです。

```text
10_official_suite/cases/<case-name>/
├── case.yaml       # 規範contract（署名、ISA、比較規則）
└── development.py  # 入力生成 + 非native executable model
```

`case.yaml`はYAML 1.2 JSON schemaの安全な部分だけを受理します。anchor、alias、merge
key、明示tag、重複key、浮動小数点numberは拒否されます。成果物のhashはYAMLの見た目では
なく、JSON data modelへ変換した値から計算されます。

## Rubyっぽい小さな塊

普通の2項vector演算なら、`development.py`に残るのは型、演算子、面白い入力だけです。
乱数、rounding、laneのdecode/encode、飽和、符号変換は共通部品へ畳みました。

```python
from ioitf.casepack_families import binary_case

EXAMPLES = (
    ((0, 1, 0xffffffff, 0x80000000), (1, 2, 1, 0xffffffff)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.add.i32x4.default", "i32x4", "+", EXAMPLES,
    standard=8,
)
```

使える短い演算子は`+ - & | ^ ~& == > < sat+ sat- avg min max *lo *hi`です。
case固有の意味があるときだけ、従来どおり`candidates`と`execute`を直接書けます。
つまり簡単なcaseは短く、難しいcaseを無理にマクロへ押し込めません。

generatorとdevelopment fixtureはこのファイルを自動発見するため、中央の`if case_id ==`
dispatchを変更する必要はありません。Intel/OpenPOWERのnative evidence adapterはCPUごとに
別コンパイルする安全境界なので、引き続き`adapters/`に置きます。

Native側の単純wrapperも[`../shortcuts.h`](../shortcuts.h)で1行です。

```c
IOITF_BINARY(i32x4, i32x4, intel_add_i32x4, _mm_add_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, power_add_i32x4, vec_add(a, b))
```

複雑なshuffleや変換は普通のC関数のままなので、開いたときに重要なコードだけが縦に
大きく見えます。


OpenPOWER / VSXの中心部分だけを先に眺めたい場合は、隣の
[`../openpower/`](../openpower/)に短いCコード例があります。
