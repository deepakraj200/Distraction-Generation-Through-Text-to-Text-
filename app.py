from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import PyPDF2
import requests
import json
import random
import uuid
from datetime import datetime

app = Flask(__name__, static_folder='static')
app.secret_key = "your_secret_key" # Change this to a secure key
CORS(app)

# Folder paths
UPLOAD_FOLDER = 'uploads'
DATA_FOLDER = 'data'
TESTS_FOLDER = os.path.join(DATA_FOLDER, 'tests')
RESULTS_FOLDER = os.path.join(DATA_FOLDER, 'results')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TESTS_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Fake database for login credentials (Use a real DB later)
USERS = {
    "student1": {"password": "pass123", "role": "student"},
    "student2": {"password": "student456", "role": "student"},
    "staff1": {"password": "staffpass", "role": "staff"},
    "admin": {"password": "adminpass", "role": "staff"}
}

# Replace with your Groq API key
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

@app.route('/')
def login_page():
    if "username" in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")
    
    user = USERS.get(username)
    if user and user["password"] == password and user["role"] == role:
        session["username"] = username
        session["role"] = role
        print(f"Login successful: {username} as {role}")
        return jsonify({"success": True})
    
    return jsonify({"success": False, "message": "Invalid credentials. Please try again."})

@app.route('/dashboard')
def dashboard():
    if "username" not in session:
        return redirect(url_for('login_page'))
    
    role = session.get("role")
    username = session.get("username")
    print(f"User logged in as {username} ({role})")
    
    if role == "student":
        return render_template("student_dashboard.html", username=username, role=role)
    elif role == "staff":
        return render_template("staff_dashboard.html", username=username, role=role)
    
    return redirect(url_for('logout'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/available_tests')
def available_tests():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    tests = []
    for filename in os.listdir(TESTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(TESTS_FOLDER, filename), 'r') as f:
                test_data = json.load(f)
                tests.append({
                    "id": test_data["id"],
                    "name": test_data["name"],
                    "questionCount": len(test_data["questions"]),
                    "timeLimit": test_data.get("timeLimit", 30),
                    "creator": test_data.get("creator", "Unknown"),
                    "difficulty": test_data.get("difficulty", "Standard")
                })
    
    return jsonify({"success": True, "tests": tests})

@app.route('/get_test/<test_id>')
def get_test(test_id):
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404
    
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    return jsonify({"success": True, "test": test_data})

@app.route('/take_test')
def take_test():
    if "username" not in session or session["role"] != "student":
        return redirect(url_for('login_page'))
    
    return render_template('take_test.html')

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    test_id = data.get('testId')
    answers = data.get('answers', [])
    time_taken = data.get('timeTaken', 0)
    
    if not test_id or not answers:
        return jsonify({"success": False, "message": "Missing required fields"})
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404
    
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    # Evaluate answers
    correct_count = 0
    total_questions = len(answers)
    evaluated_answers = []
    
    for answer in answers:
        question = answer.get('question')
        selected = answer.get('selected')
        correct = answer.get('correct')
        is_correct = selected == correct
        
        if is_correct:
            correct_count += 1
        
        # Generate feedback using AI
        feedback = generate_feedback(question, selected, correct, is_correct)
        
        evaluated_answers.append({
            "question": question,
            "selected": selected,
            "correct": correct,
            "isCorrect": is_correct,
            "feedback": feedback
        })
    
    # Calculate score
    score_percent = round((correct_count / total_questions) * 100) if total_questions > 0 else 0
    
    # Save result
    result_id = str(uuid.uuid4())
    result_data = {
        "id": result_id,
        "testId": test_id,
        "testName": test_data["name"],
        "student": session["username"],
        "date": datetime.now().isoformat(),
        "scorePercent": score_percent,
        "correctCount": correct_count,
        "totalQuestions": total_questions,
        "timeTaken": time_taken,
        "answers": evaluated_answers
    }
    
    with open(os.path.join(RESULTS_FOLDER, f"{result_id}.json"), 'w') as f:
        json.dump(result_data, f, indent=2)
    
    return jsonify({
        "success": True,
        "results": {
            "id": result_id,
            "scorePercent": score_percent,
            "correctCount": correct_count,
            "totalQuestions": total_questions,
            "timeTaken": time_taken
        }
    })

def generate_feedback(question, selected, correct, is_correct):
    # If the answer is correct, give positive feedback
    if is_correct:
        return "Correct! Well done."
    
    # If answer is incorrect, generate personalized feedback
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
    Question: {question}
    Student's answer: {selected}
    Correct answer: {correct}
    Provide a brief, helpful feedback (2-3 sentences) explaining why the student's answer is incorrect and why the correct answer is better. Be encouraging and educational.
    """
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are an educational assistant providing helpful feedback to students on their test answers."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        feedback = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return feedback.strip()
    except Exception as e:
        print(f"Error generating feedback: {e}")
        return "Your answer was incorrect. Review the correct answer and related material."

@app.route('/test_history')
def test_history():
    if "username" not in session or session["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    student = session["username"]
    history = []
    
    for filename in os.listdir(RESULTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(RESULTS_FOLDER, filename), 'r') as f:
                result_data = json.load(f)
                if result_data.get("student") == student:
                    history.append({
                        "id": result_data["id"],
                        "testId": result_data.get("testId", ""),
                        "testName": result_data["testName"],
                        "date": result_data["date"],
                        "scorePercent": result_data.get("scorePercent", 0),
                        "timeTaken": result_data.get("timeTaken", 0)
                    })
    
    # Sort by date (newest first)
    history.sort(key=lambda x: x["date"], reverse=True)
    return jsonify({"success": True, "history": history})

@app.route('/test_results')
def test_results():
    if "username" not in session:
        return redirect(url_for('login_page'))
    
    result_id = request.args.get('id')
    if not result_id:
        return redirect(url_for('dashboard'))
    
    result_file = os.path.join(RESULTS_FOLDER, f"{result_id}.json")
    if not os.path.exists(result_file):
        return redirect(url_for('dashboard'))
    
    with open(result_file, 'r') as f:
        result_data = json.load(f)
    
    # Check if the user is authorized to view this result
    if session["role"] == "student" and result_data["student"] != session["username"]:
        return redirect(url_for('dashboard'))
    
    return render_template('test_results.html', result=result_data)

@app.route('/get_result/<result_id>')
def get_result(result_id):
    if "username" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    result_file = os.path.join(RESULTS_FOLDER, f"{result_id}.json")
    if not os.path.exists(result_file):
        return jsonify({"success": False, "message": "Result not found"}), 404
    
    with open(result_file, 'r') as f:
        result_data = json.load(f)
    
    # Verify the user has permission to view this result
    if session["role"] == "student" and result_data["student"] != session["username"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    return jsonify({"success": True, "result": result_data})

def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def generate_question_sets(mcqs, num_sets):
    """Generate random sets of questions from the MCQs"""
    if not mcqs:
        return []
    
    total_questions = len(mcqs)
    questions_per_set = min(total_questions, max(3, total_questions // 2))
    question_sets = []
    
    for i in range(num_sets):
        # Create a copy of the questions to shuffle to avoid modifying the original
        question_pool = mcqs.copy()
        random.shuffle(question_pool)
        
        # Take a subset of questions for this set
        set_questions = question_pool[:questions_per_set]
        
        # Create the set with a name
        question_sets.append({
            "name": f"Set {i+1}",
            "questions": set_questions
        })
    
    return question_sets

@app.route('/upload', methods=['POST'])
def upload():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    num_questions = int(request.form.get('num_questions', 5))
    complexity = request.form.get('complexity', 'Easy')
    num_sets = int(request.form.get('num_sets', 4))
    num_question_sets = int(request.form.get('num_question_sets', 3))
    
    extracted_text = extract_text_from_pdf(filepath)
    mcqs = generate_ai_mcqs(extracted_text, num_questions, complexity, num_sets)
    
    # Generate random question sets
    question_sets = generate_question_sets(mcqs, num_question_sets)
    
    return jsonify({
        "success": True,
        "mcqs": mcqs,
        "questionSets": question_sets
    })

def generate_ai_mcqs(text, num_questions, complexity, num_sets):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Truncate text if too long (API limits)
    max_tokens = 16000
    if len(text) > max_tokens:
        text = text[:max_tokens]
    
    # Create the prompt for MCQ generation
    prompt = f"""
    Based on the following text, generate {num_questions} multiple-choice questions with {num_sets} options each.
    The complexity level should be {complexity}.
    For each question:
    1. Create a clear, concise question
    2. Provide {num_sets} options (including one correct answer and {num_sets-1} distractors)
    3. Mark the correct answer
    4. Ensure distractors are plausible but clearly incorrect
    5. Make sure options don't overlap in meaning
    
    TEXT:
    {text}
    
    FORMAT YOUR RESPONSE AS A JSON ARRAY of objects with the following structure:
    
    {{
        "question": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option A"
    }}
    
    Only provide the JSON array, no additional text.
    """
    
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": "You are an expert in generating high-quality multiple choice questions with plausible distractors. You always format your responses as properly structured JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        
        # Extract the JSON from the response
        assistant_message = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse the JSON response
        try:
            import re
            json_match = re.search(r'\[\s*{.*}\s*\]', assistant_message, re.DOTALL)
            if json_match:
                assistant_message = json_match.group(0)
            
            mcqs = json.loads(assistant_message)
            formatted_mcqs = []
            
            for i, mcq in enumerate(mcqs):
                question = mcq.get("question", "")
                options = mcq.get("options", [])
                correct_answer = mcq.get("correct_answer", "")
                
                # Mark the correct answer in the options
                marked_options = []
                for option in options:
                    if option == correct_answer:
                        marked_options.append(f"{option} (Correct)")
                    else:
                        marked_options.append(option)
                
                formatted_mcqs.append({
                    "question": question,
                    "options": marked_options
                })
            
            return formatted_mcqs
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            print("Response content:", assistant_message)
            return []
    except Exception as e:
        print(f"Error generating MCQs: {e}")
        return []

@app.route('/save_test', methods=['POST'])
def save_test():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    test_id = str(uuid.uuid4())
    
    test_data = {
        "id": test_id,
        "name": data.get("name", "Untitled Test"),
        "timeLimit": data.get("timeLimit", 30),
        "questions": data.get("questions", []),
        "createdAt": datetime.now().isoformat(),
        "createdBy": session["username"],
        "difficulty": data.get("difficulty", "Standard")
    }
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    return jsonify({"success": True, "id": test_id})

@app.route('/staff_tests')
def staff_tests():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    tests = []
    for filename in os.listdir(TESTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(TESTS_FOLDER, filename), 'r') as f:
                test_data = json.load(f)
                tests.append({
                    "id": test_data["id"],
                    "name": test_data["name"],
                    "questionCount": len(test_data["questions"]),
                    "timeLimit": test_data.get("timeLimit", 30),
                    "createdAt": test_data.get("createdAt", ""),
                    "createdBy": test_data.get("createdBy", "Unknown"),
                    "difficulty": test_data.get("difficulty", "Standard")
                })
    
    # Sort by date (newest first)
    tests.sort(key=lambda x: x["createdAt"], reverse=True)
    return jsonify({"success": True, "tests": tests})

@app.route('/student_results')
def student_results():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    results = []
    for filename in os.listdir(RESULTS_FOLDER):
        if filename.endswith('.json'):
            with open(os.path.join(RESULTS_FOLDER, filename), 'r') as f:
                result_data = json.load(f)
                results.append({
                    "id": result_data["id"],
                    "student": result_data["student"],
                    "testName": result_data["testName"],
                    "date": result_data["date"],
                    "scorePercent": result_data.get("scorePercent", round(result_data.get("score", 0) * 100)),
                    "correctCount": result_data.get("correctCount", result_data.get("correct", 0)),
                    "totalQuestions": result_data.get("totalQuestions", result_data.get("total", 0))
                })
    
    # Sort by date (newest first)
    results.sort(key=lambda x: x["date"], reverse=True)
    return jsonify({"success": True, "results": results})

@app.route('/create_test')
def create_test():
    if "username" not in session or session["role"] != "staff":
        return redirect(url_for('login_page'))
    
    return render_template('create_test.html')

@app.route('/edit_test/<test_id>')
def edit_test(test_id):
    if "username" not in session or session["role"] != "staff":
        return redirect(url_for('login_page'))
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return redirect(url_for('dashboard'))
    
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    return render_template('edit_test.html', test=test_data)

@app.route('/update_test', methods=['POST'])
def update_test():
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    data = request.json
    test_id = data.get('id')
    
    if not test_id:
        return jsonify({"success": False, "message": "Missing test ID"}), 400
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404
    
    # Read existing test data
    with open(test_file, 'r') as f:
        test_data = json.load(f)
    
    # Update test data
    test_data["name"] = data.get("name", test_data["name"])
    test_data["timeLimit"] = data.get("timeLimit", test_data["timeLimit"])
    test_data["questions"] = data.get("questions", test_data["questions"])
    test_data["updatedAt"] = datetime.now().isoformat()
    test_data["updatedBy"] = session["username"]
    
    # Save updated test
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    return jsonify({"success": True, "id": test_id})

@app.route('/delete_test/<test_id>', methods=['POST'])
def delete_test(test_id):
    if "username" not in session or session["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    test_file = os.path.join(TESTS_FOLDER, f"{test_id}.json")
    if not os.path.exists(test_file):
        return jsonify({"success": False, "message": "Test not found"}), 404
    
    try:
        os.remove(test_file)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/view_result/<result_id>')
def view_result(result_id):
    if "username" not in session:
        return redirect(url_for('login_page'))
    
    result_file = os.path.join(RESULTS_FOLDER, f"{result_id}.json")
    if not os.path.exists(result_file):
        return redirect(url_for('dashboard'))
    
    with open(result_file, 'r') as f:
        result_data = json.load(f)
    
    # Check if the user is authorized to view this result
    if session["role"] == "student" and result_data["student"] != session["username"]:
        return redirect(url_for('dashboard'))
    
    return render_template('view_result.html', result=result_data)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)

