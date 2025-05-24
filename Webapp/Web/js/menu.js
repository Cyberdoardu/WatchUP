document.addEventListener('DOMContentLoaded', function () {
    function loadMonitors() {
        fetch('php/get_monitors.php')
            .then(response => response.json())
            .then(data => {
                const monitorsList = document.getElementById('monitors-list');
                monitorsList.innerHTML = '';

                data.data.forEach(monitor => {
                    const monitorElement = document.createElement('div');
                    monitorElement.classList.add('bg-white', 'border', 'rounded', 'p-4', 'shadow-sm');

                    const header = document.createElement('div');
                    header.classList.add('flex', 'justify-between', 'items-center', 'mb-2');
                    header.innerHTML = `
                        <h3 class="text-lg font-semibold text-gray-800">${monitor.monitor_name}</h3>
                        <span class="text-sm text-gray-600">${monitor.current_status}</span>
                    `;

                    const timeline = document.createElement('div');
                    timeline.classList.add('flex', 'gap-[1px]', 'h-2', 'mt-2');

                    monitor.history_90_days.forEach(status => {
                        const bar = document.createElement('div');
                        bar.classList.add('flex-1');

                        if (status === 'available') {
                            bar.classList.add('bg-green-500');
                        } else if (status === 'unavailable') {
                            bar.classList.add('bg-red-500');
                        } else {
                            bar.classList.add('bg-gray-300');
                        }

                        timeline.appendChild(bar);
                    });

                    monitorElement.appendChild(header);
                    monitorElement.appendChild(timeline);
                    monitorsList.appendChild(monitorElement);
                });
            })
            .catch(error => {
                console.error('Erro ao carregar monitores:', error);
            });
    }

    loadMonitors();
});
