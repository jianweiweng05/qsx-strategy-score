const DEFAULT_API_BASE = 'https://www.quantscopex.com';
const LEGACY_LOCAL_API_PATTERN = /^https?:\/\/(?:127\.0\.0\.1|localhost):8001\/?$/i;
const LEGACY_API_BASE_PATTERN = /^https:\/\/api\.quantscopex\.com\/?$/i;
const UI_COPY = {
  zh: {
    apiLabel: 'API 地址',
    assetLabel: '对比资产',
    autoDetect: '自动检测',
    langLabel: '语言',
    strategyFileTitle: '选择策略文件',
    strategyFileHint: 'CSV / TSV / Excel，最大 5MB',
    benchmarkTitle: '可选：上传基准资产 K 线',
    benchmarkHint: 'date + close/price，用它对比持有和随机择时',
    scoreButton: '开始评分',
    uploadHelp: '支持收益序列、净值曲线、闭合交易记录，以及常见回测工具导出文件。',
    freeRadarLink: '免费虚拟币顶底风险雷达',
    loading: '正在分析策略...',
    anotherButton: '分析另一个策略',
    errorTitle: '分析失败',
    retryButton: '返回重试',
    errorHint: '确认 API 可访问，并上传收益曲线、净值曲线或交易记录 CSV / Excel。',
    fallbackCtaTitle: '继续做完整策略尽调',
    fallbackCtaBody: '免费评分已完成。下一步检查成本、滑点、黑天鹅窗口和真实 MTM 回撤。',
    fallbackCtaButton: '查看完整报告',
    noAsset: '未评估',
    customBenchmark: '自定义K线',
    bundledBenchmark: '内置基准',
    bars: 'bars',
    years: '年',
  },
  en: {
    apiLabel: 'API URL',
    assetLabel: 'Benchmark asset',
    autoDetect: 'Auto-detect',
    langLabel: 'Language',
    strategyFileTitle: 'Choose strategy file',
    strategyFileHint: 'CSV / TSV / Excel, max 5 MB',
    benchmarkTitle: 'Optional: upload benchmark price/K-line',
    benchmarkHint: 'date + close/price for hold and random-timing tests',
    scoreButton: 'Score strategy',
    uploadHelp: 'Supports return series, equity curves, closed-trade logs, and common backtest exports.',
    freeRadarLink: 'Free Crypto Top/Bottom Risk Radar',
    loading: 'Analyzing strategy...',
    anotherButton: 'Analyze another strategy',
    errorTitle: 'Analysis failed',
    retryButton: 'Try again',
    errorHint: 'Check that the API is reachable and the file is a return curve, equity curve, or trade log CSV / Excel.',
    fallbackCtaTitle: 'Continue with a full strategy audit',
    fallbackCtaBody: 'The free score is complete. Next check costs, slippage, crisis windows, and true MTM drawdown.',
    fallbackCtaButton: 'View full report',
    noAsset: 'not evaluated',
    customBenchmark: 'custom K-line',
    bundledBenchmark: 'bundled benchmark',
    bars: 'bars',
    years: 'years',
  },
  ja: {
    apiLabel: 'API URL',
    assetLabel: '比較資産',
    autoDetect: '自動検出',
    langLabel: '言語',
    strategyFileTitle: '戦略ファイルを選択',
    strategyFileHint: 'CSV / TSV / Excel、最大5 MB',
    benchmarkTitle: '任意：基準価格/Kラインをアップロード',
    benchmarkHint: 'date + close/priceで保有・ランダム検査',
    scoreButton: 'スコア計算',
    uploadHelp: 'リターン系列、エクイティ曲線、クローズ済み取引ログ、一般的なバックテスト出力に対応します。',
    freeRadarLink: '無料Cryptoトップ/ボトム・リスクレーダー',
    loading: '戦略を分析中...',
    anotherButton: '別の戦略を分析',
    errorTitle: '分析に失敗しました',
    retryButton: '再試行',
    errorHint: 'API接続と、リターン曲線・エクイティ曲線・取引ログのCSV / Excelか確認してください。',
    fallbackCtaTitle: '完全な戦略監査へ進む',
    fallbackCtaBody: '無料スコアは完了しました。次にコスト、スリッページ、危機局面、真のMTMドローダウンを確認します。',
    fallbackCtaButton: '完全レポートを見る',
    noAsset: '未評価',
    customBenchmark: 'カスタムKライン',
    bundledBenchmark: '内蔵ベンチマーク',
    bars: 'bars',
    years: '年',
  },
  ko: {
    apiLabel: 'API 주소',
    assetLabel: '비교 자산',
    autoDetect: '자동 감지',
    langLabel: '언어',
    strategyFileTitle: '전략 파일 선택',
    strategyFileHint: 'CSV / TSV / Excel, 최대 5 MB',
    benchmarkTitle: '선택: 기준 가격/K-line 업로드',
    benchmarkHint: 'date + close/price로 보유/랜덤 타이밍 검사',
    scoreButton: '전략 점수 계산',
    uploadHelp: '수익률 시계열, 에쿼티 커브, 종료된 거래 로그, 일반 백테스트 내보내기를 지원합니다.',
    freeRadarLink: '무료 Crypto 고점/저점 리스크 레이더',
    loading: '전략 분석 중...',
    anotherButton: '다른 전략 분석',
    errorTitle: '분석 실패',
    retryButton: '다시 시도',
    errorHint: 'API 연결과 수익률/에쿼티/거래 로그 CSV 또는 Excel 파일인지 확인하세요.',
    fallbackCtaTitle: '전체 전략 실사로 계속',
    fallbackCtaBody: '무료 점수는 완료되었습니다. 다음으로 비용, 슬리피지, 위기 구간, 실제 MTM 드로다운을 확인하세요.',
    fallbackCtaButton: '전체 보고서 보기',
    noAsset: '미평가',
    customBenchmark: '사용자 K-line',
    bundledBenchmark: '내장 기준',
    bars: 'bars',
    years: '년',
  },
  es: {
    apiLabel: 'URL de API',
    assetLabel: 'Activo de referencia',
    autoDetect: 'Auto-detectar',
    langLabel: 'Idioma',
    strategyFileTitle: 'Elegir archivo de estrategia',
    strategyFileHint: 'CSV / TSV / Excel, máx. 5 MB',
    benchmarkTitle: 'Opcional: subir precio/K-line de referencia',
    benchmarkHint: 'date + close/price para hold y timing aleatorio',
    scoreButton: 'Puntuar estrategia',
    uploadHelp: 'Soporta series de retornos, curvas de equity, logs de trades cerrados y exports comunes de backtest.',
    freeRadarLink: 'Radar crypto gratis de techos/suelos',
    loading: 'Analizando estrategia...',
    anotherButton: 'Analizar otra estrategia',
    errorTitle: 'Análisis fallido',
    retryButton: 'Reintentar',
    errorHint: 'Verifica que la API responda y que el archivo sea una curva de retornos/equity o un trade log CSV / Excel.',
    fallbackCtaTitle: 'Continuar con auditoría completa',
    fallbackCtaBody: 'El score gratuito está listo. Luego revisa costos, slippage, crisis y drawdown MTM real.',
    fallbackCtaButton: 'Ver informe completo',
    noAsset: 'no evaluado',
    customBenchmark: 'K-line personalizada',
    bundledBenchmark: 'benchmark incluido',
    bars: 'bars',
    years: 'años',
  },
  'pt-BR': {
    apiLabel: 'URL da API',
    assetLabel: 'Ativo de referência',
    autoDetect: 'Auto-detectar',
    langLabel: 'Idioma',
    strategyFileTitle: 'Escolher arquivo da estratégia',
    strategyFileHint: 'CSV / TSV / Excel, máx. 5 MB',
    benchmarkTitle: 'Opcional: enviar preço/K-line de referência',
    benchmarkHint: 'date + close/price para hold e timing aleatório',
    scoreButton: 'Pontuar estratégia',
    uploadHelp: 'Suporta séries de retorno, curvas de equity, logs de trades fechados e exports comuns de backtest.',
    freeRadarLink: 'Radar crypto grátis de topos/fundos',
    loading: 'Analisando estratégia...',
    anotherButton: 'Analisar outra estratégia',
    errorTitle: 'Análise falhou',
    retryButton: 'Tentar novamente',
    errorHint: 'Verifique se a API responde e se o arquivo é uma curva de retorno/equity ou trade log CSV / Excel.',
    fallbackCtaTitle: 'Continuar com auditoria completa',
    fallbackCtaBody: 'O score gratuito está pronto. Depois revise custos, slippage, crises e drawdown MTM real.',
    fallbackCtaButton: 'Ver relatório completo',
    noAsset: 'não avaliado',
    customBenchmark: 'K-line personalizada',
    bundledBenchmark: 'benchmark incluído',
    bars: 'bars',
    years: 'anos',
  },
};
const DIAGNOSTIC_COPY = {
  zh: {
    open: '查看完整诊断详情',
    close: '收起诊断详情',
    metrics: '核心指标',
    scorecard: '分享评分卡',
    equity: '净值 / 持有对比',
    drawdown: '回撤曲线',
    monteCarlo: '蒙特卡洛压力测试',
    benchmark: '买入持有对比',
    riskEvidence: '风险与证据',
    issues: '主要问题 / 下一步',
    noDetails: '本次返回的是简版评分，没有可展开的诊断数据。',
    noData: '暂无可显示数据',
    noIssues: '免费评分卡没有发现明确硬伤。下一步应检查成本、滑点、黑天鹅窗口和真实 MTM 回撤。',
    sims: '次模拟',
    profit: '盈利概率',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: '策略',
    buyHold: '买入持有',
    calmarAlpha: '策略 - 持有',
    ddReduction: '回撤改善',
    retCapture: '收益捕获',
    overlap: '重叠区间',
    edgePersistence: 'Edge 持续性',
    evidence: '证据质量',
    dependency: '资产依赖',
    low: '低',
    medium: '中',
    high: '高',
  },
  en: {
    open: 'View full diagnostic details',
    close: 'Collapse diagnostic details',
    metrics: 'Core metrics',
    scorecard: 'Shareable scorecard',
    equity: 'Equity / Hold comparison',
    drawdown: 'Drawdown curve',
    monteCarlo: 'Monte Carlo stress test',
    benchmark: 'Buy & Hold comparison',
    riskEvidence: 'Risk and evidence',
    issues: 'Main issues / next step',
    noDetails: 'This run returned the compact score only.',
    noData: 'No data available',
    noIssues: 'No clear hard failure in the free scorecard. Next check costs, slippage, crisis windows, and true MTM drawdown.',
    sims: 'simulations',
    profit: 'profit probability',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: 'Strategy',
    buyHold: 'Buy & Hold',
    calmarAlpha: 'strategy - hold',
    ddReduction: 'drawdown improvement',
    retCapture: 'return capture',
    overlap: 'overlap',
    edgePersistence: 'Edge persistence',
    evidence: 'Evidence quality',
    dependency: 'Asset dependency',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
  },
  ja: {
    open: '診断詳細を表示',
    close: '診断詳細を閉じる',
    metrics: '主要指標',
    scorecard: '共有スコアカード',
    equity: 'エクイティ / 保有比較',
    drawdown: 'ドローダウン',
    monteCarlo: 'モンテカルロ・ストレス',
    benchmark: 'Buy & Hold 比較',
    riskEvidence: 'リスクと証拠',
    issues: '主な問題 / 次の確認',
    noDetails: 'この結果には簡易スコアのみ含まれます。',
    noData: '表示データなし',
    noIssues: '明確な重大問題はありません。次にコスト、スリッページ、危機局面、真のMTMドローダウンを確認してください。',
    sims: '回シミュレーション',
    profit: '利益確率',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: '戦略',
    buyHold: 'Buy & Hold',
    calmarAlpha: '戦略 - 保有',
    ddReduction: 'DD改善',
    retCapture: 'リターン捕捉',
    overlap: '重複区間',
    edgePersistence: 'Edge持続性',
    evidence: '証拠品質',
    dependency: '資産依存',
    low: '低',
    medium: '中',
    high: '高',
  },
  ko: {
    open: '전체 진단 상세 보기',
    close: '진단 상세 접기',
    metrics: '핵심 지표',
    scorecard: '공유 스코어카드',
    equity: '에쿼티 / 보유 비교',
    drawdown: '드로다운',
    monteCarlo: '몬테카를로 스트레스',
    benchmark: 'Buy & Hold 비교',
    riskEvidence: '리스크와 증거',
    issues: '주요 문제 / 다음 단계',
    noDetails: '이번 결과에는 간단 점수만 포함됩니다.',
    noData: '표시할 데이터 없음',
    noIssues: '명확한 치명적 문제는 없습니다. 다음으로 비용, 슬리피지, 위기 구간, 실제 MTM 드로다운을 확인하세요.',
    sims: '회 시뮬레이션',
    profit: '수익 확률',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: '전략',
    buyHold: 'Buy & Hold',
    calmarAlpha: '전략 - 보유',
    ddReduction: '드로다운 개선',
    retCapture: '수익 포착',
    overlap: '겹친 구간',
    edgePersistence: 'Edge 지속성',
    evidence: '증거 품질',
    dependency: '자산 의존',
    low: '낮음',
    medium: '중간',
    high: '높음',
  },
  es: {
    open: 'Ver diagnóstico completo',
    close: 'Cerrar diagnóstico',
    metrics: 'Métricas clave',
    scorecard: 'Scorecard compartible',
    equity: 'Capital / comparación hold',
    drawdown: 'Drawdown',
    monteCarlo: 'Estrés Monte Carlo',
    benchmark: 'Comparación Buy & Hold',
    riskEvidence: 'Riesgo y evidencia',
    issues: 'Problemas / siguiente paso',
    noDetails: 'Este análisis devolvió solo el score compacto.',
    noData: 'Sin datos disponibles',
    noIssues: 'No hay fallo claro en el scorecard gratuito. Luego revisa costos, slippage, crisis y drawdown MTM real.',
    sims: 'simulaciones',
    profit: 'prob. de ganancia',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: 'Estrategia',
    buyHold: 'Buy & Hold',
    calmarAlpha: 'estrategia - hold',
    ddReduction: 'mejora drawdown',
    retCapture: 'captura retorno',
    overlap: 'solape',
    edgePersistence: 'Persistencia edge',
    evidence: 'Calidad evidencia',
    dependency: 'Dependencia activo',
    low: 'Bajo',
    medium: 'Medio',
    high: 'Alto',
  },
  'pt-BR': {
    open: 'Ver diagnóstico completo',
    close: 'Fechar diagnóstico',
    metrics: 'Métricas principais',
    scorecard: 'Scorecard compartilhável',
    equity: 'Capital / comparação hold',
    drawdown: 'Drawdown',
    monteCarlo: 'Estresse Monte Carlo',
    benchmark: 'Comparação Buy & Hold',
    riskEvidence: 'Risco e evidência',
    issues: 'Problemas / próximo passo',
    noDetails: 'Esta análise retornou apenas o score compacto.',
    noData: 'Sem dados disponíveis',
    noIssues: 'Não há falha clara no scorecard gratuito. Depois revise custos, slippage, crises e drawdown MTM real.',
    sims: 'simulações',
    profit: 'prob. de lucro',
    cagrBand: 'CAGR 5-95%',
    worst5: 'worst 5% MaxDD',
    strategy: 'Estratégia',
    buyHold: 'Buy & Hold',
    calmarAlpha: 'estratégia - hold',
    ddReduction: 'melhora drawdown',
    retCapture: 'captura retorno',
    overlap: 'sobreposição',
    edgePersistence: 'Persistência edge',
    evidence: 'Qualidade evidência',
    dependency: 'Dependência ativo',
    low: 'Baixo',
    medium: 'Médio',
    high: 'Alto',
  },
};

