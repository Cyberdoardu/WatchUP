const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modal = document.getElementById('incidentModal');
    const tipoAviso = document.getElementById('tipoAviso');
    const maintenanceFields = document.getElementById('maintenanceFields');
    const incidentForm = document.getElementById('incidentForm');
    const incidentList = document.getElementById('incidentList');

    openModalBtn.addEventListener('click', () => modal.classList.remove('hidden'));
    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });

    tipoAviso.addEventListener('change', () => {
      maintenanceFields.classList.toggle('hidden', tipoAviso.value !== 'maintenance');
    });
    incidentForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const titulo = document.getElementById('titulo').value;
      const impacto = document.getElementById('impacto').value;
      const tipo = document.getElementById('tipoAviso').value;
      const servico = document.getElementById('servicoAfetado').value;
      const descricao = document.getElementById('descricao').value;

      let cor = 'border-gray-300';
      if (tipo === 'problem') cor = 'border-red-500';
      else if (tipo === 'warning') cor = 'border-yellow-400';
      else if (tipo === 'informative') cor = 'border-blue-400';
      else if (tipo === 'maintenance') cor = 'border-purple-500';

      const item = document.createElement('li');
      item.className = `bg-white border-l-4 ${cor} p-4 rounded shadow-sm relative`;

      let estadoAtual = 'Identificado';
      const estados = ['Identificado', 'Reconhecido', 'Resolvido'];
      const concluidos = [estadoAtual];

      const cores = {
        'Identificado': 'red-500',
        'Reconhecido': 'yellow-400',
        'Resolvido': 'green-500',
      };

      const renderEstados = () => {
        return `
          <div class="flex items-center gap-6 text-sm text-gray-600 mb-2">
            <span>
              Impacto: <strong>${impacto}</strong>
              | Serviço: <strong>${servico}</strong>
              | Estado Atual: <strong class="${
                estadoAtual === 'Identificado' ? 'text-red-500' :
                estadoAtual === 'Reconhecido' ? 'text-yellow-500' :
                'text-green-500'
              }">${estadoAtual}</strong>
            </span>
          </div>
          <div class="flex gap-6 mb-1">
            ${estados.map((estado, idx) => {
              const passou = concluidos.includes(estado);
              const podeClicar = !passou && estados[idx - 1] === estadoAtual && estadoAtual !== 'Resolvido';
              return `
                <div class="flex items-center gap-2 estado-etapa ${podeClicar ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}"
                     data-estado="${estado}" ${podeClicar ? '' : 'data-disabled'}>
                  <div class="${passou ? `bg-${cores[estado]}` : `border-2 border-${cores[estado]}` } w-3.5 h-3.5 rounded-full"></div>
                  <span class="${passou ? `text-${cores[estado]} font-semibold` : 'text-gray-600'} text-sm">${estado}</span>
                </div>
              `;
            }).join('')}
          </div>
        `;
      };

      item.innerHTML = `
        <div class="absolute top-2 right-2 flex gap-4 text-sm">
          <button class="editar text-blue-600 hover:underline">Editar</button>
          <button class="remover text-red-600 hover:underline">Remover</button>
        </div>
        <h3 class="font-semibold text-gray-800">${titulo}</h3>
        <p class="text-sm text-gray-700 whitespace-pre-line mb-2">${descricao}</p>
        <div class="estado-container">${renderEstados()}</div>
      `;

      const atualizarEstado = (novoEstado) => {
        estadoAtual = novoEstado;
        if (!concluidos.includes(novoEstado)) concluidos.push(novoEstado);
        item.querySelector('.estado-container').innerHTML = renderEstados();
        configurarEstados();
      };

      const configurarEstados = () => {
        item.querySelectorAll('.estado-etapa').forEach(etapa => {
          const estado = etapa.dataset.estado;
          const isDisabled = etapa.hasAttribute('data-disabled');
          if (!isDisabled) {
            etapa.addEventListener('click', () => atualizarEstado(estado));
          }
        });
      };

      item.querySelector('.remover').addEventListener('click', () => item.remove());
      item.querySelector('.editar').addEventListener('click', () => alert('Funcionalidade de edição ainda não implementada.'));

      incidentList.prepend(item);
      configurarEstados();
      modal.classList.add('hidden');
      incidentForm.reset();
      maintenanceFields.classList.add('hidden');
    });