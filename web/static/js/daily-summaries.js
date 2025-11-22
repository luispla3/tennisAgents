// Daily summaries page functionality
document.addEventListener('DOMContentLoaded', function() {
    const matchesContainer = document.getElementById('matchesContainer');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const emptyState = document.getElementById('emptyState');

    // Fetch and render matches on page load
    async function fetchAndRenderMatches() {
        try {
            loadingIndicator.style.display = 'flex';
            matchesContainer.style.display = 'none';
            emptyState.style.display = 'none';

            const response = await fetch('/api/fetch-daily-summaries', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success && data.matches_data) {
                renderMatches(data.matches_data);
            } else {
                showEmptyState();
            }
        } catch (error) {
            console.error('Error fetching daily summaries:', error);
            showEmptyState();
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }

    function renderMatches(matchesData) {
        const summaries = matchesData.summaries || [];
        
        // Filtrar solo partidos finalizados (estado "ended" o "closed")
        const endedMatches = summaries.filter(summary => {
            const status = summary.sport_event_status?.status;
            return status === 'ended' || status === 'closed';
        });
        
        if (endedMatches.length === 0) {
            showEmptyState();
            return;
        }

        // Group matches by season (championship)
        const matchesBySeason = {};
        
        endedMatches.forEach(summary => {
            const season = summary.sport_event?.sport_event_context?.season;
            const seasonName = season?.name || 'Unknown Championship';
            
            if (!matchesBySeason[seasonName]) {
                matchesBySeason[seasonName] = [];
            }
            
            matchesBySeason[seasonName].push(summary);
        });

        // Render matches grouped by season, sorted by gender (men first, then women)
        let html = '';
        
        Object.keys(matchesBySeason).forEach(seasonName => {
            const seasonMatches = matchesBySeason[seasonName];
            
            // Sort matches by gender: men first, then women
            seasonMatches.sort((a, b) => {
                const genderA = a.sport_event?.sport_event_context?.competition?.gender || '';
                const genderB = b.sport_event?.sport_event_context?.competition?.gender || '';
                
                // men = 1, women = 2, others = 3
                const orderA = genderA === 'men' ? 1 : (genderA === 'women' ? 2 : 3);
                const orderB = genderB === 'men' ? 1 : (genderB === 'women' ? 2 : 3);
                
                return orderA - orderB;
            });
            
            html += renderSeasonGroup(seasonName, seasonMatches);
        });

        matchesContainer.innerHTML = html;
        matchesContainer.style.display = 'block';
        
        // Attach event listeners for stats buttons
        attachStatsListeners();
        
        // Attach event listeners for player buttons
        attachPlayerListeners();
    }

    function renderSeasonGroup(seasonName, matches) {
        let html = `
            <div class="season-group">
                <div class="season-header">
                    <h2 class="season-title">${escapeHtml(seasonName)}</h2>
                    <span class="season-match-count">${matches.length} ${matches.length === 1 ? 'partido' : 'partidos'}</span>
                </div>
                <div class="matches-grid">
        `;

        matches.forEach((summary, index) => {
            html += renderMatch(summary, index);
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    function renderMatch(summary, index) {
        const sportEvent = summary.sport_event || {};
        const status = summary.sport_event_status || {};
        const statistics = summary.statistics || {};
        const competitors = sportEvent.competitors || [];
        const venue = sportEvent.venue || {};
        const round = sportEvent.sport_event_context?.round || {};
        const competition = sportEvent.sport_event_context?.competition || {};
        const startTime = sportEvent.start_time || '';

        // Get players
        const homePlayer = competitors.find(c => c.qualifier === 'home') || competitors[0] || {};
        const awayPlayer = competitors.find(c => c.qualifier === 'away') || competitors[1] || {};
        
        // Format player names for buttons
        const homePlayerShort = formatPlayerNameShort(homePlayer.name || '');
        const awayPlayerShort = formatPlayerNameShort(awayPlayer.name || '');

        // Format start time
        const formattedTime = formatDateTime(startTime);

        // Get scores
        const homeScore = status.home_score || 0;
        const awayScore = status.away_score || 0;
        const periodScores = status.period_scores || [];

        // Match status
        const matchStatus = status.status || 'unknown';
        const matchStatusText = status.match_status || '';

        // Get gender
        const gender = competition.gender || '';
        const genderDisplay = gender === 'men' ? '👨' : (gender === 'women' ? '👩' : '');

        const matchId = `match-${index}`;
        const statsId = `stats-${index}`;
        const modalId = `modal-${index}`;

        return `
            <div class="match-card" data-match-id="${matchId}">
                <div class="match-header">
                    <div class="match-time">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="8" cy="8" r="6"/>
                            <path d="M8 4V8L10 10"/>
                        </svg>
                        <span>${formattedTime}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${genderDisplay ? `<span class="gender-badge">${genderDisplay}</span>` : ''}
                        ${round.name ? `<div class="match-round">${escapeHtml(round.name)}</div>` : ''}
                    </div>
                    ${matchStatus === 'ended' || matchStatus === 'closed' ? '<div class="match-status-badge ended">FINALIZADO</div>' : ''}
                </div>

                <div class="match-venue">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M8 2C5.8 2 4 3.8 4 6C4 9 8 13 8 13C8 13 12 9 12 6C12 3.8 10.2 2 8 2Z"/>
                        <circle cx="8" cy="6" r="1.5"/>
                    </svg>
                    <span>${escapeHtml(venue.name || '')}</span>
                    ${venue.city_name ? `<span class="venue-location">${escapeHtml(venue.city_name)}${venue.country_name ? ', ' + escapeHtml(venue.country_name) : ''}</span>` : ''}
                </div>

                <div class="match-players">
                    <div class="player player-home" data-player-name="${escapeHtml(homePlayer.name || '')}">
                        <div class="player-info">
                            <div class="player-name-wrapper">
                                <div class="player-name">${escapeHtml(homePlayer.name || 'N/A')}</div>
                            </div>
                            ${homePlayer.country_code ? `<div class="player-country">${escapeHtml(homePlayer.country_code)}</div>` : ''}
                        </div>
                        <div class="player-score">
                            <div class="score-main">${homeScore}</div>
                            ${periodScores.length > 0 ? `
                                <div class="score-sets">
                                    ${periodScores.map(period => `<span class="set-score">${period.home_score || 0}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <div class="match-vs">VS</div>

                    <div class="player player-away" data-player-name="${escapeHtml(awayPlayer.name || '')}">
                        <div class="player-info">
                            <div class="player-name-wrapper">
                                <div class="player-name">${escapeHtml(awayPlayer.name || 'N/A')}</div>
                            </div>
                            ${awayPlayer.country_code ? `<div class="player-country">${escapeHtml(awayPlayer.country_code)}</div>` : ''}
                        </div>
                        <div class="player-score">
                            <div class="score-main">${awayScore}</div>
                            ${periodScores.length > 0 ? `
                                <div class="score-sets">
                                    ${periodScores.map(period => `<span class="set-score">${period.away_score || 0}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>

                <div class="match-actions">
                    <button class="btn-action btn-stats" data-modal-id="${modalId}" data-match-index="${index}">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M2 12L6 8L9 11L14 6"/>
                            <path d="M14 6H10V10"/>
                        </svg>
                        Stats
                    </button>
                    <button class="btn-action btn-historial">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M2 2H14V14H2V2Z"/>
                            <path d="M2 6H14"/>
                            <path d="M6 2V14"/>
                        </svg>
                        Historial
                    </button>
                    <button class="btn-action btn-player" 
                            data-player="A" 
                            data-competitor-id="${homePlayer.id || ''}"
                            data-player-name="${escapeHtml(homePlayer.name || '')}"
                            data-match-index="${index}">
                        ${escapeHtml(homePlayerShort)}
                    </button>
                    <button class="btn-action btn-player" 
                            data-player="B" 
                            data-competitor-id="${awayPlayer.id || ''}"
                            data-player-name="${escapeHtml(awayPlayer.name || '')}"
                            data-match-index="${index}">
                        ${escapeHtml(awayPlayerShort)}
                    </button>
                    <button class="btn-action btn-draw">
                        Draw
                    </button>
                </div>
            </div>
            
            <!-- Statistics Modal -->
            <div id="${modalId}" class="stats-modal" data-modal-id="${modalId}">
                <div class="stats-modal-backdrop"></div>
                <div class="stats-modal-content">
                    <div class="stats-modal-header">
                        <h3 class="stats-modal-title">Estadísticas del Partido</h3>
                        <button class="btn-close-modal" data-modal-id="${modalId}">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6L18 18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="stats-modal-body">
                        ${renderStatistics(statistics)}
                    </div>
                </div>
            </div>
            
            <!-- Player Profile Modal -->
            <div id="player-modal-${index}" class="stats-modal player-profile-modal" data-modal-id="player-modal-${index}">
                <div class="stats-modal-backdrop"></div>
                <div class="stats-modal-content">
                    <div class="stats-modal-header">
                        <h3 class="stats-modal-title">Perfil del Jugador</h3>
                        <button class="btn-close-modal" data-modal-id="player-modal-${index}">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6L18 18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="stats-modal-body" id="player-profile-body-${index}">
                        <div class="loading-indicator">
                            <div class="loading-spinner"></div>
                            <p>Cargando perfil del jugador...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function renderStatistics(statistics) {
        const totals = statistics.totals || {};
        const competitors = totals.competitors || [];

        if (competitors.length === 0) {
            return '<div class="stats-empty"><p>No hay estadísticas disponibles para este partido</p></div>';
        }

        // Get home and away players
        const homeCompetitor = competitors.find(c => c.qualifier === 'home') || competitors[0];
        const awayCompetitor = competitors.find(c => c.qualifier === 'away') || competitors[1];

        if (!homeCompetitor && !awayCompetitor) {
            return '<div class="stats-empty"><p>No hay estadísticas disponibles</p></div>';
        }

        let html = '<div class="stats-content-flip">';

        // Render both players side by side
        [homeCompetitor, awayCompetitor].forEach((competitor, idx) => {
            if (!competitor) return;
            
            const stats = competitor.statistics || {};
            const playerName = competitor.name || `Jugador ${idx + 1}`;
            const isHome = competitor.qualifier === 'home' || idx === 0;
            const playerClass = isHome ? 'stats-player-home' : 'stats-player-away';

            // Calculate percentages
            const firstServeTotal = stats.first_serve_successful || 0;
            const firstServeWon = stats.first_serve_points_won || 0;
            const firstServePct = firstServeTotal > 0 ? ((firstServeWon / firstServeTotal) * 100).toFixed(1) : 0;
            
            const breakpointsTotal = stats.total_breakpoints || 0;
            const breakpointsWon = stats.breakpoints_won || 0;
            const breakpointsPct = breakpointsTotal > 0 ? ((breakpointsWon / breakpointsTotal) * 100).toFixed(1) : 0;

            const servicePointsTotal = (stats.service_points_won || 0) + (stats.service_points_lost || 0);
            const servicePointsPct = servicePointsTotal > 0 ? ((stats.service_points_won || 0) / servicePointsTotal * 100).toFixed(1) : 0;

            html += `
                <div class="stats-player-card ${playerClass}">
                    <h4 class="stats-player-name-flip">${escapeHtml(playerName)}</h4>
                    
                    <div class="stats-sections">
                        <!-- Serve Stats -->
                        <div class="stats-section">
                            <h5 class="stats-section-title">Servicio</h5>
                            <div class="stats-grid-flip">
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Aces</span>
                                    <span class="stat-value-flip">${stats.aces || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Dobles Faltas</span>
                                    <span class="stat-value-flip">${stats.double_faults || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">1er Servicio</span>
                                    <span class="stat-value-flip">${stats.first_serve_successful || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Puntos 1er Servicio</span>
                                    <span class="stat-value-flip">${stats.first_serve_points_won || 0} <span class="stat-percentage">(${firstServePct}%)</span></span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">2do Servicio</span>
                                    <span class="stat-value-flip">${stats.second_serve_successful || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Puntos 2do Servicio</span>
                                    <span class="stat-value-flip">${stats.second_serve_points_won || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Efectividad Servicio</span>
                                    <span class="stat-value-flip">${servicePointsPct}%</span>
                                </div>
                            </div>
                        </div>

                        <!-- Break Points -->
                        <div class="stats-section">
                            <h5 class="stats-section-title">Break Points</h5>
                            <div class="stats-grid-flip">
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Convertidos</span>
                                    <span class="stat-value-flip">${breakpointsWon}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Total</span>
                                    <span class="stat-value-flip">${breakpointsTotal}</span>
                                </div>
                                <div class="stat-item-flip stat-item-highlight">
                                    <span class="stat-label-flip">Efectividad</span>
                                    <span class="stat-value-flip">${breakpointsPct}%</span>
                                </div>
                            </div>
                        </div>

                        <!-- Points & Games -->
                        <div class="stats-section">
                            <h5 class="stats-section-title">Puntos y Juegos</h5>
                            <div class="stats-grid-flip">
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Puntos Ganados</span>
                                    <span class="stat-value-flip">${stats.points_won || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Juegos Ganados</span>
                                    <span class="stat-value-flip">${stats.games_won || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Juegos de Servicio</span>
                                    <span class="stat-value-flip">${stats.service_games_won || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Tiebreaks Ganados</span>
                                    <span class="stat-value-flip">${stats.tiebreaks_won || 0}</span>
                                </div>
                            </div>
                        </div>

                        <!-- Streaks -->
                        <div class="stats-section">
                            <h5 class="stats-section-title">Rachas</h5>
                            <div class="stats-grid-flip">
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Puntos Consecutivos</span>
                                    <span class="stat-value-flip">${stats.max_points_in_a_row || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Juegos Consecutivos</span>
                                    <span class="stat-value-flip">${stats.max_games_in_a_row || 0}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    function attachStatsListeners() {
        // Handle Stats button click (open modal)
        document.querySelectorAll('.btn-stats').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const modalId = this.getAttribute('data-modal-id');
                const modal = document.getElementById(modalId);
                
                if (modal) {
                    modal.classList.add('active');
                    document.body.style.overflow = 'hidden'; // Prevent body scroll
                }
            });
        });
        
        // Handle close button click
        document.querySelectorAll('.btn-close-modal').forEach(button => {
            button.addEventListener('click', function(e) {
                e.stopPropagation();
                const modalId = this.getAttribute('data-modal-id');
                const modal = document.getElementById(modalId);
                
                if (modal) {
                    modal.classList.remove('active');
                    document.body.style.overflow = ''; // Restore body scroll
                }
            });
        });
        
        // Handle backdrop click (close modal)
        document.querySelectorAll('.stats-modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', function(e) {
                const modal = this.closest('.stats-modal');
                if (modal) {
                    modal.classList.remove('active');
                    document.body.style.overflow = ''; // Restore body scroll
                }
            });
        });
        
        // Handle Escape key (close modal)
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.stats-modal.active');
                if (activeModal) {
                    activeModal.classList.remove('active');
                    document.body.style.overflow = ''; // Restore body scroll
                }
            }
        });
    }

    function formatDateTime(dateTimeString) {
        if (!dateTimeString) return 'N/A';
        
        try {
            const date = new Date(dateTimeString);
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            return `${hours}:${minutes}`;
        } catch (e) {
            return dateTimeString;
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatPlayerNameShort(name) {
        if (!name) return 'N/A';
        
        // If name is already in "Lastname, Firstname" format
        if (name.includes(',')) {
            const parts = name.split(',').map(p => p.trim());
            if (parts.length >= 2) {
                const lastname = parts[0];
                const firstname = parts[1];
                const firstInitial = firstname.charAt(0).toUpperCase();
                return `${lastname}, ${firstInitial}.`;
            }
        }
        
        // If name is in "Firstname Lastname" format
        const nameParts = name.trim().split(/\s+/);
        if (nameParts.length >= 2) {
            const firstname = nameParts[0];
            const lastname = nameParts.slice(1).join(' ');
            const firstInitial = firstname.charAt(0).toUpperCase();
            return `${lastname}, ${firstInitial}.`;
        }
        
        // If only one part, return as is
        return name;
    }

    function attachPlayerListeners() {
        // Handle player button click
        document.querySelectorAll('.btn-player').forEach(button => {
            button.addEventListener('click', async function(e) {
                e.stopPropagation();
                const competitorId = this.getAttribute('data-competitor-id');
                const playerName = this.getAttribute('data-player-name');
                const matchIndex = this.getAttribute('data-match-index');
                const modalId = `player-modal-${matchIndex}`;
                const modal = document.getElementById(modalId);
                const bodyElement = document.getElementById(`player-profile-body-${matchIndex}`);
                
                if (!competitorId) {
                    alert('No se encontró el ID del competidor');
                    return;
                }
                
                if (modal && bodyElement) {
                    // Show modal with loading state
                    modal.classList.add('active');
                    document.body.style.overflow = 'hidden';
                    bodyElement.innerHTML = `
                        <div class="loading-indicator">
                            <div class="loading-spinner"></div>
                            <p>Cargando perfil de ${escapeHtml(playerName)}...</p>
                        </div>
                    `;
                    
                    try {
                        // Fetch competitor profile (encode competitor_id for URL)
                        const encodedCompetitorId = encodeURIComponent(competitorId);
                        const response = await fetch(`/api/competitor-profile/${encodedCompetitorId}`);
                        const data = await response.json();
                        
                        if (data.success && data.data) {
                            bodyElement.innerHTML = renderPlayerProfile(data.data);
                        } else {
                            bodyElement.innerHTML = `
                                <div class="stats-empty">
                                    <p>Error al cargar el perfil: ${escapeHtml(data.error || 'Error desconocido')}</p>
                                </div>
                            `;
                        }
                    } catch (error) {
                        console.error('Error fetching player profile:', error);
                        bodyElement.innerHTML = `
                            <div class="stats-empty">
                                <p>Error al cargar el perfil del jugador</p>
                            </div>
                        `;
                    }
                }
            });
            
            // Add hover effect to highlight player name
            button.addEventListener('mouseenter', function() {
                const playerName = this.getAttribute('data-player-name');
                const matchCard = this.closest('.match-card');
                if (matchCard) {
                    const playerElement = matchCard.querySelector(`[data-player-name="${playerName}"]`);
                    if (playerElement) {
                        playerElement.classList.add('player-highlight');
                    }
                }
            });
            
            button.addEventListener('mouseleave', function() {
                const playerName = this.getAttribute('data-player-name');
                const matchCard = this.closest('.match-card');
                if (matchCard) {
                    const playerElement = matchCard.querySelector(`[data-player-name="${playerName}"]`);
                    if (playerElement) {
                        playerElement.classList.remove('player-highlight');
                    }
                }
            });
        });
    }

    function renderPlayerProfile(profileData) {
        const competitor = profileData.competitor || {};
        const info = profileData.info || {};
        const rankings = profileData.competitor_rankings || [];
        const periods = profileData.periods || [];
        
        // Get the first (most recent) year
        const firstPeriod = periods.length > 0 ? periods[0] : null;
        
        let html = `
            <div class="player-profile-content">
                <!-- Player Basic Info -->
                <div class="player-profile-header">
                    <div class="player-profile-name">
                        <h2>${escapeHtml(competitor.name || 'N/A')}</h2>
                        ${competitor.country ? `<div class="player-profile-country">${escapeHtml(competitor.country)}</div>` : ''}
                    </div>
                    ${rankings.length > 0 ? `
                        <div class="player-profile-ranking">
                            <div class="ranking-item">
                                <span class="ranking-label">Ranking</span>
                                <span class="ranking-value">#${rankings[0].rank || 'N/A'}</span>
                            </div>
                            ${rankings[0].points ? `
                                <div class="ranking-item">
                                    <span class="ranking-label">Puntos</span>
                                    <span class="ranking-value">${rankings[0].points.toLocaleString()}</span>
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
                
                <!-- Player Details -->
                <div class="player-profile-details">
                    ${info.pro_year ? `<div class="detail-item"><span class="detail-label">Año Pro:</span><span class="detail-value">${info.pro_year}</span></div>` : ''}
                    ${info.handedness ? `<div class="detail-item"><span class="detail-label">Mano:</span><span class="detail-value">${info.handedness === 'right' ? 'Derecha' : info.handedness === 'left' ? 'Izquierda' : escapeHtml(info.handedness)}</span></div>` : ''}
                    ${info.height ? `<div class="detail-item"><span class="detail-label">Altura:</span><span class="detail-value">${info.height} cm</span></div>` : ''}
                    ${info.weight ? `<div class="detail-item"><span class="detail-label">Peso:</span><span class="detail-value">${info.weight} kg</span></div>` : ''}
                    ${info.date_of_birth ? `<div class="detail-item"><span class="detail-label">Fecha de Nacimiento:</span><span class="detail-value">${formatDate(info.date_of_birth)}</span></div>` : ''}
                    ${info.highest_singles_ranking ? `<div class="detail-item"><span class="detail-label">Mejor Ranking Singles:</span><span class="detail-value">#${info.highest_singles_ranking}${info.highest_singles_ranking_date ? ` (${info.highest_singles_ranking_date})` : ''}</span></div>` : ''}
                </div>
        `;
        
        // Statistics from first year
        if (firstPeriod) {
            const year = firstPeriod.year;
            const yearStats = firstPeriod.statistics || {};
            const surfaces = firstPeriod.surfaces || [];
            
            html += `
                <div class="player-profile-stats">
                    <h3 class="stats-year-title">Estadísticas ${year}</h3>
                    
                    <!-- Overall Statistics -->
                    <div class="stats-section">
                        <h4 class="stats-section-title">Resumen General</h4>
                        <div class="stats-grid-flip">
                            <div class="stat-item-flip">
                                <span class="stat-label-flip">Competiciones Jugadas</span>
                                <span class="stat-value-flip">${yearStats.competitions_played || 0}</span>
                            </div>
                            <div class="stat-item-flip">
                                <span class="stat-label-flip">Competiciones Ganadas</span>
                                <span class="stat-value-flip">${yearStats.competitions_won || 0}</span>
                            </div>
                            <div class="stat-item-flip">
                                <span class="stat-label-flip">Partidos Jugados</span>
                                <span class="stat-value-flip">${yearStats.matches_played || 0}</span>
                            </div>
                            <div class="stat-item-flip stat-item-highlight">
                                <span class="stat-label-flip">Partidos Ganados</span>
                                <span class="stat-value-flip">${yearStats.matches_won || 0}</span>
                            </div>
                            ${yearStats.matches_played > 0 ? `
                                <div class="stat-item-flip stat-item-highlight">
                                    <span class="stat-label-flip">Win Rate</span>
                                    <span class="stat-value-flip">${((yearStats.matches_won / yearStats.matches_played) * 100).toFixed(1)}%</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
            `;
            
            // Surface statistics
            if (surfaces.length > 0) {
                html += `
                    <div class="stats-section">
                        <h4 class="stats-section-title">Por Superficie</h4>
                `;
                
                surfaces.forEach(surface => {
                    const surfaceType = surface.type || 'unknown';
                    const surfaceStats = surface.statistics || {};
                    const surfaceName = formatSurfaceName(surfaceType);
                    
                    html += `
                        <div class="surface-stats">
                            <h5 class="surface-name">${escapeHtml(surfaceName)}</h5>
                            <div class="stats-grid-flip">
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Competiciones</span>
                                    <span class="stat-value-flip">${surfaceStats.competitions_played || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Ganadas</span>
                                    <span class="stat-value-flip">${surfaceStats.competitions_won || 0}</span>
                                </div>
                                <div class="stat-item-flip">
                                    <span class="stat-label-flip">Partidos</span>
                                    <span class="stat-value-flip">${surfaceStats.matches_played || 0}</span>
                                </div>
                                <div class="stat-item-flip stat-item-highlight">
                                    <span class="stat-label-flip">Ganados</span>
                                    <span class="stat-value-flip">${surfaceStats.matches_won || 0}</span>
                                </div>
                                ${surfaceStats.matches_played > 0 ? `
                                    <div class="stat-item-flip stat-item-highlight">
                                        <span class="stat-label-flip">Win Rate</span>
                                        <span class="stat-value-flip">${((surfaceStats.matches_won / surfaceStats.matches_played) * 100).toFixed(1)}%</span>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                });
                
                html += `</div>`;
            }
            
            html += `</div>`;
        }
        
        html += `</div>`;
        
        return html;
    }

    function formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric' });
        } catch (e) {
            return dateString;
        }
    }

    function formatSurfaceName(surfaceType) {
        const surfaceNames = {
            'hardcourt_indoor': 'Pista Dura (Interior)',
            'hardcourt_outdoor': 'Pista Dura (Exterior)',
            'grass': 'Hierba',
            'red_clay': 'Tierra Batida',
            'red_clay_indoor': 'Tierra Batida (Interior)',
            'carpet_indoor': 'Indoor',
            'unknown': 'Desconocida'
        };
        return surfaceNames[surfaceType] || surfaceType;
    }

    function showEmptyState() {
        emptyState.style.display = 'flex';
        matchesContainer.style.display = 'none';
    }

    // Load matches on page load
    fetchAndRenderMatches();
});

