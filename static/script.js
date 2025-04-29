window.onload = function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;
            
            fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password, role })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    document.getElementById('loginMessage').innerText = data.message;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('loginMessage').innerText = 'Login failed. Please try again.';
            });
        });
    }

    // Upload form handling
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const fileInput = document.getElementById('pdfFile');
            if (fileInput.files.length === 0) {
                alert('Please select a file to upload.');
                return;
            }
            
            const formData = new FormData(this);
            const resultDiv = document.getElementById('result');
            
            // Show loading indicator
            resultDiv.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Generating MCQs... This may take a minute.</p>
                </div>
            `;
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.mcqs && data.mcqs.length > 0) {
                    displayMCQs(data.mcqs, data.questionSets);
                } else {
                    resultDiv.innerHTML = '<p>No MCQs were generated. Please try again with different parameters.</p>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                resultDiv.innerHTML = '<p>Error generating MCQs. Please try again later.</p>';
            });
        });
    }
};

function displayMCQs(mcqs, questionSets) {
    const resultDiv = document.getElementById('result');
    
    // Create tabs for all questions and question sets
    let tabsHTML = `
        <div class="tabs">
            <button class="tab-button active" data-tab="all-questions">All Questions</button>
            ${questionSets.map((set, index) => 
                `<button class="tab-button" data-tab="set-${index}">${set.name}</button>`
            ).join('')}
        </div>
        
        <div class="tab-content">
            <div id="all-questions" class="tab-pane active">
                <h3>All Generated Questions</h3>
                <div class="mcq-container">
                    ${mcqs.map((mcq, index) => 
                        `<div class="mcq-item">
                            <h4>Question ${index + 1}: ${mcq.question}</h4>
                            <ul class="options-list">
                                ${mcq.options.map(option => 
                                    `<li class="${option.includes('(Correct)') ? 'correct-answer' : ''}">${option}</li>`
                                ).join('')}
                            </ul>
                        </div>`
                    ).join('')}
                </div>
            </div>
            
            ${questionSets.map((set, setIndex) => 
                `<div id="set-${setIndex}" class="tab-pane">
                    <h3>${set.name}</h3>
                    <div class="mcq-container">
                        ${set.questions.map((mcq, qIndex) => 
                            `<div class="mcq-item">
                                <h4>Question ${qIndex + 1}: ${mcq.question}</h4>
                                <ul class="options-list">
                                    ${mcq.options.map(option => 
                                        `<li class="${option.includes('(Correct)') ? 'correct-answer' : ''}">${option}</li>`
                                    ).join('')}
                                </ul>
                            </div>`
                        ).join('')}
                    </div>
                </div>`
            ).join('')}
        </div>
        
        <div class="export-container">
            <button id="saveAsTestBtn">Save as Test</button>
        </div>
    `;
    
    resultDiv.innerHTML = tabsHTML;
    
    // Add event listeners to tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all tabs and panes
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
    
    // Add event listener to save test button
    document.getElementById('saveAsTestBtn').addEventListener('click', function() {
        // Implement save as test functionality
        saveAsTest(mcqs, questionSets);
    });
}

function saveAsTest(mcqs, questionSets) {
    // Create modal for test details
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <h3>Save as Test</h3>
            <form id="saveTestForm">
                <div class="form-group">
                    <label for="testName">Test Name:</label>
                    <input type="text" id="testName" required>
                </div>
                <div class="form-group">
                    <label for="timeLimit">Time Limit (minutes):</label>
                    <input type="number" id="timeLimit" min="5" max="180" value="30" required>
                </div>
                <button type="submit">Save Test</button>
            </form>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Close modal when clicking X
    modal.querySelector('.close').addEventListener('click', () => {
        document.body.removeChild(modal);
    });
    
    // Handle form submission
    modal.querySelector('#saveTestForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Get active tab to determine which question set to save
        const activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
        let questions = [];
        
        if (activeTab === 'all-questions') {
            questions = mcqs;
        } else {
            const setIndex = parseInt(activeTab.replace('set-', ''));
            questions = questionSets[setIndex].questions;
        }
        
        const testData = {
            name: document.getElementById('testName').value,
            timeLimit: parseInt(document.getElementById('timeLimit').value),
            questions: questions
        };
        
        // Send test data to server
        fetch('/save_test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(testData)
        })
        .then(response => response.json())
        .then(data => {
            document.body.removeChild(modal);
            if (data.success) {
                alert('Test saved successfully!');
            } else {
                alert('Failed to save test: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving test:', error);
            document.body.removeChild(modal);
            alert('Error saving test. Please try again later.');
        });
    });
}
