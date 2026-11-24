// O servidor continua responsável pelos dados e pelas validações dos formulários.
for (const aviso of document.querySelectorAll('.toast.show')) {
    setTimeout(() => aviso.classList.remove('show'), 3600);
}

const tipoRelatorio = document.getElementById('relatorio-tipo');

function atualizarCamposRelatorio() {
    const personalizado = tipoRelatorio.value === 'personalizado';
    const mensal = tipoRelatorio.value === 'mes';
    document.getElementById('campo-mes').hidden = !mensal;
    document.getElementById('campo-ano').hidden = personalizado;
    document.getElementById('campo-inicio').hidden = !personalizado;
    document.getElementById('campo-fim').hidden = !personalizado;
    for (const nome of ['mes', 'ano', 'inicio', 'fim']) {
        const campo = document.getElementById('relatorio-' + nome);
        campo.disabled = campo.closest('.field').hidden;
        campo.required = !campo.disabled;
    }
}

if (tipoRelatorio) {
    tipoRelatorio.addEventListener('change', atualizarCamposRelatorio);
    atualizarCamposRelatorio();
    document.getElementById('imprimir-relatorio').addEventListener('click', () => window.print());
}
