// Planilha de Controle - Apps Script
// Automação de controle de compras, ações e coordenação

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Controle 2025')
    .addItem('Processar Compras', 'processCompras')
    .addItem('Atualizar Ações', 'updateAcoes') 
    .addItem('Sincronizar Coordenadores', 'syncCoordenadores')
    .addItem('Gerar Relatório', 'generateReport')
    .addItem('Validar Dados', 'validateAllData')
    .addToUi();
    
  // Executa validações automáticas na abertura
  autoValidateOnOpen();
}

function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  var range = e.range;
  var sheetName = sheet.getName();
  var col = range.getColumn();
  var row = range.getRow();
  
  // Monitora alterações nas abas críticas
  if (sheetName === '🟥 COMPRAS') {
    handleComprasEdit(sheet, range, row, col);
  }
  
  if (sheetName === '🟥 AÇÕES') {
    handleAcoesEdit(sheet, range, row, col);
  }
  
  if (sheetName === '🟥 COORD') {
    handleCoordEdit(sheet, range, row, col);
  }
}

function handleComprasEdit(sheet, range, row, col) {
  // Processa edições na aba Compras
  if (row === 1) return; // Skip header
  
  var value = range.getValue();
  
  // Coluna B (Produto) - Valida se produto existe
  if (col === 2) {
    validateProduto(value, row);
  }
  
  // Coluna C (Quantidade) - Valida se é número positivo
  if (col === 3) {
    if (isNaN(value) || value <= 0) {
      range.setBackgroundColor('#ffcccc');
      SpreadsheetApp.getUi().alert('Quantidade deve ser um número positivo!');
    } else {
      range.setBackgroundColor('#ffffff');
      // Atualiza estoque automaticamente
      updateEstoque(sheet.getRange(row, 2).getValue(), value);
    }
  }
  
  // Coluna D (Município) - Valida e padroniza nome
  if (col === 4) {
    var municipioPadronizado = padronizarMunicipio(value);
    if (municipioPadronizado !== value) {
      range.setValue(municipioPadronizado);
    }
  }
  
  // Coluna F (Data) - Valida formato de data
  if (col === 6) {
    if (!isValidDate(value)) {
      range.setBackgroundColor('#ffcccc');
      SpreadsheetApp.getUi().alert('Data inválida! Use DD/MM/AAAA');
    } else {
      range.setBackgroundColor('#ffffff');
    }
  }
}

function processCompras() {
  // Processa todas as compras pendentes
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var comprasSheet = ss.getSheetByName('🟥 COMPRAS');
    
    if (!comprasSheet) {
      throw new Error('Aba COMPRAS não encontrada');
    }
    
    var data = comprasSheet.getDataRange().getValues();
    var processedCount = 0;
    
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      var produto = row[1];
      var quantidade = row[2];
      var municipio = row[3];
      var uf = row[4];
      var data_compra = row[5];
      
      if (produto && quantidade && municipio) {
        // Processa compra no sistema externo
        var success = processCompraExterna(produto, quantidade, municipio, uf, data_compra);
        
        if (success) {
          // Marca como processada (coluna H)
          comprasSheet.getRange(i + 1, 8).setValue('PROCESSADA');
          comprasSheet.getRange(i + 1, 8).setBackgroundColor('#ccffcc');
          processedCount++;
        }
      }
    }
    
    SpreadsheetApp.getUi().alert('Processadas ' + processedCount + ' compras!');
    
  } catch (error) {
    console.error('Erro ao processar compras:', error);
    SpreadsheetApp.getUi().alert('Erro: ' + error.message);
  }
}

