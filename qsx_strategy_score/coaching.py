"""Constructive coaching copy for the free report card — BILINGUAL.

The card ships both English and Chinese for every dynamic line so the website can
render whichever the page language is (the site toggles language client-side, so a
single-language string from the backend would leave the other language stale). The
verdict stays harsh+honest (the number can be <60 and the flags name the real
problem), but the FRAMING is constructive: name the issue, give a direction to fix
it, and end with encouragement. This module is the single place the card copy lives.

Chinese is plain and direct (no jargon dump), matching the rest of the site.
"""
from __future__ import annotations

from typing import List

# flag code -> {"problem": {en, zh}, "direction": {en, zh}}
ISSUE_ADVICE = {
    "TOO_GOOD_TO_BE_TRUE": {
        "problem": {
            "en": "Results look too good to be true — the most common backtest trap.",
            "zh": "结果好得不真实——这是回测里最常见的坑。"},
        "direction": {
            "en": "Check for look-ahead bias, survivorship, and fill assumptions (slippage, fees, "
                  "whether you could actually get filled) before trusting any number.",
            "zh": "先排查未来函数、幸存者偏差和成交假设（滑点、手续费、到底能不能成交），再信任何数字。"}},
    "FORWARD_LOOKING_INPUT": {
        "problem": {
            "en": "The input explicitly mentions future/leaky/look-ahead data.",
            "zh": "输入文件明确提示可能含未来函数 / 泄露数据。"},
        "direction": {
            "en": "Treat the score as invalid until the strategy is re-run with lagged signals and "
                  "only information available at the decision time.",
            "zh": "在确认信号已滞后一根、且只使用决策当时可见的信息之前，不要把这个分数当有效结论。"}},
    "NEGATIVE_RETURN": {
        "problem": {
            "en": "Not profitable over the full sample.",
            "zh": "整个样本上是亏损的。"},
        "direction": {
            "en": "Get the strategy reliably positive in-sample first, then worry about optimizing.",
            "zh": "先让策略在样本内稳定为正，再谈优化。"}},
    "INSUFFICIENT_SAMPLE": {
        "problem": {
            "en": "Too few observations — treat this score as a rough indication only.",
            "zh": "观测太少——这个分只能当个大致参考。"},
        "direction": {
            "en": "Gather more observations or extend the backtest window (aim for >1 year), then re-test.",
            "zh": "积累更多观测或拉长回测区间（争取 1 年以上），再重测。"}},
    "LOW_FREQUENCY": {
        "problem": {
            "en": "Low-frequency / event strategy — few trades by design, not a sample defect.",
            "zh": "低频 / 事件型策略——交易笔数少是设计使然，不是样本缺陷。"},
        "direction": {
            "en": "Scored on the events you have, as an event-track read. More independent events "
                  "across different markets over time will firm it up.",
            "zh": "按你已有的事件来评，作为事件轨读数。随时间在不同行情里积累更多独立事件，结论会更扎实。"}},
    "BACKGROUND_REQUIRED": {
        "problem": {
            "en": "The return scale is unusually large — the score can't see how it was produced.",
            "zh": "收益规模异常大——评分看不到它是怎么做出来的。"},
        "direction": {
            "en": "Verify starting capital, leverage, venue fills and capacity before treating the "
                  "scale as repeatable — small capital in a mania reads very differently from size.",
            "zh": "把本金、杠杆、成交所/成交价、可容纳资金量核实清楚，再把这个收益规模当成可复制——"
                  "小资金踩中一波行情，和大资金做出来完全是两回事。"}},
    "OOS_NEGATIVE_RETURN": {
        "problem": {
            "en": "Lost money out-of-sample — the in-sample edge did not carry over.",
            "zh": "样本外是亏的——样本内的优势没延续过去。"},
        "direction": {
            "en": "Classic overfitting: simplify the parameters, run walk-forward validation, and "
                  "confirm the edge holds on data it never saw.",
            "zh": "典型过拟合：精简参数、做滚动前推验证，确认优势在没见过的数据上仍然成立。"}},
    "UNDERPERFORMS_HOLD_RISKADJ": {
        "problem": {
            "en": "On a risk-adjusted basis it did not beat simply holding the asset.",
            "zh": "风险调整后，没跑赢直接持有该资产。"},
        "direction": {
            "en": "Pin down what your timing/selection actually adds — trade only when it has a real "
                  "edge, or reframe it as a lower-drawdown way to hold.",
            "zh": "想清楚你的择时/选币到底加了什么——只在真有优势时出手，或干脆定位成"
                  "「回撤更小的持有方式」。"}},
    "RANDOM_CONTROL_NOT_BEATEN": {
        "problem": {
            "en": "On this asset your results are indistinguishable from random timing — the return is "
                  "likely just the asset trending up.",
            "zh": "在这个资产上，你的结果和随机择时没区别——收益很可能只是资产本身在涨。"},
        "direction": {
            "en": "A classic no-timing-edge signal: simplify the rules, cut parameters, and test whether "
                  "the signal adds value beyond plain asset exposure.",
            "zh": "典型的「没有择时优势」信号：精简规则、砍参数，验证信号是否真的能超过资产暴露本身。"}},
    "OVERFIT_SUSPECT_HOLDOUT": {
        "problem": {
            "en": "The later period is clearly weaker than the earlier one — possible overfitting.",
            "zh": "后段明显比前段弱——可能过拟合了。"},
        "direction": {
            "en": "Cut parameters and widen the test window to see whether the edge is stable.",
            "zh": "砍参数、拉宽测试区间，看优势稳不稳。"}},
    "RANDOM_CONTROL_WEAK_EDGE": {
        "problem": {
            "en": "Only marginally beats random timing — the edge is thin.",
            "zh": "只比随机择时强一点点——优势很薄。"},
        "direction": {
            "en": "Strengthen the signal or tighten entry conditions so the edge is clearer.",
            "zh": "强化信号或收紧入场条件，让优势更清楚。"}},
    "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": {
        "problem": {
            "en": "Hard to distinguish from luck so far, and no asset was provided for comparison.",
            "zh": "目前难以和运气区分，而且没提供对比资产。"},
        "direction": {
            "en": "Upload the K-line of the asset you traded to see whether you actually beat holding "
                  "or random timing.",
            "zh": "上传你交易的那个资产的 K 线，看看到底有没有跑赢「持有」或「随机择时」。"}},
    "DSR_FAIL": {
        "problem": {
            "en": "Given how many variants you tried, this Sharpe is what pure selection luck produces "
                  "— the deflated Sharpe is below a coin flip.",
            "zh": "考虑到你试过的版本数量，这条夏普就是纯海选运气能做出来的——折减后的夏普还不到掷硬币。"},
        "direction": {
            "en": "Treat it as no demonstrated edge yet: shrink the search space drastically, pick rules "
                  "with a structural rationale, and validate the survivor on data it never touched.",
            "zh": "当成「还没证明有优势」：大幅缩小搜索空间、挑有结构性逻辑的规则，再用没碰过的数据验证留下来的那条。"}},
    "DSR_OVERFIT_RISK": {
        "problem": {
            "en": "After deflating for the variants you tried, the Sharpe no longer clears the 95% "
                  "significance bar.",
            "zh": "按你试过的版本数折减后，夏普过不了 95% 的显著性门槛了。"},
        "direction": {
            "en": "Lock parameters early and stop re-optimizing; an edge worth trading should survive "
                  "your full search budget — check the 'survives ~N trials' number.",
            "zh": "早点锁死参数、别再反复优化；值得交易的优势应该扛得住你全部的搜索次数——看那个「经得起约 N 次海选」的数。"}},
    "SHORT_TRACK_RECORD": {
        "problem": {
            "en": "The track record is under 2 years — one good year can be luck, not skill.",
            "zh": "历史不到 2 年——一个好年头可能是运气，不是本事。"},
        "direction": {
            "en": "Extend the backtest (or keep running it live) to 2+ years covering different market "
                  "regimes, then re-score: the Bronze cap lifts automatically.",
            "zh": "把回测拉到 2 年以上、覆盖不同行情（或继续实盘跑），再评分：铜牌封顶会自动解除。"}},
    "LOW_EFFECTIVE_SAMPLE": {
        "problem": {
            "en": "Profit is concentrated in a handful of trades — the record is fragile.",
            "zh": "利润集中在少数几笔上——这份记录很脆。"},
        "direction": {
            "en": "Let the strategy accumulate more independent trades; an edge should keep showing up, "
                  "not rest on a few lucky hits.",
            "zh": "让策略积累更多独立交易；真优势应该反复出现，而不是靠几笔好运撑着。"}},
}

