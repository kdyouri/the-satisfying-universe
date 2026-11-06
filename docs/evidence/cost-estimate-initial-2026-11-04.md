# Cost estimate — USD, 2026-11-04

No spending authorized. Implemented default caps: $0/day and $0/month.

## Verified model rates and assumptions

Rates below come from the saved [live OpenRouter catalogue](docs/evidence/openrouter-video-models-2026-11-04.json).
Use exact SKUs rather than lowest advertised rates. For Seedance, apply the
[published formula](https://openrouter.ai/bytedance/seedance-2.0):
video tokens = width × height × seconds × 24 / 1024. No reference-video input.
Revalidate combination and quote with the first authorized run.

Assume 60 original targets per 30-day month. A 25% regeneration load means
75 full video attempts, not a guaranteed acceptance rate. Actual accepted-video
cost rises when concepts fail both attempts. Two attempts maximum means up to
120 full attempts/month while still possibly missing the production target.

| Model / format | SKU | Seconds billed per attempt | Cost per attempt | 60 attempts | 75 attempts | Worst case 120 |
|---|---|---:|---:|---:|---:|---:|
| Veo Fast 720p, silent | without_audio_720p $0.08/s | 16 (2 clips) | $1.28 | $76.80 | $96.00 | $153.60 |
| Veo Fast 1080p, silent | without_audio $0.10/s | 16 (2 clips) | $1.60 | $96.00 | $120.00 | $192.00 |
| Veo Fast 1080p, audio | with_audio $0.12/s | 16 (2 clips) | $1.92 | $115.20 | $144.00 | $230.40 |
| Wan 720p, text input | text_to_video_720p $0.08/s | 20 (2 clips) | $1.60 | $96.00 | $120.00 | $192.00 |
| Wan 1080p, text input | text_to_video_1080p $0.12/s | 20 (2 clips) | $2.40 | $144.00 | $180.00 | $288.00 |
| Seedance 720×1280 | video_tokens $0.000007/token | 15 | $2.268 | $136.08 | $170.10 | $272.16 |
| Seedance 1080×1920 | video_tokens_1080p $0.0000077/token | 15 | $5.6133 | $336.80 | $421.00 | $673.60 |

Text-to-video Wan pricing does not imply that a separately supplied audio track is free.
Model audio defaults and payable variants must be checked; no audio SKU is invented.
720p does not become native 1080p by re-encoding. Technical acceptance thresholds must
state whether upscaling is allowed; initial preference is native 1080p.

## Proposed authorized pilot

Benchmark three concepts × three model families, using the 1080p configurations above:
Veo 3×$1.60 + Wan 3×$2.40 + Seedance 3×$5.6133 = **$28.84** generation estimate.
Reserve an upper-bound pilot envelope of **$50**, including quality analysis,
metadata, price variance and a limited repair allowance. Do not run it before explicit
authorization. Prepare quotes per request and stop when the envelope would be exceeded.

Suggested subsequent caps: **$12/day and $300/calendar month** of AI usage. These
support provisional Veo/Wan scenarios but do not fund sustained Seedance native-1080p
at the assumed retry rate. A cap can pause work before two accepted videos exist.
Caps are safety ceilings, not targets or subscriptions. No default model chosen yet.

## Other costs and cash outlay

Planning allowances, not provider quotes: creative text $1–5/month, multimodal QA
$3–15/month, small server $10–25/month, storage/backups $2–10/month, optional domain
$10–20/year. Obtain actual hosting quotes before purchase. FFmpeg has no per-video API
charge; compute and storage still cost money. Local testing uses existing hardware.

Illustrative native-1080p operating envelope: $120–180 generation + $4–20 text/QA +
$12–35 infrastructure ≈ **$136–235/month**, before fees, tax, and domain. This is
an estimate, not a guaranteed quality or revenue outcome. No monetization assumed.

[OpenRouter Standard pricing](https://openrouter.ai/pricing) lists a 5.5% fee when
buying credits, exclusive of taxes. For example, $180 of inference credits implies
approximately $189.90 cash before tax, subject to checkout rounding/minimums.
Application budgets track inference usage; credit-purchase fees and infrastructure
are separate commitments requiring authorization. Disable auto top-up initially.
