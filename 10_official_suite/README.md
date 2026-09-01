# Official equivalence suite

<p>
  <img alt="Intel SSE2" src="https://img.shields.io/badge/Intel-SSE2-0071c5?style=flat&amp;logo=intel&amp;logoColor=white">
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/SIMD-VSX-f7b500?style=flat">
  <img alt="128 cases" src="https://img.shields.io/badge/cases-128-7c4dff?style=flat">
  <img alt="128,000 standard vectors" src="https://img.shields.io/badge/standard_vectors-128k-00bfa5?style=flat">
  <img alt="Cross build passing" src="https://img.shields.io/badge/Clang_cross_build-passing-2ea44f?style=flat&amp;logo=llvm">
</p>

このrepositoryの先頭に置く、公式のIntel ↔ OpenPOWER equivalence suiteです。
128個のcontractと、両architectureの全操作を一覧できるコードをまとめています。

```text
10_official_suite/
├── cases/       128個のequivalence contract
├── intel/       SSE2による全128操作
└── openpower/   VSXによる全128操作
```

| Block | Cases | Intel | OpenPOWER |
|---|---:|---|---|
| f32/f64/i32 bit cast | 4 | [`intel/f32x4.c`](intel/f32x4.c) | [`openpower/f32x4.c`](openpower/f32x4.c) |
| f64 arithmetic / bit / construct / lane / compare | 36 | [`intel/f64x2.c`](intel/f64x2.c) | [`openpower/f64x2.c`](openpower/f64x2.c) |
| i8 arithmetic / saturation / average / SAD / minmax / shift / lane / mask | 19 | [`intel/i8x16.c`](intel/i8x16.c) | [`openpower/i8x16.c`](openpower/i8x16.c) |
| i16 arithmetic / multiply / saturation / average / minmax / compare / shift / pack / lane | 31 | [`intel/i16x8.c`](intel/i16x8.c) | [`openpower/i16x8.c`](openpower/i16x8.c) |
| i32 arithmetic / multiply / logic / compare / shift / construct / pack / lane | 25 | [`intel/i32x4.c`](intel/i32x4.c) | [`openpower/i32x4.c`](openpower/i32x4.c) |
| i64 arithmetic / shift / construct / lane | 13 | [`intel/i64x2.c`](intel/i64x2.c) | [`openpower/i64x2.c`](openpower/i64x2.c) |
| **Total** | **128** | **128 operations** | **128 operations** |

- [`cases/`](cases/)は入力生成、比較方法、両architectureのsymbolをまとめたcase packです。
- [`intel/`](intel/)と[`openpower/`](openpower/)は、両側の中心部分を同じ粒度で見せます。
- 実際に証拠を生成するadapterは[`../adapters/`](../adapters/)にあります。

## Clang cross build

Homebrew LLVMなど、x86_64とppc64le backendを持つClangなら1コマンドです。

```sh
./10_official_suite/cross-compile.sh
```

```text
intel/f64x2.o:     ELF 64-bit LSB relocatable, x86-64
openpower/f64x2.o: ELF 64-bit LSB relocatable, OpenPOWER ELF V2 ABI
```

Intel側はx86-64 ELF、OpenPOWER側はOpenPOWER ELF V2 ABIのppc64le objectになります。
これは実際のcross compilationです。残っているのはppc64le実機上での実行と、
その結果をnative evidenceとして収集するrunnerです。

```sh
ioitf check --profile standard --count-per-case 1000 --showcase-report
```

この1コマンドで128ケース・128,000 vectorsの比較とSFレポート生成まで進みます。
