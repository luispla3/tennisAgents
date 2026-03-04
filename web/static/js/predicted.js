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
                        <div>
                            <h3 class="predicted-match-title">${escapeHtml(matchLabel)}</h3>
                            <div class="predicted-match-meta">
                                <span>${escapeHtml(analysisDate)}</span>
                                ${tournament ? `<span class="predicted-tournament">${escapeHtml(tournament)}</span>` : ''}
                            </div>
                        </div>
                        <button class="btn-action btn-predictions">
                            Predicciones
                        </button>
                    </div>
                    <div class="predicted-predictions" style="display: none;"></div>
                </article>
            `;
        });

        return html;
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

                if (!storage || !matchDir || !analysisDate || !predictionsContainer) {
                    return;
                }

                const isVisible = predictionsContainer.style.display === 'block';
                if (isVisible) {
                    predictionsContainer.style.display = 'none';
                    return;
                }

                // If already loaded once, just toggle visibility
                if (predictionsContainer.dataset.loaded === 'true') {
                    predictionsContainer.style.display = 'block';
                    return;
                }

                predictionsContainer.innerHTML = `
                    <div class="loading-indicator">
                        <div class="loading-spinner"></div>
                        <p>Cargando predicciones...</p>
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
                            <div class="empty-state">
                                <p>No se pudieron cargar las predicciones para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    const predictions = data.predictions || [];
                    if (predictions.length === 0) {
                        predictionsContainer.innerHTML = `
                            <div class="empty-state">
                                <p>No hay predicciones disponibles para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    let html = '';
                    predictions.forEach((prediction, index) => {
                        const title = prediction.title || prediction.filename || `Predicción ${index + 1}`;
                        const content = prediction.content || '';
                        html += `
                            <article class="prediction-item">
                                <h4 class="prediction-title">Predicción ${index + 1} - ${escapeHtml(title)}</h4>
                                <pre class="prediction-content">${escapeHtml(content)}</pre>
                            </article>
                        `;
                    });

                    predictionsContainer.innerHTML = html;
                    predictionsContainer.dataset.loaded = 'true';
                } catch (error) {
                    console.error('Error fetching predicted match details:', error);
                    predictionsContainer.innerHTML = `
                        <div class="empty-state">
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


