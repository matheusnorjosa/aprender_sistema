// Disponibilidade - Apps Script
// Controle automático de disponibilidade mensal e anual dos formadores

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('Disponibilidade 2025')
    .addItem('Atualizar Calendários', 'updateAllCalendars')
    .addItem('Calcular Disponibilidade Mensal', 'calculateMonthlyAvailability')
    .addItem('Gerar Relatório Anual', 'generateAnnualReport')
    .addItem('Sincronizar Bloqueios', 'syncBlockings')
    .addToUi();
}

function onEdit(e) {
  var sheet = e.source.getActiveSheet();
  var range = e.range;
  var sheetName = sheet.getName();
  
  // Monitora alterações nas abas críticas
  if (sheetName === 'Bloqueios') {
    // Atualiza disponibilidade quando bloqueios são alterados
    var row = range.getRow();
    if (row > 1) { // Skip header
      updateAvailabilityFromBlocking(row);
    }
  }
  
  if (sheetName === 'MENSAL') {
    // Recalcula totais quando dados mensais são alterados
    calculateMonthlyTotals();
  }
}

function updateAllCalendars() {
  // Busca eventos de todos os formadores no Google Calendar
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var configSheet = ss.getSheetByName('Configurações');
    
    if (!configSheet) {
      throw new Error('Aba Configurações não encontrada');
    }
    
    // Busca lista de formadores
    var formadores = getFormadores();
    
    formadores.forEach(function(formador) {
      updateFormadorCalendar(formador);
    });
    
    SpreadsheetApp.getUi().alert('Calendários atualizados!');
    
  } catch (error) {
    console.error('Erro ao atualizar calendários:', error);
    SpreadsheetApp.getUi().alert('Erro: ' + error.message);
  }
}

function getFormadores() {
  // Busca formadores da aba Configurações
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var configSheet = ss.getSheetByName('Configurações');
  
  var data = configSheet.getDataRange().getValues();
  var formadores = [];
  
  for (var i = 1; i < data.length; i++) {
    var formador = data[i][2]; // Coluna C (Formador)
    var email = data[i][3];    // Coluna D (Email)
    
    if (formador && email) {
      formadores.push({
        nome: formador,
        email: email
      });
    }
  }
  
  return formadores;
}

function updateFormadorCalendar(formador) {
  // Atualiza disponibilidade baseada no Google Calendar do formador
  try {
    // Busca calendário do formador
    var calendar = CalendarApp.getCalendarsByName(formador.email)[0];
    if (!calendar) {
      console.log('Calendar não encontrado para:', formador.email);
      return;
    }
    
    // Período de análise: próximos 3 meses
    var startDate = new Date();
    var endDate = new Date();
    endDate.setMonth(endDate.getMonth() + 3);
    
    // Busca eventos no período
    var events = calendar.getEvents(startDate, endDate);
    
    // Atualiza planilha com eventos encontrados
    updateAvailabilitySheet(formador, events);
    
  } catch (error) {
    console.error('Erro ao atualizar calendar do formador', formador.nome, ':', error);
  }
}

function calculateMonthlyAvailability() {
  // Calcula disponibilidade mensal automática
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var mensalSheet = ss.getSheetByName('MENSAL');
  
  if (!mensalSheet) {
    throw new Error('Aba MENSAL não encontrada');
  }
  
  // Fórmulas complexas para cálculo de disponibilidade
  var formulas = [
    '=SUMPRODUCT((MONTH(Eventos!C:C)=MONTH(TODAY()))*(Eventos!E:E<>\"\"))',
    '=COUNTIFS(Bloqueios!B:B,\">=\"&DATE(YEAR(TODAY()),MONTH(TODAY()),1),Bloqueios!C:C,\"<=\"&EOMONTH(TODAY(),0))',
    '=NETWORKDAYS(DATE(YEAR(TODAY()),MONTH(TODAY()),1),EOMONTH(TODAY(),0))*8-SUMIF(Bloqueios!D:D,\"Total\",Bloqueios!C:C-Bloqueios!B:B+1)*8'
  ];
  
  // Aplica fórmulas nas células apropriadas
  mensalSheet.getRange('B10').setFormula(formulas[0]); // Total eventos
  mensalSheet.getRange('B11').setFormula(formulas[1]); // Total bloqueios
  mensalSheet.getRange('B12').setFormula(formulas[2]); // Horas disponíveis
}

