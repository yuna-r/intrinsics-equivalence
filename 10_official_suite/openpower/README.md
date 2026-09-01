# OpenPOWER examples

<p>
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/vector-VSX-f7b500?style=flat">
  <img alt="ppc64le" src="https://img.shields.io/badge/arch-ppc64le-5c6bc0?style=flat">
</p>

Intel IntrinsicをOpenPOWERへ移すときの中心部分を、全48ケース分まとめました。
細切れにせず、f64 / i8 / i16 / i32の4つの塊で読めます。

```text
openpower/
├── f64x2.c  18 operations // arithmetic, bit, broadcast, lane, compare
├── i8x16.c   8 operations // arithmetic, saturation, compare
├── i16x8.c   8 operations // arithmetic, saturation, compare
└── i32x4.c  14 operations // arithmetic, logic, compare, shift, lane
```

| Family | Intel Intrinsics | OpenPOWER expression |
|---|---|---|
| f64 arithmetic | `_mm_add_pd` / `_mm_sub_pd` / `_mm_mul_pd` | `vec_add` / `vec_sub` / `vec_mul` |
| f64 bit | `_mm_and_pd` / `_mm_or_pd` / `_mm_xor_pd` | vector `&` / `\|` / `^` |
| f64 lane | `_mm_set1_pd` / `_mm_move_sd` / unpack ×2 | `vec_splats` / lane initializer |
| f64 compare | eq / lt / le / gt / ge / neq / ord / unord | lane comparison + all-bits mask |
| i8 arithmetic / saturation | add / sub / adds / subs | vector operators / `vec_adds` / `vec_subs` |
| i8 compare | `_mm_cmpeq_epi8` / `_mm_cmpgt_epi8` | `vec_cmpeq` / `vec_cmpgt` |
| i16 arithmetic / saturation | add / sub / adds / subs | vector operators / `vec_adds` / `vec_subs` |
| i16 compare | `_mm_cmpeq_epi16` / `_mm_cmpgt_epi16` | `vec_cmpeq` / `vec_cmpgt` |
| i32 arithmetic | `_mm_add_epi32` / `_mm_sub_epi32` | vector `+` / `-` |
| i32 logic | and / or / xor / andnot | vector bit operators |
| i32 compare | `_mm_cmpeq_epi32` / `_mm_cmpgt_epi32` | `vec_cmpeq` / `vec_cmpgt` |
| i32 shift | slli / srli / srai | `vec_sl` / `vec_sr` / `vec_sra` |
| i32 lane | shuffle / unpacklo / unpackhi | lane initializer |

Linux ppc64leでは通常のnative buildに含まれます。

```sh
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
```

ここは見通し優先のofficial exampleです。共通ABI、入力のdecode、例外観測まで含む
実際の実装は[`../../adapters/openpower/sse2_pd.c`](../../adapters/openpower/sse2_pd.c)にあります。
