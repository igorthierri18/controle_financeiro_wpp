// Dashboard.js - Versão Completa Corrigida com Debug
// Variáveis globais
let periodoAtual = 'semana';
let dadosGrafico = [];
let perfilAtual = 'pessoal';

// Funções de formatação
function formatarData(dataStr) {
    try {
        if (!dataStr) return '';
        const data = new Date(dataStr);
        return data.toLocaleDateString('pt-BR');
    } catch (error) {
        console.error('❌ [ERROR] Erro ao formatar data:', error, 'Data:', dataStr);
        return dataStr || '';
    }
}

function formatarValor(valor) {
    try {
        if (valor === null || valor === undefined || valor === '') {
            console.warn('⚠️ [WARNING] Valor nulo/undefined para formatação, usando 0');
            return 'R$ 0,00';
        }
        
        const numero = parseFloat(valor);
        if (isNaN(numero)) {
            console.warn('⚠️ [WARNING] Valor não numérico para formatação:', valor);
            return 'R$ 0,00';
        }
        
        return 'R$ ' + numero.toFixed(2).replace('.', ',');
    } catch (error) {
        console.error('❌ [ERROR] Erro na formatação de valor:', error, 'Valor:', valor);
        return 'R$ 0,00';
    }
}

// Atualiza os indicadores de tendência
function atualizarTendencias(tendencias) {
    console.log('🔍 [DEBUG] Atualizando tendências:', tendencias);
    
    if (!tendencias) {
        console.warn('⚠️ [WARNING] Tendências não fornecidas');
        return;
    }
    
    try {
        // Despesas
        const trendDespesas = document.getElementById('trend-despesas');
        if (trendDespesas && typeof tendencias.despesas === 'number') {
            if (tendencias.despesas > 0) {
                trendDespesas.className = 'trend-indicator trend-up';
                trendDespesas.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-despesas-valor">${tendencias.despesas.toFixed(1).replace('.', ',')}%</span>`;
            } else {
                trendDespesas.className = 'trend-indicator trend-down';
                trendDespesas.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-despesas-valor">${Math.abs(tendencias.despesas).toFixed(1).replace('.', ',')}%</span>`;
            }
        }
        
        // Receitas
        const trendReceitas = document.getElementById('trend-receitas');
        if (trendReceitas && typeof tendencias.receitas === 'number') {
            if (tendencias.receitas > 0) {
                trendReceitas.className = 'trend-indicator trend-up';
                trendReceitas.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-receitas-valor">${tendencias.receitas.toFixed(1).replace('.', ',')}%</span>`;
            } else {
                trendReceitas.className = 'trend-indicator trend-down';
                trendReceitas.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-receitas-valor">${Math.abs(tendencias.receitas).toFixed(1).replace('.', ',')}%</span>`;
            }
        }
        
        // Saldo
        const trendSaldo = document.getElementById('trend-saldo');
        if (trendSaldo && typeof tendencias.saldo === 'number') {
            if (tendencias.saldo > 0) {
                trendSaldo.className = 'trend-indicator trend-up';
                trendSaldo.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-saldo-valor">${tendencias.saldo.toFixed(1).replace('.', ',')}%</span>`;
            } else {
                trendSaldo.className = 'trend-indicator trend-down';
                trendSaldo.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-saldo-valor">${Math.abs(tendencias.saldo).toFixed(1).replace('.', ',')}%</span>`;
            }
        }
        
        // Economia
        const trendEconomia = document.getElementById('trend-economia');
        if (trendEconomia && typeof tendencias.economia === 'number') {
            if (tendencias.economia > 0) {
                trendEconomia.className = 'trend-indicator trend-up';
                trendEconomia.innerHTML = `<i class="bi bi-arrow-up-short"></i> <span id="trend-economia-valor">${tendencias.economia.toFixed(1).replace('.', ',')}%</span>`;
            } else {
                trendEconomia.className = 'trend-indicator trend-down';
                trendEconomia.innerHTML = `<i class="bi bi-arrow-down-short"></i> <span id="trend-economia-valor">${Math.abs(tendencias.economia).toFixed(1).replace('.', ',')}%</span>`;
            }
        }
        
        console.log('✅ [SUCCESS] Tendências atualizadas com sucesso');
    } catch (error) {
        console.error('❌ [ERROR] Erro ao atualizar tendências:', error);
    }
}

// Função para mostrar valores padrão em caso de erro
function mostrarValoresPadrao() {
    console.log('🔄 [INFO] Mostrando valores padrão devido a erro');
    
    const elementos = [
        { id: 'total-despesas', valor: 'R$ 0,00' },
        { id: 'total-receitas', valor: 'R$ 0,00' },
        { id: 'total-saldo', valor: 'R$ 0,00' },
        { id: 'percentual-economia', valor: '0%' }
    ];
    
    elementos.forEach(({ id, valor }) => {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = valor;
            console.log(`🔄 [INFO] Valor padrão definido para ${id}: ${valor}`);
        } else {
            console.error(`❌ [ERROR] Elemento ${id} não encontrado para valor padrão`);
        }
    });
}

// Função auxiliar para carregar dados complementares
async function carregarDadosComplementares(params) {
    try {
        console.log('🔍 [DEBUG] Iniciando carregamento de dados complementares');
        
        // Carrega o gráfico por categoria
        try {
            const graficoResponse = await fetch(`/api/grafico/por_categoria?${params}`);
            if (graficoResponse.ok) {
                const dadosGrafico = await graficoResponse.json();
                atualizarGrafico(dadosGrafico);
                console.log('✅ [SUCCESS] Gráfico carregado');
            } else {
                console.warn('⚠️ [WARNING] Falha ao carregar gráfico:', graficoResponse.status);
                // Criar gráfico vazio se a API falhar
                criarGraficoVazio();
            }
        } catch (error) {
            console.error('❌ [ERROR] Erro no gráfico:', error.message);
            criarGraficoVazio();
        }

        // Carrega as despesas e receitas
        try {
            const [despesasResponse, receitasResponse] = await Promise.allSettled([
                fetch(`/api/despesas?${params}`),
                fetch(`/api/receitas?${params}`)
            ]);
            
            let despesas = [];
            let receitas = [];
            
            if (despesasResponse.status === 'fulfilled' && despesasResponse.value && despesasResponse.value.ok) {
                despesas = await despesasResponse.value.json();
                console.log('✅ [SUCCESS] Despesas carregadas:', despesas.length, 'itens');
            } else {
                console.warn('⚠️ [WARNING] Falha ao carregar despesas');
            }
            
            if (receitasResponse.status === 'fulfilled' && receitasResponse.value && receitasResponse.value.ok) {
                receitas = await receitasResponse.value.json();
                console.log('✅ [SUCCESS] Receitas carregadas:', receitas.length, 'itens');
            } else {
                console.warn('⚠️ [WARNING] Falha ao carregar receitas');
            }
            
            // Atualiza as listas de transações
            atualizarListaTransacoes(despesas, receitas);
            
        } catch (error) {
            console.error('❌ [ERROR] Erro ao carregar transações:', error.message);
            // Mostrar lista vazia se houver erro
            atualizarListaTransacoes([], []);
        }

        // Carrega outros componentes de forma não-crítica
        const componentesSecundarios = [
            () => carregarLembretesProximos(),
            () => carregarOrcamentos(),
            () => carregarDividas(),
            () => carregarMetas(),
            () => carregarCalendario()
        ];
        
        for (let i = 0; i < componentesSecundarios.length; i++) {
            try {
                await componentesSecundarios[i]();
                console.log(`✅ [SUCCESS] Componente secundário ${i + 1} carregado`);
            } catch (error) {
                console.warn(`⚠️ [WARNING] Erro em componente secundário ${i + 1}:`, error.message);
                // Não interrompe o carregamento por causa de erro em componente secundário
            }
        }
        
        console.log('✅ [SUCCESS] Dados complementares carregados');
        
    } catch (error) {
        console.error('❌ [ERROR] Erro nos dados complementares:', error);
        // Não re-lança o erro para não quebrar o carregamento principal
    }
}

