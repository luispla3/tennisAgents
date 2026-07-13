// Predicted matches page functionality
document.addEventListener('DOMContentLoaded', function() {
    const predictedSection = document.getElementById('predictedSection');
    const predictedMatchesContainer = document.getElementById('predictedMatchesContainer');
    const filterDate = document.getElementById('filterDate');
    const filterPlayer1 = document.getElementById('filterPlayer1');
    const filterPlayer2 = document.getElementById('filterPlayer2');
    const clearFiltersBtn = document.getElementById('clearFilters');

    if (!predictedSection || !predictedMatchesContainer) {
        return;
    }

    // Store original matches data
    let allMatches = [];

    function normalizeFinalDecision(content) {
        if (!content || typeof content !== 'string') return content;
        const trimmed = content.trim();
        if (!trimmed.startsWith('{')) return content;

        try {
            const data = JSON.parse(trimmed);
            const match = data.match || {};
            const state = data.state || {};
            const target = data.target?.tool_call || {};
            const name = (target.name || 'wait').toLowerCase();
            const args = target.arguments || {};
            const labels = { wait: 'Esperar', bet: 'Apostar', close: 'Cerrar posición' };
            const lines = [
                `# Decisión Final — ${match.player_a || ''} vs ${match.player_b || ''}`,
                '',
                `**Torneo:** ${match.tournament || 'N/A'}`,
                `**Fecha:** ${match.match_date || 'N/A'}`,
                `**Fase:** ${state.phase || 'N/A'}`,
            ];

            if (state.score) lines.push(`**Marcador:** ${state.score}`);
            const balance = state.available_balance ?? state.wallet_balance;
            if (balance !== undefined && balance !== null) {
                lines.push(`**Saldo disponible:** ${balance}`);
            }

            lines.push('', `## Acción: ${labels[name] || name}`, '');

            if (name === 'bet') {
                lines.push(
                    `- **Mercado:** ${args.market || 'N/A'}`,
                    `- **Selección:** ${args.option || 'N/A'}`,
                    `- **Stake:** ${args.stake ?? 'N/A'}`,
                    `- **Cuota:** ${args.odds ?? 'N/A'}`,
                    `- **Motivo:** ${args.reason || 'N/A'}`
                );
            } else if (name === 'close') {
                const closePct = args.close_percentage;
                const closeLabel = closePct !== undefined && closePct !== null
                    ? `${Math.round(Number(closePct) * 100)}%`
                    : 'N/A';
                lines.push(
                    `- **Posición:** ${args.position_id || 'N/A'}`,
                    `- **Cierre:** ${closeLabel}`,
                    `- **Motivo:** ${args.reason || 'N/A'}`
                );
            } else {
                lines.push(`- **Motivo:** ${args.reason || 'N/A'}`);
            }

            if (data.timestamp) {
                lines.push('', '---', `*Generado: ${data.timestamp}*`);
            }

            return lines.join('\n');
        } catch (error) {
            return content;
        }
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
                allMatches = [];
                return;
            }

            // Store all matches for filtering
            allMatches = matches;
            
            // Apply initial filters and render
            applyFilters();
            
            // Tras completar una predicción, abrir automáticamente la decisión
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
                        // Abrir el panel de Decisión automáticamente
                        const summaryButton = card.querySelector('.btn-decision');
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
            const status = match.status || 'completed';

            html += `
                <article class="predicted-match-card"
                         data-storage="${escapeHtml(storage)}"
                         data-match-dir="${escapeHtml(matchDir)}"
                         data-analysis-date="${escapeHtml(analysisDate)}">
                    <div class="predicted-match-header">
                        <div style="flex: 1;">
                            <h3 class="predicted-match-title">
                                ${escapeHtml(matchLabel)}
                                ${status === 'cancelled' ? '<span style="font-size: 0.7em; background-color: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); padding: 2px 6px; border-radius: 4px; margin-left: 8px; vertical-align: middle;">CANCELADO</span>' : ''}
                            </h3>
                            <div class="predicted-match-meta">
                                <span>${escapeHtml(analysisDate)}</span>
                                ${tournament ? `<span class="predicted-tournament">${escapeHtml(tournament)}</span>` : ''}
                            </div>
                        </div>
                        <div class="predicted-actions" style="display: flex; gap: 8px; align-items: center;">
                            <button class="btn-action btn-decision" style="background-color: #2a2a2a; color: #fff; border: 1px solid #333; min-width: 100px;">
                                Decisión
                            </button>
                            <button class="btn-action btn-reports" style="min-width: 120px;">
                                Informes
                            </button>
                        </div>
                    </div>
                    <div class="predicted-decision" style="display: none; margin-top: 15px;"></div>
                    <div class="predicted-reports" style="display: none; margin-top: 15px;"></div>
                </article>
            `;
        });

        return html;
    }

    function renderMarkdown(content) {
        if (typeof marked !== 'undefined') {
            return marked.parse(content);
        }
        return `<pre style="white-space: pre-wrap; font-family: inherit;">${escapeHtml(content)}</pre>`;
    }

    function attachDecisionListeners() {
        const buttons = document.querySelectorAll('.btn-decision');

        buttons.forEach((button) => {
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                const card = this.closest('.predicted-match-card');
                if (!card) return;

                const storage = card.getAttribute('data-storage');
                const matchDir = card.getAttribute('data-match-dir');
                const analysisDate = card.getAttribute('data-analysis-date');
                const decisionContainer = card.querySelector('.predicted-decision');
                const reportsContainer = card.querySelector('.predicted-reports');
                const reportsButton = card.querySelector('.btn-reports');

                if (!storage || !matchDir || !analysisDate || !decisionContainer) {
                    return;
                }

                const isVisible = decisionContainer.style.display === 'block';
                if (isVisible) {
                    decisionContainer.style.display = 'none';
                    this.style.borderColor = '#333';
                    return;
                }

                if (reportsContainer) {
                    reportsContainer.style.display = 'none';
                }
                if (reportsButton) {
                    reportsButton.style.borderColor = '';
                }

                this.style.borderColor = 'var(--accent-primary)';

                if (decisionContainer.dataset.loaded === 'true') {
                    decisionContainer.style.display = 'block';
                    return;
                }

                decisionContainer.innerHTML = `
                    <div class="loading-indicator" style="padding: 1rem;">
                        <div class="loading-spinner" style="width: 24px; height: 24px;"></div>
                        <p style="font-size: 0.8rem;">Cargando decisión...</p>
                    </div>
                `;
                decisionContainer.style.display = 'block';

                try {
                    const params = new URLSearchParams({
                        storage: storage,
                        match_dir: matchDir,
                        analysis_date: analysisDate
                    });

                    const response = await fetch(`/api/predicted-match-details?${params.toString()}`);
                    const data = await response.json();

                    if (!data.success) {
                        decisionContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No se pudo cargar la decisión.</p>
                            </div>
                        `;
                        return;
                    }

                    const finalDecision = normalizeFinalDecision(data.final_bet_decision);
                    
                    if (!finalDecision) {
                        decisionContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No hay decisión disponible para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    decisionContainer.innerHTML = `
                        <div class="prediction-item summary-content" style="background: linear-gradient(135deg, rgba(255, 107, 53, 0.08) 0%, rgba(255, 184, 77, 0.05) 100%); border: 1px solid rgba(255, 107, 53, 0.2); border-radius: 12px; padding: 1.5rem; margin-top: 1rem; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);">
                            <h4 class="prediction-title" style="color: var(--accent-primary); margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid rgba(255, 107, 53, 0.3); padding-bottom: 0.75rem;">Decisión Final</h4>
                            <div class="markdown-body" style="font-size: 0.9rem; line-height: 1.7; color: var(--text-primary);">${renderMarkdown(finalDecision)}</div>
                        </div>
                    `;
                    decisionContainer.dataset.loaded = 'true';

                } catch (error) {
                    console.error('Error fetching decision:', error);
                    decisionContainer.innerHTML = `
                        <div class="empty-state" style="padding: 1rem;">
                            <p>Error al cargar la decisión.</p>
                        </div>
                    `;
                }
            });
        });
    }

    function attachReportsListeners() {
        const buttons = document.querySelectorAll('.btn-reports');

        buttons.forEach((button) => {
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                const card = this.closest('.predicted-match-card');
                if (!card) return;

                const storage = card.getAttribute('data-storage');
                const matchDir = card.getAttribute('data-match-dir');
                const analysisDate = card.getAttribute('data-analysis-date');
                const reportsContainer = card.querySelector('.predicted-reports');
                const decisionContainer = card.querySelector('.predicted-decision');
                const decisionButton = card.querySelector('.btn-decision');

                if (!storage || !matchDir || !analysisDate || !reportsContainer) {
                    return;
                }

                const isVisible = reportsContainer.style.display === 'block';
                if (isVisible) {
                    reportsContainer.style.display = 'none';
                    this.style.borderColor = '';
                    return;
                }

                if (decisionContainer) {
                    decisionContainer.style.display = 'none';
                }
                if (decisionButton) {
                    decisionButton.style.borderColor = '#333';
                }

                this.style.borderColor = 'var(--accent-primary)';

                if (reportsContainer.dataset.loaded === 'true') {
                    reportsContainer.style.display = 'block';
                    return;
                }

                reportsContainer.innerHTML = `
                    <div class="loading-indicator" style="padding: 1rem;">
                        <div class="loading-spinner" style="width: 24px; height: 24px;"></div>
                        <p style="font-size: 0.8rem;">Cargando informes...</p>
                    </div>
                `;
                reportsContainer.style.display = 'block';

                try {
                    const params = new URLSearchParams({
                        storage: storage,
                        match_dir: matchDir,
                        analysis_date: analysisDate
                    });

                    let data;
                    let usedFallback = false;
                    let response = await fetch(`/api/match-reports?${params.toString()}`);
                    if (response.ok) {
                        data = await response.json();
                    } else {
                        usedFallback = true;
                        response = await fetch(`/api/predicted-match-details?${params.toString()}`);
                        data = await response.json();
                    }

                    if (!response.ok || !data.success) {
                        reportsContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No se pudieron cargar los informes para este partido.</p>
                            </div>
                        `;
                        return;
                    }

                    const reports = data.reports || [];
                    if (reports.length === 0) {
                        const staleServer = usedFallback || data.reports === undefined;
                        reportsContainer.innerHTML = `
                            <div class="empty-state" style="padding: 1rem;">
                                <p>No hay informes disponibles para este partido.</p>
                                ${staleServer ? `
                                    <p style="font-size:0.85rem;color:var(--text-secondary);margin-top:10px;line-height:1.5;">
                                        El servidor web parece desactualizado. Cierra todas las terminales,
                                        ejecuta <code>python -m web.run</code> y recarga esta página (Ctrl+F5).
                                    </p>
                                ` : ''}
                            </div>
                        `;
                        return;
                    }

                    let html = '';
                    reports.forEach((report, index) => {
                        const agent = report.agent || report.title || 'Agente';
                        const content = report.content || '';
                        const isLast = index === reports.length - 1;

                        html += `
                            <article class="prediction-item" style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 12px; padding: 1.5rem; ${isLast ? 'margin-bottom: 0;' : 'margin-bottom: 1rem;'} box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);">
                                <h4 class="prediction-title" style="color: #60a5fa; margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid rgba(59, 130, 246, 0.3); padding-bottom: 0.75rem;">${escapeHtml(agent)}</h4>
                                <div class="markdown-body" style="font-size: 0.9rem; line-height: 1.7; color: var(--text-primary);">${renderMarkdown(content)}</div>
                            </article>
                        `;
                    });

                    reportsContainer.innerHTML = html;
                    reportsContainer.dataset.loaded = 'true';
                } catch (error) {
                    console.error('Error fetching match reports:', error);
                    reportsContainer.innerHTML = `
                        <div class="empty-state" style="padding: 1rem;">
                            <p>Error al cargar los informes.</p>
                        </div>
                    `;
                }
            });
        });
    }

    function attachSummaryListeners() {
        attachDecisionListeners();
    }

    function attachPredictionsListeners() {
        attachReportsListeners();
    }

    // Filter functionality
    function applyFilters() {
        if (allMatches.length === 0) {
            return;
        }

        const dateFilter = filterDate ? filterDate.value : '';
        const player1Filter = filterPlayer1 ? filterPlayer1.value.trim().toLowerCase() : '';
        const player2Filter = filterPlayer2 ? filterPlayer2.value.trim().toLowerCase() : '';

        // Check if any filter is active
        const hasActiveFilters = dateFilter || player1Filter || player2Filter;
        
        // Show/hide clear button
        if (clearFiltersBtn) {
            clearFiltersBtn.style.display = hasActiveFilters ? 'inline-flex' : 'none';
        }

        // Filter matches
        let filteredMatches = allMatches.filter(match => {
            // Filter by date
            if (dateFilter) {
                const matchDate = match.analysis_date || '';
                if (matchDate !== dateFilter) {
                    return false;
                }
            }

            // Get player names (case-insensitive matching)
            const player1 = (match.player1 || '').toLowerCase();
            const player2 = (match.player2 || '').toLowerCase();
            const matchLabel = (match.match_label || '').toLowerCase();

            // If both players are specified, both must be present
            if (player1Filter && player2Filter) {
                // Check if both players are in the match
                const hasPlayer1 = player1.includes(player1Filter) || matchLabel.includes(player1Filter);
                const hasPlayer2 = player2.includes(player2Filter) || matchLabel.includes(player2Filter);
                
                // Both players must be present
                if (!hasPlayer1 || !hasPlayer2) {
                    return false;
                }
            } else {
                // If only one player is specified, check if that player is in the match
                if (player1Filter) {
                    const hasPlayer1 = player1.includes(player1Filter) || matchLabel.includes(player1Filter);
                    if (!hasPlayer1) {
                        return false;
                    }
                }
                
                if (player2Filter) {
                    const hasPlayer2 = player2.includes(player2Filter) || matchLabel.includes(player2Filter);
                    if (!hasPlayer2) {
                        return false;
                    }
                }
            }

            return true;
        });

        // Render filtered matches
        if (filteredMatches.length === 0) {
            predictedMatchesContainer.innerHTML = `
                <div class="empty-state">
                    <p>No se encontraron partidos que coincidan con los filtros aplicados.</p>
                </div>
            `;
        } else {
            predictedMatchesContainer.innerHTML = renderPredictedMatches(filteredMatches);
            attachPredictionsListeners();
            attachSummaryListeners();
        }
    }

    // Add event listeners for filters
    if (filterDate) {
        filterDate.addEventListener('input', applyFilters);
        filterDate.addEventListener('change', applyFilters);
    }

    if (filterPlayer1) {
        filterPlayer1.addEventListener('input', applyFilters);
    }

    if (filterPlayer2) {
        filterPlayer2.addEventListener('input', applyFilters);
    }

    // Clear filters button
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            if (filterDate) filterDate.value = '';
            if (filterPlayer1) filterPlayer1.value = '';
            if (filterPlayer2) filterPlayer2.value = '';
            applyFilters();
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
