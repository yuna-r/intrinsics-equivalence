# Examples

<p>
  <img alt="Intel SSE2" src="https://img.shields.io/badge/Intel-SSE2-0071c5?style=flat&amp;logo=intel&amp;logoColor=white">
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/SIMD-VSX-f7b500?style=flat">
  <img alt="24 cases" src="https://img.shields.io/badge/cases-24-7c4dff?style=flat">
</p>

同じSIMD処理を、contractとOpenPOWERコードの両方から眺められます。

```text
examples/
├── sse2/       24個のIntel ↔ OpenPOWER equivalence case
└── openpower/  読んですぐ分かる3つのVSXコード例
```

| Intel Intrinsic | OpenPOWER / VSX | 見る場所 |
|---|---|---|
| `_mm_add_pd(a, b)` | `vec_add(a, b)` | [`openpower/add-f64x2.c`](openpower/add-f64x2.c) |
| `_mm_set1_pd(x)` | `vec_splats(x)` | [`openpower/set1-f64x2.c`](openpower/set1-f64x2.c) |
| `_mm_shuffle_epi32(v, 27)` | `{v[3], v[2], v[1], v[0]}` | [`openpower/shuffle-i32x4.c`](openpower/shuffle-i32x4.c) |

- [`sse2/`](sse2/)は入力生成、比較方法、両architectureのsymbolをまとめたcase packです。
- [`openpower/`](openpower/)はABIの細部を外し、VSXの中心部分だけを見せる小さな例です。
- 実際に証拠を生成するadapterは[`../adapters/openpower/`](../adapters/openpower/)にあります。
