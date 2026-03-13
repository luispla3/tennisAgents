// Predicted matches page functionality
document.addEventListener('DOMContentLoaded', function() {
    const predictedSection = document.getElementById('predictedSection');
    const predictedMatchesContainer = document.getElementById('predictedMatchesContainer');

    if (!predictedSection || !predictedMatchesContainer) {
        return;
    }

    // Initial load
    loadPredictedMatches();

    async function loadPredictedMatches() {
        predictedMatchesContainer.innerHTML = `
            <div class="loading-indicator">
                <div class="loading-spinner"></div>
                <p>Cargando partidos analizados...</p>
            </div>
        `;

        try {
            const response = await fetch('/api/predicted-matches');
            const data = await response.json();

            if (!data.success) {
                predictedMatchesContainer.innerHTML = `
                    <div class="empty-state">
                        <p>No se pudieron cargar los partidos analizados.</p>
                    </div>
                `;
                return;
            }

            const matches = data.matches || [];
            if (matches.length === 0) {
                predictedMatchesContainer.innerHTML = `
                    <div class="empty-state">
                        <p>Todavía no hay partidos analizados con predicciones guardadas.</p>
                    </div>
                `;
                return;
            }

            predictedMatchesContainer.innerHTML = renderPredictedMatches(matches);
            attachPredictionsListeners();
            attachSummaryListeners();
            
            // Verificar si hay parámetros en la URL para abrir automáticamente el resumen
            const urlParams = new URLSearchParams(window.location.search);
            const matchDir = urlParams.get('match_dir');
            const analysisDate = urlParams.get('analysis_date');
            const showSummary = urlParams.get('show_summary') === 'true';
            
            if (matchDir && analysisDate && showSummary) {
                // Buscar la tarjeta del partido correspondiente
                const cards = document.querySelectorAll('.predicted-match-card');
                cards.forEach((card) => {
                    const cardMatchDir = card.getAttribute('data-match-dir');
                    const cardAnalysisDate = card.getAttribute('data-analysis-date');
                    
                    if (cardMatchDir === matchDir && cardAnalysisDate === analysisDate) {
                        // Encontrar el botón de resumen y hacer clic automáticamente
                        const summaryButton = card.querySelector('.btn-summary');
                        if (summaryButton) {
                            // Hacer scroll suave hasta la tarjeta
                            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            
                            // Esperar un momento para que el scroll se complete, luego hacer clic
                            setTimeout(() => {
                                summaryButton.click();
                            }, 500);
                        }
                    }
                });
                
                // Limpiar los parámetros de la URL después de usarlos
                const newUrl = window.location.pathname;
                window.history.replaceState({}, document.title, newUrl);
            }
        } catch (error) {
            console.error('Error fetching predicted matches:', error);
            predictedMatchesContainer.innerHTML = `
                <div class="empty-state">
                    <p>Error al cargar los partidos analizados.</p>
                </div>
            `;
        }
    }

    function renderPredictedMatches(matches) {
        let html = '';

        matches.forEach((match) => {
            const storage = match.storage || 'web';
            const matchDir = match.match_dir || '';
            const analysisDate = match.analysis_date || '';
            const player1 = match.player1 || match.match_label || 'Jugador 1';
            const player2 = match.player2 || '';
            const matchLabel = match.match_label || `${player1}${player2 ? ' vs ' + player2 : ''}`;
            const tournament = match.tournament || '';

            html += `
                <article class="predicted-match-card"
                         data-storage="${escapeHtml(storage)}"
                         data-match-dir="${escapeHtml(matchDir)}"
                         data-analysis-date="${escapeHtml(analysisDate)}">
                    <div class="predicted-match-header">
                        <div style="flex: 1;">
                            <h3 class="predicted-match-title">${escapeHtml(matchLabel)}</h3>
                            <div class="predicted-match-meta">
                                <span>${escapeHtml(analysisDate)}</span>
                                ${tournament ? `<span class="predicted-tournament">${escapeHtml(tournament)}</span>` : ''}
                            </div>
                        </div>
                        <div class="predicted-actions" style="display: flex; gap: 8px; align-items: center;">
                            <button class="btn-action btn-summary" style="background-color: #2a2a2a; color: #fff; border: 1px solid #333; min-width: 100px;">
                                Resumen
                            </button>
                            <button class="btn-action btn-predictions" style="min-width: 120px;">
                                Predicciones
                            </button>
                        </div>
                    </div>
                    <div class="predicted-summary" style="display: none; margin-top: 15px;"></div>
                    <div class="predicted-predictions" style="display: none; margin-top: 15px;"></div>
                </article>
            `;
        });

        return html;
    }

    function attachSummaryListeners() {
        const buttons = document.querySelectorAll('.btn-summary');

        buttons.forEach((button) => {
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                const card = this.closest('.predicted-match-card');
                if (!card) return;

                const storage = card.getAttribute('data-storage');
                const matchDir = card.getAttribute('data-match-dir');
                const analysisDate = card.getAttribute('data-analysis-date');
                const summaryContainer = card.querySelector('.predicted-summary');
                const predictionsContainer = card.querySelector('.predicted-predictions');
                const predictionsButton = card.querySelector('.btn-predictions');

                if (!storage || !matchDir || !analysisDate || !summaryContainer) {
                    return;
                }

                const isVisible = summaryContainer.style.display === 'block';
                if (isVisible) {
                    summaryContainer.style.display = 'none';
                    // Optional: Change button style back when closed
                    this.style.borderColor = '#333';
                    return;
                }

                // Close predictions container if open
                if (predictionsContainer) {
                    predictionsContainer.style.display = 'none';
                }
                // Reset predictions button style
                if (predictionsButton) {
                    predictionsButton.style.borderColor = '';
                }

                // Highlight active button
                this.style.borderColor = 'var(--accent-primary)';

                // If already loaded once, just toggle visibility
                if (summaryContainer.dataset.loaded === 'true') {
                    summaryContainer.style.display = 'block';
                    return;
                }

                summaryContainer.innerHTML = `
                    <div class="loading-indicator" style="padding: 1rem;">
                        <div class="loading-spinner" style="width: 24px; height: 24px;"></div>
                        <p style="font-size: 0.8rem;">Cargando resumen...</p>
                    </div>
                `;
                summaryContainer.style.display = 'block';

                try {
                    const params = new URLSearchParams({
                        storage: storage,
                        match_dir: matchDir,
                        analysis_date: analysisDate
                    });

                    const response = await fetch(`/api/predicted-match-details?${params.toString()}`);
                    const data = await response.json();

                    if (!data.success) {
                        summaryContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No se pudo cargar el resumen.</p>
                            </div>
                        `;
                        return;
                    }

                    const finalResponse = data.final_response;
                    
                    if (!finalResponse) {
                        summaryContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No hay resumen disponible para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    // Render markdown using marked if available, otherwise plain text
                    let contentHtml = '';
                    if (typeof marked !== 'undefined') {
                        contentHtml = marked.parse(finalResponse);
                    } else {
                        contentHtml = `<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(finalResponse)}</pre>`;
                    }

                    summaryContainer.innerHTML = `
                        <div class="prediction-item summary-content" style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.08) 0%, rgba(255, 184, 77, 0.05) 100%); border: 1px solid rgba(255, 107, 53, 0.2); border-radius: 12px; padding: 1.5rem; margin-top: 1rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);">
                            <h4 class="prediction-title" style="color: var(--accent-primary); margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid rgba(255, 107, 53, 0.3); padding-bottom: 0.75rem;">Síntesis Final de Apuestas</h4>
                            <div class="markdown-body" style="font-size: 0.9rem; line-height: 1.7; color: var(--text-primary);">${contentHtml}</div>
                        </div>
                    `;
                    summaryContainer.dataset.loaded = 'true';

                } catch (error) {
                    console.error('Error fetching summary:', error);
                    summaryContainer.innerHTML = `
                        <div class="empty-state" style="padding: 1rem;">
                            <p>Error al cargar el resumen.</p>
                        </div>
                    `;
                }
            });
        });
    }

    function attachPredictionsListeners() {
        const buttons = document.querySelectorAll('.btn-predictions');

        buttons.forEach((button) => {
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                const card = this.closest('.predicted-match-card');
                if (!card) return;

                const storage = card.getAttribute('data-storage');
                const matchDir = card.getAttribute('data-match-dir');
                const analysisDate = card.getAttribute('data-analysis-date');
                const predictionsContainer = card.querySelector('.predicted-predictions');
                const summaryContainer = card.querySelector('.predicted-summary');
                const summaryButton = card.querySelector('.btn-summary');

                if (!storage || !matchDir || !analysisDate || !predictionsContainer) {
                    return;
                }

                const isVisible = predictionsContainer.style.display === 'block';
                if (isVisible) {
                    predictionsContainer.style.display = 'none';
                    return;
                }

                // Close summary container if open
                if (summaryContainer) {
                    summaryContainer.style.display = 'none';
                }
                // Reset summary button style
                if (summaryButton) {
                    summaryButton.style.borderColor = '#333';
                }

                // If already loaded once, just toggle visibility
                if (predictionsContainer.dataset.loaded === 'true') {
                    predictionsContainer.style.display = 'block';
                    return;
                }

                predictionsContainer.innerHTML = `
                    <div class="loading-indicator" style="padding: 1rem;">
                        <div class="loading-spinner" style="width: 24px; height: 24px;"></div>
                        <p style="font-size: 0.8rem;">Cargando predicciones...</p>
                    </div>
                `;
                predictionsContainer.style.display = 'block';

                try {
                    const params = new URLSearchParams({
                        storage: storage,
                        match_dir: matchDir,
                        analysis_date: analysisDate
                    });

                    const response = await fetch(`/api/predicted-match-details?${params.toString()}`);
                    const data = await response.json();

                    if (!data.success) {
                        predictionsContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No se pudieron cargar las predicciones para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    const predictions = data.predictions || [];
                    if (predictions.length === 0) {
                        predictionsContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No hay predicciones disponibles para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    let html = '';
                    predictions.forEach((prediction, index) => {
                        const filename = prediction.filename || prediction.title || '';
                        const content = prediction.content || '';
                        
                        // Extraer el nombre del modelo del filename
                        let modelName = 'Modelo Principal';
                        if (filename) {
                            // Remover la extensión .md
                            const nameWithoutExt = filename.replace(/\.md$/, '');
                            
                            // Si el filename contiene "final_bet_decision_", extraer la parte después
                            if (nameWithoutExt.startsWith('final_bet_decision_')) {
                                modelName = nameWithoutExt.replace('final_bet_decision_', '');
                            } else if (nameWithoutExt === 'final_bet_decision') {
                                modelName = 'Modelo Principal';
                            }
                        }
                        
                        // Try to render markdown if marked is available
                        let contentHtml = '';
                        if (typeof marked !== 'undefined') {
                            contentHtml = marked.parse(content);
                        } else {
                            contentHtml = `<pre class="prediction-content" style="white-space: pre-wrap; font-family: inherit; background-color: rgba(0, 0, 0, 0.2); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-color);">${escapeHtml(content)}</pre>`;
                        }

                        const isLast = index === predictions.length - 1;
                        html += `
                            <article class="prediction-item" style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.08) 0%, rgba(255, 184, 77, 0.05) 100%); border: 1px solid rgba(255, 107, 53, 0.2); border-radius: 12px; padding: 1.5rem; ${isLast ? 'margin-bottom: 0;' : 'margin-bottom: 1rem;'} box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);">
                                <h4 class="prediction-title" style="color: var(--accent-primary); margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid rgba(255, 107, 53, 0.3); padding-bottom: 0.75rem;">PREDICCIÓN ${index + 1}: ${escapeHtml(modelName)}</h4>
                                <div class="markdown-body" style="font-size: 0.9rem; line-height: 1.7; color: var(--text-primary);">${typeof marked !== 'undefined' ? contentHtml : contentHtml}</div>
                            </article>
                        `;
                    });

                    predictionsContainer.innerHTML = html;
                    predictionsContainer.dataset.loaded = 'true';
                } catch (error) {
                    console.error('Error fetching predicted match details:', error);
                    predictionsContainer.innerHTML = `
                        <div class="empty-state" style="padding: 1rem;">
                            <p>Error al cargar las predicciones.</p>
                        </div>
                    `;
                }
            });
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
