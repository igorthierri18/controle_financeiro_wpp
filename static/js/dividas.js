// dividas.js - Script completo corrigido
// Autor: Claude
// Data: Maio 2025

// Variáveis globais
let perfilAtual = 'pessoal';
let dividaParaExcluir = null;
let rendaMensal = 0;
let tipoAtivo = 'all';
let planoUsuario = 'gratuito'; // Padrão é 'gratuito', será atualizado na inicialização

// Ícones para tipos de dívida
const debtIcons = {
    'emprestimo': 'bi-cash-coin',
    'cartao_credito': 'bi-credit-card',
    'financiamento': 'bi-house-door',
    'outros': 'bi-currency-exchange'
};

// Cores para tipos de dívida
const debtColors = {
    'emprestimo': '#6f42c1',       // Roxo
    'cartao_credito': '#e83e8c',   // Rosa
    'financiamento': '#20c997',    // Verde água
    'outros': '#6c757d'            // Cinza
};

// Nomes para exibição dos tipos de dívida
const debtTypeNames = {
    'emprestimo': 'Empréstimo',
    'cartao_credito': 'Cartão de Crédito',
    'financiamento': 'Financiamento',
    'outros': 'Outros'
};

// Mapeamento entre o ID da aba e o tipo de dívida
const tiposDivida = {
    'loans': 'emprestimo',
    'credit': 'cartao_credito',
    'finance': 'financiamento',
    'all': 'todos'
};

// Função para buscar a renda mensal do usuário
async function buscarRendaMensal() {
    try {
        const response = await fetch('/api/usuario/renda');
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Obtém a renda diretamente do objeto de resposta
        rendaMensal = data.renda || 0;
        
        console.log('Renda mensal carregada:', formatarMoeda(rendaMensal));
        
        // Depois de obter a renda, atualiza o resumo
        if (rendaMensal > 0) {
            // Recarrega as dívidas para atualizar o cálculo de comprometimento
            carregarDividas();
        }
    } catch (error) {
        console.error('Erro ao buscar renda mensal:', error);
        rendaMensal = 0; // Define valor padrão em caso de erro
    }
}

// Função para buscar o plano do usuário
async function buscarPlanoUsuario() {
    try {
        const response = await fetch('/api/usuario/perfil');
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        planoUsuario = data.plano || 'gratuito';
        
        console.log('Plano do usuário:', planoUsuario);
        
        // Configura a interface com base no plano
        configurarInterfacePlano();
        
        return planoUsuario;
    } catch (error) {
        console.error('Erro ao buscar plano do usuário:', error);
        // Em caso de erro, assume plano gratuito por segurança
        planoUsuario = 'gratuito';
        configurarInterfacePlano();
        return 'gratuito';
    }
}

// Função para configurar a interface com base no plano do usuário
function configurarInterfacePlano() {
    const isPlanoGratuito = planoUsuario === 'gratuito';
    const profileBusiness = document.getElementById('profile-business');
    
    // Configura o seletor de perfil empresarial
    if (profileBusiness) {
        if (isPlanoGratuito) {
            // Desabilita o perfil empresarial para plano gratuito
            profileBusiness.classList.add('disabled');
            profileBusiness.removeEventListener('click', alterarParaPerfilEmpresarial);
            profileBusiness.addEventListener('click', mostrarModalUpgrade);
        } else {
            // Habilita para plano premium
            profileBusiness.classList.remove('disabled');
            profileBusiness.removeEventListener('click', mostrarModalUpgrade);
            profileBusiness.addEventListener('click', alterarParaPerfilEmpresarial);
        }
    }
    
    // Configura os selects de tipo de perfil nos formulários
    const perfilSelect = document.getElementById('divida-tipo-perfil');
    const editarPerfilSelect = document.getElementById('editar-divida-tipo-perfil');
    
    if (perfilSelect) {
        // Opção empresarial no formulário de adicionar
        const opcaoEmpresarial = perfilSelect.querySelector('option[value="empresarial"]');
        if (opcaoEmpresarial) {
            opcaoEmpresarial.disabled = isPlanoGratuito;
            if (isPlanoGratuito) {
                opcaoEmpresarial.textContent = 'Empresarial (Premium)';
            } else {
                opcaoEmpresarial.textContent = 'Empresarial';
            }
        }
    }
    
    if (editarPerfilSelect) {
        // Opção empresarial no formulário de editar
        const opcaoEmpresarial = editarPerfilSelect.querySelector('option[value="empresarial"]');
        if (opcaoEmpresarial) {
            opcaoEmpresarial.disabled = isPlanoGratuito;
            if (isPlanoGratuito) {
                opcaoEmpresarial.textContent = 'Empresarial (Premium)';
            } else {
                opcaoEmpresarial.textContent = 'Empresarial';
            }
        }
    }
    
    // Se estiver no perfil empresarial e o plano mudar para gratuito, volta para o perfil pessoal
    if (isPlanoGratuito && perfilAtual === 'empresarial') {
        perfilAtual = 'pessoal';
        const profilePersonal = document.getElementById('profile-personal');
        if (profilePersonal) {
            profilePersonal.classList.add('active');
            if (profileBusiness) profileBusiness.classList.remove('active');
        }
        carregarDividas();
    }
}

