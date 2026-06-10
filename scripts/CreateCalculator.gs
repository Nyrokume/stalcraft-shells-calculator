/**
 * ВАЖНО: весь код в ОДНОМ файле (Code.gs).
 * Удалите лишние .gs файлы в проекте. Сохраните Ctrl+S перед Run.
 *
 * Запуск: syncAndFixAll  или меню «Калькулятор → Обновить»
 */
var MAX_N = 109;

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Калькулятор')
    .addItem('Обновить (syncAndFixAll)', 'syncAndFixAll')
    .addItem('Полная пересборка', 'createCalculator')
    .addItem('Только B37:C47', 'fixBinomialFormulas')
    .addToUi();
}

function syncAndFixAll() {
  buildCalculator_(false);
}

function createCalculator() {
  buildCalculator_(true);
}

function fixBinomialFormulas() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Калькулятор');
  if (!sheet) {
    sheet = SpreadsheetApp.getActiveSpreadsheet().insertSheet('Калькулятор');
  }
  var p = readParamsFromSheet1_();
  writeBinomialValues_(sheet, p);
  SpreadsheetApp.getUi().alert('B37:C47 обновлены. N=' + p.n);
}

function buildCalculator_(fullRebuild) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName('Калькулятор');
  if (!sheet) {
    sheet = ss.insertSheet('Калькулятор');
  } else if (fullRebuild) {
    sheet.clear();
  }

  var p = readParamsFromSheet1_();

  sheet.getRange('A1:E1').merge().setValue('КАЛЬКУЛЯТОР ХОДОК (данные с Лист1)');
  sheet.getRange('A2:C2').setValues([['Параметр', 'Значение', 'Ед.']]);
  sheet.getRange('A3:C7').setValues([
    ['Закуп за ходку', p.zkp, '₽'],
    ['Смерть при миграции', p.migrate, 'доля'],
    ['Смерть на севере', p.sever, 'доля'],
    ['Лут при успехе', p.loot, '₽'],
    ['Количество ходок (N)', p.n, ''],
  ]);

  sheet.getRange('A9').setValue('РЕЗУЛЬТАТ');
  sheet.getRange('A10:A18').setValues([
    ['P добраться (1 ходка)'],
    ['P успех (1 ходка)'],
    ['EV за 1 ходку'],
    ['Затраты за N'],
    ['Ожид. валовый лут'],
    ['Ожид. чистый профит'],
    ['P (≥1 успех за N)'],
    ['P (≥1 добег за N)'],
    ['Ожид. выносов'],
  ]);
  sheet.getRange('B10').setFormula('=1-B4');
  sheet.getRange('B11').setFormula('=(1-B4)*(1-B5)');
  sheet.getRange('B12').setFormula('=B11*B6-B3');
  sheet.getRange('B13').setFormula('=B7*B3');
  sheet.getRange('B14').setFormula('=B7*B11*B6');
  sheet.getRange('B15').setFormula('=B7*(B11*B6-B3)');
  sheet.getRange('B16').setFormula('=1-(1-B11)^INT(B7)');
  sheet.getRange('B17').setFormula('=1-B4^INT(B7)');
  sheet.getRange('B18').setFormula('=INT(B7)*B11');

  writeBinomialValues_(sheet, p);
  writeProfitTable_(sheet, 20, MAX_N);
  writeProbTable_(sheet, 230, MAX_N);
  writeSingleTripBlock_(sheet);
  writeExpectedOutcomes_(sheet, p);
  styleSheet_(sheet);
  rebuildCharts_(sheet);

  SpreadsheetApp.getUi().alert(
    'Готово.\nЛист: ' + p.sourceSheet +
      '\nN=1..' + MAX_N + '\nB37:C47 — числа (без #ERROR)'
  );
}