const ARTIFACT_COPY = {
  zh: {
    title: '保存并分享这次结果',
    subtitle: '分享成绩卡，或保存三页免费诊断报告。',
    share: '分享成绩卡',
    preparing: '生成中...',
    png: '下载 PNG',
    pdf: '三页 PDF',
    email: '发送 PNG + PDF',
    consent: '同时接收少量 QuantScopeX 产品更新。可选，可随时退订。',
    sent: '已发送，请查收邮箱。',
    failed: '操作失败，请稍后重试。',
  },
  en: {
    title: 'Keep and share this result',
    subtitle: 'Share the scorecard, or keep the three-page free diagnostic.',
    share: 'Share scorecard',
    preparing: 'Preparing...',
    png: 'PNG',
    pdf: '3-page PDF',
    email: 'Email PNG + PDF',
    consent: 'Also send occasional QuantScopeX product updates. Optional; unsubscribe anytime.',
    sent: 'Sent. Check your inbox.',
    failed: 'That did not work. Please try again.',
  },
};

const state = {
  file: null,
  benchmarkFile: null,
  result: null,
  artifactBusy: false,
};

const views = {
  upload: document.getElementById('upload-view'),
  loading: document.getElementById('loading-view'),
  result: document.getElementById('result-view'),
  error: document.getElementById('error-view'),
};

