while (gridCalendario.children.length > 7) {
    gridCalendario.removeChild(gridCalendario.lastChild);
}

// Primeiro dia do mês (0 = Domingo, 1 = Segunda, etc.)
const primeiroDia = new Date(ano, mes, 1).getDay();

// Último dia do mês
const ultimoDia = new Date(ano, mes + 1, 0).getDate();

// Último dia do mês anterior
const ultimoDiaMesAnterior = new Date(ano, mes, 0).getDate();

// Data de hoje para comparação
const hoje = new Date();
const diaHoje = hoje.getDate();
const mesHoje = hoje.getMonth();
const anoHoje = hoje.getFullYear();

// Adiciona dias do mês anterior
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

// Adiciona dias do mês atual
for (let i = 1; i <= ultimoDia; i++) {
    const diaElement = document.createElement('div');
    diaElement.className = 'calendar-day';
    
    // Marca o dia de hoje
    if (i === diaHoje && mes === mesHoje && ano === anoHoje) {
        diaElement.classList.add('today');
    }
    
    diaElement.innerHTML = `
        <div class="calendar-day-number">${i}</div>
        <div class="calendar-day-events"></div>
    `;
    
    // Adiciona eventos deste dia (lembretes)
    const dataString = `${ano}-${String(mes + 1).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
    const lembretesDoDia = getLembretesPorData(dataString);
    
    if (lembretesDoDia.length > 0) {
        const eventsContainer = diaElement.querySelector('.calendar-day-events');
        
        lembretesDoDia.forEach(lembrete => {
            const eventDot = document.createElement('div');
            eventDot.className = `calendar-day-event ${lembrete.tipo_perfil}`;
            eventsContainer.appendChild(eventDot);
        });
        
        // Adiciona evento de clique para mostrar detalhes dos lembretes
        diaElement.addEventListener('click', function() {
            mostrarDetalhesLembretes(lembretesDoDia, `${i}/${mes+1}/${ano}`);
        });
    }
    
    gridCalendario.appendChild(diaElement);
}

// Adiciona dias do próximo mês para preencher a grade (até completar a última semana)
const diasAdicionados = primeiroDia + ultimoDia;
const diasNecessarios = 7 * Math.ceil(diasAdicionados / 7);
const celulasRestantes = diasNecessarios - diasAdicionados;

for (let i = 1; i <= celulasRestantes; i++) {
    const diaElement = document.createElement('div');
    diaElement.className = 'calendar-day other-month';
    diaElement.innerHTML = `
        <div class="calendar-day-number">${i}</div>
        <div class="calendar-day-events"></div>
    `;
    
    gridCalendario.appendChild(diaElement);
}
}

function getLembretesPorData(data) {
// Usar a estrutura de dados que preparamos inicialmente
if (!window.todosLembretes) {
    prepararLembretesParaCalendario();
}

// Filtrar lembretes pela data
return window.todosLembretes.filter(lembrete => lembrete.data === data);
}

function mostrarDetalhesLembretes(lembretes, dataFormatada) {
// Preenche o modal com os detalhes dos lembretes
const container = document.getElementById('detalhe-lembrete-content');
container.innerHTML = `<h5 class="mb-3">Lembretes para ${dataFormatada}</h5>`;

if (lembretes.length === 0) {
    container.innerHTML += '<p class="text-muted">Nenhum lembrete para esta data.</p>';
} else {
    lembretes.forEach(lembrete => {
        const tipoTag = lembrete.tipo_perfil === 'personal' ? 
            '<span class="lembrete-tag lembrete-tag-personal">Pessoal</span>' : 
            '<span class="lembrete-tag lembrete-tag-business">Empresarial</span>';
        
        container.innerHTML += `
        <div class="card mb-2">
            <div class="card-body">
                <h6 class="card-title">${lembrete.titulo}</h6>
                <div>${tipoTag}</div>
            </div>
        </div>
        `;
    });
    
    // Adiciona botão para adicionar novo lembrete nesta data
    container.innerHTML += `
    <div class="text-center mt-3">
        <button class="btn btn-sm btn-success btn-adicionar-lembrete-data" data-data="${dataFormatada}">
            <i class="bi bi-plus-circle"></i> Adicionar lembrete para esta data
        </button>
    </div>
    `;
    
    // Adiciona evento para o botão
    setTimeout(() => {
        const btnAdicionarData = document.querySelector('.btn-adicionar-lembrete-data');
        if (btnAdicionarData) {
            btnAdicionarData.addEventListener('click', function() {
                const data = this.dataset.data;
                const partes = data.split('/');
                
                // Formatar a data para o formato do input (YYYY-MM-DD)
                const dataFormatada = `${partes[2]}-${partes[1].padStart(2, '0')}-${partes[0].padStart(2, '0')}`;
                
                // Fechar o modal atual
                const modalDetalhes = bootstrap.Modal.getInstance(document.getElementById('modalDetalhesLembrete'));
                modalDetalhes.hide();
                
                // Abrir o modal de adicionar lembrete com a data preenchida
                document.getElementById('lembrete-data').value = dataFormatada;
                const modalAddLembrete = new bootstrap.Modal(document.getElementById('modalAddLembrete'));
                modalAddLembrete.show();
            });
        }
    }, 100);
}

// Abre o modal
const modalDetalhesLembrete = new bootstrap.Modal(document.getElementById('modalDetalhesLembrete'));
modalDetalhesLembrete.show();
}
</script>
{% endblock %}