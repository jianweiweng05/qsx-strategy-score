// content.js - 注入到 TradingView 页面的脚本

(function() {
  'use strict';

  const DEFAULT_API_BASE = 'https://www.quantscopex.com';
  const LEGACY_LOCAL_API_PATTERN = /^https?:\/\/(?:127\.0\.0\.1|localhost):8001\/?$/i;
  const LEGACY_API_BASE_PATTERN = /^https:\/\/api\.quantscopex\.com\/?$/i;
  const MODAL_COPY = {
    zh: {
      autoDetect: '自动检测',
      buttonTitle: 'QSX Strategy Score：分析策略过拟合、回撤和择时优势',
      uploadTitle: '上传 TradingView 导出文件',
      uploadSubtitle: '支持 CSV 或 XLSX 格式',
      assetLabel: '对比资产',
      benchmarkLabel: '自定义基准 K 线',
      benchmarkButton: '选择 K 线文件',
      benchmarkHint: '可选：包含日期和收盘价，优先于资产下拉选项',
      selectFile: '选择文件',
      helpTitle: '如何从 TradingView 导出数据？',
      help1: '打开 TradingView 策略测试器',
      help2: '点击“交易列表”标签',
      help3: '点击右上角的下载图标',
      help4: '选择“导出 CSV”或“导出 Excel”',
      loading: '正在分析策略…',
      failed: '分析失败',
      failedHint: '请确认文件由 TradingView 策略测试器导出。',
      sample: '样本量：',
      enough: '充足',
      thin: '偏小',
      edge: '优势检验：',
      problems: '发现的问题',
      another: '分析另一个策略',
      fullReport: '查看完整报告',
      fallbackCtaTitle: '继续做完整策略尽调',
      fallbackCtaBody: '免费评分已完成。下一步检查成本、滑点、极端行情窗口和真实逐日盯市回撤。',
    },
    en: {
      autoDetect: 'Auto-detect',
      buttonTitle: 'QSX Strategy Score: analyze overfit, drawdown, and timing edge',
      uploadTitle: 'Upload TradingView export',
      uploadSubtitle: 'CSV or XLSX supported',
      assetLabel: 'Benchmark asset',
      benchmarkLabel: 'Custom benchmark K-line',
      benchmarkButton: 'Choose K-line file',
      benchmarkHint: 'Optional: date + close/price, overrides asset selector',
      selectFile: 'Choose file',
      helpTitle: 'How to export data?',
      help1: 'Open TradingView Strategy Tester',
      help2: 'Click the "List of Trades" tab',
      help3: 'Click the download icon in the top right',
      help4: 'Choose "Export to CSV" or "Export to Excel"',
      loading: 'Analyzing strategy...',
      failed: 'Analysis failed',
      failedHint: 'Make sure the file was exported from TradingView Strategy Tester.',
      sample: 'Sample:',
      enough: 'enough',
      thin: 'thin',
      edge: 'Edge test:',
      problems: 'Issues found',
      another: 'Analyze another strategy',
      fullReport: 'View full report',
      fallbackCtaTitle: 'Continue with a full strategy audit',
      fallbackCtaBody: 'The free score is complete. Next check costs, slippage, crisis windows, and true MTM drawdown.',
    },
    ja: {
      autoDetect: '自動検出',
      buttonTitle: 'QSX Strategy Score：過剰最適化、DD、タイミング優位性を分析',
      uploadTitle: 'TradingViewエクスポートをアップロード',
      uploadSubtitle: 'CSVまたはXLSX対応',
      assetLabel: '比較資産',
      benchmarkLabel: 'カスタム基準Kライン',
      benchmarkButton: 'Kラインを選択',
      benchmarkHint: '任意：date + close/price。資産選択より優先',
      selectFile: 'ファイルを選択',
      helpTitle: 'データのエクスポート方法',
      help1: 'TradingView Strategy Testerを開く',
      help2: '"List of Trades"タブをクリック',
      help3: '右上のダウンロードアイコンをクリック',
      help4: '"Export to CSV"または"Export to Excel"を選択',
      loading: '戦略を分析中...',
      failed: '分析に失敗しました',
      failedHint: 'TradingView Strategy Testerからエクスポートしたファイルか確認してください。',
      sample: 'サンプル:',
      enough: '十分',
      thin: '不足',
      edge: 'Edge検査:',
      problems: '検出された問題',
      another: '別の戦略を分析',
      fullReport: '完全レポートを見る',
      fallbackCtaTitle: '完全な戦略監査へ進む',
      fallbackCtaBody: '無料スコアは完了しました。次にコスト、スリッページ、危機局面、真のMTMドローダウンを確認します。',
    },
    ko: {
      autoDetect: '자동 감지',
      buttonTitle: 'QSX Strategy Score: 과최적화, 드로다운, 타이밍 엣지 분석',
      uploadTitle: 'TradingView 내보내기 업로드',
      uploadSubtitle: 'CSV 또는 XLSX 지원',
      assetLabel: '비교 자산',
      benchmarkLabel: '사용자 기준 K-line',
      benchmarkButton: 'K-line 파일 선택',
      benchmarkHint: '선택: date + close/price, 자산 선택보다 우선',
      selectFile: '파일 선택',
      helpTitle: '데이터 내보내기 방법',
      help1: 'TradingView Strategy Tester 열기',
      help2: '"List of Trades" 탭 클릭',
      help3: '오른쪽 위 다운로드 아이콘 클릭',
      help4: '"Export to CSV" 또는 "Export to Excel" 선택',
      loading: '전략 분석 중...',
      failed: '분석 실패',
      failedHint: 'TradingView Strategy Tester에서 내보낸 파일인지 확인하세요.',
      sample: '표본:',
      enough: '충분',
      thin: '부족',
      edge: 'Edge 검사:',
      problems: '발견된 문제',
      another: '다른 전략 분석',
      fullReport: '전체 보고서 보기',
      fallbackCtaTitle: '전체 전략 실사로 계속',
      fallbackCtaBody: '무료 점수는 완료되었습니다. 다음으로 비용, 슬리피지, 위기 구간, 실제 MTM 드로다운을 확인하세요.',
    },
    es: {
      autoDetect: 'Auto-detectar',
      buttonTitle: 'QSX Strategy Score: analiza sobreajuste, drawdown y edge',
      uploadTitle: 'Subir export de TradingView',
      uploadSubtitle: 'CSV o XLSX soportado',
      assetLabel: 'Activo de referencia',
      benchmarkLabel: 'K-line personalizada',
      benchmarkButton: 'Elegir K-line',
      benchmarkHint: 'Opcional: date + close/price, reemplaza el activo',
      selectFile: 'Elegir archivo',
      helpTitle: '¿Cómo exportar datos?',
      help1: 'Abre TradingView Strategy Tester',
      help2: 'Haz clic en "List of Trades"',
      help3: 'Haz clic en el icono de descarga',
      help4: 'Elige "Export to CSV" o "Export to Excel"',
      loading: 'Analizando estrategia...',
      failed: 'Análisis fallido',
      failedHint: 'Asegúrate de que el archivo venga de TradingView Strategy Tester.',
      sample: 'Muestra:',
      enough: 'suficiente',
      thin: 'débil',
      edge: 'Prueba de edge:',
      problems: 'Problemas encontrados',
      another: 'Analizar otra estrategia',
      fullReport: 'Ver informe completo',
      fallbackCtaTitle: 'Continuar con auditoría completa',
      fallbackCtaBody: 'El score gratuito está listo. Luego revisa costos, slippage, crisis y drawdown MTM real.',
    },
    'pt-BR': {
      autoDetect: 'Auto-detectar',
      buttonTitle: 'QSX Strategy Score: analisa overfit, drawdown e edge',
      uploadTitle: 'Enviar export do TradingView',
      uploadSubtitle: 'CSV ou XLSX suportado',
      assetLabel: 'Ativo de referência',
      benchmarkLabel: 'K-line personalizada',
      benchmarkButton: 'Escolher K-line',
      benchmarkHint: 'Opcional: date + close/price, substitui o ativo',
      selectFile: 'Escolher arquivo',
      helpTitle: 'Como exportar dados?',
      help1: 'Abra TradingView Strategy Tester',
      help2: 'Clique na aba "List of Trades"',
      help3: 'Clique no ícone de download',
      help4: 'Escolha "Export to CSV" ou "Export to Excel"',
      loading: 'Analisando estratégia...',
      failed: 'Análise falhou',
      failedHint: 'Confira se o arquivo foi exportado do TradingView Strategy Tester.',
      sample: 'Amostra:',
      enough: 'suficiente',
      thin: 'fraca',
      edge: 'Teste de edge:',
      problems: 'Problemas encontrados',
      another: 'Analisar outra estratégia',
      fullReport: 'Ver relatório completo',
      fallbackCtaTitle: 'Continuar com auditoria completa',
      fallbackCtaBody: 'O score gratuito está pronto. Depois revise custos, slippage, crises e drawdown MTM real.',
    },
  };
  let modalElement = null;
  let benchmarkFile = null;
  let currentModalLang = inferBrowserLang();

  // 检测是否在 Strategy Tester 页面
  function isStrategyTesterPage() {
    return window.location.href.includes('/chart/') &&
           (
             document.querySelector('[data-name="backtesting"]') ||
             document.querySelector('[data-name="backtesting-toolbar"]') ||
             document.body.innerText.includes('Strategy Tester')
           );
  }

  async function getApiBase() {
    try {
      const saved = await chrome.storage.local.get(['apiBase']);
      const apiBase = (saved.apiBase || DEFAULT_API_BASE).replace(/\/+$/, '');
      if (LEGACY_LOCAL_API_PATTERN.test(apiBase) || LEGACY_API_BASE_PATTERN.test(apiBase)) {
        await chrome.storage.local.set({ apiBase: DEFAULT_API_BASE });
        return DEFAULT_API_BASE;
      }
      return apiBase;
    } catch (error) {
      return DEFAULT_API_BASE;
    }
  }

  async function getPreferredLang() {
    try {
      const saved = await chrome.storage.local.get(['lang']);
      if (saved.lang) return saved.lang;
    } catch (error) {
      // Keep the TradingView modal usable even if extension storage is unavailable.
    }
    const browserLang = (navigator.language || 'zh').toLowerCase();
    if (browserLang.startsWith('zh')) return 'zh';
    if (browserLang.startsWith('ja')) return 'ja';
    if (browserLang.startsWith('ko')) return 'ko';
    if (browserLang.startsWith('es')) return 'es';
    if (browserLang.startsWith('pt')) return 'pt-BR';
    return 'en';
  }

  function inferBrowserLang() {
    const browserLang = (navigator.language || 'en').toLowerCase();
    if (browserLang.startsWith('zh')) return 'zh';
    if (browserLang.startsWith('ja')) return 'ja';
    if (browserLang.startsWith('ko')) return 'ko';
    if (browserLang.startsWith('es')) return 'es';
    if (browserLang.startsWith('pt')) return 'pt-BR';
    return 'en';
  }

  async function syncPreferredLang() {
    currentModalLang = await getPreferredLang();
    return currentModalLang;
  }

  function getCurrentModalLang() {
    return currentModalLang;
  }

  function modalCopy(lang = currentModalLang) {
    return MODAL_COPY[lang] || MODAL_COPY.en;
  }

  async function loadAssetsInto(select, lang = currentModalLang) {
    const fallback = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'SPY', 'QQQ', 'AAPL', 'TSLA'];
    try {
      const response = await fetch(`${await getApiBase()}/api/score/assets`);
      const payload = await response.json();
      const keys = Array.isArray(payload.assets)
        ? payload.assets.map((item) => item.key).filter(Boolean)
        : [];
      populateAssetSelect(select, keys.length ? keys : fallback, lang);
    } catch (error) {
      populateAssetSelect(select, fallback, lang);
    }
  }

  function populateAssetSelect(select, keys, lang = currentModalLang) {
    const copy = modalCopy(lang);
    select.innerHTML = `<option value="">${escapeHtml(copy.autoDetect)}</option>`;
    keys.forEach((key) => {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = key;
      select.appendChild(option);
    });
  }

  // 创建诊断按钮
  function createButton() {
    const button = document.createElement('div');
    button.id = 'qsx-diagnose-btn';
    button.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M9 2a7 7 0 100 14A7 7 0 009 2zm0 12a5 5 0 110-10 5 5 0 010 10zm0-8a.75.75 0 01.75.75v2.5h2.5a.75.75 0 010 1.5h-3.25a.75.75 0 01-.75-.75v-3.25A.75.75 0 019 6z"/>
      </svg>
      <span>QSX Strategy Score</span>
    `;
    button.title = modalCopy(getCurrentModalLang()).buttonTitle;

    button.addEventListener('click', () => {
      showModal();
    });

    return button;
  }

  // 注入按钮到页面
  function injectButton() {
    if (document.getElementById('qsx-diagnose-btn')) return;

    // 寻找合适的位置插入按钮（Strategy Tester 工具栏）
    const toolbar = document.querySelector('[data-name="backtesting-toolbar"]') ||
                   document.querySelector('.backtesting-header') ||
                   document.querySelector('body');

    const button = createButton();
    if (toolbar && toolbar !== document.body) {
      toolbar.appendChild(button);
    } else {
      // 如果找不到工具栏，创建浮动按钮
      button.style.position = 'fixed';
      button.style.bottom = '20px';
      button.style.right = '20px';
      button.style.zIndex = '10000';
      document.body.appendChild(button);
    }
  }

  // 显示上传弹窗
  async function showModal() {
    const lang = await syncPreferredLang();
    if (modalElement) {
      if (modalElement.dataset.lang !== lang) {
        modalElement.remove();
        modalElement = null;
      } else {
        modalElement.style.display = 'flex';
        return;
      }
    }

    if (modalElement) {
      modalElement.style.display = 'flex';
      return;
    }

    const copy = modalCopy(lang);
    modalElement = document.createElement('div');
    modalElement.id = 'qsx-modal';
    modalElement.dataset.lang = lang;
    modalElement.innerHTML = `
      <div class="qsx-modal-content">
        <div class="qsx-modal-header">
          <h2>QSX Strategy Score</h2>
          <button class="qsx-close">&times;</button>
        </div>

        <div class="qsx-modal-body">
          <div id="qsx-upload-area" class="qsx-upload-area">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            <h3>${escapeHtml(copy.uploadTitle)}</h3>
            <p>${escapeHtml(copy.uploadSubtitle)}</p>
            <div class="qsx-controls">
              <label>
                <span>${escapeHtml(copy.assetLabel)}</span>
                <select id="qsx-asset-select">
                  <option value="">${escapeHtml(copy.autoDetect)}</option>
                </select>
              </label>
              <label>
                <span>${escapeHtml(copy.benchmarkLabel)}</span>
                <button id="qsx-select-benchmark" class="qsx-btn qsx-btn-secondary" type="button">
                  ${escapeHtml(copy.benchmarkButton)}
                </button>
                <input type="file" id="qsx-benchmark-input" accept=".csv,.tsv,.txt,.xlsx,.xls,.xlsm" style="display:none">
                <small id="qsx-benchmark-name">${escapeHtml(copy.benchmarkHint)}</small>
              </label>
            </div>
            <input type="file" id="qsx-file-input" accept=".csv,.xlsx,.xls" style="display:none">
            <button id="qsx-select-file" class="qsx-btn qsx-btn-primary" type="button">
              ${escapeHtml(copy.selectFile)}
            </button>
            <div class="qsx-help">
              <details>
                <summary>${escapeHtml(copy.helpTitle)}</summary>
                <ol>
                  <li>${escapeHtml(copy.help1)}</li>
                  <li>${escapeHtml(copy.help2)}</li>
                  <li>${escapeHtml(copy.help3)}</li>
                  <li>${escapeHtml(copy.help4)}</li>
                </ol>
              </details>
            </div>
          </div>

          <div id="qsx-result-area" class="qsx-result-area" style="display:none">
            <!-- 结果显示区域 -->
          </div>

          <div id="qsx-loading-area" class="qsx-loading-area" style="display:none">
            <div class="qsx-spinner"></div>
            <p id="qsx-loading-text">${escapeHtml(copy.loading)}</p>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modalElement);

    // 绑定事件
    modalElement.querySelector('.qsx-close').addEventListener('click', () => {
      modalElement.style.display = 'none';
    });

    modalElement.addEventListener('click', (e) => {
      if (e.target === modalElement) {
        modalElement.style.display = 'none';
      }
    });

    document.getElementById('qsx-select-file').addEventListener('click', () => {
      document.getElementById('qsx-file-input').click();
    });
    document.getElementById('qsx-file-input').addEventListener('change', handleFileUpload);
    document.getElementById('qsx-select-benchmark').addEventListener('click', () => {
      document.getElementById('qsx-benchmark-input').click();
    });
    document.getElementById('qsx-benchmark-input').addEventListener('change', (event) => {
      benchmarkFile = event.target.files[0] || null;
      document.getElementById('qsx-benchmark-name').textContent = benchmarkFile
        ? benchmarkFile.name
        : modalCopy(getCurrentModalLang()).benchmarkHint;
    });
    loadAssetsInto(document.getElementById('qsx-asset-select'), lang);

    // 拖拽上传
    const uploadArea = document.getElementById('qsx-upload-area');
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) {
        analyzeFile(file);
      }
    });
  }

  // 处理文件上传
  function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
      analyzeFile(file);
    }
  }

  // 分析文件
  async function analyzeFile(file) {
    const uploadArea = document.getElementById('qsx-upload-area');
    const loadingArea = document.getElementById('qsx-loading-area');
    const resultArea = document.getElementById('qsx-result-area');
    const lang = await syncPreferredLang();
    const copy = modalCopy(lang);

    uploadArea.style.display = 'none';
    loadingArea.style.display = 'block';
    document.getElementById('qsx-loading-text').textContent = copy.loading;
    resultArea.style.display = 'none';

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('lang', lang);
      const assetSelect = document.getElementById('qsx-asset-select');
      if (assetSelect?.value) {
        formData.append('asset_key', assetSelect.value);
      }
      if (benchmarkFile) {
        formData.append('benchmark_file', benchmarkFile);
      }

      const response = await fetch(`${await getApiBase()}/api/score`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || error.hint || error.error || modalCopy(lang).failed);
      }

      const result = await response.json();
      displayResult(normalizeScorePayload(result, lang), lang);

    } catch (error) {
      loadingArea.style.display = 'none';
      resultArea.style.display = 'block';
      resultArea.innerHTML = renderErrorCard(error, copy);
      const retry = document.getElementById('qsx-error-retry');
      retry?.addEventListener('click', () => {
        resultArea.style.display = 'none';
        uploadArea.style.display = 'block';
      });
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
      headline_local: report.headline_local || report.meta?.headline_local || (lang === 'zh' ? (report.meta?.headline_zh || report.headline) : report.headline),
      meta: { ...(report.meta || {}), resolved_asset: payload.resolved_asset || null },
    };
  }

  // 显示结果
  function displayResult(data, lang = 'zh') {
    const c = modalCopy(lang);
    const loadingArea = document.getElementById('qsx-loading-area');
    const resultArea = document.getElementById('qsx-result-area');

    loadingArea.style.display = 'none';
    resultArea.style.display = 'block';

    const gradeColors = {
      'GOLD': '#FFD700',
      'SILVER': '#C0C0C0',
      'BRONZE': '#CD7F32',
      'NEEDS WORK': '#FF6B6B',
      'FLAGGED': '#E74C3C'
    };

    const edgeIcons = {
      'beat': '✅',
      'marginal': '⚠️',
      'lost': '❌',
      'random_fail': '❌',
      'not_evaluated': 'ℹ️'
    };

    resultArea.innerHTML = `
      <div class="qsx-score-card">
        <div class="qsx-score-header">
          <div class="qsx-score-number" style="color: ${gradeColors[data.grade] || '#666'}">
            ${data.display}
          </div>
          <div class="qsx-score-grade">
            <span class="qsx-badge" style="background: ${gradeColors[data.grade] || '#666'}">
              ${escapeHtml(localizedGrade(data.grade, lang))}
            </span>
          </div>
        </div>

        <div class="qsx-headline">
          ${escapeHtml(data.headline_local || data.headline || '')}
        </div>

        <div class="qsx-pillars">
          ${Object.entries(data.pillars || {}).map(([name, pillar]) => `
            <div class="qsx-pillar">
              <div class="qsx-pillar-label">${escapeHtml(localizedPillarName(name, data, lang))}</div>
              <div class="qsx-pillar-bar">
                <div class="qsx-pillar-fill" style="width: ${pillar.value || 0}%"></div>
              </div>
              <div class="qsx-pillar-value">${Math.round(pillar.value || 0)}</div>
            </div>
          `).join('')}
        </div>

        <div class="qsx-lights">
          <div class="qsx-light">
            <span>${escapeHtml(c.sample)}</span>
            <span class="qsx-light-${escapeHtml(data.lights?.sample || '')}">
              ${data.lights?.sample === 'ok' ? `✅ ${escapeHtml(c.enough)}` : `⚠️ ${escapeHtml(c.thin)}`}
            </span>
          </div>
          <div class="qsx-light">
            <span>${escapeHtml(c.edge)}</span>
            <span class="qsx-light-${escapeHtml(data.lights?.edge || '')}">
              ${edgeIcons[data.lights?.edge] || ''}
              ${escapeHtml(localizedEdge(data.lights?.edge, lang))}
            </span>
          </div>
        </div>

        ${data.flags && data.flags.length > 0 ? `
          <div class="qsx-flags">
            <h4>${escapeHtml(c.problems)}</h4>
            <ul>
              ${data.flags.map(flag => `
                <li class="qsx-flag-${escapeHtml(flag.severity || 'warn')}">
                  ${escapeHtml(flag.msg_local || flag.msg || flag.code || '')}
                </li>
              `).join('')}
            </ul>
          </div>
        ` : ''}

        ${renderSmartCTA(data, lang)}

        <div class="qsx-actions">
          <button id="qsx-analyze-another" class="qsx-btn qsx-btn-secondary" type="button">
            ${escapeHtml(c.another)}
          </button>
          <a href="https://www.quantscopex.com/report?utm_source=chrome_ext&utm_medium=result_cta&utm_campaign=tv_extension&utm_content=modal_footer"
             target="_blank" class="qsx-btn qsx-btn-primary">
            ${escapeHtml(c.fullReport)}
          </a>
        </div>
      </div>
    `;

    document.getElementById('qsx-analyze-another').addEventListener('click', () => {
      document.getElementById('qsx-file-input').value = '';
      document.getElementById('qsx-benchmark-input').value = '';
      benchmarkFile = null;
      document.getElementById('qsx-benchmark-name').textContent = modalCopy(lang).benchmarkHint;
      document.getElementById('qsx-upload-area').style.display = 'block';
      document.getElementById('qsx-result-area').style.display = 'none';
    });
  }

  function renderSmartCTA(data, lang) {
    if (!window.QSXSmartCTA) {
      const c = modalCopy(lang);
      return `
        <div class="qsx-smart-cta qsx-smart-cta-pro">
          <div class="qsx-smart-kicker">${escapeHtml(c.fullReport)}</div>
          <h3>${escapeHtml(c.fallbackCtaTitle)}</h3>
          <p>${escapeHtml(c.fallbackCtaBody)}</p>
          <div class="qsx-smart-actions">
            <a href="https://www.quantscopex.com/report?utm_source=chrome_ext&utm_medium=fallback_cta&utm_campaign=tv_extension"
               target="_blank" rel="noopener noreferrer" class="qsx-btn qsx-btn-primary">
              ${escapeHtml(c.fullReport)}
            </a>
          </div>
        </div>
      `;
    }
    const cta = window.QSXSmartCTA.getSmartCTA(data, lang);
    return `
      <div class="qsx-smart-cta qsx-smart-cta-${escapeHtml(cta.kind)}">
        <div class="qsx-smart-kicker">${escapeHtml(cta.kicker)}</div>
        <h3>${escapeHtml(cta.title)}</h3>
        <p>${escapeHtml(cta.body)}</p>
        <div class="qsx-smart-proof">
          <span>${escapeHtml(cta.evidenceLabel)}</span>
          ${cta.evidence.slice(0, 3).map(item => `<strong>${escapeHtml(item)}</strong>`).join('')}
        </div>
        <div class="qsx-smart-actions">
          <a href="${escapeHtml(cta.primaryUrl)}" target="_blank" rel="noopener noreferrer" class="qsx-btn qsx-btn-primary">
            ${escapeHtml(cta.button)}
          </a>
          <a href="${escapeHtml(cta.secondaryUrl)}" target="_blank" rel="noopener noreferrer" class="qsx-btn qsx-btn-secondary">
            ${escapeHtml(cta.secondaryLabel)}
          </a>
        </div>
      </div>
    `;
  }

  function renderErrorCard(error, copy) {
    return `
      <div class="qsx-error-card">
        <h3>${escapeHtml(copy.failed)}</h3>
        <p>${escapeHtml(error?.message || copy.failedHint)}</p>
        <p>${escapeHtml(copy.failedHint)}</p>
        <div class="qsx-actions">
          <button id="qsx-error-retry" class="qsx-btn qsx-btn-secondary" type="button">
            ${escapeHtml(copy.another)}
          </button>
          <a href="https://www.quantscopex.com/report?utm_source=chrome_ext&utm_medium=api_error&utm_campaign=tv_extension"
             target="_blank" rel="noopener noreferrer" class="qsx-btn qsx-btn-primary">
            ${escapeHtml(copy.fullReport)}
          </a>
        </div>
      </div>
    `;
  }

  function localizedPillarName(name, data, lang = currentModalLang) {
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

  function localizedGrade(grade, lang = currentModalLang) {
    const labels = {
      zh: {
        GOLD: '金牌',
        SILVER: '银牌',
        BRONZE: '铜牌',
        PROVISIONAL: '暂定',
        'NEEDS WORK': '需改进',
        FLAGGED: '存疑',
      },
      en: { GOLD: 'Gold', SILVER: 'Silver', BRONZE: 'Bronze', PROVISIONAL: 'Provisional', 'NEEDS WORK': 'Needs work', FLAGGED: 'Flagged' },
      ja: { GOLD: 'ゴールド', SILVER: 'シルバー', BRONZE: 'ブロンズ', PROVISIONAL: '暫定', 'NEEDS WORK': '要改善', FLAGGED: '要検証' },
      ko: { GOLD: '골드', SILVER: '실버', BRONZE: '브론즈', PROVISIONAL: '잠정', 'NEEDS WORK': '개선 필요', FLAGGED: '검증 필요' },
      es: { GOLD: 'Oro', SILVER: 'Plata', BRONZE: 'Bronce', PROVISIONAL: 'Provisional', 'NEEDS WORK': 'Necesita trabajo', FLAGGED: 'Sospechoso' },
      'pt-BR': { GOLD: 'Ouro', SILVER: 'Prata', BRONZE: 'Bronze', PROVISIONAL: 'Provisória', 'NEEDS WORK': 'Precisa melhorar', FLAGGED: 'Sinalizado' },
    };
    return labels[lang]?.[grade] || grade || '-';
  }

  function localizedEdge(edge, lang = currentModalLang) {
    const labels = {
      zh: {
        beat: '跑赢买入持有和随机择时',
        hold_only: '跑赢买入持有，随机对照不可用',
        lost: '未跑赢买入持有',
        random_fail: '相比随机择时没有优势',
        marginal: '优势很薄',
        luck_unclear: '难以和运气区分',
        not_evaluated: '未评估优势',
      },
      en: { beat: 'beats hold + random timing', hold_only: 'beats buy & hold; random control unavailable', lost: 'did NOT beat buy & hold', random_fail: 'no edge over random timing', marginal: 'only a marginal edge', luck_unclear: 'hard to tell from luck', not_evaluated: 'not evaluated — add asset K-line' },
      ja: { beat: '保有とランダムを上回る', hold_only: '買い持ちを上回るがランダム対照不可', lost: '買い持ちに劣後', random_fail: 'ランダムタイミングに優位性なし', marginal: '優位性はわずか', luck_unclear: '運との区別が難しい', not_evaluated: '未評価 - 資産価格を追加' },
      ko: { beat: '보유와 랜덤 타이밍을 상회', hold_only: '매수 보유 상회, 랜덤 대조 불가', lost: '매수 보유보다 낮음', random_fail: '랜덤 타이밍 대비 우위 없음', marginal: '우위가 약함', luck_unclear: '운과 구분이 어려움', not_evaluated: '미평가 - 자산 가격 추가' },
      es: { beat: 'supera hold y timing aleatorio', hold_only: 'supera buy & hold; control aleatorio no disponible', lost: 'no supera buy & hold', random_fail: 'sin ventaja vs timing aleatorio', marginal: 'ventaja marginal', luck_unclear: 'difícil separarlo de suerte', not_evaluated: 'no evaluado - agrega precios del activo' },
      'pt-BR': { beat: 'supera hold e timing aleatório', hold_only: 'supera buy & hold; controle aleatório indisponível', lost: 'não supera buy & hold', random_fail: 'sem vantagem vs timing aleatório', marginal: 'vantagem marginal', luck_unclear: 'difícil separar de sorte', not_evaluated: 'não avaliado - adicione preços do ativo' },
    };
    return labels[lang]?.[edge] || edge || '-';
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // 初始化
  function init() {
    // 每秒检查一次是否在 Strategy Tester 页面
    setInterval(() => {
      if (isStrategyTesterPage() && !document.getElementById('qsx-diagnose-btn')) {
        injectButton();
      }
    }, 1000);
  }

  init();
})();
