"""QuantScopeX Strategy Score Streamlit demo.

This app mirrors the public QuantScopeX score page: a focused dark tool surface,
not Streamlit's default sidebar-heavy demo. The scoring engine remains local and
open-source; only the presentation layer lives here.
"""
from __future__ import annotations

import os
import sys
import tempfile
import base64
from html import escape
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import streamlit as st

from qsx_strategy_score import build_triage_diagnostics, load_returns, score_unified, coaching
from qsx_strategy_score import assets as asset_lib
from qsx_strategy_score.asset_library import detect_asset, asset_close
from qsx_strategy_score.i18n import SUPPORTED_LANGS, t
from qsx_strategy_score.io import load_prices
from qsx_strategy_score.metrics import benchmark_compare, calmar, cagr, equity_curve, max_drawdown, monte_carlo, sharpe, sortino
from qsx_strategy_score.overlay_client import OverlayPreviewError, run_overlay_preview, trade_log_to_daily_overlay_returns
from qsx_strategy_score.report import render_unified_png


AUTO_ASSET = "__auto__"
SKIP_ASSET = "__skip__"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ASSET_KEYS = asset_lib.available_keys()
ASSET_LABELS = {k: f"{k} - {asset_lib.ASSET_BY_KEY[k].name}" for k in ASSET_KEYS}

LANG_LABELS = {
    "en": "English",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "pt-BR": "Português (BR)",
}

