"""Rendering.

`render_unified_text(report)` -> a terminal-friendly box (no third-party deps).
`render_unified_png(report, returns, out)` -> a single shareable PNG report card
with the score, the pillars, charts, the red-flag area and the disclaimer.
matplotlib is imported lazily inside render_unified_png so the core package stays
pandas-only.
"""
from __future__ import annotations

import textwrap
from typing import Optional

import pandas as pd

from .i18n import has_message, localize_cap_reason, t
from .metrics import equity_curve

DISCLAIMER = (
    "This score measures historical backtest QUALITY, not future performance, "
    "and is not investment advice.\nIt is computed from the return series alone "
    "— it CANNOT detect look-ahead, survivorship, unrealistic fills or "
    "in-sample selection."
)
DEEP_DIVE_CTA = (
    "Paid deep-dive: MTM drawdown, costs/slippage, out-of-sample robustness and forward-survival odds"
)


# --------------------------------------------------------------------------- #
# terminal
# --------------------------------------------------------------------------- #
def _bar(v: float, width: int = 10) -> str:
    n = int(round(max(0.0, min(100.0, v)) / 100 * width))
    return "█" * n + "░" * (width - n)


# --------------------------------------------------------------------------- #
# PNG card
# --------------------------------------------------------------------------- #
def _maybe_cjk_font(plt, *texts) -> None:
    """Choose a script-aware font for the current card render.

    Matplotlib rcParams are process-global, so a previous CJK render can leak its
    font into later Spanish/Portuguese cards. Reset Latin cards explicitly.
    """
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["mathtext.fontset"] = "dejavusans"
    chars = "".join(str(t) for t in texts if t)
    from matplotlib import font_manager

    def _set_first_available(candidates) -> None:
        for name in candidates:
            try:
                font_manager.findfont(name, fallback_to_default=False)
            except Exception:  # noqa: BLE001
                continue
            plt.rcParams["font.family"] = "sans-serif"
            plt.rcParams["font.sans-serif"] = list(dict.fromkeys([
                name,
                "DejaVu Sans",
                "Arial Unicode MS",
                "Arial",
                "Helvetica",
                "Liberation Sans",
            ]))
            return
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica", "Liberation Sans"]

    if not any(ord(ch) >= 0x3000 for ch in chars):
        _set_first_available(("DejaVu Sans", "Arial Unicode MS", "Arial", "Helvetica", "Liberation Sans"))
        return
    has_hangul = any(0xAC00 <= ord(ch) <= 0xD7AF for ch in chars)
    has_kana = any(0x3040 <= ord(ch) <= 0x30FF for ch in chars)
    if has_hangul:
        candidates = (
            "Apple SD Gothic Neo", "Nanum Gothic", "AppleGothic", "Arial Unicode MS",
            "Noto Sans CJK KR", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei",
        )
    elif has_kana:
        candidates = (
            "Hiragino Sans", "YuGothic", "Hiragino Maru Gothic Pro",
            "Arial Unicode MS", "Noto Sans CJK JP", "Noto Sans CJK SC",
            "Microsoft YaHei", "SimHei",
        )
    else:
        candidates = (
            "PingFang SC", "PingFang HK", "Heiti SC", "Heiti TC", "Songti SC",
            "STHeiti", "Arial Unicode MS",
            # Linux (Debian fonts-noto-cjk): matplotlib enumerates only the JP face
            # of the .ttc, which still covers ~all simplified glyphs — without it a
            # Linux server renders Chinese as tofu boxes.
            "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans CJK TC",
            "Microsoft YaHei", "SimHei",
        )
    _set_first_available(candidates)


# =========================================================================== #
# Unified report card (the merged 4-question product)
# =========================================================================== #
_CARD_BG = "#07090b"
_CARD_PANEL = "#111317"
_CARD_PANEL_2 = "#0c0f12"
_CARD_BORDER = "#2a2f38"
_CARD_TEXT = "#f4f4f5"
_CARD_MUTED = "#9ca3af"
_CARD_FAINT = "#6b7280"
_CARD_GREEN = "#34d399"
_CARD_AMBER = "#fbbf24"
_CARD_BLUE = "#60a5fa"
_CARD_RED = "#fb7185"

_EDGE_TEXT = {
    "beat": "beats hold + random timing",
    "hold_only": "beats buy & hold; random control unavailable",
    "lost": "did NOT beat buy & hold",
    "random_fail": "no edge over random timing",
    "marginal": "only a marginal edge",
    "luck_unclear": "hard to tell from luck — add the asset",
    "not_evaluated": "add the asset's K-line to evaluate",
}
# terminal/Streamlit edge icons (the PNG card builds its own glyphs in _png_edge_summary).
_EDGE_ICON_EMOJI = {"beat": "✅", "hold_only": "\U0001F7E1", "lost": "\U0001F534", "random_fail": "\U0001F534",
                    "marginal": "\U0001F7E1", "luck_unclear": "\U0001F7E1", "not_evaluated": "➖"}


def _unified_status(report):
    """(emoji, hex, verdict_word) from judgement + tier."""
    if report.judgement == "FLAGGED":
        return "\U0001F534", "#d62728", "FLAGGED"
    if report.judgement == "CAUTION":
        return "\U0001F7E0", "#e08214", "NEEDS WORK"
    if report.tier in ("GOLD", "SILVER"):
        return "\U0001F7E2", "#1a9850", "PASS"
    if report.tier == "BRONZE":
        return "\U0001F7E1", "#91cf60", "PASS"
    return "⚪", "#9aa0a6", "OK"


def _grade_color(v: float) -> str:
    """Grade-scale color zones (used for the total and the pillar bars). RED below
    60 (below passing) so a weak pillar is clearly distinct from a good one."""
    if v >= 90:
        return "#1a9850"   # green   — excellent (A)
    if v >= 80:
        return "#66bd63"   # l.green — good (B)
    if v >= 70:
        return "#fee08b"   # yellow  — fair (C)
    if v >= 60:
        return "#fc8d59"   # orange  — passing-ish (D)
    return "#d73027"       # red     — below passing / alarming (F)


