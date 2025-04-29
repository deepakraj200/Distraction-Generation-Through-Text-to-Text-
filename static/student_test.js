// Global variables for test state
let testQuestions = [];
let testId = '';
let testStartTime = null;
let timeLimit = 30; // Default 30 minutes
let timerInterval = null;

// Get test ID from URL
window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    testId = urlParams.get('id');
    
    if (!testId) {
        document.getElementById('test-container').innerHTML = '<p>Error: No test ID provided</p>';
        return;
    }
    
    loadTest(testId);
    
    // Set up test submission handler
    document.getElementById('testForm').addEventListener('submit', function(e) {
        e.preventDefault();
        submitTest();
    });
};

// Load test data
function loadTest(testId) {
    fetch(`/get_test/${testId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                testQuestions = data.test.questions;
                document.getElementById('test-title').textContent = data.test.name || 'MCQ Test';
                timeLimit = data.test.timeLimit || 30;
                
                // Render questions
                renderQuestions(testQuestions);
                
                // Start timer
                startTimer(timeLimit);
            } else {
                document.getElementById('questions-container').innerHTML = `
                    <p>Error loading test: ${data.message}</p>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading test:', error);
            document.getElementById('questions-container').innerHTML = `
                <p>Error loading test. Please try again later.</p>
            `;
        });
}

// Render questions in the test form
function renderQuestions(questions) {
    const container = document.getElementById('questions-container');
    container.innerHTML = '';
    
    questions.forEach((question, qIndex) => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'test-question';
        
        // Remove the "(Correct)" marker from options for display
        const cleanOptions = question.options.map(opt => opt.replace(' (Correct)', ''));
        
        questionDiv.innerHTML = `
            <h4>Question ${qIndex + 1}: ${question.question}</h4>
            <ul class="options-list">
                ${cleanOptions.map((option, oIndex) => `
                    <li>
                        <label>
                            <input type="radio" name="question-${qIndex}" value="${option}">
                            ${option}
                        </label>
                    </li>
                `).join('')}
            </ul>
        `;
        
        container.appendChild(questionDiv);
    });
    
    // Record test start time
    testStartTime = Date.now();
}

// Start the timer
function startTimer(minutes) {
    const timerDisplay = document.getElementById('time-display');
    const endTime = Date.now() + (minutes * 60 * 1000);
    
    function updateTimer() {
        const now = Date.now();
        const timeLeft = Math.max(0, endTime - now);
        
        if (timeLeft === 0) {
            clearInterval(timerInterval);
            alert('Time is up! Your test will be submitted automatically.');
            submitTest();
            return;
        }
        
        const minutesLeft = Math.floor(timeLeft / (60 * 1000));
        const secondsLeft = Math.floor((timeLeft % (60 * 1000)) / 1000);
        
        timerDisplay.textContent = `${minutesLeft.toString().padStart(2, '0')}:${secondsLeft.toString().padStart(2, '0')}`;
    }
    
    // Update immediately and then every second
    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);
}

// Submit test
function submitTest() {
    const answers = [];
    
    testQuestions.forEach((question, qIndex) => {
        const selectedOption = document.querySelector(`input[name="question-${qIndex}"]:checked`);
        const correctOption = question.options.find(opt => opt.includes('(Correct)'));
        
        answers.push({
            question: question.question,
            selected: selectedOption ? selectedOption.value : null,
            correct: correctOption ? correctOption.replace(' (Correct)', '') : null
        });
    });
    
    // Calculate time taken in minutes
    const timeTaken = Math.round((Date.now() - testStartTime) / 60000);
    
    fetch('/submit_test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            testId: testId,
            answers: answers,
            timeTaken: timeTaken
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            clearInterval(timerInterval);
            alert(`Test submitted successfully! Your score: ${data.results.scorePercent}%`);
            window.location.href = `/test_results?id=${data.results.id}`;
        } else {
            alert(`Error submitting test: ${data.message}`);
        }
    })
    .catch(error => {
        console.error('Error submitting test:', error);
        alert('Error submitting test. Please try again.');
    });
}
