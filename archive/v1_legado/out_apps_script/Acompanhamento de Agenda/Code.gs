// Acompanhamento de Agenda - Apps Script Principal
// Automação de criação e sincronização de eventos no Google Calendar

function onOpen() {
  // Trigger executado ao abrir a planilha
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Agenda 2025')
    .addItem('Sincronizar com Google Calendar', 'syncAllCalendars')
    .addItem('Processar Eventos Pendentes', 'processNewEvents')
    .addItem('Validar Conflitos', 'checkConflicts')
    .addItem('Limpar Cache', 'clearCache')
    .addToUi();
  
  // Log de abertura
  console.log('Planilha aberta: ' + new Date());
}

function onEdit(e) {
  // Trigger crítico - executa a cada edição
  var sheet = e.source.getActiveSheet();
  var range = e.range;
  var sheetName = sheet.getName();
  
  // Processa apenas abas relevantes
  var targetSheets = ['Super', 'ACerta', 'Vidas', 'Outros', 'Brincando'];
  
  if (targetSheets.indexOf(sheetName) === -1) return;
  
  // Colunas críticas que disparam automação
  var col = range.getColumn();
  var row = range.getRow();
  
  // Coluna A (Controle) - Liga/desliga processamento
  if (col === 1 && row > 1) {
    var value = range.getValue();
    if (value === 'SIM') {
      // Marca para processamento automático
      markForProcessing(sheetName, row);
    }
  }
  
  // Coluna B (Aprovação) - Dispara criação no calendar
  if (col === 2 && row > 1) {
    var value = range.getValue();
    if (value === 'APROVADO') {
      // Cria evento automaticamente
      createCalendarEvent(sheetName, row);
    }
  }
  
  // Coluna C (Atualizar) - Atualiza evento existente
  if (col === 3 && row > 1) {
    var value = range.getValue();
    if (value === true || value === 'SIM') {
      updateCalendarEvent(sheetName, row);
    }
  }
  
  // Coluna D (Cancelar) - Remove evento
  if (col === 4 && row > 1) {
    var value = range.getValue();
    if (value === true || value === 'SIM') {
      cancelCalendarEvent(sheetName, row);
    }
  }
}

function syncAllCalendars() {
  // Função principal de sincronização
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheets = ['Super', 'ACerta', 'Vidas', 'Outros', 'Brincando'];
    
    for (var i = 0; i < sheets.length; i++) {
      var sheet = ss.getSheetByName(sheets[i]);
      if (sheet) {
        syncSheetToCalendar(sheet);
      }
    }
    
    // Atualiza aba Google Agenda
    updateGoogleAgendaSheet();
    
    SpreadsheetApp.getUi().alert('Sincronização concluída!');
    
  } catch (error) {
    console.error('Erro na sincronização:', error);
    SpreadsheetApp.getUi().alert('Erro: ' + error.message);
  }
}

function createCalendarEvent(sheetName, row) {
  // Cria evento no Google Calendar
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(sheetName);
    var data = sheet.getRange(row, 1, 1, 20).getValues()[0];
    
    // Extrai dados da linha
    var municipio = data[4];  // Coluna E
    var encontro = data[5];   // Coluna F
    var tipo = data[6];       // Coluna G
    var data_evento = data[7]; // Coluna H
    var hora_inicio = data[8]; // Coluna I
    var hora_fim = data[9];    // Coluna J
    var projeto = data[10];    // Coluna K
    var coordenador = data[13]; // Coluna N
    var formadores = [data[14], data[15], data[16], data[17], data[18]]; // Colunas O-S
    var convidados = data[19];  // Coluna T
    
    // Constrói título do evento
    var titulo = projeto + ' - ' + municipio + ' - ' + encontro;
    
    // Constrói descrição
    var descricao = 'Projeto: ' + projeto + '\\n';
    descricao += 'Coordenador: ' + coordenador + '\\n';
    descricao += 'Formadores: ' + formadores.filter(f => f).join(', ') + '\\n';
    descricao += 'Tipo: ' + tipo;
    
    // Cria data/hora completa
    var inicio = new Date(data_evento);
    if (hora_inicio) {
      var horaStr = hora_inicio.toString();
      var horas = horaStr.split(':');
      inicio.setHours(parseInt(horas[0]), parseInt(horas[1] || 0));
    }
    
    var fim = new Date(inicio);
    if (hora_fim) {
      var horaFimStr = hora_fim.toString();
      var horasFim = horaFimStr.split(':');
      fim.setHours(parseInt(horasFim[0]), parseInt(horasFim[1] || 0));
    } else {
      fim.setHours(inicio.getHours() + 2); // Default 2h
    }
    
    // Lista de convidados
    var guests = [];
    if (convidados) {
      guests = convidados.split(',').map(email => email.trim());
    }
    
    // Cria evento no Calendar
    var calendar = CalendarApp.getDefaultCalendar();
    var event = calendar.createEvent(titulo, inicio, fim, {
      description: descricao,
      location: municipio,
      guests: guests.join(','),
      sendInvites: true
    });
    
    // Registra o ID do evento na planilha
    var googleSheet = ss.getSheetByName('Google Agenda');
    if (googleSheet) {
      // Adiciona linha na aba Google Agenda
      var lastRow = googleSheet.getLastRow() + 1;
      googleSheet.getRange(lastRow, 1, 1, 21).setValues([[
        false, // Delete
        true,  // Update
        titulo,
        data_evento,
        data_evento,
        hora_inicio,
        hora_fim,
        '', '', '', '', '', // Repeat fields
        descricao,
        municipio,
        'America/Fortaleza',
        guests.join(','),
        event.getId(),
        event.getEditUrl(),
        '', // Meet link
        'Peacock',
        ''  // Attachments
      ]]);
    }
    
    console.log('Evento criado:', event.getId());
    return event.getId();
    
  } catch (error) {
    console.error('Erro ao criar evento:', error);
    throw error;
  }
}