// Função para mostrar o modal de upgrade para premium
function mostrarModalUpgrade() {
    const modalUpgrade = new bootstrap.Modal(document.getElementById('modalUpgrade'));
    modalUpgrade.show();
}

// Função para alterar para o perfil empresarial
function alterarParaPerfilEmpresarial() {
    // Somente permita se for plano premium
    if (planoUsuario !== 'gratuito') {
        perfilAtual = 'empresarial';
        document.getElementById('profile-business').classList.add('active');
        document.getElementById('profile-personal').classList.remove('active');
        carregarDividas();
    } else {
        mostrarModalUpgrade();
    }
}

// Função para atualizar o texto dos botões de adicionar com base na aba ativa
function atualizarBotaoAdicionar() {
    const addButtonDesktop = document.getElementById('addButtonDesktop');
    const addButtonMobile = document.getElementById('addButtonMobile');
    const centeredButton = document.getElementById('centeredButton');
    const modalTitle = document.getElementById('modalAddDividaLabel');
    const dividaTipoSelect = document.getElementById('divida-tipo');
    
    let labelText, titleText, tipoValue;
    
    switch (tipoAtivo) {
        case 'loans':
            labelText = 'Adicionar Empréstimo';
            titleText = 'Adicionar Novo Empréstimo';
            tipoValue = 'emprestimo';
            break;
        case 'credit':
            labelText = 'Adicionar Cartão de Crédito';
            titleText = 'Adicionar Novo Cartão de Crédito';
            tipoValue = 'cartao_credito';
            break;
        case 'finance':
            labelText = 'Adicionar Financiamento';
            titleText = 'Adicionar Novo Financiamento';
            tipoValue = 'financiamento';
            break;
        default:
            labelText = 'Adicionar Dívida';
            titleText = 'Adicionar Nova Dívida';
            tipoValue = '';
    }
    
    // Atualiza os botões desktop e mobile
    if (addButtonDesktop) {
        addButtonDesktop.setAttribute('aria-label', labelText);
        addButtonDesktop.setAttribute('title', labelText);
    }
    
    if (addButtonMobile) {
        addButtonMobile.setAttribute('aria-label', labelText);
        addButtonMobile.setAttribute('title', labelText);
    }

    // Atualiza o botão centralizado
    if (centeredButton) {
        centeredButton.setAttribute('aria-label', labelText);
        centeredButton.setAttribute('title', labelText);
    }
    
    // Atualiza o título do modal
    if (modalTitle) {
        modalTitle.textContent = titleText;
    }
    
    // Pré-seleciona o tipo de dívida no formulário
    if (dividaTipoSelect && tipoValue) {
        dividaTipoSelect.value = tipoValue;
    }
}

// Função para atualizar o resumo com barra de progresso para comprometimento
function atualizarResumo(dividas) {
    // Calcula totais
    const totalDividas = dividas.reduce((total, divida) => total + (divida.valor_total - divida.valor_pago), 0);
    
    // Calcula parcelas mensais (simplificado)
    let parcelasMensais = 0;
    dividas.forEach(divida => {
        if (divida.status !== 'quitada') {
            // Calcula parcelas baseado no valor restante e parcelas restantes
            const valorRestante = divida.valor_total - divida.valor_pago;
            const parcelasRestantes = divida.parcelas_total - divida.parcelas_pagas;
            
            if (parcelasRestantes > 0) {
                parcelasMensais += valorRestante / parcelasRestantes;
            }
        }
    });
    
    // Calcula comprometimento baseado na renda mensal do usuário
    const comprometimento = rendaMensal > 0 ? (parcelasMensais / rendaMensal) * 100 : 0;
    
    // Atualiza os valores na tela
    document.getElementById('total-dividas').textContent = formatarMoeda(totalDividas);
    document.getElementById('parcelas-mensais').textContent = formatarMoeda(parcelasMensais);
    document.getElementById('percentual-comprometimento').textContent = `${comprometimento.toFixed(1)}%`;
    
    // Muda a cor do comprometimento com base no percentual
    const comprometimentoElement = document.getElementById('percentual-comprometimento');
    const comprometimentoBar = document.querySelector('#comprometimento-barra .progress-inner');
    
    if (comprometimento > 40) {
        comprometimentoElement.style.color = '#dc3545'; // vermelho para alto comprometimento
        if (comprometimentoBar) comprometimentoBar.style.backgroundColor = '#dc3545';
    } else if (comprometimento > 30) {
        comprometimentoElement.style.color = '#fd7e14'; // laranja para médio comprometimento
        if (comprometimentoBar) comprometimentoBar.style.backgroundColor = '#fd7e14';
    } else {
        comprometimentoElement.style.color = '#29A143'; // verde para baixo comprometimento
        if (comprometimentoBar) comprometimentoBar.style.backgroundColor = '#29A143';
    }
    
    // Atualiza a barra de progresso
    if (comprometimentoBar) {
        comprometimentoBar.style.width = `${Math.min(comprometimento, 100)}%`;
    }
}

// Quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    // Inicialização do componente de dívidas
    inicializarComponenteDividas();
    
    // Busca o plano do usuário
    buscarPlanoUsuario();
    
    // Inicializa os campos de data para hoje
    document.getElementById('divida-data-inicio').valueAsDate = new Date();
    document.getElementById('pagamento-data').valueAsDate = new Date();
    
    // Calcula data de fim (1 ano a partir de hoje)
    const dataFim = new Date();
    dataFim.setFullYear(dataFim.getFullYear() + 1);
    document.getElementById('divida-data-fim').valueAsDate = dataFim;
    
    // Seletor de perfil
    document.getElementById('profile-personal').addEventListener('click', function() {
        perfilAtual = 'pessoal';
        document.getElementById('profile-personal').classList.add('active');
        const profileBusiness = document.getElementById('profile-business');
        if (profileBusiness) profileBusiness.classList.remove('active');
        carregarDividas();
    });
    
    // Botão para salvar nova dívida
    document.getElementById('btn-salvar-divida').addEventListener('click', function() {
        const form = document.getElementById('form-add-divida');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Verifica se está tentando adicionar uma dívida empresarial com plano gratuito
        const tipoPerfilSelect = document.getElementById('divida-tipo-perfil');
        if (tipoPerfilSelect && tipoPerfilSelect.value === 'empresarial' && planoUsuario === 'gratuito') {
            mostrarModalUpgrade();
            return;
        }
        
        // Captura os dados do formulário
        const formData = new FormData(form);
        const divida = {};
        
        formData.forEach((value, key) => {
            if (['valor_total', 'valor_pago', 'taxa_juros', 'parcelas_total', 'parcelas_pagas'].includes(key)) {
                divida[key] = parseFloat(value) || 0;
            } else {
                divida[key] = value;
            }
        });
        
        // Adiciona o perfil atual
        divida.tipo_perfil = perfilAtual;
        
        // Envia para a API
        criarDivida(divida);
    });
    
    // Botões para as abas de tipo de dívida
    document.querySelectorAll('#debt-type-tabs .nav-link').forEach(tab => {
        tab.addEventListener('click', function(event) {
            const novoTipo = this.id.replace('-tab', '');
            if (novoTipo !== tipoAtivo) {
                tipoAtivo = novoTipo;
                atualizarBotaoAdicionar();
            }
        });
        
        // Também adicionamos o evento bootstrap 'shown.bs.tab' para garantir que seja executado
        tab.addEventListener('shown.bs.tab', function(event) {
            const novoTipo = event.target.id.replace('-tab', '');
            tipoAtivo = novoTipo;
            atualizarBotaoAdicionar();
            filtrarDividasPorTipo(tipoAtivo);
        });
    });
    
    // Botão de confirmação de exclusão
    document.getElementById('btn-confirmar-exclusao').addEventListener('click', function() {
        if (dividaParaExcluir) {
            excluirDivida(dividaParaExcluir);
        }
    });
    
    // Botão para registrar pagamento
    document.getElementById('btn-confirmar-pagamento').addEventListener('click', function() {
        const form = document.getElementById('form-registrar-pagamento');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Captura os dados do formulário
        const formData = new FormData(form);
        const pagamento = {};
        
        formData.forEach((value, key) => {
            if (key === 'valor') {
                pagamento[key] = parseFloat(value);
            } else {
                pagamento[key] = value;
            }
        });
        
        // Registra o pagamento
        registrarPagamento(pagamento);
    });
    
    // Botão para atualizar dívida
    document.getElementById('btn-atualizar-divida').addEventListener('click', function() {
        const form = document.getElementById('form-editar-divida');
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }
        
        // Verifica se está tentando editar uma dívida para perfil empresarial com plano gratuito
        const tipoPerfilSelect = document.getElementById('editar-divida-tipo-perfil');
        if (tipoPerfilSelect && tipoPerfilSelect.value === 'empresarial' && planoUsuario === 'gratuito') {
            mostrarModalUpgrade();
            return;
        }
        
        // Captura os dados do formulário
        const formData = new FormData(form);
        const divida = {};
        const id = document.getElementById('editar-divida-id').value;
        
        formData.forEach((value, key) => {
            if (['valor_total', 'valor_pago', 'parcelas_total', 'parcelas_pagas'].includes(key)) {
                divida[key] = parseFloat(value) || 0;
            } else if (key !== 'id') {
                divida[key] = value;
            }
        });
        
        // Atualiza a dívida
        atualizarDivida(id, divida);
    });
    
    // Configura o botão inicial com base na aba ativa
    atualizarBotaoAdicionar();
    
    // Busca a renda mensal do usuário primeiro
    buscarRendaMensal();
    
    // Carrega as dívidas iniciais após um breve atraso para garantir que a renda foi buscada
    setTimeout(() => {
        carregarDividas();
    }, 100);
});

