// Variáveis globais
let periodoAtual = 'semana';
let dadosGrafico = [];
let perfilAtual = 'pessoal';

// Funções de formatação
function formatarData(dataStr) {
    const data = new Date(dataStr);
    return data.toLocaleDateString('pt-BR');
}

function formatarValor(valor) {
    if (!valor && valor !== 0) return 'R$ 0,00';
    return 'R$ ' + parseFloat(valor).toFixed(2).replace('.', ',');
}

// Atualiza os indicadores de tendência
function atualizarTendencias(tendencias) {
    if (!tendencias) return;
    
    // Despesas
    const trendDespesas = document.getElementById('trend-despesas');
    if (tendencias.despesas > 0) {
        trendDespesas.className = 'trend-indicator trend-up';
        trendDespesas.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-despesas-valor">${tendencias.despesas.toFixed(1).replace('.', ',')}%</span>`;
    } else {
        trendDespesas.className = 'trend-indicator trend-down';
        trendDespesas.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-despesas-valor">${Math.abs(tendencias.despesas).toFixed(1).replace('.', ',')}%</span>`;
    }
    
    // Receitas
    const trendReceitas = document.getElementById('trend-receitas');
    if (tendencias.receitas > 0) {
        trendReceitas.className = 'trend-indicator trend-up';
        trendReceitas.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-receitas-valor">${tendencias.receitas.toFixed(1).replace('.', ',')}%</span>`;
    } else {
        trendReceitas.className = 'trend-indicator trend-down';
        trendReceitas.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-receitas-valor">${Math.abs(tendencias.receitas).toFixed(1).replace('.', ',')}%</span>`;
    }
    
    // Saldo
    const trendSaldo = document.getElementById('trend-saldo');
    if (tendencias.saldo > 0) {
        trendSaldo.className = 'trend-indicator trend-up';
        trendSaldo.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-saldo-valor">${tendencias.saldo.toFixed(1).replace('.', ',')}%</span>`;
    } else {
        trendSaldo.className = 'trend-indicator trend-down';
        trendSaldo.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-saldo-valor">${Math.abs(tendencias.saldo).toFixed(1).replace('.', ',')}%</span>`;
    }
    
    // Economia
    const trendEconomia = document.getElementById('trend-economia');
    if (tendencias.economia > 0) {
        trendEconomia.className = 'trend-indicator trend-up';
        trendEconomia.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-economia-valor">${tendencias.economia.toFixed(1).replace('.', ',')}%</span>`;
    } else {
        trendEconomia.className = 'trend-indicator trend-down';
        trendEconomia.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-economia-valor">${Math.abs(tendencias.economia).toFixed(1).replace('.', ',')}%</span>`;
    }
}

// Carrega os dados com base no período selecionado
async function carregarDados(periodo = 'semana') {
    periodoAtual = periodo;
    
    // Atualiza os subtítulos com o período selecionado
    let textoPeríodo = 'nesta semana';
    if (periodo === 'dia') textoPeríodo = 'hoje';
    if (periodo === 'mes') textoPeríodo = 'neste mês';
    if (periodo === 'ano') textoPeríodo = 'neste ano';
    if (periodo === 'custom') textoPeríodo = 'no período selecionado';
    
    document.getElementById('period-subtitle').textContent = textoPeríodo;
    document.getElementById('period-subtitle-receitas').textContent = textoPeríodo;
    document.getElementById('period-subtitle-saldo').textContent = textoPeríodo;
    document.getElementById('period-subtitle-economia').textContent = textoPeríodo;
    
    try {
        // Exibe indicador de carregamento
        mostrarCarregamento(true);
        
        // Prepara os parâmetros da requisição
        let params = `periodo=${periodo}&tipo_perfil=${perfilAtual}`;
        
        // Se for período personalizado, adiciona as datas
        if (periodo === 'custom') {
            const dataInicio = document.getElementById('date-inicio').value;
            const dataFim = document.getElementById('date-fim').value;
            if (dataInicio && dataFim) {
                params += `&data_inicio=${dataInicio}&data_fim=${dataFim}`;
            }
        }
        
        // Carrega o resumo
        const resumoResponse = await fetch(`/api/resumo?${params}`);
        if (!resumoResponse.ok) {
            throw new Error('Erro ao carregar resumo financeiro');
        }
        const resumo = await resumoResponse.json();
        
        // Atualiza os totais
        document.getElementById('total-despesas').textContent = formatarValor(resumo.total_despesas);
        document.getElementById('total-receitas').textContent = formatarValor(resumo.total_receitas);
        document.getElementById('total-saldo').textContent = formatarValor(resumo.saldo);
        
        // Calcula e atualiza a economia percentual
        const economiaPercentual = resumo.economia_percentual || 0;
        document.getElementById('percentual-economia').textContent = `${economiaPercentual.toFixed(1).replace('.', ',')}%`;
        
        // Atualiza os indicadores de tendência
        if (resumo.tendencias) {
            atualizarTendencias(resumo.tendencias);
        }
        
        // Carrega o gráfico por categoria
        const graficoResponse = await fetch(`/api/grafico/por_categoria?${params}`);
        if (!graficoResponse.ok) {
            throw new Error('Erro ao carregar dados do gráfico');
        }
        const dadosGrafico = await graficoResponse.json();
        
        // Atualiza o gráfico
        atualizarGrafico(dadosGrafico);
        
        // Carrega as despesas
        const despesasResponse = await fetch(`/api/despesas?${params}`);
        if (!despesasResponse.ok) {
            throw new Error('Erro ao carregar despesas');
        }
        const despesas = await despesasResponse.json();
        
        // Carrega as receitas
        const receitasResponse = await fetch(`/api/receitas?${params}`);
        if (!receitasResponse.ok) {
            throw new Error('Erro ao carregar receitas');
        }
        const receitas = await receitasResponse.json();
        
        // Atualiza as listas de transações
        atualizarListaTransacoes(despesas, receitas);
        
        // Carrega lembretes próximos
        await carregarLembretesProximos();
        
        // Carrega orçamentos
        await carregarOrcamentos();
        
        // Carrega dívidas
        await carregarDividas();
        
        // Carrega metas
        await carregarMetas();
        
        // Carrega calendário
        await carregarCalendario();
        
        // Esconde indicador de carregamento
        mostrarCarregamento(false);
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        // Mostra mensagem de erro
        mostrarErro('Ocorreu um erro ao carregar os dados. Por favor, tente novamente.');
        // Esconde indicador de carregamento
        mostrarCarregamento(false);
    }
}