COPY = {
    "en": {
        "nav_score": "Scorecard",
        "eyebrow": "Free strategy scorecard",
        "title": "Is your backtest real?",
        "subtitle": "Upload returns, equity, or trades. Get a 0-100 score, core metrics, overfit/risk checks, Monte Carlo, Overlay, and a shareable card.",
        "subtitle_assets": "Benchmarks: crypto, US stocks/ETFs, global indices, China A-share ETFs, Hong Kong, metals, energy, bonds, and FX.",
        "language": "Language",
        "upload_title": "Drop a strategy file, or click to choose",
        "upload_help": "Return series (date,return), equity curve (date,equity), or trade log (entry/exit/pnl_pct).",
        "strategy_file": "Strategy file",
        "upload_size_help": "Maximum file size: 10 MB.",
        "upload_too_large": "File is larger than 10 MB. Please upload a smaller return, equity, or trade-log file.",
        "input_type": "Input type",
        "input_auto": "Auto",
        "input_returns": "Returns",
        "input_equity": "Equity",
        "input_trade_log": "Trade log",
        "benchmark_asset": "Benchmark asset",
        "benchmark_help": "Pick the asset you traded. Auto-detect is only a starting point.",
        "custom_benchmark": "Custom benchmark K-line",
        "custom_help": "Optional price CSV/TSV/Excel with a close column. This overrides the asset selector.",
        "auto_asset": "Auto-detect from strategy file",
        "skip_asset": "No asset comparison",
        "ready_title": "Data cleaned and ready",
        "waiting_title": "Waiting for upload",
        "waiting_body": "Choose a strategy file to generate the free scorecard.",
        "using_custom": "Using your uploaded benchmark K-line.",
        "manual_asset": "Using manual benchmark",
        "auto_detected": "Auto-detected",
        "auto_failed": "Could not auto-detect the traded asset. Choose a benchmark above.",
        "asset_skipped": "Asset comparison skipped. Skill-vs-luck tests will be incomplete.",
        "asset_overlap_warn": "Benchmark prices do not overlap the strategy dates, so comparison was skipped.",
        "read_error": "Could not read the strategy file",
        "bench_error": "Could not read the benchmark file",
        "sample": "Sample",
        "track_record": "Track record",
        "years": "years",
        "thin_sample": "thin - provisional",
        "adequate_sample": "adequate",
        "cap_prefix": "Score capped",
        "pillars": "Capability pillars",
        "return_quality": "Return quality",
        "credibility": "Overfit-risk detection",
        "risk": "Drawdown control",
        "sharpe": "Sharpe",
        "maxdd": "MaxDD",
        "cred_hint": "robustness · consistency · anomaly checks",
        "triage": "Free due-diligence lite",
        "dependency": "Dependency lite",
        "unavailable": "Unavailable",
        "issues": "What to look at",
        "overlay_title": "Free QSX Overlay Preview",
        "overlay_body": "Run QSX Overlay Preview on your own return or NAV curve. It tests QSX Crypto Universal Position Engine 1.0 as an external risk-control layer before you do anything else.",
        "overlay_button": "Run free QSX Overlay Preview",
        "overlay_privacy": "Only normalized daily date-return rows are transmitted. Raw files, filenames, trade logs, strategy code and account information remain on your machine.",
        "overlay_online": "Uses QuantScopeX hosted API; no production overlay series is bundled in this open-source repo.",
        "overlay_trade_log_note": "Trade-log Overlay Preview rejects overlapping per-position trades. Upload an equity curve or daily returns so the preview uses the aggregate strategy path.",
        "overlay_hash": "Input SHA256",
        "overlay_unavailable": "Overlay preview unavailable",
        "equity_vs_hold": "Strategy vs buy & hold",
        "equity": "Equity (rebased)",
        "drawdown": "Drawdown",
        "monte_carlo": "Monte Carlo",
        "download_strategy_card": "Download strategy scorecard PNG",
        "share_card_note": "Shareable card includes the score, verdict, core pillars, equity/drawdown view, and main problems.",
        "share_card_unavailable": "Strategy scorecard PNG unavailable",
        "share_card_brand": "QuantScopeX Strategy Scorecard",
        "raw": "Raw report / metadata",
        "disclaimer": "This score measures historical backtest quality, not future performance, and is not investment advice. It is computed from the uploaded path alone and cannot detect look-ahead, survivorship, unrealistic fills, or in-sample selection.",
        "built_by": "Built by QuantScopeX",
        "edge.beat": "Beat buy & hold AND random timing",
        "edge.hold_only": "Beat buy & hold; random control unavailable",
        "edge.lost": "Did NOT beat buy & hold",
        "edge.random_fail": "No edge over random timing",
        "edge.marginal": "Only a marginal edge",
        "edge.luck_unclear": "Hard to tell from luck",
        "edge.not_evaluated": "Edge not evaluated - add the asset",
        "headline.flagged": "Looks too good to be true. Verify the backtest before trusting the score.",
        "headline.negative": "Not profitable over the sample.",
        "headline.sample": "Sample too small. Treat this as provisional.",
        "headline.edge_beat": "Beat buy & hold and random timing. A demonstrable edge in this sample.",
        "headline.edge_hold_only": "Beat buy & hold, but random-timing evidence is not available.",
        "headline.edge_lost": "Did not beat buy & hold on a risk-adjusted basis.",
        "headline.edge_random_fail": "Indistinguishable from random timing. No proven timing edge.",
        "headline.edge_marginal": "Only a marginal edge. Promising, but not proven.",
        "headline.edge_unknown": "Add the traded asset K-line to test skill vs luck.",
        "coaching_ok": "Solid foundation. Keep refining and re-score after more live or out-of-sample evidence.",
        "coaching_caution": "Promising, but not proven yet. Firm up the edge and the sample, then re-score.",
        "coaching_flagged": "Clean up the backtest methodology, rule out artifacts, and run it again.",
    },
    "zh": {
        "nav_score": "评分器",
        "eyebrow": "免费策略评分器",
        "title": "你的回测是真的吗？",
        "subtitle": "上传收益/权益/交易日志，几秒生成 0-100 评分、核心指标、过拟合/风险识别、蒙特卡洛、Overlay 和分享卡。",
        "subtitle_assets": "资产对比：虚拟币、美股/ETF、全球指数、A股 ETF、港股、金银、原油、铜、天然气、债券、外汇。",
        "language": "语言",
        "upload_title": "拖入策略文件，或点击选择文件",
        "upload_help": "收益序列（date,return）、权益曲线（date,equity）或交易日志（entry/exit/pnl_pct）。",
        "strategy_file": "策略文件",
        "upload_size_help": "最大文件大小：10 MB。",
        "upload_too_large": "文件超过 10 MB。请上传更小的收益、净值或交易日志文件。",
        "input_type": "输入类型",
        "input_auto": "自动",
        "input_returns": "收益率",
        "input_equity": "权益",
        "input_trade_log": "交易日志",
        "benchmark_asset": "对比资产",
        "benchmark_help": "选择你实际交易的资产。自动识别只是起点。",
        "custom_benchmark": "自定义基准 K 线",
        "custom_help": "可选：带 close 列的价格 CSV/TSV/Excel。上传后优先使用它。",
        "auto_asset": "从策略文件自动识别",
        "skip_asset": "不做资产对比",
        "ready_title": "数据已清洗，可评分",
        "waiting_title": "等待上传",
        "waiting_body": "选择一个策略文件，生成免费评分卡。",
        "using_custom": "正在使用你上传的基准 K 线。",
        "manual_asset": "手动对比基准",
        "auto_detected": "自动识别",
        "auto_failed": "无法自动识别交易资产。请在上方选择对比资产。",
        "asset_skipped": "已跳过资产对比；本事 vs 运气检验将不完整。",
        "asset_overlap_warn": "基准价格与策略日期没有重叠，已跳过对比。",
        "read_error": "无法读取策略文件",
        "bench_error": "无法读取基准文件",
        "sample": "样本",
        "track_record": "数据年限",
        "years": "年",
        "thin_sample": "偏少 - 结论暂定",
        "adequate_sample": "充足",
        "cap_prefix": "分数封顶",
        "pillars": "能力支柱",
        "return_quality": "收益质量",
        "credibility": "过拟合识别",
        "risk": "回撤控制",
        "sharpe": "夏普",
        "maxdd": "最大回撤",
        "cred_hint": "稳健性 · 一致性 · 异常平滑 · 收益集中",
        "triage": "免费尽调 Lite",
        "dependency": "依赖扫描 Lite",
        "unavailable": "不可用",
        "issues": "重点检查",
        "overlay_title": "免费 QSX Overlay Preview",
        "overlay_body": "把 QSX Overlay Preview 套到你自己的收益曲线或净值序列上，测试 QSX Crypto Universal Position Engine 1.0 作为外部风控叠加层是否改善风险收益。",
        "overlay_button": "运行免费 QSX Overlay Preview",
        "overlay_privacy": "只上传标准化后的每日 date-return 序列。原始文件、文件名、交易日志、策略代码和账户信息都留在本机。",
        "overlay_online": "使用 QuantScopeX 托管 API；这个开源仓库不打包生产 overlay 序列。",
        "overlay_trade_log_note": "交易日志 Overlay Preview 会拒绝多笔重叠持仓。请上传净值曲线或每日收益序列，让预览使用聚合后的策略路径。",
        "overlay_hash": "输入 SHA256",
        "overlay_unavailable": "风控叠加预览暂不可用",
        "equity_vs_hold": "策略 vs 买入持有",
        "equity": "净值（归一化）",
        "drawdown": "回撤",
        "monte_carlo": "蒙特卡洛",
        "download_strategy_card": "下载策略评分卡 PNG",
        "share_card_note": "分享卡包含评分、结论、核心支柱、净值/回撤图和主要问题，适合直接转发。",
        "share_card_unavailable": "策略评分卡 PNG 暂不可用",
        "share_card_brand": "QuantScopeX 策略评分卡",
        "raw": "原始报告 / 元数据",
        "disclaimer": "本评分衡量的是历史回测质量，而非未来表现，且不构成投资建议。它仅依据上传路径计算，无法识别未来函数、幸存者偏差、不切实际成交或样本内选择。",
        "built_by": "由 QuantScopeX 开发",
        "edge.beat": "跑赢「持有」与「随机择时」",
        "edge.hold_only": "跑赢买入持有；随机对照不可用",
        "edge.lost": "未跑赢买入持有",
        "edge.random_fail": "相比随机择时没有优势",
        "edge.marginal": "优势非常微弱",
        "edge.luck_unclear": "难以和运气区分",
        "edge.not_evaluated": "未评估优势 - 请补充资产",
        "headline.flagged": "看着好得不真实。先核回测，再信分数。",
        "headline.negative": "整个样本上没赚钱。",
        "headline.sample": "样本太小，结论只能暂定。",
        "headline.edge_beat": "跑赢买入持有和随机择时，样本内优势可验证。",
        "headline.edge_hold_only": "跑赢买入持有，但随机择时证据不可用。",
        "headline.edge_lost": "风险调整后没跑赢买入持有。",
        "headline.edge_random_fail": "和随机择时无法区分，未证明有择时优势。",
        "headline.edge_marginal": "优势很薄，有潜力但还没证明。",
        "headline.edge_unknown": "加入交易资产 K 线，才能判断本事还是运气。",
        "coaching_ok": "底子不错。继续打磨，积累更多样本外或实盘证据后再评分。",
        "coaching_caution": "有潜力，但还没证明。把优势和样本做扎实，再来评一次。",
        "coaching_flagged": "先把回测方法理干净、排除假象，再跑一遍。",
    },
    "ja": {
        "nav_score": "スコア",
        "eyebrow": "無料ストラテジー・スコアカード",
        "title": "そのバックテストは本物ですか？",
        "subtitle": "リターン、エクイティ、取引ログから0-100スコア、主要指標、過剰最適化/リスク検査、モンテカルロ、Overlay、共有カードを生成。",
        "subtitle_assets": "ベンチマーク：暗号資産、米株/ETF、主要指数、中国A株ETF、香港、金属、エネルギー、債券、FX。",
        "language": "言語",
        "upload_title": "ファイルをドロップ、またはクリックして選択",
        "upload_help": "リターン系列（date,return）、エクイティ曲線（date,equity）、取引ログ（entry/exit/pnl_pct）。",
        "strategy_file": "戦略ファイル",
        "upload_size_help": "最大ファイルサイズ：10 MB。",
        "upload_too_large": "ファイルが10 MBを超えています。より小さなリターン、エクイティ、または取引ログをアップロードしてください。",
        "input_type": "入力タイプ",
        "input_auto": "自動",
        "input_returns": "リターン",
        "input_equity": "エクイティ",
        "input_trade_log": "取引ログ",
        "benchmark_asset": "比較資産",
        "benchmark_help": "実際に取引した資産を選択してください。自動検出は出発点です。",
        "custom_benchmark": "カスタム基準価格",
        "custom_help": "任意：close列を含む価格CSV/TSV/Excel。アップロード時は優先されます。",
        "auto_asset": "戦略ファイルから自動検出",
        "skip_asset": "資産比較なし",
        "ready_title": "データはスコア可能です",
        "waiting_title": "アップロード待ち",
        "waiting_body": "戦略ファイルを選択して無料スコアカードを生成します。",
        "using_custom": "アップロードした基準価格を使用中。",
        "manual_asset": "手動基準",
        "auto_detected": "自動検出",
        "auto_failed": "取引資産を自動検出できません。比較資産を選択してください。",
        "asset_skipped": "資産比較をスキップしました。スキル対運の検査は不完全です。",
        "asset_overlap_warn": "基準価格と戦略期間が重ならないため比較をスキップしました。",
        "read_error": "戦略ファイルを読めません",
        "bench_error": "基準ファイルを読めません",
        "sample": "サンプル",
        "track_record": "期間",
        "years": "年",
        "thin_sample": "薄い - 暫定",
        "adequate_sample": "十分",
        "cap_prefix": "スコア上限",
        "pillars": "能力の柱",
        "return_quality": "収益品質",
        "credibility": "証拠信頼度",
        "risk": "ドローダウン管理",
        "sharpe": "シャープ",
        "maxdd": "最大DD",
        "cred_hint": "データ経路 · 堅牢性 · 妥当性",
        "triage": "無料デューデリジェンスLite",
        "dependency": "依存度Lite",
        "unavailable": "利用不可",
        "issues": "確認ポイント",
        "overlay_title": "無料 QSX Overlay Preview",
        "overlay_body": "QSX Overlay PreviewをあなたのリターンまたはNAV曲線に適用し、QSX Crypto Universal Position Engine 1.0が外部リスク管理レイヤーとして機能するかを確認します。",
        "overlay_button": "無料QSX Overlay Previewを実行",
        "overlay_privacy": "標準化された日次 date-return のみ送信します。元ファイル、ファイル名、取引ログ、戦略コード、口座情報はローカルに残ります。",
        "overlay_online": "QuantScopeX のホスト API を使用します。このオープンソースリポジトリには本番 overlay 系列は含まれません。",
        "overlay_trade_log_note": "取引ログのOverlay Previewは重複するポジションを拒否します。集計済みのエクイティ曲線または日次リターンをアップロードしてください。",
        "overlay_hash": "Input SHA256",
        "overlay_unavailable": "Overlay preview unavailable",
        "equity_vs_hold": "戦略 vs 保有",
        "equity": "エクイティ（リベース）",
        "drawdown": "ドローダウン",
        "monte_carlo": "モンテカルロ",
        "download_strategy_card": "戦略スコアカードPNGをダウンロード",
        "share_card_note": "共有カードにはスコア、判定、主要柱、エクイティ/ドローダウン、主な問題が含まれます。",
        "share_card_unavailable": "戦略スコアカードPNGを生成できません",
        "share_card_brand": "QuantScopeX 戦略スコアカード",
        "raw": "生レポート / メタデータ",
        "disclaimer": "このスコアは過去のバックテスト品質を測るもので、将来の成績や投資助言ではありません。",
        "built_by": "QuantScopeX 開発",
        "edge.beat": "保有とランダム売買を上回る",
        "edge.hold_only": "保有を上回るがランダム対照不可",
        "edge.lost": "買い持ちを上回らない",
        "edge.random_fail": "ランダム売買への優位性なし",
        "edge.marginal": "優位性はわずか",
        "edge.luck_unclear": "運との区別が難しい",
        "edge.not_evaluated": "未評価 - 資産を追加",
        "headline.flagged": "良すぎる結果です。スコアを信じる前に検証してください。",
        "headline.negative": "サンプル全体では利益が出ていません。",
        "headline.sample": "サンプルが小さく、結論は暫定です。",
        "headline.edge_beat": "保有とランダム売買を上回りました。",
        "headline.edge_hold_only": "保有を上回りましたが、ランダム対照は利用できません。",
        "headline.edge_lost": "リスク調整後で保有を上回りません。",
        "headline.edge_random_fail": "ランダム売買と区別できません。タイミング優位性は証明されていません。",
        "headline.edge_marginal": "優位性はわずかです。まだ証明不足です。",
        "headline.edge_unknown": "取引資産の価格を追加して確認してください。",
        "coaching_ok": "土台は良好です。追加のライブ/OOS証拠で再評価してください。",
        "coaching_caution": "有望ですが、まだ証明不足です。",
        "coaching_flagged": "バックテスト手法を確認し、再実行してください。",
    },
    "ko": {
        "nav_score": "스코어러",
        "eyebrow": "무료 전략 스코어카드",
        "title": "이 백테스트는 진짜인가요?",
        "subtitle": "수익률, 에쿼티, 거래 로그로 0-100 점수, 핵심 지표, 과최적화/리스크 점검, 몬테카를로, Overlay, 공유 카드를 생성합니다.",
        "subtitle_assets": "벤치마크: 암호화폐, 미국 주식/ETF, 글로벌 지수, 중국 A주 ETF, 홍콩, 금속, 에너지, 채권, FX.",
        "language": "언어",
        "upload_title": "전략 파일을 드롭하거나 클릭해 선택",
        "upload_help": "수익률 시계열(date,return), 에쿼티 곡선(date,equity), 거래 로그(entry/exit/pnl_pct).",
        "strategy_file": "전략 파일",
        "upload_size_help": "최대 파일 크기: 10 MB.",
        "upload_too_large": "파일이 10 MB보다 큽니다. 더 작은 수익률, 에쿼티 또는 거래 로그 파일을 업로드하세요.",
        "input_type": "입력 유형",
        "input_auto": "자동",
        "input_returns": "수익률",
        "input_equity": "에쿼티",
        "input_trade_log": "거래 로그",
        "benchmark_asset": "비교 자산",
        "benchmark_help": "실제로 거래한 자산을 선택하세요. 자동 감지는 시작점입니다.",
        "custom_benchmark": "사용자 기준 K-line",
        "custom_help": "선택: close 열이 있는 가격 CSV/TSV/Excel. 업로드하면 우선 사용됩니다.",
        "auto_asset": "전략 파일에서 자동 감지",
        "skip_asset": "자산 비교 없음",
        "ready_title": "데이터 준비 완료",
        "waiting_title": "업로드 대기 중",
        "waiting_body": "전략 파일을 선택해 무료 스코어카드를 생성하세요.",
        "using_custom": "업로드한 기준 가격을 사용 중.",
        "manual_asset": "수동 기준",
        "auto_detected": "자동 감지",
        "auto_failed": "거래 자산을 자동 감지하지 못했습니다. 비교 자산을 선택하세요.",
        "asset_skipped": "자산 비교를 건너뛰었습니다. 실력 대 운 검증이 불완전합니다.",
        "asset_overlap_warn": "기준 가격과 전략 기간이 겹치지 않아 비교를 건너뛰었습니다.",
        "read_error": "전략 파일을 읽을 수 없습니다",
        "bench_error": "기준 파일을 읽을 수 없습니다",
        "sample": "표본",
        "track_record": "기간",
        "years": "년",
        "thin_sample": "부족 - 잠정",
        "adequate_sample": "충분",
        "cap_prefix": "점수 상한",
        "pillars": "역량 지표",
        "return_quality": "수익 품질",
        "credibility": "증거 신뢰도",
        "risk": "드로다운 관리",
        "sharpe": "샤프",
        "maxdd": "최대DD",
        "cred_hint": "데이터 경로 · 견고성 · 타당성",
        "triage": "무료 실사 Lite",
        "dependency": "의존도 Lite",
        "unavailable": "사용 불가",
        "issues": "확인할 점",
        "overlay_title": "무료 QSX Overlay Preview",
        "overlay_body": "QSX Overlay Preview를 본인의 수익률 또는 NAV 곡선에 적용해 QSX Crypto Universal Position Engine 1.0이 외부 리스크 제어 레이어로 도움이 되는지 확인하세요.",
        "overlay_button": "무료 QSX Overlay Preview 실행",
        "overlay_privacy": "정규화된 일별 date-return 행만 전송됩니다. 원본 파일, 파일명, 거래 로그, 전략 코드, 계정 정보는 로컬에 남습니다.",
        "overlay_online": "QuantScopeX 호스팅 API를 사용합니다. 이 오픈소스 저장소에는 프로덕션 overlay 시리즈가 포함되지 않습니다.",
        "overlay_trade_log_note": "거래 로그 Overlay Preview는 중복 포지션을 거부합니다. 집계된 에쿼티 곡선 또는 일별 수익률을 업로드하세요.",
        "overlay_hash": "Input SHA256",
        "overlay_unavailable": "Overlay preview unavailable",
        "equity_vs_hold": "전략 vs 보유",
        "equity": "에쿼티(리베이스)",
        "drawdown": "드로다운",
        "monte_carlo": "몬테카를로",
        "download_strategy_card": "전략 점수 카드 PNG 다운로드",
        "share_card_note": "공유 카드에는 점수, 판정, 핵심 축, 에쿼티/드로다운, 주요 문제가 포함됩니다.",
        "share_card_unavailable": "전략 점수 카드 PNG를 생성할 수 없습니다",
        "share_card_brand": "QuantScopeX 전략 점수 카드",
        "raw": "원시 보고서 / 메타데이터",
        "disclaimer": "이 점수는 과거 백테스트 품질을 측정하며 미래 성과나 투자 조언이 아닙니다.",
        "built_by": "QuantScopeX 개발",
        "edge.beat": "보유와 랜덤 타이밍을 상회",
        "edge.hold_only": "매수 보유 상회, 랜덤 대조 불가",
        "edge.lost": "매수 보유를 이기지 못함",
        "edge.random_fail": "랜덤 타이밍 대비 우위 없음",
        "edge.marginal": "우위가 약함",
        "edge.luck_unclear": "운과 구분 어려움",
        "edge.not_evaluated": "미평가 - 자산 추가",
        "headline.flagged": "결과가 지나치게 좋습니다. 검증 후 신뢰하세요.",
        "headline.negative": "전체 표본에서 수익성이 없습니다.",
        "headline.sample": "표본이 작아 결론은 잠정적입니다.",
        "headline.edge_beat": "보유와 랜덤 타이밍을 모두 상회했습니다.",
        "headline.edge_hold_only": "매수 보유는 상회했지만 랜덤 대조는 사용할 수 없습니다.",
        "headline.edge_lost": "위험 조정 기준으로 보유를 이기지 못했습니다.",
        "headline.edge_random_fail": "랜덤 타이밍과 구분되지 않습니다. 타이밍 우위가 입증되지 않았습니다.",
        "headline.edge_marginal": "우위가 약합니다. 아직 입증 부족입니다.",
        "headline.edge_unknown": "거래 자산 가격을 추가해 확인하세요.",
        "coaching_ok": "기초는 좋습니다. 추가 라이브/OOS 증거로 다시 평가하세요.",
        "coaching_caution": "가능성은 있지만 아직 입증 부족입니다.",
        "coaching_flagged": "백테스트 방법을 정리하고 다시 실행하세요.",
    },
    "es": {
        "nav_score": "Evaluador",
        "eyebrow": "Tarjeta de puntuación gratuita",
        "title": "¿Tu prueba retrospectiva es real?",
        "subtitle": "Sube retornos, capital o trades. Obtén score 0-100, métricas, sobreajuste/riesgo, Monte Carlo, Overlay y tarjeta compartible.",
        "subtitle_assets": "Benchmarks: cripto, acciones/ETF de EE. UU., índices globales, ETF de acciones A chinas, Hong Kong, metales, energía, bonos y FX.",
        "language": "Idioma",
        "upload_title": "Arrastra un archivo o haz clic para elegir",
        "upload_help": "Retornos (date,return), curva de capital (date,equity) o registro de operaciones (entry/exit/pnl_pct).",
        "strategy_file": "Archivo de estrategia",
        "upload_size_help": "Tamaño máximo de archivo: 10 MB.",
        "upload_too_large": "El archivo supera 10 MB. Sube un archivo más pequeño de retornos, capital o registro de operaciones.",
        "input_type": "Tipo de entrada",
        "input_auto": "Auto",
        "input_returns": "Retornos",
        "input_equity": "Capital",
        "input_trade_log": "Registro de operaciones",
        "benchmark_asset": "Activo de referencia",
        "benchmark_help": "Elige el activo operado. Auto-detectar es solo un punto de partida.",
        "custom_benchmark": "Referencia personalizada",
        "custom_help": "Opcional: CSV/TSV/Excel de precios con columna de cierre. Tiene prioridad.",
        "auto_asset": "Auto-detectar desde archivo",
        "skip_asset": "Sin comparación de activo",
        "ready_title": "Datos listos para puntuar",
        "waiting_title": "Esperando archivo",
        "waiting_body": "Elige un archivo de estrategia para generar la tarjeta de puntuación gratuita.",
        "using_custom": "Usando tu referencia personalizada.",
        "manual_asset": "Referencia manual",
        "auto_detected": "Auto-detectado",
        "auto_failed": "No se pudo auto-detectar el activo. Elige un benchmark arriba.",
        "asset_skipped": "Comparación omitida. La prueba habilidad vs suerte queda incompleta.",
        "asset_overlap_warn": "Los precios de referencia no se solapan con la estrategia; se omitió la comparación.",
        "read_error": "No se pudo leer el archivo",
        "bench_error": "No se pudo leer el benchmark",
        "sample": "Muestra",
        "track_record": "Historial",
        "years": "años",
        "thin_sample": "débil - provisional",
        "adequate_sample": "adecuada",
        "cap_prefix": "Puntuación limitada",
        "pillars": "Pilares",
        "return_quality": "Calidad del retorno",
        "credibility": "Credibilidad de evidencia",
        "risk": "Control de caídas",
        "sharpe": "Sharpe",
        "maxdd": "MaxDD",
        "cred_hint": "ruta de datos · robustez · plausibilidad",
        "triage": "Diligencia debida Lite",
        "dependency": "Dependencia Lite",
        "unavailable": "No disponible",
        "issues": "Qué revisar",
        "overlay_title": "QSX Overlay Preview gratuito",
        "overlay_body": "Aplica QSX Overlay Preview a tu curva de retornos o capital para probar QSX Crypto Universal Position Engine 1.0 como capa externa de control de riesgo.",
        "overlay_button": "Ejecutar QSX Overlay Preview gratis",
        "overlay_privacy": "Solo se transmite la serie diaria normalizada date-return. Archivos originales, nombres, registros, código y datos de cuenta permanecen en tu máquina.",
        "overlay_online": "Usa la API alojada de QuantScopeX; este repositorio abierto no incluye la serie overlay de producción.",
        "overlay_trade_log_note": "Overlay Preview rechaza registros con posiciones superpuestas. Sube una curva de capital o retornos diarios agregados.",
        "overlay_hash": "SHA256 de entrada",
        "overlay_unavailable": "Vista previa no disponible",
        "equity_vs_hold": "Estrategia vs comprar y mantener",
        "equity": "Capital (normalizado)",
        "drawdown": "Caída",
        "monte_carlo": "Monte Carlo",
        "download_strategy_card": "Descargar scorecard PNG",
        "share_card_note": "La tarjeta comparte puntuación, veredicto, pilares, capital/drawdown y problemas principales.",
        "share_card_unavailable": "No se pudo generar la scorecard PNG",
        "share_card_brand": "Scorecard de estrategia QuantScopeX",
        "raw": "Reporte crudo / metadatos",
        "disclaimer": "Esta puntuación mide la calidad histórica de la prueba retrospectiva, no el rendimiento futuro, y no es asesoría de inversión.",
        "built_by": "Desarrollado por QuantScopeX",
        "edge.beat": "Supera comprar y mantener y sincronización aleatoria",
        "edge.hold_only": "Supera buy & hold; control aleatorio no disponible",
        "edge.lost": "No supera comprar y mantener",
        "edge.random_fail": "Sin ventaja vs timing aleatorio",
        "edge.marginal": "Ventaja marginal",
        "edge.luck_unclear": "Difícil separarlo de suerte",
        "edge.not_evaluated": "No evaluado - agrega el activo",
        "headline.flagged": "Parece demasiado bueno. Verifica el backtest antes de confiar.",
        "headline.negative": "No es rentable en la muestra.",
        "headline.sample": "Muestra demasiado pequeña; conclusión provisional.",
        "headline.edge_beat": "Supera comprar y mantener y sincronización aleatoria.",
        "headline.edge_hold_only": "Supera buy & hold, pero el control aleatorio no está disponible.",
        "headline.edge_lost": "No supera comprar y mantener ajustado por riesgo.",
        "headline.edge_random_fail": "Indistinguible de la sincronización aleatoria. No demuestra ventaja de timing.",
        "headline.edge_marginal": "Ventaja marginal. Prometedor, no probado.",
        "headline.edge_unknown": "Agrega precios del activo para probar habilidad vs suerte.",
        "coaching_ok": "Base sólida. Reevalúa con más evidencia live/OOS.",
        "coaching_caution": "Prometedor, pero no probado.",
        "coaching_flagged": "Limpia la metodología del backtest y vuelve a correrlo.",
    },
    "pt-BR": {
        "nav_score": "Avaliador",
        "eyebrow": "Cartão de pontuação gratuito",
        "title": "Seu teste retrospectivo é real?",
        "subtitle": "Envie retornos, capital ou trades. Receba score 0-100, métricas, sobreajuste/risco, Monte Carlo, Overlay e card compartilhável.",
        "subtitle_assets": "Benchmarks: cripto, ações/ETFs dos EUA, índices globais, ETFs de ações A chinesas, Hong Kong, metais, energia, bonds e FX.",
        "language": "Idioma",
        "upload_title": "Arraste um arquivo ou clique para escolher",
        "upload_help": "Retornos (date,return), curva de capital (date,equity) ou registro de operações (entry/exit/pnl_pct).",
        "strategy_file": "Arquivo da estratégia",
        "upload_size_help": "Tamanho máximo do arquivo: 10 MB.",
        "upload_too_large": "O arquivo tem mais de 10 MB. Envie um arquivo menor de retornos, capital ou registro de operações.",
        "input_type": "Tipo de entrada",
        "input_auto": "Auto",
        "input_returns": "Retornos",
        "input_equity": "Capital",
        "input_trade_log": "Registro de operações",
        "benchmark_asset": "Ativo de referência",
        "benchmark_help": "Escolha o ativo negociado. Auto-detecção é só o começo.",
        "custom_benchmark": "Referência personalizada",
        "custom_help": "Opcional: CSV/TSV/Excel de preços com coluna de fechamento. Tem prioridade.",
        "auto_asset": "Auto-detectar pelo arquivo",
        "skip_asset": "Sem comparação de ativo",
        "ready_title": "Dados prontos para pontuar",
        "waiting_title": "Aguardando upload",
        "waiting_body": "Escolha um arquivo de estratégia para gerar o cartão de pontuação gratuito.",
        "using_custom": "Usando sua referência personalizada.",
        "manual_asset": "Referência manual",
        "auto_detected": "Auto-detectado",
        "auto_failed": "Não foi possível auto-detectar o ativo. Escolha um benchmark acima.",
        "asset_skipped": "Comparação omitida. O teste habilidade vs sorte fica incompleto.",
        "asset_overlap_warn": "Os preços de referência não se sobrepõem à estratégia; comparação omitida.",
        "read_error": "Não foi possível ler o arquivo",
        "bench_error": "Não foi possível ler o benchmark",
        "sample": "Amostra",
        "track_record": "Histórico",
        "years": "anos",
        "thin_sample": "fraca - provisória",
        "adequate_sample": "adequada",
        "cap_prefix": "Pontuação limitada",
        "pillars": "Pilares",
        "return_quality": "Qualidade do retorno",
        "credibility": "Credibilidade da evidência",
        "risk": "Controle de queda",
        "sharpe": "Sharpe",
        "maxdd": "MaxDD",
        "cred_hint": "caminho dos dados · robustez · plausibilidade",
        "triage": "Diligência Lite",
        "dependency": "Dependência Lite",
        "unavailable": "Indisponível",
        "issues": "O que revisar",
        "overlay_title": "QSX Overlay Preview gratuito",
        "overlay_body": "Aplique o QSX Overlay Preview à sua curva de retornos ou capital para testar o QSX Crypto Universal Position Engine 1.0 como camada externa de controle de risco.",
        "overlay_button": "Executar QSX Overlay Preview gratuito",
        "overlay_privacy": "Somente a série diária normalizada date-return é transmitida. Arquivos originais, nomes, logs, código e dados de conta ficam na sua máquina.",
        "overlay_online": "Usa a API hospedada da QuantScopeX; este repositório aberto não inclui a série overlay de produção.",
        "overlay_trade_log_note": "O Overlay Preview rejeita registros com posições sobrepostas. Envie uma curva de capital ou retornos diários agregados.",
        "overlay_hash": "SHA256 de entrada",
        "overlay_unavailable": "Prévia indisponível",
        "equity_vs_hold": "Estratégia vs comprar e manter",
        "equity": "Capital (normalizado)",
        "drawdown": "Queda",
        "monte_carlo": "Monte Carlo",
        "download_strategy_card": "Baixar scorecard PNG",
        "share_card_note": "O cartão compartilhável inclui pontuação, veredito, pilares, curva/drawdown e principais problemas.",
        "share_card_unavailable": "Não foi possível gerar o scorecard PNG",
        "share_card_brand": "Scorecard de estratégia QuantScopeX",
        "raw": "Relatório bruto / metadados",
        "disclaimer": "Esta pontuação mede a qualidade histórica do teste retrospectivo, não desempenho futuro, e não é recomendação de investimento.",
        "built_by": "Desenvolvido por QuantScopeX",
        "edge.beat": "Supera comprar e manter e temporização aleatória",
        "edge.hold_only": "Supera buy & hold; controle aleatório indisponível",
        "edge.lost": "Não supera comprar e manter",
        "edge.random_fail": "Sem vantagem vs timing aleatório",
        "edge.marginal": "Vantagem marginal",
        "edge.luck_unclear": "Difícil separar de sorte",
        "edge.not_evaluated": "Não avaliado - adicione o ativo",
        "headline.flagged": "Parece bom demais. Verifique o backtest antes de confiar.",
        "headline.negative": "Não foi lucrativa na amostra.",
        "headline.sample": "Amostra pequena demais; conclusão provisória.",
        "headline.edge_beat": "Supera comprar e manter e temporização aleatória.",
        "headline.edge_hold_only": "Supera buy & hold, mas o controle aleatório está indisponível.",
        "headline.edge_lost": "Não supera comprar e manter ajustado por risco.",
        "headline.edge_random_fail": "Indistinguível de temporização aleatória. Não comprova vantagem de timing.",
        "headline.edge_marginal": "Vantagem marginal. Promissora, mas não provada.",
        "headline.edge_unknown": "Adicione preços do ativo para testar habilidade vs sorte.",
        "coaching_ok": "Boa base. Reavalie com mais evidência live/OOS.",
        "coaching_caution": "Promissor, mas ainda não provado.",
        "coaching_flagged": "Limpe a metodologia do backtest e rode novamente.",
    },
}