def _edge_phrase(report, lang: str = "en") -> str:
    e = report.lights.get("edge", "not_evaluated")
    # A 'too good to be true' strategy beats everything PRECISELY because it is
    # probably overfit / look-ahead — so 'beats hold+random' is suspicion, not proof.
    if report.judgement == "FLAGGED":
        if e in ("beat", "marginal"):
            return ("⚠ 'beats hold + random' — but the equity is implausibly clean, "
                    "so that 'edge' is the red flag, not proof")
        return "⚠ edge is unreliable until the backtest is verified"
    txt = t(f"edge.{e}", lang) if lang != "en" else _EDGE_TEXT.get(e, "")
    rp = report.meta.get("random_p")
    if e in ("beat", "random_fail") and rp is not None:
        txt += f" (p={rp:.2f})"
    icon = _EDGE_ICON_EMOJI.get(e, "")
    return f"{icon} {txt}"


def _png_edge_summary(report, lang: str = "en") -> tuple[str, str, str]:
    """Natural-language edge line for the share card.

    The text is deliberately NOT built as "NO " + "no edge..."; share cards need
    one clear sentence, not a terminal-style status token plus a repeated denial.
    Returns (label, text, color).
    """
    e = report.lights.get("edge", "not_evaluated")
    if report.judgement == "FLAGGED":
        text = {
            "zh": "先验证回测真实性，再判断优势。",
            "ja": "まずバックテストの信頼性を検証してください。",
            "ko": "먼저 백테스트 신뢰성을 검증해야 합니다.",
            "es": "Primero verifica la integridad del backtest.",
            "pt-BR": "Verifique primeiro a integridade do backtest.",
        }.get(lang, "Verify backtest integrity before trusting the edge.")
        return _png_label("skill_luck", lang), text, _CARD_RED
    labels = {
        "beat": {
            "en": "Passed hold and random-timing checks.",
            "zh": "通过持有与随机择时检验。",
            "ja": "保有・ランダム売買の検査を通過。",
            "ko": "보유 및 랜덤 타이밍 검사를 통과.",
            "es": "Supera hold y timing aleatorio.",
            "pt-BR": "Supera hold e timing aleatório.",
        },
        "hold_only": {
            "en": "Beat buy and hold; random control unavailable.",
            "zh": "跑赢买入持有；随机对照不可用。",
            "ja": "買い持ちを上回るが、ランダム対照は不可。",
            "ko": "매수 보유는 상회, 랜덤 대조 불가.",
            "es": "Supera buy-and-hold; control aleatorio no disponible.",
            "pt-BR": "Supera buy-and-hold; controle aleatório indisponível.",
        },
        "lost": {
            "en": "Did not beat buy and hold.",
            "zh": "未跑赢买入持有。",
            "ja": "買い持ちを上回っていません。",
            "ko": "매수 보유를 이기지 못했습니다.",
            "es": "No supera comprar y mantener.",
            "pt-BR": "Não supera comprar e manter.",
        },
        "random_fail": {
            "en": "Timing edge not proven.",
            "zh": "未证明择时优势。",
            "ja": "タイミング優位性は未証明。",
            "ko": "타이밍 우위가 입증되지 않았습니다.",
            "es": "No demuestra ventaja de timing.",
            "pt-BR": "Vantagem de timing não comprovada.",
        },
        "marginal": {
            "en": "Weak edge; needs more evidence.",
            "zh": "优势偏弱，需要更多证据。",
            "ja": "優位性は弱く、追加証拠が必要。",
            "ko": "우위가 약해 추가 증거가 필요합니다.",
            "es": "Ventaja débil; necesita más evidencia.",
            "pt-BR": "Vantagem fraca; precisa de mais evidência.",
        },
        "luck_unclear": {
            "en": "Hard to separate skill from luck.",
            "zh": "暂难区分本事和运气。",
            "ja": "スキルと運の区別が難しい。",
            "ko": "실력과 운을 구분하기 어렵습니다.",
            "es": "Difícil separar habilidad de suerte.",
            "pt-BR": "Difícil separar habilidade de sorte.",
        },
        "not_evaluated": {
            "en": "Add asset benchmark to test skill vs luck.",
            "zh": "加入资产基准后再判断本事/运气。",
            "ja": "資産ベンチマークを追加して検証。",
            "ko": "자산 벤치마크를 추가해 검증하세요.",
            "es": "Agrega benchmark para separar habilidad y suerte.",
            "pt-BR": "Adicione benchmark para separar habilidade e sorte.",
        },
    }
    color = {
        "beat": _CARD_GREEN,
        "hold_only": _CARD_AMBER,
        "lost": _CARD_RED,
        "random_fail": _CARD_RED,
        "marginal": _CARD_AMBER,
        "luck_unclear": _CARD_AMBER,
        "not_evaluated": _CARD_FAINT,
    }.get(e, _CARD_FAINT)
    rp = report.meta.get("random_p")
    suffix = f" p={rp:.2f}" if e in ("beat", "random_fail") and rp is not None else ""
    return _png_label("skill_luck", lang), labels.get(e, labels["not_evaluated"]).get(lang, labels[e]["en"]) + suffix, color


def _png_sample_summary(report, lang: str = "en") -> tuple[str, str, str]:
    m = report.meta
    n = m.get("n")
    unit = m.get("sample_unit", "bars")
    ok = bool(m.get("sample_ok", True))
    low_frequency = bool(m.get("low_frequency"))
    unit_txt = t(unit, lang) if unit in ("bars", "trades") else unit
    if ok and low_frequency and unit == "trades":
        text = {
            "zh": f"事件样本 ({n} {unit_txt})",
            "ja": f"イベント標本 ({n} {unit_txt})",
            "ko": f"이벤트 표본 ({n} {unit_txt})",
            "es": f"Muestra de eventos ({n} {unit_txt})",
            "pt-BR": f"Amostra de eventos ({n} {unit_txt})",
        }.get(lang, f"Event sample ({n} {unit_txt})")
        return _png_label("sample", lang), text, _CARD_AMBER
    if ok:
        text = {
            "zh": f"样本充足 ({n} {unit_txt})",
            "ja": f"サンプル十分 ({n} {unit_txt})",
            "ko": f"표본 충분 ({n} {unit_txt})",
            "es": f"Muestra suficiente ({n} {unit_txt})",
            "pt-BR": f"Amostra suficiente ({n} {unit_txt})",
        }.get(lang, f"Adequate sample ({n} {unit_txt})")
        return _png_label("sample", lang), text, _CARD_GREEN
    text = {
        "zh": f"样本偏薄 ({n} {unit_txt})",
        "ja": f"サンプル不足 ({n} {unit_txt})",
        "ko": f"표본 부족 ({n} {unit_txt})",
        "es": f"Muestra limitada ({n} {unit_txt})",
        "pt-BR": f"Amostra limitada ({n} {unit_txt})",
    }.get(lang, f"Thin sample ({n} {unit_txt})")
    return _png_label("sample", lang), text, _CARD_AMBER


