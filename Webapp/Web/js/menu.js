document.addEventListener('DOMContentLoaded', function () {
    function loadMonitors() {
        // Busca os dados dos monitores e dos incidentes simultaneamente
        Promise.all([
            fetch('php/get_monitors.php').then(res => res.json()),
            fetch('php/incidentes.php').then(res => res.json())
        ])
        .then(([monitorData, incidentData]) => {
            const monitorsList = document.getElementById('monitors-list');
            const statusBannerContainer = document.getElementById('status-banner-container');
            monitorsList.innerHTML = ''; // Limpa a lista antes de adicionar os novos elementos

            // Filtra incidentes que ainda não foram resolvidos
            const activeIncidents = incidentData.sucesso ? incidentData.incidentes.filter(inc => inc.resolvido_em === null) : [];
            let overallStatus = 'operational'; // Status inicial padrão

            // Itera sobre cada monitor para criar seu elemento visual
            if (monitorData.data && monitorData.data.length > 0) {
                monitorData.data.forEach(monitor => {
                    // Determina o status geral com base no monitor de maior criticidade
                    if (monitor.current_status === 'downtime' || monitor.current_status === 'critical') {
                        overallStatus = 'critical';
                    } else if (monitor.current_status === 'degraded' && overallStatus !== 'critical') {
                        overallStatus = 'degraded';
                    }

                    // Cria o contêiner principal para o monitor
                    const monitorElement = document.createElement('div');
                    monitorElement.className = 'bg-white border rounded p-4 shadow-sm';

                    // Cria o cabeçalho com o nome e o status atual
                    const header = document.createElement('div');
                    header.className = 'flex justify-between items-center mb-2';
                    header.innerHTML = `
                        <h3 class="text-lg font-semibold text-gray-800">${monitor.monitor_name}</h3>
                        <span class="text-sm font-semibold capitalize text-gray-700">${(monitor.current_status || 'N/A').replace('_', ' ')}</span>
                    `;

                    // Cria a linha do tempo para o histórico de 90 dias
                    const timeline = document.createElement('div');
                    timeline.className = 'flex gap-[1px] h-2 mt-2';

                    // Adiciona uma barra para cada dia no histórico
                    monitor.history_90_days.forEach((day, index) => {
                        const bar = document.createElement('div');
                        bar.className = 'flex-1 relative'; // `relative` para posicionar o tooltip

                        // Define a cor da barra com base no status do dia
                        if (day.status === 'available') {
                            bar.classList.add('bg-green-500');
                        } else if (day.status === 'unavailable') {
                            bar.classList.add('bg-red-500');
                        } else {
                            bar.classList.add('bg-gray-300');
                        }
                        
                        // Cria o elemento do tooltip, inicialmente oculto
                        const tooltip = document.createElement('div');
                        tooltip.className = 'absolute hidden bg-gray-800 text-white text-xs rounded py-1 px-2 z-10 whitespace-nowrap bottom-full left-1/2 -translate-x-1/2 mb-2';
                        
                        const date = new Date();
                        date.setDate(date.getDate() - (89 - index));
                        tooltip.innerHTML = `
                            <div class="text-center">${date.toLocaleDateString('pt-BR')}</div>
                            <div class="text-center">SLA: ${day.sla}%</div>
                        `;
                        bar.appendChild(tooltip);

                        // Mostra e esconde o tooltip ao passar o mouse
                        bar.addEventListener('mouseenter', () => tooltip.classList.remove('hidden'));
                        bar.addEventListener('mouseleave', () => tooltip.classList.add('hidden'));

                        timeline.appendChild(bar);
                    });
                    
                    // Adiciona as legendas "90 dias atrás" e "Hoje"
                    const timelineLabels = document.createElement('div');
                    timelineLabels.className = 'flex justify-between items-center text-xs text-gray-500 mt-1';
                    timelineLabels.innerHTML = `
                        <span>90 dias atrás</span>
                        <span>Hoje</span>
                    `;
                    
                    // Monta o elemento final do monitor
                    monitorElement.appendChild(header);
                    monitorElement.appendChild(timeline);
                    monitorElement.appendChild(timelineLabels);
                    monitorsList.appendChild(monitorElement);
                });
            }

            // Se existirem incidentes ativos, o status geral se torna crítico
            if (activeIncidents.length > 0) {
                overallStatus = 'critical';
                const incidentContainer = document.createElement('div');
                incidentContainer.className = 'space-y-4 mb-6'; // Adicionado margin-bottom
                incidentContainer.innerHTML = '<h3 class="text-xl font-semibold text-gray-800">Incidentes Ativos</h3>';
                
                activeIncidents.forEach(incident => {
                    const incidentElement = document.createElement('div');
                    incidentElement.className = 'bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800 p-4';
                    incidentElement.innerHTML = `
                        <p class="font-bold">${incident.titulo}</p>
                        <p class="text-sm">${incident.descricao}</p>
                    `;
                    incidentContainer.appendChild(incidentElement);
                });
                // Adiciona os incidentes no topo da lista
                monitorsList.prepend(incidentContainer);
            }

            // Atualiza o banner de status com base no status geral
            let bannerHTML = '';
            if (overallStatus === 'critical') {
                bannerHTML = `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center">
                            <svg class="h-5 w-5 text-red-500 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v4a1 1 0 102 0V7zm-1 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path></svg>
                            <span class="font-medium text-red-800">Um ou mais serviços estão com problemas críticos ou incidentes ativos.</span>
                        </div>
                    </div>`;
            } else if (overallStatus === 'degraded') {
                bannerHTML = `
                    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center">
                            <svg class="h-5 w-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.636-1.22 2.85-1.22 3.486 0l5.58 10.762c.636 1.22-.472 2.639-1.743 2.639H4.42c-1.27 0-2.379-1.419-1.743-2.639l5.58-10.762zM10 14a1 1 0 110-2 1 1 0 010 2zm-1-3a1 1 0 001 1h.01a1 1 0 100-2H10a1 1 0 00-1 1z" clip-rule="evenodd"></path></svg>
                            <span class="font-medium text-yellow-800">Alguns serviços estão operando com performance degradada.</span>
                        </div>
                    </div>`;
            } else {
                bannerHTML = `
                    <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                        <div class="flex items-center">
                            <svg class="h-5 w-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>
                            <span class="font-medium text-green-800">Todos os recursos estão operacionais.</span>
                        </div>
                    </div>`;
            }
            statusBannerContainer.innerHTML = bannerHTML;

        })
        .catch(error => {
            console.error('Erro ao carregar dados:', error);
            document.getElementById('monitors-list').innerHTML = '<p class="text-red-500">Não foi possível carregar os dados dos monitores.</p>';
        });
    }

    loadMonitors();
});