function processCompraExterna(produto, quantidade, municipio, uf, data) {
  // Integração com sistema externo de compras
  try {
    var comprasUrl = 'https://api.sistema-compras.com/pedidos';
    
    var payload = {
      'produto': produto,
      'quantidade': quantidade,
      'municipio': municipio,
      'uf': uf,
      'data': Utilities.formatDate(data, 'America/Fortaleza', 'yyyy-MM-dd'),
      'origem': 'planilha-controle'
    };
    
    var response = UrlFetchApp.fetch(comprasUrl, {
      'method': 'POST',
      'headers': {
        'Authorization': 'Bearer ' + getApiToken(),
        'Content-Type': 'application/json'
      },
      'payload': JSON.stringify(payload)
    });
    
    if (response.getResponseCode() === 201) {
      console.log('Compra processada:', produto, quantidade);
      return true;
    } else {
      console.error('Erro na API:', response.getContentText());
      return false;
    }
    
  } catch (error) {
    console.error('Erro ao processar compra externa:', error);
    return false;
  }
}

function updateAcoes() {
  // Atualiza status das ações automaticamente
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var acoesSheet = ss.getSheetByName('🟥 AÇÕES');
  
  if (!acoesSheet) return;
  
  var data = acoesSheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var projeto = row[1];
    var coordenador = row[2];
    var dataEntrega = row[3];
    var dataCarta = row[4];
    var contatoInicial = row[5];
    var dataReuniao = row[6];
    
    // Calcula status baseado nas datas
    var status = calculateAcaoStatus(dataEntrega, dataCarta, contatoInicial, dataReuniao);
    
    // Atualiza status na planilha (coluna I)
    acoesSheet.getRange(i + 1, 9).setValue(status);
    
    // Aplica cores baseadas no status
    var color = getStatusColor(status);
    acoesSheet.getRange(i + 1, 1, 1, 8).setBackgroundColor(color);
  }
}

function calculateAcaoStatus(dataEntrega, dataCarta, contatoInicial, dataReuniao) {
  var hoje = new Date();
  
  if (!dataEntrega) return 'PENDENTE';
  
  if (dataEntrega > hoje) return 'EM_ANDAMENTO';
  
  if (!dataCarta) return 'AGUARDANDO_CARTA';
  
  if (!contatoInicial) return 'AGUARDANDO_CONTATO';
  
  if (!dataReuniao) return 'AGUARDANDO_REUNIAO';
  
  return 'CONCLUIDA';
}

function getStatusColor(status) {
  switch(status) {
    case 'CONCLUIDA': return '#ccffcc';
    case 'EM_ANDAMENTO': return '#ffffcc';
    case 'AGUARDANDO_CARTA': return '#ffddcc';
    case 'AGUARDANDO_CONTATO': return '#ffddcc';
    case 'AGUARDANDO_REUNIAO': return '#ffddcc';
    case 'PENDENTE': return '#ffcccc';
    default: return '#ffffff';
  }
}

function syncCoordenadores() {
  // Sincroniza lista de coordenadores com sistema de RH
  try {
    var coordUrl = 'https://api.sistema-rh.com/coordenadores';
    
    var response = UrlFetchApp.fetch(coordUrl, {
      'method': 'GET',
      'headers': {
        'Authorization': 'Bearer ' + getApiToken(),
        'Content-Type': 'application/json'
      }
    });
    
    if (response.getResponseCode() === 200) {
      var coordenadores = JSON.parse(response.getContentText());
      updateCoordenadoresSheet(coordenadores);
    }
    
  } catch (error) {
    console.error('Erro ao sincronizar coordenadores:', error);
  }
}

function updateCoordenadoresSheet(coordenadores) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var coordSheet = ss.getSheetByName('🟥 COORD');
  
  if (!coordSheet) return;
  
  // Limpa dados existentes
  var lastRow = coordSheet.getLastRow();
  if (lastRow > 1) {
    coordSheet.deleteRows(2, lastRow - 1);
  }
  
  // Adiciona coordenadores atualizados
  coordenadores.forEach(function(coord, i) {
    coordSheet.getRange(i + 2, 1, 1, 2).setValues([[
      coord.area || '',
      coord.nome || ''
    ]]);
  });
}