const apiBaseInput = document.getElementById('api-base');
const assetInput = document.getElementById('asset');
const langInput = document.getElementById('lang');
const fileInput = document.getElementById('file-input');
const benchmarkInput = document.getElementById('benchmark-input');
const fileName = document.getElementById('file-name');
const benchmarkName = document.getElementById('benchmark-name');
const dropZone = document.getElementById('drop-zone');
const benchmarkZone = document.getElementById('benchmark-zone');
const scoreBtn = document.getElementById('score-btn');
const artifactTitle = document.getElementById('artifact-title');
const artifactSubtitle = document.getElementById('artifact-subtitle');
const shareCardBtn = document.getElementById('share-card-btn');
const downloadCardBtn = document.getElementById('download-card-btn');
const downloadPdfBtn = document.getElementById('download-pdf-btn');
const artifactEmail = document.getElementById('artifact-email');
const artifactMarketing = document.getElementById('artifact-marketing');
const emailArtifactsBtn = document.getElementById('email-artifacts-btn');
const artifactConsentCopy = document.getElementById('artifact-consent-copy');
const artifactStatus = document.getElementById('artifact-status');

function applyManifestVersion() {
  const versionEl = document.getElementById('app-version');
  if (!versionEl) return;
  const version = globalThis.chrome?.runtime?.getManifest?.().version;
  if (version) versionEl.textContent = `v${version}`;
}

