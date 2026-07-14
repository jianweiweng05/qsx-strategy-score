(function() {
  'use strict';

  const COPY = {
    zh: {
      kicker: '推荐下一步',
      evidence: '本次依据',
      secondary: '查看完整 Pro 尽调',
      overlayTitle: '策略有 edge，但回撤风险会限制实盘',
      overlayBody: '先免费跑一次 QSX Crypto Universal Overlay Preview（虚拟币通用 Overlay），测试动态暴露控制能否在保留收益的同时降低回撤。',
      overlayButton: '免费测试虚拟币通用 Overlay',
      randomTitle: '策略还不能和随机择时清晰区分',
      randomBody: '先别急着优化参数。完整尽调会检查样本外稳定性、HCRI 主场和真实可交易性。',
      randomButton: '查看 Pro 尽调路径',
      tradeDependencyTitle: '高分成立，但收益集中和回测假设要核验',
      tradeDependencyBody: '这类闭合交易日志看不到持仓中的真实 MTM 回撤。下一步应核验少数大赢家、手续费/滑点、杠杆、小本金和成交容量。',
      tradeDependencyButton: '查看 Pro 尽调路径',
      dependencyTitle: '收益可能高度依赖持有资产',
      dependencyBody: '下一步应拆分 alpha 和 beta，确认策略贡献不是被牛市或单一资产暴露掩盖。',
      dependencyButton: '查看暴露度诊断',
      lowScoreTitle: '策略还需要先修基本问题',
      lowScoreBody: '先根据免费报告修复主要风险，再决定是否值得跑虚拟币通用 Overlay 或 Pro 深诊。',
      lowScoreButton: '查看改进方向',
      proTitle: '免费筛查通过，下一步是尽调深水区',
      proBody: '如果准备上实盘，继续检查成本/滑点、黑天鹅窗口、HCRI 主场和真实 MTM 回撤。',
      proButton: '查看完整报告',
    },
    en: {
      kicker: 'Recommended next step',
      evidence: 'Evidence from this run',
      secondary: 'View full Pro audit',
      overlayTitle: 'There is edge, but drawdown may block live deployment',
      overlayBody: 'Run the free QSX Crypto Universal Overlay Preview to test whether dynamic exposure control can reduce drawdown without killing the edge.',
      overlayButton: 'Run free Crypto Universal Overlay',
      randomTitle: 'This strategy is not clearly better than random timing',
      randomBody: 'Do not optimize parameters first. The full audit checks out-of-sample stability, HCRI home field, and tradability.',
      randomButton: 'View Pro audit path',
      tradeDependencyTitle: 'High score, but concentration and backtest assumptions need audit',
      tradeDependencyBody: 'This closed-trade log cannot show true mark-to-market drawdown inside each position. Next check large-winner concentration, fees/slippage, leverage, small capital, and venue capacity.',
      tradeDependencyButton: 'View Pro audit path',
      dependencyTitle: 'Returns may depend heavily on the underlying asset',
      dependencyBody: 'Next, separate alpha from beta so bull-market exposure is not mistaken for strategy skill.',
      dependencyButton: 'View exposure diagnosis',
      lowScoreTitle: 'Fix the basic issues before deeper testing',
      lowScoreBody: 'Use the free report to repair the main risks first, then decide whether the crypto universal Overlay or Pro is worth testing.',
      lowScoreButton: 'View improvement path',
      proTitle: 'Free screening passed; due diligence is the next layer',
      proBody: 'Before live deployment, check costs/slippage, crisis windows, HCRI home field, and true MTM drawdown.',
      proButton: 'View full report',
    },
    ja: {
      kicker: '推奨される次のステップ',
      evidence: '今回の根拠',
      secondary: 'Pro監査を見る',
      overlayTitle: 'エッジはありますが、ドローダウンが実運用の壁です',
      overlayBody: '無料のQSX Crypto Universal Overlay Previewで、暗号資産向けの動的エクスポージャー制御がリターンを残しつつドローダウンを下げられるか確認します。',
      overlayButton: '無料Crypto Universal Overlayを試す',
      randomTitle: 'ランダムなタイミングとの差が明確ではありません',
      randomBody: 'まずパラメータ調整に進まず、サンプル外安定性、HCRI適性、実運用性を確認してください。',
      randomButton: 'Pro監査パスを見る',
      tradeDependencyTitle: '高スコアですが、収益集中とバックテスト前提の監査が必要です',
      tradeDependencyBody: 'この閉じた取引ログでは、ポジション中の真のMTMドローダウンが見えません。大きな勝ちトレード、手数料/スリッページ、レバレッジ、小資金、約定容量を確認してください。',
      tradeDependencyButton: 'Pro監査パスを見る',
      dependencyTitle: '収益が原資産への依存に偏っている可能性があります',
      dependencyBody: '次にalphaとbetaを分解し、強気相場の露出を戦略スキルと誤認していないか確認します。',
      dependencyButton: 'エクスポージャー診断を見る',
      lowScoreTitle: '深い検査の前に基本問題を修正してください',
      lowScoreBody: '無料レポートで主要リスクを先に直し、その後Crypto Universal OverlayやProの価値を判断します。',
      lowScoreButton: '改善方向を見る',
      proTitle: '無料スクリーニング後はデューデリジェンスです',
      proBody: '実運用前にコスト/スリッページ、危機局面、HCRI適性、真のMTMドローダウンを確認します。',
      proButton: '完全レポートを見る',
    },
    ko: {
      kicker: '추천 다음 단계',
      evidence: '이번 진단 근거',
      secondary: 'Pro 실사 보기',
      overlayTitle: '엣지는 있지만 드로다운이 실전 운용을 막을 수 있습니다',
      overlayBody: '무료 QSX Crypto Universal Overlay Preview로 암호화폐 범용 동적 익스포저 제어가 수익을 유지하면서 드로다운을 낮출 수 있는지 테스트하세요.',
      overlayButton: '무료 Crypto Universal Overlay 실행',
      randomTitle: '랜덤 타이밍보다 낫다고 보기 어렵습니다',
      randomBody: '파라미터 최적화보다 먼저 OOS 안정성, HCRI 홈필드, 실제 거래 가능성을 확인해야 합니다.',
      randomButton: 'Pro 실사 경로 보기',
      tradeDependencyTitle: '점수는 높지만 수익 집중과 백테스트 가정을 감사해야 합니다',
      tradeDependencyBody: '닫힌 거래 로그만으로는 포지션 중 실제 MTM 드로다운을 볼 수 없습니다. 큰 승리 거래, 비용/슬리피지, 레버리지, 소액 자본, 체결 용량을 확인하세요.',
      tradeDependencyButton: 'Pro 실사 경로 보기',
      dependencyTitle: '수익이 기초자산 보유에 크게 의존할 수 있습니다',
      dependencyBody: '다음 단계는 alpha와 beta를 분리해 상승장 노출을 전략 실력으로 착각하지 않는지 확인하는 것입니다.',
      dependencyButton: '익스포저 진단 보기',
      lowScoreTitle: '심화 테스트 전에 기본 문제를 먼저 고치세요',
      lowScoreBody: '무료 리포트로 주요 리스크를 먼저 고친 뒤 Crypto Universal Overlay나 Pro 테스트 가치가 있는지 판단하세요.',
      lowScoreButton: '개선 방향 보기',
      proTitle: '무료 스크리닝 이후에는 실사가 필요합니다',
      proBody: '실전 투입 전 비용/슬리피지, 위기 구간, HCRI 홈필드, 실제 MTM 드로다운을 점검하세요.',
      proButton: '전체 리포트 보기',
    },
    es: {
      kicker: 'Siguiente paso recomendado',
      evidence: 'Evidencia de este análisis',
      secondary: 'Ver auditoría Pro',
      overlayTitle: 'Hay edge, pero el drawdown puede bloquear el despliegue real',
      overlayBody: 'Ejecuta QSX Crypto Universal Overlay Preview gratis para probar si el control dinámico de exposición en crypto puede bajar el drawdown sin matar el edge.',
      overlayButton: 'Ejecutar Crypto Universal Overlay gratis',
      randomTitle: 'La estrategia no supera claramente al timing aleatorio',
      randomBody: 'No optimices parámetros primero. La auditoría completa revisa estabilidad OOS, HCRI y tradabilidad.',
      randomButton: 'Ver camino Pro',
      tradeDependencyTitle: 'Score alto, pero hay que auditar concentración y supuestos',
      tradeDependencyBody: 'Este log de operaciones cerradas no muestra el drawdown MTM real dentro de cada posición. Revisa grandes ganadoras, costos/slippage, apalancamiento, capital pequeño y capacidad de ejecución.',
      tradeDependencyButton: 'Ver camino Pro',
      dependencyTitle: 'Los retornos pueden depender mucho del activo subyacente',
      dependencyBody: 'El siguiente paso es separar alpha y beta para no confundir exposición alcista con habilidad.',
      dependencyButton: 'Ver diagnóstico de exposición',
      lowScoreTitle: 'Corrige los problemas básicos antes de pruebas profundas',
      lowScoreBody: 'Usa el reporte gratuito para reparar los riesgos principales y luego decide si Crypto Universal Overlay o Pro valen la pena.',
      lowScoreButton: 'Ver ruta de mejora',
      proTitle: 'El screening gratuito pasó; sigue la due diligence',
      proBody: 'Antes de operar en vivo, revisa costos/slippage, crisis, HCRI y drawdown MTM real.',
      proButton: 'Ver reporte completo',
    },
    'pt-BR': {
      kicker: 'Próximo passo recomendado',
      evidence: 'Evidência desta análise',
      secondary: 'Ver auditoria Pro',
      overlayTitle: 'Há edge, mas o drawdown pode impedir operação real',
      overlayBody: 'Rode o QSX Crypto Universal Overlay Preview gratuito para testar se controle dinâmico de exposição em crypto reduz drawdown sem matar o edge.',
      overlayButton: 'Rodar Crypto Universal Overlay grátis',
      randomTitle: 'A estratégia não supera claramente timing aleatório',
      randomBody: 'Não otimize parâmetros primeiro. A auditoria completa verifica estabilidade OOS, HCRI e tradabilidade.',
      randomButton: 'Ver caminho Pro',
      tradeDependencyTitle: 'Score alto, mas concentração e premissas precisam de auditoria',
      tradeDependencyBody: 'Este log de trades fechados não mostra o drawdown MTM real dentro de cada posição. Revise grandes vencedoras, custos/slippage, alavancagem, capital pequeno e capacidade de execução.',
      tradeDependencyButton: 'Ver caminho Pro',
      dependencyTitle: 'Os retornos podem depender muito do ativo subjacente',
      dependencyBody: 'O próximo passo é separar alpha e beta para não confundir exposição de mercado com habilidade.',
      dependencyButton: 'Ver diagnóstico de exposição',
      lowScoreTitle: 'Corrija os problemas básicos antes de testes profundos',
      lowScoreBody: 'Use o relatório gratuito para reparar os principais riscos e depois decida se Crypto Universal Overlay ou Pro valem a pena.',
      lowScoreButton: 'Ver caminho de melhoria',
      proTitle: 'O screening gratuito passou; due diligence é a próxima camada',
      proBody: 'Antes do live, revise custos/slippage, crises, HCRI e drawdown MTM real.',
      proButton: 'Ver relatório completo',
    },
  };

  function normalizeLang(lang) {
    const value = String(lang || '').toLowerCase();
    if (value.startsWith('zh')) return 'zh';
    if (value.startsWith('ja')) return 'ja';
    if (value.startsWith('ko')) return 'ko';
    if (value.startsWith('es')) return 'es';
    if (value.startsWith('pt')) return 'pt-BR';
    return 'en';
  }

  function copy(lang) {
    return COPY[normalizeLang(lang)] || COPY.en;
  }

  function pct(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '-';
    return `${n.toFixed(Math.abs(n) >= 10 ? 0 : 1)}%`;
  }

  function fmtNum(value, digits = 1) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '-';
    return n.toFixed(digits);
  }

  function buildCampaignUrl(target, content, data, extra = {}) {
    const base = target === 'tools' ? 'https://www.quantscopex.com/tools' : 'https://www.quantscopex.com/report';
    const params = new URLSearchParams({
      utm_source: 'chrome_ext',
      utm_medium: 'smart_cta',
      utm_campaign: 'tv_extension',
      utm_content: content,
      score: Number.isFinite(Number(data.display)) ? Number(data.display).toFixed(1) : '',
      grade: data.grade || data.tier || data.judgement || '',
      asset: data.meta?.resolved_asset || data.meta?.requested_asset || '',
    });
    Object.entries(extra).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    [...params.entries()].forEach(([key, value]) => {
      if (value === '') params.delete(key);
    });
    return `${base}?${params.toString()}`;
  }

  function getSmartCTA(data, lang = 'zh') {
    const c = copy(lang);
    const diagnostics = data.diagnostics || {};
    const core = diagnostics.core_metrics || {};
    const mc = diagnostics.monte_carlo || {};
    const triage = data.triage || {};
    const dep = triage.dependency_lite || {};
    const score = Number(data.display);
    const edge = data.lights?.edge || '';
    const randomP = Number(data.meta?.random_p);
    const mdd = Math.abs(Number(core.max_drawdown_pct));
    const tailMdd = Math.abs(Number(mc.maxdd_worst5_pct));
    const dependencyLabel = String(dep.label || dep.label_local || '').toLowerCase();
    const dependencyReason = dep.reason || '';
    const isTradeDependency = dep.type === 'trade_dependency_scan';
    const highDependency = dependencyLabel.includes('high') ||
      dependencyLabel.includes('高') ||
      dependencyLabel.includes('높') ||
      dependencyLabel.includes('alto');
    const baseEvidence = [
      `Score ${fmtNum(score, 1)} / ${data.grade || data.tier || data.judgement || '-'}`,
      `Edge: ${edge || '-'}`,
    ];

    if (edge === 'random_fail' || (Number.isFinite(randomP) && randomP > 0.2)) {
      return {
        kind: 'pro',
        kicker: c.kicker,
        title: c.randomTitle,
        body: c.randomBody,
        button: c.randomButton,
        secondaryLabel: c.secondary,
        primaryUrl: buildCampaignUrl('report', 'random_fail', data, { p_value: Number.isFinite(randomP) ? randomP.toFixed(3) : '' }),
        secondaryUrl: buildCampaignUrl('report', 'pro_audit_secondary', data),
        evidenceLabel: c.evidence,
        evidence: [...baseEvidence, Number.isFinite(randomP) ? `random p=${randomP.toFixed(2)}` : 'random timing failed'],
      };
    }

    if (isTradeDependency && highDependency) {
      return {
        kind: 'pro',
        kicker: c.kicker,
        title: c.tradeDependencyTitle,
        body: c.tradeDependencyBody,
        button: c.tradeDependencyButton,
        secondaryLabel: c.secondary,
        primaryUrl: buildCampaignUrl('report', 'trade_dependency_audit', data, { issue: 'trade_dependency' }),
        secondaryUrl: buildCampaignUrl('report', 'trade_dependency_secondary', data),
        evidenceLabel: c.evidence,
        evidence: [...baseEvidence, dep.label_local || dep.label || 'High dependency', dependencyReason || 'Closed-trade concentration needs audit'],
      };
    }

    if (Number.isFinite(score) && score >= 75 && (mdd >= 40 || tailMdd >= 60)) {
      return {
        kind: 'overlay',
        kicker: c.kicker,
        title: c.overlayTitle,
        body: c.overlayBody,
        button: c.overlayButton,
        secondaryLabel: c.secondary,
        primaryUrl: buildCampaignUrl('tools', 'overlay_high_dd', data, { action: 'overlay', mdd: Number.isFinite(mdd) ? mdd.toFixed(1) : '' }),
        secondaryUrl: buildCampaignUrl('report', 'overlay_high_dd_secondary', data),
        evidenceLabel: c.evidence,
        evidence: [...baseEvidence, `MaxDD ${pct(-mdd)}`, tailMdd ? `MC worst 5% ${pct(-tailMdd)}` : 'Monte Carlo tail risk'],
      };
    }

    if (highDependency || (Number.isFinite(score) && score >= 60 && score < 82 && edge === 'marginal')) {
      return {
        kind: 'exposure',
        kicker: c.kicker,
        title: c.dependencyTitle,
        body: c.dependencyBody,
        button: c.dependencyButton,
        secondaryLabel: c.secondary,
        primaryUrl: buildCampaignUrl('report', 'dependency_exposure', data, { issue: 'dependency' }),
        secondaryUrl: buildCampaignUrl('report', 'dependency_secondary', data),
        evidenceLabel: c.evidence,
        evidence: [...baseEvidence, dep.label_local || dep.label || 'Dependency signal', dependencyReason || 'Benchmark dependency needs decomposition'],
      };
    }

    if (Number.isFinite(score) && score < 60) {
      return {
        kind: 'coaching',
        kicker: c.kicker,
        title: c.lowScoreTitle,
        body: c.lowScoreBody,
        button: c.lowScoreButton,
        secondaryLabel: c.secondary,
        primaryUrl: buildCampaignUrl('tools', 'coaching_low_score', data, { action: 'coaching' }),
        secondaryUrl: buildCampaignUrl('report', 'low_score_secondary', data),
        evidenceLabel: c.evidence,
        evidence: [...baseEvidence, `MaxDD ${pct(-mdd)}`, `CAGR ${pct(core.cagr_pct)}`],
      };
    }

    return {
      kind: 'pro',
      kicker: c.kicker,
      title: c.proTitle,
      body: c.proBody,
      button: c.proButton,
      secondaryLabel: c.overlayButton,
      primaryUrl: buildCampaignUrl('report', 'default_pro_audit', data),
      secondaryUrl: buildCampaignUrl('tools', 'overlay_default_secondary', data, { action: 'overlay' }),
      evidenceLabel: c.evidence,
      evidence: [...baseEvidence, `Sharpe ${fmtNum(core.sharpe, 2)}`, `Calmar ${fmtNum(core.calmar, 2)}`],
    };
  }

  window.QSXSmartCTA = {
    getSmartCTA,
  };
})();
