document.addEventListener('DOMContentLoaded', function() {
    // Function to load monitors and display their status
    function loadMonitors() {
        fetch('php/get_monitors.php')
            .then(response => response.json())
            .then(data => {
                const monitorsList = document.getElementById('monitors-list');
                monitorsList.innerHTML = ''; // Clear existing content
                data.forEach(monitor => { // Add outer div for each monitor
                    // Create the main monitor element
                    const monitorElement = document.createElement('div');
                    monitorElement.classList.add('monitor-item', 'mb-4', 'p-4', 'border', 'rounded'); // Add some basic Tailwind classes
                    // Create the timeline container
                    const timelineElement = document.createElement('div');
                    timelineElement.classList.add('flex', 'mt-2'); // Use flexbox for the timeline

                    // Add monitor name and current status
                    const monitorInfo = document.createElement('div');
                    monitorInfo.innerHTML = `
                        <h3 class="text-lg font-semibold">${monitor.monitor_name}</h3>
                        <p>Status: ${monitor.current_status}</p>
                    `;
                    monitorElement.appendChild(monitorInfo);

                    // Generate the 90-day timeline squares
                    monitor.history_90_days.forEach(status => {
                        const daySquare = document.createElement('div');
                        daySquare.classList.add('w-2', 'h-2', 'mr-0.5'); // Fixed size and margin using Tailwind classes
                        // Add Tailwind background color classes based on status
                        if (status === 'available') daySquare.classList.add('bg-green-500');
                        else if (status === 'unavailable') daySquare.classList.add('bg-red-500');
                        else daySquare.classList.add('bg-gray-400'); // For 'no_data' or any other status
                        timelineElement.appendChild(daySquare);
                    });

                    monitorElement.innerHTML = `
                        <p>Status: ${monitor.current_status}</p>
                    `;
                    monitorsList.appendChild(monitorElement);
                }); // Close the forEach loop
            })
            .catch(error => {
                console.error('Error fetching monitors:', error);
            });
    }

    // Call the function to load monitors when the page loads
    loadMonitors();

    // The existing timeline code remains
    // const timeline = document.getElementById('timeline');
    // const totalDias = 90;

    // ... (rest of the timeline code)
    // This part of the code is commented out as it was not part of the original request to modify
    // and its purpose is unclear without the corresponding HTML structure.
});