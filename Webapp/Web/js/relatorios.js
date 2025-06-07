document.addEventListener('DOMContentLoaded', () => {
    // <-- CORREÇÃO AQUI: O ID do botão foi ajustado para 'gerarPDFbtn', como está no seu HTML.
    const gerarPDFbtn = document.getElementById('gerarPDFbtn');
    const relatorioContainer = document.getElementById('report-container');

    // --- FUNÇÕES AUXILIARES ---

    /**
     * Gera um número inteiro aleatório entre min e max (inclusivo).
     * @param {number} min - O valor mínimo.
     * @param {number} max - O valor máximo.
     * @returns {number} - O número inteiro aleatório.
     */
    const getRandomInt = (min, max) => {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    };

    /**
     * Formata um objeto Date para uma string "dd/mm/aaaa HH:MM".
     * @param {Date} date - O objeto Date a ser formatado.
     * @returns {string} - A data formatada.
     */
    const formatDateTime = (date) => {
        const pad = (num) => num.toString().padStart(2, '0');
        const day = pad(date.getDate());
        const month = pad(date.getMonth() + 1);
        const year = date.getFullYear();
        const hours = pad(date.getHours());
        const minutes = pad(date.getMinutes());
        return `${day}/${month}/${year} ${hours}:${minutes}`;
    };

    /**
      * Formata uma string de data (YYYY-MM-DD) para um objeto Date, 
      * garantindo que a data seja interpretada corretamente para evitar problemas de fuso horário.
      * @param {string} dateString - A data no formato 'YYYY-MM-DD'.
      * @returns {Date}
      */
    const parseDateString = (dateString) => {
        return new Date(dateString + 'T00:00:00');
    }

    /**
     * Formata segundos para uma string "Xm Ys".
     * @param {number} totalSeconds - O total de segundos.
     * @returns {string} - A string formatada.
     */
    const formatSecondsToMinutes = (totalSeconds) => {
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}m ${seconds}s`;
    };

    // --- LÓGICA PRINCIPAL ---

    // Adiciona uma verificação para garantir que o botão foi encontrado antes de adicionar o listener
    if (gerarPDFbtn) {
        gerarPDFbtn.addEventListener('click', () => {
            // 1. Coletar dados do formulário
            const companyName = document.getElementById('companyName').value.trim();
            const serviceName = document.getElementById('servico').value;
            const startDateStr = document.getElementById('startDate').value;
            const endDateStr = document.getElementById('endDate').value;

            // Validação simples
            if (!companyName || !startDateStr || !endDateStr) {
                alert("Por favor, preencha o nome da empresa e as datas de início e fim.");
                return;
            }

            const startDate = parseDateString(startDateStr);
            const endDate = parseDateString(endDateStr);

            // 2. Gerar dados aleatórios para o relatório
            const totalIncidents = getRandomInt(1, 8);
            let totalDowntimeSeconds = 0;
            const incidentsData = [];

            const timeDifference = endDate.getTime() - startDate.getTime();
            // Evitar divisão por zero se houver 0 incidentes
            const interval = totalIncidents > 0 ? timeDifference / (totalIncidents + 1) : 0;

            const statuses = [
                { text: 'Interrupção Parcial', class: 'bg-red-100 text-red-800' },
                { text: 'Desempenho Degradado', class: 'bg-yellow-100 text-yellow-800' },
                { text: 'Interrupção Total', class: 'bg-red-200 text-red-900 font-bold' }
            ];

            for (let i = 0; i < totalIncidents; i++) {
                const incidentDuration = getRandomInt(60, 900);
                totalDowntimeSeconds += incidentDuration;

                const incidentTimestamp = startDate.getTime() + (interval * (i + 1));
                const incidentDate = new Date(incidentTimestamp);

                incidentsData.push({
                    dateTime: incidentDate,
                    service: serviceName === 'Todos os Serviços' ? ['API Principal', 'Website', 'Banco de Dados'][getRandomInt(0, 2)] : serviceName,
                    status: statuses[getRandomInt(0, statuses.length - 1)],
                    duration: formatSecondsToMinutes(incidentDuration)
                });
            }

            const totalPeriodSeconds = timeDifference / 1000;
            const uptime = totalPeriodSeconds > 0 ? (100 - (totalDowntimeSeconds / totalPeriodSeconds) * 100).toFixed(4) : "100.0000";

            // 3. Popular o HTML do relatório com os dados gerados
            document.getElementById('reportCompanyName').textContent = companyName;

            // <-- CORREÇÃO ADICIONAL: corrigido um pequeno erro de digitação em 'toLocaleDateString'
            document.getElementById('reportDateRange').textContent = `Período: ${startDate.toLocaleDateString('pt-BR')} - ${endDate.toLocaleDateString('pt-BR')}`;

            document.getElementById('reportUptime').textContent = `${uptime}%`;
            document.getElementById('reportIncidents').textContent = totalIncidents;
            document.getElementById('reportDowntime').textContent = formatSecondsToMinutes(totalDowntimeSeconds);

            const tbody = document.getElementById('reportIncidentTbody');
            tbody.innerHTML = '';
            incidentsData.sort((a, b) => a.dateTime - b.dateTime).forEach(incident => {
                const row = `
                    <tr>
                        <td class="p-3 text-sm text-gray-700 border">${formatDateTime(incident.dateTime)}</td>
                        <td class="p-3 text-sm text-gray-700 border">${incident.service}</td>
                        <td class="p-3 text-sm text-gray-700 border">
                            <span class="px-2 py-1 rounded ${incident.status.class}">${incident.status.text}</span>
                        </td>
                        <td class="p-3 text-sm text-gray-700 border">${incident.duration}</td>
                    </tr>
                `;
                tbody.innerHTML += row;
            });

            document.getElementById('reportFooter').textContent = `Relatório gerado automaticamente - WatchUp | © ${new Date().getFullYear()} ${companyName}. Todos os direitos reservados.`;

            // 4. Exibir o container do relatório
            relatorioContainer.classList.remove('hidden');

            // 5. Gerar o PDF a partir do conteúdo populado
            const reportElement = document.getElementById('report-preview');
            const options = {
                margin: [0.5, 0.5, 0.5, 0.5],
                filename: `relatorio_sla_${companyName.toLowerCase().replace(/\s/g, '_')}.pdf`,
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
            };

            html2pdf().from(reportElement).set(options).save();
        });
    } else {
        console.error("O botão com o ID 'gerarPDFbtn' não foi encontrado. Verifique o ID no arquivo HTML.");
    }
});