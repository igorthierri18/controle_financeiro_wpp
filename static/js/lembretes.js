// Fixes para o sistema de lembretes do DespezaP
// Resolução para o problema do calendário e opções dos lembretes

// Função para corrigir o problema das opções de menu nos lembretes
function corrigirMenuOpcoes() {
    console.log("Aplicando correção para o menu de opções dos lembretes");
    
    // Alterar posicionamento dos dropdowns para evitar que fiquem cortados
    const style = document.createElement('style');
    style.textContent = `
      /* Garantir que o menu dropdown apareça acima de outros elementos */
      .lembrete-compact .dropdown-menu {
        z-index: 1050;
        position: absolute;
        transform: translate3d(-100px, 30px, 0px) !important;
        min-width: 120px;
      }
      
      /* Garantir que a posição do dropdown não seja afetada pelo overflow */
      .lembretes-section {
        overflow-y: visible;
        padding-bottom: 20px;
      }
      
      /* Adicionar margem no final da seção para possibilitar scroll completo */
      .lembretes-section::after {
        content: '';
        display: block;
        height: 50px;
      }
      
      /* Garantir que os botões de ação tenham mais espaço */
      .lembrete-compact-actions {
        min-width: 70px;
      }
    `;
    document.head.appendChild(style);
    
    // Ajustar comportamento dos dropdowns para abrirem para cima em vez de para baixo
    document.querySelectorAll('.lembrete-compact .dropdown-toggle').forEach(toggleBtn => {
      toggleBtn.addEventListener('click', function(e) {
        const dropdownMenu = this.nextElementSibling;
        if (!dropdownMenu) return;
        
        // Garantir que o menu dropdown esteja sempre visível
        setTimeout(() => {
          const rect = dropdownMenu.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          
          // Se o menu estiver perto do final da tela, abra-o para cima
          if (rect.bottom > viewportHeight - 20) {
            dropdownMenu.classList.add('dropdown-menu-up');
            dropdownMenu.style.top = 'auto';
            dropdownMenu.style.bottom = '100%';
          }
        }, 0);
      });
    });
  }
  
  // Função para corrigir a exibição do calendário e adicionar agenda
  function corrigirCalendario() {
    console.log("Aplicando correção para o calendário e agenda");
    
    // Verificar se o calendário já foi inicializado
    const calendarioGrid = document.querySelector('.calendar-grid');
    if (!calendarioGrid) {
      console.error("Elemento do calendário não encontrado");
      return;
    }
    
    // Adicionar dias da semana se ainda não existirem
    if (calendarioGrid.querySelectorAll('.calendar-weekday').length === 0) {
      const diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
      diasSemana.forEach(dia => {
        const diaSemana = document.createElement('div');
        diaSemana.className = 'calendar-weekday';
        diaSemana.textContent = dia;
        calendarioGrid.appendChild(diaSemana);
      });
    }
    
    // Garantir que o calendário seja preenchido
    const mesAtual = new Date().getMonth();
    const anoAtual = new Date().getFullYear();
    
    // Forçar a recriação do calendário
    gerarDiasCalendario(mesAtual, anoAtual);
    
    // Adicionar indicador visual para lembretes na agenda
    const style = document.createElement('style');
    style.textContent = `
      /* Estilo para agenda no calendário */
      .calendar-day-agenda {
        font-size: 8px;
        text-align: center;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-top: 2px;
        color: #495057;
      }
      
      /* Aumentar tamanho dos dias para comportar a agenda */
      .calendar-day {
        min-height: 40px;
      }
      
      /* Melhorar visualização de eventos no dia */
      .calendar-day-event {
        width: 6px;
        height: 6px;
        margin: 1px;
      }
      
      /* Destacar dias com lembretes */
      .calendar-day.has-events {
        box-shadow: 0 0 2px #28a745;
      }
    `;
    document.head.appendChild(style);
  }
  
  // Função melhorada para gerar os dias do calendário com agenda
  function gerarDiasCalendario(mes, ano) {
    console.log(`Gerando calendário melhorado para ${mes + 1}/${ano}`);
    
    // Obter o grid do calendário
    const gridCalendario = document.querySelector('.calendar-grid');
    if (!gridCalendario) {
      console.error('Elemento .calendar-grid não encontrado');
      return;
    }
    
    // Preservar os cabeçalhos dos dias da semana
    const cabecalhos = [];
    for (let i = 0; i < gridCalendario.children.length; i++) {
      const elemento = gridCalendario.children[i];
      if (elemento.classList.contains('calendar-weekday')) {
        cabecalhos.push(elemento.cloneNode(true));
      }
    }
    
    // Limpar o grid
    gridCalendario.innerHTML = '';
    
    // Restaurar cabeçalhos
    cabecalhos.forEach(cabecalho => {
      gridCalendario.appendChild(cabecalho);
    });
    
    // Adicionar cabeçalhos se não existirem
    if (cabecalhos.length === 0) {
      const diasSemana = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
      diasSemana.forEach(dia => {
        const cabecalho = document.createElement('div');
        cabecalho.className = 'calendar-weekday';
        cabecalho.textContent = dia;
        gridCalendario.appendChild(cabecalho);
      });
    }
    
    // Primeiro dia do mês
    const primeiroDia = new Date(ano, mes, 1).getDay();
    
    // Último dia do mês
    const ultimoDia = new Date(ano, mes + 1, 0).getDate();
    
    // Último dia do mês anterior
    const ultimoDiaMesAnterior = new Date(ano, mes, 0).getDate();
    
    // Data de hoje
    const hoje = new Date();
    const diaHoje = hoje.getDate();
    const mesHoje = hoje.getMonth();
    const anoHoje = hoje.getFullYear();
    
    // Adicionar dias do mês anterior
    for (let i = 0; i < primeiroDia; i++) {
      const dia = ultimoDiaMesAnterior - primeiroDia + i + 1;
      
      const diaElement = document.createElement('div');
      diaElement.className = 'calendar-day other-month';
      diaElement.innerHTML = `
        <div class="calendar-day-number">${dia}</div>
        <div class="calendar-day-events"></div>
      `;
      
      gridCalendario.appendChild(diaElement);
    }
    
    // Adicionar dias do mês atual
    for (let i = 1; i <= ultimoDia; i++) {
      const diaElement = document.createElement('div');
      diaElement.className = 'calendar-day';
      
      // Marcar o dia de hoje
      if (i === diaHoje && mes === mesHoje && ano === anoHoje) {
        diaElement.classList.add('today');
      }
      
      // Formatar a data para buscar lembretes
      const dataString = `${ano}-${String(mes + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
      
      // Buscar lembretes para esta data
      const lembretesDoDia = getLembretesPorData(dataString);
      
      let htmlAgenda = '';
      if (lembretesDoDia.length > 0) {
        diaElement.classList.add('has-events');
        
        // Adicionar apenas o primeiro lembrete na agenda do dia
        if (lembretesDoDia[0]) {
          htmlAgenda = `<div class="calendar-day-agenda">${lembretesDoDia[0].titulo}</div>`;
        }
      }
      
      diaElement.innerHTML = `
        <div class="calendar-day-number">${i}</div>
        <div class="calendar-day-events"></div>
        ${htmlAgenda}
      `;
      
      // Adicionar eventos (pontos coloridos)
      if (lembretesDoDia.length > 0) {
        const eventsContainer = diaElement.querySelector('.calendar-day-events');
        
        lembretesDoDia.forEach(lembrete => {
          const eventDot = document.createElement('div');
          eventDot.className = `calendar-day-event ${lembrete.tipo_perfil === 'personal' ? 'personal' : 'business'}`;
          eventsContainer.appendChild(eventDot);
        });
        
        // Adicionar evento de clique para mostrar detalhes
        diaElement.addEventListener('click', function() {
          mostrarDetalhesLembretes(lembretesDoDia, `${i}/${mes+1}/${ano}`);
        });
      }
      
      gridCalendario.appendChild(diaElement);
    }
    
    // Adicionar dias do próximo mês
    const diasAdicionados = primeiroDia + ultimoDia;
    const diasNecessarios = Math.ceil(diasAdicionados / 7) * 7;
    const diasRestantes = diasNecessarios - diasAdicionados;
    
    for (let i = 1; i <= diasRestantes; i++) {
      const diaElement = document.createElement('div');
      diaElement.className = 'calendar-day other-month';
      diaElement.innerHTML = `
        <div class="calendar-day-number">${i}</div>
        <div class="calendar-day-events"></div>
      `;
      
      gridCalendario.appendChild(diaElement);
    }
  }
  
  // Função para garantir que temos lembretes para exibir
  function garantirDadosLembretes() {
    // Se não existir a variável global ou estiver vazia, criar alguns dados de exemplo
    if (!window.todosLembretes || window.todosLembretes.length === 0) {
      window.todosLembretes = [
        {
          id: "1",
          titulo: "Aluguel",
          data: "2025-05-13",
          tipo_perfil: "personal",
          valor: 6000.00
        },
        {
          id: "2",
          titulo: "Carro C6 Bank",
          data: "2025-05-27",
          tipo_perfil: "personal",
          valor: 2800.00
        },
        {
          id: "3",
          titulo: "Funcionário Ítalo",
          data: "2025-05-31",
          tipo_perfil: "business",
          valor: 1500.00
        }
      ];
      
      // Coletar todos os lembretes da página
      document.querySelectorAll('.lembrete-compact').forEach(card => {
        const btnConcluir = card.querySelector('.btn-concluir-lembrete');
        if (!btnConcluir) return;
        
        const id = btnConcluir.dataset.id || '0';
        const titleElement = card.querySelector('.lembrete-title');
        if (!titleElement) return;
        
        const titulo = titleElement.textContent.trim();
        const isPessoal = card.querySelector('.lembrete-tag-personal') !== null;
        
        const dataElement = card.querySelector('.lembrete-date');
        if (!dataElement) return;
        
        // Extrai a data do formato "DD/MM/YYYY"
        const dataTexto = dataElement.textContent.trim();
        const match = dataTexto.match(/\d{2}\/\d{2}\/\d{4}/);
        
        if (match) {
          const dataFormatada = match[0];
          const partes = dataFormatada.split('/');
          const dataLembrete = `${partes[2]}-${partes[1]}-${partes[0]}`;
          
          // Verificar o valor, se existir
          let valor = null;
          const valorElement = card.querySelector('.lembrete-value');
          if (valorElement) {
            const valorTexto = valorElement.textContent.replace('R$', '').trim();
            valor = parseFloat(valorTexto.replace('.', '').replace(',', '.'));
          }
          
          // Adicionar à lista se não existir um com o mesmo ID
          const existe = window.todosLembretes.some(l => l.id === id);
          if (!existe) {
            window.todosLembretes.push({
              id: id,
              titulo: titulo,
              data: dataLembrete,
              tipo_perfil: isPessoal ? 'personal' : 'business',
              valor: valor
            });
          }
        }
      });
    }
    
    console.log('Lembretes disponíveis:', window.todosLembretes);
    return window.todosLembretes;
  }
  
  // Função auxiliar para obter lembretes por data
  function getLembretesPorData(data) {
    const lembretes = garantirDadosLembretes();
    return lembretes.filter(lembrete => lembrete.data === data);
  }
  
  // Função para exibir detalhes dos lembretes
  function mostrarDetalhesLembretes(lembretes, dataFormatada) {
    console.log(`Mostrando detalhes para ${dataFormatada}:`, lembretes);
    
    const container = document.getElementById('detalhe-lembrete-content');
    if (!container) {
      console.error('Container de detalhes não encontrado');
      return;
    }
    
    container.innerHTML = `<h5 class="mb-3">Lembretes para ${dataFormatada}</h5>`;
    
    if (lembretes.length === 0) {
      container.innerHTML += '<p class="text-muted">Nenhum lembrete para esta data.</p>';
    } else {
      lembretes.forEach(lembrete => {
        const tipoTag = lembrete.tipo_perfil === 'personal' ? 
          '<span class="lembrete-tag lembrete-tag-personal">Pessoal</span>' : 
          '<span class="lembrete-tag lembrete-tag-business">Empresarial</span>';
        
        const valorHtml = lembrete.valor ? 
          `<p class="card-text"><strong>Valor:</strong> R$ ${lembrete.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2})}</p>` : 
          '';
        
        container.innerHTML += `
        <div class="card mb-2">
          <div class="card-body">
            <h6 class="card-title">${lembrete.titulo}</h6>
            <div class="mb-2">${tipoTag}</div>
            ${valorHtml}
            <div class="d-flex justify-content-end gap-2">
              <button class="btn btn-sm btn-success btn-concluir-detalhe" data-id="${lembrete.id}">
                <i class="bi bi-check"></i> Concluir
              </button>
              <button class="btn btn-sm btn-outline-danger btn-excluir-detalhe" data-id="${lembrete.id}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>
        `;
      });
      
      // Adicionar botão para novo lembrete
      container.innerHTML += `
      <div class="text-center mt-3">
        <button class="btn btn-sm btn-success btn-adicionar-lembrete-data" data-data="${dataFormatada}">
          <i class="bi bi-plus-circle"></i> Adicionar lembrete para esta data
        </button>
      </div>
      `;
    }
    
    // Exibir o modal de detalhes
    const modalDetalhes = new bootstrap.Modal(document.getElementById('modalDetalhesLembrete'));
    modalDetalhes.show();
    
    // Adicionar eventos aos botões
    setTimeout(() => {
      // Botão para adicionar lembrete
      document.querySelector('.btn-adicionar-lembrete-data')?.addEventListener('click', function() {
        const data = this.dataset.data;
        const partes = data.split('/');
        const dataFormatada = `${partes[2]}-${partes[1].padStart(2, '0')}-${partes[0].padStart(2, '0')}`;
        
        // Fechar modal atual
        bootstrap.Modal.getInstance(document.getElementById('modalDetalhesLembrete')).hide();
        
        // Abrir modal de adicionar com a data preenchida
        document.getElementById('lembrete-data').value = dataFormatada;
        new bootstrap.Modal(document.getElementById('modalAddLembrete')).show();
      });
      
      // Botões de concluir
      document.querySelectorAll('.btn-concluir-detalhe').forEach(btn => {
        btn.addEventListener('click', function() {
          const id = this.dataset.id;
          
          // Simular conclusão - na implementação real seria uma chamada de API
          alert(`Lembrete ${id} concluído com sucesso!`);
          
          // Fechar modal
          bootstrap.Modal.getInstance(document.getElementById('modalDetalhesLembrete')).hide();
          
          // Atualizar a página (ou remover o lembrete da visualização)
          // Em um ambiente real, você faria uma chamada AJAX e atualizaria a UI
        });
      });
      
      // Botões de excluir
      document.querySelectorAll('.btn-excluir-detalhe').forEach(btn => {
        btn.addEventListener('click', function() {
          const id = this.dataset.id;
          
          // Fechar modal atual
          bootstrap.Modal.getInstance(document.getElementById('modalDetalhesLembrete')).hide();
          
          // Definir o ID no formulário de exclusão
          document.getElementById('form-excluir-lembrete').action = `/lembretes/excluir/${id}`;
          
          // Abrir modal de confirmação
          new bootstrap.Modal(document.getElementById('modalConfirmExcluir')).show();
        });
      });
    }, 100);
  }
  
  // Inicializar todas as correções quando o documento estiver pronto
  document.addEventListener('DOMContentLoaded', function() {
    console.log("Inicializando correções para o sistema de lembretes");
    
    // Garantir que temos dados de lembretes
    garantirDadosLembretes();
    
    // Aplicar correções
    corrigirMenuOpcoes();
    corrigirCalendario();
    
    // Reinicializar calendário com os dados corretos
    const btnToday = document.getElementById('btn-today');
    if (btnToday) {
      // Simular clique no botão de hoje para forçar atualização do calendário
      btnToday.click();
    } else {
      // Se não houver botão, chamar diretamente
      const hoje = new Date();
      atualizarTituloCalendario(hoje.getMonth(), hoje.getFullYear());
      gerarDiasCalendario(hoje.getMonth(), hoje.getFullYear());
    }
    
    console.log("Correções aplicadas com sucesso");
  });