GRADE_LOCAL = {
    "en": {},
    "zh": {"GOLD": "金牌", "SILVER": "银牌", "BRONZE": "铜牌", "PROVISIONAL": "暂定", "NEEDS WORK": "需改进", "FLAGGED": "存疑"},
    "ja": {"GOLD": "ゴールド", "SILVER": "シルバー", "BRONZE": "ブロンズ", "PROVISIONAL": "暫定", "NEEDS WORK": "要改善", "FLAGGED": "要検証"},
    "ko": {"GOLD": "골드", "SILVER": "실버", "BRONZE": "브론즈", "PROVISIONAL": "잠정", "NEEDS WORK": "개선 필요", "FLAGGED": "검증 필요"},
    "es": {"GOLD": "Oro", "SILVER": "Plata", "BRONZE": "Bronce", "PROVISIONAL": "Provisional", "NEEDS WORK": "Necesita trabajo", "FLAGGED": "Sospechoso"},
    "pt-BR": {"GOLD": "Ouro", "SILVER": "Prata", "BRONZE": "Bronze", "PROVISIONAL": "Provisória", "NEEDS WORK": "Precisa melhorar", "FLAGGED": "Sinalizado"},
}

FUNNEL_COPY = {
    "en": {
        "results_title": "Free Strategy Check",
        "results_subtitle": "One-page read: health, risk, problems, and whether QSX Overlay Preview is worth testing.",
        "core_metrics": "Core Metrics",
        "risk_diagnosis": "Risk Diagnosis",
        "main_problems": "Main Problems",
        "overlay_question": "Can QSX Overlay Preview Improve This Strategy?",
        "overlay_hint": "Run a hosted lite simulation before you buy anything. The open-source app sends only a normalized daily date-return series.",
        "advanced_details": "Advanced details",
        "score_label": "Strategy Score",
        "verdict": "Verdict",
        "drawdown_risk": "Drawdown Risk",
        "stability_risk": "Return Stability",
        "overfit_risk": "Overfit Risk",
        "sample_risk": "Sample Risk",
        "tail_risk": "Tail Risk",
        "mc_source_note": "Computed locally from this uploaded return series with moving-block bootstrap. No Overlay/API call is used.",
        "mc_profit_prob": "Profit probability",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "Worst 5% MaxDD",
        "high": "High",
        "medium": "Medium",
        "low": "Low",
        "no_major_issue": "No major issue surfaced in the free check.",
        "overlay_primary": "Run Free Overlay Simulation",
    },
    "zh": {
        "results_title": "免费策略体检",
        "results_subtitle": "一页看完：健康度、风险、主要问题，以及是否值得测试 QSX Overlay Preview。",
        "core_metrics": "核心指标",
        "risk_diagnosis": "风险诊断",
        "main_problems": "主要问题",
        "overlay_question": "QSX Overlay Preview 能改善这个策略吗？",
        "overlay_hint": "先免费跑一次托管 Lite 模拟。开源 app 只发送标准化后的每日 date-return 序列。",
        "advanced_details": "高级细节",
        "score_label": "策略评分",
        "verdict": "结论",
        "drawdown_risk": "回撤风险",
        "stability_risk": "收益稳定性",
        "overfit_risk": "过拟合风险",
        "sample_risk": "样本规模风险",
        "tail_risk": "极端行情风险",
        "mc_source_note": "基于本次上传的收益率序列在本地做 moving-block bootstrap，不调用 Overlay/API。",
        "mc_profit_prob": "盈利概率",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "最坏 5% 最大回撤",
        "high": "高",
        "medium": "中",
        "low": "低",
        "no_major_issue": "免费体检未发现特别突出的主要问题。",
        "overlay_primary": "运行免费 Overlay 模拟",
    },
    "ja": {
        "results_title": "無料ストラテジー診断",
        "results_subtitle": "健康度、リスク、主な問題、QSX Overlay Previewを試す価値を1ページで確認します。",
        "core_metrics": "主要指標",
        "risk_diagnosis": "リスク診断",
        "main_problems": "主な問題",
        "overlay_question": "QSX Overlay Previewで改善できますか？",
        "overlay_hint": "購入前にホスト型Liteシミュレーションを実行します。送信されるのは標準化された日次date-returnのみです。",
        "advanced_details": "詳細",
        "score_label": "戦略スコア",
        "verdict": "判定",
        "drawdown_risk": "ドローダウンリスク",
        "stability_risk": "収益安定性",
        "overfit_risk": "過剰最適化リスク",
        "sample_risk": "サンプルリスク",
        "tail_risk": "テールリスク",
        "mc_source_note": "アップロードされたリターン系列をローカルで moving-block bootstrap します。Overlay/APIは使いません。",
        "mc_profit_prob": "利益確率",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "ワースト5% 最大DD",
        "high": "高",
        "medium": "中",
        "low": "低",
        "no_major_issue": "無料診断では大きな問題は見つかりませんでした。",
        "overlay_primary": "無料Overlayシミュレーション",
    },
    "ko": {
        "results_title": "무료 전략 점검",
        "results_subtitle": "건강도, 리스크, 주요 문제, QSX Overlay Preview 테스트 가치를 한 페이지에서 봅니다.",
        "core_metrics": "핵심 지표",
        "risk_diagnosis": "리스크 진단",
        "main_problems": "주요 문제",
        "overlay_question": "QSX Overlay Preview가 이 전략을 개선할까요?",
        "overlay_hint": "구매 전 호스팅 Lite 시뮬레이션을 실행하세요. 표준화된 일별 date-return만 전송됩니다.",
        "advanced_details": "상세",
        "score_label": "전략 점수",
        "verdict": "판정",
        "drawdown_risk": "드로다운 리스크",
        "stability_risk": "수익 안정성",
        "overfit_risk": "과최적화 리스크",
        "sample_risk": "표본 리스크",
        "tail_risk": "꼬리위험",
        "mc_source_note": "업로드된 수익률 시계열을 로컬에서 moving-block bootstrap으로 계산합니다. Overlay/API를 사용하지 않습니다.",
        "mc_profit_prob": "수익 확률",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "최악 5% 최대 DD",
        "high": "높음",
        "medium": "보통",
        "low": "낮음",
        "no_major_issue": "무료 점검에서 큰 문제는 발견되지 않았습니다.",
        "overlay_primary": "무료 Overlay 시뮬레이션 실행",
    },
    "es": {
        "results_title": "Chequeo gratuito de estrategia",
        "results_subtitle": "Una página: salud, riesgos, problemas y si vale la pena probar QSX Overlay Preview.",
        "core_metrics": "Métricas clave",
        "risk_diagnosis": "Diagnóstico de riesgo",
        "main_problems": "Problemas principales",
        "overlay_question": "¿QSX Overlay Preview puede mejorar esta estrategia?",
        "overlay_hint": "Ejecuta una simulación Lite alojada antes de comprar. Solo se envía date-return diario normalizado.",
        "advanced_details": "Detalles avanzados",
        "score_label": "Puntuación",
        "verdict": "Veredicto",
        "drawdown_risk": "Riesgo de caída",
        "stability_risk": "Estabilidad",
        "overfit_risk": "Riesgo de sobreajuste",
        "sample_risk": "Riesgo de muestra",
        "tail_risk": "Riesgo extremo",
        "mc_source_note": "Calculado localmente desde esta serie de retornos con moving-block bootstrap. No usa Overlay/API.",
        "mc_profit_prob": "Probabilidad de ganancia",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "Peor 5% MaxDD",
        "high": "Alto",
        "medium": "Medio",
        "low": "Bajo",
        "no_major_issue": "El chequeo gratuito no encontró un problema principal claro.",
        "overlay_primary": "Ejecutar Overlay gratis",
    },
    "pt-BR": {
        "results_title": "Checagem gratuita da estratégia",
        "results_subtitle": "Uma página: saúde, risco, problemas e se vale testar o QSX Overlay Preview.",
        "core_metrics": "Métricas-chave",
        "risk_diagnosis": "Diagnóstico de risco",
        "main_problems": "Principais problemas",
        "overlay_question": "O QSX Overlay Preview pode melhorar esta estratégia?",
        "overlay_hint": "Rode uma simulação Lite hospedada antes de comprar. Só é enviada a série diária date-return normalizada.",
        "advanced_details": "Detalhes avançados",
        "score_label": "Pontuação",
        "verdict": "Veredito",
        "drawdown_risk": "Risco de queda",
        "stability_risk": "Estabilidade",
        "overfit_risk": "Risco de sobreajuste",
        "sample_risk": "Risco de amostra",
        "tail_risk": "Risco extremo",
        "mc_source_note": "Calculado localmente a partir desta série de retornos com moving-block bootstrap. Não usa Overlay/API.",
        "mc_profit_prob": "Probabilidade de lucro",
        "mc_cagr_range": "CAGR 5-95%",
        "mc_tail_dd": "Pior 5% MaxDD",
        "high": "Alto",
        "medium": "Médio",
        "low": "Baixo",
        "no_major_issue": "A checagem gratuita não encontrou um problema principal claro.",
        "overlay_primary": "Rodar Overlay grátis",
    },
}


