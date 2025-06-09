document.addEventListener('DOMContentLoaded', () => {
  const API = 'php/incidentes.php';
  const openBtn = document.getElementById('openModalBtn');
  const closeBtn = document.getElementById('closeModalBtn');
  const modal = document.getElementById('incidentModal');
  const tipo = document.getElementById('tipo');
  const maintenanceFields = document.getElementById('maintenanceFields');
  const form = document.getElementById('incidentForm');
  const list = document.getElementById('incidentList');
  const formError = document.getElementById('formError');

  openBtn.addEventListener('click', () => {
    formError.textContent = '';
    modal.classList.remove('hidden');
  });
  closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
  modal.addEventListener('click', e => { if (e.target === modal) modal.classList.add('hidden'); });

  tipo.addEventListener('change', () => {
    maintenanceFields.classList.toggle('hidden', tipo.value !== 'maintenance');
  });

  async function carregar() {
    list.innerHTML = '';
    try {
      const res = await fetch(API);
      const { sucesso, incidentes, mensagem } = await res.json();
      if (!sucesso) throw new Error(mensagem || 'Erro ao carregar');
      incidentes.forEach(criarItem);
    } catch (err) {
      list.innerHTML = '<li class="text-red-600">Erro ao carregar incidentes.</li>';
      console.error(err);
    }
  }

  function criarItem(item) {
    let estado = item.estado_atual || 'Identificado';
    const concluidos = [estado];
    const estados = ['Identificado','Reconhecido','Resolvido'];
    const coresEstado = { Identificado: 'red-500', Reconhecido: 'yellow-400', Resolvido: 'green-500' };
    const borda = {
      problem: 'red-500',
      warning: 'yellow-400',
      informative: 'blue-400',
      maintenance: 'purple-500'
    }[item.tipo] || 'gray-300';

    const li = document.createElement('li');
    li.className = `bg-white border-l-4 border-${borda} p-4 rounded shadow-sm mb-4 relative`;

    const renderEstados = () => `
      <div class="estado-container">
        <div class="flex items-center gap-6 text-sm text-gray-600 mb-2">
          <span>
            Estado Atual: <strong class="${
              estado==='Identificado'?'text-red-500':
              estado==='Reconhecido'?'text-yellow-500':'text-green-500'
            }">${estado}</strong>
          </span>
        </div>
        <div class="flex gap-6 mb-1">
          ${estados.map((e,i) => {
            const done = concluidos.includes(e);
            const can = !done && estados[i-1] === estado && estado!=='Resolvido';
            return `
              <div class="flex items-center gap-2 estado-etapa ${can?'cursor-pointer hover:opacity-80':'cursor-default'}"
                   data-estado="${e}" ${can?'':'data-disabled'}>
                <div class="${
                  done?`bg-${coresEstado[e]}`:`border-2 border-${coresEstado[e]}`
                } w-3.5 h-3.5 rounded-full"></div>
                <span class="${
                  done? `text-${coresEstado[e]} font-semibold`:'text-gray-600'
                } text-sm">${e}</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;

    li.innerHTML = `
      <div class="absolute top-2 right-2 flex gap-4 text-sm">
        <button class="editar text-blue-600 hover:underline">Editar</button>
        <button class="remover text-red-600 hover:underline">Remover</button>
      </div>
      <h3 class="font-semibold text-gray-800">${item.titulo}</h3>
      <p class="text-sm text-gray-700 whitespace-pre-line mb-2">${item.descricao}</p>
      ${renderEstados()}
    `;

    // Remover
    li.querySelector('.remover').addEventListener('click', async () => {
      if (!confirm('Remover este incidente?')) return;
      await fetch(`${API}?action=delete`, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ id: item.id })
      });
      li.remove();
    });

    // Atualizar estado
    const setup = () => {
      li.querySelectorAll('.estado-etapa').forEach(el => {
        if (!el.hasAttribute('data-disabled')) {
          el.addEventListener('click', async () => {
            const novo = el.dataset.estado;
            await fetch(`${API}?action=updateState`, {
              method: 'POST',
              headers: {'Content-Type':'application/json'},
              body: JSON.stringify({ id: item.id, estado: novo })
            });
            estado = novo;
            if (!concluidos.includes(novo)) concluidos.push(novo);
            li.querySelector('.estado-container').innerHTML = renderEstados();
            setup();
          });
        }
      });
    };
    setup();

    list.prepend(li);
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    formError.textContent = '';
    const payload = {
      titulo: form.titulo.value.trim(),
      descricao: form.descricao.value.trim(),
      impacto: form.impacto.value,
      tipo: form.tipo.value,
      servico: form.servico.value.trim()
    };
    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.sucesso) throw new Error(data.mensagem);
      form.reset();
      maintenanceFields.classList.add('hidden');
      modal.classList.add('hidden');
      carregar();
    } catch (err) {
      formError.textContent = err.message;
    }
  });

  carregar();
});
