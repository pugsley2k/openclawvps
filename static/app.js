// ==================== DOM ELEMENTS ====================
const cardNameInput = document.getElementById('cardName');
const searchBtn = document.getElementById('searchBtn');
const thresholdSlider = document.getElementById('thresholdSlider');
const thresholdValue = document.getElementById('thresholdValue');
const resultsSection = document.getElementById('resultsSection');
const tabButtons = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

const watchlistCardName = document.getElementById('watchlistCardName');
const watchlistCardSet = document.getElementById('watchlistCardSet');
const watchlistThreshold = document.getElementById('watchlistThreshold');
const addWatchlistBtn = document.getElementById('addWatchlistBtn');
const watchlistContainer = document.getElementById('watchlistContainer');

const dealsContainer = document.getElementById('dealsContainer');

// ==================== EVENT LISTENERS ====================
searchBtn.addEventListener('click', searchCards);
cardNameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') searchCards();
});

thresholdSlider.addEventListener('input', (e) => {
    thresholdValue.textContent = e.target.value;
});

addWatchlistBtn.addEventListener('click', addToWatchlist);

tabButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
        const tab = e.target.dataset.tab;
        switchTab(tab);
    });
});

// ==================== MAIN FUNCTIONS ====================
async function searchCards() {
    const cardName = cardNameInput.value.trim();
    const threshold = parseInt(thresholdSlider.value);

    if (!cardName) {
        alert('Please enter a card name');
        return;
    }

    searchBtn.disabled = true;
    searchBtn.textContent = '🔍 Searching...';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_name: cardName, threshold })
        });

        const data = await response.json();

        // Display market price
        if (data.market_price) {
            document.getElementById('marketPrice').textContent = 
                `£${data.market_price.price.toFixed(2)} (${data.market_price.currency} - ${data.market_price.source})`;
        } else {
            document.getElementById('marketPrice').textContent = 'Price not found';
        }

        // Display results
        displayEbayResults(data.ebay, data.market_price);
        displayVintedResults(data.vinted, data.market_price);

        resultsSection.style.display = 'block';
        switchTab('ebay');
    } catch (error) {
        console.error('Search error:', error);
        alert('Error searching for card. Check console.');
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = '🔍 Search';
    }
}

function displayEbayResults(listings, marketPrice) {
    const tbody = document.getElementById('ebayTableBody');
    
    if (!listings || listings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No eBay listings found</td></tr>';
        return;
    }

    tbody.innerHTML = listings.map(listing => {
        const discount = marketPrice ? 
            ((marketPrice.price - listing.price) / marketPrice.price * 100).toFixed(1) : 0;
        
        let discountClass = 'discount-low';
        if (discount > 30) discountClass = 'discount-high';
        else if (discount > 15) discountClass = 'discount-medium';

        return `
            <tr>
                <td>${listing.title}</td>
                <td>£${listing.price?.toFixed(2) || 'N/A'}</td>
                <td>£${marketPrice?.price?.toFixed(2) || 'N/A'}</td>
                <td><span class="${discountClass}">${discount}%</span></td>
                <td>${listing.condition || 'Unknown'}</td>
                <td><a href="${listing.url}" target="_blank">View →</a></td>
            </tr>
        `;
    }).join('');
}

function displayVintedResults(listings, marketPrice) {
    const tbody = document.getElementById('vintedTableBody');
    
    if (!listings || listings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No Vinted listings found</td></tr>';
        return;
    }

    tbody.innerHTML = listings.map(listing => {
        const discount = marketPrice ? 
            ((marketPrice.price - listing.price) / marketPrice.price * 100).toFixed(1) : 0;
        
        let discountClass = 'discount-low';
        if (discount > 30) discountClass = 'discount-high';
        else if (discount > 15) discountClass = 'discount-medium';

        return `
            <tr>
                <td>${listing.title}</td>
                <td>£${listing.price?.toFixed(2) || 'N/A'}</td>
                <td>£${marketPrice?.price?.toFixed(2) || 'N/A'}</td>
                <td><span class="${discountClass}">${discount}%</span></td>
                <td>${listing.condition || 'Unknown'}</td>
                <td><a href="${listing.url}" target="_blank">View →</a></td>
            </tr>
        `;
    }).join('');
}