def tr(key: str, lang: str) -> str:
    return COPY.get(lang, COPY["en"]).get(key) or COPY["en"].get(key) or t(key, lang)


def ft(key: str, lang: str) -> str:
    return FUNNEL_COPY.get(lang, FUNNEL_COPY["en"]).get(key) or FUNNEL_COPY["en"].get(key, key)


def lang_label(code: str) -> str:
    return f"{code} - {LANG_LABELS.get(code, code)}"


def upload_size_ok(upload, lang: str) -> bool:
    if upload is None:
        return True
    size = getattr(upload, "size", None)
    if size is not None and int(size) > MAX_UPLOAD_BYTES:
        st.error(tr("upload_too_large", lang))
        return False
    return True


def asset_label(key: str, lang: str) -> str:
    if key == AUTO_ASSET:
        return tr("auto_asset", lang)
    if key == SKIP_ASSET:
        return tr("skip_asset", lang)
    return ASSET_LABELS.get(key, key)


def local_grade(grade: str, lang: str) -> str:
    return GRADE_LOCAL.get(lang, {}).get(grade, grade)


def local_headline(report, lang: str) -> str:
    if lang == "zh" and report.meta.get("headline_zh"):
        return str(report.meta["headline_zh"])
    if report.judgement == "FLAGGED":
        return tr("headline.flagged", lang)
    if any(f.get("code") == "NEGATIVE_RETURN" for f in report.flags):
        return tr("headline.negative", lang)
    if any(f.get("code") == "INSUFFICIENT_SAMPLE" for f in report.flags):
        return tr("headline.sample", lang)
    edge = report.lights.get("edge")
    return {
        "beat": tr("headline.edge_beat", lang),
        "hold_only": tr("headline.edge_hold_only", lang),
        "lost": tr("headline.edge_lost", lang),
        "random_fail": tr("headline.edge_random_fail", lang),
        "marginal": tr("headline.edge_marginal", lang),
        "luck_unclear": tr("headline.edge_unknown", lang),
        "not_evaluated": tr("headline.edge_unknown", lang),
    }.get(edge, report.headline if lang == "en" else tr("headline.edge_unknown", lang))


