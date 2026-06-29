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
        fetch('http://127.0.0.1:5050/api/status')
            .then(response => {
                if (!response.ok) throw new Error("Offline");
                return response.json();
            })
            .then(data => {
                // Atualizar badges da Barra Inferior
                updateBadge('status-runtime', data.execucao, 'badge-active');
                
                const gitClass = data.git_status === 'SINCRONIZADO' ? 'badge-active' : 'badge-warning';
                updateBadge('status-git', data.git_status, gitClass);
                
                updateBadge('status-hash', data.git_commit, 'badge-real');
                updateBadge('git-commit', data.git_commit, 'badge-real');
                updateBadge('git-branch', data.git_branch, 'badge-real');
                
                updateBadge('status-memory', data.memoria, data.memoria === 'OK' ? 'badge-active' : 'badge-error');
                updateBadge('status-gov', data.governanca, data.governanca === 'OK' ? 'badge-active' : 'badge-error');
                updateBadge('status-sqlite', data.memoria, data.memoria === 'OK' ? 'badge-active' : 'badge-error');
                updateBadge('status-obsidian', data.sincronia, 'badge-active');
                
                // Remove UNAVAILABLE status from left sidebar git elements if it matches
                const leftGitStatus = document.getElementById('git-status');
                if (leftGitStatus) {
                    leftGitStatus.textContent = data.git_status;
                    leftGitStatus.className = `badge ${gitClass}`;
                }
            })
            .catch(error => {
                console.warn("Backend (Real-Time API) não detectado. Mantendo INDISPONÍVEL.");
                // Retornar para INDISPONÍVEL se o backend cair
                const ids = ['status-runtime', 'status-git', 'status-hash', 'status-memory', 'status-gov', 'status-sqlite', 'status-obsidian'];
                ids.forEach(id => updateBadge(id, 'INDISPONÍVEL', 'badge-unavailable'));
            });
    }

    function updateBadge(id, text, className) {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = text;
            el.className = `badge ${className}`;
        }
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
        const resizerLeftH = document.getElementById('resizer-left-h');
        const leftTopSection = document.getElementById('left-top-section');

        let isResizingLeft = false;
        let isResizingRight = false;
        let isResizingLeftH = false;

        resizerLeft.addEventListener('mousedown', (e) => {
            isResizingLeft = true;
            resizerLeft.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        resizerRight.addEventListener('mousedown', (e) => {
            isResizingRight = true;
            resizerRight.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        resizerLeftH.addEventListener('mousedown', (e) => {
            isResizingLeftH = true;
            resizerLeftH.classList.add('resizing');
            document.body.style.cursor = 'row-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizingLeft && !isResizingRight && !isResizingLeftH) return;

            if (isResizingLeft) {
                leftBar.style.width = `${e.clientX}px`;
            }

            if (isResizingRight) {
                const newWidth = document.body.clientWidth - e.clientX;
                rightBar.style.width = `${newWidth}px`;
            }

            if (isResizingLeftH) {
                const containerRect = leftBar.getBoundingClientRect();
                const newHeight = e.clientY - containerRect.top;
                leftTopSection.style.height = `${newHeight}px`;
            }
        });

        document.addEventListener('mouseup', () => {
            isResizingLeft = false;
            isResizingRight = false;
            isResizingLeftH = false;
            resizerLeft.classList.remove('resizing');
            resizerRight.classList.remove('resizing');
            resizerLeftH.classList.remove('resizing');
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
        });
    }

    // Loop de heartbeat para API
    setInterval(fetchBackendStatus, 3000);
    
    // Inicialização
    fetchBackendStatus();
    loadMarkdownFiles();
    setupResizers();
});