function readParamsFromSheet1_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var data = sh.getRange('A1:E80').getValues();
  var out = {
    sourceSheet: sh.getName(),
    zkp: 17000,
    migrate: 0.05,
    sever: 0.35,
    n: 5,
    loot: 73927.4,
  };
  var i;
  for (i = 0; i < data.length; i++) {
    var name = String(data[i][1] || '').toLowerCase().replace(/\s/g, '');
    var val = parseNum_(data[i][2]);
    if (val === null) continue;
    if (name.indexOf('avgzkp') >= 0 || name.indexOf('закуп') >= 0) out.zkp = val;
    if (name.indexOf('migratedth') >= 0 || name.indexOf('миграции') >= 0) {
      out.migrate = val > 1 ? val / 100 : val;
    }
    if (name.indexOf('severdeath') >= 0 || (name.indexOf('севере') >= 0 && name.indexOf('жизн') < 0)) {
      out.sever = val > 1 ? val / 100 : val;
    }
    if (name.indexOf('attemp') >= 0 || name.indexOf('попыт') >= 0) out.n = Math.max(1, Math.round(val));
    if (name.indexOf('loot') >= 0 || name.indexOf('лут') >= 0) out.loot = val;
  }
  out.pOk = (1 - out.migrate) * (1 - out.sever);
  if (out.pOk > 0) {
    for (i = 0; i < data.length; i++) {
      var nm = String(data[i][1] || '').toLowerCase();
      var v = parseNum_(data[i][2]);
      if (v !== null && (nm.indexOf('avgvns') >= 0 || nm.indexOf('avgprf') >= 0)) {
        out.loot = (v / out.n + out.zkp) / out.pOk;
        break;
      }
    }
  }
  return out;
}

function parseNum_(v) {
  if (v === '' || v === null) return null;
  if (typeof v === 'number') return v;
  var n = parseFloat(String(v).replace(/\s/g, '').replace(',', '.'));
  return isNaN(n) ? null : n;
}

function comb_(n, k) {
  if (k < 0 || k > n) return 0;
  var r = 1;
  var i;
  for (i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
  return r;
}

function binomPmf_(n, p, k) {
  if (k < 0 || k > n) return 0;
  return comb_(n, k) * Math.pow(p, k) * Math.pow(1 - p, n - k);
}

/** B37:C47 — готовые числа (не формулы) */
function writeBinomialValues_(sheet, p) {
  var n = Math.round(p.n);
  var k;
  var rows = [['k успехов', 'Вероятность', 'Чистый профит']];
  for (k = 0; k <= 10; k++) {
    if (k > n) {
      rows.push([k, '', '']);
    } else {
      rows.push([k, binomPmf_(n, p.pOk, k), k * p.loot - n * p.zkp]);
    }
  }
  sheet.getRange('A36:C47').setValues(rows);
  sheet.getRange('B37:B47').setNumberFormat('0.00%');
  sheet.getRange('C37:C47').setNumberFormat('#,##0');
}

function writeProfitTable_(sheet, headerRow, maxN) {
  var rows = [['N ходок', 'Чистый профит', 'Затраты', 'Валовый лут', 'P(≥1 успех)']];
  var i;
  for (i = 1; i <= maxN; i++) {
    var r = headerRow + i;
    rows.push([
      i,
      '=A' + r + '*(($B$11)*$B$6-$B$3)',
      '=A' + r + '*$B$3',
      '=A' + r + '*$B$11*$B$6',
      '=1-(1-$B$11)^A' + r,
    ]);
  }
  var lastRow = headerRow + maxN;
  sheet.getRange('A' + headerRow + ':E' + lastRow).setValues(rows);
}

function writeProbTable_(sheet, headerRow, maxN) {
  var rows = [['N', 'P (≥1 добег)', 'P (≥1 успех)', 'P (0 успехов)']];
  var i;
  for (i = 1; i <= maxN; i++) {
    var r = headerRow + i;
    rows.push([
      i,
      '=1-$B$4^A' + r,
      '=1-(1-$B$11)^A' + r,
      '=(1-$B$11)^A' + r,
    ]);
  }
  var lastRow = headerRow + maxN;
  sheet.getRange('A' + headerRow + ':D' + lastRow).setValues(rows);
}

function writeSingleTripBlock_(sheet) {
  sheet.getRange('A50:B50').setValues([['Исход (1 ходка)', 'P']]);
  sheet.getRange('A51:A53').setValues([
    ['1. Смерть при миграции'],
    ['2. Умер на севере'],
    ['3. Успешный вынос'],
  ]);
  sheet.getRange('B51').setFormula('=B4');
  sheet.getRange('B52').setFormula('=(1-B4)*B5');
  sheet.getRange('B53').setFormula('=B11');

  sheet.getRange('A55:B55').setValues([['Метрика', 'P']]);
  sheet.getRange('A56:A60').setValues([
    ['Не добежал'],
    ['Добежал'],
    ['Умер на севере'],
    ['Вынос'],
    ['Провал'],
  ]);
  sheet.getRange('B56').setFormula('=B4');
  sheet.getRange('B57').setFormula('=1-B4');
  sheet.getRange('B58').setFormula('=(1-B4)*B5');
  sheet.getRange('B59').setFormula('=B11');
  sheet.getRange('B60').setFormula('=1-B11');
}

function writeExpectedOutcomes_(sheet, p) {
  var n = Math.round(p.n);
  sheet.getRange('A340:B345').setValues([
    ['Исход за N', 'Ожид. кол-во'],
    ['Не добежал', n * p.migrate],
    ['Добежал', n * (1 - p.migrate)],
    ['Умер на севере', n * (1 - p.migrate) * p.sever],
    ['Успешный вынос', n * p.pOk],
    ['Провал', n * (1 - p.pOk)],
  ]);
}

function styleSheet_(sheet) {
  sheet.getRange('B3:B7').setBackground('#fff9c4');
  sheet.getRange('A10:B18').setBackground('#e8f5e9');
  sheet.getRange('A36:C47').setBackground('#e8eaf6');
  sheet.getRange('A1').setBackground('#3366aa').setFontColor('#ffffff').setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, 6);
}