function processNewEvents() {
  // Processa eventos marcados para criação
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheets = ['Super', 'ACerta', 'Vidas', 'Outros', 'Brincando'];
  
  sheets.forEach(function(sheetName) {
    var sheet = ss.getSheetByName(sheetName);
    if (!sheet) return;
    
    var data = sheet.getDataRange().getValues();
    
    for (var i = 1; i < data.length; i++) { // Skip header
      var row = data[i];
      var controle = row[0];      // Coluna A
      var aprovacao = row[1];     // Coluna B
      var eventId = row[16] || ''; // Coluna Q (Event ID)
      
      // Se está marcado para controle, aprovado, mas sem Event ID
      if (controle === 'SIM' && aprovacao === 'APROVADO' && !eventId) {
        try {
          createCalendarEvent(sheetName, i + 1);
        } catch (error) {
          console.error('Erro ao processar evento linha', i + 1, ':', error);
        }
      }
    }
  });
}

function checkConflicts() {
  // Valida conflitos de agenda entre formadores
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var conflitos = [];
  
  // Implementação de detecção de conflitos
  // TODO: Implementar lógica de validação
  
  if (conflitos.length > 0) {
    SpreadsheetApp.getUi().alert('Conflitos detectados: ' + conflitos.length);
  } else {
    SpreadsheetApp.getUi().alert('Nenhum conflito detectado.');
  }
}

// Trigger automático baseado em tempo
function createTimeDrivenTriggers() {
  // Executa sincronização automática a cada hora
  ScriptApp.newTrigger('autoSync')
    .timeBased()
    .everyHours(1)
    .create();
  
  // Executa limpeza diária às 02:00
  ScriptApp.newTrigger('dailyCleanup')
    .timeBased()
    .everyDays(1)
    .atHour(2)
    .create();
}

function autoSync() {
  // Sincronização automática (executada de hora em hora)
  try {
    processNewEvents();
    console.log('Auto-sync executado:', new Date());
  } catch (error) {
    console.error('Erro no auto-sync:', error);
  }
}

function dailyCleanup() {
  // Limpeza diária de dados antigos
  try {
    // Remove eventos antigos (> 30 dias)
    cleanOldEvents();
    console.log('Limpeza diária executada:', new Date());
  } catch (error) {
    console.error('Erro na limpeza diária:', error);
  }
}

// FUNÇÕES DE INTEGRAÇÃO EXTERNA

function fetchExternalData() {
  // Busca dados de sistemas externos
  try {
    var response = UrlFetchApp.fetch('https://api.aprender.com/formadores', {
      'method': 'GET',
      'headers': {
        'Authorization': 'Bearer ' + getApiToken(),
        'Content-Type': 'application/json'
      }
    });
    
    if (response.getResponseCode() === 200) {
      var data = JSON.parse(response.getContentText());
      updateFormatorsData(data);
    }
    
  } catch (error) {
    console.error('Erro ao buscar dados externos:', error);
  }
}

function getApiToken() {
  // RISCO DE SEGURANÇA: Token pode estar hardcoded
  return PropertiesService.getScriptProperties().getProperty('API_TOKEN') || 'fallback-token-123';
}

function validateFormatorAvailability(formador, data, horario) {
  // Valida disponibilidade do formador
  try {
    var disponibilidadeUrl = 'https://api.sistema-interno.com/disponibilidade';
    var payload = {
      'formador': formador,
      'data': data,
      'horario': horario
    };
    
    var response = UrlFetchApp.fetch(disponibilidadeUrl, {
      'method': 'POST',
      'headers': {
        'Content-Type': 'application/json'
      },
      'payload': JSON.stringify(payload)
    });
    
    return response.getResponseCode() === 200;
    
  } catch (error) {
    console.error('Erro na validação:', error);
    return false;
  }
}