// Função para mostrar/esconder indicador de carregamento
function mostrarCarregamento(exibir) {
    const loader = document.getElementById('loading-indicator');
    if (loader) {
        loader.style.display = exibir ? 'flex' : 'none';
    }
}

// Função para mostrar mensagens de erro
function mostrarErro(mensagem) {
    // Verifica se já existe um alerta de erro
    const alertaExistente = document.querySelector('.alert-danger');
    if (alertaExistente) {
        alertaExistente.remove();
    }
    
    // Cria o elemento de alerta
    const alerta = document.createElement('div');
    alerta.className = 'alert alert-danger alert-dismissible fade show';
    alerta.role = 'alert';
    alerta.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
    `;
    
    // Adiciona o alerta no topo da página
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(alerta, container.firstChild);
    
    // Remove o alerta após 5 segundos
    setTimeout(() => {
        alerta.classList.remove('show');
        setTimeout(() => alerta.remove(), 300);
    }, 5000);
}

// Função para carregar lembretes próximos
async function carregarLembretesProximos() {
    try {
        const resposta = await fetch(`/api/lembretes?tipo_perfil=${perfilAtual}&concluido=0`);
        if (!resposta.ok) {
            throw new Error('Erro ao carregar lembretes');
        }
        
        const lembretes = await resposta.json();
        
        // Ordena por data mais próxima
        lembretes.sort((a, b) => new Date(a.data) - new Date(b.data));
        
        // Limita a exibir apenas os 3 próximos
        const proximosLembretes = lembretes.slice(0, 3);
        
        // Atualiza a lista de lembretes
        const container = document.getElementById('proximos-lembretes');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (proximosLembretes.length === 0) {
            container.innerHTML = `
            <div class="list-group-item text-center py-4">
                <i class="bi bi-check-circle text-success" style="font-size: 24px;"></i>
                <p class="mt-2">Não há lembretes próximos</p>
            </div>`;
            return;
        }
        
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        proximosLembretes.forEach(lembrete => {
            const dataLembrete = new Date(lembrete.data);
            dataLembrete.setHours(0, 0, 0, 0);
            
            // Calcula dias restantes
            const diffTime = dataLembrete - hoje;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            // Define a cor do badge baseado na proximidade
            let badgeClass = 'bg-success';
            let textoData = `${diffDays} dias`;
            
            if (diffDays < 0) {
                badgeClass = 'bg-danger';
                textoData = 'Atrasado';
            } else if (diffDays === 0) {
                badgeClass = 'bg-warning';
                textoData = 'Hoje';
            } else if (diffDays <= 3) {
                badgeClass = 'bg-danger';
            } else if (diffDays <= 7) {
                badgeClass = 'bg-warning';
            }
            
            container.innerHTML += `
            <div class="list-group-item d-flex justify-content-between align-items-start">
                <div class="ms-2 me-auto">
                    <div class="fw-bold">${lembrete.titulo}</div>
                    <small class="text-muted">${formatarData(lembrete.data)}</small>
                    ${lembrete.valor ? `<small class="d-block">${formatarValor(lembrete.valor)}</small>` : ''}
                </div>
                <span class="badge ${badgeClass} rounded-pill">${textoData}</span>
            </div>`;
        });
        
    } catch (error) {
        console.error('Erro ao carregar lembretes:', error);
        // Não exibe erro para o usuário, apenas registra no console
    }
}

// Função para carregar orçamentos
async function carregarOrcamentos() {
    try {
        const response = await fetch(`/api/orcamentos?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar orçamentos');
        }
        
        const orcamentos = await response.json();
        
        // Container principal
        const container = document.getElementById('lista-orcamentos');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Container no modal
        const containerModal = document.getElementById('lista-orcamentos-modal');
        if (containerModal) {
            containerModal.innerHTML = '';
        }
        
        if (!orcamentos || orcamentos.length === 0) {
            container.innerHTML = `
            <div class="text-center py-3">
                <p class="text-muted">Nenhum orçamento cadastrado</p>
                <button class="btn btn-sm btn-outline-success" data-bs-toggle="modal" data-bs-target="#modalBudget">
                    <i class="bi bi-plus-circle me-1"></i>Adicionar Orçamento
                </button>
            </div>`;
            
            if (containerModal) {
                containerModal.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-cash-stack text-muted" style="font-size: 32px;"></i>
                    <p class="mt-2 mb-3">Nenhum orçamento cadastrado</p>
                    <button class="btn btn-success btn-sm" id="btn-novo-orcamento-tab">
                        <i class="bi bi-plus-circle me-1"></i>Criar Orçamento
                    </button>
                </div>`;
                
                // Event listener para o botão
                document.getElementById('btn-novo-orcamento-tab')?.addEventListener('click', function() {
                    document.getElementById('tab-novo-orcamento')?.click();
                });
            }
            
            return;
        }
        
        // Cores para diferentes categorias
        const coresCategorias = {
            'alimentação': '#FFA726',
            'transporte': '#42A5F5',
            'moradia': '#66BB6A',
            'saúde': '#EC407A',
            'educação': '#7E57C2',
            'lazer': '#26A69A',
            'vestuário': '#FF7043',
            'outros': '#78909C'
        };
        
        // Emojis para diferentes categorias
        const emojisCategorias = {
            'alimentação': '<i class="bi bi-cart"></i>',
            'transporte': '<i class="bi bi-car-front"></i>',
            'moradia': '<i class="bi bi-house"></i>',
            'saúde': '<i class="bi bi-heart-pulse"></i>',
            'educação': '<i class="bi bi-book"></i>',
            'lazer': '<i class="bi bi-controller"></i>',
            'vestuário': '<i class="bi bi-bag"></i>',
            'outros': '<i class="bi bi-three-dots"></i>'
        };
        
        // Cria os widgets de orçamento
        orcamentos.forEach(orcamento => {
            // Busca o valor gasto para este orçamento
            const valorGasto = orcamento.valor_gasto || 0;
            const valorLimite = orcamento.valor_limite || 0;
            
            const corCategoria = coresCategorias[orcamento.categoria] || '#78909C';
            const emojiCategoria = emojisCategorias[orcamento.categoria] || '<i class="bi bi-three-dots"></i>';
            
            // Cálculo de porcentagem
            const porcentagem = Math.min(100, Math.round((valorGasto / valorLimite) * 100)) || 0;
            
            // Define a cor da barra de progresso
            let corBarra = '#66BB6A'; // Verde por padrão
            if (porcentagem >= 90) {
                corBarra = '#dc3545'; // Vermelho se estiver >= 90%
            } else if (porcentagem >= 75) {
                corBarra = '#ffc107'; // Amarelo se estiver >= 75%
            }
            
            // Widget principal
            container.innerHTML += `
            <div class="widget-item">
                <div class="widget-icon" style="background-color: ${corCategoria};">
                    ${emojiCategoria}
                </div>
                <div>
                    <div class="widget-title">${orcamento.categoria.charAt(0).toUpperCase() + orcamento.categoria.slice(1)}</div>
                    <div class="widget-subtitle">${orcamento.periodicidade.charAt(0).toUpperCase() + orcamento.periodicidade.slice(1)}</div>
                    <div class="budget-progress">
                        <div class="budget-bar" style="width: ${porcentagem}%; background-color: ${corBarra};"></div>
                    </div>
                </div>
                <div class="widget-value">
                    <div>${formatarValor(valorGasto)}/${formatarValor(valorLimite)}</div>
                    <small class="text-muted">${porcentagem}%</small>
                </div>
            </div>`;
            
            // Item na lista de orçamentos do modal
            if (containerModal) {
                containerModal.innerHTML += `
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" data-id="${orcamento.id}">
                    <div>
                        <h6 class="mb-1">${orcamento.categoria.charAt(0).toUpperCase() + orcamento.categoria.slice(1)}</h6>
                        <p class="mb-1 small text-muted">${formatarValor(orcamento.valor_limite)} / ${orcamento.periodicidade.charAt(0).toUpperCase() + orcamento.periodicidade.slice(1)}</p>
                        <div class="progress" style="height: 5px; width: 150px;">
                            <div class="progress-bar" role="progressbar" style="width: ${porcentagem}%; background-color: ${corBarra}"></div>
                        </div>
                    </div>
                    <div>
                        <button class="btn btn-sm btn-outline-primary me-1 btn-editar-orcamento" data-id="${orcamento.id}">Editar</button>
                        <button class="btn btn-sm btn-outline-danger btn-excluir-orcamento" data-id="${orcamento.id}">Excluir</button>
                    </div>
                </div>`;
            }
        });
        
        // Adiciona event listeners para botões de editar e excluir
        document.querySelectorAll('.btn-editar-orcamento').forEach(btn => {
            btn.addEventListener('click', function() {
                const orcamentoId = this.getAttribute('data-id');
                editarOrcamento(orcamentoId);
            });
        });
        
        document.querySelectorAll('.btn-excluir-orcamento').forEach(btn => {
            btn.addEventListener('click', function() {
                const orcamentoId = this.getAttribute('data-id');
                excluirOrcamento(orcamentoId);
            });
        });
        
    } catch (error) {
        console.error('Erro ao carregar orçamentos:', error);
        // Não exibe erro para o usuário, apenas registra no console
    }
}

// Função para carregar dívidas
async function carregarDividas() {
    try {
        const response = await fetch(`/api/dividas?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar dívidas');
        }
        
        const dividas = await response.json();
        
        const container = document.getElementById('lista-dividas');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!dividas || dividas.length === 0) {
            container.innerHTML = `
            <div class="text-center py-3">
                <p class="text-muted">Nenhuma dívida cadastrada</p>
                <a href="/dividas/nova" class="btn btn-sm btn-outline-success">
                    <i class="bi bi-plus-circle me-1"></i>Adicionar Dívida
                </a>
            </div>`;
            return;
        }
        
        // Cores para diferentes tipos de dívida
        const coresDividas = {
            'cartao_credito': '#EC407A',
            'financiamento': '#AB47BC',
            'emprestimo': '#5C6BC0',
            'outros': '#78909C'
        };
        
        // Ícones para diferentes tipos de dívida
        const iconesDividas = {
            'cartao_credito': '<i class="bi bi-credit-card"></i>',
            'financiamento': '<i class="bi bi-house-door"></i>',
            'emprestimo': '<i class="bi bi-cash-stack"></i>',
            'outros': '<i class="bi bi-file-earmark-text"></i>'
        };
        
        dividas.forEach(divida => {
            const corDivida = coresDividas[divida.tipo] || '#78909C';
            const iconeDivida = iconesDividas[divida.tipo] || '<i class="bi bi-file-earmark-text"></i>';
            
            let subtitulo = '';
            if (divida.data_vencimento) {
                subtitulo = `Vence em ${formatarData(divida.data_vencimento)}`;
            } else if (divida.parcelas_total > 0) {
                subtitulo = `${divida.parcelas_pagas}x de ${divida.parcelas_total}`;
            }
            
            container.innerHTML += `
            <div class="widget-item">
                <div class="widget-icon" style="background-color: ${corDivida};">
                    ${iconeDivida}
                </div>
                <div>
                    <div class="widget-title">${divida.nome}</div>
                    <div class="widget-subtitle">${subtitulo}</div>
                </div>
                <div class="widget-value">${formatarValor(divida.valor_total)}</div>
            </div>`;
        });
        
    } catch (error) {
        console.error('Erro ao carregar dívidas:', error);
        // Não exibe erro para o usuário, apenas registra no console
    }
}