// Função para inicializar o componente de dívidas com as melhorias solicitadas
function inicializarComponenteDividas() {
    // 1. Adicionar elemento para barra de progresso do comprometimento
    const comprometimentoElement = document.querySelector('#dividas-resumo .col-md-4:last-child .debt-body');
    
    if (comprometimentoElement && !document.getElementById('comprometimento-barra')) {
        // Adicionar a barra de progresso após o valor percentual (verificar se já não existe)
        const barraProgresso = document.createElement('div');
        barraProgresso.className = 'debt-progress-bar mt-2';
        barraProgresso.id = 'comprometimento-barra';
        barraProgresso.innerHTML = '<div class="progress-inner" style="width: 0%;"></div>';
        
        // Inserir após o texto de percentual
        const percentualElement = comprometimentoElement.querySelector('.fw-bold');
        if (percentualElement) {
            percentualElement.parentNode.insertBefore(barraProgresso, percentualElement.nextSibling);
        } else {
            comprometimentoElement.appendChild(barraProgresso);
        }
    }
    
    // 2. Ajustar navegação mobile dos sub-menus (cartão, financiamento, empréstimos)
    const navTabs = document.querySelector('#debt-type-tabs');
    
    if (navTabs) {
        // Ajustar o estilo para desktop e mobile
        navTabs.classList.add('flex-wrap');
        
        // Ajustar o contêiner do menu para permitir o botão centralizado
        const navContainer = navTabs.parentElement;
        if (navContainer && !navContainer.classList.contains('debt-type-nav-container')) {
            navContainer.classList.add('debt-type-nav-container');
            
            // 3. Remover botão existente para evitar duplicação
            const existingButton = document.getElementById('centeredButton');
            if (existingButton) {
                existingButton.remove();
            }
            
            // Criar um botão centralizado no meio do menu nav
            const centeredButton = document.createElement('button');
            centeredButton.className = 'fab-button centered-fab-button';
            centeredButton.id = 'centeredButton';
            centeredButton.setAttribute('data-bs-toggle', 'modal');
            centeredButton.setAttribute('data-bs-target', '#modalAddDivida');
            centeredButton.innerHTML = '<i class="bi bi-plus"></i>';
            
            // Adicionar o botão centralizado
            navContainer.appendChild(centeredButton);
            
            // Adicionar eventos ao botão centralizado
            centeredButton.addEventListener('click', function() {
                atualizarBotaoAdicionar();
            });
        }
    }
    
    // 4. Ajustar layout do sub-menu para mobile
    const menuItems = document.querySelectorAll('#debt-type-tabs .nav-item');
    if (menuItems.length > 0) {
        // Adiciona a classe para layout horizontal em mobile
        menuItems.forEach(item => {
            item.classList.add('d-flex');
            
            // Ajustar o estilo do link para ocupar menos espaço em mobile
            const link = item.querySelector('.nav-link');
            if (link) {
                link.classList.add('px-3', 'py-2', 'me-2');
            }
        });
    }
}