def _png_card_headline(report, lang: str = "en") -> str:
    """Short headline for the shareable PNG.

    The terminal report can afford a full sentence with caveats. The PNG is a
    compact social/share card, so the protagonist line must be short enough to
    survive fixed-size rendering without clipping.
    """
    if lang != "en":
        return _localized_headline(report, lang)
    edge = report.lights.get("edge")
    if report.judgement == "FLAGGED":
        return "Looks too good to be true. Verify methodology first."
    if report.meta.get("cagr", 0.0) <= 0:
        return "Not profitable over the full sample."
    if not report.meta.get("sample_ok", True):
        return "Sample is thin. Treat this score as provisional."
    if edge == "beat":
        return "Beat buy & hold and random timing in this sample."
    if edge == "hold_only":
        return "Beat buy & hold. Random timing control not available."
    if edge == "lost":
        return "Did not beat buy & hold on a risk-adjusted basis."
    if edge == "random_fail":
        return "No proven timing edge versus random timing."
    if edge == "marginal":
        return "Weak edge. Needs more evidence before trusting it."
    if edge == "luck_unclear":
        return "Hard to separate skill from luck so far."
    return "Add the traded asset benchmark to test skill vs luck."


def _short_png_value(text: str, max_chars: int = 24) -> str:
    """Compact dynamic labels for small PNG check cells."""
    replacements = {
        "Passed hold and random-timing checks.": "Passed checks",
        "Beat buy and hold; random control unavailable.": "Hold passed only",
        "跑赢买入持有；随机对照不可用。": "仅持有对照通过",
        "Timing edge not proven.": "Not proven",
        "Did not beat buy and hold.": "Lost to hold",
        "Weak edge; needs more evidence.": "Weak edge",
        "Hard to separate skill from luck.": "Unclear",
        "Add asset benchmark to test skill vs luck.": "Add benchmark",
        "Verify backtest integrity before trusting the edge.": "Verify first",
        "Adequate sample": "Sample",
    }
    out = text or ""
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    out = out.replace("(", "").replace(")", "")
    if len(out) <= max_chars:
        return out
    return out[: max_chars - 3].rstrip(" .,;:-") + "..."


def _sample_phrase(report, lang: str = "en") -> str:
    m = report.meta
    ok = m.get("sample_ok", True)
    n, unit, eff = m.get("n"), m.get("sample_unit", "bars"), m.get("effective_n")
    mark = "✅" if ok else "⚠"
    unit_txt = t(unit, lang) if unit in ("bars", "trades") else unit
    if ok and m.get("low_frequency") and unit == "trades":
        label = {
            "zh": "事件样本",
            "ja": "イベント標本",
            "ko": "이벤트 표본",
            "es": "muestra de eventos",
            "pt-BR": "amostra de eventos",
        }.get(lang, "event sample")
        return f"{mark} {label} ({n} {unit_txt})"
    if ok:
        return f"{mark} {t('sample_adequate', lang)} ({n} {unit_txt})"
    eff_txt = f", ~{eff:.0f} effective" if eff else ""
    return f"{mark} {t('sample_thin', lang)} ({n} {unit_txt}{eff_txt}) - provisional"


def _png_grade(grade: str, lang: str) -> str:
    if lang == "zh":
        return {"GOLD": "金牌", "SILVER": "银牌", "BRONZE": "铜牌", "NEEDS WORK": "需改进", "FLAGGED": "存疑"}.get(grade, grade)
    if lang == "ja":
        return {"GOLD": "ゴールド", "SILVER": "シルバー", "BRONZE": "ブロンズ", "NEEDS WORK": "要改善", "FLAGGED": "要検証"}.get(grade, grade)
    if lang == "ko":
        return {"GOLD": "골드", "SILVER": "실버", "BRONZE": "브론즈", "NEEDS WORK": "개선 필요", "FLAGGED": "검증 필요"}.get(grade, grade)
    if lang == "es":
        return {"GOLD": "Oro", "SILVER": "Plata", "BRONZE": "Bronce", "NEEDS WORK": "Necesita trabajo", "FLAGGED": "Sospechoso"}.get(grade, grade)
    if lang == "pt-BR":
        return {"GOLD": "Ouro", "SILVER": "Prata", "BRONZE": "Bronze", "NEEDS WORK": "Precisa melhorar", "FLAGGED": "Sinalizado"}.get(grade, grade)
    return grade


def _png_status_word(word: str, lang: str) -> str:
    if lang == "zh":
        return {"PASS": "通过", "NEEDS WORK": "需改进", "FLAGGED": "存疑", "OK": "可参考"}.get(word, word)
    if lang == "ja":
        return {"PASS": "合格", "NEEDS WORK": "要改善", "FLAGGED": "要検証", "OK": "参考"}.get(word, word)
    if lang == "ko":
        return {"PASS": "통과", "NEEDS WORK": "개선 필요", "FLAGGED": "검증 필요", "OK": "참고"}.get(word, word)
    if lang == "es":
        return {"PASS": "Aprobado", "NEEDS WORK": "Mejorar", "FLAGGED": "Sospechoso", "OK": "Revisar"}.get(word, word)
    if lang == "pt-BR":
        return {"PASS": "Aprovado", "NEEDS WORK": "Melhorar", "FLAGGED": "Sinalizado", "OK": "Revisar"}.get(word, word)
    return word


