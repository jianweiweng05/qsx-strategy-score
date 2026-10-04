"""Small runtime translation layer for the public/free scorer.

The free package keeps machine-readable fields stable in English, while CLI,
PNG, and app surfaces can render user-facing labels in a supported language.
This is intentionally lightweight: no runtime dependency, no gettext compiler,
and fallback to English for missing strings.
"""
from __future__ import annotations

from typing import Any
import re


SUPPORTED_LANGS = ("en", "zh", "ja", "ko", "es", "pt-BR")


_ALIASES = {
    "zh-cn": "zh",
    "zh-hans": "zh",
    "cn": "zh",
    "jp": "ja",
    "pt": "pt-BR",
    "pt-br": "pt-BR",
    "br": "pt-BR",
}


MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "Return quality",
        "credibility": "Path credibility",
        "overfit_hint": "robustness · consistency · anomaly checks",
        "drawdown_control": "Drawdown control",
        "edge_label": "Edge vs hold/random",
        "sample": "Sample",
        "what_to_look_at": "What to look at",
        "free_triage": "Free triage, not investment advice.",
        "pro_unlocks": "Pro unlocks",
        "pro_unlocks_short": "Pro unlocks: HCRI home field / Exposure X-Ray / Black Swan / Cost & MTM",
        "pro_cta": "Want the full strategy due-diligence report? QuantScopeX Pro tests HCRI home field, Exposure X-Ray, Black Swan events, costs/slippage and true mark-to-market drawdown.",
        "edge_persistence": "Edge persistence",
        "evidence_confidence": "Evidence confidence",
        "dependency_lite": "Dependency lite",
        "stable": "Stable",
        "weakening": "Weakening",
        "deteriorating": "Deteriorating",
        "unavailable": "Unavailable",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "limited": "Limited",
        "adequate": "adequate",
        "thin": "thin",
        "bars": "bars",
        "trades": "trades",
        "score_capped": "score capped",
        "pillars_avg": "pillars average",
        "download_card": "Download shareable PNG card",
        "equity_rebased": "Equity (rebased)",
        "equity_vs_hold": "Equity vs Buy & Hold",
        "drawdown": "Drawdown",
        "monte_carlo": "Monte Carlo",
        "raw_report": "Raw report / metadata",
        "flagged_clean": "score withheld — results too clean to be real",
        "sample_adequate": "sample adequate",
        "sample_thin": "sample thin",
        "edge.beat": "beats hold + random timing",
        "edge.hold_only": "beats buy & hold; random control unavailable",
        "edge.lost": "did NOT beat buy & hold",
        "edge.random_fail": "no edge over random timing",
        "edge.marginal": "only a marginal edge",
        "edge.luck_unclear": "hard to tell from luck",
        "edge.not_evaluated": "not evaluated — add asset K-line",
        "input_type": "Input type",
        "asset_compare": "Asset to compare against",
        "upload_prompt": "Upload a strategy CSV to begin.",
        "headline.flagged": "Looks too good to be true. Verify the backtest before trusting the score.",
        "headline.negative": "Not profitable over the sample.",
        "headline.sample": "Sample too small. Treat this as provisional.",
        "headline.edge_beat": "Beat buy & hold and random timing. A demonstrable edge in this sample.",
        "headline.edge_hold_only": "Beat buy & hold, but random-timing evidence is not available.",
        "headline.edge_lost": "Did not beat buy & hold on a risk-adjusted basis.",
        "headline.edge_random_fail": "Indistinguishable from random timing. No proven timing edge.",
        "headline.edge_marginal": "Only a marginal edge. Promising, but not proven.",
        "headline.edge_unknown": "Add the traded asset K-line to test skill vs luck.",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "Results look too good to be true.",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "Check look-ahead bias, survivorship, fill assumptions, fees, and slippage before trusting the score.",
        "issue.BACKGROUND_REQUIRED.problem": "The return scale is unusually large.",
        "issue.BACKGROUND_REQUIRED.direction": "Verify starting capital, leverage, venue fills, and capacity before treating the result as repeatable.",
        "issue.LOW_FREQUENCY.problem": "Low-frequency/event strategy.",
        "issue.LOW_FREQUENCY.direction": "This is scored as an event-track read; more independent events across regimes will firm it up.",
        "issue.INSUFFICIENT_SAMPLE.problem": "Too few observations.",
        "issue.INSUFFICIENT_SAMPLE.direction": "Gather more observations or extend the test window, then re-score.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "Only marginally beats random timing.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "Strengthen the signal or tighten entries until the edge is clearer.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "Random-timing control did not run.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "Provide entry/exit timestamps and an overlapping asset K-line to run the event-window control.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "Hard to distinguish from luck.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "Add the traded asset K-line to compare against holding and random timing.",
    },
    "zh": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "收益质量",
        "credibility": "路径可信度",
        "overfit_hint": "稳健性 · 一致性 · 异常平滑 · 收益集中",
        "drawdown_control": "回撤控制",
        "edge_label": "相对买入持有和随机择时",
        "sample": "样本",
        "what_to_look_at": "重点检查",
        "free_triage": "免费体检，不构成投资建议。",
        "pro_unlocks": "专业版可解锁",
        "pro_unlocks_short": "专业版可解锁：HCRI 主场、暴露透视、黑天鹅、成本与真实逐日盯市回撤",
        "pro_cta": "想看完整策略尽调？QuantScopeX 专业版会检查 HCRI 主场、暴露透视、黑天鹅事件、成本、滑点和真实逐日盯市回撤。",
        "edge_persistence": "优势持续性",
        "evidence_confidence": "证据可信度",
        "dependency_lite": "轻量依赖扫描",
        "stable": "稳定",
        "weakening": "减弱",
        "deteriorating": "恶化",
        "unavailable": "不可用",
        "high": "高",
        "medium": "中",
        "low": "低",
        "limited": "有限",
        "adequate": "充足",
        "thin": "偏薄",
        "bars": "个数据点",
        "trades": "笔交易",
        "score_capped": "分数封顶",
        "pillars_avg": "三柱均值",
        "download_card": "下载可分享的 PNG 评分卡",
        "equity_rebased": "净值（归一化）",
        "equity_vs_hold": "净值与买入持有对比",
        "drawdown": "回撤",
        "monte_carlo": "蒙特卡洛",
        "raw_report": "原始报告与元数据",
        "flagged_clean": "暂不打分：曲线好得不真实",
        "sample_adequate": "样本充足",
        "sample_thin": "样本偏薄",
        "edge.beat": "跑赢买入持有和随机择时",
        "edge.hold_only": "跑赢买入持有；随机对照不可用",
        "edge.lost": "没跑赢买入持有",
        "edge.random_fail": "没跑赢随机择时",
        "edge.marginal": "优势很薄",
        "edge.luck_unclear": "难以和运气区分",
        "edge.not_evaluated": "未评估：请加入资产 K 线",
        "input_type": "输入类型",
        "asset_compare": "对比资产",
        "upload_prompt": "上传策略 CSV 开始。",
        "headline.flagged": "看着好得不真实。先核回测，再信分数。",
        "headline.negative": "整个样本上没赚钱。",
        "headline.sample": "样本太小，结论只能暂定。",
        "headline.edge_beat": "跑赢买入持有和随机择时，样本内优势可验证。",
        "headline.edge_hold_only": "跑赢买入持有，但随机择时证据不可用。",
        "headline.edge_lost": "风险调整后没跑赢买入持有。",
        "headline.edge_random_fail": "和随机择时无法区分，未证明有择时优势。",
        "headline.edge_marginal": "优势很薄，有潜力但还没证明。",
        "headline.edge_unknown": "加入交易资产的价格序列，才能判断策略能力还是运气。",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "结果好得不真实。",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "先排查未来函数、幸存者偏差、成交假设、手续费和滑点。",
        "issue.BACKGROUND_REQUIRED.problem": "收益规模异常大。",
        "issue.BACKGROUND_REQUIRED.direction": "核实本金、杠杆、成交、容量，再判断是否可复制。",
        "issue.LOW_FREQUENCY.problem": "低频/事件型策略。",
        "issue.LOW_FREQUENCY.direction": "按已有事件评分；跨行情积累更多独立事件后结论会更扎实。",
        "issue.INSUFFICIENT_SAMPLE.problem": "观测太少。",
        "issue.INSUFFICIENT_SAMPLE.direction": "拉长窗口或积累更多观测后再评分。",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "只比随机择时强一点。",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "强化信号或收紧入场条件，让优势更清楚。",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "随机择时对照未运行。",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "补充入场/出场时间和重叠资产 K 线，才能运行事件窗口随机对照。",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "难以和运气区分。",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "加入交易资产 K 线，对比买入持有和随机择时。",
    },
    "ja": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "収益品質",
        "credibility": "経路の信頼性",
        "overfit_hint": "堅牢性 · 一貫性 · 異常検出",
        "drawdown_control": "ドローダウン管理",
        "edge_label": "保有/ランダム比の優位性",
        "sample": "サンプル",
        "what_to_look_at": "確認ポイント",
        "free_triage": "無料診断であり、投資助言ではありません。",
        "pro_unlocks": "Proで確認",
        "pro_unlocks_short": "Pro: HCRI適性 / Exposure X-Ray / ブラックスワン / コストとMTM",
        "pro_cta": "完全な戦略デューデリジェンスでは、HCRI適性、Exposure X-Ray、ブラックスワン、コスト/スリッページ、真のMTMドローダウンを検査します。",
        "edge_persistence": "優位性の持続",
        "evidence_confidence": "証拠信頼度",
        "dependency_lite": "依存度 Lite",
        "stable": "安定",
        "weakening": "弱含み",
        "deteriorating": "悪化",
        "unavailable": "利用不可",
        "high": "高",
        "medium": "中",
        "low": "低",
        "limited": "限定的",
        "adequate": "十分",
        "thin": "薄い",
        "bars": "本",
        "trades": "取引",
        "score_capped": "スコア上限",
        "pillars_avg": "柱平均",
        "download_card": "共有PNGカードをダウンロード",
        "equity_rebased": "エクイティ（基準化）",
        "equity_vs_hold": "エクイティ vs Buy & Hold",
        "drawdown": "ドローダウン",
        "monte_carlo": "モンテカルロ",
        "raw_report": "生レポート / メタデータ",
        "flagged_clean": "スコア保留 — 結果が良すぎます",
        "edge.beat": "保有とランダムを上回る",
        "edge.hold_only": "買い持ちを上回るがランダム対照不可",
        "edge.lost": "買い持ちに劣後",
        "edge.random_fail": "ランダムタイミングに優位性なし",
        "edge.marginal": "優位性はわずか",
        "edge.luck_unclear": "運との区別が難しい",
        "edge.not_evaluated": "未評価 - 資産価格を追加",
        "input_type": "入力タイプ",
        "asset_compare": "比較資産",
        "upload_prompt": "戦略CSVをアップロードしてください。",
        "headline.flagged": "良すぎる結果です。スコアを信じる前にバックテストを検証してください。",
        "headline.negative": "サンプル全体では利益が出ていません。",
        "headline.sample": "サンプルが小さく、結論は暫定です。",
        "headline.edge_beat": "買い持ちとランダムタイミングを上回りました。",
        "headline.edge_hold_only": "買い持ちは上回りましたが、ランダム対照は利用できません。",
        "headline.edge_lost": "リスク調整後で買い持ちを上回っていません。",
        "headline.edge_random_fail": "ランダムタイミングと区別できません。タイミング優位性は証明されていません。",
        "headline.edge_marginal": "優位性はわずかです。まだ証明不足です。",
        "headline.edge_unknown": "取引資産の価格データを追加して、スキルか運かを確認してください。",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "結果が良すぎます。",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "先読み、サバイバーシップ、約定、手数料、スリッページを確認してください。",
        "issue.BACKGROUND_REQUIRED.problem": "リターン規模が異常に大きいです。",
        "issue.BACKGROUND_REQUIRED.direction": "元本、レバレッジ、約定、キャパシティを確認してください。",
        "issue.LOW_FREQUENCY.problem": "低頻度/イベント型戦略です。",
        "issue.LOW_FREQUENCY.direction": "イベント実績として評価します。異なる相場で独立イベントを増やすと信頼度が上がります。",
        "issue.INSUFFICIENT_SAMPLE.problem": "観測数が少なすぎます。",
        "issue.INSUFFICIENT_SAMPLE.direction": "期間を延ばすか観測数を増やしてから再評価してください。",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "ランダムタイミングへの優位性が弱いです。",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "シグナルを強化するかエントリー条件を絞ってください。",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "ランダム対照は実行されませんでした。",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "エントリー/終了時刻と重複する資産価格を追加してください。",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "運との区別が難しいです。",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "取引資産の価格データを追加して比較してください。",
    },
    "ko": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "수익 품질",
        "credibility": "경로 신뢰도",
        "overfit_hint": "견고성 · 일관성 · 이상 징후",
        "drawdown_control": "드로다운 관리",
        "edge_label": "보유/랜덤 대비 우위",
        "sample": "표본",
        "what_to_look_at": "확인할 점",
        "free_triage": "무료 진단이며 투자 조언이 아닙니다.",
        "pro_unlocks": "Pro에서 확인",
        "pro_unlocks_short": "Pro: HCRI 홈필드 / Exposure X-Ray / 블랙스완 / 비용과 MTM",
        "pro_cta": "전체 전략 실사에서는 HCRI 홈필드, Exposure X-Ray, 블랙스완, 비용/슬리피지, 실제 MTM 드로다운을 검사합니다.",
        "edge_persistence": "엣지 지속성",
        "evidence_confidence": "증거 신뢰도",
        "dependency_lite": "의존도 Lite",
        "stable": "안정",
        "weakening": "약화",
        "deteriorating": "악화",
        "unavailable": "사용 불가",
        "high": "높음",
        "medium": "중간",
        "low": "낮음",
        "limited": "제한적",
        "adequate": "충분",
        "thin": "얇음",
        "bars": "바",
        "trades": "거래",
        "score_capped": "점수 상한",
        "pillars_avg": "필러 평균",
        "download_card": "공유 PNG 카드 다운로드",
        "equity_rebased": "에쿼티(리베이스)",
        "equity_vs_hold": "에쿼티 vs Buy & Hold",
        "drawdown": "드로다운",
        "monte_carlo": "몬테카를로",
        "raw_report": "원본 리포트 / 메타데이터",
        "flagged_clean": "점수 보류 — 결과가 지나치게 좋습니다",
        "edge.beat": "보유와 랜덤 타이밍을 상회",
        "edge.hold_only": "매수 보유 상회, 랜덤 대조 불가",
        "edge.lost": "매수 보유보다 낮음",
        "edge.random_fail": "랜덤 타이밍 대비 우위 없음",
        "edge.marginal": "우위가 약함",
        "edge.luck_unclear": "운과 구분이 어려움",
        "edge.not_evaluated": "미평가 - 자산 가격 추가",
        "input_type": "입력 유형",
        "asset_compare": "비교 자산",
        "upload_prompt": "전략 CSV를 업로드하세요.",
        "headline.flagged": "결과가 지나치게 좋습니다. 점수를 믿기 전에 백테스트를 검증하세요.",
        "headline.negative": "전체 표본에서 수익성이 없습니다.",
        "headline.sample": "표본이 작아 결론은 잠정적입니다.",
        "headline.edge_beat": "매수 보유와 랜덤 타이밍을 모두 상회했습니다.",
        "headline.edge_hold_only": "매수 보유는 상회했지만 랜덤 타이밍 증거는 사용할 수 없습니다.",
        "headline.edge_lost": "위험 조정 기준으로 매수 보유를 이기지 못했습니다.",
        "headline.edge_random_fail": "랜덤 타이밍과 구분되지 않습니다. 타이밍 우위가 입증되지 않았습니다.",
        "headline.edge_marginal": "우위가 약합니다. 아직 입증 부족입니다.",
        "headline.edge_unknown": "거래 자산 가격을 추가해 실력과 운을 구분하세요.",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "결과가 지나치게 좋습니다.",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "미래정보, 생존편향, 체결, 수수료, 슬리피지를 확인하세요.",
        "issue.BACKGROUND_REQUIRED.problem": "수익 규모가 비정상적으로 큽니다.",
        "issue.BACKGROUND_REQUIRED.direction": "초기 자본, 레버리지, 체결, 수용 가능 규모를 검증하세요.",
        "issue.LOW_FREQUENCY.problem": "저빈도/이벤트형 전략입니다.",
        "issue.LOW_FREQUENCY.direction": "이벤트 트랙으로 평가합니다. 다양한 장세의 독립 이벤트가 늘수록 신뢰도가 올라갑니다.",
        "issue.INSUFFICIENT_SAMPLE.problem": "관측치가 너무 적습니다.",
        "issue.INSUFFICIENT_SAMPLE.direction": "기간이나 관측치를 늘린 뒤 다시 평가하세요.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "랜덤 타이밍 대비 우위가 약합니다.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "신호를 강화하거나 진입 조건을 좁히세요.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "랜덤 대조를 실행하지 못했습니다.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "진입/청산 시각과 겹치는 자산 가격을 추가하세요.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "운과 구분하기 어렵습니다.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "거래 자산 가격을 추가해 비교하세요.",
    },
    "es": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "Calidad del retorno",
        "credibility": "Credibilidad de trayectoria",
        "overfit_hint": "robustez · consistencia · anomalías",
        "drawdown_control": "Control de drawdown",
        "edge_label": "Ventaja vs hold/azar",
        "sample": "Muestra",
        "what_to_look_at": "Qué revisar",
        "free_triage": "Triage gratuito, no es asesoría de inversión.",
        "pro_unlocks": "Pro desbloquea",
        "pro_unlocks_short": "Pro: HCRI / Exposure X-Ray / cisnes negros / costos y MTM",
        "pro_cta": "El informe Pro revisa HCRI, Exposure X-Ray, eventos de cisne negro, costos/slippage y drawdown MTM real.",
        "edge_persistence": "Persistencia de ventaja",
        "evidence_confidence": "Confianza de evidencia",
        "dependency_lite": "Dependencia Lite",
        "stable": "Estable",
        "weakening": "Debilitándose",
        "deteriorating": "Deteriorando",
        "unavailable": "No disponible",
        "high": "Alta",
        "medium": "Media",
        "low": "Baja",
        "limited": "Limitada",
        "adequate": "adecuada",
        "thin": "débil",
        "bars": "barras",
        "trades": "operaciones",
        "score_capped": "puntaje limitado",
        "pillars_avg": "promedio de pilares",
        "download_card": "Descargar tarjeta PNG",
        "equity_rebased": "Capital (base 1)",
        "equity_vs_hold": "Capital vs Buy & Hold",
        "drawdown": "Drawdown",
        "monte_carlo": "Monte Carlo",
        "raw_report": "Reporte bruto / metadatos",
        "flagged_clean": "puntaje retenido — resultados demasiado buenos",
        "edge.beat": "supera hold y timing aleatorio",
        "edge.hold_only": "supera buy & hold; control aleatorio no disponible",
        "edge.lost": "no supera buy & hold",
        "edge.random_fail": "sin ventaja vs timing aleatorio",
        "edge.marginal": "ventaja marginal",
        "edge.luck_unclear": "difícil separarlo de suerte",
        "edge.not_evaluated": "no evaluado - agrega precios del activo",
        "input_type": "Tipo de entrada",
        "asset_compare": "Activo de comparación",
        "upload_prompt": "Sube un CSV de estrategia para empezar.",
        "headline.flagged": "Los resultados parecen demasiado buenos. Verifica el backtest antes de confiar en el puntaje.",
        "headline.negative": "No es rentable en toda la muestra.",
        "headline.sample": "Muestra demasiado pequeña. La conclusión es provisional.",
        "headline.edge_beat": "Supera buy & hold y timing aleatorio en esta muestra.",
        "headline.edge_hold_only": "Supera buy & hold, pero no hay evidencia de timing aleatorio.",
        "headline.edge_lost": "No supera buy & hold ajustado por riesgo.",
        "headline.edge_random_fail": "No se distingue del timing aleatorio. No demuestra ventaja de timing.",
        "headline.edge_marginal": "La ventaja es marginal. Prometedor, pero no probado.",
        "headline.edge_unknown": "Agrega precios del activo operado para separar habilidad de suerte.",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "Los resultados parecen demasiado buenos.",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "Revisa look-ahead, survivorship, fills, comisiones y slippage.",
        "issue.BACKGROUND_REQUIRED.problem": "La escala de retorno es inusualmente grande.",
        "issue.BACKGROUND_REQUIRED.direction": "Verifica capital inicial, apalancamiento, fills y capacidad antes de asumir repetibilidad.",
        "issue.LOW_FREQUENCY.problem": "Estrategia de baja frecuencia/eventos.",
        "issue.LOW_FREQUENCY.direction": "Se evalúa como historial de eventos; más eventos independientes aumentan la confianza.",
        "issue.INSUFFICIENT_SAMPLE.problem": "Muy pocas observaciones.",
        "issue.INSUFFICIENT_SAMPLE.direction": "Extiende la ventana o reúne más observaciones y vuelve a puntuar.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "Apenas supera el timing aleatorio.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "Fortalece la señal o endurece entradas para que la ventaja sea más clara.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "El control aleatorio no se ejecutó.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "Agrega timestamps de entrada/salida y precios del activo con solape.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "Difícil distinguirlo de suerte.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "Agrega precios del activo para comparar contra hold y timing aleatorio.",
    },
    "pt-BR": {
        "brand": "QuantScopeX Strategy Score",
        "score_title": "QSX Strategy Score",
        "return_quality": "Qualidade do retorno",
        "credibility": "Credibilidade da trajetória",
        "overfit_hint": "robustez · consistência · anomalias",
        "drawdown_control": "Controle de drawdown",
        "edge_label": "Vantagem vs hold/aleatório",
        "sample": "Amostra",
        "what_to_look_at": "O que revisar",
        "free_triage": "Triagem gratuita, não é recomendação de investimento.",
        "pro_unlocks": "Pro desbloqueia",
        "pro_unlocks_short": "Pro: HCRI / Exposure X-Ray / cisnes negros / custos e MTM",
        "pro_cta": "O relatório Pro testa HCRI, Exposure X-Ray, eventos de cisne negro, custos/slippage e drawdown MTM real.",
        "edge_persistence": "Persistência da vantagem",
        "evidence_confidence": "Confiança da evidência",
        "dependency_lite": "Dependência Lite",
        "stable": "Estável",
        "weakening": "Enfraquecendo",
        "deteriorating": "Deteriorando",
        "unavailable": "Indisponível",
        "high": "Alta",
        "medium": "Média",
        "low": "Baixa",
        "limited": "Limitada",
        "adequate": "adequada",
        "thin": "fraca",
        "bars": "barras",
        "trades": "trades",
        "score_capped": "pontuação limitada",
        "pillars_avg": "média dos pilares",
        "download_card": "Baixar card PNG",
        "equity_rebased": "Capital (base 1)",
        "equity_vs_hold": "Capital vs Buy & Hold",
        "drawdown": "Drawdown",
        "monte_carlo": "Monte Carlo",
        "raw_report": "Relatório bruto / metadados",
        "flagged_clean": "pontuação retida — resultado bom demais",
        "edge.beat": "supera hold e timing aleatório",
        "edge.hold_only": "supera buy & hold; controle aleatório indisponível",
        "edge.lost": "não supera buy & hold",
        "edge.random_fail": "sem vantagem vs timing aleatório",
        "edge.marginal": "vantagem marginal",
        "edge.luck_unclear": "difícil separar de sorte",
        "edge.not_evaluated": "não avaliado - adicione preços do ativo",
        "input_type": "Tipo de entrada",
        "asset_compare": "Ativo de comparação",
        "upload_prompt": "Envie um CSV da estratégia para começar.",
        "headline.flagged": "Os resultados parecem bons demais. Verifique o backtest antes de confiar na pontuação.",
        "headline.negative": "Não foi lucrativa na amostra completa.",
        "headline.sample": "Amostra pequena demais. A conclusão é provisória.",
        "headline.edge_beat": "Supera buy & hold e timing aleatório nesta amostra.",
        "headline.edge_hold_only": "Supera buy & hold, mas a evidência de timing aleatório não está disponível.",
        "headline.edge_lost": "Não supera buy & hold ajustado por risco.",
        "headline.edge_random_fail": "Não se distingue de timing aleatório. Não comprova vantagem de timing.",
        "headline.edge_marginal": "A vantagem é marginal. Promissora, mas ainda não provada.",
        "headline.edge_unknown": "Adicione preços do ativo operado para separar habilidade de sorte.",
        "issue.TOO_GOOD_TO_BE_TRUE.problem": "Os resultados parecem bons demais.",
        "issue.TOO_GOOD_TO_BE_TRUE.direction": "Revise look-ahead, survivorship, execução, taxas e slippage.",
        "issue.BACKGROUND_REQUIRED.problem": "A escala de retorno é incomum.",
        "issue.BACKGROUND_REQUIRED.direction": "Verifique capital inicial, alavancagem, execução e capacidade antes de assumir repetibilidade.",
        "issue.LOW_FREQUENCY.problem": "Estratégia de baixa frequência/eventos.",
        "issue.LOW_FREQUENCY.direction": "É avaliada como histórico de eventos; mais eventos independentes aumentam a confiança.",
        "issue.INSUFFICIENT_SAMPLE.problem": "Poucas observações.",
        "issue.INSUFFICIENT_SAMPLE.direction": "Estenda a janela ou reúna mais observações e rode novamente.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.problem": "Apenas supera timing aleatório por pouco.",
        "issue.RANDOM_CONTROL_WEAK_EDGE.direction": "Fortaleça o sinal ou aperte entradas para deixar a vantagem mais clara.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.problem": "O controle aleatório não rodou.",
        "issue.RANDOM_CONTROL_UNAVAILABLE.direction": "Adicione entrada/saída e preços do ativo com sobreposição.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem": "Difícil separar de sorte.",
        "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.direction": "Adicione preços do ativo para comparar com hold e timing aleatório.",
    },
}

