# Official equivalence suite

<p>
  <img alt="Intel SSE2" src="https://img.shields.io/badge/Intel-SSE2-0071c5?style=flat&amp;logo=intel&amp;logoColor=white">
  <img alt="OpenPOWER" src="https://img.shields.io/badge/OpenPOWER-POWER8-cb2027?style=flat">
  <img alt="VSX" src="https://img.shields.io/badge/SIMD-VSX-f7b500?style=flat">
  <img alt="24 cases" src="https://img.shields.io/badge/cases-24-7c4dff?style=flat">
  <img alt="480 standard vectors" src="https://img.shields.io/badge/standard_vectors-480-00bfa5?style=flat">
</p>

このrepositoryの先頭に置く、公式のIntel ↔ OpenPOWER equivalence suiteです。
24個のcontractと、その全操作を一覧できるOpenPOWERコードをまとめています。

```text
10_official_suite/
├── cases/      24個のIntel ↔ OpenPOWER equivalence case
└── openpower/  全24操作をf64 / i32の2ファイルへ集約
```

| Block | Cases | OpenPOWER code |
|---|---:|---|
| f64 arithmetic / bit / lane | 10 | [`openpower/f64x2.c`](openpower/f64x2.c) |
| i32 arithmetic / logic / compare / shift / lane | 14 | [`openpower/i32x4.c`](openpower/i32x4.c) |
| **Total** | **24** | **2 readable files** |

- [`cases/`](cases/)は入力生成、比較方法、両architectureのsymbolをまとめたcase packです。
- [`openpower/`](openpower/)はABIの細部を外し、VSXの中心部分だけを見せる小さな例です。
- 実際に証拠を生成するadapterは[`../adapters/openpower/`](../adapters/openpower/)にあります。

```sh
ioitf check --profile standard --count-per-case 20 --showcase-report
```

この1コマンドで24ケース・480 vectorsの比較とSFレポート生成まで進みます。