// Carrega os dados com base no período selecionado - VERSÃO CORRIGIDA
async function carregarDados(periodo = 'semana') {
    console.log('🔍 [DEBUG] Iniciando carregarDados com período:', periodo);
    console.log('🔍 [DEBUG] Perfil atual:', perfilAtual);
    
    periodoAtual = periodo;
    
    // Atualiza os subtítulos com o período selecionado
    let textoPeríodo = 'nesta semana';
    if (periodo === 'dia') textoPeríodo = 'hoje';
    if (periodo === 'mes') textoPeríodo = 'neste mês';
    if (periodo === 'ano') textoPeríodo = 'neste ano';
    if (periodo === 'custom') textoPeríodo = 'no período selecionado';
    
    // Atualizar subtítulos com verificação de existência
    const subtitulos = ['period-subtitle', 'period-subtitle-receitas', 'period-subtitle-saldo', 'period-subtitle-economia'];
    subtitulos.forEach(id => {
        const elemento = document.getElementById(id);
        if (elemento) {
            elemento.textContent = textoPeríodo;
        } else {
            console.warn(`⚠️ [WARNING] Elemento de subtítulo não encontrado: ${id}`);
        }
    });
    
    try {
        // Exibe indicador de carregamento
        mostrarCarregamento(true);
        
        // Prepara os parâmetros da requisição
        let params = `periodo=${periodo}&tipo_perfil=${perfilAtual}`;
        
        // Se for período personalizado, adiciona as datas
        if (periodo === 'custom') {
            const dataInicio = document.getElementById('date-inicio')?.value;
            const dataFim = document.getElementById('date-fim')?.value;
            if (dataInicio && dataFim) {
                params += `&data_inicio=${dataInicio}&data_fim=${dataFim}`;
            }
        }
        
        console.log('🔍 [DEBUG] Parâmetros da requisição:', params);
        console.log('🔍 [DEBUG] URL completa do resumo:', `/api/resumo?${params}`);
        
        // Carrega o resumo
        const resumoResponse = await fetch(`/api/resumo?${params}`);
        console.log('🔍 [DEBUG] Status da resposta resumo:', resumoResponse.status);
        
        if (!resumoResponse.ok) {
            const errorText = await resumoResponse.text();
            console.error('❌ [ERROR] Erro na API do resumo:', errorText);
            throw new Error(`Erro na API do resumo: ${resumoResponse.status} - ${errorText}`);
        }
        
        const resumo = await resumoResponse.json();
        console.log('✅ [SUCCESS] Dados do resumo recebidos:', resumo);
        
        // ADICIONAR VALIDAÇÃO DOS DADOS
        if (!resumo || typeof resumo !== 'object') {
            console.error('❌ [ERROR] Dados do resumo inválidos:', resumo);
            throw new Error('Dados do resumo são inválidos');
        }
        
        // Atualiza os totais COM VERIFICAÇÃO
        const totalDespesas = resumo.total_despesas ?? 0;
        const totalReceitas = resumo.total_receitas ?? 0;
        const saldo = resumo.saldo ?? 0;
        
        console.log('🔍 [DEBUG] Valores a serem atualizados:');
        console.log('  - Total Despesas:', totalDespesas);
        console.log('  - Total Receitas:', totalReceitas);
        console.log('  - Saldo:', saldo);
        
        // VERIFICAR SE OS ELEMENTOS EXISTEM ANTES DE ATUALIZAR
        const elemTotalDespesas = document.getElementById('total-despesas');
        const elemTotalReceitas = document.getElementById('total-receitas');
        const elemTotalSaldo = document.getElementById('total-saldo');
        
        if (!elemTotalDespesas) {
            console.error('❌ [ERROR] Elemento #total-despesas não encontrado!');
        } else {
            const valorFormatado = formatarValor(totalDespesas);
            elemTotalDespesas.textContent = valorFormatado;
            console.log('✅ [SUCCESS] Total despesas atualizado:', valorFormatado);
        }
        
        if (!elemTotalReceitas) {
            console.error('❌ [ERROR] Elemento #total-receitas não encontrado!');
        } else {
            const valorFormatado = formatarValor(totalReceitas);
            elemTotalReceitas.textContent = valorFormatado;
            console.log('✅ [SUCCESS] Total receitas atualizado:', valorFormatado);
        }
        
        if (!elemTotalSaldo) {
            console.error('❌ [ERROR] Elemento #total-saldo não encontrado!');
        } else {
            const valorFormatado = formatarValor(saldo);
            elemTotalSaldo.textContent = valorFormatado;
            console.log('✅ [SUCCESS] Saldo atualizado:', valorFormatado);
        }
        
        // Calcula e atualiza a economia percentual
        const economiaPercentual = resumo.economia_percentual ?? 0;
        const elemEconomia = document.getElementById('percentual-economia');
        if (elemEconomia) {
            const valorFormatado = `${economiaPercentual.toFixed(1).replace('.', ',')}%`;
            elemEconomia.textContent = valorFormatado;
            console.log('✅ [SUCCESS] Economia atualizada:', valorFormatado);
        } else {
            console.error('❌ [ERROR] Elemento #percentual-economia não encontrado!');
        }
        
        // Atualiza os indicadores de tendência
        if (resumo.tendencias) {
            console.log('🔍 [DEBUG] Atualizando tendências:', resumo.tendencias);
            atualizarTendencias(resumo.tendencias);
        } else {
            console.warn('⚠️ [WARNING] Nenhuma tendência recebida');
        }
        
        // TENTAR CARREGAR OUTROS DADOS COM TRATAMENTO DE ERRO INDIVIDUAL
        await carregarDadosComplementares(params);
        
        // Esconde indicador de carregamento
        mostrarCarregamento(false);
        console.log('✅ [SUCCESS] carregarDados concluído com sucesso');
        
    } catch (error) {
        console.error('❌ [ERROR] Erro crítico em carregarDados:', error);
        console.error('❌ [ERROR] Stack trace:', error.stack);
        
        // Mostra valores padrão em caso de erro
        mostrarValoresPadrao();
        
        // Mostra mensagem de erro
        mostrarErro(`Erro ao carregar dados: ${error.message}`);
        
        // Esconde indicador de carregamento
        mostrarCarregamento(false);
    }
}