_EXTRA_MESSAGES = {
    "en": {
        "next_step": "Next step",
        "evidence_status": "Evidence status",
        "evidence.qualified": "Qualified",
        "evidence.provisional": "Provisional",
        "evidence.insufficient": "Insufficient",
        "next_step.collect_evidence": "Add a benchmark and re-score",
        "next_step.collect_evidence_title": "Complete the free evidence first",
        "next_step.collect_evidence_body": "Select the traded asset or upload its price series. This checks whether the return path beats holding and the available proxy random control.",
        "next_step.overlay": "Run free Overlay Preview",
        "next_step.overlay_title": "Risk path is the next question",
        "next_step.overlay_body": "Test whether an external risk-sizing layer improves drawdown. It does not replace strategy validation.",
        "next_step.pro": "Open full due diligence",
        "next_step.pro_title": "Free screening is complete",
        "next_step.pro_body": "Use the full audit for costs, true MTM drawdown, independent validation, exposure, regimes, stress cases, and capacity.",
        "encouragement.ok": "Solid foundation. Keep refining and re-score after more live or out-of-sample evidence.",
        "encouragement.caution": "Promising, but not proven yet. Firm up the edge and the sample, then re-score.",
        "encouragement.flagged": "Clean up the backtest methodology, rule out artifacts, and run it again.",
    },
    "zh": {
        "next_step": "下一步",
        "evidence_status": "证据状态",
        "evidence.qualified": "证据充分",
        "evidence.provisional": "暂定",
        "evidence.insufficient": "不足",
        "next_step.collect_evidence": "补充基准后重新评分",
        "next_step.collect_evidence_title": "先补齐免费的关键证据",
        "next_step.collect_evidence_body": "选择交易资产或上传其价格序列，检查是否跑赢持有与当前可用的代理随机对照。",
        "next_step.overlay": "运行免费 Overlay Preview",
        "next_step.overlay_title": "下一步检查风险路径",
        "next_step.overlay_body": "测试外部仓位控制能否改善回撤；它不能替代策略验证。",
        "next_step.pro": "打开完整尽调",
        "next_step.pro_title": "免费初筛已完成",
        "next_step.pro_body": "完整尽调用于检查成本、真实逐日盯市回撤、独立验证、暴露、市场环境、压力情景和容量。",
        "encouragement.ok": "底子不错。继续打磨，积累更多样本外或实盘证据后再评分。",
        "encouragement.caution": "有潜力，但还没证明。把优势和样本做扎实，再来评一次。",
        "encouragement.flagged": "先把回测方法理干净、排除假象，再跑一遍。",
    },
    "ja": {
        "sample_adequate": "サンプル十分",
        "sample_thin": "サンプル不足",
        "next_step": "次のステップ",
        "evidence_status": "証拠ステータス",
        "evidence.qualified": "十分",
        "evidence.provisional": "暫定",
        "evidence.insufficient": "不足",
        "next_step.collect_evidence": "ベンチマークを追加して再評価",
        "next_step.collect_evidence_title": "まず無料で補える証拠を追加",
        "next_step.collect_evidence_body": "取引資産または価格系列を追加し、保有と利用可能な代理ランダム対照を比較します。",
        "next_step.overlay": "無料Overlay Previewを実行",
        "next_step.overlay_title": "次はリスク経路を確認",
        "next_step.overlay_body": "外部のリスク調整でドローダウン改善を確認します。戦略検証の代わりにはなりません。",
        "next_step.pro": "完全なデューデリジェンスを開く",
        "next_step.pro_title": "無料診断は完了",
        "next_step.pro_body": "コスト、真のMTM、独立検証、エクスポージャー、環境、ストレス、容量を確認します。",
        "encouragement.ok": "土台は良好です。追加のライブ/OOS証拠を集めて再評価してください。",
        "encouragement.caution": "有望ですが、まだ証明不足です。優位性とサンプルを強化してください。",
        "encouragement.flagged": "バックテスト手法を整理し、アーティファクトを除外して再実行してください。",
    },
    "ko": {
        "sample_adequate": "표본 충분",
        "sample_thin": "표본 부족",
        "next_step": "다음 단계",
        "evidence_status": "증거 상태",
        "evidence.qualified": "충분",
        "evidence.provisional": "잠정",
        "evidence.insufficient": "부족",
        "next_step.collect_evidence": "기준자산을 추가해 다시 평가",
        "next_step.collect_evidence_title": "무료로 보완할 증거부터 추가",
        "next_step.collect_evidence_body": "거래 자산 또는 가격 시계열을 추가해 보유 및 이용 가능한 대리 랜덤 대조와 비교하세요.",
        "next_step.overlay": "무료 Overlay Preview 실행",
        "next_step.overlay_title": "다음은 리스크 경로 점검",
        "next_step.overlay_body": "외부 리스크 조절이 낙폭을 개선하는지 테스트합니다. 전략 검증을 대체하지 않습니다.",
        "next_step.pro": "전체 실사 열기",
        "next_step.pro_title": "무료 진단 완료",
        "next_step.pro_body": "비용, 실제 MTM, 독립 검증, 익스포저, 국면, 스트레스, 수용 능력을 점검합니다.",
        "encouragement.ok": "기초는 좋습니다. 추가 라이브/OOS 증거를 모은 뒤 다시 평가하세요.",
        "encouragement.caution": "가능성은 있지만 아직 입증 부족입니다. 엣지와 표본을 더 단단히 하세요.",
        "encouragement.flagged": "백테스트 방법을 정리하고 인공적인 요인을 제거한 뒤 다시 실행하세요.",
    },
    "es": {
        "sample_adequate": "muestra adecuada",
        "sample_thin": "muestra débil",
        "next_step": "Siguiente paso",
        "evidence_status": "Estado de evidencia",
        "evidence.qualified": "Calificada",
        "evidence.provisional": "Provisional",
        "evidence.insufficient": "Insuficiente",
        "next_step.collect_evidence": "Añade benchmark y reevalúa",
        "next_step.collect_evidence_title": "Completa primero la evidencia gratuita",
        "next_step.collect_evidence_body": "Añade el activo negociado o su serie de precios para comparar contra holding y el control aleatorio disponible.",
        "next_step.overlay": "Ejecutar Overlay Preview gratis",
        "next_step.overlay_title": "El siguiente punto es el riesgo",
        "next_step.overlay_body": "Prueba si un control externo de exposición mejora el drawdown. No reemplaza validar la estrategia.",
        "next_step.pro": "Abrir due diligence completa",
        "next_step.pro_title": "El filtro gratuito terminó",
        "next_step.pro_body": "La auditoría completa revisa costos, MTM real, validación independiente, exposición, regímenes, estrés y capacidad.",
        "encouragement.ok": "Base sólida. Sigue refinando y vuelve a puntuar con más evidencia live/OOS.",
        "encouragement.caution": "Prometedor, pero no probado. Refuerza la ventaja y la muestra, luego reevalúa.",
        "encouragement.flagged": "Limpia la metodología del backtest, descarta artefactos y vuelve a correrlo.",
    },
    "pt-BR": {
        "sample_adequate": "amostra adequada",
        "sample_thin": "amostra fraca",
        "next_step": "Próximo passo",
        "evidence_status": "Status da evidência",
        "evidence.qualified": "Qualificada",
        "evidence.provisional": "Provisória",
        "evidence.insufficient": "Insuficiente",
        "next_step.collect_evidence": "Adicione benchmark e pontue novamente",
        "next_step.collect_evidence_title": "Complete primeiro a evidência gratuita",
        "next_step.collect_evidence_body": "Adicione o ativo negociado ou sua série de preços para comparar com hold e o controle aleatório disponível.",
        "next_step.overlay": "Executar Overlay Preview grátis",
        "next_step.overlay_title": "O próximo ponto é o risco",
        "next_step.overlay_body": "Teste se o controle externo de exposição melhora o drawdown. Não substitui validar a estratégia.",
        "next_step.pro": "Abrir due diligence completa",
        "next_step.pro_title": "A triagem gratuita terminou",
        "next_step.pro_body": "A auditoria completa revisa custos, MTM real, validação independente, exposição, regimes, estresse e capacidade.",
        "encouragement.ok": "Boa base. Continue refinando e rode novamente com mais evidência live/OOS.",
        "encouragement.caution": "Promissor, mas ainda não provado. Fortaleça a vantagem e a amostra, depois reavalie.",
        "encouragement.flagged": "Limpe a metodologia do backtest, descarte artefatos e rode novamente.",
    },
}