def _png_label(key: str, lang: str) -> str:
    labels = {
        "en": {
            "status": "Status",
            "score": "Strategy score",
            "pillars": "Why this score",
            "equity": "Equity curve",
            "drawdown": "Drawdown",
            "issues": "Key issues",
            "skill_luck": "Skill vs luck",
            "sample": "Sample",
            "overfit": "Overfit",
            "risk": "Risk",
            "scorecard": "Strategy Scorecard",
            "diagnostics": "Diagnostics",
            "period": "Period",
            "score_line": "Free strategy scorecard",
            "dependency": "Dependency",
            "return_quality": "Return quality",
            "overfit_risk": "Overfit risk",
            "maxdd": "MaxDD",
            "calmar": "Calmar",
            "historical_path": "historical path",
            "risk_adjusted_return": "risk-adjusted return",
            "strategy": "Strategy",
            "buy_hold": "Buy & Hold",
            "no_issues": "No major issue surfaced in the free scorecard.",
            "note": "Free historical backtest-quality scorecard. Not investment advice.",
            "audit_report_cta": "Full audit report: quantscopex.com/report",
        },
        "zh": {
            "status": "结论",
            "score": "策略评分",
            "pillars": "为什么是这个分数",
            "equity": "净值曲线",
            "drawdown": "回撤",
            "max": "最大",
            "issues": "主要问题",
            "skill_luck": "本事/运气",
            "sample": "样本",
            "overfit": "过拟合",
            "risk": "风险",
            "scorecard": "策略评分卡",
            "diagnostics": "诊断",
            "period": "区间",
            "score_line": "免费策略评分卡",
            "dependency": "依赖扫描",
            "return_quality": "收益质量",
            "overfit_risk": "过拟合风险",
            "maxdd": "最大回撤",
            "calmar": "Calmar",
            "historical_path": "历史路径",
            "risk_adjusted_return": "风险调整收益",
            "strategy": "策略",
            "buy_hold": "买入持有",
            "no_issues": "免费评分卡未发现特别突出的主要问题。",
            "note": "免费历史回测质量评分卡，不构成投资建议。",
            "audit_report_cta": "完整审计报告：quantscopex.com/report",
        },
        "ja": {
            "status": "判定",
            "score": "戦略スコア",
            "pillars": "スコア理由",
            "equity": "エクイティ曲線",
            "drawdown": "ドローダウン",
            "issues": "主な問題",
            "skill_luck": "スキル/運",
            "sample": "サンプル",
            "overfit": "過剰最適化",
            "risk": "リスク",
            "scorecard": "戦略スコアカード",
            "diagnostics": "診断",
            "period": "期間",
            "score_line": "無料戦略スコアカード",
            "dependency": "依存度",
            "return_quality": "リターン品質",
            "overfit_risk": "過剰最適化リスク",
            "maxdd": "最大DD",
            "calmar": "Calmar",
            "historical_path": "過去パス",
            "risk_adjusted_return": "リスク調整リターン",
            "strategy": "戦略",
            "buy_hold": "買い持ち",
            "no_issues": "無料スコアカードでは大きな問題は見つかりませんでした。",
            "note": "過去バックテスト品質の無料スコアカード。投資助言ではありません。",
            "audit_report_cta": "完全監査レポート: quantscopex.com/report",
        },
        "ko": {
            "status": "판정",
            "score": "전략 점수",
            "pillars": "점수 이유",
            "equity": "에쿼티 곡선",
            "drawdown": "드로다운",
            "issues": "주요 문제",
            "skill_luck": "실력/운",
            "sample": "표본",
            "overfit": "과최적화",
            "risk": "리스크",
            "scorecard": "전략 점수 카드",
            "diagnostics": "진단",
            "period": "기간",
            "score_line": "무료 전략 점수 카드",
            "dependency": "의존도",
            "return_quality": "수익 품질",
            "overfit_risk": "과최적화 리스크",
            "maxdd": "최대낙폭",
            "calmar": "Calmar",
            "historical_path": "과거 경로",
            "risk_adjusted_return": "위험조정 수익",
            "strategy": "전략",
            "buy_hold": "매수 보유",
            "no_issues": "무료 점수 카드에서 큰 문제는 발견되지 않았습니다.",
            "note": "과거 백테스트 품질 무료 점수 카드이며 투자 조언이 아닙니다.",
            "audit_report_cta": "전체 감사 보고서: quantscopex.com/report",
        },
        "es": {
            "status": "Veredicto",
            "score": "Puntuación",
            "pillars": "Por qué",
            "equity": "Curva de capital",
            "drawdown": "Caída",
            "issues": "Problemas clave",
            "skill_luck": "Habilidad/suerte",
            "sample": "Muestra",
            "overfit": "Sobreajuste",
            "risk": "Riesgo",
            "scorecard": "Scorecard de estrategia",
            "diagnostics": "Diagnóstico",
            "period": "Periodo",
            "score_line": "Scorecard gratuito",
            "dependency": "Dependencia",
            "return_quality": "Calidad retorno",
            "overfit_risk": "Riesgo sobreajuste",
            "maxdd": "MaxDD",
            "calmar": "Calmar",
            "historical_path": "ruta histórica",
            "risk_adjusted_return": "retorno ajustado",
            "strategy": "Estrategia",
            "buy_hold": "Buy & Hold",
            "no_issues": "El scorecard gratuito no encontró un problema principal claro.",
            "note": "Scorecard histórico gratuito; no es asesoría de inversión.",
            "audit_report_cta": "Informe completo: quantscopex.com/report",
        },
        "pt-BR": {
            "status": "Veredito",
            "score": "Pontuação",
            "pillars": "Por quê",
            "equity": "Curva de capital",
            "drawdown": "Queda",
            "issues": "Principais problemas",
            "skill_luck": "Habilidade/sorte",
            "sample": "Amostra",
            "overfit": "Sobreajuste",
            "risk": "Risco",
            "scorecard": "Scorecard de estratégia",
            "diagnostics": "Diagnóstico",
            "period": "Período",
            "score_line": "Scorecard gratuito",
            "dependency": "Dependência",
            "return_quality": "Qualidade retorno",
            "overfit_risk": "Risco sobreajuste",
            "maxdd": "MaxDD",
            "calmar": "Calmar",
            "historical_path": "trajeto histórico",
            "risk_adjusted_return": "retorno ajustado",
            "strategy": "Estratégia",
            "buy_hold": "Buy & Hold",
            "no_issues": "O scorecard gratuito não encontrou um problema principal claro.",
            "note": "Scorecard histórico gratuito; não é recomendação de investimento.",
            "audit_report_cta": "Relatório completo: quantscopex.com/report",
        },
    }
    return labels.get(lang, labels["en"]).get(key, labels["en"][key])


def _cap_note(report, lang: str = "en") -> str:
    m = report.meta
    if not m.get("capped"):
        return ""
    if report.judgement == "FLAGGED":
        return t("flagged_clean", lang)
    reasons = m.get("cap_reasons") or []
    reasons = [localize_cap_reason(str(x), lang) for x in reasons]
    if not reasons:
        return ""
    return f"{t('score_capped', lang)} — {reasons[0]} ({t('pillars_avg', lang)} {m.get('uncapped_score', 0):.0f})"


