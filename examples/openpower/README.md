# OpenPOWER examples

<p>
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/vector-VSX-f7b500?style=flat">
  <img alt="ppc64le" src="https://img.shields.io/badge/arch-ppc64le-5c6bc0?style=flat">
</p>

Intel IntrinsicをOpenPOWERへ移すとき、中心になる式だけを3ファイルにしました。

```text
_mm_add_pd(a, b)           ──> vec_add(a, b)
_mm_set1_pd(value)         ──> vec_splats(value)
_mm_shuffle_epi32(v, 0x1b) ──> {v[3], v[2], v[1], v[0]}
```

| ファイル | 内容 |
|---|---|
| [`add-f64x2.c`](add-f64x2.c) | binary64を2レーン同時に加算 |
| [`set1-f64x2.c`](set1-f64x2.c) | scalarを2レーンへbroadcast |
| [`shuffle-i32x4.c`](shuffle-i32x4.c) | 4つの32-bitレーンを逆順に並べ替え |

Linux ppc64leでは通常のnative buildに含まれます。

```sh
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
```

ここは読みやすさ優先のshort exampleです。共通ABI、入力のdecode、例外観測まで含む
実際の実装は[`../../adapters/openpower/sse2_pd.c`](../../adapters/openpower/sse2_pd.c)にあります。