for _lang, _items in _EXTRA_MESSAGES.items():
    MESSAGES.setdefault(_lang, {}).update(_items)


_CAP_STATIC = {
    "en": {
        "not net profitable": "not net profitable",
        "input explicitly suggests forward-looking/leaky data": "input explicitly suggests forward-looking/leaky data",
        "sample too small": "sample too small",
        "lost money out-of-sample": "lost money out-of-sample",
        "did not beat buy & hold": "did not beat buy & hold",
        "did not beat random timing": "did not beat random timing",
        "only a marginal edge over random": "only a marginal edge over random",
        "random timing control unavailable": "random timing control unavailable",
        "no asset comparison; hard to tell from luck": "no asset comparison; hard to tell from luck",
        "no asset provided — edge not evaluated": "no asset provided — edge not evaluated",
    },
    "zh": {
        "not net profitable": "整个样本上没赚钱",
        "input explicitly suggests forward-looking/leaky data": "输入明确提示可能含未来函数/泄露数据",
        "sample too small": "样本太小",
        "lost money out-of-sample": "样本外亏钱",
        "did not beat buy & hold": "没跑赢买入持有",
        "did not beat random timing": "没跑赢随机择时",
        "only a marginal edge over random": "相对随机择时只有微弱优势",
        "random timing control unavailable": "随机择时对照不可用",
        "no asset comparison; hard to tell from luck": "没有资产对比，难以和运气区分",
        "no asset provided — edge not evaluated": "未提供资产，优势未评估",
    },
    "ja": {
        "not net profitable": "全期間で利益がありません",
        "input explicitly suggests forward-looking/leaky data": "入力名が先読み/リークを示唆",
        "sample too small": "サンプルが小さすぎます",
        "lost money out-of-sample": "アウトオブサンプルで損失",
        "did not beat buy & hold": "Buy & Holdを上回っていません",
        "did not beat random timing": "ランダムタイミングを上回っていません",
        "only a marginal edge over random": "ランダム比の優位性がわずかです",
        "random timing control unavailable": "ランダム対照が利用できません",
        "no asset comparison; hard to tell from luck": "資産比較がなく、運との区別が困難",
        "no asset provided — edge not evaluated": "資産未指定 — 優位性は未評価",
    },
    "ko": {
        "not net profitable": "전체 구간에서 수익이 없습니다",
        "input explicitly suggests forward-looking/leaky data": "입력명이 미래정보/누수를 시사합니다",
        "sample too small": "표본이 너무 작습니다",
        "lost money out-of-sample": "OOS 구간에서 손실",
        "did not beat buy & hold": "Buy & Hold를 이기지 못했습니다",
        "did not beat random timing": "랜덤 타이밍을 이기지 못했습니다",
        "only a marginal edge over random": "랜덤 대비 우위가 약합니다",
        "random timing control unavailable": "랜덤 대조를 사용할 수 없습니다",
        "no asset comparison; hard to tell from luck": "자산 비교가 없어 운과 구분하기 어렵습니다",
        "no asset provided — edge not evaluated": "자산 미제공 — 엣지 미평가",
    },
    "es": {
        "not net profitable": "no rentable",
        "input explicitly suggests forward-looking/leaky data": "la entrada sugiere datos futuros/leakage",
        "sample too small": "muestra demasiado pequeña",
        "lost money out-of-sample": "pierde fuera de muestra",
        "did not beat buy & hold": "no supera buy & hold",
        "did not beat random timing": "no supera timing aleatorio",
        "only a marginal edge over random": "ventaja marginal vs aleatorio",
        "random timing control unavailable": "control aleatorio no disponible",
        "no asset comparison; hard to tell from luck": "sin comparación de activo; difícil separar de suerte",
        "no asset provided — edge not evaluated": "sin activo — ventaja no evaluada",
    },
    "pt-BR": {
        "not net profitable": "não lucrativo",
        "input explicitly suggests forward-looking/leaky data": "a entrada sugere dados futuros/vazamento",
        "sample too small": "amostra pequena demais",
        "lost money out-of-sample": "perde fora da amostra",
        "did not beat buy & hold": "não supera buy & hold",
        "did not beat random timing": "não supera timing aleatório",
        "only a marginal edge over random": "vantagem marginal vs aleatório",
        "random timing control unavailable": "controle aleatório indisponível",
        "no asset comparison; hard to tell from luck": "sem comparação de ativo; difícil separar de sorte",
        "no asset provided — edge not evaluated": "sem ativo — vantagem não avaliada",
    },
}


