# OpenPOWER examples

<p>
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/vector-VSX-f7b500?style=flat">
  <img alt="ppc64le" src="https://img.shields.io/badge/arch-ppc64le-5c6bc0?style=flat">
</p>

Intel IntrinsicをOpenPOWERへ移すときの中心部分を、全96ケース分まとめました。
細切れにしすぎず、データ型ごとの塊で読めます。

```text
openpower/
├── f64x2.c  28 operations // arithmetic, bit, construct, lane, compare
├── i8x16.c  17 operations // arithmetic, saturation, average, SAD, shift, mask
├── i16x8.c  24 operations // arithmetic, multiply, average, shift, pack, lane
├── i32x4.c  18 operations // arithmetic, logic, compare, shift, construct, lane
└── i64x2.c   9 operations // arithmetic, shift, construct, lane
```

| Family | Intel Intrinsics | OpenPOWER expression |
|---|---|---|
| f64 arithmetic | `_mm_add_pd` / `_mm_sub_pd` / `_mm_mul_pd` | `vec_add` / `vec_sub` / `vec_mul` |
| f64 bit | `_mm_and_pd` / `_mm_or_pd` / `_mm_xor_pd` | vector `&` / `\|` / `^` |
| f64 construct / lane | set / set1 / move / shuffle / unpack / cast | splat / lane initializer / bit cast |
| f64 compare | ordered, unordered, negated predicates | lane comparison + all-bits mask |
| i8 arithmetic / reduction | add / sub / adds / subs / avg / SAD / min / max | vector operations + half reduction |
| i8 lane / mask | byte shifts / unpack / movemask | semantic lane initializer + sign-bit pack |
| i8 compare | `_mm_cmpeq_epi8` / `_mm_cmpgt_epi8` | `vec_cmpeq` / `vec_cmpgt` |
| i16 arithmetic / multiply | add / sub / saturating / mul / madd / avg / min / max | vector operations + widened products |
| i16 compare | `_mm_cmpeq_epi16` / `_mm_cmpgt_epi16` | `vec_cmpeq` / `vec_cmpgt` |
| i16 shift / lane / pack | shift / shuffle / unpack / packs | guarded shift / lane initializer / saturating pack |
| i32 arithmetic / construct | add / sub / even-lane mul / scalar insert / broadcast | vector operations + lane initializer |
| i32 logic | and / or / xor / andnot | vector bit operators |
| i32 compare | `_mm_cmpeq_epi32` / `_mm_cmpgt_epi32` | `vec_cmpeq` / `vec_cmpgt` |
| i32 shift | slli / srli / srai | `vec_sl` / `vec_sr` / `vec_sra` |
| i32 lane / pack | shuffle / unpack / signed pack | lane initializer / saturating pack |
| i64 arithmetic / shift / lane | add / sub / shift / unpack / move / construct | vector operations + lane initializer |

Linux ppc64leでは通常のnative buildに含まれます。

```sh
cmake -S . -B build/native -DCMAKE_BUILD_TYPE=Release
cmake --build build/native --parallel
```

ここは見通し優先のofficial exampleです。共通ABI、入力のdecode、例外観測まで含む
実際の実装は[`../../adapters/openpower/sse2_pd.c`](../../adapters/openpower/sse2_pd.c)にあります。