# priority order: lead with the most fundamental / most actionable problem
_PRIORITY = [
    "FORWARD_LOOKING_INPUT", "TOO_GOOD_TO_BE_TRUE", "NEGATIVE_RETURN", "DSR_FAIL", "INSUFFICIENT_SAMPLE",
    "OOS_NEGATIVE_RETURN", "UNDERPERFORMS_HOLD_RISKADJ", "RANDOM_CONTROL_NOT_BEATEN",
    "OVERFIT_SUSPECT_HOLDOUT", "RANDOM_CONTROL_WEAK_EDGE", "DSR_OVERFIT_RISK",
    "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK", "SHORT_TRACK_RECORD", "LOW_EFFECTIVE_SAMPLE",
    "LOW_FREQUENCY", "BACKGROUND_REQUIRED",
]

CTA = {
    "en": "Want a professional diagnosis — true mark-to-market drawdown, cost/slippage sensitivity, "
          "an out-of-sample robustness check and forward-survival odds? → quantscopex.com/report",
    "zh": "想要专业诊断——真实逐笔盯市回撤、成本/滑点敏感性、样本外稳健性检验和前向存活概率？→ quantscopex.com/report",
}

ENCOURAGEMENT = {
    "FLAGGED": {
        "en": "Clean up the backtest methodology, rule out the artifacts, and run it again — "
              "we'll be here. \U0001F4AA",
        "zh": "把回测方法理干净、排除假象，再跑一遍——我们都在。\U0001F4AA"},
    "CAUTION": {
        "en": "Don't be discouraged — most strategies don't clear these gates on the first "
              "try. Iterate on the directions above and keep going. \U0001F4AA",
        "zh": "别灰心——大多数策略第一次都过不了这些关。照上面的方向迭代，继续干。\U0001F4AA"},
    "OK": {
        "en": "Solid foundation — keep refining and aim for a higher grade next time. \U0001F4AA",
        "zh": "底子不错——继续打磨，下次冲更高的评级。\U0001F4AA"},
    # judgement stays "OK" even when a soft flag (weak/luck-unclear edge, overfit
    # suspicion, thin sample) is present — congratulating "Solid foundation" there
    # contradicts the same card's headline, so use a tempered line instead.
    "OK_SOFT": {
        "en": "Promising, but not proven yet — firm up the edge and the sample, then re-score. \U0001F4AA",
        "zh": "有潜力，但还没被证明——把优势和样本做扎实，再来评一次。\U0001F4AA"},
}