def localize_cap_reason(reason: str, lang: str | None = "en") -> str:
    lang = normalize_lang(lang)
    static = _CAP_STATIC.get(lang, _CAP_STATIC["en"])
    if reason in static:
        return static[reason]

    m = re.match(r"approximate DSR below 50% after (\d+) reported trials \(DSR (.+)\)$", reason)
    if m:
        count, value = m.groups()
        return {
            "en": f"Approximate DSR below 50% after {count} reported trials (DSR {value})",
            "zh": f"按自报 {count} 次搜索估计，近似 DSR 低于 50%（DSR {value}）",
            "ja": f"申告 {count} 回の探索後、近似DSRは50%未満（DSR {value}）",
            "ko": f"신고 탐색 {count}회 후 근사 DSR이 50% 미만 (DSR {value})",
            "es": f"DSR aproximado inferior al 50% tras {count} pruebas declaradas (DSR {value})",
            "pt-BR": f"DSR aproximado inferior a 50% após {count} tentativas declaradas (DSR {value})",
        }[lang]
    m = re.match(r"Sharpe does not clearly survive (\d+) search trials \(DSR (.+)\)$", reason)
    if m:
        if lang == "zh":
            return f"夏普扛不住你报告的 {m.group(1)} 次海选（DSR {m.group(2)}）"
        if lang == "ja":
            return f"Sharpeは {m.group(1)} 回の探索に耐えません（DSR {m.group(2)}）"
        if lang == "ko":
            return f"Sharpe가 {m.group(1)}회 탐색 후 약합니다 (DSR {m.group(2)})"
        if lang == "es":
            return f"Sharpe no sobrevive claramente {m.group(1)} búsquedas (DSR {m.group(2)})"
        if lang == "pt-BR":
            return f"Sharpe não sobrevive claramente {m.group(1)} buscas (DSR {m.group(2)})"
    m = re.match(r"only (.+)y of history — Gold/Silver need (\d+)y\+$", reason)
    if m:
        if lang == "zh":
            return f"只有 {m.group(1)} 年历史——金/银牌需 {m.group(2)} 年以上"
        if lang == "ja":
            return f"履歴は {m.group(1)} 年のみ — Gold/Silverには {m.group(2)} 年以上が必要"
        if lang == "ko":
            return f"기록 {m.group(1)}년 — Gold/Silver는 {m.group(2)}년 이상 필요"
        if lang == "es":
            return f"solo {m.group(1)} años de historial — Gold/Silver requiere {m.group(2)}+ años"
        if lang == "pt-BR":
            return f"apenas {m.group(1)} anos de histórico — Gold/Silver exige {m.group(2)}+ anos"
    m = re.match(r"profit concentrated in ~(\d+) effective trades — Gold/Silver need a broader base$", reason)
    if m:
        if lang == "zh":
            return f"利润集中在约 {m.group(1)} 笔有效交易上——金/银牌需要更宽的基础"
        if lang == "ja":
            return f"利益が約 {m.group(1)} 件の有効取引に集中 — Gold/Silverには広い基盤が必要"
        if lang == "ko":
            return f"수익이 약 {m.group(1)}개 유효 거래에 집중 — Gold/Silver는 더 넓은 기반 필요"
        if lang == "es":
            return f"ganancia concentrada en ~{m.group(1)} trades efectivos — Gold/Silver necesita base más amplia"
        if lang == "pt-BR":
            return f"lucro concentrado em ~{m.group(1)} trades efetivos — Gold/Silver exige base mais ampla"
    return reason


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return "en"
    raw = str(lang).strip()
    if not raw or raw.lower() == "auto":
        return "en"
    key = _ALIASES.get(raw.lower(), raw)
    if key in SUPPORTED_LANGS:
        return key
    base = key.split("-", 1)[0].lower()
    return _ALIASES.get(base, base) if _ALIASES.get(base, base) in SUPPORTED_LANGS else "en"


