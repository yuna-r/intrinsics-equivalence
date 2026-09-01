# Intel examples

<p>
  <img alt="Intel" src="https://img.shields.io/badge/Intel-x86__64-0071c5?style=flat&amp;logo=intel&amp;logoColor=white">
  <img alt="SSE2" src="https://img.shields.io/badge/vector-SSE2-00a4ef?style=flat">
  <img alt="48 operations" src="https://img.shields.io/badge/operations-48-7c4dff?style=flat">
</p>

OpenPOWER側と同じ全48ケースを、Intel SSE2 Intrinsicsで4つの塊にまとめています。

```text
intel/
├── f64x2.c  18 operations // arithmetic, bit, broadcast, lane, compare
├── i8x16.c   8 operations // arithmetic, saturation, compare
├── i16x8.c   8 operations // arithmetic, saturation, compare
└── i32x4.c  14 operations // arithmetic, logic, compare, shift, lane
```

| Block | Cases | Source |
|---|---:|---|
| f64 arithmetic / bit / lane / compare | 18 | [`f64x2.c`](f64x2.c) |
| i8 arithmetic / saturation / compare | 8 | [`i8x16.c`](i8x16.c) |
| i16 arithmetic / saturation / compare | 8 | [`i16x8.c`](i16x8.c) |
| i32 arithmetic / logic / compare / shift / lane | 14 | [`i32x4.c`](i32x4.c) |

入力decodeや共通ABIを外し、比較対象になるIntrinsic呼び出しを見やすくしたofficial exampleです。
実際のevidence adapterは[`../../adapters/intel/sse2_pd.c`](../../adapters/intel/sse2_pd.c)にあります。
