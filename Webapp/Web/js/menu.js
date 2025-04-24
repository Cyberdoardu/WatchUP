document.addEventListener('DOMContentLoaded', function() {
    const timeline = document.getElementById('timeline');
    const totalDias = 90;

    timeline.innerHTML = '';

    for (let i = 0; i < totalDias; i++) {
        const segmento = document.createElement('div');
        segmento.className = 'segmento-tempo';
        segmento.title = `Dia ${i+1} - 100% disponível`;
        timeline.appendChild(segmento);
    }

    const segmentos = document.querySelectorAll('.segmento-tempo');
    const espacamento = 1;
    segmentos.forEach(seg => {
        seg.style.marginRight = `${espacamento}px`;
    });
    segmentos[segmentos.length - 1].style.marginRight = '0';
});