def localize_flag_message(code: str | None, message: str | None, lang: str | None = "en") -> str:
    """Translate user-facing scoring flags, including numeric diagnostics.

    Flag ``msg`` remains the stable English machine-facing field.  Clients use
    this companion value so dynamic values such as autocorrelation, Sharpe,
    CAGR, and drawdown remain visible without leaking the English template.
    """
    lang = normalize_lang(lang)
    code = str(code or "")
    raw = str(message or "")
    if code == "ACCOUNT_PATH_REQUIRED":
        return t("account_path_required", lang)
    static_keys = {
        "TOO_GOOD_TO_BE_TRUE": "issue.TOO_GOOD_TO_BE_TRUE.problem",
        "BACKGROUND_REQUIRED": "issue.BACKGROUND_REQUIRED.problem",
        "LOW_FREQUENCY": "issue.LOW_FREQUENCY.problem",
        "INSUFFICIENT_SAMPLE": "issue.INSUFFICIENT_SAMPLE.problem",
        "RANDOM_CONTROL_WEAK_EDGE": "issue.RANDOM_CONTROL_WEAK_EDGE.problem",
        "RANDOM_CONTROL_UNAVAILABLE": "issue.RANDOM_CONTROL_UNAVAILABLE.problem",
        "EDGE_HARD_TO_DISTINGUISH_FROM_LUCK": "issue.EDGE_HARD_TO_DISTINGUISH_FROM_LUCK.problem",
        "NEGATIVE_RETURN": "issue.NEGATIVE_RETURN.problem",
        "OOS_NEGATIVE_RETURN": "issue.OOS_NEGATIVE_RETURN.problem",
        "UNDERPERFORMS_HOLD_RISKADJ": "issue.UNDERPERFORMS_HOLD_RISKADJ.problem",
        "RANDOM_CONTROL_NOT_BEATEN": "issue.RANDOM_CONTROL_NOT_BEATEN.problem",
        "OVERFIT_SUSPECT_HOLDOUT": "issue.OVERFIT_SUSPECT_HOLDOUT.problem",
        "DSR_FAIL": "issue.DSR_FAIL.problem",
        "DSR_OVERFIT_RISK": "issue.DSR_OVERFIT_RISK.problem",
        "SHORT_TRACK_RECORD": "issue.SHORT_TRACK_RECORD.problem",
        "LOW_EFFECTIVE_SAMPLE": "issue.LOW_EFFECTIVE_SAMPLE.problem",
    }
    key = static_keys.get(code)
    if key and has_message(key, lang):
        return t(key, lang)

    m = re.search(r"lag-1 return autocorr ([0-9.\-]+)", raw)
    if code == "STALE_OR_INTERPOLATED" and m:
        value = m.group(1)
        return {
            "en": f"Lag-1 return autocorrelation is {value}: equity may be interpolated or stale-marked.",
            "zh": f"一阶收益自相关为 {value}：净值曲线可能经过插值或被标记为不变。",
            "ja": f"1期リターン自己相関は {value}：株価曲線が補間または据え置き処理された可能性があります。",
            "ko": f"1시차 수익 자기상관은 {value}입니다. 자산 곡선이 보간되었거나 고정 표시되었을 수 있습니다.",
            "es": f"La autocorrelación de retorno de primer rezago es {value}: la curva puede estar interpolada o marcada como estática.",
            "pt-BR": f"A autocorrelação do retorno no primeiro lag é {value}: a curva pode ter sido interpolada ou marcada como estática.",
        }[lang]

    m = re.search(r"annualized Sharpe ([0-9.\-]+)", raw)
    if code == "SHARPE_TOO_GOOD" and m:
        value = m.group(1)
        return {
            "en": f"Annualized Sharpe {value} is implausibly high for this asset class.",
            "zh": f"年化夏普 {value} 对该资产类别来说异常高。",
            "ja": f"年率換算Sharpe {value} はこの資産クラスには不自然に高すぎます。",
            "ko": f"연환산 Sharpe {value}은(는) 이 자산군에 비해 비현실적으로 높습니다.",
            "es": f"El Sharpe anualizado {value} es inverosímilmente alto para esta clase de activo.",
            "pt-BR": f"O Sharpe anualizado {value} é implausivelmente alto para esta classe de ativo.",
        }[lang]

    m = re.search(r"([0-9.]+)% of periods positive with only ([0-9.\-]+)% drawdown", raw)
    if code == "NEAR_MONOTONIC" and m:
        positive, drawdown = m.groups()
        return {
            "en": f"{positive}% of periods are positive with only {drawdown}% drawdown: suspiciously smooth.",
            "zh": f"{positive}% 的时间段为正，回撤却只有 {drawdown}%：曲线异常平滑。",
            "ja": f"期間の {positive}% がプラスで、ドローダウンは {drawdown}% のみ：不自然に滑らかです。",
            "ko": f"전체 구간의 {positive}%가 플러스인데 낙폭은 {drawdown}%에 불과합니다. 지나치게 매끄럽습니다.",
            "es": f"El {positive}% de los periodos es positivo con solo {drawdown}% de drawdown: demasiado uniforme.",
            "pt-BR": f"{positive}% dos períodos são positivos com apenas {drawdown}% de drawdown: suavidade suspeita.",
        }[lang]

    if code == "BACKGROUND_CAGR":
        m = re.search(r"CAGR ([0-9.\-]+)%/yr sustained over ([0-9.]+)y", raw)
        if m:
            cagr, years = m.groups()
            return {
                "en": f"CAGR {cagr}%/yr sustained for {years} years: verify capital, leverage, fills, and capacity.",
                "zh": f"年化收益率 {cagr}% 持续 {years} 年：核实本金、杠杆、成交和容量。",
                "ja": f"年率 {cagr}% が {years} 年継続：元本、レバレッジ、約定、容量を確認してください。",
                "ko": f"연환산 수익률 {cagr}%가 {years}년 지속되었습니다. 원금, 레버리지, 체결, 수용력을 확인하세요.",
                "es": f"CAGR del {cagr}%/año durante {years} años: verifica capital, apalancamiento, ejecuciones y capacidad.",
                "pt-BR": f"CAGR de {cagr}%/ano por {years} anos: verifique capital, alavancagem, execuções e capacidade.",
            }[lang]
    if code == "BACKGROUND_CALMAR":
        m = re.search(r"Calmar ([0-9.\-]+) \(>10\)", raw)
        if m:
            value = m.group(1)
            return {
                "en": f"Calmar {value} (>10): verify mark-to-market drawdowns, leverage, and fills before treating it as scalable.",
                "zh": f"Calmar {value}（>10）：把它当作可扩展结果前，先核实逐日盯市回撤、杠杆和成交。",
                "ja": f"Calmar {value}（>10）：拡張可能とみなす前に、時価評価ドローダウン、レバレッジ、約定を確認してください。",
                "ko": f"Calmar {value}(>10)입니다. 확장 가능한 결과로 보기 전에 시가평가 낙폭, 레버리지, 체결을 확인하세요.",
                "es": f"Calmar {value} (>10): verifica drawdown a mercado, apalancamiento y ejecuciones antes de escalarlo.",
                "pt-BR": f"Calmar {value} (>10): verifique drawdown a mercado, alavancagem e execuções antes de tratá-lo como escalável.",
            }[lang]
    if code == "BACKGROUND_GROWTH":
        m = re.search(r"equity grew ([0-9,]+)x over the sample", raw)
        if m:
            value = m.group(1)
            return {
                "en": f"Equity grew {value}x over the sample: verify capital base, leverage, liquidity, and survivorship.",
                "zh": f"样本期净值增长 {value} 倍：核实本金、杠杆、流动性和幸存者偏差。",
                "ja": f"サンプル期間で株価曲線が {value} 倍に成長：元本、レバレッジ、流動性、生存者バイアスを確認してください。",
                "ko": f"표본 기간 자산 곡선이 {value}배 증가했습니다. 원금, 레버리지, 유동성, 생존자 편향을 확인하세요.",
                "es": f"El capital creció {value}x en la muestra: verifica base de capital, apalancamiento, liquidez y supervivencia.",
                "pt-BR": f"O patrimônio cresceu {value}x na amostra: verifique capital, alavancagem, liquidez e sobrevivência.",
            }[lang]
    return raw