def local_issue(issue: dict, lang: str) -> tuple[str, str]:
    if lang == "zh":
        return issue.get("problem_zh") or issue.get("problem") or "", issue.get("direction_zh") or issue.get("direction") or ""
    code = issue.get("code")
    problem_key = f"issue.{code}.problem"
    direction_key = f"issue.{code}.direction"
    problem = t(problem_key, lang)
    direction = t(direction_key, lang)
    if problem != problem_key and direction != direction_key:
        return problem, direction
    return issue.get("problem") or "", issue.get("direction") or ""


def local_encouragement(report, co: dict, lang: str) -> str:
    if lang == "zh":
        return co.get("encouragement_zh") or co.get("encouragement") or ""
    if report.judgement == "FLAGGED":
        return tr("coaching_flagged", lang)
    if report.judgement == "CAUTION" or report.lights.get("edge") in {"hold_only", "marginal", "luck_unclear", "random_fail"}:
        return tr("coaching_caution", lang)
    return tr("coaching_ok", lang)


def sample_text(report, lang: str) -> str:
    n = report.meta.get("n")
    unit = report.meta.get("sample_unit", "bars")
    if report.meta.get("sample_ok", True) and report.meta.get("low_frequency") and unit == "trades":
        if lang == "zh":
            return f"事件样本 ({n} 笔)"
        return f"event sample ({n} trades)"
    if lang == "zh":
        unit_local = "笔" if unit == "trades" else "根"
        status = tr("adequate_sample", lang) if report.meta.get("sample_ok", True) else tr("thin_sample", lang)
        return f"{status} ({n} {unit_local})"
    status = tr("adequate_sample", lang) if report.meta.get("sample_ok", True) else tr("thin_sample", lang)
    return f"{status} ({n} {unit})"


def _fmt_number(value: float, digits: int = 2) -> str:
    try:
        x = float(value)
    except Exception:
        return "-"
    if x != x or x in (float("inf"), float("-inf")):
        return "-"
    return f"{x:.{digits}f}"


def _fmt_pct_value(value: float, digits: int = 1) -> str:
    try:
        x = float(value) * 100.0
    except Exception:
        return "-"
    if x != x or x in (float("inf"), float("-inf")):
        return "-"
    return f"{x:.{digits}f}%"


def mc_verdict(mc: dict, lang: str) -> dict[str, str]:
    prob_profit = 1.0 - float(mc.get("prob_loss") or 0.0)
    cagr_p5 = float(mc.get("cagr_p5") or 0.0)
    tail_dd = float(mc.get("maxdd_worst5") or 0.0)

    if tail_dd <= -0.75:
        level = "high"
        tone = "rose"
        en = "Most resampled paths still make money, but the left-tail drawdown is extreme. This strategy needs lower leverage or a risk overlay before it is tradable at size."
        zh = "多数重抽样路径仍能赚钱，但左尾回撤极深。这个策略如果要上规模，必须先降杠杆或加风控叠加。"
    elif cagr_p5 < 0 or prob_profit < 0.75:
        level = "medium"
        tone = "amber"
        en = "The edge is not stable under resampling. A bad ordering of the same historical returns can turn the strategy weak or losing."
        zh = "重抽样后优势不够稳。同一批历史收益换一种顺序，策略可能明显变弱甚至亏损。"
    elif tail_dd <= -0.45:
        level = "medium"
        tone = "amber"
        en = "Return survival looks acceptable, but tail drawdown is still heavy. Position sizing and drawdown controls matter more than chasing a higher score."
        zh = "收益存活率可以，但尾部回撤仍然偏重。这里更该关注仓位和回撤控制，而不是继续追高分。"
    else:
        level = "low"
        tone = "green"
        en = "The return path survives resampling reasonably well. The free check does not remove execution, overfitting, or regime risks, but Monte Carlo is not the main red flag."
        zh = "重抽样后的收益路径相对稳。免费体检仍不能排除成交、过拟合或行情环境风险，但蒙特卡洛不是主要红旗。"

    text = zh if lang == "zh" else en
    return {"level": level, "tone": tone, "text": text}


def monte_carlo_summary_markup(mc: dict, lang: str) -> str:
    verdict = mc_verdict(mc, lang)
    prob_profit = max(0.0, min(1.0, 1.0 - float(mc.get("prob_loss") or 0.0)))
    if prob_profit > 0.995:
        prob_text = ">99%"
    else:
        prob_text = f"{prob_profit * 100:.0f}%"
    cagr_range = f"{_fmt_pct_value(mc.get('cagr_p5', 0.0), 0)} to {_fmt_pct_value(mc.get('cagr_p95', 0.0), 0)}"
    if lang == "zh":
        cagr_range = f"{_fmt_pct_value(mc.get('cagr_p5', 0.0), 0)} 到 {_fmt_pct_value(mc.get('cagr_p95', 0.0), 0)}"
    tail_dd = _fmt_pct_value(mc.get("maxdd_worst5", 0.0), 0)
    cells = [
        (ft("mc_profit_prob", lang), prob_text),
        (ft("mc_cagr_range", lang), cagr_range),
        (ft("mc_tail_dd", lang), tail_dd),
    ]
    metrics = "".join(
        f"<div class='qsx-mc-stat'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in cells
    )
    return (
        f"<div class='qsx-mc-summary {verdict['tone']}'>"
        f"<div class='qsx-mc-verdict'>{escape(verdict['text'])}</div>"
        f"<div class='qsx-mc-grid'>{metrics}</div>"
        f"<div class='qsx-small' style='margin-top:10px;'>{escape(ft('mc_source_note', lang))}</div>"
        "</div>"
    )


def _risk_level(score: float | None, *, high_below: float = 55.0, medium_below: float = 72.0) -> str:
    if score is None:
        return "medium"
    try:
        value = float(score)
    except Exception:
        return "medium"
    if value < high_below:
        return "high"
    if value < medium_below:
        return "medium"
    return "low"


def _risk_tone(level: str) -> str:
    return {"low": "green", "medium": "amber", "high": "rose"}.get(level, "amber")


def _risk_label(level: str, lang: str) -> str:
    return ft(level, lang)


def core_metric_rows(r: pd.Series, report, meta: dict) -> list[tuple[str, str]]:
    ppy = float(report.meta.get("ppy") or meta.get("ppy") or 252.0)
    eq = equity_curve(r)
    return [
        ("CAGR", _fmt_pct_value(cagr(r, ppy))),
        ("Sharpe", _fmt_number(sharpe(r, ppy))),
        ("Sortino", _fmt_number(sortino(r, ppy))),
        ("Calmar", _fmt_number(calmar(r, ppy))),
        ("MDD", _fmt_pct_value(max_drawdown(eq), 0)),
    ]


def risk_tags(report, triage: dict, meta: dict, co: dict, lang: str) -> list[dict]:
    flags = {f.get("code") for f in report.flags if f.get("code")}
    issues = {i.get("code") for i in co.get("issues", []) if i.get("code")}
    drawdown = _risk_level(report.risk.value, high_below=55, medium_below=72)
    stability = _risk_level(report.return_quality.value, high_below=55, medium_below=72)
    overfit = _risk_level(report.credibility.value, high_below=55, medium_below=72)
    if {"TOO_GOOD_TO_BE_TRUE", "DSR_FAIL", "OOS_NEGATIVE_RETURN"} & (flags | issues):
        overfit = "high"
    elif {"DSR_OVERFIT_RISK", "OVERFIT_SUSPECT_HOLDOUT", "LOW_EFFECTIVE_SAMPLE"} & (flags | issues):
        overfit = "medium" if overfit == "low" else overfit
    sample = "low" if report.meta.get("sample_ok", True) and float(meta.get("span_years") or 0) >= 2 else "medium"
    tail = drawdown

    if {"INSUFFICIENT_SAMPLE", "SHORT_TRACK_RECORD", "LOW_EFFECTIVE_SAMPLE"} & (flags | issues) or not report.meta.get("sample_ok", True):
        sample = "high"
    evidence = triage.get("evidence_confidence", {})
    if evidence.get("level") in {"low", "limited"} and sample != "high":
        sample = "medium"
    if report.risk.raw.get("mdd") is not None and abs(float(report.risk.raw.get("mdd") or 0)) >= 0.35:
        tail = "high"
    elif report.risk.raw.get("mdd") is not None and abs(float(report.risk.raw.get("mdd") or 0)) >= 0.20 and tail == "low":
        tail = "medium"

    return [
        {"key": "drawdown_risk", "level": drawdown},
        {"key": "stability_risk", "level": stability},
        {"key": "overfit_risk", "level": overfit},
        {"key": "sample_risk", "level": sample},
        {"key": "tail_risk", "level": tail},
    ]


def render_metric_strip(metrics_rows: list[tuple[str, str]]) -> None:
    cols = st.columns(len(metrics_rows))
    for col, (label, value) in zip(cols, metrics_rows):
        col.metric(label, value)


def strategy_scorecard_png(report, returns: pd.Series, mc: dict | None, bench_cmp: dict | None, triage: dict, lang: str) -> bytes | None:
    try:
        tmp = os.path.join(tempfile.gettempdir(), "qsx_strategy_scorecard.png")
        render_unified_png(
            report,
            returns,
            tmp,
            brand=tr("share_card_brand", lang),
            bench=bench_cmp,
            lang=lang,
            triage=triage,
        )
        with open(tmp, "rb") as f:
            return f.read()
    except Exception:  # noqa: BLE001
        return None


def risk_tags_markup(tags: list[dict], lang: str) -> str:
    cells = "".join(
        (
            f"<div class='qsx-risk-tag {_risk_tone(tag['level'])}'>"
            f"<span>{escape(ft(tag['key'], lang))}</span>"
            f"<strong>{escape(_risk_label(tag['level'], lang))}</strong>"
            "</div>"
        )
        for tag in tags
    )
    return f"<div class='qsx-risk-grid'>{cells}</div>"


def advanced_metric_grid(items: list[tuple[str, str, Optional[str]]]) -> str:
    cells = []
    for label, value, note in items:
        note_html = f"<span>{escape(note)}</span>" if note else ""
        cells.append(
            "<div class='qsx-advanced-metric'>"
            f"<small>{escape(label)}</small>"
            f"<strong>{escape(value)}</strong>"
            f"{note_html}"
            "</div>"
        )
    return "<div class='qsx-advanced-metrics'>" + "".join(cells) + "</div>"


def _chart_png(fig) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        fig.savefig(path, format="png", dpi=170, transparent=True, bbox_inches="tight", pad_inches=0.04)
        with open(path, "rb") as f:
            return f.read()
    finally:
        plt.close(fig)
        try:
            os.remove(path)
        except OSError:
            pass


