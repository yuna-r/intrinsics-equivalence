# Official SSE2 ↔ OpenPOWER cases

これはframework本体ではなく、独立したexample suiteです。1ケースはRubyのクラス1個に
近い単位として、1ディレクトリへまとめます。

現在は算術、乗算、飽和算術、平均/SAD、論理、比較、shift、pack、レーン操作を含む
128個のdevelopment case packが
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

`development.py`は同じディレクトリの`case.yaml`にだけ対応し、次をexportします。

```python
CASE_ID = "sse2.example.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}  # profile prefixに必須の入力数（任意）

def candidates(case, *, seed_text):
    yield {...}

def execute(record):
    return {"return": {...}}
```

generatorとdevelopment fixtureはこのファイルを自動発見するため、中央の`if case_id ==`
dispatchを変更する必要はありません。Intel/OpenPOWERのnative evidence adapterはCPUごとに
別コンパイルする安全境界なので、引き続き`adapters/`に置きます。

OpenPOWER / VSXの中心部分だけを先に眺めたい場合は、隣の
[`../openpower/`](../openpower/)に短いCコード例があります。