// Função para mostrar/esconder indicador de carregamento
function mostrarCarregamento(exibir) {
    const loader = document.getElementById('loading-indicator');
    if (loader) {
        loader.style.display = exibir ? 'flex' : 'none';
    } else if (exibir) {
        console.warn('⚠️ [WARNING] Elemento loading-indicator não encontrado');
    }
}

// Função para mostrar mensagens de erro
function mostrarErro(mensagem) {
    console.log('🔍 [DEBUG] Mostrando erro:', mensagem);
    
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
    
    // Remove o alerta após 10 segundos
    setTimeout(() => {
        if (alerta.parentNode) {
            alerta.classList.remove('show');
            setTimeout(() => {
                if (alerta.parentNode) {
                    alerta.remove();
                }
            }, 300);
        }
    }, 10000);
}

// Função para criar gráfico vazio
function criarGraficoVazio() {
    const graficoContainer = document.getElementById('grafico-categoria');
    if (graficoContainer) {
        graficoContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-bar-chart" style="font-size: 48px;"></i>
                <p class="mt-2">Não há dados suficientes para exibir o gráfico</p>
            </div>
        `;
    }
}

// Função para carregar lembretes próximos
async function carregarLembretesProximos() {
    try {
        console.log('🔍 [DEBUG] Carregando lembretes próximos...');
        
        const resposta = await fetch(`/api/lembretes?tipo_perfil=${perfilAtual}&concluido=0`);
        if (!resposta.ok) {
            throw new Error(`Erro na API de lembretes: ${resposta.status}`);
        }
        
        const lembretes = await resposta.json();
        console.log('✅ [SUCCESS] Lembretes carregados:', lembretes.length, 'itens');
        
        // Ordena por data mais próxima
        if (Array.isArray(lembretes)) {
            lembretes.sort((a, b) => new Date(a.data) - new Date(b.data));
        }
        
        // Limita a exibir apenas os 3 próximos
        const proximosLembretes = Array.isArray(lembretes) ? lembretes.slice(0, 3) : [];
        
        // Atualiza a lista de lembretes
        const container = document.getElementById('proximos-lembretes');
        if (!container) {
            console.warn('⚠️ [WARNING] Container de lembretes não encontrado');
            return;
        }
        
        container.innerHTML = '';
        
        if (proximosLembretes.length === 0) {
            container.innerHTML = `
            <div class="list-group-item text-center py-4">
                <i class="bi bi-check-circle text-success" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Não há lembretes próximos</p>
            </div>`;
            return;
        }
        
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);
        
        proximosLembretes.forEach(lembrete => {
            try {
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
                        <div class="fw-bold">${lembrete.titulo || 'Sem título'}</div>
                        <small class="text-muted">${formatarData(lembrete.data)}</small>
                        ${lembrete.valor ? `<small class="d-block">${formatarValor(lembrete.valor)}</small>` : ''}
                    </div>
                    <span class="badge ${badgeClass} rounded-pill">${textoData}</span>
                </div>`;
            } catch (error) {
                console.error('❌ [ERROR] Erro ao processar lembrete:', error, lembrete);
            }
        });
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar lembretes:', error);
        // Mostrar conteúdo de erro
        const container = document.getElementById('proximos-lembretes');
        if (container) {
            container.innerHTML = `
            <div class="list-group-item text-center py-4">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Erro ao carregar lembretes</p>
            </div>`;
        }
    }
}

// Função para carregar orçamentos
async function carregarOrcamentos() {
    try {
        console.log('🔍 [DEBUG] Carregando orçamentos...');
        
        const response = await fetch(`/api/orcamentos?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error(`Erro na API de orçamentos: ${response.status}`);
        }
        
        const orcamentos = await response.json();
        console.log('✅ [SUCCESS] Orçamentos carregados:', Array.isArray(orcamentos) ? orcamentos.length : 0, 'itens');
        
        // Container principal
        const container = document.getElementById('lista-orcamentos');
        if (!container) {
            console.warn('⚠️ [WARNING] Container de orçamentos não encontrado');
            return;
        }
        
        container.innerHTML = '';
        
        // Container no modal
        const containerModal = document.getElementById('lista-orcamentos-modal');
        if (containerModal) {
            containerModal.innerHTML = '';
        }
        
        if (!orcamentos || !Array.isArray(orcamentos) || orcamentos.length === 0) {
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
                const btnNovoOrcamento = document.getElementById('btn-novo-orcamento-tab');
                if (btnNovoOrcamento) {
                    btnNovoOrcamento.addEventListener('click', function() {
                        const tabNovoOrcamento = document.getElementById('tab-novo-orcamento');
                        if (tabNovoOrcamento) {
                            tabNovoOrcamento.click();
                        }
                    });
                }
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
            try {
                // Busca o valor gasto para este orçamento
                const valorGasto = parseFloat(orcamento.valor_gasto) || 0;
                const valorLimite = parseFloat(orcamento.valor_limite) || 0;
                
                const corCategoria = coresCategorias[orcamento.categoria] || '#78909C';
                const emojiCategoria = emojisCategorias[orcamento.categoria] || '<i class="bi bi-three-dots"></i>';
                
                // Cálculo de porcentagem
                const porcentagem = valorLimite > 0 ? Math.min(100, Math.round((valorGasto / valorLimite) * 100)) : 0;
                
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
                        <div class="widget-title">${(orcamento.categoria || 'Outros').charAt(0).toUpperCase() + (orcamento.categoria || 'outros').slice(1)}</div>
                        <div class="widget-subtitle">${(orcamento.periodicidade || 'mensal').charAt(0).toUpperCase() + (orcamento.periodicidade || 'mensal').slice(1)}</div>
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
                            <h6 class="mb-1">${(orcamento.categoria || 'Outros').charAt(0).toUpperCase() + (orcamento.categoria || 'outros').slice(1)}</h6>
                            <p class="mb-1 small text-muted">${formatarValor(orcamento.valor_limite)} / ${(orcamento.periodicidade || 'mensal').charAt(0).toUpperCase() + (orcamento.periodicidade || 'mensal').slice(1)}</p>
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
            } catch (error) {
                console.error('❌ [ERROR] Erro ao processar orçamento:', error, orcamento);
            }
        });
        
        // Adiciona event listeners para botões de editar e excluir
        setTimeout(() => {
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
        }, 100);
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar orçamentos:', error);
        // Mostrar conteúdo de erro
        const container = document.getElementById('lista-orcamentos');
        if (container) {
            container.innerHTML = `
            <div class="text-center py-3">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Erro ao carregar orçamentos</p>
            </div>`;
        }
    }
}

// Função para carregar dívidas
async function carregarDividas() {
    try {
        console.log('🔍 [DEBUG] Carregando dívidas...');
        
        const response = await fetch(`/api/dividas?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error(`Erro na API de dívidas: ${response.status}`);
        }
        
        const dividas = await response.json();
        console.log('✅ [SUCCESS] Dívidas carregadas:', Array.isArray(dividas) ? dividas.length : 0, 'itens');
        
        const container = document.getElementById('lista-dividas');
        if (!container) {
            console.warn('⚠️ [WARNING] Container de dívidas não encontrado');
            return;
        }
        
        container.innerHTML = '';
        
        if (!dividas || !Array.isArray(dividas) || dividas.length === 0) {
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
            try {
                const corDivida = coresDividas[divida.tipo] || '#78909C';
                const iconeDivida = iconesDividas[divida.tipo] || '<i class="bi bi-file-earmark-text"></i>';
                
                let subtitulo = '';
                if (divida.data_vencimento) {
                    subtitulo = `Vence em ${formatarData(divida.data_vencimento)}`;
                } else if (divida.parcelas_total && divida.parcelas_total > 0) {
                    const parcelasPagas = divida.parcelas_pagas || 0;
                    subtitulo = `${parcelasPagas}x de ${divida.parcelas_total}`;
                }
                
                const nome = divida.nome || divida.descricao || 'Dívida sem nome';
                const valorTotal = parseFloat(divida.valor_total) || 0;
                
                container.innerHTML += `
                <div class="widget-item">
                    <div class="widget-icon" style="background-color: ${corDivida};">
                        ${iconeDivida}
                    </div>
                    <div>
                        <div class="widget-title">${nome}</div>
                        <div class="widget-subtitle">${subtitulo}</div>
                    </div>
                    <div class="widget-value">${formatarValor(valorTotal)}</div>
                </div>`;
            } catch (error) {
                console.error('❌ [ERROR] Erro ao processar dívida:', error, divida);
            }
        });
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar dívidas:', error);
        // Mostrar conteúdo de erro
        const container = document.getElementById('lista-dividas');
        if (container) {
            container.innerHTML = `
            <div class="text-center py-3">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Erro ao carregar dívidas</p>
            </div>`;
        }
    }
}

