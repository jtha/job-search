// Shared navigation configuration and functionality
// 
// TO ADD A NEW PAGE:
// 1. Add it to the pages array below with a unique id
// 2. Create your page HTML file and call initNavigation('your-page-id')
// 3. That's it! The navigation will automatically update across all pages
//
const NavigationConfig = {
    brand: "Job Search Copilot",
    pages: [
        { name: "Dashboard", path: "dashboard/dashboard.html", id: "dashboard" },
        { name: "History", path: "history/history.html", id: "history" },
        { name: "Session", path: "session/session.html", id: "session" },
        { name: "Resume", path: "resume/resume.html", id: "resume" }
        // Add new pages here!
        // { name: "Analytics", path: "analytics/analytics.html", id: "analytics" },
    ]
};

class Navigation {
    constructor(currentPageId) {
        this.currentPageId = currentPageId;
    }

    generateNavigation() {
        // Create navigation HTML
        const navLinks = NavigationConfig.pages.map(page => {
            const isActive = page.id === this.currentPageId;
            const ariaCurrent = isActive ? ' aria-current="page"' : '';
            return `        <li><a href="../${page.path}"${ariaCurrent}>${page.name}</a></li>`;
        }).join('\n');

        return `<nav class="top-nav" aria-label="Primary">
    <div class="nav-inner">
        <div class="brand">${NavigationConfig.brand}</div>
        <ul class="nav-links" role="list">
${navLinks}
        </ul>
        <div class="spacer" aria-hidden="true"></div>
    </div>
</nav>`;
    }

    render() {
        console.log('Navigation render() called');
        // Insert navigation at the beginning of body
        const navHtml = this.generateNavigation();
        console.log('Generated navigation HTML:', navHtml.substring(0, 100) + '...');
        document.body.insertAdjacentHTML('afterbegin', navHtml);
        console.log('Navigation HTML inserted');
    }
}

// Initialize navigation when DOM is loaded
function initNavigation(currentPageId) {
    console.log('initNavigation called with:', currentPageId);
    
    if (document.readyState === 'loading') {
        console.log('DOM still loading, waiting for DOMContentLoaded');
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOMContentLoaded fired, creating navigation');
            const nav = new Navigation(currentPageId);
            nav.render();
        });
    } else {
        console.log('DOM already ready, creating navigation immediately');
        // DOM is already ready
        const nav = new Navigation(currentPageId);
        nav.render();
    }
}

// Export for use in individual pages
window.initNavigation = initNavigation;
window.NavigationConfig = NavigationConfig;