def t(key: str, lang: str | None = "en", **kwargs: Any) -> str:
    lang = normalize_lang(lang)
    text = MESSAGES.get(lang, {}).get(key) or MESSAGES["en"].get(key) or key
    return text.format(**kwargs) if kwargs else text


def has_message(key: str, lang: str | None = "en") -> bool:
    lang = normalize_lang(lang)
    return key in MESSAGES.get(lang, {}) or key in MESSAGES["en"]


# v0.4 evidence boundaries. Keep these shared by text, downloads and the app.
_V040_COPY = {
    "en": ["Trade statistics only", "Account performance, drawdown, Monte Carlo and ratings: N/A. Upload actual account NAV/returns; closed trades do not reveal the account path.", "Trades: {n}  |  Win rate: {win:.1%}", "Mean: {mean:.2%}  |  Median: {median:.2%}  |  Best: {best:.2%}  |  Worst: {worst:.2%}", "Path risk (excludes search)", "Search trials: {trials}. Approximate DSR: {dsr}. Single-curve variance proxy; positive skew capped; not a causal diagnosis.", "unknown", "Upload account NAV/returns", "Historical bootstrap profit share", "Reported search trials (0 = unknown)"],
    "zh": ["仅交易描述统计", "账户绩效、回撤、蒙特卡洛与评级：N/A。请上传真实账户净值或收益序列；已平仓交易不能还原账户路径。", "交易数：{n}  |  胜率：{win:.1%}", "均值：{mean:.2%}  |  中位数：{median:.2%}  |  最佳：{best:.2%}  |  最差：{worst:.2%}", "路径风险（不含搜索）", "搜索次数：{trials}。近似 DSR：{dsr}。采用单曲线方差代理，限制正偏度；不能据此归因于运气。", "未知", "上传账户净值或收益序列", "历史重采样盈利占比", "自报搜索次数（0 表示未知）"],
    "ja": ["取引の記述統計のみ", "口座成績・ドローダウン・モンテカルロ・格付け：N/A。実際の口座NAVまたはリターンをアップロードしてください。決済取引だけでは口座経路は分かりません。", "取引数：{n}  |  勝率：{win:.1%}", "平均：{mean:.2%}  |  中央値：{median:.2%}  |  最良：{best:.2%}  |  最悪：{worst:.2%}", "経路リスク（探索を除く）", "探索回数：{trials}。近似DSR：{dsr}。単一曲線の分散代理、正の歪度を制限。因果診断ではありません。", "不明", "口座NAV・リターンを追加", "過去再標本化の利益比率", "申告探索回数（0＝不明）"],
    "ko": ["거래 기술 통계만 제공", "계좌 성과, 낙폭, 몬테카를로, 등급: N/A. 실제 계좌 NAV 또는 수익률을 업로드하세요. 청산 거래만으로 계좌 경로를 알 수 없습니다.", "거래 수: {n}  |  승률: {win:.1%}", "평균: {mean:.2%}  |  중앙값: {median:.2%}  |  최고: {best:.2%}  |  최저: {worst:.2%}", "경로 위험 (탐색 제외)", "탐색 횟수: {trials}. 근사 DSR: {dsr}. 단일 곡선 분산 대용치, 양의 왜도 제한. 인과 진단이 아닙니다.", "알 수 없음", "계좌 NAV/수익률 업로드", "과거 재표본 수익 비율", "신고 탐색 횟수 (0 = 알 수 없음)"],
    "es": ["Solo estadísticas de operaciones", "Rendimiento de cuenta, drawdown, Monte Carlo y calificación: N/A. Sube NAV o retornos reales de la cuenta; las operaciones cerradas no revelan su trayectoria.", "Operaciones: {n}  |  Aciertos: {win:.1%}", "Media: {mean:.2%}  |  Mediana: {median:.2%}  |  Mejor: {best:.2%}  |  Peor: {worst:.2%}", "Riesgo de trayectoria (sin búsqueda)", "Pruebas de búsqueda: {trials}. DSR aproximado: {dsr}. Proxy de varianza de una curva; asimetría positiva limitada; no es diagnóstico causal.", "desconocidas", "Subir NAV/retornos de cuenta", "Proporción rentable del remuestreo histórico", "Pruebas declaradas (0 = desconocidas)"],
    "pt-BR": ["Apenas estatísticas de operações", "Desempenho da conta, drawdown, Monte Carlo e classificação: N/A. Envie NAV ou retornos reais da conta; operações encerradas não revelam sua trajetória.", "Operações: {n}  |  Acertos: {win:.1%}", "Média: {mean:.2%}  |  Mediana: {median:.2%}  |  Melhor: {best:.2%}  |  Pior: {worst:.2%}", "Risco da trajetória (sem busca)", "Tentativas de busca: {trials}. DSR aproximado: {dsr}. Proxy de variância de uma curva; assimetria positiva limitada; não é diagnóstico causal.", "desconhecidas", "Enviar NAV/retornos da conta", "Proporção lucrativa da reamostragem histórica", "Tentativas declaradas (0 = desconhecidas)"],
}
for _lang, _values in _V040_COPY.items():
    MESSAGES[_lang].update(dict(zip(("trade_only_title", "account_path_required", "trade_count_win", "trade_return_stats", "path_risk", "search_method", "search_unknown", "upload_account_path", "bootstrap_profit_share", "search_trials_input"), _values)))


