/* 
    ==========================================================================
    2.10. ANIMAÇÕES DE HOVER NAS DISCIPLINAS
    ==========================================================================
    */    /* 
    ==========================================================================
    2.11. PROGRESS BAR ANIMADA
    ==========================================================================
    */
    
    .progress-bar-container {
        width: 100%;
        height: 8px;
        background: #e2e8f0;
        border-radius: 10px;
        overflow: hidden;
        margin: 20px 0;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .progress-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #f59e0b, #ea580c);
        border-radius: 10px;
        animation: fillProgress 1.5s ease-out forwards;
        box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
    }
    
    /* Confete */
    .confetti {
        position: fixed;
        width: 10px;
        height: 10px;
        z-index: 9999;
        pointer-events: none;
        animation: confettiFall linear forwards;
    }
    
    /* 
    ==========================================================================
    2.12. SKELETON LOADING & SHIMMER
    ==========================================================================
    */
    
    .skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: shimmerLoading 1.5s infinite;
        border-radius: 8px;
    }
    
    @keyframes shimmerLoading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* 
    ==========================================================================
    2.13. CHECKBOX ANIMADO (CHECKMARK)
    ==========================================================================
    */
    
    .checkbox-animated {
        position: relative;
        display: inline-block;
        width: 24px;
        height: 24px;
    }
    
    .checkbox-animated input[type="checkbox"] {
        display: none;
    }
    
    .checkbox-custom {
        position: absolute;
        top: 0;
        left: 0;
        width: 24px;
        height: 24px;
        border: 2px solid #cbd5e1;
        border-radius: 6px;
        background: white;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .checkbox-animated input[type="checkbox"]:checked + .checkbox-custom {
        background: #22c55e;
        border-color: #22c55e;
        animation: checkboxPop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    @keyframes checkboxPop {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.2); }
    }
    
    .checkbox-custom::after {
        content: '';
        position: absolute;
        top: 2px;
        left: 7px;
        width: 6px;
        height: 12px;
        border: solid white;
        border-width: 0 2px 2px 0;
        transform: rotate(45deg) scale(0);
        transition: transform 0.2s ease 0.1s;
    }
    
    .checkbox-animated input[type="checkbox"]:checked + .checkbox-custom::after {
        transform: rotate(45deg) scale(1);
        animation: checkmarkDraw 0.3s ease forwards;
    }
    
    @keyframes checkmarkDraw {
        0% {
            height: 0;
            width: 0;
        }
        50% {
            height: 12px;
            width: 0;
        }
        100% {
            height: 12px;
            width: 6px;
        }
    }
    
    /* 
    ==========================================================================
    2.14. BUSCA COM HIGHLIGHT
    ==========================================================================
    */
    
    .search-container {
        position: sticky;
        top: 0;
        z-index: 100;
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    
    .search-input {
        width: 100%;
        padding: 12px 16px;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .search-input:focus {
        outline: none;
        border-color: #ea580c;
        box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.1);
    }
    
    .highlight {
        background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%);
        padding: 2px 4px;
        border-radius: 3px;
        animation: highlightPulse 1s ease-in-out;
    }
    
    @keyframes highlightPulse {
        0%, 100% { background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%); }
        50% { background: linear-gradient(120deg, #fde68a 0%, #fbbf24 100%); }
    }
    
    /* 
    ==========================================================================
    2.15. STREAK COUNTER
    ==========================================================================
    */
    
    .streak-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, #ff6b6b, #ee5a6f);
        color: white;
        padding: 8px 16px;
        border-radius: 50px;
        font-weight: 700;
        font-size: 0.9rem;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
        animation: streakPulse 2s ease-in-out infinite;
    }
    
    @keyframes streakPulse {
        0%, 100% { 
            transform: scale(1);
            box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3);
        }
        50% { 
            transform: scale(1.05);
            box-shadow: 0 6px 20px rgba(255, 107, 107, 0.5);
        }
    }
    
    .flame-icon {
        animation: flameFlicker 1.5s ease-in-out infinite;
        font-size: 1.2rem;
    }
    
    @keyframes flameFlicker {
        0%, 100% { transform: scale(1) rotate(-5deg); }
        25% { transform: scale(1.1) rotate(5deg); }
        50% { transform: scale(0.95) rotate(-3deg); }
        75% { transform: scale(1.05) rotate(3deg); }
    }
    
    /* 
    ==========================================================================
    2.16. POMODORO TIMER
    ==========================================================================
    */
    
    .pomodoro-container {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    .timer-circle {
        position: relative;
        width: 120px;
        height: 120px;
        margin: 0 auto;
    }
    
    .timer-circle svg {
        transform: rotate(-90deg);
    }
    
    .timer-text {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* 
    ==========================================================================
    2.17. TRANSITIONS SUAVES ENTRE SEÇÕES
    ==========================================================================
    */
    
    .section-fade {
        animation: sectionFadeIn 0.8s ease-out forwards;
        opacity: 0;
    }
    
    @keyframes sectionFadeIn {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .section-fade:nth-child(1) { animation-delay: 0.1s; }
    .section-fade:nth-child(2) { animation-delay: 0.2s; }
    .section-fade:nth-child(3) { animation-delay: 0.3s; }
    
    /* 
    ==========================================================================
    2.18. MILESTONE CELEBRATION (Fogos)
    ==========================================================================
    */
    
    .firework {
        position: fixed;
        width: 4px;
        height: 4px;
        border-radius: 50%;
        pointer-events: none;
        z-index: 10000;
    }
    
    @keyframes fireworkExplode {
        0% {
            opacity: 1;
            transform: translate(0, 0) scale(1);
        }
        100% {
            opacity: 0;
            transform: translate(var(--tx), var(--ty)) scale(0);
        }
    }
    
    .disciplina-header {
        margin-top: 30px;
        border-bottom: 2px solid;
        padding-bottom: 5px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    
    .disciplina-header::before {
        content: '';
        position: absolute;
        left: -100%;
        bottom: 0;
        width: 100%;
        height: 2px;
        background: linear-gradient(90deg, transparent, white, transparent);
        transition: left 0.6s ease;
    }
    
    .disciplina-header:hover::before {
        left: 100%;
    }
    
    .disciplina-header:hover {
        transform: translateX(5px);
        padding-left: 10px;
    }

    /* Animação do Título Dashboard */
    .header-content h1 {
        background: linear-gradient(90deg, #ffffff 0%, #93c5fd 50%, #ffffff 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 3s linear infinite;
        cursor: pointer;
    }
    
    @keyframes shimmer {
        to {
            background-position: 200% center;
        }
    }
    
    /* Easter Egg - Tema Secreto */
    body.secret-theme {
        background: linear-gradient(45deg, #1a0033, #330033, #1a0033) !important;
    }
    
    body.secret-theme .header-container {
        background: linear-gradient(135deg, #6b21a8 0%, #7c3aed 100%) !important;
        box-shadow: 0 0 30px rgba(124, 58, 237, 0.6) !important;
    }
    
    body.secret-theme .metric-card {
        background: rgba(30, 27, 75, 0.8) !important;
        border-color: #7c3aed !important;
        color: white !important;
    }
    
    body.secret-theme .metric-value {
        color: #c084fc !important;
    }

    /* Responsividade */
    @media (max-width: 768px) {
        .header-container {
            flex-direction: column;
            padding: 1.5rem;
            text-align: center;
        }
        .header-logo {
            position: static;
            margin-bottom: 1rem;
            transform: none;
        }
        .header-info {
            position: static;
            margin-top: 1rem;
            text-align: center;
            width: 100%;
        }
        .metric-card {
            margin-bottom: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)