function showView(name) {
  Object.entries(views).forEach(([key, el]) => {
    el.classList.toggle('active', key === name);
  });
}

function cleanApiBase(value) {
  return String(value || DEFAULT_API_BASE).trim().replace(/\/+$/, '');
}

function uiCopy(lang = langInput?.value) {
  return UI_COPY[lang] || UI_COPY.en;
}

function artifactCopy(lang = langInput?.value) {
  return ARTIFACT_COPY[lang === 'zh' ? 'zh' : 'en'];
}

function localizedPillarName(name, data, lang = langInput.value) {
  const labels = data?.pillar_labels?.[name];
  if (labels?.[lang]) return labels[lang];
  const fallback = {
    'Return quality': {
      zh: '收益质量',
      en: 'Return quality',
      ja: '収益品質',
      ko: '수익 품질',
      es: 'Calidad del retorno',
      'pt-BR': 'Qualidade do retorno',
    },
    Credibility: {
      zh: '过拟合识别',
      en: 'Overfit-risk detection',
      ja: '過剰最適化リスク検出',
      ko: '과최적화 위험 감지',
      es: 'Detección de sobreajuste',
      'pt-BR': 'Detecção de overfit',
    },
    'Overfit risk': {
      zh: '过拟合风险',
      en: 'Overfit risk',
      ja: '過剰最適化リスク',
      ko: '과최적화 위험',
      es: 'Riesgo de sobreajuste',
      'pt-BR': 'Risco de overfit',
    },
    'Drawdown risk': {
      zh: '回撤控制',
      en: 'Drawdown control',
      ja: 'ドローダウン管理',
      ko: '드로다운 제어',
      es: 'Control de drawdown',
      'pt-BR': 'Controle de drawdown',
    },
    'Edge vs hold/random': {
      zh: '相对持有/随机择时',
      en: 'Edge vs hold/random',
      ja: '保有/ランダム比の優位性',
      ko: '보유/랜덤 대비 우위',
      es: 'Edge vs hold/random',
      'pt-BR': 'Edge vs hold/random',
    },
  };
  return fallback[name]?.[lang] || name;
}

function applyLanguage() {
  const copy = uiCopy();
  document.documentElement.lang = langInput.value === 'zh' ? 'zh-CN' : langInput.value;
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.dataset.i18n;
    if (copy[key]) el.textContent = copy[key];
  });
  const autoOption = assetInput.querySelector('option[value=""]');
  if (autoOption) autoOption.textContent = copy.autoDetect;
  if (!state.file) fileName.textContent = copy.strategyFileHint;
  if (!state.benchmarkFile) benchmarkName.textContent = copy.benchmarkHint;
  const artifact = artifactCopy();
  artifactTitle.textContent = artifact.title;
  artifactSubtitle.textContent = artifact.subtitle;
  shareCardBtn.textContent = artifact.share;
  downloadCardBtn.textContent = artifact.png;
  downloadPdfBtn.textContent = artifact.pdf;
  emailArtifactsBtn.textContent = artifact.email;
  artifactConsentCopy.textContent = artifact.consent;
}

function normalizeSavedApiBase(value) {
  const apiBase = cleanApiBase(value);
  return LEGACY_LOCAL_API_PATTERN.test(apiBase) || LEGACY_API_BASE_PATTERN.test(apiBase) ? DEFAULT_API_BASE : apiBase;
}

async function loadSettings() {
  if (!globalThis.chrome?.storage) return;
  const saved = await chrome.storage.local.get(['apiBase', 'lang']);
  const apiBase = normalizeSavedApiBase(saved.apiBase);
  apiBaseInput.value = apiBase;
  if (saved.apiBase && apiBase !== cleanApiBase(saved.apiBase)) {
    await chrome.storage.local.set({ apiBase });
  }
  if (saved.lang) langInput.value = saved.lang;
}

async function loadAssets() {
  const fallback = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'SPY', 'QQQ', 'AAPL', 'TSLA'];
  try {
    const response = await fetch(`${cleanApiBase(apiBaseInput.value)}/api/score/assets`);
    const payload = await response.json();
    const keys = Array.isArray(payload.assets)
      ? payload.assets.map((item) => item.key).filter(Boolean)
      : [];
    populateAssets(keys.length ? keys : fallback);
  } catch (error) {
    populateAssets(fallback);
  }
}

function populateAssets(keys) {
  const current = assetInput.value;
  assetInput.innerHTML = `<option value="">${escapeHtml(uiCopy().autoDetect)}</option>`;
  keys.forEach((key) => {
    const option = document.createElement('option');
    option.value = key;
    option.textContent = key;
    assetInput.appendChild(option);
  });
  if ([...assetInput.options].some((option) => option.value === current)) {
    assetInput.value = current;
  }
}