def _localized_issue(it: dict, lang: str) -> tuple[str, str]:
    if lang == "zh":
        return it.get("problem_zh") or it.get("problem", ""), it.get("direction_zh") or it.get("direction", "")
    code = it.get("code")
    if code and has_message(f"issue.{code}.problem", lang):
        return t(f"issue.{code}.problem", lang), t(f"issue.{code}.direction", lang)
    return it.get("problem", ""), it.get("direction", "")


def _localized_headline(report, lang: str) -> str:
    if lang == "zh":
        return report.meta.get("headline_zh") or report.headline
    if lang == "en":
        return report.headline
    if report.judgement == "FLAGGED":
        return t("headline.flagged", lang)
    if report.meta.get("cagr", 0.0) <= 0:
        return t("headline.negative", lang)
    if not report.meta.get("sample_ok", True):
        return t("headline.sample", lang)
    edge = report.lights.get("edge")
    if edge == "beat":
        return t("headline.edge_beat", lang)
    if edge == "hold_only":
        return t("headline.edge_hold_only", lang)
    if edge == "lost":
        return t("headline.edge_lost", lang)
    if edge == "random_fail":
        return t("headline.edge_random_fail", lang)
    if edge == "marginal":
        return t("headline.edge_marginal", lang)
    return t("headline.edge_unknown", lang)


def render_unified_text(report, *, lang: str = "en", triage: Optional[dict] = None) -> str:
    from .coaching import coaching as _coaching
    co = _coaching(report)
    emoji, _c, _w = _unified_status(report)
    L = ["=" * 64]
    L.append(f"  {t('score_title', lang):<28} {report.display:5.1f} / 100   {emoji} {report.grade}")
    headline = _localized_headline(report, lang)
    for ln in textwrap.wrap(headline, width=58):
        L.append("  " + ln)
    cn = _cap_note(report, lang)
    if cn:
        L.append("  (" + cn + ")")
    L.append("=" * 64)

    def _pillar(name, s, hint):
        if s is None or s.value is None:
            L.append(f"  {name:<19} {'·' * 10}   n/a")
        else:
            L.append(f"  {name:<19} {_bar(s.value)} {s.value:4.0f}   {hint}")
    rq, cr, rk = report.return_quality, report.credibility, report.risk
    _pillar(t("return_quality", lang), rq, f"Sharpe {rq.raw.get('sharpe', 0):.2f}")
    _pillar(t("credibility", lang), cr, t("overfit_hint", lang))
    _pillar(t("drawdown_control", lang), rk, f"MaxDD {rk.raw.get('mdd', 0) * 100:.0f}%")
    L.append(f"  {t('edge_label', lang):<19} {_edge_phrase(report, lang=lang)}")
    L.append(f"  {t('sample', lang):<19} {_sample_phrase(report, lang=lang)}")
    if triage:
        ep = triage.get("edge_persistence") or {}
        ev = triage.get("evidence_confidence") or {}
        dep = triage.get("dependency_lite") or {}
        L.append(f"  {t('edge_persistence', lang):<19} {ep.get('label_local') or ep.get('label') or 'n/a'}")
        L.append(f"  {t('evidence_confidence', lang):<19} {ev.get('level_local') or ev.get('level') or 'n/a'}")
        dep_label = dep.get("label_local") or dep.get("label")
        dep_txt = dep_label if dep.get("available") else t("unavailable", lang)
        L.append(f"  {t('dependency_lite', lang):<19} {dep_txt}")
    L.append("-" * 64)
    if co["issues"]:
        L.append(f"  {t('what_to_look_at', lang)}:")
        for it in co["issues"]:
            problem, direction = _localized_issue(it, lang)
            L.append("   • " + problem)
            for ln in textwrap.wrap(direction, width=56):
                L.append("     " + ln)
    pro_cta = (triage or {}).get("pro_unlock_map", {}).get("cta") or t("pro_cta", lang)
    for ln in textwrap.wrap(pro_cta, width=60):
        L.append("  " + ln)
    if report.judgement == "FLAGGED":
        enc_key = "encouragement.flagged"
    elif report.judgement == "CAUTION" or co["issues"]:
        enc_key = "encouragement.caution"
    else:
        enc_key = "encouragement.ok"
    enc = t(enc_key, lang)
    L.append("  " + (enc or ""))
    if triage:
        L.append("-" * 64)
        L.append("  " + ((triage.get("pro_unlock_map") or {}).get("headline") or t("pro_unlocks_short", lang)))
    L.append("-" * 64)
    L.append("  " + (t("free_triage", lang) if lang != "en" else DISCLAIMER.replace("\n", "\n  ")))
    L.append("=" * 64)
    return "\n".join(L)