// Função para carregar metas financeiras
async function carregarMetas() {
    try {
        console.log('🔍 [DEBUG] Carregando metas...');
        
        const response = await fetch(`/api/metas?tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error(`Erro na API de metas: ${response.status}`);
        }
        
        const metas = await response.json();
        console.log('✅ [SUCCESS] Metas carregadas:', Array.isArray(metas) ? metas.length : 0, 'itens');
        
        const container = document.getElementById('lista-metas');
        if (!container) {
            console.warn('⚠️ [WARNING] Container de metas não encontrado');
            return;
        }
        
        container.innerHTML = '';
        
        if (!metas || !Array.isArray(metas) || metas.length === 0) {
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
            try {
                const corMeta = coresMetas[meta.icone] || '#78909C';
                
                // Cálculo de porcentagem
                const valorAtual = parseFloat(meta.valor_atual) || 0;
                const valorAlvo = parseFloat(meta.valor_alvo) || 1; // Evita divisão por zero
                const porcentagem = Math.min(100, Math.round((valorAtual / valorAlvo) * 100));
                
                const titulo = meta.titulo || 'Meta sem título';
                const dataAlvo = meta.data_alvo || '';
                const icone = meta.icone || 'bi-piggy-bank';
                
                container.innerHTML += `
                <div class="widget-item">
                    <div class="widget-icon" style="background-color: ${corMeta};">
                        <i class="${icone}"></i>
                    </div>
                    <div>
                        <div class="widget-title">${titulo}</div>
                        <div class="widget-subtitle">Até ${formatarData(dataAlvo)}</div>
                        <div class="budget-progress">
                            <div class="budget-bar" style="width: ${porcentagem}%; background-color: ${corMeta};"></div>
                        </div>
                    </div>
                    <div class="widget-value">
                        <div>${formatarValor(valorAtual)}/${formatarValor(valorAlvo)}</div>
                        <small class="text-muted">${porcentagem}%</small>
                    </div>
                </div>`;
            } catch (error) {
                console.error('❌ [ERROR] Erro ao processar meta:', error, meta);
            }
        });
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar metas:', error);
        // Mostrar conteúdo de erro
        const container = document.getElementById('lista-metas');
        if (container) {
            container.innerHTML = `
            <div class="text-center py-3">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Erro ao carregar metas</p>
            </div>`;
        }
    }
}

// Função para carregar o calendário
async function carregarCalendario() {
    try {
        console.log('🔍 [DEBUG] Carregando calendário...');
        
        // Obtém o elemento do calendário
        const calendarGrid = document.getElementById('calendar-grid');
        if (!calendarGrid) {
            console.warn('⚠️ [WARNING] Grid do calendário não encontrado');
            return;
        }
        
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
        let eventos = [];
        try {
            const response = await fetch(`/api/eventos?mes=${mesAtual + 1}&ano=${anoAtual}&tipo_perfil=${perfilAtual}`);
            if (response.ok) {
                eventos = await response.json();
                console.log('✅ [SUCCESS] Eventos carregados:', Array.isArray(eventos) ? eventos.length : 0, 'itens');
            } else {
                console.warn('⚠️ [WARNING] Falha ao carregar eventos:', response.status);
            }
        } catch (error) {
            console.error('❌ [ERROR] Erro ao carregar eventos:', error);
        }
        
        // Mapeia os dias com eventos
        const diasComEventos = {};
        if (Array.isArray(eventos)) {
            eventos.forEach(evento => {
                try {
                    const dataEvento = new Date(evento.data);
                    const diaEvento = dataEvento.getDate();
                    diasComEventos[diaEvento] = true;
                } catch (error) {
                    console.error('❌ [ERROR] Erro ao processar evento:', error, evento);
                }
            });
        }
        
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
        setTimeout(() => {
            document.querySelectorAll('.calendar-day:not(.text-muted)').forEach(day => {
                day.addEventListener('click', function() {
                    const dia = this.getAttribute('data-dia');
                    if (dia) {
                        carregarEventosDia(dia, mesAtual + 1, anoAtual);
                    }
                });
            });
        }, 100);
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar calendário:', error);
        // Mostrar conteúdo de erro
        const calendarGrid = document.getElementById('calendar-grid');
        if (calendarGrid) {
            calendarGrid.innerHTML = `
            <div class="text-center py-3">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 24px;"></i>
                <p class="mt-2 mb-0">Erro ao carregar calendário</p>
            </div>`;
        }
    }
}

// Função para carregar eventos de um dia específico
async function carregarEventosDia(dia, mes, ano) {
    try {
        console.log('🔍 [DEBUG] Carregando eventos do dia:', dia, mes, ano);
        
        const response = await fetch(`/api/eventos?dia=${dia}&mes=${mes}&ano=${ano}&tipo_perfil=${perfilAtual}`);
        if (!response.ok) {
            throw new Error(`Erro na API de eventos: ${response.status}`);
        }
        
        const eventos = await response.json();
        
        // Aqui você pode mostrar os eventos em um modal ou em uma seção da página
        if (Array.isArray(eventos) && eventos.length > 0) {
            // Cria uma string com os eventos para mostrar em um alerta (temporário)
            let eventosStr = `Eventos para ${dia}/${mes}/${ano}:\n\n`;
            eventos.forEach(evento => {
                eventosStr += `- ${evento.titulo || 'Evento sem título'}\n`;
            });
            
            alert(eventosStr);
            
            // Em uma implementação real, você poderia mostrar isso em um modal
            // ou em uma área específica da página
        } else {
            alert(`Não há eventos para ${dia}/${mes}/${ano}`);
        }
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao carregar eventos do dia:', error);
        alert(`Erro ao carregar eventos para ${dia}/${mes}/${ano}`);
    }
}

// Atualiza o gráfico
function atualizarGrafico(dados) {
    try {
        console.log('🔍 [DEBUG] Atualizando gráfico com dados:', dados);
        
        if (!dados || !dados.data) {
            console.warn('⚠️ [WARNING] Dados do gráfico inválidos, criando gráfico vazio');
            criarGraficoVazio();
            return;
        }
        
        // Verifica se Plotly está disponível
        if (typeof Plotly === 'undefined') {
            console.error('❌ [ERROR] Plotly não está carregado');
            criarGraficoVazio();
            return;
        }
        
        // Renderiza o gráfico com Plotly
        Plotly.newPlot('grafico-categoria', dados.data, dados.layout, {responsive: true});
        
        // Armazena os dados para uso posterior
        dadosGrafico = dados;
        
        console.log('✅ [SUCCESS] Gráfico atualizado com sucesso');
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao atualizar gráfico:', error);
        criarGraficoVazio();
    }
}

// Função para agrupar transações por data
function agruparTransacoesPorData(transacoes) {
    const grupos = {};
    
    if (!transacoes || !Array.isArray(transacoes)) {
        console.warn('⚠️ [WARNING] Transações inválidas para agrupamento:', transacoes);
        return grupos;
    }
    
    transacoes.forEach(transacao => {
        try {
            if (!transacao.data) return;
            
            const data = transacao.data;
            if (!grupos[data]) {
                grupos[data] = [];
            }
            grupos[data].push(transacao);
        } catch (error) {
            console.error('❌ [ERROR] Erro ao agrupar transação:', error, transacao);
        }
    });
    
    return grupos;
}

// Função para criar HTML de uma transação
function criarHTMLTransacao(transacao, isReceita = false) {
    try {
        if (!transacao) {
            console.warn('⚠️ [WARNING] Transação inválida para criar HTML');
            return '';
        }
        
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
            if (transacao.data) {
                const dataObj = new Date(transacao.data + 'T00:00:00');
                dataFormatada = dataObj.toLocaleDateString('pt-BR', {day: '2-digit', month: '2-digit'});
            }
        } catch (e) {
            console.error('❌ [ERROR] Erro ao formatar data da transação:', e);
            dataFormatada = transacao.data || '';
        }
        
        // Formata o valor com sinal + ou -
        const valorFormatado = formatarValor(transacao.valor);
        const descricao = transacao.descricao || 'Sem descrição';
        const categoria = transacao.categoria || 'outros';
        const categoriaFormatada = categoria.charAt(0).toUpperCase() + categoria.slice(1);
        
        return `
        <div class="expense-item d-flex justify-content-between align-items-center" data-filter="${filterClass}">
            <div class="d-flex align-items-center">
                <div class="category-pill me-3 ${categoriaClass} text-white">${emoji}</div>
                <div>
                    <h6 class="expense-item-title">${descricao}</h6>
                    <p class="expense-item-subtitle">${dataFormatada} • ${isReceita ? 'Receita' : categoriaFormatada}</p>
                </div>
            </div>
            <div class="expense-item-amount" style="color: ${isReceita ? '#28a745' : '#e74c3c'}">${isReceita ? '+' : '-'} ${valorFormatado}</div>
        </div>
        `;
    } catch (error) {
        console.error('❌ [ERROR] Erro ao criar HTML da transação:', error, transacao);
        return '';
    }
}

// Atualiza a lista de transações
function atualizarListaTransacoes(despesas, receitas) {
    try {
        console.log('🔍 [DEBUG] Atualizando lista de transações - Despesas:', Array.isArray(despesas) ? despesas.length : 0, 'Receitas:', Array.isArray(receitas) ? receitas.length : 0);
        
        // Container para as transações
        const todasTransacoesContainer = document.getElementById('todas-transacoes');
        if (!todasTransacoesContainer) {
            console.warn('⚠️ [WARNING] Container de transações não encontrado');
            return;
        }
        
        // Limpa o container
        todasTransacoesContainer.innerHTML = '';
        
        // Verifica se as listas são válidas
        if (!Array.isArray(despesas)) {
            console.warn('⚠️ [WARNING] Despesas não é um array válido:', despesas);
            despesas = [];
        }
        if (!Array.isArray(receitas)) {
            console.warn('⚠️ [WARNING] Receitas não é um array válido:', receitas);
            receitas = [];
        }
        
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
            try {
                let dataFormatada = '';
                try {
                    const dataObj = new Date(data + 'T00:00:00');
                    dataFormatada = dataObj.toLocaleDateString('pt-BR', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                    });
                } catch (e) {
                    console.error('❌ [ERROR] Erro ao formatar data do grupo:', e);
                    dataFormatada = data || 'Data desconhecida';
                }
                
                // Para todas as transações
                if (despesasPorData[data] || receitasPorData[data]) {
                    todasTransacoesContainer.innerHTML += `<div class="transaction-date ps-3">${dataFormatada}</div>`;
                    
                    // Adiciona receitas
                    if (receitasPorData[data] && Array.isArray(receitasPorData[data])) {
                        receitasPorData[data].forEach(receita => {
                            const htmlReceita = criarHTMLTransacao(receita, true);
                            if (htmlReceita) {
                                todasTransacoesContainer.innerHTML += htmlReceita;
                            }
                        });
                    }
                    
                    // Adiciona despesas
                    if (despesasPorData[data] && Array.isArray(despesasPorData[data])) {
                        despesasPorData[data].forEach(despesa => {
                            const htmlDespesa = criarHTMLTransacao(despesa, false);
                            if (htmlDespesa) {
                                todasTransacoesContainer.innerHTML += htmlDespesa;
                            }
                        });
                    }
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao processar data de transações:', error, data);
            }
        });
        
        console.log('✅ [SUCCESS] Lista de transações atualizada com sucesso');
        
    } catch (error) {
        console.error('❌ [ERROR] Erro ao atualizar lista de transações:', error);
        // Mostrar conteúdo de erro
        const todasTransacoesContainer = document.getElementById('todas-transacoes');
        if (todasTransacoesContainer) {
            todasTransacoesContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-exclamation-triangle text-warning" style="font-size: 48px;"></i>
                <p class="mt-3 text-muted">Erro ao carregar transações</p>
            </div>`;
        }
    }
}

