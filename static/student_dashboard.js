document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all tabs and panes
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
            
            // Load data for specific tabs when needed
            if (tabId === 'available-tests') {
                loadAvailableTests();
            } else if (tabId === 'test-history') {
                loadTestHistory();
            }
        });
    });

    // Load available tests
    function loadAvailableTests() {
        const testsContainer = document.getElementById('tests-list');
        testsContainer.innerHTML = '<p class="loading-text">Loading available tests...</p>';
        
        fetch('/available_tests')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.tests.length > 0) {
                    testsContainer.innerHTML = '';
                    data.tests.forEach(test => {
                        const testCard = document.createElement('div');
                        testCard.className = 'test-card';
                        testCard.innerHTML = `
                            <h4>${test.name}</h4>
                            <p>${test.questionCount} questions | ${test.timeLimit} minutes</p>
                            <button class="start-test-btn" data-id="${test.id}">Take Test</button>
                        `;
                        testsContainer.appendChild(testCard);
                    });

                    // Add event listeners to start test buttons
                    document.querySelectorAll('.start-test-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const testId = this.getAttribute('data-id');
                            window.location.href = `/take_test?id=${testId}`;
                        });
                    });
                } else {
                    testsContainer.innerHTML = '<p>No tests available at the moment.</p>';
                }
            })
            .catch(error => {
                console.error('Error loading tests:', error);
                testsContainer.innerHTML = '<p>Error loading tests. Please try again later.</p>';
            });
    }

    // Load test history
    function loadTestHistory() {
        const historyContainer = document.getElementById('history-list');
        historyContainer.innerHTML = '<p class="loading-text">Loading test history...</p>';
        
        fetch('/test_history')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.history.length > 0) {
                    historyContainer.innerHTML = `
                        <table class="history-table">
                            <thead>
                                <tr>
                                    <th>Test Name</th>
                                    <th>Date</th>
                                    <th>Score</th>
                                    <th>Time Taken</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.history.map(item => `
                                    <tr>
                                        <td>${item.testName}</td>
                                        <td>${new Date(item.date).toLocaleString()}</td>
                                        <td>${item.scorePercent}%</td>
                                        <td>${item.timeTaken} min</td>
                                        <td><a href="/test_results?id=${item.id}">View Results</a></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `;
                    
                    // If there's history, show the latest result in a pie chart
                    if (data.history.length > 0) {
                        const latestResult = data.history[0];
                        createPieChart(latestResult);
                    }
                } else {
                    historyContainer.innerHTML = '<p>Complete a test to see your history here.</p>';
                }
            })
            .catch(error => {
                console.error('Error loading test history:', error);
                historyContainer.innerHTML = '<p>Error loading test history. Please try again later.</p>';
            });
    }

    // Create pie chart for test results
    function createPieChart(result) {
        const chartContainer = document.getElementById('result-chart');
        if (!chartContainer) return;
        
        // Clear previous chart
        chartContainer.innerHTML = '<h4>Latest Test Result</h4>';
        
        // Create canvas for chart
        const canvas = document.createElement('canvas');
        canvas.id = 'pieChart';
        chartContainer.appendChild(canvas);
        
        // Calculate correct and incorrect answers
        const correct = result.scorePercent;
        const incorrect = 100 - correct;
        
        // Draw pie chart (using a simple div-based solution since we don't have Chart.js)
        const pieDiv = document.createElement('div');
        pieDiv.className = 'pie-chart-container';
        pieDiv.innerHTML = `
            <div class="pie-chart">
                <div class="pie-slice correct" style="transform: rotate(0deg); clip-path: polygon(50% 50%, 50% 0%, ${correct > 50 ? '100% 0%, 100% 100%, 0% 100%, 0% 0%' : `${50 + 50 * Math.sin(correct/100 * Math.PI * 2)}% ${50 - 50 * Math.cos(correct/100 * Math.PI * 2)}%, 50% 0%`})"></div>
                <div class="pie-slice incorrect" style="transform: rotate(${correct/100 * 360}deg); clip-path: polygon(50% 50%, 50% 0%, ${incorrect > 50 ? '100% 0%, 100% 100%, 0% 100%, 0% 0%' : `${50 + 50 * Math.sin(incorrect/100 * Math.PI * 2)}% ${50 - 50 * Math.cos(incorrect/100 * Math.PI * 2)}%, 50% 0%`})"></div>
            </div>
            <div class="pie-legend">
                <div class="legend-item">
                    <span class="color-box correct"></span>
                    <span>Correct: ${correct}%</span>
                </div>
                <div class="legend-item">
                    <span class="color-box incorrect"></span>
                    <span>Incorrect: ${incorrect}%</span>
                </div>
            </div>
        `;
        chartContainer.appendChild(pieDiv);
    }

    // Load available tests when the page loads
    loadAvailableTests();
});
