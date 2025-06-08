document.addEventListener('DOMContentLoaded', () => {
    const gerarPDFbtn = document.getElementById('gerarPDFbtn');
    const relatorioContainer = document.getElementById('report-container');
    const monitorSelect = document.getElementById('monitorSelect');

    // --- FUNÇÕES DE FORMATAÇÃO ---
    const formatDateTime = (dateString) => {
        const date = new Date(dateString);
        const pad = (num) => num.toString().padStart(2, '0');
        const day = pad(date.getDate());
        const month = pad(date.getMonth() + 1);
        const year = date.getFullYear();
        const hours = pad(date.getHours());
        const minutes = pad(date.getMinutes());
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    };

    const formatSecondsToMinutes = (totalSeconds) => {
        if (totalSeconds < 60) return `${totalSeconds}s`;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}m ${seconds}s`;
    };

    // --- CARREGA OS MONITORES DA API ---
    async function loadMonitors() {
        try {
            const response = await fetch('php/api-gateway.php?endpoint=monitors');
            if (!response.ok) {
                throw new Error('Erro de rede ao buscar monitores.');
            }
            const monitors = await response.json();

            monitorSelect.innerHTML = '<option value="">Selecione um Monitor</option>'; 
            
            monitors.forEach(monitor => {
                const option = document.createElement('option');
                option.value = monitor.id;
                option.textContent = monitor.monitor_name;
                option.dataset.monitorName = monitor.monitor_name; 
                monitorSelect.appendChild(option);
            });

        } catch (error) {
            monitorSelect.innerHTML = '<option value="">Erro ao carregar monitores</option>';
            console.error("Falha ao carregar monitores:", error);
        }
    }

    // --- LÓGICA PRINCIPAL PARA GERAR O RELATÓRIO ---
    gerarPDFbtn.addEventListener('click', async () => {
        const companyName = document.getElementById('companyName').value.trim();
        const monitorId = monitorSelect.value;
        const startDateStr = document.getElementById('startDate').value;
        const endDateStr = document.getElementById('endDate').value;
        
        const selectedOption = monitorSelect.options[monitorSelect.selectedIndex];
        const monitorName = selectedOption.dataset.monitorName || 'N/A';

        if (!companyName || !monitorId || !startDateStr || !endDateStr) {
            alert("Por favor, preencha todos os campos: Nome da Empresa, Monitor, Data de Início e Fim.");
            return;
        }
        
        gerarPDFbtn.textContent = 'Gerando...';
        gerarPDFbtn.disabled = true;

        try {
            const params = new URLSearchParams({
                monitor_id: monitorId,
                start_date: startDateStr,
                end_date: endDateStr
            });

            const response = await fetch(`php/api-gateway.php?endpoint=report_data&${params}`);
            
            if (!response.ok) {
                 const errorData = await response.json();
                 throw new Error(errorData.error || 'Erro de rede ao buscar dados do relatório.');
            }

            const reportData = await response.json();

            let totalDowntimeSeconds = 0;
            const incidents = [];
            
            reportData.forEach(entry => {
                if (entry.success == 0) {
                    const downtime = parseInt(entry.request_interval, 10);
                    totalDowntimeSeconds += downtime;
                    incidents.push({
                        dateTime: entry.timestamp,
                        duration: downtime,
                        status: { text: 'Falha na Verificação', class: 'bg-red-100 text-red-800' }
                    });
                }
            });

            const totalChecks = reportData.length;
            const failedChecks = incidents.length;
            const uptimePercentage = totalChecks > 0 ? (((totalChecks - failedChecks) / totalChecks) * 100).toFixed(4) : "100.0000";

            document.getElementById('reportCompanyName').textContent = companyName;
            document.getElementById('reportDateRange').textContent = `Período: ${new Date(startDateStr+'T00:00:00').toLocaleDateString('pt-BR')} - ${new Date(endDateStr+'T00:00:00').toLocaleDateString('pt-BR')}`;
            document.getElementById('reportUptime').textContent = `${uptimePercentage}%`;
            document.getElementById('reportIncidents').textContent = failedChecks;
            document.getElementById('reportDowntime').textContent = formatSecondsToMinutes(totalDowntimeSeconds);

            const tbody = document.getElementById('reportIncidentTbody');
            tbody.innerHTML = '';
            if(incidents.length > 0){
                incidents.forEach(incident => {
                    const row = `
                        <tr>
                            <td class="p-3 text-sm text-gray-700 border">${formatDateTime(incident.dateTime)}</td>
                            <td class="p-3 text-sm text-gray-700 border">${formatSecondsToMinutes(incident.duration)}</td>
                            <td class="p-3 text-sm text-gray-700 border">
                                <span class="px-2 py-1 rounded ${incident.status.class}">${incident.status.text}</span>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += row;
                });
            } else {
                 tbody.innerHTML = '<tr><td colspan="3" class="p-3 text-center text-gray-500 border">Nenhum incidente registrado neste período.</td></tr>';
            }

            document.getElementById('reportFooter').textContent = `Relatório gerado para o monitor "${monitorName}" | © ${new Date().getFullYear()} ${companyName}.`;

            relatorioContainer.classList.remove('hidden');

            const reportElement = document.getElementById('report-preview');
            const options = {
                margin: [0.5, 0.5, 0.5, 0.5],
                filename: `relatorio_sla_${monitorName.toLowerCase().replace(/\s/g, '_')}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
            };
            html2pdf().from(reportElement).set(options).save();

        } catch (error) {
            alert(`Erro ao gerar relatório: ${error.message}`);
            console.error("Falha na geração do relatório:", error);
        } finally {
            gerarPDFbtn.textContent = 'Gerar e Baixar PDF';
            gerarPDFbtn.disabled = false;
        }
    });

    loadMonitors();
});