for _lang, _direction in {
    "en": "Use actual account NAV/returns and a matching daily benchmark; unsupported exposures remain N/A.",
    "zh": "使用真实账户净值/收益及匹配的日频基准；超出支持范围的敞口仍为 N/A。",
    "ja": "実際の口座NAV・リターンと一致する日次基準を使用してください。範囲外のエクスポージャーはN/Aです。",
    "ko": "실제 계좌 NAV/수익률과 일치하는 일별 벤치마크를 사용하세요. 지원 범위 밖 노출은 N/A입니다.",
    "es": "Usa NAV/retornos reales y un benchmark diario compatible; las exposiciones no admitidas siguen en N/A.",
    "pt-BR": "Use NAV/retornos reais e um benchmark diário compatível; exposições não suportadas permanecem N/A.",
}.items():
    MESSAGES[_lang]["issue.RANDOM_CONTROL_UNAVAILABLE.direction"] = _direction

# Short, concrete reasons shared by CLI, report artifacts and client payloads.
_UNAVAILABLE_COPY = {
    "BENCHMARK_MISSING": ["No matching benchmark was supplied.", "尚未提供匹配基准。", "一致する基準がありません。", "일치하는 벤치마크가 없습니다.", "Falta un benchmark compatible.", "Falta um benchmark compatível."],
    "UNSUPPORTED_OR_SATURATED_EXPOSURE": ["Exposure is near zero, saturated or outside the proxy range.", "敞口接近零、已饱和或超出代理支持范围。", "エクスポージャーがゼロ付近・飽和・対象範囲外です。", "노출이 0에 가깝거나 포화 또는 지원 범위 밖입니다.", "Exposición casi nula, saturada o fuera del proxy.", "Exposição quase nula, saturada ou fora do proxy."],
    "STATIC_EXPOSURE_NOT_BEATEN": ["The matched static exposure reference was not beaten.", "未跑赢匹配的恒定敞口参考。", "一致する固定エクスポージャー基準を上回っていません。", "일치하는 고정 노출 기준을 이기지 못했습니다.", "No supera la referencia de exposición fija.", "Não supera a referência de exposição fixa."],
    "NATIVE_STATIC_REFERENCE_UNAVAILABLE": ["Intraday data need a benchmark on the same complete native grid.", "日内数据需要同一完整原始频率的基准。", "日中データには同じ完全な元の頻度の基準が必要です。", "일중 데이터에는 동일한 완전한 원래 빈도의 벤치마크가 필요합니다.", "Los datos intradía necesitan un benchmark con la misma cuadrícula completa.", "Dados intradiários precisam de benchmark na mesma grade completa."],
    "INSUFFICIENT_PAIRED_DAYS": ["Fewer than 120 paired daily intervals.", "共同日频区间不足 120 个。", "対応する日次区間が120未満です。", "대응하는 일별 구간이 120개 미만입니다.", "Menos de 120 intervalos diarios emparejados.", "Menos de 120 intervalos diários pareados."],
    "DAILY_ENDPOINTS_UNAVAILABLE": ["The two paths do not share a daily cutoff.", "两条路径没有共同日末时点。", "両経路の日次締め時刻が一致しません。", "두 경로의 일별 마감 시점이 다릅니다.", "Las trayectorias no comparten cierre diario.", "As trajetórias não compartilham fechamento diário."],
    "MISSING_DAILY_ENDPOINTS": ["Strategy NAV is missing required benchmark endpoints.", "策略净值缺少基准所需的共同端点。", "戦略NAVに必要な基準端点がありません。", "전략 NAV에 필요한 벤치마크 끝점이 없습니다.", "Faltan puntos NAV requeridos por el benchmark.", "Faltam pontos NAV exigidos pelo benchmark."],
    "DEGENERATE_RANDOM_CONTROL": ["Random reference paths have no usable dispersion.", "随机参考路径没有可用的离散度。", "ランダム基準に有効なばらつきがありません。", "무작위 기준 경로에 유효한 분산이 없습니다.", "Las referencias aleatorias carecen de dispersión útil.", "As referências aleatórias não têm dispersão útil."],
    "MATCHED_COST_MODEL_REQUIRED": ["Matched execution costs cannot be inferred from returns.", "无法从收益序列推断匹配的交易成本。", "リターンから一致する取引費用は推定できません。", "수익률로 동일한 거래 비용을 추정할 수 없습니다.", "No se pueden inferir costes comparables de los retornos.", "Não é possível inferir custos comparáveis dos retornos."],
}
_UNAVAILABLE_COPY["NATIVE_STATIC_EXPOSURE_NOT_BEATEN"] = _UNAVAILABLE_COPY["STATIC_EXPOSURE_NOT_BEATEN"]
_UNAVAILABLE_COPY["AMBIGUOUS_DAILY_CUTOFF"] = _UNAVAILABLE_COPY["DAILY_ENDPOINTS_UNAVAILABLE"]
_UNAVAILABLE_COPY["ZERO_BENCHMARK_VARIANCE"] = _UNAVAILABLE_COPY["DEGENERATE_RANDOM_CONTROL"]