function saveSettings() {
  if (!globalThis.chrome?.storage) return;
  chrome.storage.local.set({
    apiBase: cleanApiBase(apiBaseInput.value),
    lang: langInput.value,
  });
}

function selectFile(file) {
  state.file = file || null;
  fileName.textContent = file ? file.name : uiCopy().strategyFileHint;
  scoreBtn.disabled = !file;
}

function selectBenchmarkFile(file) {
  state.benchmarkFile = file || null;
  benchmarkName.textContent = file ? file.name : uiCopy().benchmarkHint;
}

async function scoreFile() {
  if (!state.file) return;
  saveSettings();
  showView('loading');

  const formData = new FormData();
  formData.append('file', state.file);
  if (assetInput.value) formData.append('asset_key', assetInput.value);
  if (state.benchmarkFile) {
    formData.append('benchmark_file', state.benchmarkFile);
  }

  try {
    const response = await fetch(`${cleanApiBase(apiBaseInput.value)}/api/score`, {
      method: 'POST',
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || payload.hint || payload.error || `HTTP ${response.status}`);
    }
    state.result = normalizeScorePayload(payload, langInput.value);
    renderResult(state.result);
    showView('result');
  } catch (error) {
    document.getElementById('error-message').textContent = error.message || 'Unknown error';
    document.getElementById('error-hint').textContent = uiCopy().errorHint;
    showView('error');
  }
}

function artifactFormData() {
  if (!state.file) throw new Error('No strategy file selected.');
  const formData = new FormData();
  formData.append('file', state.file);
  formData.append('lang', langInput.value === 'zh' ? 'zh' : 'en');
  formData.append('input_type', 'auto');
  if (assetInput.value) formData.append('asset_key', assetInput.value);
  if (state.benchmarkFile) formData.append('benchmark_file', state.benchmarkFile);
  return formData;
}

function setArtifactBusy(busy, label = '') {
  state.artifactBusy = busy;
  [shareCardBtn, downloadCardBtn, downloadPdfBtn, emailArtifactsBtn].forEach((button) => {
    button.disabled = busy;
  });
  if (busy && label) artifactStatus.textContent = label;
}

function setArtifactStatus(message, error = false) {
  artifactStatus.textContent = message;
  artifactStatus.classList.toggle('error', error);
}