function rebuildCharts_(sheet) {
  sheet.getCharts().forEach(function (c) {
    sheet.removeChart(c);
  });
  var W = 560;
  var H = 320;
  var lastProfit = 20 + MAX_N;

  sheet.insertChart(
    sheet.newChart().setChartType(Charts.ChartType.PIE).addRange(sheet.getRange('A51:B53'))
      .setPosition(1, 7, 0, 0).setOption('title', '1. Исходы 1 ходки')
      .setOption('width', W).setOption('height', H).build()
  );
  sheet.insertChart(
    sheet.newChart().setChartType(Charts.ChartType.COLUMN).addRange(sheet.getRange('A56:B60'))
      .setPosition(1, 13, 0, 0).setOption('title', '2. P одной ходки')
      .setOption('legend', { position: 'none' }).setOption('width', W).setOption('height', H).build()
  );
  sheet.insertChart(
    sheet.newChart().setChartType(Charts.ChartType.LINE).addRange(sheet.getRange('A230:D' + (230 + MAX_N)))
      .setPosition(18, 7, 0, 0).setOption('title', '3. P(добег) и P(успех)')
      .setOption('legend', { position: 'bottom' }).setOption('width', W).setOption('height', H).build()
  );
  sheet.insertChart(
    sheet.newChart().setChartType(Charts.ChartType.LINE).addRange(sheet.getRange('A21:E' + lastProfit))
      .setPosition(18, 13, 0, 0).setOption('title', '4. Профит N=1..' + MAX_N)
      .setOption('legend', { position: 'bottom' }).setOption('width', W).setOption('height', H).build()
  );
  sheet.insertChart(
    sheet.newChart().setChartType(Charts.ChartType.COLUMN).addRange(sheet.getRange('A36:B47'))
      .setPosition(35, 7, 0, 0).setOption('title', '5. k успехов за N')
      .setOption('legend', { position: 'none' }).setOption('width', W).setOption('height', H).build()
  );
}