def _style_static_axis(ax, title: str) -> None:
    ax.set_facecolor("#0d1117")
    ax.set_title(title, loc="left", fontsize=11.5, color="#f4f4f5", fontweight="bold", pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(True, color="#2a3647", alpha=0.55, linewidth=0.8)
    ax.tick_params(colors="#a1a1aa", labelsize=8.5, length=0)
    ax.margins(x=0.02)


def _render_static_chart(title: str, series: dict[str, pd.Series], *,
                         kind: str = "line", lang: str = "zh", log_y: bool = False,
                         fill_between: Optional[tuple[pd.Series, pd.Series]] = None) -> Optional[bytes]:
    clean: dict[str, pd.Series] = {}
    for label, values in series.items():
        s = pd.Series(values).astype(float).replace([float("inf"), float("-inf")], pd.NA).dropna()
        if len(s):
            clean[label] = s
    if not clean:
        return None
    import matplotlib.pyplot as plt
    from qsx_strategy_score.report import _maybe_cjk_font

    _maybe_cjk_font(plt, title, *clean.keys())
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(7.4, 2.65), facecolor="#0d1117")
    _style_static_axis(ax, title)
    palette = ["#34d399", "#fbbf24", "#60a5fa", "#a78bfa"]
    if fill_between is not None:
        lo, hi = fill_between
        lo = pd.Series(lo).astype(float)
        hi = pd.Series(hi).astype(float)
        x = clean[next(iter(clean))].index
        ax.fill_between(x, lo.to_numpy(), hi.to_numpy(), color="#60a5fa", alpha=0.16, linewidth=0)
    for i, (label, s) in enumerate(clean.items()):
        color = palette[i % len(palette)]
        if kind == "area":
            ax.fill_between(s.index, s.to_numpy(), 0.0, color=color, alpha=0.34, linewidth=0)
            ax.plot(s.index, s.to_numpy(), color=color, linewidth=1.7)
        else:
            ax.plot(s.index, s.to_numpy(), color=color, linewidth=2.1, solid_capstyle="round", label=label)
    if log_y and all(bool((s > 0).all()) for s in clean.values()):
        ax.set_yscale("log")
    if len(clean) > 1:
        leg = ax.legend(loc="upper left", bbox_to_anchor=(0, 1.02), ncol=min(3, len(clean)),
                        frameon=False, fontsize=8.5, handlelength=2.2, columnspacing=1.2)
        for text in leg.get_texts():
            text.set_color("#d4d4d8")
    if kind == "area":
        ax.yaxis.set_major_formatter(lambda x, _pos: f"{x:.0f}%")
    fig.tight_layout(pad=0.5)
    return _chart_png(fig)