// Função para carregar metas financeiras
async function carregarMetas() {
    try {
        const response = await fetch(`/api/metas?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error('Erro ao carregar metas financeiras');
        }
        
        const metas = await response.json();
        
        const container = document.getElementById('lista-metas');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!metas || metas.length === 0) {
            container.innerHTML = `
            <div class="text-center py-3">
                <p class="text-muted">Nenhuma meta financeira cadastrada</p>
                <button class="btn btn-sm btn-outline-success" data-bs-toggle="modal" data-bs-target="#modalFinancialGoal">
                    <i class="bi bi-plus-circle me-1"></i>Adicionar Meta
                </button>
            </div>`;
            return;
        }
        
        // Cores para diferentes tipos de meta
        const coresMetas = {
            'bi-airplane': '#26C6DA',
            'bi-house': '#66BB6A',
            'bi-car-front': '#FFA726',
            'bi-laptop': '#8D6E63',
            'bi-mortarboard': '#7E57C2',
            'bi-piggy-bank': '#F06292',
            'bi-gift': '#42A5F5',
            'bi-bank': '#FF7043'
        };
        
        metas.forEach(meta => {
            const corMeta = coresMetas[meta.icone] || '#78909C';
            
            // Cálculo de porcentagem
            const valorAtual = parseFloat(meta.valor_atual) || 0;
            const valorAlvo = parseFloat(meta.valor_alvo) || 1; // Evita divisão por zero
            const porcentagem = Math.min(100, Math.round((valorAtual / valorAlvo) * 100));
            
            container.innerHTML += `
            <div class="widget-item">
                <div class="widget-icon" style="background-color: ${corMeta};">
                    <i class="${meta.icone}"></i>
                </div>
                <div>
                    <div class="widget-title">${meta.titulo}</div>
                    <div class="widget-subtitle">Até ${formatarData(meta.data_alvo)}</div>
                    <div class="budget-progress">
                        <div class="budget-bar" style="width: ${porcentagem}%; background-color: ${corMeta};"></div>
                    </div>
                </div>
                <div class="widget-value">
                    <div>${formatarValor(meta.valor_atual)}/${formatarValor(meta.valor_alvo)}</div>
                    <small class="text-muted">${porcentagem}%</small>
                </div>
            </div>`;
        });
        
    } catch (error) {
        console.error('Erro ao carregar metas:', error);
        // Não exibe erro para o usuário, apenas registra no console
    }
}
            'cartao_credito': '#EC407A',
            'financiamento': '#AB47BC',
            'emprestimo': '#5C6BC0',
            'outros': '#78909C'
        };
        
        // Ícones para diferentes tipos de dívida
        const iconesDividas = {
            'cartao_credito': '<i class="bi bi-credit-card"></i>',
            'financiamento': '<i class="bi bi-house-door"></i>',
            'emprestimo': '<i class="bi bi-cash-stack"></i>',
            'outros': '<i class="bi bi-file-earmark-text"></i>'
        };
        
        dividas.forEach(divida => {
            const corDivida = coresDividas[divida.tipo] || '#78909C';
            const iconeDivida = iconesDividas[divida.tipo] || '<i class="bi bi-file-earmark-text"></i>';
            
            let subtitulo = '';
            if (divida.data_vencimento) {
                subtitulo = `Vence em ${formatarData(divida.data_vencimento)}`;
            } else if (divida.parcelas_total > 0) {
                subtitulo = `${divida.parcelas_pagas}x de ${divida.parcelas_total}`;
            }
            
            container.innerHTML += `
            <div class="widget-item">
                <div class="widget-icon" style="background-color: ${corDivida};">
                    ${iconeDivida}
                </div>
                <div>
                    <div class="widget-title">${divida.descricao}</div>
                    <div class="widget-subtitle">${subtitulo}</div>
                </div>
                <div class="widget-value">${formatarValor(divida.valor_total)}</div>
            </div>`;
        });
        
    } catch (error) {
        console.error('Erro ao carregar dívidas:', error);
    }
}

// Função para carregar metas financeiras
async function carregarMetas() {
    try {
        const response = await fetch(`/api/metas?tipo_perfil=${perfilAtual}`);
        const metas = await response.json();
        
        const container = document.getElementById('lista-metas');
        container.innerHTML = '';
        
        if (metas.length === 0) {
            container.innerHTML = `
            <div class="text-center py-3">
                <p class="text-muted">Nenhuma meta financeira cadastrada</p>
                <button class="btn btn-sm btn-outline-success" data-bs-toggle="modal" data-bs-target="#modalFinancialGoal">
                    <i class="bi bi-plus-circle me-1"></i>Adicionar Meta
                </button>
            </div>`;
            return;
        }
        
        // Cores para diferentes tipos de meta
        const coresMetas = {
            'bi-airplane': '#26C6DA',
            'bi-house': '#66BB6A',
            'bi-car-front': '#FFA726',
            'bi-laptop': '#8D6E63',
            'bi-mortarboard': '#7E57C2',
            'bi-piggy-bank': '#F06292',
            'bi-gift': '#42A5F5',
            'bi-bank': '#FF7043'
        };
        
        metas.forEach(meta => {
            const corMeta = coresMetas[meta.icone] || '#78909C';
            
            // Cálculo de porcentagem
            const porcentagem = Math.min(100, Math.round((meta.valor_atual / meta.valor_alvo) * 100));
            
            container.innerHTML += `
            <div class="widget-item">
                <div class="widget-icon" style="background-color: ${corMeta};">
                    <i class="${meta.icone}"></i>
                </div>
                <div>
                    <div class="widget-title">${meta.titulo}</div>
                    <div class="widget-subtitle">Até ${formatarData(meta.data_alvo)}</div>
                    <div class="budget-progress">
                        <div class="budget-bar" style="width: ${porcentagem}%; background-color: ${corMeta};"></div>
                    </div>
                </div>
                <div class="widget-value">
                    <div>${formatarValor(meta.valor_atual)}/${formatarValor(meta.valor_alvo)}</div>
                    <small class="text-muted">${porcentagem}%</small>
                </div>
            </div>`;
        });
        
    } catch (error) {
        console.error('Erro ao carregar metas:', error);
    }
}

// Função para carregar o calendário
async function carregarCalendario() {
    try {
        // Obtém o elemento do calendário
        const calendarGrid = document.getElementById('calendar-grid');
        
        // Obtém o mês atual
        const dataAtual = new Date();
        const mesAtual = dataAtual.getMonth();
        const anoAtual = dataAtual.getFullYear();
        
        // Primeiro dia do mês
        const primeiroDia = new Date(anoAtual, mesAtual, 1);
        const diaSemana = primeiroDia.getDay(); // 0 = Domingo, 1 = Segunda, ...
        
        // Último dia do mês
        const ultimoDia = new Date(anoAtual, mesAtual + 1, 0).getDate();
        
        // Último dia do mês anterior
        const ultimoDiaMesAnterior = new Date(anoAtual, mesAtual, 0).getDate();
        
        // Limpa o grid
        calendarGrid.innerHTML = '';
        
        // Busca eventos do mês
        const response = await fetch(`/api/eventos?mes=${mesAtual + 1}&ano=${anoAtual}&tipo_perfil=${perfilAtual}`);
        const eventos = await response.json();
        
        // Mapeia os dias com eventos
        const diasComEventos = {};
        eventos.forEach(evento => {
            const dataEvento = new Date(evento.data);
            const diaEvento = dataEvento.getDate();
            diasComEventos[diaEvento] = true;
        });
        
        // Dias do mês anterior
        for (let i = 0; i < diaSemana; i++) {
            const dia = ultimoDiaMesAnterior - diaSemana + i + 1;
            calendarGrid.innerHTML += `<div class="calendar-day text-muted">${dia}</div>`;
        }
        
        // Dias do mês atual
        for (let i = 1; i <= ultimoDia; i++) {
            const isHoje = i === dataAtual.getDate();
            const temEventos = diasComEventos[i];
            
            const classes = [
                'calendar-day',
                isHoje ? 'active' : '',
                temEventos ? 'has-events' : ''
            ].filter(Boolean).join(' ');
            
            calendarGrid.innerHTML += `<div class="${classes}" data-dia="${i}">${i}</div>`;
        }
        
        // Dias do próximo mês
        const diasRestantes = 7 - ((diaSemana + ultimoDia) % 7);
        if (diasRestantes < 7) {
            for (let i = 1; i <= diasRestantes; i++) {
                calendarGrid.innerHTML += `<div class="calendar-day text-muted">${i}</div>`;
            }
        }
        
        // Event Listeners
        document.querySelectorAll('.calendar-day:not(.text-muted)').forEach(day => {
            day.addEventListener('click', function() {
                const dia = this.getAttribute('data-dia');
                if (dia) {
                    carregarEventosDia(dia, mesAtual + 1, anoAtual);
                }
            });
        });
        
    } catch (error) {
        console.error('Erro ao carregar calendário:', error);
    }
}

// Função para carregar eventos de um dia específico
async function carregarEventosDia(dia, mes, ano) {
    try {
        const response = await fetch(`/api/eventos?dia=${dia}&mes=${mes}&ano=${ano}&tipo_perfil=${perfilAtual}`);
        const eventos = await response.json();
        
        // Aqui você pode mostrar os eventos em um modal ou em uma seção da página
        if (eventos.length > 0) {
            // Cria uma string com os eventos para mostrar em um alerta (temporário)
            let eventosStr = `Eventos para ${dia}/${mes}/${ano}:\n\n`;
            eventos.forEach(evento => {
                eventosStr += `- ${evento.titulo}\n`;
            });
            
            alert(eventosStr);
            
            // Em uma implementação real, você poderia mostrar isso em um modal
            // ou em uma área específica da página
        } else {
            alert(`Não há eventos para ${dia}/${mes}/${ano}`);
        }
        
    } catch (error) {
        console.error('Erro ao carregar eventos do dia:', error);
    }
}

// Atualiza o gráfico
function atualizarGrafico(dados) {
    if (!dados || !dados.data) {
        console.error('Dados do gráfico inválidos');
        return;
    }
    
    // Renderiza o gráfico com Plotly
    Plotly.newPlot('grafico-categoria', dados.data, dados.layout, {responsive: true});
    
    // Armazena os dados para uso posterior
    dadosGrafico = dados;
}

// Função para agrupar transações por data
function agruparTransacoesPorData(transacoes) {
    const grupos = {};
    
    if (!transacoes || !Array.isArray(transacoes)) {
        return grupos;
    }
    
    transacoes.forEach(transacao => {
        if (!transacao.data) return;
        
        const data = transacao.data;
        if (!grupos[data]) {
            grupos[data] = [];
        }
        grupos[data].push(transacao);
    });
    
    return grupos;
}

// Função para criar HTML de uma transação
function criarHTMLTransacao(transacao, isReceita = false) {
    if (!transacao) return '';
    
    // Determina o emoji/ícone baseado na categoria
    let emoji = '📦'; // Padrão
    let categoriaClass = 'category-outros';
    let filterClass = isReceita ? 'income' : 'expense';
    
    if (isReceita) {
        emoji = '💰';
        categoriaClass = 'bg-success';
        
        // Ícones específicos para categorias de receita
        if (transacao.categoria === 'salario') emoji = '💵';
        if (transacao.categoria === 'freelance') emoji = '💼';
        if (transacao.categoria === 'investimento') emoji = '📈';
        if (transacao.categoria === 'presente') emoji = '🎁';
    } else {
        // Mapa de categorias para emojis e classes de filtro
        const emojisCategoria = {
            'alimentação': '🍽️',
            'transporte': '🚗',
            'moradia': '🏠',
            'saúde': '⚕️',
            'educação': '📚',
            'lazer': '🎭',
            'vestuário': '👕',
            'outros': '📦'
        };
        
        const filterClasses = {
            'alimentação': 'food',
            'transporte': 'transport',
            'moradia': 'housing',
            'saúde': 'health',
            'educação': 'education',
            'lazer': 'leisure',
            'vestuário': 'clothing',
            'outros': 'other'
        };
        
        if (transacao.categoria) {
            emoji = emojisCategoria[transacao.categoria] || '📦';
            categoriaClass = `category-${transacao.categoria}`;
            filterClass = filterClasses[transacao.categoria] || 'other';
        }
    }
    
    // Formata data e hora
    let dataFormatada = '';
    try {
        const dataObj = new Date(transacao.data + 'T00:00:00');
        dataFormatada = dataObj.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'});
    } catch (e) {
        console.error('Erro ao formatar data:', e);
        dataFormatada = transacao.data || '';
    }
    
    // Formata o valor com sinal + ou -
    const valorFormatado = formatarValor(transacao.valor);
    
    return `
    <div class="expense-item d-flex justify-content-between align-items-center" data-filter="${filterClass}">
        <div class="d-flex align-items-center">
            <div class="category-pill me-3 ${categoriaClass} text-white">${emoji}</div>
            <div>
                <h6 class="expense-item-title">${transacao.descricao || 'Sem descrição'}</h6>
                <p class="expense-item-subtitle">${dataFormatada} • ${isReceita ? 'Receita' : (transacao.categoria ? transacao.categoria.charAt(0).toUpperCase() + transacao.categoria.slice(1) : 'Outros')}</p>
            </div>
        </div>
        <div class="expense-item-amount" style="color: ${isReceita ? '#28a745' : '#e74c3c'}">${isReceita ? '+' : '-'} ${valorFormatado}</div>
    </div>
    `;
}

// Atualiza a lista de transações
function atualizarListaTransacoes(despesas, receitas) {
    // Container para as transações
    const todasTransacoesContainer = document.getElementById('todas-transacoes');
    if (!todasTransacoesContainer) return;
    
    // Limpa o container
    todasTransacoesContainer.innerHTML = '';
    
    // Verifica se as listas são válidas
    if (!Array.isArray(despesas)) despesas = [];
    if (!Array.isArray(receitas)) receitas = [];
    
    // Agrupa transações por data
    const despesasPorData = agruparTransacoesPorData(despesas);
    const receitasPorData = agruparTransacoesPorData(receitas);
    
    // Combina todas as datas únicas
    const todasDatas = [...new Set([...Object.keys(despesasPorData), ...Object.keys(receitasPorData)])].sort().reverse();
    
    // Se não há transações
    if (todasDatas.length === 0) {
        const mensagemVazia = `
        <div class="text-center py-5">
            <i class="bi bi-receipt text-muted" style="font-size: 48px;"></i>
            <p class="mt-3 text-muted">Nenhuma transação encontrada neste período.</p>
            <button class="btn btn-outline-success btn-sm" data-bs-toggle="modal" data-bs-target="#modalAddTransacao">
                <i class="bi bi-plus-circle me-1"></i>Adicionar Transação
            </button>
        </div>
        `;
        todasTransacoesContainer.innerHTML = mensagemVazia;
        return;
    }
    
    // Preenche a lista de transações
    todasDatas.forEach(data => {
        let dataFormatada = '';
        try {
            const dataObj = new Date(data + 'T00:00:00');
            dataFormatada = dataObj.toLocaleDateString('pt-BR', {
                day: 'numeric',
                month: 'long',
                year: 'numeric'
            });
        } catch (e) {
            console.error('Erro ao formatar data:', e);
            dataFormatada = data || 'Data desconhecida';
        }
        
        // Para todas as transações
        if (despesasPorData[data] || receitasPorData[data]) {
            todasTransacoesContainer.innerHTML += `<div class="transaction-date ps-3">${dataFormatada}</div>`;
            
            // Adiciona receitas
            if (receitasPorData[data]) {
                receitasPorData[data].forEach(receita => {
                    todasTransacoesContainer.innerHTML += criarHTMLTransacao(receita, true);
                });
            }
            
            // Adiciona despesas
            if (despesasPorData[data]) {
                despesasPorData[data].forEach(despesa => {
                    todasTransacoesContainer.innerHTML += criarHTMLTransacao(despesa, false);
                });
            }
        }
    });
}

// Funções para gerenciar orçamentos
function editarOrcamento(id) {
    // Buscar dados do orçamento e preencher o formulário
    fetch(`/api/orcamentos/${id}`)
        .then(response => response.json())
        .then(orcamento => {
            // Preenche o formulário
            document.getElementById('orcamento-categoria').value = orcamento.categoria;
            document.getElementById('orcamento-valor').value = orcamento.valor_limite;
            document.getElementById('orcamento-periodicidade').value = orcamento.periodicidade;
            document.getElementById('orcamento-alerta').value = orcamento.alerta_percentual;
            document.getElementById('orcamento-tipo-perfil').value = orcamento.tipo_perfil;
            
            // Adiciona o ID do orçamento como atributo data no formulário
            document.getElementById('form-orcamento').setAttribute('data-id', id);
            
            // Altera o texto do botão
            document.querySelector('#form-orcamento button[type="submit"]').textContent = 'Atualizar Orçamento';
            
            // Ativa a tab do formulário
            document.getElementById('tab-novo-orcamento').click();
        })
        .catch(error => {
            console.error('Erro ao buscar dados do orçamento:', error);
            alert('Erro ao carregar dados do orçamento. Por favor, tente novamente.');
        });
}

function excluirOrcamento(id) {
    if (confirm('Tem certeza que deseja excluir este orçamento?')) {
        fetch(`/api/orcamentos/${id}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                alert('Orçamento excluído com sucesso!');
                carregarOrcamentos();
            } else {
                throw new Error('Erro ao excluir orçamento');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao excluir o orçamento. Por favor, tente novamente.');
        });
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Seletor de perfil (pessoal/empresarial)
    const profilePersonal = document.getElementById('profile-personal');
    const profileBusiness = document.getElementById('profile-business');
    
    profilePersonal.addEventListener('click', function() {
        profilePersonal.classList.add('active');
        profileBusiness.classList.remove('active');
        perfilAtual = 'pessoal';
        carregarDados(periodoAtual);
    });
    
    if (profileBusiness && !profileBusiness.classList.contains('disabled')) {
        profileBusiness.addEventListener('click', function() {
            profileBusiness.classList.add('active');
            profilePersonal.classList.remove('active');
            perfilAtual = 'empresarial';
            carregarDados(periodoAtual);
        });
    }
    
    // Event listener para os botões de período
    document.querySelectorAll('.period-btn').forEach(botao => {
        botao.addEventListener('click', function() {
            if (this.dataset.period === 'custom') {
                // Este botão abre o modal de datas, não altera o período ainda
                return;
            }
            
            // Remove a classe ativa de todos os botões
            document.querySelectorAll('.period-btn').forEach(btn => {
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-success');
            });
            
            // Adiciona a classe ativa ao botão clicado
            this.classList.remove('btn-outline-success');
            this.classList.add('btn-success');
            
            // Carrega os dados para o período selecionado
            carregarDados(this.dataset.period);
        });
    });
    
    // Botão para aplicar datas personalizadas
    document.getElementById('btn-aplicar-datas').addEventListener('click', function() {
        const dataInicio = document.getElementById('date-inicio').value;
        const dataFim = document.getElementById('date-fim').value;
        
        if (!dataInicio || !dataFim) {
            alert('Por favor, selecione as datas de início e fim');
            return;
        }
        
        // Fecha o modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalDatePicker'));
        modal.hide();
        
        // Remove a classe ativa de todos os botões de período
        document.querySelectorAll('.period-btn').forEach(btn => {
            btn.classList.remove('btn-success');
            btn.classList.add('btn-outline-success');
        });
        
        // Adiciona a classe ativa ao botão personalizado
        const btnCustom = document.querySelector('.period-btn[data-period="custom"]');
        btnCustom.classList.remove('btn-outline-success');
        btnCustom.classList.add('btn-success');
        
        // Carrega os dados para o período personalizado
        carregarDados('custom');
    });
    
    // Event listener para os botões de tipo de gráfico
    document.getElementById('btn-chart-category').addEventListener('click', function() {
        fetch(`/api/grafico/por_categoria?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
            .then(response => response.json())
            .then(dados => atualizarGrafico(dados));
    });
    
    document.getElementById('btn-chart-time').addEventListener('click', function() {
        fetch(`/api/grafico/por_tempo?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
            .then(response => response.json())
            .then(dados => atualizarGrafico(dados));
    });
    
    document.getElementById('btn-chart-comparison').addEventListener('click', function() {
        fetch(`/api/grafico/comparativo?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
            .then(response => response.json())
            .then(dados => atualizarGrafico(dados));
    });
    
    // Event listener para pesquisa de transações
    document.getElementById('search-transactions').addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        document.querySelectorAll('#todas-transacoes .expense-item').forEach(item => {
            const title = item.querySelector('.expense-item-title').textContent.toLowerCase();
            const subtitle = item.querySelector('.expense-item-subtitle').textContent.toLowerCase();
            
            if (title.includes(searchTerm) || subtitle.includes(searchTerm)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    });
    
    // Event listeners para os filtros por chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', function() {
            // Atualiza as classes ativas
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            
            // Obtém o filtro
            const filtro = this.dataset.filter;
            
            // Aplica o filtro nas transações
            document.querySelectorAll('#todas-transacoes .expense-item').forEach(item => {
                if (filtro === 'all' || item.dataset.filter === filtro) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    });
    
    // Event listener para o formulário de despesa
    document.getElementById('form-despesa').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Cria um objeto FormData com os dados do formulário
        const formData = new FormData(this);
        
        // Converte FormData para objeto JSON
        const dadosDespesa = {};
        formData.forEach((valor, chave) => {
            // Converte checkboxes para 0 ou 1
            if (chave === 'parcelado') {
                dadosDespesa[chave] = valor === 'on' ? 1 : 0;
            } else {
                dadosDespesa[chave] = valor;
            }
        });
        
        try {
            // Envia os dados para a API
            const response = await fetch('/api/despesas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosDespesa)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                modal.hide();
                
                // Recarrega os dados
                carregarDados(periodoAtual);
                
                // Limpa o formulário
                this.reset();
                
                // Define a data para hoje
                document.getElementById('despesa-data').valueAsDate = new Date();
                
                // Mostra mensagem de sucesso
                alert('Despesa adicionada com sucesso!');
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao adicionar a despesa.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao adicionar a despesa. Por favor, tente novamente.');
        }
    });
    
    // Event listener para o formulário de receita
    document.getElementById('form-receita').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Cria um objeto FormData com os dados do formulário
        const formData = new FormData(this);
        
        // Converte FormData para objeto JSON
        const dadosReceita = {};
        formData.forEach((valor, chave) => {
            // Converte checkboxes para 0 ou 1
            if (chave === 'recorrente') {
                dadosReceita[chave] = valor === 'on' ? 1 : 0;
            } else {
                dadosReceita[chave] = valor;
            }
        });
        
        try {
            // Envia os dados para a API
            const response = await fetch('/api/receitas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosReceita)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                modal.hide();
                
                // Recarrega os dados
                carregarDados(periodoAtual);
                
                // Limpa o formulário
                this.reset();
                
                // Define a data para hoje
                document.getElementById('receita-data').valueAsDate = new Date();
                
                // Mostra mensagem de sucesso
                alert('Receita adicionada com sucesso!');
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao adicionar a receita.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao adicionar a receita. Por favor, tente novamente.');
        }
    });
    
    // Event listener para o formulário de transferência
    document.getElementById('form-transferencia').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Verificar se a conta de origem e destino são diferentes
        const origem = document.getElementById('transferencia-origem').value;
        const destino = document.getElementById('transferencia-destino').value;
        
        if (origem === destino) {
            alert('A conta de origem e destino devem ser diferentes.');
            return;
        }
        
        // Cria um objeto FormData com os dados do formulário
        const formData = new FormData(this);
        
        // Converte FormData para objeto JSON
        const dadosTransferencia = {};
        formData.forEach((valor, chave) => {
            dadosTransferencia[chave] = valor;
        });
        
        try {
            // Envia os dados para a API
            const response = await fetch('/api/transferencias', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosTransferencia)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                modal.hide();
                
                // Recarrega os dados
                carregarDados(periodoAtual);
                
                // Limpa o formulário
                this.reset();
                
                // Define a data para hoje
                document.getElementById('transferencia-data').valueAsDate = new Date();
                
                // Mostra mensagem de sucesso
                alert('Transferência registrada com sucesso!');
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao registrar a transferência.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao registrar a transferência. Por favor, tente novamente.');
        }
    });
    
    // Event listener para o formulário de orçamento
    document.getElementById('form-orcamento').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Cria um objeto FormData com os dados do formulário
        const formData = new FormData(this);
        
        // Converte FormData para objeto JSON
        const dadosOrcamento = {};
        formData.forEach((valor, chave) => {
            dadosOrcamento[chave] = valor;
        });
        
        // Verifica se é uma atualização ou novo orçamento
        const orcamentoId = this.getAttribute('data-id');
        const isEdicao = orcamentoId !== null;
        
        try {
            // Envia os dados para a API
            const url = isEdicao ? `/api/orcamentos/${orcamentoId}` : '/api/orcamentos';
            const method = isEdicao ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosOrcamento)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalBudget'));
                modal.hide();
                
                // Recarrega os dados
                carregarOrcamentos();
                
                // Limpa o formulário
                this.reset();
                this.removeAttribute('data-id');
                
                // Restaura o texto do botão
                document.querySelector('#form-orcamento button[type="submit"]').textContent = 'Salvar Orçamento';
                
                // Mostra mensagem de sucesso
                alert(`Orçamento ${isEdicao ? 'atualizado' : 'salvo'} com sucesso!`);
                
                // Ativa a tab de listar orçamentos
                document.getElementById('tab-listar-orcamentos').click();
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao salvar o orçamento.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao salvar o orçamento. Por favor, tente novamente.');
        }
    });
    
    // Event listener para o formulário de meta financeira
    document.getElementById('form-meta-financeira').addEventListener('submit', async function(event) {
        event.preventDefault();
        
        // Cria um objeto FormData com os dados do formulário
        const formData = new FormData(this);
        
        // Converte FormData para objeto JSON
        const dadosMeta = {};
        formData.forEach((valor, chave) => {
            dadosMeta[chave] = valor;
        });
        
        try {
            // Envia os dados para a API
            const response = await fetch('/api/metas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosMeta)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalFinancialGoal'));
                modal.hide();
                
                // Recarrega os dados
                carregarMetas();
                
                // Limpa o formulário
                this.reset();
                
                // Mostra mensagem de sucesso
                alert('Meta financeira adicionada com sucesso!');
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao adicionar a meta.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao adicionar a meta. Por favor, tente novamente.');
        }
    });
    
    // Modal para escanear comprovante
    document.getElementById('btn-upload-receipt').addEventListener('click', function() {
        document.getElementById('receipt-upload').click();
    });
    
    document.getElementById('receipt-upload').addEventListener('change', function(event) {
        if (this.files && this.files[0]) {
            const reader = new FileReader();
            
            reader.onload = function(e) {
                // Oculta o container da câmera
                document.getElementById('camera-container').style.display = 'none';
                
                // Mostra o preview
                document.getElementById('receipt-preview').style.display = 'block';
                document.getElementById('preview-image').src = e.target.result;
                document.getElementById('btn-save-receipt').style.display = 'block';
                
                // Em uma implementação real, aqui faria o OCR e preencheria os campos
                // Por enquanto, deixamos os campos vazios para serem preenchidos pelo usuário
                document.getElementById('ocr-valor').value = '';
                document.getElementById('ocr-data').value = formatarData(new Date());
                document.getElementById('ocr-estabelecimento').value = '';
            }
            
            reader.readAsDataURL(this.files[0]);
        }
    });
    
    document.getElementById('btn-capture-photo').addEventListener('click', function() {
        document.getElementById('camera-container').style.display = 'block';
        document.getElementById('receipt-preview').style.display = 'none';
    });
    
    document.getElementById('btn-take-photo').addEventListener('click', function() {
        // Em uma implementação real, capturaria a foto da câmera
        // Por enquanto, apenas simulamos o processo
        
        document.getElementById('camera-container').style.display = 'none';
        document.getElementById('receipt-preview').style.display = 'block';
        document.getElementById('preview-image').src = '/img/receipt-placeholder.jpg';
        document.getElementById('btn-save-receipt').style.display = 'block';
        
        // Em uma implementação real, aqui faria o OCR e preencheria os campos
        document.getElementById('ocr-valor').value = '';
        document.getElementById('ocr-data').value = formatarData(new Date());
        document.getElementById('ocr-estabelecimento').value = '';
    });
    
    document.getElementById('btn-save-receipt').addEventListener('click', async function() {
        // Coleta os dados do formulário
        const valor = document.getElementById('ocr-valor').value;
        const data = document.getElementById('ocr-data').value;
        const estabelecimento = document.getElementById('ocr-estabelecimento').value;
        const categoria = document.getElementById('ocr-categoria').value;
        
        // Valida os dados
        if (!valor || !data || !estabelecimento) {
            alert('Por favor, preencha todos os campos.');
            return;
        }
        
        // Criar objeto com os dados da despesa
        const dadosDespesa = {
            valor: parseFloat(valor.replace('R$', '').replace('.', '').replace(',', '.')),
            descricao: estabelecimento,
            categoria: categoria,
            data: data,
            forma_pagamento: '',
            parcelado: 0,
            tipo_perfil: perfilAtual
        };
        
        try {
            // Envia os dados para a API
            const response = await fetch('/api/despesas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(dadosDespesa)
            });
            
            if (response.ok) {
                // Fecha o modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('modalScanReceipt'));
                modal.hide();
                
                // Recarrega os dados
                carregarDados(periodoAtual);
                
                // Limpa o preview
                document.getElementById('receipt-preview').style.display = 'none';
                document.getElementById('camera-container').style.display = 'none';
                document.getElementById('btn-save-receipt').style.display = 'none';
                
                // Mostra mensagem de sucesso
                alert('Comprovante processado e despesa registrada com sucesso!');
            } else {
                const erro = await response.json();
                alert(`Erro: ${erro.error || 'Ocorreu um erro ao registrar a despesa.'}`);
            }
        } catch (error) {
            console.error('Erro:', error);
            alert('Ocorreu um erro ao registrar a despesa. Por favor, tente novamente.');
        }
    });
    
    // Event listener para mostrar/esconder campos adicionais
    document.getElementById('despesa-parcelada').addEventListener('change', function() {
        document.getElementById('div-parcelas').style.display = this.checked ? 'block' : 'none';
    });
    
    document.getElementById('receita-recorrente').addEventListener('change', function() {
        document.getElementById('div-periodicidade').style.display = this.checked ? 'block' : 'none';
    });
    
    // Botão para compartilhar gráfico via WhatsApp
    document.getElementById('btn-share-chart').addEventListener('click', function() {
        // Obtém a URL da imagem do gráfico
        const urlGrafico = `/api/grafico/imagem?tipo=categoria&periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`;
        
        // Cria a URL do WhatsApp
        const textoCompartilhamento = `Veja meu resumo financeiro ${periodoAtual === 'dia' ? 'de hoje' : 
                                      periodoAtual === 'semana' ? 'desta semana' : 
                                      periodoAtual === 'mes' ? 'deste mês' : 'deste ano'}:`;
        const urlWhatsApp = `https://wa.me/?text=${encodeURIComponent(textoCompartilhamento + "\n" + urlGrafico)}`;
        
        // Abre a URL
        window.open(urlWhatsApp, '_blank');
    });
    
    // Inicialização do dashboard
    // Define a data atual como padrão para os campos de data
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    
    document.getElementById('despesa-data').valueAsDate = hoje;
    document.getElementById('receita-data').valueAsDate = hoje;
    document.getElementById('transferencia-data').valueAsDate = hoje;
    document.getElementById('date-inicio').valueAsDate = new Date(hoje.getFullYear(), hoje.getMonth(), 1); // Primeiro dia do mês
    document.getElementById('date-fim').valueAsDate = hoje;
    
    const dataLimiteMetaFinanceira = new Date(hoje);
    dataLimiteMetaFinanceira.setMonth(dataLimiteMetaFinanceira.getMonth() + 6); // Data limite padrão: 6 meses a partir de hoje
    document.getElementById('meta-data-alvo').valueAsDate = dataLimiteMetaFinanceira;
    
    // Carrega os dados iniciais
    carregarDados(periodoAtual);
});