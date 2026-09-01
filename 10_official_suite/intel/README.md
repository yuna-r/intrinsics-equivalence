# Intel examples

<p>
  <img alt="Intel" src="https://img.shields.io/badge/Intel-x86__64-0071c5?style=flat&amp;logo=intel&amp;logoColor=white">
  <img alt="SSE2" src="https://img.shields.io/badge/vector-SSE2-00a4ef?style=flat">
  <img alt="96 operations" src="https://img.shields.io/badge/operations-96-7c4dff?style=flat">
</p>

OpenPOWER側と同じ全96ケースを、Intel SSE2 Intrinsicsで型ごとの塊にまとめています。

```text
intel/
├── f64x2.c  28 operations // arithmetic, bit, construct, lane, compare
├── i8x16.c  17 operations // arithmetic, saturation, average, SAD, shift, mask
├── i16x8.c  24 operations // arithmetic, multiply, average, shift, pack, lane
├── i32x4.c  18 operations // arithmetic, logic, compare, shift, construct, lane
└── i64x2.c   9 operations // arithmetic, shift, construct, lane
```

| Block | Cases | Source |
|---|---:|---|
| f64 arithmetic / bit / construct / lane / compare | 28 | [`f64x2.c`](f64x2.c) |
| i8 arithmetic / saturation / average / SAD / minmax / shift / lane / mask | 17 | [`i8x16.c`](i8x16.c) |
| i16 arithmetic / multiply / saturation / average / minmax / compare / shift / pack / lane | 24 | [`i16x8.c`](i16x8.c) |
| i32 arithmetic / multiply / logic / compare / shift / construct / pack / lane | 18 | [`i32x4.c`](i32x4.c) |
| i64 arithmetic / shift / construct / lane | 9 | [`i64x2.c`](i64x2.c) |

入力decodeや共通ABIを外し、比較対象になるIntrinsic呼び出しを見やすくしたofficial exampleです。
実際のevidence adapterは[`../../adapters/intel/sse2_pd.c`](../../adapters/intel/sse2_pd.c)にあります。