// Funções para gerenciar orçamentos
function editarOrcamento(id) {
    console.log('🔍 [DEBUG] Editando orçamento:', id);
    
    // Buscar dados do orçamento e preencher o formulário
    fetch(`/api/orcamentos/${id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erro na API: ${response.status}`);
            }
            return response.json();
        })
        .then(orcamento => {
            console.log('✅ [SUCCESS] Dados do orçamento carregados:', orcamento);
            
            // Preenche o formulário
            const campos = [
                { id: 'orcamento-categoria', valor: orcamento.categoria },
                { id: 'orcamento-valor', valor: orcamento.valor_limite },
                { id: 'orcamento-periodicidade', valor: orcamento.periodicidade },
                { id: 'orcamento-alerta', valor: orcamento.alerta_percentual },
                { id: 'orcamento-tipo-perfil', valor: orcamento.tipo_perfil }
            ];
            
            campos.forEach(campo => {
                const elemento = document.getElementById(campo.id);
                if (elemento) {
                    elemento.value = campo.valor || '';
                } else {
                    console.warn(`⚠️ [WARNING] Campo do formulário não encontrado: ${campo.id}`);
                }
            });
            
            // Adiciona o ID do orçamento como atributo data no formulário
            const form = document.getElementById('form-orcamento');
            if (form) {
                form.setAttribute('data-id', id);
                
                // Altera o texto do botão
                const botaoSubmit = form.querySelector('button[type="submit"]');
                if (botaoSubmit) {
                    botaoSubmit.textContent = 'Atualizar Orçamento';
                }
                
                // Ativa a tab do formulário
                const tabNovoOrcamento = document.getElementById('tab-novo-orcamento');
                if (tabNovoOrcamento) {
                    tabNovoOrcamento.click();
                }
            }
        })
        .catch(error => {
            console.error('❌ [ERROR] Erro ao buscar dados do orçamento:', error);
            alert('Erro ao carregar dados do orçamento. Por favor, tente novamente.');
        });
}