function switchTab(tabName) {
    // Update tab buttons
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });

    // Update tab contents
    tabContents.forEach(content => {
        content.classList.remove('active');
        if (content.id === `${tabName}Tab`) {
            content.classList.add('active');
        }
    });
}

// ==================== WATCHLIST FUNCTIONS ====================
async function addToWatchlist() {
    const cardName = watchlistCardName.value.trim();
    const cardSet = watchlistCardSet.value.trim();
    const threshold = parseInt(watchlistThreshold.value) || 20;

    if (!cardName) {
        alert('Please enter a card name');
        return;
    }

    try {
        const response = await fetch('/api/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_name: cardName, card_set: cardSet, threshold })
        });

        const data = await response.json();

        if (response.ok) {
            watchlistCardName.value = '';
            watchlistCardSet.value = '';
            watchlistThreshold.value = '20';
            loadWatchlist();
            showMessage('Card added to watchlist!', 'success');
        } else {
            alert(data.error || 'Error adding to watchlist');
        }
    } catch (error) {
        console.error('Watchlist error:', error);
        alert('Error adding to watchlist');
    }
}

async function loadWatchlist() {
    try {
        const response = await fetch('/api/watchlist');
        const items = await response.json();

        if (items.length === 0) {
            watchlistContainer.innerHTML = '<p class="placeholder">No cards in watchlist. Add one above!</p>';
            return;
        }

        watchlistContainer.innerHTML = items.map(item => `
            <div class="watchlist-item">
                <div class="watchlist-item-info">
                    <div class="watchlist-item-name">${item.card_name}</div>
                    <div class="watchlist-item-details">
                        ${item.card_set ? `Set: ${item.card_set} | ` : ''}
                        Added: ${new Date(item.added_at).toLocaleDateString()}
                    </div>
                </div>
                <div class="watchlist-item-threshold">${item.threshold}% threshold</div>
                <button class="remove-btn" onclick="removeFromWatchlist(${item.id})">Remove</button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading watchlist:', error);
    }
}

async function removeFromWatchlist(id) {
    if (!confirm('Remove this card from watchlist?')) return;

    try {
        const response = await fetch('/api/watchlist', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        });

        if (response.ok) {
            loadWatchlist();
            showMessage('Card removed from watchlist', 'success');
        } else {
            alert('Error removing from watchlist');
        }
    } catch (error) {
        console.error('Error removing:', error);
    }
}

// ==================== DEALS FUNCTIONS ====================
async function loadDeals() {
    try {
        const response = await fetch('/api/deals');
        const deals = await response.json();

        if (deals.length === 0) {
            dealsContainer.innerHTML = '<p class="placeholder">No deals found yet. Start searching or add to watchlist!</p>';
            return;
        }

        dealsContainer.innerHTML = deals.slice(0, 20).map(deal => `
            <div class="deal-item">
                <div class="deal-item-content">
                    <div class="deal-item-title">${deal.card_name}</div>
                    <div class="deal-item-meta">
                        <span class="deal-item-source">${deal.source}</span>
                        <span><strong>Price:</strong> £${deal.price?.toFixed(2) || 'N/A'}</span>
                        <span><strong>Market:</strong> £${deal.market_price?.toFixed(2) || 'N/A'}</span>
                        <span class="deal-item-discount">-${deal.discount_percent?.toFixed(1) || 0}%</span>
                    </div>
                    <a href="${deal.url}" target="_blank" class="deal-item-link">View Listing →</a>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading deals:', error);
    }
}

// ==================== UTILITY FUNCTIONS ====================
function showMessage(message, type = 'info') {
    const div = document.createElement('div');
    div.className = type;
    div.textContent = message;
    div.style.margin = '20px 0';
    div.style.padding = '15px';
    div.style.borderRadius = '6px';
    
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.parentNode.insertBefore(div, resultsSection.nextSibling);
    
    setTimeout(() => div.remove(), 5000);
}

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('🔍 Pokemon Card Bargain Finder loaded');
    loadWatchlist();
    loadDeals();
    
    // Refresh deals every 5 minutes
    setInterval(loadDeals, 300000);
});

// ==================== API HEALTH CHECK ====================
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('✅ App health:', data);
        return true;
    } catch (error) {
        console.error('❌ App health check failed:', error);
        return false;
    }
}

// Run health check on load
window.addEventListener('load', checkHealth);
