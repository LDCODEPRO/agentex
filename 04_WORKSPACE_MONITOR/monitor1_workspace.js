/*
AGENTE-X | Monitor 1 Workspace - JS Engine
Este script inicializa a interface e tenta buscar os dados do backend.
Seguindo a regra "Truth First": se o backend não existir, mantemos UNAVAILABLE.
*/

document.addEventListener("DOMContentLoaded", () => {
    // Nesta versão inicial (V1), o backend em Python (WebSocket ou REST API)
    // ainda não foi inicializado/acoplado à UI.
    // Assim, nossa função fetchStatus sempre cairá no catch e manterá o INDISPONÍVEL
    // evitando falsificar dados verdes inexistentes.

    const badges = document.querySelectorAll('.badge-unavailable');
    
    function fetchBackendStatus() {
        // Simulando a tentativa de conexão com a porta local (ex: localhost:8080)
        fetch('http://127.0.0.1:8080/api/status')
            .then(response => {
                if (!response.ok) throw new Error("Offline");
                return response.json();
            })
            .then(data => {
                // Se houvesse backend, processaríamos data.git, data.sqlite, etc.
                console.log("Backend conectado.");
            })
            .catch(error => {
                console.warn("Backend (Real-Time API) não detectado. Mantendo INDISPONÍVEL em todas as frentes.");
                // As badges por padrão já são INDISPONÍVEL. 
                // A regra determina: "Não inventar status verde".
            });
    }

    // Carregar .md files se estiver usando um servidor estático que suporte File API
    function loadMarkdownFiles() {
        const wtContent = document.getElementById('walkthrough-content');
        const implContent = document.getElementById('impl-plan-content');

        // Em ambientes "file://", fetch de outros arquivos costuma dar erro de CORS
        // Portanto, falhará graciosamente e permanecerá UNAVAILABLE
        fetch('../08_AUDITS/walkthrough.md') // Tenta buscar de alguma pasta relativa
            .then(res => {
                if(!res.ok) throw new Error("Not found");
                return res.text();
            })
            .then(text => {
                wtContent.innerHTML = `<pre>${text.substring(0, 300)}...</pre>`;
                wtContent.previousElementSibling.innerHTML += ' <span class="badge badge-real">REAL</span>';
            })
            .catch(() => {
                wtContent.innerHTML = '<span class="badge badge-unavailable">INDISPONÍVEL</span>';
            });
            
        fetch('../08_AUDITS/implementation_plan.md')
            .then(res => {
                if(!res.ok) throw new Error("Not found");
                return res.text();
            })
            .then(text => {
                implContent.innerHTML = `<pre>${text.substring(0, 300)}...</pre>`;
                implContent.previousElementSibling.innerHTML += ' <span class="badge badge-real">REAL</span>';
            })
            .catch(() => {
                implContent.innerHTML = '<span class="badge badge-unavailable">INDISPONÍVEL</span>';
            });
    }

    // --- RESIZER LOGIC ---
    function setupResizers() {
        const leftBar = document.getElementById('left-bar');
        const rightBar = document.getElementById('right-bar');
        const resizerLeft = document.getElementById('resizer-left');
        const resizerRight = document.getElementById('resizer-right');

        let isResizingLeft = false;
        let isResizingRight = false;

        resizerLeft.addEventListener('mousedown', (e) => {
            isResizingLeft = true;
            resizerLeft.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            // Disable text selection during drag
            document.body.style.userSelect = 'none';
        });

        resizerRight.addEventListener('mousedown', (e) => {
            isResizingRight = true;
            resizerRight.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizingLeft && !isResizingRight) return;

            if (isResizingLeft) {
                // Width is bounded by CSS min/max-width
                leftBar.style.width = `${e.clientX}px`;
            }

            if (isResizingRight) {
                // Right bar width is total width minus mouse position
                const newWidth = document.body.clientWidth - e.clientX;
                rightBar.style.width = `${newWidth}px`;
            }
        });

        document.addEventListener('mouseup', () => {
            isResizingLeft = false;
            isResizingRight = false;
            resizerLeft.classList.remove('resizing');
            resizerRight.classList.remove('resizing');
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
        });
    }

    // Loop de heartbeat simulado
    setInterval(fetchBackendStatus, 5000);
    
    // Inicialização
    fetchBackendStatus();
    loadMarkdownFiles();
    setupResizers();
});