function generateAnnualReport() {
  // Gera relatório anual de disponibilidade
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var anualSheet = ss.getSheetByName('ANUAL');
  
  if (!anualSheet) {
    throw new Error('Aba ANUAL não encontrada');
  }
  
  // Busca dados de todo o ano
  var formadores = getFormadores();
  var meses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 
               'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ'];
  
  // Constrói matriz de disponibilidade anual
  var matrix = [];
  
  formadores.forEach(function(formador, i) {
    var row = [formador.nome];
    
    meses.forEach(function(mes, j) {
      // Fórmula para calcular disponibilidade por mês
      var formula = '=SUMPRODUCT((MONTH(Eventos!C:C)=' + (j+1) + ')*(Eventos!E:E=\"' + formador.nome + '\"))';
      row.push(formula);
    });
    
    matrix.push(row);
  });
  
  // Escreve matriz na planilha
  if (matrix.length > 0) {
    anualSheet.getRange(2, 1, matrix.length, matrix[0].length).setValues(matrix);
  }
}

function syncBlockings() {
  // Sincroniza bloqueios com sistemas externos
  try {
    var bloqueiosUrl = 'https://api.sistema-rh.com/bloqueios';
    
    var response = UrlFetchApp.fetch(bloqueiosUrl, {
      'method': 'GET',
      'headers': {
        'Authorization': 'Bearer ' + getApiToken(),
        'Content-Type': 'application/json'
      }
    });
    
    if (response.getResponseCode() === 200) {
      var bloqueios = JSON.parse(response.getContentText());
      updateBloqueiosSheet(bloqueios);
    }
    
  } catch (error) {
    console.error('Erro ao sincronizar bloqueios:', error);
  }
}

function updateBloqueiosSheet(bloqueios) {
  // Atualiza aba Bloqueios com dados externos
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var bloqueiosSheet = ss.getSheetByName('Bloqueios');
  
  if (!bloqueiosSheet) return;
  
  // Limpa dados existentes (exceto header)
  var lastRow = bloqueiosSheet.getLastRow();
  if (lastRow > 1) {
    bloqueiosSheet.deleteRows(2, lastRow - 1);
  }
  
  // Adiciona novos bloqueios
  bloqueios.forEach(function(bloqueio, i) {
    bloqueiosSheet.getRange(i + 2, 1, 1, 4).setValues([[
      bloqueio.pessoa || '',
      new Date(bloqueio.dataInicio),
      new Date(bloqueio.dataFim), 
      bloqueio.tipo || 'Total'
    ]]);
  });
}

// Triggers automáticos baseados em tempo
function createTimeDrivenTriggers() {
  // Atualização diária às 06:00
  ScriptApp.newTrigger('dailyUpdate')
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .create();
  
  // Sincronização de bloqueios a cada 4 horas
  ScriptApp.newTrigger('syncBlockings')
    .timeBased()
    .everyHours(4)
    .create();
  
  // Relatório semanal às segundas 08:00
  ScriptApp.newTrigger('weeklyReport')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8)
    .create();
}

function dailyUpdate() {
  // Atualização automática diária
  try {
    updateAllCalendars();
    calculateMonthlyAvailability();
    console.log('Atualização diária executada:', new Date());
  } catch (error) {
    console.error('Erro na atualização diária:', error);
  }
}

function weeklyReport() {
  // Relatório semanal automático
  try {
    generateAnnualReport();
    sendWeeklyEmail();
    console.log('Relatório semanal executado:', new Date());
  } catch (error) {
    console.error('Erro no relatório semanal:', error);
  }
}

function sendWeeklyEmail() {
  // Envia relatório por email
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var url = ss.getUrl();
    
    var subject = 'Relatório Semanal de Disponibilidade - ' + Utilities.formatDate(new Date(), 'America/Fortaleza', 'dd/MM/yyyy');
    var body = 'Relatório de disponibilidade atualizado.\\n\\nAcesse: ' + url;
    
    // Lista de destinatários (RISCO: emails hardcoded)
    var recipients = [
      'gestao@aprender.com',
      'coordenacao@aprender.com', 
      'rh@aprender.com'
    ];
    
    recipients.forEach(function(email) {
      MailApp.sendEmail(email, subject, body);
    });
    
  } catch (error) {
    console.error('Erro ao enviar email:', error);
  }
}

function getApiToken() {
  // RISCO: Token pode estar exposto
  return PropertiesService.getScriptProperties().getProperty('API_TOKEN') || 'default-token-456';
}

// Função de validação de dados críticos
function validateDisponibilidadeData() {
  // Valida integridade dos dados de disponibilidade
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var errors = [];
  
  // Validação de bloqueios
  var bloqueiosSheet = ss.getSheetByName('Bloqueios');
  if (bloqueiosSheet) {
    var data = bloqueiosSheet.getDataRange().getValues();
    
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      var pessoa = row[0];
      var inicio = row[1];
      var fim = row[2];
      
      if (!pessoa || !inicio || !fim) {
        errors.push('Linha ' + (i+1) + ': Dados incompletos');
      }
      
      if (inicio > fim) {
        errors.push('Linha ' + (i+1) + ': Data fim anterior ao início');
      }
    }
  }
  
  return errors;
}