// Função para formatar moeda
function formatarMoeda(valor) {
    return 'R$ ' + valor.toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

// Função para formatar data
function formatarData(data) {
    if (!data) return "";
    
    const dataObj = new Date(data);
    return dataObj.toLocaleDateString('pt-BR');
}

// Função para carregar as dívidas
async function carregarDividas() {
    try {
        // Mostra indicador de carregamento
        document.getElementById('all-debts-list').innerHTML = `
            <div class="col-12 text-center my-5">
                <div class="spinner-border text-success" role="status">
                    <span class="visually-hidden">Carregando...</span>
                </div>
                <p class="mt-2">Carregando dívidas...</p>
            </div>
        `;
        
        // Adicionar timeout para não ficar esperando infinitamente
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos de timeout
        
        // Faz a chamada para a API
        let url = `/api/dividas?tipo_perfil=${perfilAtual}`;
        
        // Se estivermos em uma visualização específica (não em "Todos"), adiciona o filtro de tipo
        if (tipoAtivo !== 'all' && tiposDivida[tipoAtivo] !== 'todos') {
            url += `&tipo=${tiposDivida[tipoAtivo]}`;
        }
        
        const response = await fetch(url, {signal: controller.signal});
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const dividas = await response.json();
        
        // Atualiza a interface
        renderizarDividas(dividas);
        atualizarResumo(dividas);
        
    } catch (error) {
        console.error('Erro ao carregar dívidas:', error);
        
        // Se houver erro, mostrar mensagem e dados vazios para não ficar carregando infinitamente
        document.getElementById('all-debts-list').innerHTML = `
            <div class="col-12">
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    Não foi possível carregar as dívidas. Clique para tentar novamente.
                    <button class="btn btn-sm btn-outline-warning ms-3" onclick="carregarDividas()">
                        <i class="bi bi-arrow-clockwise"></i> Recarregar
                    </button>
                </div>
            </div>
        `;
        
        // Mostrar números vazios em vez de ficar carregando
        document.getElementById('total-dividas').textContent = 'R$ 0,00';
        document.getElementById('parcelas-mensais').textContent = 'R$ 0,00';
        document.getElementById('percentual-comprometimento').textContent = '0%';
        
        // Atualiza barra de progresso
        const comprometimentoBar = document.querySelector('#comprometimento-barra .progress-inner');
        if (comprometimentoBar) {
            comprometimentoBar.style.width = '0%';
        }
    }
}

// Função para renderizar as dívidas na tela
function renderizarDividas(dividas) {
    const listaDividas = document.getElementById('all-debts-list');
    const loansLista = document.getElementById('loans-list');
    const creditLista = document.getElementById('credit-list');
    const financeLista = document.getElementById('finance-list');
    
    // Limpa todas as listas
    listaDividas.innerHTML = '';
    loansLista.innerHTML = '';
    creditLista.innerHTML = '';
    financeLista.innerHTML = '';
    
    // Mostra o estado vazio se não houver dívidas
    if (dividas.length === 0) {
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('dividas-resumo').style.display = 'flex';
        
        // Também mostra estado vazio nas abas específicas
        loansLista.innerHTML = criarEmptyState('emprestimo');
        creditLista.innerHTML = criarEmptyState('cartao_credito');
        financeLista.innerHTML = criarEmptyState('financiamento');
        
        return;
    } else {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('dividas-resumo').style.display = 'flex';
    }
    
    // Contadores para verificar se cada tipo de lista está vazia
    let emprestimosCount = 0;
    let cartoesCount = 0;
    let financiamentosCount = 0;
    
    // Renderiza cada dívida
    dividas.forEach(divida => {
        // Adiciona à lista principal (todos)
        const divCol = criarCardDivida(divida);
        listaDividas.appendChild(divCol.cloneNode(true));
        
        // Adiciona a dívida à lista específica do seu tipo
        if (divida.tipo === 'emprestimo') {
            loansLista.appendChild(divCol.cloneNode(true));
            emprestimosCount++;
        } else if (divida.tipo === 'cartao_credito') {
            creditLista.appendChild(divCol.cloneNode(true));
            cartoesCount++;
        } else if (divida.tipo === 'financiamento') {
            financeLista.appendChild(divCol.cloneNode(true));
            financiamentosCount++;
        }
    });
    
    // Verifica se alguma lista específica está vazia
    if (emprestimosCount === 0) {
        loansLista.innerHTML = criarEmptyState('emprestimo');
    }
    
    if (cartoesCount === 0) {
        creditLista.innerHTML = criarEmptyState('cartao_credito');
    }
    
    if (financiamentosCount === 0) {
        financeLista.innerHTML = criarEmptyState('financiamento');
    }
    
    // Adiciona eventos aos botões
    adicionarEventosBotoes();
}

// Função para criar um estado vazio para um tipo específico
function criarEmptyState(tipo) {
    const tipoPtBr = debtTypeNames[tipo] || 'Dívidas';
    const tipoPlural = tipo === 'emprestimo' ? 'empréstimos' : 
                      (tipo === 'cartao_credito' ? 'cartões de crédito' : 
                      (tipo === 'financiamento' ? 'financiamentos' : 'dívidas'));
    
    return `
        <div class="col-12">
            <div class="empty-state" style="padding: 30px;">
                <div class="empty-state-icon" style="font-size: 36px;">
                    <i class="bi ${debtIcons[tipo] || 'bi-credit-card'}"></i>
                </div>
                <h3 class="empty-state-title" style="font-size: 18px;">Nenhum ${tipoPlural.split(' ')[0]} registrado</h3>
                <p class="empty-state-text">Você ainda não tem ${tipoPlural} cadastrados.</p>
                <button class="btn btn-success" data-bs-toggle="modal" data-bs-target="#modalAddDivida" onclick="document.getElementById('divida-tipo').value = '${tipo}'">
                    <i class="bi bi-plus-circle me-1"></i> Adicionar ${tipoPtBr}
                </button>
            </div>
        </div>
    `;
}

// Função para criar um card de dívida
function criarCardDivida(divida) {
    // Calcula a porcentagem paga
    const porcentagemPaga = (divida.valor_pago / divida.valor_total) * 100;
    const porcentagemParcelas = (divida.parcelas_pagas / divida.parcelas_total) * 100;
    
    // Determina a cor e ícone com base no tipo
    const corDivida = debtColors[divida.tipo] || '#6c757d';
    const iconeDivida = debtIcons[divida.tipo] || 'bi-cash';
    
    // Determina a classe de status
    const statusClass = `status-${divida.status}`;
    const statusText = divida.status === 'em_dia' ? 'Em Dia' : 
                     (divida.status === 'atrasado' ? 'Atrasado' : 
                     (divida.status === 'quitada' ? 'Quitado' : divida.status));
    
    // Cria o elemento da coluna
    const divCol = document.createElement('div');
    divCol.className = 'col-md-6 col-lg-4 mb-4';
    
    divCol.innerHTML = `
        <div class="debt-card">
            <div class="debt-header">
                <h5 class="debt-title">
                    <span class="icon" style="background-color: ${corDivida}">
                        <i class="bi ${iconeDivida}"></i>
                    </span>
                    ${divida.nome}
                </h5>
                <span class="debt-status ${statusClass}">${statusText}</span>
            </div>
            <div class="debt-body">
                <div class="debt-details">
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Valor Total</div>
                        <div class="debt-detail-value">${formatarMoeda(divida.valor_total)}</div>
                    </div>
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Valor Pago</div>
                        <div class="debt-detail-value">${formatarMoeda(divida.valor_pago)}</div>
                    </div>
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Valor Restante</div>
                        <div class="debt-detail-value">${formatarMoeda(divida.valor_total - divida.valor_pago)}</div>
                    </div>
                </div>
                
                <div class="debt-details">
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Início</div>
                        <div class="debt-detail-value">${formatarData(divida.data_inicio)}</div>
                    </div>
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Vencimento</div>
                        <div class="debt-detail-value">${formatarData(divida.data_fim)}</div>
                    </div>
                    <div class="debt-detail-col">
                        <div class="debt-detail-label">Taxa de Juros</div>
                        <div class="debt-detail-value">${divida.taxa_juros ? divida.taxa_juros + '% a.m.' : 'N/A'}</div>
                    </div>
                </div>
                
                <div class="debt-progress">
                    <div class="debt-detail-label">Progresso de Pagamento</div>
                    <div class="debt-progress-bar">
                        <div class="progress-inner" style="width: ${porcentagemPaga.toFixed(0)}%"></div>
                    </div>
                    <div class="debt-progress-text">
                        <span>${formatarMoeda(divida.valor_pago)}</span>
                        <span>${porcentagemPaga.toFixed(0)}%</span>
                        <span>${formatarMoeda(divida.valor_total)}</span>
                    </div>
                </div>
                
                <div class="debt-progress">
                    <div class="debt-detail-label">Parcelas Pagas</div>
                    <div class="debt-progress-bar">
                        <div class="progress-inner" style="width: ${porcentagemParcelas.toFixed(0)}%"></div>
                    </div>
                    <div class="debt-progress-text">
                        <span>${divida.parcelas_pagas} de ${divida.parcelas_total}</span>
                        <span>${porcentagemParcelas.toFixed(0)}%</span>
                    </div>
                </div>
            </div>
            <div class="debt-footer">
                <button class="btn btn-sm btn-outline-success btn-registrar-pagamento" data-id="${divida.id}">
                    <i class="bi bi-cash me-1"></i> Registrar Pagamento
                </button>
                <button class="btn btn-sm btn-outline-primary btn-editar-divida" data-id="${divida.id}">
                    <i class="bi bi-pencil"></i> Editar
                </button>
                <button class="btn btn-sm btn-outline-danger btn-excluir-divida" data-id="${divida.id}">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    return divCol;
}

// Função para filtrar dívidas por tipo
function filtrarDividasPorTipo(tipo) {
    // Se for "all", todas as dívidas já estão mostradas
    if (tipo === 'all') return;
    
    // Atualizar o botão de adicionar para refletir o tipo atual
    atualizarBotaoAdicionar();
    
    // Recarregar as dívidas filtradas para a aba atual
    carregarDividas();
}

// Função para adicionar eventos aos botões
function adicionarEventosBotoes() {
    // Botões de editar dívida
    document.querySelectorAll('.btn-editar-divida').forEach(button => {
        button.addEventListener('click', function() {
            const dividaId = this.dataset.id;
            abrirModalEditarDivida(dividaId);
        });
    });
    
    // Botões de excluir dívida
    document.querySelectorAll('.btn-excluir-divida').forEach(button => {
        button.addEventListener('click', function() {
            dividaParaExcluir = this.dataset.id;
            
            // Abre o modal de confirmação
            const modal = new bootstrap.Modal(document.getElementById('modalConfirmExcluir'));
            modal.show();
        });
    });
    
    // Botões de registrar pagamento
    document.querySelectorAll('.btn-registrar-pagamento').forEach(button => {
        button.addEventListener('click', function() {
            const dividaId = this.dataset.id;
            abrirModalRegistrarPagamento(dividaId);
        });
    });
}

// Função para abrir o modal de edição de dívida
async function abrirModalEditarDivida(dividaId) {
    try {
        // Mostrar indicador de carregamento no botão
        const botaoEditar = document.querySelector(`.btn-editar-divida[data-id="${dividaId}"]`);
        const textoOriginal = botaoEditar.innerHTML;
        botaoEditar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Carregando...`;
        botaoEditar.disabled = true;
        
        // Busca dados da dívida
        const response = await fetch(`/api/dividas/${dividaId}`);
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const divida = await response.json();
        
        // Restaura o botão
        botaoEditar.innerHTML = textoOriginal;
        botaoEditar.disabled = false;
        
        // Preenche o formulário
        document.getElementById('editar-divida-id').value = divida.id;
        document.getElementById('editar-divida-tipo').value = divida.tipo;
        document.getElementById('editar-divida-nome').value = divida.nome;
        document.getElementById('editar-divida-valor-total').value = divida.valor_total;
        document.getElementById('editar-divida-valor-pago').value = divida.valor_pago;
        document.getElementById('editar-divida-data-inicio').value = divida.data_inicio;
        document.getElementById('editar-divida-data-fim').value = divida.data_fim;
        document.getElementById('editar-divida-juros').value = divida.taxa_juros || '';
        document.getElementById('editar-divida-parcelas-total').value = divida.parcelas_total;
        document.getElementById('editar-divida-parcelas-pagas').value = divida.parcelas_pagas;
        document.getElementById('editar-divida-credor').value = divida.credor || '';
        document.getElementById('editar-divida-tipo-perfil').value = divida.tipo_perfil;
        
        // Verificar se o usuário pode editar o perfil empresarial
        if (planoUsuario === 'gratuito' && divida.tipo_perfil === 'empresarial') {
            // Impedir que o usuário gratuito altere dívidas empresariais
            mostrarModalUpgrade();
            return;
        }
        
        // Abre o modal
        const modal = new bootstrap.Modal(document.getElementById('modalEditarDivida'));
        modal.show();
        
    } catch (error) {
        console.error('Erro ao abrir modal de edição:', error);
        mostrarAlerta('danger', 'Erro ao carregar dados da dívida. Por favor, tente novamente.');
        
        // Restaura o botão em caso de erro
        const botaoEditar = document.querySelector(`.btn-editar-divida[data-id="${dividaId}"]`);
        if (botaoEditar) {
            botaoEditar.innerHTML = `<i class="bi bi-pencil"></i> Editar`;
            botaoEditar.disabled = false;
        }
    }
}