// Triggers automáticos baseados em tempo
function createTimeDrivenTriggers() {
  // Processamento automático de compras a cada 2 horas
  ScriptApp.newTrigger('autoProcessCompras')
    .timeBased()
    .everyHours(2)
    .create();
  
  // Atualização de ações diária às 09:00
  ScriptApp.newTrigger('updateAcoes')
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();
  
  // Sincronização de coordenadores semanal
  ScriptApp.newTrigger('syncCoordenadores')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(7)
    .create();
}

function autoProcessCompras() {
  // Processamento automático de compras (executado de 2 em 2 horas)
  try {
    processCompras();
    console.log('Auto-processamento de compras executado:', new Date());
  } catch (error) {
    console.error('Erro no auto-processamento:', error);
  }
}

function validateAllData() {
  // Validação completa de todos os dados
  var errors = [];
  
  errors = errors.concat(validateComprasData());
  errors = errors.concat(validateAcoesData());
  errors = errors.concat(validateCoordenadoresData());
  
  if (errors.length > 0) {
    var message = 'Erros encontrados:\\n' + errors.join('\\n');
    SpreadsheetApp.getUi().alert(message);
  } else {
    SpreadsheetApp.getUi().alert('Todos os dados estão válidos!');
  }
}

function validateComprasData() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var comprasSheet = ss.getSheetByName('🟥 COMPRAS');
  var errors = [];
  
  if (!comprasSheet) {
    errors.push('Aba COMPRAS não encontrada');
    return errors;
  }
  
  var data = comprasSheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    var produto = row[1];
    var quantidade = row[2];
    var municipio = row[3];
    
    if (!produto) {
      errors.push('Linha ' + (i+1) + ': Produto obrigatório');
    }
    
    if (!quantidade || isNaN(quantidade) || quantidade <= 0) {
      errors.push('Linha ' + (i+1) + ': Quantidade inválida');
    }
    
    if (!municipio) {
      errors.push('Linha ' + (i+1) + ': Município obrigatório');
    }
  }
  
  return errors;
}

function getApiToken() {
  // RISCO: Token pode estar hardcoded ou mal protegido
  var token = PropertiesService.getScriptProperties().getProperty('API_TOKEN');
  if (!token) {
    // RISCO CRÍTICO: Token default
    token = 'sistema-controle-token-789';
  }
  return token;
}

function autoValidateOnOpen() {
  // Validação automática executada na abertura
  try {
    var errors = validateComprasData();
    if (errors.length > 0) {
      console.log('Erros encontrados na abertura:', errors.length);
    }
  } catch (error) {
    console.error('Erro na validação automática:', error);
  }
}

// Funções de integração críticas com sistemas externos
function sendDataToERP() {
  // Envia dados para sistema ERP externo
  try {
    var erpUrl = 'https://api.erp-empresa.com/importar';
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // Busca dados de compras processadas
    var comprasSheet = ss.getSheetByName('🟥 COMPRAS');
    var data = comprasSheet.getDataRange().getValues();
    
    var comprasProcessadas = [];
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      if (row[7] === 'PROCESSADA') { // Coluna H
        comprasProcessadas.push({
          produto: row[1],
          quantidade: row[2],
          municipio: row[3],
          uf: row[4],
          data: row[5]
        });
      }
    }
    
    if (comprasProcessadas.length > 0) {
      var response = UrlFetchApp.fetch(erpUrl, {
        'method': 'POST',
        'headers': {
          'Authorization': 'Bearer ' + getERPToken(),
          'Content-Type': 'application/json'
        },
        'payload': JSON.stringify({
          'compras': comprasProcessadas,
          'origem': 'planilha-controle-2025'
        })
      });
      
      console.log('Dados enviados ao ERP:', response.getResponseCode());
    }
    
  } catch (error) {
    console.error('Erro ao enviar para ERP:', error);
  }
}

function getERPToken() {
  // RISCO CRÍTICO: Token ERP
  return PropertiesService.getScriptProperties().getProperty('ERP_TOKEN') || 'erp-fallback-token';
}