# soft / edge-weak flag codes that keep judgement "OK" but mean the edge or sample is
# not yet proven (so the card must not say "Solid foundation").
_SOFT_EDGE = frozenset({
    "RANDOM_CONTROL_WEAK_EDGE", "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK", "DSR_OVERFIT_RISK",
    "OVERFIT_SUSPECT_HOLDOUT", "SHORT_TRACK_RECORD", "LOW_EFFECTIVE_SAMPLE",
})


def coaching(report) -> dict:
    """Build the constructive block from a UnifiedReport (duck-typed: .flags,
    .grade, .judgement). Each issue + the encouragement ship in BOTH languages
    (problem/direction = English; problem_zh/direction_zh = Chinese) so the site can
    render the page's current language without a re-fetch."""
    codes: List[str] = []
    for f in report.flags:
        c = f.get("code")
        if c in ISSUE_ADVICE and c not in codes:
            codes.append(c)
    codes.sort(key=lambda c: _PRIORITY.index(c) if c in _PRIORITY else 99)
    issues = []
    for c in codes[:3]:
        adv = ISSUE_ADVICE[c]
        issues.append({
            "code": c,
            "problem": adv["problem"]["en"], "problem_zh": adv["problem"]["zh"],
            "direction": adv["direction"]["en"], "direction_zh": adv["direction"]["zh"],
        })
    judgement = report.judgement
    key = "OK_SOFT" if (judgement == "OK" and any(c in _SOFT_EDGE for c in codes)) else judgement
    enc = ENCOURAGEMENT.get(key, ENCOURAGEMENT["OK"])
    return dict(
        grade=report.grade,
        judgement=judgement,
        issues=issues,
        cta=CTA["en"], cta_zh=CTA["zh"],
        encouragement=enc["en"], encouragement_zh=enc["zh"],
    )