def render_advanced_chart(title: str, png: bytes | None) -> None:
    if png:
        b64 = base64.b64encode(png).decode("ascii")
        st.markdown(
            f"<div class='qsx-chart-card'><img src='data:image/png;base64,{b64}' alt='{escape(title)}'></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"<div class='qsx-chart-card'><div class='qsx-muted'>{escape(title)}</div></div>", unsafe_allow_html=True)


def problem_list_markup(co: dict, lang: str) -> str:
    issues = list(co.get("issues") or [])[:4]
    if not issues:
        return f"<div class='qsx-muted'>{escape(ft('no_major_issue', lang))}</div>"
    rows = []
    for i, issue in enumerate(issues, start=1):
        problem, _direction = local_issue(issue, lang)
        rows.append(
            f"<div class='qsx-problem-row'><span>{i}</span><strong>{escape(problem)}</strong></div>"
        )
    return "<div class='qsx-problem-list'>" + "\n".join(rows) + "</div>"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --qsx-bg: #0a0a0b;
          --qsx-panel: rgba(24, 24, 27, 0.62);
          --qsx-panel-2: rgba(9, 9, 11, 0.78);
          --qsx-border: rgba(63, 63, 70, 0.78);
          --qsx-muted: #a1a1aa;
          --qsx-faint: #71717a;
          --qsx-text: #f4f4f5;
          --qsx-green: #34d399;
          --qsx-violet: #8b5cf6;
          --qsx-amber: #f59e0b;
          --qsx-rose: #fb7185;
        }
        html, body, [data-testid="stAppViewContainer"], .stApp {
          background:
            radial-gradient(ellipse 60% 50% at 15% 0%, rgba(16, 185, 129, 0.08), transparent 60%),
            radial-gradient(ellipse 50% 40% at 85% 100%, rgba(99, 102, 241, 0.07), transparent 60%),
            var(--qsx-bg) !important;
          color: var(--qsx-text) !important;
        }
        [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {display: none !important;}
        [data-testid="stDecoration"] {background: linear-gradient(90deg, #10b981, #8b5cf6) !important;}
        .block-container {
          max-width: 1050px !important;
          padding: 28px 20px 56px !important;
        }
        h1, h2, h3, p, li, label, span, div {font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", "Inter", sans-serif;}
        .qsx-nav {
          display: flex; align-items: center; justify-content: space-between;
          border-bottom: 1px solid rgba(63,63,70,.55); padding: 2px 0 24px; margin-bottom: 46px;
        }
        .qsx-brand {display: flex; align-items: center; gap: 12px; font-weight: 800; font-size: 18px; letter-spacing: .01em;}
        .qsx-logo {
          width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center;
          color: #052e2b; font-weight: 900;
          background: linear-gradient(135deg, #34d399, #14b8a6);
          box-shadow: 0 0 26px rgba(16,185,129,.45);
        }
        .qsx-x {color: #34d399;}
        .qsx-product-pill {
          color: #d4d4d8; border: 1px solid rgba(52,211,153,.8); border-radius: 8px;
          padding: 5px 9px; font-size: 14px; font-weight: 750;
        }
        .qsx-built-by {
          position: fixed; right: 18px; bottom: 14px; z-index: 9999;
          display: inline-flex; align-items: center; gap: 7px;
          color: #a1a1aa; background: rgba(9,9,11,.82);
          border: 1px solid rgba(63,63,70,.76); border-radius: 999px;
          padding: 8px 11px; font-size: 12px; line-height: 1; text-decoration: none;
          backdrop-filter: blur(12px);
        }
        .qsx-built-by:hover {color:#f4f4f5;border-color:rgba(52,211,153,.7);}
        .qsx-built-by span {color:#34d399;font-weight:850;}
        .qsx-hero {margin-bottom: 28px;}
        .qsx-eyebrow {font-size: 13px; color: #34d399; font-weight: 700; margin-bottom: 16px;}
        .qsx-title {font-size: clamp(38px, 5vw, 58px); line-height: 1.05; font-weight: 850; letter-spacing: 0; color: #fafafa; margin: 0 0 22px;}
        .qsx-subtitle {max-width: 940px; color: #a1a1aa; font-size: 17px; line-height: 1.7; margin: 0;}
        .qsx-subtitle span {display:block;}
        .qsx-card {
          border: 1px solid var(--qsx-border); background: var(--qsx-panel);
          border-radius: 12px; padding: 24px;
        }
        .qsx-result-card {
          border: 1px solid rgba(63,63,70,.82); background: rgba(9,9,11,.78);
          border-radius: 12px; padding: 22px; margin-top: 18px;
        }
        .qsx-result-kicker {color:#34d399;font-size:13px;font-weight:800;margin-bottom:10px;}
        .qsx-result-title {font-size:26px;line-height:1.2;font-weight:850;color:#fafafa;margin-bottom:8px;}
        .qsx-card-tight {
          border: 1px solid var(--qsx-border); background: var(--qsx-panel);
          border-radius: 12px; padding: 18px;
        }
        .qsx-pro {
          border: 1px solid rgba(139,92,246,.48); background: rgba(139,92,246,.07);
          border-radius: 12px; padding: 22px; margin-top: 26px;
        }
        .qsx-overlay {
          border: 1px solid rgba(52,211,153,.46); background: rgba(16,185,129,.07);
          border-radius: 12px; padding: 22px; margin-top: 18px;
        }
        .qsx-pro-title {font-weight: 800; color: #fafafa; margin-bottom: 10px;}
        .qsx-pro-body {color: #a1a1aa; line-height: 1.65; font-size: 14px;}
        .qsx-button {
          display: inline-flex; align-items: center; justify-content: center; margin-top: 18px;
          color: white; background: #7c3aed; border-radius: 8px; padding: 11px 18px; font-weight: 800;
        }
        .qsx-button.green {background: #10b981; color: #020617;}
        div[data-testid="stButton"] > button {
          background: #10b981 !important; color: #020617 !important; border: 0 !important;
          border-radius: 8px !important; font-weight: 850 !important; min-height: 48px !important;
          box-shadow: 0 0 0 1px rgba(52,211,153,.2), 0 14px 34px rgba(16,185,129,.18) !important;
        }
        div[data-testid="stDownloadButton"] > button {
          background: #10b981 !important; color: #020617 !important;
          border: 0 !important; border-radius: 8px !important;
          font-weight: 750 !important; min-height: 42px !important;
          box-shadow: 0 0 0 1px rgba(52,211,153,.2), 0 14px 34px rgba(16,185,129,.18) !important;
        }
        div[data-testid="stDownloadButton"] > button:hover {
          background: #34d399 !important; color: #020617 !important;
        }
        .qsx-pill-row {display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px;}
        .qsx-pill {border: 1px solid rgba(52,211,153,.24); background: rgba(52,211,153,.08); color: #bbf7d0; padding: 7px 10px; border-radius: 8px; font-size: 12px;}
        .qsx-upload-copy {
          border: 2px dashed rgba(82,82,91,.95); border-radius: 12px; background: rgba(24,24,27,.45);
          min-height: 170px; display: flex; align-items: center; justify-content: center;
          text-align: center; color: #d4d4d8; margin-bottom: -142px; pointer-events: none;
        }
        .qsx-upload-copy strong {display: block; color: #f4f4f5; font-size: 17px; margin-bottom: 12px;}
        .qsx-upload-copy small {display: block; color: #71717a; line-height: 1.55; max-width: 620px;}
        div[data-testid="stFileUploader"] {
          border: 0 !important; border-radius: 12px; background: transparent !important;
          min-height: 170px; padding: 16px;
        }
        div[data-testid="stFileUploader"] section {min-height: 132px; opacity: 0;}
        div[data-testid="stFileUploader"] section * {
          color: transparent !important;
          border-color: transparent !important;
          background: transparent !important;
          box-shadow: none !important;
        }
        div[data-testid="stFileUploader"] label {display: none;}
        .qsx-upload-copy.compact {
          min-height: 106px;
          margin-bottom: -106px;
          padding: 14px;
        }
        .qsx-upload-copy.compact strong {font-size: 14px; margin-bottom: 8px;}
        .qsx-upload-copy.compact small {font-size: 12px;}
        .qsx-upload-compact-wrap div[data-testid="stFileUploader"] {
          min-height: 106px;
          padding: 10px;
        }
        .qsx-upload-compact-wrap div[data-testid="stFileUploader"] section {min-height: 84px;}
        .stSelectbox label, .stRadio label {color: #a1a1aa !important; font-weight: 650 !important;}
        div[data-baseweb="select"] > div, .stTextInput input {
          background: #09090b !important; border-color: #3f3f46 !important; color: #e4e4e7 !important; border-radius: 8px !important;
        }
        div[role="radiogroup"] label {color: #d4d4d8 !important;}
        .stAlert {background: rgba(24,24,27,.72) !important; border-color: rgba(63,63,70,.8) !important; color: #e4e4e7 !important;}
        .stMetric {background: rgba(9,9,11,.35); border: 1px solid rgba(63,63,70,.66); border-radius: 10px; padding: 14px;}
        [data-testid="stMetricLabel"] {color: #a1a1aa !important;}
        [data-testid="stMetricValue"] {color: #f4f4f5 !important;}
        .qsx-score-number {font-size: 72px; font-weight: 900; color: #34d399; line-height: .95;}
        .qsx-grade {display: inline-flex; border: 1px solid rgba(52,211,153,.36); color: #6ee7b7; background: rgba(52,211,153,.08); border-radius: 999px; padding: 6px 12px; font-weight: 800; margin-top: 8px;}
        .qsx-headline {font-size: 19px; line-height: 1.55; color: #fafafa; font-weight: 700;}
        .qsx-light {display: flex; gap: 9px; align-items: center; color: #d4d4d8; font-size: 14px; margin-top: 9px;}
        .qsx-dot {width: 8px; height: 8px; border-radius: 50%; background: #71717a; display: inline-block; flex: 0 0 auto;}
        .qsx-dot.green {background: #34d399;} .qsx-dot.amber {background: #f59e0b;} .qsx-dot.rose {background: #fb7185;}
        .qsx-section-title {font-weight: 850; color: #f4f4f5; font-size: 16px; margin-bottom: 14px;}
        .qsx-muted {color: #a1a1aa; font-size: 14px; line-height: 1.65;}
        .qsx-small {color: #71717a; font-size: 12px; line-height: 1.55;}
        .qsx-metric-grid {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:12px;}
        .qsx-metric-cell {border:1px solid rgba(63,63,70,.7);background:rgba(24,24,27,.55);border-radius:10px;padding:13px 12px;min-width:0;}
        .qsx-metric-label {color:#a1a1aa;font-size:12px;font-weight:700;}
        .qsx-metric-value {color:#f4f4f5;font-size:22px;font-weight:850;margin-top:6px;font-variant-numeric:tabular-nums;white-space:nowrap;}
        .qsx-chart-card {
          border: 1px solid rgba(63,63,70,.74);
          background: #0d1117;
          border-radius: 12px;
          padding: 10px;
          min-height: 246px;
          overflow: hidden;
          margin-bottom: 12px;
        }
        .qsx-chart-card img {
          display: block;
          width: 100%;
          height: auto;
          border-radius: 8px;
        }
        .qsx-advanced-metrics {
          display:grid;
          grid-template-columns:repeat(4,minmax(0,1fr));
          gap:10px;
          margin: 2px 0 18px;
        }
        .qsx-advanced-metric {
          border:1px solid rgba(63,63,70,.7);
          background:rgba(9,9,11,.44);
          border-radius:10px;
          padding:13px 14px;
          min-width:0;
        }
        .qsx-advanced-metric small {
          display:block;
          color:#a1a1aa;
          font-size:11.5px;
          line-height:1.25;
          font-weight:750;
        }
        .qsx-advanced-metric strong {
          display:block;
          color:#f4f4f5;
          font-size:24px;
          line-height:1.12;
          font-weight:850;
          margin-top:8px;
          font-variant-numeric:tabular-nums;
          white-space:nowrap;
        }
        .qsx-advanced-metric span {
          display:block;
          color:#71717a;
          font-size:11px;
          margin-top:5px;
        }
        .qsx-risk-grid {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-top:12px;}
        .qsx-risk-tag {border:1px solid rgba(63,63,70,.7);background:rgba(24,24,27,.44);border-radius:10px;padding:12px;min-height:76px;}
        .qsx-risk-tag span {display:block;color:#a1a1aa;font-size:12px;line-height:1.25;font-weight:700;}
        .qsx-risk-tag strong {display:block;margin-top:10px;font-size:18px;font-weight:850;}
        .qsx-risk-tag.green strong {color:#34d399;} .qsx-risk-tag.amber strong {color:#f59e0b;} .qsx-risk-tag.rose strong {color:#fb7185;}
        .qsx-problem-list {display:grid;gap:10px;margin-top:10px;}
        .qsx-problem-row {display:flex;gap:12px;align-items:flex-start;border:1px solid rgba(245,158,11,.22);background:rgba(245,158,11,.06);border-radius:10px;padding:12px 14px;}
        .qsx-problem-row span {display:grid;place-items:center;width:24px;height:24px;border-radius:999px;background:rgba(245,158,11,.16);color:#fde68a;font-weight:850;font-size:12px;flex:0 0 auto;}
        .qsx-problem-row strong {color:#f4f4f5;font-size:14px;line-height:1.5;}
        .qsx-mc-summary {border:1px solid rgba(63,63,70,.74);background:rgba(24,24,27,.54);border-radius:10px;padding:14px;margin:8px 0 12px;}
        .qsx-mc-summary.green {border-color:rgba(52,211,153,.34);background:rgba(16,185,129,.07);}
        .qsx-mc-summary.amber {border-color:rgba(245,158,11,.34);background:rgba(245,158,11,.07);}
        .qsx-mc-summary.rose {border-color:rgba(251,113,133,.34);background:rgba(251,113,133,.07);}
        .qsx-mc-verdict {color:#f4f4f5;font-size:14px;line-height:1.55;font-weight:750;}
        .qsx-mc-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:12px;}
        .qsx-mc-stat {border:1px solid rgba(63,63,70,.55);border-radius:8px;padding:10px;background:rgba(9,9,11,.36);min-width:0;}
        .qsx-mc-stat span {display:block;color:#a1a1aa;font-size:11px;font-weight:700;line-height:1.25;}
        .qsx-mc-stat strong {display:block;color:#f4f4f5;font-size:16px;font-weight:850;margin-top:5px;white-space:nowrap;}
        .qsx-issue {border: 1px solid rgba(245,158,11,.25); background: rgba(245,158,11,.07); border-radius: 10px; padding: 14px; margin-bottom: 10px;}
        .qsx-issue strong {color: #fde68a;}
        .qsx-issue div {color: #d4d4d8; margin-top: 6px; font-size: 14px; line-height: 1.55;}
        @media (max-width: 720px) {
          .qsx-product-pill {display: none;}
          .qsx-built-by {right: 10px; bottom: 10px; font-size: 11px; padding: 7px 9px;}
          .qsx-title {font-size: 36px;}
          .block-container {padding-left: 16px !important; padding-right: 16px !important;}
          .qsx-metric-grid, .qsx-risk-grid, .qsx-mc-grid, .qsx-advanced-metrics {grid-template-columns:repeat(2,minmax(0,1fr));}
          .qsx-metric-value {font-size:19px;}
          .qsx-advanced-metric strong {font-size:20px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def pillar_bar(label: str, value: float | None, hint: str) -> None:
    v = 0 if value is None else max(0, min(100, float(value)))
    color = "#34d399" if v >= 72 else "#f59e0b" if v >= 55 else "#fb923c"
    value_text = "-" if value is None else f"{v:.0f}"
    st.markdown(
        f"""
        <div style="margin: 14px 0 16px;">
          <div style="display:flex;align-items:baseline;justify-content:space-between;font-size:14px;">
            <span style="color:#d4d4d8;">{label}</span>
            <span style="color:#a1a1aa;font-variant-numeric:tabular-nums;">{value_text} <span style="color:#52525b;">/ 100</span></span>
          </div>
          <div style="height:8px;background:#27272a;border-radius:999px;overflow:hidden;margin-top:8px;">
            <div style="height:100%;width:{v:.1f}%;background:{color};border-radius:999px;"></div>
          </div>
          <div class="qsx-small" style="margin-top:6px;">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def edge_tone(edge: str | None) -> str:
    if edge == "beat":
        return "green"
    if edge in {"lost", "random_fail"}:
        return "rose"
    if edge in {"hold_only", "marginal", "luck_unclear"}:
        return "amber"
    return ""


def fmt_pct(x) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except Exception:
        return "-"


def render_overlay_preview(
    returns: pd.Series,
    lang: str,
    *,
    upload=None,
    meta: dict | None = None,
    intro: bool = True,
    button_label: str | None = None,
) -> None:
    if intro:
        st.markdown(
            f"""
            <div class="qsx-overlay">
              <div class="qsx-pro-title">{tr("overlay_title", lang)}</div>
              <div class="qsx-pro-body">{tr("overlay_body", lang)}</div>
              <div class="qsx-small" style="margin-top:12px;">{tr("overlay_privacy", lang)}</div>
              <div class="qsx-small" style="margin-top:6px;">{tr("overlay_online", lang)}</div>
              <div class="qsx-small" style="margin-top:6px;">{tr("overlay_trade_log_note", lang)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="qsx-small" style="margin:8px 0 12px;">
              {tr("overlay_privacy", lang)}<br/>
              {tr("overlay_online", lang)}<br/>
              {tr("overlay_trade_log_note", lang)}
            </div>
            """,
            unsafe_allow_html=True,
        )
    label = button_label or tr("overlay_button", lang)
    if not st.button(label, type="primary"):
        return
    try:
        with st.spinner(label):
            overlay_returns = returns
            if (meta or {}).get("input_type") == "trade_log" and upload is not None:
                try:
                    upload.seek(0)
                except Exception:  # noqa: BLE001
                    pass
                overlay_returns = trade_log_to_daily_overlay_returns(upload, filename=getattr(upload, "name", None))
            preview = run_overlay_preview(overlay_returns, lang=lang)
    except OverlayPreviewError as e:
        st.warning(f"{tr('overlay_unavailable', lang)}: {e}")
        return

    card = preview.get("cardPngBase64")
    if isinstance(card, str) and card:
        png = base64.b64decode(card)
        st.image(png, use_container_width=True)
        st.markdown(
            f"""<div class="qsx-small" style="margin-top:8px;">{tr("overlay_hash", lang)}: {escape(str(preview.get("inputSha256", "-")))}</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"{tr('overlay_unavailable', lang)}: missing preview image")


def main() -> None:
    st.set_page_config(page_title="QSX Strategy Scorecard", page_icon="Q", layout="wide")
    inject_css()

    initial_lang = st.session_state.get("app_lang", "en")
    lang = initial_lang if initial_lang in SUPPORTED_LANGS else "en"

    st.markdown(
        f"""
        <a class="qsx-built-by" href="https://www.quantscopex.com/" target="_blank" rel="noopener noreferrer">
          {tr("built_by", lang)} <span>↗</span>
        </a>
        """,
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([0.72, 0.28])
    with top_left:
        st.markdown(
            f"""
            <div class="qsx-nav">
              <div class="qsx-brand"><div class="qsx-logo">Q</div><div>QuantScope<span class="qsx-x">X</span></div></div>
              <div class="qsx-product-pill">{tr("nav_score", lang)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_right:
        lang = st.selectbox(
            tr("language", lang),
            list(SUPPORTED_LANGS),
            index=list(SUPPORTED_LANGS).index(lang),
            format_func=lang_label,
            key="app_lang",
            label_visibility="collapsed",
        )

    st.markdown(
        f"""
        <section class="qsx-hero">
          <div class="qsx-eyebrow">{tr("eyebrow", lang)}</div>
          <h1 class="qsx-title">{tr("title", lang)}</h1>
          <p class="qsx-subtitle"><span>{tr("subtitle", lang)}</span><span>{tr("subtitle_assets", lang)}</span></p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="qsx-upload-copy">
          <div>
            <strong>{tr("upload_title", lang)}</strong>
            <small>{tr("upload_help", lang)}</small>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    up = st.file_uploader(
        tr("strategy_file", lang),
        type=["csv", "tsv", "txt", "xlsx", "xls", "xlsm"],
        help=tr("upload_size_help", lang),
        label_visibility="collapsed",
    )

    control_cols = st.columns([0.26, 0.36, 0.38])
    with control_cols[0]:
        input_values = ["auto", "returns", "equity", "trade_log"]
        itype = st.selectbox(
            tr("input_type", lang),
            input_values,
            format_func=lambda v: {
                "auto": tr("input_auto", lang),
                "returns": tr("input_returns", lang),
                "equity": tr("input_equity", lang),
                "trade_log": tr("input_trade_log", lang),
            }.get(v, v),
            key="input_type_value",
        )
    with control_cols[1]:
        asset_opts = [AUTO_ASSET, SKIP_ASSET] + ASSET_KEYS
        asset_choice = st.selectbox(
            tr("benchmark_asset", lang),
            asset_opts,
            format_func=lambda k: asset_label(k, lang),
            key="asset_choice_value",
        )
        st.caption(tr("benchmark_help", lang))
    with control_cols[2]:
        st.markdown(
            f"""
            <div class="qsx-upload-compact-wrap">
              <div class="qsx-upload-copy compact">
                <div>
                  <strong>{tr("custom_benchmark", lang)}</strong>
                  <small>{tr("custom_help", lang)}</small>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        bench_up = st.file_uploader(
            tr("custom_benchmark", lang),
            type=["csv", "tsv", "txt", "xlsx", "xls", "xlsm"],
            help=f"{tr('custom_help', lang)} {tr('upload_size_help', lang)}",
            label_visibility="collapsed",
        )

    if not upload_size_ok(up, lang) or not upload_size_ok(bench_up, lang):
        return

    if up is None:
        st.markdown(
            f"""
            <div class="qsx-card" style="margin-top:28px;">
              <div class="qsx-section-title">{tr("waiting_title", lang)}</div>
              <div class="qsx-muted">{tr("waiting_body", lang)}</div>
              <div class="qsx-pill-row">
                <span class="qsx-pill">{ft("score_label", lang)} 0-100</span>
                <span class="qsx-pill">{ft("core_metrics", lang)}</span>
                <span class="qsx-pill">{ft("risk_diagnosis", lang)}</span>
                <span class="qsx-pill">{ft("main_problems", lang)}</span>
                <span class="qsx-pill">{ft("overlay_primary", lang)}</span>
              </div>
            </div>
            <p class="qsx-small" style="margin-top:24px;max-width:760px;">{tr("disclaimer", lang)}</p>
            """,
            unsafe_allow_html=True,
        )
        return

    try:
        r, meta = load_returns(up, input_type=itype)
    except Exception as e:  # noqa: BLE001
        st.error(f"{tr('read_error', lang)}: {e}")
        return

    st.markdown(
        f"""
        <div class="qsx-card-tight" style="margin-top:22px;">
          <div class="qsx-section-title">{tr("ready_title", lang)}</div>
          <div class="qsx-muted">{meta.get("input_type", itype)} · {len(r):,} observations · {meta.get("span_years", 0):.2f} {tr("years", lang)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    detection = None
    choice = SKIP_ASSET
    try:
        detection = detect_asset(r, filename=getattr(up, "name", None), symbol=meta.get("symbol"))
    except Exception:  # noqa: BLE001
        detection = None

    bench_cmp = None
    resolved_profile = "other"
    asset_note = ""
    if bench_up is not None:
        asset_note = tr("using_custom", lang)
        try:
            px = load_prices(bench_up)
            bench_cmp = benchmark_compare(r, px)
            if bench_cmp is None:
                st.warning(tr("asset_overlap_warn", lang))
        except Exception as e:  # noqa: BLE001
            st.warning(f"{tr('bench_error', lang)}: {e}")
    elif asset_choice == AUTO_ASSET:
        if detection is not None and detection.best is not None and detection.best.key in ASSET_KEYS:
            choice = detection.best.key
            asset_note = f"{tr('auto_detected', lang)}: {ASSET_LABELS.get(choice, choice)}"
        else:
            asset_note = tr("auto_failed", lang)
            st.warning(asset_note)
    elif asset_choice == SKIP_ASSET:
        asset_note = tr("asset_skipped", lang)
    else:
        choice = asset_choice
        asset_note = f"{tr('manual_asset', lang)}: {ASSET_LABELS.get(choice, choice)}"

    if bench_up is None and choice != SKIP_ASSET:
        px = asset_close(choice)
        resolved_profile = asset_lib.ASSET_BY_KEY[choice].profile
        if px is not None:
            bench_cmp = benchmark_compare(r, px)
            if bench_cmp is None:
                st.warning(tr("asset_overlap_warn", lang))

    report = score_unified(r, resolved_profile, meta=meta, benchmark=bench_cmp)
    co = coaching(report)
    triage = build_triage_diagnostics(r, report, meta=meta, benchmark=bench_cmp, lang=lang).to_dict()
    mc = monte_carlo(r, report.meta["ppy"])

    edge = report.lights.get("edge")
    rand_p = report.meta.get("random_p")
    edge_suffix = f" (p={rand_p:.2f})" if rand_p is not None and edge in {"beat", "random_fail"} else ""
    track_years = float(meta.get("span_years") or report.meta.get("span_years") or 0.0)
    cap = ""
    if report.meta.get("capped"):
        cap = f"<div class='qsx-light'><span class='qsx-dot amber'></span>{tr('cap_prefix', lang)}: {report.display:.0f}</div>"

    evidence = report.meta.get("evidence") or {}
    evidence_status = evidence.get("status", "insufficient")
    evidence_label = t(f"evidence.{evidence_status}", lang)
    next_step = triage.get("next_step") or {}
    evidence_reasons = ", ".join(evidence.get("reason_codes") or [])
    st.markdown(
        f"""
        <div class="qsx-result-card">
          <div class="qsx-result-kicker">{ft("results_title", lang)}</div>
          <div class="qsx-result-title">{escape(local_headline(report, lang))}</div>
          <div class="qsx-muted">{ft("results_subtitle", lang)}</div>
          <div class="qsx-small" style="margin-top:10px;">{tr("evidence_status", lang)}: <strong>{escape(evidence_label)}</strong>{(" · " + escape(evidence_reasons.replace("_", " ").lower())) if evidence_reasons else ""}</div>
          <div class="qsx-small" style="margin-top:6px;">{escape(asset_note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    scorecard_png = strategy_scorecard_png(report, r, mc, bench_cmp, triage, lang)
    if scorecard_png:
        st.download_button(
            tr("download_strategy_card", lang),
            scorecard_png,
            file_name="qsx_strategy_scorecard.png",
            mime="image/png",
            type="primary",
            use_container_width=True,
        )
        st.markdown(f"<div class='qsx-small' style='margin-top:-4px;'>{tr('share_card_note', lang)}</div>", unsafe_allow_html=True)
    else:
        st.caption(tr("share_card_unavailable", lang))

    left, right = st.columns([0.27, 0.73])
    with left:
        st.markdown(
            f"""
            <div class="qsx-card">
              <div class="qsx-small">{ft("score_label", lang)}</div>
              <div class="qsx-score-number">{report.display:.0f}</div>
              <div class="qsx-small">/ 100</div>
              <div class="qsx-grade">{local_grade(report.grade, lang)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <div class="qsx-section-title" style="margin-top:4px;">{ft("core_metrics", lang)}</div>
            """,
            unsafe_allow_html=True,
        )
        render_metric_strip(core_metric_rows(r, report, meta))

    st.markdown(f"<div class='qsx-section-title' style='margin-top:18px;'>{tr('pillars', lang)}</div>", unsafe_allow_html=True)
    pillar_bar(
        tr("return_quality", lang),
        report.return_quality.value,
        f"{tr('sharpe', lang)} {report.return_quality.raw.get('sharpe', 0):.2f}",
    )
    pillar_bar(tr("credibility", lang), report.credibility.value, tr("cred_hint", lang))
    pillar_bar(
        tr("risk", lang),
        report.risk.value,
        f"{tr('maxdd', lang)} {fmt_pct(report.risk.raw.get('mdd', 0))}",
    )

    ep = triage["edge_persistence"]
    ev = triage["evidence_confidence"]
    dep = triage["dependency_lite"]
    st.markdown(f"<div class='qsx-section-title' style='margin-top:18px;'>{tr('triage', lang)}</div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric(t("edge_persistence", lang), ep.get("label_local") or ep.get("label") or "-")
    m2.metric(t("evidence_confidence", lang), ev.get("level_local") or ev.get("level") or "-")
    m3.metric(tr("dependency", lang), (dep.get("label_local") or dep.get("label") or tr("unavailable", lang)) if dep.get("available") else tr("unavailable", lang))

    eq = equity_curve(r)
    dd = (eq / eq.cummax() - 1.0) * 100.0
    st.markdown(f"<div class='qsx-section-title' style='margin-top:22px;'>{ft('advanced_details', lang)}</div>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        if bench_cmp and report.judgement != "FLAGGED":
            chart_title = tr("equity_vs_hold", lang)
            png = _render_static_chart(
                chart_title,
                {
                    ("策略" if lang == "zh" else "Strategy"): pd.Series(bench_cmp["strat_curve"]),
                    ("买入持有" if lang == "zh" else "Buy & hold"): pd.Series(bench_cmp["bnh_curve"]),
                },
                lang=lang,
                log_y=True,
            )
            render_advanced_chart(chart_title, png)
        else:
            chart_title = tr("equity", lang)
            png = _render_static_chart(chart_title, {("策略" if lang == "zh" else "Strategy"): eq}, lang=lang, log_y=True)
            render_advanced_chart(chart_title, png)
    with g2:
        chart_title = tr("drawdown", lang)
        png = _render_static_chart(chart_title, {tr("drawdown", lang): dd}, kind="area", lang=lang)
        render_advanced_chart(chart_title, png)

    if bench_cmp and report.judgement != "FLAGGED":
        s, b = bench_cmp["strat"], bench_cmp["bnh"]
        st.markdown(
            advanced_metric_grid([
                ("Calmar alpha", f"{bench_cmp['cal_alpha']:+.2f}", None),
                ("Calmar S/H", f"{s['calmar']:.2f} / {b['calmar']:.2f}", None),
                ("MaxDD S/H", f"{s['mdd'] * 100:.0f}% / {b['mdd'] * 100:.0f}%", None),
                ("Return capture", f"{bench_cmp['ret_capture']:.2f}x", None),
            ]),
            unsafe_allow_html=True,
        )

    if mc:
        st.markdown(monte_carlo_summary_markup(mc, lang), unsafe_allow_html=True)
        mc_index = eq.index
        chart_title = tr("monte_carlo", lang)
        mc_series = {
            ("中位数" if lang == "zh" else "Median"): pd.Series(mc["band_mid"], index=mc_index),
            ("实际" if lang == "zh" else "Actual"): pd.Series(eq.values, index=mc_index),
        }
        png = _render_static_chart(
            chart_title,
            mc_series,
            lang=lang,
            log_y=True,
            fill_between=(
                pd.Series(mc["band_lo"], index=mc_index),
                pd.Series(mc["band_hi"], index=mc_index),
            ),
        )
        render_advanced_chart(chart_title, png)

    st.markdown(
        f"""
        <div class="qsx-card-tight" style="margin-top:16px;">
          <div class="qsx-section-title">{ft("verdict", lang)}</div>
          <div class="qsx-light"><span class="qsx-dot {edge_tone(edge)}"></span>{tr(f"edge.{edge}", lang)}{edge_suffix}</div>
          <div class="qsx-light"><span class="qsx-dot {'green' if report.meta.get('sample_ok', True) else 'amber'}"></span>{tr("sample", lang)}: {sample_text(report, lang)}</div>
          <div class="qsx-light"><span class="qsx-dot {'green' if track_years >= 2 else 'amber'}"></span>{tr("track_record", lang)}: {track_years:.1f} {tr("years", lang)}</div>
          {cap}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="qsx-result-card">
          <div class="qsx-section-title">{ft("risk_diagnosis", lang)}</div>
          {risk_tags_markup(risk_tags(report, triage, meta, co, lang), lang)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="qsx-result-card">
          <div class="qsx-section-title">{ft("main_problems", lang)}</div>
          {problem_list_markup(co, lang)}
          <p class="qsx-muted" style="margin-top:14px;">{escape(local_encouragement(report, co, lang))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    route = next_step.get("route", "collect_evidence")
    st.markdown(
        f"""
        <div class="qsx-result-card">
          <div class="qsx-section-title">{escape(next_step.get("title") or tr("next_step", lang))}</div>
          <div class="qsx-muted">{escape(next_step.get("body") or "")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if route == "collect_evidence":
        st.info(next_step.get("body") or tr("next_step.collect_evidence_body", lang))
    elif route == "overlay":
        render_overlay_preview(r, lang, upload=up, meta=meta, intro=False,
                               button_label=(next_step.get("primary_action") or {}).get("label"))
        if (next_step.get("secondary_action") or {}).get("id") == "open_pro":
            st.link_button((next_step["secondary_action"]).get("label"),
                           "https://www.quantscopex.com/report?utm_source=free_score&utm_medium=result&utm_campaign=evidence_aware&utm_content=overlay_secondary",
                           use_container_width=True)
    else:
        st.link_button((next_step.get("primary_action") or {}).get("label", tr("next_step.pro", lang)),
                       "https://www.quantscopex.com/report?utm_source=free_score&utm_medium=result&utm_campaign=evidence_aware&utm_content=pro",
                       type="primary", use_container_width=True)
        if (next_step.get("secondary_action") or {}).get("id") == "open_overlay":
            render_overlay_preview(r, lang, upload=up, meta=meta, intro=False,
                                   button_label=(next_step["secondary_action"]).get("label"))

    with st.expander(tr("raw", lang)):
        raw = report.to_dict()
        raw["triage"] = triage
        raw["lang"] = lang
        st.json(raw)

    st.markdown(
        f"""
        <div style="margin-top:26px;max-width:820px;">
          <p class="qsx-small">{tr("disclaimer", lang)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