def render_unified_png(report, returns: pd.Series, out_path: str, *,
                       brand: str = "QSX Strategy Scorecard",
                       cta: Optional[str] = None,
                       bench: Optional[dict] = None, lang: str = "en",
                       triage: Optional[dict] = None) -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import FancyBboxPatch
        from matplotlib.ticker import NullFormatter
    except ImportError as e:  # pragma: no cover
        raise ImportError("render_unified_png needs matplotlib: pip install 'qsx-score-free[card]'") from e
    from .coaching import coaching as _coaching
    headline = _png_card_headline(report, lang)
    _maybe_cjk_font(plt, "QSX Strategy Score", brand, headline, cta)
    co = _coaching(report)
    r = returns.astype(float)
    eq = equity_curve(r)
    m = report.meta
    _emoji, status_color, word = _unified_status(report)

    def tone() -> str:
        if report.judgement == "FLAGGED":
            return "#ef4444"
        if report.grade == "NEEDS WORK":
            return "#f59e0b"
        if report.grade == "BRONZE":
            return "#60a5fa"
        return "#59c85f"

    accent = tone()

    def axis_box(bounds, *, face=_CARD_PANEL, edge=_CARD_BORDER, radius=0.026, lw=1.5):
        ax = fig.add_axes(bounds)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_facecolor("none")
        ax.add_patch(FancyBboxPatch(
            (0, 0), 1, 1, transform=ax.transAxes,
            boxstyle=f"round,pad=0.012,rounding_size={radius}",
            facecolor=face, edgecolor=edge, linewidth=lw, clip_on=False, zorder=-10,
        ))
        return ax

    def wrap_lines(text: str, width: int, max_lines: int = 2) -> list[str]:
        if not text:
            return []
        if " " not in text and len(text) > width:
            lines = [text[i:i + width] for i in range(0, len(text), width)]
        else:
            lines = textwrap.wrap(text, width=width)
        lines = lines[:max_lines]
        if len(lines) == max_lines and len(" ".join(lines)) < len(text):
            lines[-1] = lines[-1].rstrip(".,;: ") + "..."
        return lines

    def add_wrapped(ax, x, y, text, *, width, max_lines=2, fontsize=18,
                    color=_CARD_TEXT, weight="normal", lineheight=0.13):
        for line in wrap_lines(text, width, max_lines):
            ax.text(x, y, line, transform=ax.transAxes, fontsize=fontsize,
                    color=color, fontweight=weight, va="top")
            y -= lineheight
        return y

    def metric_box(bounds, label: str, value: str, color: str, note: str = ""):
        ax = axis_box(bounds, face="#111820", edge="#2a3647", radius=0.022, lw=1.2)
        ax.text(0.075, 0.78, label.upper(), fontsize=9.6, color=_CARD_MUTED,
                fontweight="bold", va="top")
        ax.text(0.075, 0.43, value, fontsize=23, color=color,
                fontweight="bold", va="center")
        if note:
            ax.text(0.075, 0.12, note, fontsize=8.2, color=_CARD_FAINT, va="bottom")
        return ax

    def compact_issue_text(item: dict) -> str:
        problem, direction = _localized_issue(item, lang)
        code = item.get("code")
        short_by_lang = {
            "en": {
                "TOO_GOOD_TO_BE_TRUE": "Looks too good to be true.",
                "FORWARD_LOOKING_INPUT": "Input may contain future data.",
                "NEGATIVE_RETURN": "Not profitable over the full sample.",
                "INSUFFICIENT_SAMPLE": "Too few observations.",
                "LOW_FREQUENCY": "Low-frequency strategy — few trades, analyze further.",
                "BACKGROUND_REQUIRED": "Return scale is unusually large.",
                "OOS_NEGATIVE_RETURN": "Lost money out-of-sample.",
                "UNDERPERFORMS_HOLD_RISKADJ": "Did not beat buy-and-hold.",
                "RANDOM_CONTROL_NOT_BEATEN": "No proven timing edge.",
                "OVERFIT_SUSPECT_HOLDOUT": "Later period is weaker.",
                "RANDOM_CONTROL_WEAK_EDGE": "Only weak edge vs random timing.",
                "RANDOM_CONTROL_UNAVAILABLE": "Random control unavailable.",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "Hard to separate skill from luck.",
                "DSR_FAIL": "Selection luck can explain this Sharpe.",
                "DSR_OVERFIT_RISK": "Sharpe weak after search penalty.",
                "SHORT_TRACK_RECORD": "Track record is under 2 years.",
                "LOW_EFFECTIVE_SAMPLE": "Profit is concentrated.",
            },
            "zh": {
                "TOO_GOOD_TO_BE_TRUE": "结果好得不真实。",
                "FORWARD_LOOKING_INPUT": "输入可能含未来数据。",
                "NEGATIVE_RETURN": "全样本未盈利。",
                "INSUFFICIENT_SAMPLE": "观测太少。",
                "LOW_FREQUENCY": "成交数偏少，建议进一步分析。",
                "BACKGROUND_REQUIRED": "收益规模异常大。",
                "OOS_NEGATIVE_RETURN": "样本外亏损。",
                "UNDERPERFORMS_HOLD_RISKADJ": "未跑赢买入持有。",
                "RANDOM_CONTROL_NOT_BEATEN": "未证明择时优势。",
                "OVERFIT_SUSPECT_HOLDOUT": "后段表现变弱。",
                "RANDOM_CONTROL_WEAK_EDGE": "相对随机择时优势弱。",
                "RANDOM_CONTROL_UNAVAILABLE": "随机对照未运行。",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "难以区分实力和运气。",
                "DSR_FAIL": "Sharpe 可能来自筛选运气。",
                "DSR_OVERFIT_RISK": "搜索惩罚后 Sharpe 偏弱。",
                "SHORT_TRACK_RECORD": "记录不足两年。",
                "LOW_EFFECTIVE_SAMPLE": "利润过于集中。",
            },
            "ja": {
                "TOO_GOOD_TO_BE_TRUE": "結果が良すぎます。",
                "FORWARD_LOOKING_INPUT": "未来データの疑い。",
                "NEGATIVE_RETURN": "全期間で非収益。",
                "INSUFFICIENT_SAMPLE": "観測数が不足。",
                "LOW_FREQUENCY": "低頻度イベント型。",
                "BACKGROUND_REQUIRED": "リターン規模が異常。",
                "OOS_NEGATIVE_RETURN": "OOSで損失。",
                "UNDERPERFORMS_HOLD_RISKADJ": "Buy & hold未満。",
                "RANDOM_CONTROL_NOT_BEATEN": "タイミング優位性なし。",
                "OVERFIT_SUSPECT_HOLDOUT": "後半が弱い。",
                "RANDOM_CONTROL_WEAK_EDGE": "ランダム比の優位性が弱い。",
                "RANDOM_CONTROL_UNAVAILABLE": "ランダム対照なし。",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "運との区別が難しい。",
                "DSR_FAIL": "選択運で説明可能。",
                "DSR_OVERFIT_RISK": "補正後Sharpeが弱い。",
                "SHORT_TRACK_RECORD": "2年未満の実績。",
                "LOW_EFFECTIVE_SAMPLE": "利益が集中。",
            },
            "ko": {
                "TOO_GOOD_TO_BE_TRUE": "결과가 지나치게 좋습니다.",
                "FORWARD_LOOKING_INPUT": "미래 데이터 의심.",
                "NEGATIVE_RETURN": "전체 구간 비수익.",
                "INSUFFICIENT_SAMPLE": "관측치 부족.",
                "LOW_FREQUENCY": "저빈도 이벤트형.",
                "BACKGROUND_REQUIRED": "수익 규모가 비정상적.",
                "OOS_NEGATIVE_RETURN": "OOS 손실.",
                "UNDERPERFORMS_HOLD_RISKADJ": "Buy & hold 미달.",
                "RANDOM_CONTROL_NOT_BEATEN": "타이밍 우위 미입증.",
                "OVERFIT_SUSPECT_HOLDOUT": "후반 성과 약화.",
                "RANDOM_CONTROL_WEAK_EDGE": "랜덤 대비 우위 약함.",
                "RANDOM_CONTROL_UNAVAILABLE": "랜덤 대조 불가.",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "운과 구분 어려움.",
                "DSR_FAIL": "선택 운으로 설명 가능.",
                "DSR_OVERFIT_RISK": "보정 후 Sharpe 약함.",
                "SHORT_TRACK_RECORD": "2년 미만 기록.",
                "LOW_EFFECTIVE_SAMPLE": "수익 집중.",
            },
            "es": {
                "TOO_GOOD_TO_BE_TRUE": "Demasiado bueno.",
                "FORWARD_LOOKING_INPUT": "Posible dato futuro.",
                "NEGATIVE_RETURN": "No rentable.",
                "INSUFFICIENT_SAMPLE": "Muestra insuficiente.",
                "LOW_FREQUENCY": "Baja frecuencia.",
                "BACKGROUND_REQUIRED": "Retorno inusualmente grande.",
                "OOS_NEGATIVE_RETURN": "Pierde fuera de muestra.",
                "UNDERPERFORMS_HOLD_RISKADJ": "No supera buy-and-hold.",
                "RANDOM_CONTROL_NOT_BEATEN": "Sin edge de timing.",
                "OVERFIT_SUSPECT_HOLDOUT": "La parte final es débil.",
                "RANDOM_CONTROL_WEAK_EDGE": "Edge débil vs aleatorio.",
                "RANDOM_CONTROL_UNAVAILABLE": "Control aleatorio no disponible.",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "Difícil separar de suerte.",
                "DSR_FAIL": "Sharpe explicable por selección.",
                "DSR_OVERFIT_RISK": "Sharpe débil tras penalización.",
                "SHORT_TRACK_RECORD": "Menos de 2 años.",
                "LOW_EFFECTIVE_SAMPLE": "Beneficio concentrado.",
            },
            "pt-BR": {
                "TOO_GOOD_TO_BE_TRUE": "Bom demais.",
                "FORWARD_LOOKING_INPUT": "Possível dado futuro.",
                "NEGATIVE_RETURN": "Não lucrativo.",
                "INSUFFICIENT_SAMPLE": "Amostra insuficiente.",
                "LOW_FREQUENCY": "Baixa frequência.",
                "BACKGROUND_REQUIRED": "Retorno incomum.",
                "OOS_NEGATIVE_RETURN": "Perde fora da amostra.",
                "UNDERPERFORMS_HOLD_RISKADJ": "Não supera buy-and-hold.",
                "RANDOM_CONTROL_NOT_BEATEN": "Sem edge de timing.",
                "OVERFIT_SUSPECT_HOLDOUT": "Trecho final fraco.",
                "RANDOM_CONTROL_WEAK_EDGE": "Edge fraco vs aleatório.",
                "RANDOM_CONTROL_UNAVAILABLE": "Controle aleatório indisponível.",
                "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "Difícil separar de sorte.",
                "DSR_FAIL": "Sharpe explicado por seleção.",
                "DSR_OVERFIT_RISK": "Sharpe fraco após penalidade.",
                "SHORT_TRACK_RECORD": "Menos de 2 anos.",
                "LOW_EFFECTIVE_SAMPLE": "Lucro concentrado.",
            },
        }
        short = short_by_lang.get(lang, short_by_lang["en"]).get(code)
        if short:
            return short
        text = problem or direction or ""
        text = text.replace("On this asset your results are ", "Results are ")
        text = text.replace("The return scale is unusually large.", "Return scale is unusually large.")
        text = text.replace("Results look too good to be true.", "Looks too good to be true.")
        return text

    fig = plt.figure(figsize=(16, 9), facecolor=_CARD_BG)
    canvas = fig.add_axes([0, 0, 1, 1], zorder=0)
    canvas.set_xlim(0, 1); canvas.set_ylim(0, 1); canvas.axis("off")

    # Header: one stable text object. Do not split the brand glyph; font metrics
    # vary by platform and previously caused visible misalignment.
    fig.text(0.045, 0.925, "QSX Strategy Score", fontsize=28, fontweight="bold",
             color=_CARD_TEXT, va="center")
    fig.text(0.82, 0.925, _png_label("scorecard", lang).upper(),
             fontsize=13, color=_CARD_MUTED, fontweight="bold", va="center")
    fig.text(0.045, 0.885,
             f"{_png_label('period', lang)} {str(m.get('start',''))[:10]} -> {str(m.get('end',''))[:10]} · n={m.get('n')}",
             fontsize=10.5, color=_CARD_FAINT, va="center")
    canvas.plot([0.045, 0.955], [0.855, 0.855], color=_CARD_GREEN, lw=3.0,
                solid_capstyle="butt")

    # Score + verdict.
    score_ax = axis_box([0.045, 0.63, 0.205, 0.205], face="#111820", edge="#2a3647")
    score_ax.text(0.09, 0.82, "QSX SCORE", fontsize=10.5, color=_CARD_MUTED,
                  fontweight="bold", va="top")
    score_ax.text(0.09, 0.47, f"{report.display:.0f}", fontsize=54,
                  fontweight="bold", color=accent, va="center", family="monospace")
    score_ax.text(0.46, 0.34, "/100", fontsize=18, color=_CARD_MUTED, va="center")
    score_ax.add_patch(FancyBboxPatch(
        (0.09, 0.08), 0.72, 0.18, transform=score_ax.transAxes,
        boxstyle="round,pad=0.012,rounding_size=0.045",
        facecolor=accent, edgecolor=accent, linewidth=1.0,
    ))
    score_ax.text(0.45, 0.17, _png_grade(report.grade, lang), fontsize=12.0,
                  color="#071014", fontweight="bold", va="center", ha="center")

    verdict_ax = axis_box([0.275, 0.63, 0.68, 0.205], face="#111820", edge="#2a3647")
    verdict_ax.text(0.035, 0.82, _png_status_word(word, lang).upper(), fontsize=13.5,
                    color=status_color if report.judgement != "OK" else accent,
                    fontweight="bold", va="top")
    add_wrapped(verdict_ax, 0.035, 0.62, headline, width=54 if lang == "en" else 30,
                max_lines=2, fontsize=19 if lang == "en" else 17,
                color=_CARD_TEXT, weight="bold", lineheight=0.18)
    edge_label, edge_text, edge_color = _png_edge_summary(report, lang)
    sample_label, sample_text, sample_color = _png_sample_summary(report, lang)
    checks = [
        (edge_label, _short_png_value(edge_text, 24), edge_color),
        (sample_label, _short_png_value(sample_text, 24), sample_color),
        (
            _png_label("dependency", lang),
            (triage or {}).get("dependency_lite", {}).get("label_local")
            or ((triage or {}).get("dependency_lite", {}).get("label") if (triage or {}).get("dependency_lite", {}).get("available") else t("unavailable", lang)),
            _CARD_AMBER,
        ),
    ]
    for i, (label, value, color) in enumerate(checks):
        x = 0.035 + i * 0.315
        verdict_ax.text(x, 0.22, label.upper(), fontsize=8.3, color=_CARD_MUTED,
                        fontweight="bold", va="bottom")
        verdict_ax.text(x, 0.07, "\n".join(wrap_lines(value, 25, 1)), fontsize=10.8,
                        color=color, fontweight="bold", va="bottom")

    # Four summary metrics.
    mdd = float(report.risk.raw.get("mdd") or 0.0)
    mdd_abs = abs(mdd)
    calmar_value = (float(m.get("cagr") or 0.0) / mdd_abs) if mdd_abs > 1e-12 else 0.0
    metric_y, metric_h, gap = 0.49, 0.115, 0.017
    metric_w = (0.91 - 3 * gap) / 4
    metrics = [
        (_png_label("return_quality", lang), f"{report.return_quality.value:.0f}/100", _grade_color(report.return_quality.value), ""),
        (_png_label("overfit_risk", lang), f"{report.credibility.value:.0f}/100", _grade_color(report.credibility.value), ""),
        (_png_label("maxdd", lang), f"{mdd * 100:.0f}%", _grade_color(report.risk.value), _png_label("historical_path", lang)),
        (_png_label("calmar", lang), f"{calmar_value:.2f}", _grade_color(report.return_quality.value), _png_label("risk_adjusted_return", lang)),
    ]
    for i, item in enumerate(metrics):
        metric_box([0.045 + i * (metric_w + gap), metric_y, metric_w, metric_h], *item)

    # Equity path + key issues.
    chart_ax = axis_box([0.045, 0.18, 0.565, 0.25], face="#0d131b", edge="#2a3647", radius=0.02)
    chart_ax.text(0.025, 0.91, _png_label("equity", lang), fontsize=10.5,
                  color=_CARD_MUTED, fontweight="bold", va="top", transform=chart_ax.transAxes)
    def draw_chart_legend(items: list[tuple[str, str]]) -> None:
        x = 0.18 if lang == "en" else 0.16
        y = 0.91
        for label, color in items:
            chart_ax.plot([x, x + 0.035], [y - 0.015, y - 0.015],
                          transform=chart_ax.transAxes, color=color, lw=3.2,
                          solid_capstyle="round", clip_on=False)
            chart_ax.text(x + 0.045, y - 0.015, label, transform=chart_ax.transAxes,
                          fontsize=9.2, color=_CARD_TEXT, fontweight="bold",
                          va="center")
            x += 0.20 if lang == "en" else 0.16

    inset = fig.add_axes([0.065, 0.205, 0.525, 0.175], facecolor="#0d131b")
    if bench and bench.get("bnh_curve") is not None and report.judgement != "FLAGGED":
        sc, bc = bench["strat_curve"], bench["bnh_curve"]
        draw_chart_legend([
            (_png_label("strategy", lang), _CARD_GREEN),
            (_png_label("buy_hold", lang), _CARD_AMBER),
        ])
        inset.plot(sc.index, sc.values, color=_CARD_GREEN, lw=2.8)
        inset.plot(bc.index, bc.values, color=_CARD_AMBER, lw=2.0, alpha=0.95)
        if bool((sc.values > 0).all() and (bc.values > 0).all()):
            inset.set_yscale("log")
    else:
        draw_chart_legend([(_png_label("strategy", lang), accent)])
        inset.plot(eq.index, eq.values, color=accent, lw=2.8)
        if bool((eq.values > 0).all()):
            inset.set_yscale("log")
    inset.grid(color="white", alpha=0.08, linewidth=0.8)
    inset.xaxis.set_major_formatter(NullFormatter())
    inset.xaxis.set_minor_formatter(NullFormatter())
    inset.yaxis.set_major_formatter(NullFormatter())
    inset.yaxis.set_minor_formatter(NullFormatter())
    inset.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for sp in inset.spines.values():
        sp.set_visible(False)

    issues_ax = axis_box([0.635, 0.18, 0.32, 0.25], face="#0d131b", edge="#2a3647", radius=0.02)
    issues_ax.text(0.055, 0.86, _png_label("issues", lang), fontsize=12,
                   color=_CARD_TEXT, fontweight="bold", va="top")
    y = 0.66
    if co["issues"]:
        for issue in co["issues"][:3]:
            issues_ax.scatter([0.065], [y - 0.01], s=24, color=accent,
                              transform=issues_ax.transAxes, clip_on=False)
            add_wrapped(issues_ax, 0.105, y, compact_issue_text(issue),
                        width=44 if lang == "en" else 20, max_lines=1,
                        fontsize=10.5 if lang == "en" else 10,
                        color=_CARD_TEXT, lineheight=0.12)
            y -= 0.20
    else:
        issues_ax.scatter([0.065], [y - 0.01], s=24, color=_CARD_GREEN,
                          transform=issues_ax.transAxes, clip_on=False)
        add_wrapped(issues_ax, 0.105, y, _png_label("no_issues", lang),
                    width=44 if lang == "en" else 20, max_lines=2,
                    fontsize=10.5, color=_CARD_TEXT, lineheight=0.12)

    fig.text(0.045, 0.085, _png_label("note", lang), fontsize=9.5,
             color=_CARD_FAINT, va="center")
    fig.text(0.68, 0.085, cta or _png_label("audit_report_cta", lang), fontsize=12,
             color=_CARD_GREEN, fontweight="bold", va="center")

    fig.savefig(out_path, dpi=100, facecolor=_CARD_BG)
    plt.close(fig)
    return out_path