// Função para abrir o modal de registro de pagamento
function abrirModalRegistrarPagamento(dividaId) {
    // Preenche o ID da dívida no formulário
    document.getElementById('pagamento-divida-id').value = dividaId;
    
    // Define a data atual
    document.getElementById('pagamento-data').valueAsDate = new Date();
    
    // Abre o modal
    const modal = new bootstrap.Modal(document.getElementById('modalRegistrarPagamento'));
    modal.show();
}

// Função para criar uma nova dívida
async function criarDivida(divida) {
    try {
        // Mostra indicador de carregamento no botão
        const botaoSalvar = document.getElementById('btn-salvar-divida');
        const textoOriginal = botaoSalvar.innerHTML;
        botaoSalvar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...`;
        botaoSalvar.disabled = true;
        
        // Chama a API para criar a dívida
        const response = await fetch('/api/dividas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(divida)
        });
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const resposta = await response.json();
        
        console.log('Dívida criada:', resposta);
        
        // Restaura o botão
        botaoSalvar.innerHTML = textoOriginal;
        botaoSalvar.disabled = false;
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddDivida'));
        modal.hide();
        
        // Limpa o formulário
        document.getElementById('form-add-divida').reset();
        
        // Define valores padrão nos campos
        document.getElementById('divida-valor-pago').value = '0';
        document.getElementById('divida-parcelas-total').value = '1';
        document.getElementById('divida-parcelas-pagas').value = '0';
        document.getElementById('divida-data-inicio').valueAsDate = new Date();
        const dataFim = new Date();
        dataFim.setFullYear(dataFim.getFullYear() + 1);
        document.getElementById('divida-data-fim').valueAsDate = dataFim;
        
        // Recarrega as dívidas
        carregarDividas();
        
        // Feedback para o usuário
        mostrarAlerta('success', 'Dívida adicionada com sucesso!');
        
    } catch (error) {
        console.error('Erro ao criar dívida:', error);
        mostrarAlerta('danger', 'Erro ao adicionar dívida. Por favor, tente novamente.');
        
        // Restaura o botão
        const botaoSalvar = document.getElementById('btn-salvar-divida');
        botaoSalvar.innerHTML = `Adicionar Dívida`;
        botaoSalvar.disabled = false;
    }
}

// Função para excluir uma dívida
async function excluirDivida(id) {
    try {
        // Mostra indicador de carregamento no botão
        const botaoExcluir = document.getElementById('btn-confirmar-exclusao');
        const textoOriginal = botaoExcluir.innerHTML;
        botaoExcluir.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Excluindo...`;
        botaoExcluir.disabled = true;
        
        // Chama a API para excluir a dívida
        const response = await fetch(`/api/dividas/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const resposta = await response.json();
        
        console.log('Dívida excluída:', resposta);
        
        // Restaura o botão
        botaoExcluir.innerHTML = textoOriginal;
        botaoExcluir.disabled = false;
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalConfirmExcluir'));
        modal.hide();
        
        // Recarrega as dívidas
        carregarDividas();
        
        // Feedback para o usuário
        mostrarAlerta('success', 'Dívida excluída com sucesso!');
        
    } catch (error) {
        console.error('Erro ao excluir dívida:', error);
        mostrarAlerta('danger', 'Erro ao excluir dívida. Por favor, tente novamente.');
        
        // Restaura o botão
        const botaoExcluir = document.getElementById('btn-confirmar-exclusao');
        botaoExcluir.innerHTML = `Excluir`;
        botaoExcluir.disabled = false;
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalConfirmExcluir'));
        modal.hide();
    }
}

// Função para registrar um pagamento
async function registrarPagamento(pagamento) {
    try {
        // Mostra indicador de carregamento no botão
        const botaoPagamento = document.getElementById('btn-confirmar-pagamento');
        const textoOriginal = botaoPagamento.innerHTML;
        botaoPagamento.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Registrando...`;
        botaoPagamento.disabled = true;
        
        // Chama a API para registrar o pagamento
        const response = await fetch('/api/dividas/pagamento', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pagamento)
        });
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const resposta = await response.json();
        
        console.log('Pagamento registrado:', resposta);
        
        // Restaura o botão
        botaoPagamento.innerHTML = textoOriginal;
        botaoPagamento.disabled = false;
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalRegistrarPagamento'));
        modal.hide();
        
        // Limpa o formulário
        document.getElementById('form-registrar-pagamento').reset();
        document.getElementById('pagamento-data').valueAsDate = new Date();
        document.getElementById('pagamento-tipo').value = 'parcela';
        
        // Recarrega as dívidas
        carregarDividas();
        
        // Feedback para o usuário
        mostrarAlerta('success', 'Pagamento registrado com sucesso!');
        
    } catch (error) {
        console.error('Erro ao registrar pagamento:', error);
        mostrarAlerta('danger', 'Erro ao registrar pagamento. Por favor, tente novamente.');
        
        // Restaura o botão
        const botaoPagamento = document.getElementById('btn-confirmar-pagamento');
        botaoPagamento.innerHTML = `Registrar Pagamento`;
        botaoPagamento.disabled = false;
    }
}