function excluirOrcamento(id) {
    console.log('🔍 [DEBUG] Excluindo orçamento:', id);
    
    if (confirm('Tem certeza que deseja excluir este orçamento?')) {
        fetch(`/api/orcamentos/${id}`, {
            method: 'DELETE'
        })
        .then(response => {
            if (response.ok) {
                console.log('✅ [SUCCESS] Orçamento excluído com sucesso');
                alert('Orçamento excluído com sucesso!');
                carregarOrcamentos();
            } else {
                throw new Error(`Erro na API: ${response.status}`);
            }
        })
        .catch(error => {
            console.error('❌ [ERROR] Erro ao excluir orçamento:', error);
            alert('Ocorreu um erro ao excluir o orçamento. Por favor, tente novamente.');
        });
    }
}

// Verificação de integridade dos elementos DOM
function verificarElementosDOM() {
    console.log('🔍 [DEBUG] Verificando elementos DOM essenciais...');
    
    const elementosEssenciais = [
        'total-despesas',
        'total-receitas', 
        'total-saldo',
        'percentual-economia',
        'period-subtitle',
        'period-subtitle-receitas',
        'period-subtitle-saldo',
        'period-subtitle-economia'
    ];
    
    const elementosAusentes = [];
    
    elementosEssenciais.forEach(id => {
        const elemento = document.getElementById(id);
        if (!elemento) {
            elementosAusentes.push(id);
            console.error(`❌ [ERROR] Elemento essencial não encontrado: #${id}`);
        } else {
            console.log(`✅ [SUCCESS] Elemento encontrado: #${id}`);
        }
    });
    
    if (elementosAusentes.length > 0) {
        console.error('❌ [ERROR] Elementos DOM ausentes:', elementosAusentes);
        mostrarErro(`Erro na interface: elementos ausentes (${elementosAusentes.join(', ')})`);
        return false;
    }
    
    console.log('✅ [SUCCESS] Todos os elementos DOM essenciais estão presentes');
    return true;
}