def unavailable_reason(code: str, lang="en") -> str:
    if code == "ACCOUNT_PATH_REQUIRED":
        return t("account_path_required", lang)
    langs = ["en", "zh", "ja", "ko", "es", "pt-BR"]
    values = _UNAVAILABLE_COPY.get(code)
    return values[langs.index(normalize_lang(lang))] if values else str(code).replace("_", " ").lower()


for _lang, _copy in zip(["en", "zh", "ja", "ko", "es", "pt-BR"], [
    ["Daily proxy comparison only; not timing certification.", "Review comparison limits", "Random control: N/A"],
    ["仅为日级代理比较，不是择时能力认证。", "查看对照适用范围", "随机对照：N/A"],
    ["日次代理の比較のみ。タイミング能力の認証ではありません。", "比較の適用範囲を確認", "ランダム対照：N/A"],
    ["일별 대용치 비교이며 타이밍 능력 인증이 아닙니다.", "비교 적용 범위 확인", "무작위 대조: N/A"],
    ["Solo comparación de proxies diarios; no certifica timing.", "Revisar límites de comparación", "Control aleatorio: N/A"],
    ["Apenas comparação de proxies diários; não certifica timing.", "Revisar limites da comparação", "Controle aleatório: N/A"],
]):
    MESSAGES[_lang].update(dict(zip(("proxy_scope", "review_comparison_limits", "random_na"), _copy)))

for _lang in SUPPORTED_LANGS:
    MESSAGES[_lang]["headline.edge_beat"] = MESSAGES[_lang]["proxy_scope"]