async function fetchArtifact(kind) {
  const response = await fetch(`${cleanApiBase(apiBaseInput.value)}/api/score/${kind}`, {
    method: 'POST',
    body: artifactFormData(),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return response.blob();
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function downloadArtifact(kind) {
  if (state.artifactBusy) return;
  const copy = artifactCopy();
  setArtifactBusy(true, copy.preparing);
  setArtifactStatus(copy.preparing);
  try {
    const blob = await fetchArtifact(kind);
    downloadBlob(blob, kind === 'pdf' ? 'qsx-free-strategy-diagnostic.pdf' : 'qsx-strategy-scorecard.png');
    setArtifactStatus('');
  } catch (error) {
    setArtifactStatus(error.message || copy.failed, true);
  } finally {
    setArtifactBusy(false);
  }
}

async function shareScorecard() {
  if (state.artifactBusy) return;
  const copy = artifactCopy();
  setArtifactBusy(true, copy.preparing);
  setArtifactStatus(copy.preparing);
  try {
    const blob = await fetchArtifact('card');
    const card = new File([blob], 'qsx-strategy-scorecard.png', { type: 'image/png' });
    const score = state.result?.display ?? state.result?.overall ?? '-';
    const shareData = {
      title: 'QuantScopeX Strategy Score',
      text: langInput.value === 'zh' ? `我的策略评分：${score}/100` : `My strategy score: ${score}/100`,
      files: [card],
    };
    if (navigator.share && (!navigator.canShare || navigator.canShare(shareData))) {
      await navigator.share(shareData);
    } else {
      downloadBlob(blob, card.name);
    }
    setArtifactStatus('');
  } catch (error) {
    if (!(error instanceof DOMException && error.name === 'AbortError')) {
      setArtifactStatus(error.message || copy.failed, true);
    }
  } finally {
    setArtifactBusy(false);
  }
}

function sharePlatform(platform) {
  const score = state.result?.display ?? state.result?.overall ?? '-';
  const scoreUrl = `https://www.quantscopex.com/${langInput.value === 'zh' ? 'zh/' : ''}score`;
  const title = langInput.value === 'zh'
    ? `我的 QuantScopeX 策略评分是 ${score}/100`
    : `My QuantScopeX strategy score is ${score}/100`;
  const urls = {
    x: `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(scoreUrl)}`,
    linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(scoreUrl)}`,
    reddit: `https://www.reddit.com/submit?url=${encodeURIComponent(scoreUrl)}&title=${encodeURIComponent(title)}`,
  };
  window.open(urls[platform], '_blank', 'noopener,noreferrer');
}

async function emailArtifacts() {
  if (state.artifactBusy || !artifactEmail.validity.valid || !artifactEmail.value.trim()) {
    artifactEmail.reportValidity();
    return;
  }
  const copy = artifactCopy();
  setArtifactBusy(true, copy.preparing);
  setArtifactStatus(copy.preparing);
  try {
    const formData = artifactFormData();
    formData.append('email', artifactEmail.value.trim().toLowerCase());
    formData.append('marketing_opt_in', artifactMarketing.checked ? 'true' : 'false');
    const response = await fetch(`${cleanApiBase(apiBaseInput.value)}/api/score/email`, {
      method: 'POST',
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) throw new Error(payload.detail || copy.failed);
    setArtifactStatus(copy.sent);
  } catch (error) {
    setArtifactStatus(error.message || copy.failed, true);
  } finally {
    setArtifactBusy(false);
  }
}

function normalizeScorePayload(payload, lang) {
  // Consume the same public score contract as the website; never rescore in JS.
  if (!payload?.report) return payload;
  const report = payload.report;
  const pillars = { ...(report.pillars || {}) };
  delete pillars.Credibility;
  pillars['Overfit risk'] = { value: report.overfit_risk, raw: {} };
  return {
    ...report,
    pillars,
    triage: payload.triage,
    headline_local: lang === 'zh' ? (report.meta?.headline_zh || report.headline) : report.headline,
    meta: { ...(report.meta || {}), resolved_asset: payload.resolved_asset || null },
  };
}

function renderResult(data) {
  const display = Number(data.display ?? data.overall ?? 0);
  document.getElementById('score-number').textContent = Number.isFinite(display) ? display.toFixed(1) : '--';
  document.getElementById('score-grade').textContent = data.grade || data.tier || data.judgement || '--';
  document.getElementById('score-headline').textContent = data.headline_local || data.headline || '';

  const pillars = Object.entries(data.pillars || {});
  document.getElementById('pillar-list').innerHTML = pillars.map(([name, pillar]) => {
    const value = Math.max(0, Math.min(100, Number(pillar.value || 0)));
    const label = localizedPillarName(name, data);
    return `
      <div class="pillar">
        <div class="pillar-name" title="${escapeHtml(label)}">${escapeHtml(label)}</div>
        <div class="pillar-track"><div class="pillar-fill" style="width:${value}%"></div></div>
        <div class="pillar-value">${Math.round(value)}</div>
      </div>
    `;
  }).join('');

  const meta = data.meta || {};
  const copy = uiCopy();
  const asset = meta.resolved_asset || copy.noAsset;
  const source = meta.benchmark_source === 'custom_file' ? copy.customBenchmark : meta.benchmark_source === 'bundled_asset' ? copy.bundledBenchmark : '';
  const bars = meta.n ? `${meta.n} ${copy.bars}` : '';
  const years = meta.span_years ? `${Number(meta.span_years).toFixed(2)} ${copy.years}` : '';
  const edge = data.lights?.edge ? `edge: ${data.lights.edge}` : '';
  document.getElementById('meta-line').textContent = [asset, source, bars, years, edge].filter(Boolean).join(' · ');

  const flags = Array.isArray(data.flags) ? data.flags : [];
  document.getElementById('flag-list').innerHTML = flags.map((flag) => {
    const severity = flag.severity || 'warn';
    const msg = flag.msg_local || flag.msg || flag.code || JSON.stringify(flag);
    return `<div class="flag ${escapeHtml(severity)}">${escapeHtml(msg)}</div>`;
  }).join('');

  const detailRoot = document.getElementById('detail-root');
  if (detailRoot) {
    detailRoot.innerHTML = renderDiagnosticDetails(data, langInput.value);
  }

  const smartRoot = document.getElementById('smart-cta-root');
  if (smartRoot) {
    smartRoot.innerHTML = renderSmartCTA(data, langInput.value);
  }
}

function renderSmartCTA(data, lang) {
  if (!window.QSXSmartCTA) {
    const copy = uiCopy(lang);
    return `
      <section class="smart-cta compact pro">
        <div class="smart-cta-main">
          <div class="smart-cta-kicker">${escapeHtml(copy.fallbackCtaButton)}</div>
          <h3>${escapeHtml(copy.fallbackCtaTitle)}</h3>
          <p>${escapeHtml(copy.fallbackCtaBody)}</p>
          <div class="smart-cta-actions">
            <a class="smart-cta-primary" href="https://www.quantscopex.com/report?utm_source=chrome_ext&utm_medium=fallback_cta&utm_campaign=tv_extension" target="_blank" rel="noopener noreferrer">
              ${escapeHtml(copy.fallbackCtaButton)}
            </a>
          </div>
        </div>
      </section>
    `;
  }
  const cta = window.QSXSmartCTA.getSmartCTA(data, lang);
  return `
    <section class="smart-cta compact ${escapeHtml(cta.kind)}">
      <div class="smart-cta-main">
        <div class="smart-cta-kicker">${escapeHtml(cta.kicker)}</div>
        <h3>${escapeHtml(cta.title)}</h3>
        <p>${escapeHtml(cta.body)}</p>
        <div class="smart-cta-actions">
          <a class="smart-cta-primary" href="${escapeHtml(cta.primaryUrl)}" target="_blank" rel="noopener noreferrer">
            ${escapeHtml(cta.button)}
          </a>
          <a class="smart-cta-secondary" href="${escapeHtml(cta.secondaryUrl)}" target="_blank" rel="noopener noreferrer">
            ${escapeHtml(cta.secondaryLabel)}
          </a>
        </div>
      </div>
      <div class="smart-cta-proof">
        <span>${escapeHtml(cta.evidenceLabel)}</span>
        ${cta.evidence.slice(0, 3).map(item => `<strong>${escapeHtml(item)}</strong>`).join('')}
      </div>
    </section>
  `;
}

function renderDiagnosticDetails(data, lang) {
  const copy = detailCopy(lang);
  const diagnostics = data.diagnostics || {};
  const hasDiagnosticData = Boolean(
    diagnostics.core_metrics ||
    diagnostics.benchmark ||
    diagnostics.monte_carlo ||
    diagnostics.charts ||
    data.scorecard_png_base64 ||
    data.triage
  );
  const content = hasDiagnosticData ? renderDiagnosticBody(data, copy) : `<p class="detail-muted">${escapeHtml(copy.noDetails)}</p>`;
  return `
    <details class="diagnostic-details">
      <summary>
        <span>${escapeHtml(copy.open)}</span>
        <strong>${escapeHtml(copy.close)}</strong>
      </summary>
      <div class="diagnostic-body">${content}</div>
    </details>
  `;
}

function renderDiagnosticBody(data, copy) {
  const diagnostics = data.diagnostics || {};
  const core = diagnostics.core_metrics || {};
  const benchmark = diagnostics.benchmark;
  const mc = diagnostics.monte_carlo;
  const triage = data.triage || {};
  const charts = diagnostics.charts || {};

  return `
    ${data.scorecard_png_base64 ? `
      <section class="detail-panel">
        <h3>${escapeHtml(copy.scorecard)}</h3>
        <img class="detail-scorecard" src="data:image/png;base64,${data.scorecard_png_base64}" alt="QSX scorecard">
      </section>
    ` : ''}

    <section class="detail-panel">
      <h3>${escapeHtml(copy.metrics)}</h3>
      <div class="detail-metric-grid">
        ${detailMetric('CAGR', fmtPct(core.cagr_pct))}
        ${detailMetric('Sharpe', fmtNum(core.sharpe, 2))}
        ${detailMetric('Sortino', fmtNum(core.sortino, 2))}
        ${detailMetric('Calmar', fmtNum(core.calmar, 2))}
        ${detailMetric('MaxDD', fmtPct(core.max_drawdown_pct))}
        ${detailMetric('CVaR 5%', fmtPct(core.cvar5_pct))}
      </div>
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(charts.equity?.title || copy.equity)}</h3>
      ${renderLineChart(charts.equity, copy)}
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(charts.drawdown?.title || copy.drawdown)}</h3>
      ${renderLineChart(charts.drawdown, copy, { percentAxis: true })}
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(copy.monteCarlo)}</h3>
      ${mc ? `
        <div class="detail-note">
          <strong>${escapeHtml(String(mc.n_sims))} ${escapeHtml(copy.sims)}</strong>
          <span>${escapeHtml(copy.profit)} ${fmtPct(mc.prob_profit_pct)} · ${escapeHtml(copy.cagrBand)} ${fmtPct(mc.cagr_p5_pct)} / ${fmtPct(mc.cagr_p95_pct)} · ${escapeHtml(copy.worst5)} ${fmtPct(mc.maxdd_worst5_pct)}</span>
        </div>
        ${renderBandChart(charts.monte_carlo, copy)}
      ` : `<p class="detail-muted">${escapeHtml(copy.noData)}</p>`}
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(copy.benchmark)}</h3>
      ${benchmark ? renderBenchmark(benchmark, copy) : `<p class="detail-muted">${escapeHtml(copy.noData)}</p>`}
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(copy.riskEvidence)}</h3>
      ${renderRiskEvidence(diagnostics.risk_tags || [], triage, copy)}
    </section>

    <section class="detail-panel">
      <h3>${escapeHtml(copy.issues)}</h3>
      ${renderIssues(diagnostics.issues || data.flags || [], copy)}
    </section>
  `;
}

function renderBenchmark(benchmark, copy) {
  return `
    <div class="detail-metric-grid two">
      ${detailMetric('Calmar Alpha', fmtNum(benchmark.cal_alpha, 2), copy.calmarAlpha)}
      ${detailMetric('DD Reduction', fmtPct(benchmark.dd_reduction_pct), copy.ddReduction)}
      ${detailMetric('Return Capture', fmtNum(benchmark.ret_capture, 2), copy.retCapture)}
      ${detailMetric('Strategy CAGR', fmtPct(benchmark.strategy?.cagr_pct), `MDD ${fmtPct(benchmark.strategy?.mdd_pct)}`)}
      ${detailMetric('Buy&Hold CAGR', fmtPct(benchmark.buy_hold?.cagr_pct), `MDD ${fmtPct(benchmark.buy_hold?.mdd_pct)}`)}
      ${detailMetric(copy.overlap, `${fmtNum(benchmark.overlap_days, 0)}d`, [benchmark.window_start, benchmark.window_end].filter(Boolean).join(' -> '))}
    </div>
  `;
}

function renderRiskEvidence(riskTags, triage, copy) {
  const dep = triage.dependency_lite || {};
  const evidence = triage.evidence_confidence || {};
  const persistence = triage.edge_persistence || {};
  return `
    <div class="detail-risk-list">
      ${riskTags.map((tag) => `
        <div class="detail-risk ${escapeHtml(tag.level || 'medium')}">
          <span>${escapeHtml(tag.label || '')}</span>
          <strong>${escapeHtml(riskLevel(tag.level, copy))}</strong>
        </div>
      `).join('')}
    </div>
    <div class="detail-metric-grid">
      ${detailMetric(copy.edgePersistence, persistence.label_local || persistence.label || '-')}
      ${detailMetric(copy.evidence, evidence.level_local || evidence.level || '-', evidence.observations ? `${evidence.observations} observations` : '')}
      ${detailMetric(copy.dependency, dep.label_local || dep.label || '-', dep.reason || '')}
    </div>
  `;
}

function renderIssues(issues, copy) {
  if (!issues.length) {
    return `<p class="detail-muted">${escapeHtml(copy.noIssues)}</p>`;
  }
  return `
    <div class="detail-issue-list">
      ${issues.slice(0, 5).map((issue, index) => {
        const text = issue.problem_local || (langInput.value === 'zh' ? issue.problem_zh : issue.problem) || issue.msg || issue.code || JSON.stringify(issue);
        const direction = issue.direction_local || (langInput.value === 'zh' ? issue.direction_zh : issue.direction) || '';
        return `
          <div class="detail-issue">
            <span>${index + 1}</span>
            <div>
              <strong>${escapeHtml(text)}</strong>
              ${direction ? `<p>${escapeHtml(direction)}</p>` : ''}
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderLineChart(chart, copy, options = {}) {
  const strategy = chart?.strategy || [];
  const buyHold = chart?.buy_hold || [];
  if (!strategy.length) {
    return `<div class="detail-chart-empty">${escapeHtml(copy.noData)}</div>`;
  }
  const series = [{ label: copy.strategy, points: strategy, color: '#1c7c54' }];
  if (buyHold.length) {
    series.push({ label: copy.buyHold, points: buyHold, color: '#b7791f' });
  }
  return renderSvgChart(series, copy, options);
}

function renderBandChart(chart, copy) {
  const band = chart?.band || [];
  if (!band.length) {
    return `<div class="detail-chart-empty">${escapeHtml(copy.noData)}</div>`;
  }
  return renderSvgChart([
    { label: '5%', points: band.map((p) => ({ x: p.x, y: p.lo })), color: '#94a3b8', muted: true },
    { label: 'Median', points: band.map((p) => ({ x: p.x, y: p.mid })), color: '#3157d5' },
    { label: '95%', points: band.map((p) => ({ x: p.x, y: p.hi })), color: '#94a3b8', muted: true },
  ], copy);
}

function renderSvgChart(series, copy, options = {}) {
  const width = 320;
  const height = 148;
  const pad = { top: 10, right: 12, bottom: 24, left: 38 };
  const allValues = series.flatMap((item) => item.points.map((point) => Number(point.y)).filter(Number.isFinite));
  if (!allValues.length) {
    return `<div class="detail-chart-empty">${escapeHtml(copy.noData)}</div>`;
  }
  let minY = Math.min(...allValues);
  let maxY = Math.max(...allValues);
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }
  const xMax = Math.max(...series.map((item) => Math.max(1, item.points.length - 1)));
  const x = (index) => pad.left + (index / xMax) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((maxY - value) / (maxY - minY)) * (height - pad.top - pad.bottom);
  const paths = series.map((item) => {
    const d = item.points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index).toFixed(1)} ${y(Number(point.y)).toFixed(1)}`).join(' ');
    return `<path d="${d}" fill="none" stroke="${item.color}" stroke-width="${item.muted ? 1.4 : 2.2}" stroke-linecap="round" stroke-linejoin="round" opacity="${item.muted ? 0.8 : 1}"/>`;
  }).join('');
  const zeroLine = minY < 0 && maxY > 0
    ? `<line x1="${pad.left}" y1="${y(0).toFixed(1)}" x2="${width - pad.right}" y2="${y(0).toFixed(1)}" stroke="#d7deeb" stroke-dasharray="4 4"/>`
    : '';
  return `
    <div class="detail-chart">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="diagnostic chart">
        <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="#d7deeb"/>
        <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="#d7deeb"/>
        ${zeroLine}
        ${paths}
        <text x="${pad.left}" y="${pad.top + 8}" class="detail-axis">${escapeHtml(axisLabel(maxY, options))}</text>
        <text x="${pad.left}" y="${height - pad.bottom - 4}" class="detail-axis">${escapeHtml(axisLabel(minY, options))}</text>
      </svg>
      <div class="detail-legend">
        ${series.map((item) => `<span><i style="background:${item.color}"></i>${escapeHtml(item.label)}</span>`).join('')}
      </div>
    </div>
  `;
}

function detailMetric(label, value, note = '') {
  return `
    <div class="detail-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value == null || value === '' ? '-' : value)}</strong>
      ${note ? `<em>${escapeHtml(note)}</em>` : ''}
    </div>
  `;
}

function detailCopy(lang) {
  return DIAGNOSTIC_COPY[lang] || DIAGNOSTIC_COPY.en;
}

function riskLevel(level, copy) {
  if (level === 'low') return copy.low;
  if (level === 'high') return copy.high;
  return copy.medium;
}

function fmtNum(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : '-';
}

function fmtPct(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(digits)}%` : '-';
}

function axisLabel(value, options = {}) {
  if (options.percentAxis) return fmtPct(value, 0);
  const abs = Math.abs(Number(value));
  if (abs >= 1000) return Number(value).toFixed(0);
  if (abs >= 10) return Number(value).toFixed(1);
  return Number(value).toFixed(2);
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

fileInput.addEventListener('change', (event) => {
  selectFile(event.target.files[0]);
});

dropZone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (event) => {
  event.preventDefault();
  dropZone.classList.remove('dragover');
  selectFile(event.dataTransfer.files[0]);
});

benchmarkInput.addEventListener('change', (event) => {
  selectBenchmarkFile(event.target.files[0]);
});

benchmarkZone.addEventListener('dragover', (event) => {
  event.preventDefault();
  benchmarkZone.classList.add('dragover');
});

benchmarkZone.addEventListener('dragleave', () => {
  benchmarkZone.classList.remove('dragover');
});

benchmarkZone.addEventListener('drop', (event) => {
  event.preventDefault();
  benchmarkZone.classList.remove('dragover');
  selectBenchmarkFile(event.dataTransfer.files[0]);
});

scoreBtn.addEventListener('click', scoreFile);
shareCardBtn.addEventListener('click', shareScorecard);
downloadCardBtn.addEventListener('click', () => downloadArtifact('card'));
downloadPdfBtn.addEventListener('click', () => downloadArtifact('pdf'));
emailArtifactsBtn.addEventListener('click', emailArtifacts);
document.querySelectorAll('[data-share-platform]').forEach((button) => {
  button.addEventListener('click', () => sharePlatform(button.dataset.sharePlatform));
});

document.getElementById('retry-btn').addEventListener('click', () => showView('upload'));
langInput.addEventListener('change', () => {
  applyLanguage();
  saveSettings();
});
document.getElementById('another-btn').addEventListener('click', () => {
  fileInput.value = '';
  benchmarkInput.value = '';
  selectFile(null);
  selectBenchmarkFile(null);
  state.result = null;
  setArtifactStatus('');
  showView('upload');
});

async function initPopup() {
  await loadSettings();
  applyManifestVersion();
  applyLanguage();
  await loadAssets();
}

initPopup();