// Teste de conectividade com as APIs
async function testarAPIs() {
    console.log('🔍 [DEBUG] Testando conectividade com APIs...');
    
    const apis = [
        '/api/resumo?periodo=semana&tipo_perfil=pessoal',
        '/api/despesas?periodo=semana&tipo_perfil=pessoal',
        '/api/receitas?periodo=semana&tipo_perfil=pessoal'
    ];
    
    for (const api of apis) {
        try {
            console.log(`🔍 [DEBUG] Testando: ${api}`);
            const response = await fetch(api);
            console.log(`🔍 [DEBUG] Status ${api}:`, response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log(`✅ [SUCCESS] API funcionando: ${api}`);
                console.log(`📊 [DATA] Amostra de dados:`, JSON.stringify(data).substring(0, 200) + '...');
            } else {
                const errorText = await response.text();
                console.error(`❌ [ERROR] API com erro ${api}:`, response.status, errorText);
            }
        } catch (error) {
            console.error(`❌ [ERROR] Falha na conexão ${api}:`, error.message);
        }
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 [INIT] Dashboard inicializando...');
    
    // Verificar se todos os elementos DOM essenciais existem
    if (!verificarElementosDOM()) {
        console.error('❌ [FATAL] Falha na verificação de elementos DOM');
        // Continua mesmo assim, mas com aviso
    }
    
    // Testar APIs (não-bloqueante)
    testarAPIs().catch(error => {
        console.error('❌ [ERROR] Erro nos testes de API:', error);
    });
    
    console.log('🔄 [INFO] Iniciando configuração de event listeners...');
    
    // Seletor de perfil (pessoal/empresarial)
    const profilePersonal = document.getElementById('profile-personal');
    const profileBusiness = document.getElementById('profile-business');
    
    if (profilePersonal) {
        profilePersonal.addEventListener('click', function() {
            console.log('🔄 [INFO] Mudando para perfil pessoal');
            profilePersonal.classList.add('active');
            if (profileBusiness) {
                profileBusiness.classList.remove('active');
            }
            perfilAtual = 'pessoal';
            carregarDados(periodoAtual);
            console.log('✅ [SUCCESS] Perfil alterado para pessoal');
        });
    }
    
    if (profileBusiness && !profileBusiness.classList.contains('disabled')) {
        profileBusiness.addEventListener('click', function() {
            console.log('🔄 [INFO] Mudando para perfil empresarial');
            profileBusiness.classList.add('active');
            if (profilePersonal) {
                profilePersonal.classList.remove('active');
            }
            perfilAtual = 'empresarial';
            carregarDados(periodoAtual);
            console.log('✅ [SUCCESS] Perfil alterado para empresarial');
        });
    }
    
    // Event listener para os botões de período
    document.querySelectorAll('.period-btn').forEach(botao => {
        botao.addEventListener('click', function() {
            console.log('🔄 [INFO] Mudando período para:', this.dataset.period);
            
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
            console.log('✅ [SUCCESS] Período alterado para:', this.dataset.period);
        });
    });
    
    // Botão para aplicar datas personalizadas
    const btnAplicarDatas = document.getElementById('btn-aplicar-datas');
    if (btnAplicarDatas) {
        btnAplicarDatas.addEventListener('click', function() {
            console.log('🔄 [INFO] Aplicando datas personalizadas');
            
            const dataInicio = document.getElementById('date-inicio')?.value;
            const dataFim = document.getElementById('date-fim')?.value;
            
            if (!dataInicio || !dataFim) {
                alert('Por favor, selecione as datas de início e fim');
                return;
            }
            
            console.log('🔍 [DEBUG] Datas selecionadas:', dataInicio, 'até', dataFim);
            
            // Fecha o modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('modalDatePicker'));
            if (modal) {
                modal.hide();
            }
            
            // Remove a classe ativa de todos os botões de período
            document.querySelectorAll('.period-btn').forEach(btn => {
                btn.classList.remove('btn-success');
                btn.classList.add('btn-outline-success');
            });
            
            // Adiciona a classe ativa ao botão personalizado
            const btnCustom = document.querySelector('.period-btn[data-period="custom"]');
            if (btnCustom) {
                btnCustom.classList.remove('btn-outline-success');
                btnCustom.classList.add('btn-success');
            }
            
            // Carrega os dados para o período personalizado
            carregarDados('custom');
            console.log('✅ [SUCCESS] Período personalizado aplicado');
        });
    }
    
    // Event listener para os botões de tipo de gráfico
    const btnChartCategory = document.getElementById('btn-chart-category');
    if (btnChartCategory) {
        btnChartCategory.addEventListener('click', function() {
            console.log('🔄 [INFO] Carregando gráfico por categoria');
            fetch(`/api/grafico/por_categoria?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                    throw new Error(`Erro na API: ${response.status}`);
                })
                .then(dados => {
                    atualizarGrafico(dados);
                    console.log('✅ [SUCCESS] Gráfico por categoria carregado');
                })
                .catch(error => {
                    console.error('❌ [ERROR] Erro ao carregar gráfico por categoria:', error);
                });
        });
    }
    
    const btnChartTime = document.getElementById('btn-chart-time');
    if (btnChartTime) {
        btnChartTime.addEventListener('click', function() {
            console.log('🔄 [INFO] Carregando gráfico por tempo');
            fetch(`/api/grafico/por_tempo?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                    throw new Error(`Erro na API: ${response.status}`);
                })
                .then(dados => {
                    atualizarGrafico(dados);
                    console.log('✅ [SUCCESS] Gráfico por tempo carregado');
                })
                .catch(error => {
                    console.error('❌ [ERROR] Erro ao carregar gráfico por tempo:', error);
                });
        });
    }
    
    const btnChartComparison = document.getElementById('btn-chart-comparison');
    if (btnChartComparison) {
        btnChartComparison.addEventListener('click', function() {
            console.log('🔄 [INFO] Carregando gráfico comparativo');
            fetch(`/api/grafico/comparativo?periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`)
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                    throw new Error(`Erro na API: ${response.status}`);
                })
                .then(dados => {
                    atualizarGrafico(dados);
                    console.log('✅ [SUCCESS] Gráfico comparativo carregado');
                })
                .catch(error => {
                    console.error('❌ [ERROR] Erro ao carregar gráfico comparativo:', error);
                });
        });
    }
    
    // Event listener para pesquisa de transações
    const searchTransactions = document.getElementById('search-transactions');
    if (searchTransactions) {
        searchTransactions.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            console.log('🔍 [DEBUG] Pesquisando transações:', searchTerm);
            
            document.querySelectorAll('#todas-transacoes .expense-item').forEach(item => {
                const title = item.querySelector('.expense-item-title')?.textContent?.toLowerCase() || '';
                const subtitle = item.querySelector('.expense-item-subtitle')?.textContent?.toLowerCase() || '';
                
                if (title.includes(searchTerm) || subtitle.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Event listeners para os filtros por chips
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', function() {
            console.log('🔄 [INFO] Aplicando filtro:', this.dataset.filter);
            
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
            
            console.log('✅ [SUCCESS] Filtro aplicado:', filtro);
        });
    });
    
    // Event listener para o formulário de despesa
    const formDespesa = document.getElementById('form-despesa');
    if (formDespesa) {
        formDespesa.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log('🔄 [INFO] Enviando formulário de despesa');
            
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
            
            console.log('🔍 [DEBUG] Dados da despesa:', dadosDespesa);
            
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
                    console.log('✅ [SUCCESS] Despesa salva com sucesso');
                    
                    // Fecha o modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Recarrega os dados
                    carregarDados(periodoAtual);
                    
                    // Limpa o formulário
                    this.reset();
                    
                    // Define a data para hoje
                    const hoje = new Date();
                    const despesaData = document.getElementById('despesa-data');
                    if (despesaData) {
                        despesaData.valueAsDate = hoje;
                    }
                    
                    // Mostra mensagem de sucesso
                    alert('Despesa adicionada com sucesso!');
                } else {
                    const erro = await response.json();
                    throw new Error(erro.error || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao salvar despesa:', error);
                alert(`Erro: ${error.message}`);
            }
        });
    }
    
    // Event listener para o formulário de receita
    const formReceita = document.getElementById('form-receita');
    if (formReceita) {
        formReceita.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log('🔄 [INFO] Enviando formulário de receita');
            
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
            
            console.log('🔍 [DEBUG] Dados da receita:', dadosReceita);
            
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
                    console.log('✅ [SUCCESS] Receita salva com sucesso');
                    
                    // Fecha o modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Recarrega os dados
                    carregarDados(periodoAtual);
                    
                    // Limpa o formulário
                    this.reset();
                    
                    // Define a data para hoje
                    const hoje = new Date();
                    const receitaData = document.getElementById('receita-data');
                    if (receitaData) {
                        receitaData.valueAsDate = hoje;
                    }
                    
                    // Mostra mensagem de sucesso
                    alert('Receita adicionada com sucesso!');
                } else {
                    const erro = await response.json();
                    throw new Error(erro.error || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao salvar receita:', error);
                alert(`Erro: ${error.message}`);
            }
        });
    }
    
    // Event listener para o formulário de transferência
    const formTransferencia = document.getElementById('form-transferencia');
    if (formTransferencia) {
        formTransferencia.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log('🔄 [INFO] Enviando formulário de transferência');
            
            // Verificar se a conta de origem e destino são diferentes
            const origem = document.getElementById('transferencia-origem')?.value;
            const destino = document.getElementById('transferencia-destino')?.value;
            
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
            
            console.log('🔍 [DEBUG] Dados da transferência:', dadosTransferencia);
            
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
                    console.log('✅ [SUCCESS] Transferência salva com sucesso');
                    
                    // Fecha o modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalAddTransacao'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Recarrega os dados
                    carregarDados(periodoAtual);
                    
                    // Limpa o formulário
                    this.reset();
                    
                    // Define a data para hoje
                    const hoje = new Date();
                    const transferenciaData = document.getElementById('transferencia-data');
                    if (transferenciaData) {
                        transferenciaData.valueAsDate = hoje;
                    }
                    
                    // Mostra mensagem de sucesso
                    alert('Transferência registrada com sucesso!');
                } else {
                    const erro = await response.json();
                    throw new Error(erro.error || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao salvar transferência:', error);
                alert(`Erro: ${error.message}`);
            }
        });
    }
    
    // Event listener para o formulário de orçamento
    const formOrcamento = document.getElementById('form-orcamento');
    if (formOrcamento) {
        formOrcamento.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log('🔄 [INFO] Enviando formulário de orçamento');
            
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
            
            console.log('🔍 [DEBUG] Dados do orçamento:', dadosOrcamento, 'Edição:', isEdicao);
            
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
                    console.log('✅ [SUCCESS] Orçamento salvo com sucesso');
                    
                    // Fecha o modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalBudget'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Recarrega os dados
                    carregarOrcamentos();
                    
                    // Limpa o formulário
                    this.reset();
                    this.removeAttribute('data-id');
                    
                    // Restaura o texto do botão
                    const botaoSubmit = this.querySelector('button[type="submit"]');
                    if (botaoSubmit) {
                        botaoSubmit.textContent = 'Salvar Orçamento';
                    }
                    
                    // Mostra mensagem de sucesso
                    alert(`Orçamento ${isEdicao ? 'atualizado' : 'salvo'} com sucesso!`);
                    
                    // Ativa a tab de listar orçamentos
                    const tabListarOrcamentos = document.getElementById('tab-listar-orcamentos');
                    if (tabListarOrcamentos) {
                        tabListarOrcamentos.click();
                    }
                } else {
                    const erro = await response.json();
                    throw new Error(erro.error || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao salvar orçamento:', error);
                alert(`Erro: ${error.message}`);
            }
        });
    }
    
    // Event listener para o formulário de meta financeira
    const formMetaFinanceira = document.getElementById('form-meta-financeira');
    if (formMetaFinanceira) {
        formMetaFinanceira.addEventListener('submit', async function(event) {
            event.preventDefault();
            console.log('🔄 [INFO] Enviando formulário de meta financeira');
            
            // Cria um objeto FormData com os dados do formulário
            const formData = new FormData(this);
            
            // Converte FormData para objeto JSON
            const dadosMeta = {};
            formData.forEach((valor, chave) => {
                dadosMeta[chave] = valor;
            });
            
            console.log('🔍 [DEBUG] Dados da meta:', dadosMeta);
            
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
                    console.log('✅ [SUCCESS] Meta salva com sucesso');
                    
                    // Fecha o modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalFinancialGoal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Recarrega os dados
                    carregarMetas();
                    
                    // Limpa o formulário
                    this.reset();
                    
                    // Mostra mensagem de sucesso
                    alert('Meta financeira adicionada com sucesso!');
                } else {
                    const erro = await response.json();
                    throw new Error(erro.error || 'Erro desconhecido');
                }
            } catch (error) {
                console.error('❌ [ERROR] Erro ao salvar meta:', error);
                alert(`Erro: ${error.message}`);
            }
        });
    }
    
    // Event listener para mostrar/esconder campos adicionais
    const despesaParcelada = document.getElementById('despesa-parcelada');
    if (despesaParcelada) {
        despesaParcelada.addEventListener('change', function() {
            const divParcelas = document.getElementById('div-parcelas');
            if (divParcelas) {
                divParcelas.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    
    const receitaRecorrente = document.getElementById('receita-recorrente');
    if (receitaRecorrente) {
        receitaRecorrente.addEventListener('change', function() {
            const divPeriodicidade = document.getElementById('div-periodicidade');
            if (divPeriodicidade) {
                divPeriodicidade.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    
    // Botão para compartilhar gráfico via WhatsApp
    const btnShareChart = document.getElementById('btn-share-chart');
    if (btnShareChart) {
        btnShareChart.addEventListener('click', function() {
            console.log('🔄 [INFO] Compartilhando gráfico via WhatsApp');
            
            // Obtém a URL da imagem do gráfico
            const urlGrafico = `/api/grafico/imagem?tipo=categoria&periodo=${periodoAtual}&tipo_perfil=${perfilAtual}`;
            
            // Cria a URL do WhatsApp
            const textoCompartilhamento = `Veja meu resumo financeiro ${periodoAtual === 'dia' ? 'de hoje' : 
                                          periodoAtual === 'semana' ? 'desta semana' : 
                                          periodoAtual === 'mes' ? 'deste mês' : 'deste ano'}:`;
            const urlWhatsApp = `https://wa.me/?text=${encodeURIComponent(textoCompartilhamento + "\n" + urlGrafico)}`;
            
            // Abre a URL
            window.open(urlWhatsApp, '_blank');
            console.log('✅ [SUCCESS] WhatsApp aberto para compartilhamento');
        });
    }
    
    // Inicialização do dashboard
    console.log('🔄 [INFO] Configurando valores padrão...');
    
    // Define a data atual como padrão para os campos de data
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    
    // Campos de data para definir como hoje
    const camposData = [
        'despesa-data',
        'receita-data',
        'transferencia-data'
    ];
    
    camposData.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.valueAsDate = hoje;
            console.log(`✅ [SUCCESS] Data padrão definida para ${id}`);
        }
    });
    
    // Campos de período personalizado
    const dateInicio = document.getElementById('date-inicio');
    const dateFim = document.getElementById('date-fim');
    
    if (dateInicio) {
        dateInicio.valueAsDate = new Date(hoje.getFullYear(), hoje.getMonth(), 1); // Primeiro dia do mês
        console.log('✅ [SUCCESS] Data início padrão definida');
    }
    
    if (dateFim) {
        dateFim.valueAsDate = hoje;
        console.log('✅ [SUCCESS] Data fim padrão definida');
    }
    
    // Meta financeira - data limite padrão: 6 meses a partir de hoje
    const metaDataAlvo = document.getElementById('meta-data-alvo');
    if (metaDataAlvo) {
        const dataLimiteMetaFinanceira = new Date(hoje);
        dataLimiteMetaFinanceira.setMonth(dataLimiteMetaFinanceira.getMonth() + 6);
        metaDataAlvo.valueAsDate = dataLimiteMetaFinanceira;
        console.log('✅ [SUCCESS] Data limite da meta definida');
    }
    
    console.log('🔄 [INFO] Iniciando carregamento de dados com delay...');
    
    // Carrega os dados iniciais COM DELAY para garantir que tudo está pronto
    setTimeout(() => {
        console.log('🔄 [INFO] Carregando dados iniciais...');
        carregarDados(periodoAtual);
    }, 500); // Aumentado para 500ms para garantir que tudo esteja pronto
    
    console.log('✅ [SUCCESS] Dashboard inicializado com sucesso');
});