// Função para atualizar uma dívida
async function atualizarDivida(id, divida) {
    try {
        // Mostra indicador de carregamento no botão
        const botaoAtualizar = document.getElementById('btn-atualizar-divida');
        const textoOriginal = botaoAtualizar.innerHTML;
        botaoAtualizar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Salvando...`;
        botaoAtualizar.disabled = true;
        
        // Chama a API para atualizar a dívida
        const response = await fetch(`/api/dividas/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(divida)
        });
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const resposta = await response.json();
        
        console.log('Dívida atualizada:', resposta);
        
        // Restaura o botão
        botaoAtualizar.innerHTML = textoOriginal;
        botaoAtualizar.disabled = false;
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalEditarDivida'));
        modal.hide();
        
        // Recarrega as dívidas
        carregarDividas();
        
        // Feedback para o usuário
        mostrarAlerta('success', 'Dívida atualizada com sucesso!');
        
    } catch (error) {
        console.error('Erro ao atualizar dívida:', error);
        mostrarAlerta('danger', 'Erro ao atualizar dívida. Por favor, tente novamente.');
        
        // Restaura o botão
        const botaoAtualizar = document.getElementById('btn-atualizar-divida');
        botaoAtualizar.innerHTML = `Salvar Alterações`;
        botaoAtualizar.disabled = false;
    }
}

// Função para mostrar alertas temporários
function mostrarAlerta(tipo, mensagem) {
    // Remove alertas existentes
    document.querySelectorAll('.alert-floating').forEach(alert => alert.remove());
    
    // Cria o elemento de alerta
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show alert-floating`;
    alerta.setAttribute('role', 'alert');
    alerta.innerHTML = `
        <i class="bi bi-${tipo === 'success' ? 'check-circle' : 
                           tipo === 'danger' ? 'exclamation-octagon' : 
                           'info-circle'}-fill me-2"></i>
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
    `;
    
    // Adiciona ao corpo do documento
    document.body.appendChild(alerta);
    
    // Remove depois de 5 segundos
    setTimeout(() => {
        alerta.classList.remove('show');
        setTimeout(() => {
            alerta.remove();
        }, 300);
    }, 5000);
}